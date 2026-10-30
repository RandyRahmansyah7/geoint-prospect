"""Data acquisition: allowlisted sources, streaming connectors, manifests, and ETL hand-off."""

from geoint_prospect.ingestion.acquire import (
    MANIFEST_SUFFIX,
    acquire,
    cleanup_staging,
    idempotency_key,
    sanitise_uri,
    staging_dir,
    to_dataset_metadata,
    write_manifest,
)
from geoint_prospect.ingestion.connectors import (
    Connector,
    FileConnector,
    HttpConnector,
    IngestionError,
    connector_for,
    validate_staged_file,
)
from geoint_prospect.ingestion.contracts import (
    AcquiredFile,
    ConnectorKind,
    IngestionManifest,
    IngestionPolicy,
    SourceDefinition,
)
from geoint_prospect.ingestion.registry import UnknownSourceError, load_sources, resolve

__all__ = [
    "MANIFEST_SUFFIX",
    "AcquiredFile",
    "Connector",
    "ConnectorKind",
    "FileConnector",
    "HttpConnector",
    "IngestionError",
    "IngestionManifest",
    "IngestionPolicy",
    "SourceDefinition",
    "UnknownSourceError",
    "acquire",
    "cleanup_staging",
    "connector_for",
    "idempotency_key",
    "load_sources",
    "resolve",
    "sanitise_uri",
    "staging_dir",
    "to_dataset_metadata",
    "validate_staged_file",
    "write_manifest",
]
