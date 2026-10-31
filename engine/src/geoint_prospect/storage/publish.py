"""Publishing: checksum first, then upload, then read-back verification per provider.

Nothing here is atomic across providers: each provider gets its own result, and a failure on one is
never hidden by a success on another. Objects whose checksum and size already match are skipped, so a
retry cannot silently duplicate or overwrite data.
"""

import tempfile
from collections.abc import Sequence
from pathlib import Path

from geoint_prospect.storage.contracts import PublishResult
from geoint_prospect.storage.keys import raw_key, slug
from geoint_prospect.storage.providers import StorageProvider, file_checksum

VERIFY_DIR = "geoint-verify"


def publish_file(
    path: Path,
    key: str,
    providers: Sequence[StorageProvider],
    *,
    verify: bool = True,
    overwrite: bool = False,
    workspace: Path | None = None,
) -> list[PublishResult]:
    """Upload one file to every provider, with optional read-back verification."""
    checksum = file_checksum(path)
    size = path.stat().st_size
    results: list[PublishResult] = []

    for provider in providers:
        bucket = provider.config.bucket
        provider_name = provider.config.provider
        try:
            existing = provider.head(key)
            if (
                existing is not None
                and not overwrite
                and existing.bytes == size
                and existing.checksum_sha256 == checksum
            ):
                results.append(
                    PublishResult(
                        provider=provider_name,
                        bucket=bucket,
                        key=key,
                        bytes=size,
                        checksum_sha256=checksum,
                        status="skipped",
                        verified=True,
                    )
                )
                continue

            provider.upload(path, key, checksum_sha256=checksum)
            if not verify:
                results.append(
                    PublishResult(
                        provider=provider_name,
                        bucket=bucket,
                        key=key,
                        bytes=size,
                        checksum_sha256=checksum,
                        status="published",
                    )
                )
                continue

            results.append(_verify(provider, key, checksum, size, workspace))
        except Exception as exc:  # noqa: BLE001 - one provider must never break the others
            results.append(
                PublishResult(
                    provider=provider_name,
                    bucket=bucket,
                    key=key,
                    bytes=size,
                    checksum_sha256=checksum,
                    status="failed",
                    error=f"{type(exc).__name__}: {str(exc)[:160]}",
                )
            )

    return results


def _verify(
    provider: StorageProvider, key: str, checksum: str, size: int, workspace: Path | None
) -> PublishResult:
    target_dir = workspace or Path(tempfile.mkdtemp(prefix=VERIFY_DIR))
    target = target_dir / f"{slug(key)}.readback"
    try:
        back = provider.download(key, target)
    finally:
        target.unlink(missing_ok=True)

    matches = back.checksum_sha256 == checksum
    return PublishResult(
        provider=provider.config.provider,
        bucket=provider.config.bucket,
        key=key,
        bytes=size,
        checksum_sha256=checksum,
        status="verified" if matches else "failed",
        verified=matches,
        error=None if matches else "read-back checksum differs from the uploaded file",
    )


def publish_raw(
    path: Path,
    *,
    source_id: str,
    version: str,
    providers: Sequence[StorageProvider],
    verify: bool = True,
    workspace: Path | None = None,
) -> list[PublishResult]:
    """Keep the acquired raw file, under its own namespace, with the same checksum rules."""
    return publish_file(
        path,
        raw_key(source_id, version, path.name),
        providers,
        verify=verify,
        workspace=workspace,
    )


def summarise(results: Sequence[PublishResult]) -> dict[str, object]:
    """Overall verdict plus per-provider status, for the CLI answer and the job summary."""
    failed = [result for result in results if result.status == "failed"]
    per_provider: dict[str, list[str]] = {}
    for result in results:
        per_provider.setdefault(result.provider.value, []).append(result.status)

    return {
        "ok": not failed,
        "objects": len(results),
        "providers": per_provider,
        "failed": [f"{result.provider.value}:{result.key}" for result in failed],
    }
