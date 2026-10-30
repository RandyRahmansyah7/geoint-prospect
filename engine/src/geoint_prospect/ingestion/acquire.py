"""Acquisition orchestration: staging directory, manifest, and hand-off to the ETL stage.

The runner filesystem is temporary, so staging lives under ``$RUNNER_TEMP`` and is removed when the
pipeline finishes — including the failure path. Published results live outside staging.
"""

import hashlib
import json
import os
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

from geoint_prospect.etl.contracts import DatasetMetadata
from geoint_prospect.ingestion.connectors import AcquiredFile, connector_for
from geoint_prospect.ingestion.contracts import (
    IngestionManifest,
    IngestionPolicy,
    SourceDefinition,
)

STAGING_ROOT_NAME = "geoint-ingest"
MANIFEST_SUFFIX = ".manifest.json"


def sanitise_uri(uri: str) -> str:
    """Record a URI without credentials, query string, or fragment."""
    if "://" not in uri:
        return uri
    parsed = urlsplit(uri)
    port = f":{parsed.port}" if parsed.port else ""
    return f"{parsed.scheme}://{parsed.hostname or ''}{port}{parsed.path}"


def staging_dir(request_id: str, source_id: str, base: Path | None = None) -> Path:
    root = base or Path(os.environ.get("RUNNER_TEMP", tempfile.gettempdir())) / STAGING_ROOT_NAME
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", f"{request_id}-{source_id}")[:120]
    return root / safe


def idempotency_key(source: SourceDefinition, acquired: AcquiredFile) -> str:
    """Same source, same content, same rules → same key, so a retry cannot silently duplicate."""
    material = "|".join(
        (source.source_id, source.uri, acquired.checksum_sha256, source.format.value)
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def acquire(
    source: SourceDefinition,
    request_id: str,
    policy: IngestionPolicy | None = None,
    base: Path | None = None,
) -> tuple[AcquiredFile, Path]:
    """Fetch ``source`` into staging and return the staged file plus its directory."""
    policy = policy or IngestionPolicy()
    staging = staging_dir(request_id, source.source_id, base)
    target = staging / f"source.{source.format.value}"
    acquired = connector_for(source.connector).acquire(source, target, policy)
    return acquired, staging


def to_dataset_metadata(
    source: SourceDefinition,
    acquired: AcquiredFile,
    request_id: str,
    processing_version: str,
    extra_provenance: dict[str, str] | None = None,
) -> DatasetMetadata:
    """Map what we actually observed onto the ETL metadata contract."""
    provenance = {
        "request_id": request_id,
        "source_uri": sanitise_uri(source.uri),
        "checksum_sha256": acquired.checksum_sha256,
        "bytes": str(acquired.bytes),
    }
    if acquired.content_type:
        provenance["content_type"] = acquired.content_type
    if source.attribution:
        provenance["attribution"] = source.attribution
    provenance.update(extra_provenance or {})

    return DatasetMetadata(
        dataset_id=source.source_id,
        format=source.format,
        location=Path(acquired.path),
        ingested_at=datetime.now(UTC),
        row_count=None,  # unknown until the ETL stage has scanned the file
        licence=source.licence,
        processing_version=processing_version,
        provenance=provenance,
    )


def write_manifest(manifest: IngestionManifest, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def cleanup_staging(staging: Path) -> None:
    """Remove staged files; never touches ETL output, which lives outside staging."""
    if staging.exists():
        for child in sorted(staging.rglob("*"), reverse=True):
            if child.is_file():
                child.unlink(missing_ok=True)
            elif child.is_dir():
                child.rmdir()
        staging.rmdir()
