from datetime import datetime
from pathlib import Path

import polars as pl
import pytest

from geoint_prospect.etl.contracts import DataFormat, DatasetMetadata
from geoint_prospect.etl.ingest import read_dataset
from geoint_prospect.etl.pipeline import run_pipeline
from geoint_prospect.etl.transform import filter_time, with_provenance

FIXTURE = Path(__file__).parent / "fixtures" / "observations.csv"


def _meta(**overrides: object) -> DatasetMetadata:
    fields: dict[str, object] = {
        "dataset_id": "observations",
        "format": DataFormat.csv,
        "location": FIXTURE,
        "provenance": {"origin": "fixture"},
    }
    fields.update(overrides)
    return DatasetMetadata(**fields)


def test_pipeline_writes_readable_parquet(tmp_path: Path) -> None:
    destination = tmp_path / "nested" / "observations.parquet"

    result = run_pipeline(_meta(), destination)

    assert result.format is DataFormat.parquet
    assert result.location == destination
    assert result.row_count == 3
    assert result.provenance == {"origin": "fixture"}

    written = pl.read_parquet(destination)
    assert written.columns == [
        "object_id",
        "observed_at",
        "latitude",
        "longitude",
        "confidence",
        "note",
        "dataset_id",
        "ingested_at",
    ]
    assert written["dataset_id"].unique().to_list() == ["observations"]


def test_missing_values_stay_null(tmp_path: Path) -> None:
    destination = tmp_path / "observations.parquet"

    run_pipeline(_meta(), destination)
    written = pl.read_parquet(destination)

    # Row c456 has no timestamp and no coordinates: nulls must not be filled in.
    assert written["observed_at"].null_count() == 1
    assert written["latitude"].null_count() == 1
    assert written["confidence"].null_count() == 0


def test_provenance_timestamp_is_not_invented(tmp_path: Path) -> None:
    destination = tmp_path / "observations.parquet"

    run_pipeline(_meta(), destination)  # metadata carries no ingested_at

    assert pl.read_parquet(destination)["ingested_at"].null_count() == 3


def test_filter_time_keeps_only_the_requested_window() -> None:
    frame = with_provenance(read_dataset(_meta()), _meta())

    windowed = filter_time(frame, "observed_at", start=datetime(2023, 10, 1, 12, 2))

    assert windowed.collect()["object_id"].to_list() == ["b789"]


def test_filter_time_rejects_unknown_column() -> None:
    frame = read_dataset(_meta())

    with pytest.raises(ValueError, match="unknown time column"):
        filter_time(frame, "missing_column")


def test_missing_dataset_is_reported() -> None:
    with pytest.raises(FileNotFoundError, match="not found"):
        read_dataset(_meta(location=Path("does-not-exist.csv")))
