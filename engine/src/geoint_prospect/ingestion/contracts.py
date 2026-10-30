"""Contracts for data acquisition: what a source is, how strictly it is fetched, what we record.

Acquisition never invents attributes the source does not provide: unknown values stay ``None``.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from geoint_prospect.etl.contracts import DataFormat


class ConnectorKind(StrEnum):
    file = "file"
    http = "http"


class SourceDefinition(BaseModel):
    """One allowlisted source. Only registered ids can be requested by a workflow."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str = Field(min_length=1)
    connector: ConnectorKind
    # file: repository-relative path. http: absolute https URL.
    uri: str = Field(min_length=1)
    format: DataFormat
    licence: str | None = None
    attribution: str | None = None
    description: str | None = None
    expected_content_types: tuple[str, ...] = ()
    enabled: bool = True


class IngestionPolicy(BaseModel):
    """Limits applied to every acquisition.

    ``allow_insecure_http`` exists for the test suite only (loopback test servers); the source
    registry never turns it on.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    timeout_seconds: float = Field(default=30.0, gt=0)
    max_attempts: int = Field(default=3, ge=1, le=5)
    backoff_seconds: float = Field(default=0.5, ge=0)
    max_bytes: int = Field(default=50 * 1024 * 1024, gt=0)
    allow_insecure_http: bool = False
    allowed_hosts: tuple[str, ...] = ()


class AcquiredFile(BaseModel):
    """The staged file plus what we measured while streaming it."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    bytes: int = Field(ge=0)
    checksum_sha256: str
    content_type: str | None = None


class IngestionManifest(BaseModel):
    """Record of one acquisition, linking source → request → staged file → ETL output."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str
    source_uri: str  # sanitised: no credentials, query string, or fragment
    connector: ConnectorKind
    format: DataFormat
    request_id: str
    status: str  # ingested | failed
    acquired_at: datetime | None = None
    source_updated_at: datetime | None = None
    checksum_sha256: str | None = None
    bytes: int | None = None
    content_type: str | None = None
    licence: str | None = None
    attribution: str | None = None
    idempotency_key: str | None = None
    etl_output: str | None = None
    etl_rows: int | None = None
    error: str | None = None
