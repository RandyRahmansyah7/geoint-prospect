"""Metadata contracts for tabular datasets.

shortcut: one model covers both source and dataset metadata; split out a SourceRef
model when remote connectors (HTTP/S3/B2) need their own fields.
"""

from datetime import datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class DataFormat(StrEnum):
    csv = "csv"
    parquet = "parquet"


class DatasetMetadata(BaseModel):
    """Where a dataset lives and where it came from.

    Unknown values stay unknown: leave a field out (or set it to None) rather than
    inventing a placeholder.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    dataset_id: str = Field(min_length=1)
    format: DataFormat
    location: Path
    ingested_at: datetime | None = None
    row_count: int | None = None
    provenance: dict[str, str] = Field(default_factory=dict)
