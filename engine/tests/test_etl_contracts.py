from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from geoint_prospect.etl.contracts import DataFormat, DatasetMetadata


def test_minimal_metadata_leaves_unknown_values_unknown() -> None:
    meta = DatasetMetadata(dataset_id="obs", format="csv", location=Path("observations.csv"))

    assert meta.ingested_at is None
    assert meta.row_count is None
    assert meta.licence is None
    assert meta.processing_version is None
    assert meta.provenance == {}


def test_metadata_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        DatasetMetadata(dataset_id="obs", format="csv", location=Path("x.csv"), bogus="x")


def test_metadata_rejects_blank_identifier() -> None:
    with pytest.raises(ValidationError):
        DatasetMetadata(dataset_id="", format="csv", location=Path("x.csv"))


def test_metadata_round_trips() -> None:
    meta = DatasetMetadata(
        dataset_id="obs",
        format=DataFormat.parquet,
        location=Path("out/observations.parquet"),
        ingested_at=datetime(2026, 10, 29, 9, 0, tzinfo=UTC),
        licence="internal",
        processing_version="0.1.0",
        provenance={"origin": "fixture"},
    )

    assert DatasetMetadata(**meta.model_dump()) == meta
