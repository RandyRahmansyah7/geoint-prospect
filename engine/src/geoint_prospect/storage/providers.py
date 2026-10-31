"""Providers: one S3-compatible adapter used for both Backblaze B2 and Filebase, plus a fake.

The S3 adapter is written once and configured per provider (endpoint, bucket, region, path-style),
so no provider-specific upload code exists. ``boto3`` is imported lazily: the fake path and the
dry-run validation work without it.
"""

import hashlib
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Protocol

from geoint_prospect.storage.contracts import ObjectRef, ProviderConfig, ProviderKind

CHUNK = 1024 * 1024

# Secret names per provider, as documented in docs/storage.md.
ENV_KEYS: dict[ProviderKind, dict[str, str]] = {
    ProviderKind.b2: {
        "endpoint": "B2_ENDPOINT",
        "bucket": "B2_BUCKET",
        "region": "B2_REGION",
        "key_id": "B2_KEY_ID",
        "secret": "B2_APPLICATION_KEY",
    },
    ProviderKind.filebase: {
        "endpoint": "FILEBASE_ENDPOINT",
        "bucket": "FILEBASE_BUCKET",
        "region": "FILEBASE_REGION",
        "key_id": "FILEBASE_ACCESS_KEY",
        "secret": "FILEBASE_SECRET_KEY",
    },
}


class StorageError(Exception):
    """Transport/permission/verification failure for one provider."""


class StorageProvider(Protocol):
    config: ProviderConfig

    def upload(self, source: Path, key: str, *, checksum_sha256: str) -> ObjectRef: ...

    def download(self, key: str, destination: Path) -> ObjectRef: ...

    def head(self, key: str) -> ObjectRef | None: ...

    def delete(self, key: str) -> None: ...


def file_checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def _import_boto3() -> object:
    try:
        import boto3  # noqa: PLC0415 - optional import, only needed for real providers

        return boto3
    except ImportError as exc:  # pragma: no cover - depends on the installed extras
        raise StorageError("boto3 is not installed; run: pip install -e .") from exc


class S3Provider:
    """S3-compatible adapter. One class, configured per provider."""

    def __init__(self, config: ProviderConfig) -> None:
        self.config = config
        boto3 = _import_boto3()
        self._client = boto3.client(  # type: ignore[attr-defined]
            "s3",
            endpoint_url=config.endpoint,
            region_name=config.region or "us-east-1",
            aws_access_key_id=config.key_id,
            aws_secret_access_key=config.secret_key.get_secret_value(),
            config=_client_config(boto3, config),
        )

    def upload(self, source: Path, key: str, *, checksum_sha256: str) -> ObjectRef:
        try:
            self._client.upload_file(  # type: ignore[attr-defined]
                str(source),
                self.config.bucket,
                key,
                ExtraArgs={"Metadata": {"sha256": checksum_sha256}},
            )
        except Exception as exc:  # noqa: BLE001 - provider errors are reported, not raised raw
            raise StorageError(_safe_error(exc)) from exc

        return ObjectRef(
            provider=self.config.provider,
            bucket=self.config.bucket,
            key=key,
            bytes=source.stat().st_size,
            checksum_sha256=checksum_sha256,
        )

    def download(self, key: str, destination: Path) -> ObjectRef:
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._client.download_file(self.config.bucket, key, str(destination))  # type: ignore[attr-defined]
        except Exception as exc:  # noqa: BLE001
            raise StorageError(_safe_error(exc)) from exc

        return ObjectRef(
            provider=self.config.provider,
            bucket=self.config.bucket,
            key=key,
            bytes=destination.stat().st_size,
            checksum_sha256=file_checksum(destination),
        )

    def head(self, key: str) -> ObjectRef | None:
        try:
            head = self._client.head_object(Bucket=self.config.bucket, Key=key)  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001 - missing object is a normal answer
            return None

        metadata: Mapping[str, str] = head.get("Metadata") or {}
        return ObjectRef(
            provider=self.config.provider,
            bucket=self.config.bucket,
            key=key,
            bytes=int(head.get("ContentLength", 0)),
            checksum_sha256=metadata.get("sha256", ""),
        )

    def delete(self, key: str) -> None:
        try:
            self._client.delete_object(Bucket=self.config.bucket, Key=key)  # type: ignore[attr-defined]
        except Exception as exc:  # noqa: BLE001
            raise StorageError(_safe_error(exc)) from exc


def _client_config(boto3: object, config: ProviderConfig) -> object:
    from botocore.config import Config  # noqa: PLC0415 - only needed for real providers

    addressing = "path" if config.path_style else "virtual"
    return Config(
        signature_version="s3v4",
        s3={"addressing_style": addressing},
        retries={"max_attempts": config.max_attempts, "mode": "standard"},
        connect_timeout=config.timeout_seconds,
        read_timeout=config.timeout_seconds,
    )


def _safe_error(exc: Exception) -> str:
    """Provider errors can echo request URLs; keep them short and credential-free."""
    text = str(exc).replace("\n", " ")[:300]
    for name in ("aws_access_key_id", "aws_secret_access_key", "Signature", "X-Amz-Credential"):
        text = text.replace(name, "«redacted»")
    return f"{type(exc).__name__}: {text}"


class FakeProvider:
    """In-memory provider for tests and dry-run validation. Never a production target."""

    def __init__(self, config: ProviderConfig) -> None:
        self.config = config
        self.objects: dict[str, bytes] = {}
        self.fail_on_upload: bool = False

    def upload(self, source: Path, key: str, *, checksum_sha256: str) -> ObjectRef:
        if self.fail_on_upload:
            raise StorageError("FakeProvider configured to fail")
        data = source.read_bytes()
        self.objects[key] = data
        return ObjectRef(
            provider=self.config.provider,
            bucket=self.config.bucket,
            key=key,
            bytes=len(data),
            checksum_sha256=checksum_sha256,
        )

    def download(self, key: str, destination: Path) -> ObjectRef:
        if key not in self.objects:
            raise StorageError(f"no such object: {key}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        data = self.objects[key]
        destination.write_bytes(data)
        return ObjectRef(
            provider=self.config.provider,
            bucket=self.config.bucket,
            key=key,
            bytes=len(data),
            checksum_sha256=hashlib.sha256(data).hexdigest(),
        )

    def head(self, key: str) -> ObjectRef | None:
        if key not in self.objects:
            return None
        data = self.objects[key]
        return ObjectRef(
            provider=self.config.provider,
            bucket=self.config.bucket,
            key=key,
            bytes=len(data),
            checksum_sha256=hashlib.sha256(data).hexdigest(),
        )

    def delete(self, key: str) -> None:
        self.objects.pop(key, None)

    def tamper(self, key: str, data: bytes) -> None:
        """Test helper: corrupt a stored object to exercise read-back verification."""
        self.objects[key] = data


def config_from_env(provider: ProviderKind, env: Mapping[str, str] | None = None) -> ProviderConfig:
    """Build a provider config from GitHub Actions secrets/variables.

    Raises StorageError naming the missing variable, never its value.
    """
    env = env if env is not None else os.environ
    names = ENV_KEYS[provider]
    missing = [
        names[field]
        for field in ("endpoint", "bucket", "key_id", "secret")
        if not env.get(names[field])
    ]
    if missing:
        raise StorageError(
            f"{provider.value}: missing configuration in Actions secrets: {', '.join(missing)}"
        )

    return ProviderConfig(
        provider=provider,
        endpoint=env[names["endpoint"]],
        bucket=env[names["bucket"]],
        region=env.get(names["region"]) or None,
        key_id=env[names["key_id"]],
        secret_key=env[names["secret"]],
    )


def parse_providers(spec: str) -> list[ProviderKind]:
    """Parse ``b2`` / ``filebase`` / ``b2,filebase`` (order kept, duplicates rejected)."""
    spec = (spec or "").strip()
    if not spec or spec.lower() in {"none", "off"}:
        return []

    kinds: list[ProviderKind] = []
    for raw in spec.split(","):
        name = raw.strip().lower()
        try:
            kind = ProviderKind(name)
        except ValueError:
            known = ", ".join(sorted(k.value for k in ProviderKind if k is not ProviderKind.fake))
            raise StorageError(
                f"unknown storage provider '{raw.strip()}'; known: {known}"
            ) from None
        if kind is ProviderKind.fake and os.environ.get("GEOINT_STORAGE_FAKE") != "1":
            raise StorageError("'fake' is a test-only provider; it is not accepted here")
        if kind in kinds:
            raise StorageError(f"provider '{kind.value}' listed twice")
        kinds.append(kind)
    return kinds


def build_provider(config: ProviderConfig) -> StorageProvider:
    if config.provider is ProviderKind.fake:
        return FakeProvider(config)
    return S3Provider(config)


def build_providers(spec: str, env: Mapping[str, str] | None = None) -> list[StorageProvider]:
    """Explicit provider selection: nothing is uploaded unless the caller asked for it."""
    providers: list[StorageProvider] = []
    for kind in parse_providers(spec):
        if kind is ProviderKind.fake:
            providers.append(
                FakeProvider(
                    ProviderConfig(
                        provider=kind,
                        endpoint="memory://",
                        bucket="fake",
                        key_id="fake",
                        secret_key="fake",  # noqa: S106 - test-only provider
                    )
                )
            )
            continue
        providers.append(build_provider(config_from_env(kind, env)))
    return providers
