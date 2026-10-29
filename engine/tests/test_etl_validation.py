from pathlib import Path

import polars as pl
import pytest

from geoint_prospect.etl.contracts import DataFormat, DatasetMetadata
from geoint_prospect.etl.ingest import read_dataset
from geoint_prospect.etl.pipeline import run_pipeline
from geoint_prospect.etl.validate import validate_table

FIXTURE = Path(__file__).parent / "fixtures" / "observations.csv"

pa_polars = pytest.importorskip("pandera.polars", reason="pandera is an optional extra")


def _schema() -> object:
    return pa_polars.DataFrameSchema(
        {
            "object_id": pa_polars.Column(str, nullable=False),
            "confidence": pa_polars.Column(float, checks=pa_polars.Check.between(0, 1)),
            "latitude": pa_polars.Column(float, nullable=True),
        }
    )


def test_schema_accepts_the_fixture() -> None:
    frame = read_dataset(DatasetMetadata(dataset_id="obs", format=DataFormat.csv, location=FIXTURE))

    assert validate_table(frame, _schema()).collect().height == 3


def test_structure_is_checked_without_loading_data() -> None:
    missing_column = pl.LazyFrame(
        {"object_id": ["x"], "confidence": [0.5]},
        schema={"object_id": pl.String, "confidence": pl.Float64},
    )

    with pytest.raises(Exception):  # noqa: B017 - pandera error types differ across versions
        validate_table(missing_column, _schema())


def test_schema_rejects_invalid_values() -> None:
    bad = pl.LazyFrame(
        {"object_id": ["x"], "confidence": [1.7], "latitude": [1.0]},
        schema={"object_id": pl.String, "confidence": pl.Float64, "latitude": pl.Float64},
    )

    with pytest.raises(Exception):  # noqa: B017 - pandera error types differ across versions
        validate_table(bad, _schema(), checks=True)


def test_schema_rejects_null_in_required_column() -> None:
    bad = pl.LazyFrame(
        {"object_id": [None], "confidence": [0.5], "latitude": [1.0]},
        schema={"object_id": pl.String, "confidence": pl.Float64, "latitude": pl.Float64},
    )

    with pytest.raises(Exception):  # noqa: B017 - pandera error types differ across versions
        validate_table(bad, _schema(), checks=True)


def test_pipeline_validates_before_writing(tmp_path: Path) -> None:
    destination = tmp_path / "observations.parquet"

    result = run_pipeline(
        DatasetMetadata(
            dataset_id="obs",
            format=DataFormat.csv,
            location=FIXTURE,
            provenance={"origin": "fixture"},
        ),
        destination,
        schema=_schema(),
    )

    assert result.row_count == 3


def test_wrong_schema_type_is_rejected() -> None:
    frame = pl.LazyFrame({"object_id": ["x"]})

    with pytest.raises(TypeError, match="pandera.polars.DataFrameSchema"):
        validate_table(frame, object())  # type: ignore[arg-type]
