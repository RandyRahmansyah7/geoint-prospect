"""Upload → read-back → delete smoke test against real providers.

Run from the manual ``storage-smoke`` workflow once the repository owner has filled in the provider
secrets. It writes a tiny object under ``test/<request_id>/`` and removes it again, so a smoke run
never touches the ``raw/``, ``processed/``, ``manifests/``, or ``tiles/`` namespaces.
"""

import json
import tempfile
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from geoint_prospect.storage.contracts import PublishResult
from geoint_prospect.storage.keys import safe_component
from geoint_prospect.storage.providers import StorageProvider
from geoint_prospect.storage.publish import publish_file

SMOKE_PREFIX = "test"
SMOKE_NAME = "smoke.json"


def smoke_key(request_id: str) -> str:
    return f"{SMOKE_PREFIX}/{safe_component(request_id, field='request_id')}/{SMOKE_NAME}"


def smoke_test(
    providers: Sequence[StorageProvider],
    request_id: str,
    *,
    keep: bool = False,
    workspace: Path | None = None,
) -> list[PublishResult]:
    """Publish a tiny object, verify the read-back checksum, then clean it up."""
    payload = json.dumps(
        {
            "kind": "storage-smoke",
            "request_id": request_id,
            "generated_at": datetime.now(UTC).isoformat(),
        },
        sort_keys=True,
    ).encode("utf-8")

    directory = workspace or Path(tempfile.mkdtemp(prefix="geoint-smoke"))
    directory.mkdir(parents=True, exist_ok=True)
    local = directory / SMOKE_NAME
    local.write_bytes(payload)

    key = smoke_key(request_id)
    results = publish_file(local, key, providers, workspace=directory)

    if not keep:
        for provider, result in zip(providers, results, strict=True):
            if result.verified:
                provider.delete(key)

    local.unlink(missing_ok=True)
    return results
