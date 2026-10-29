from pathlib import Path

import pyarrow as pa

from geoint_prospect.etl.contracts import DataFormat, DatasetMetadata
from geoint_prospect.etl.pipeline import run_pipeline
from geoint_prospect.etl.query import run_sql

FIXTURE = Path(__file__).parent / "fixtures" / "observations.csv"


def _to_parquet(tmp_path: Path) -> Path:
    destination = tmp_path / "observations.parquet"
    run_pipeline(
        DatasetMetadata(
            dataset_id="observations",
            format=DataFormat.csv,
            location=FIXTURE,
            provenance={"origin": "fixture"},
        ),
        destination,
    )
    return destination


def test_duckdb_aggregates_parquet(tmp_path: Path) -> None:
    table = run_sql(
        "SELECT count(*) AS n, avg(confidence) AS avg_confidence FROM read_parquet($path)",
        {"path": str(_to_parquet(tmp_path))},
    )

    assert isinstance(table, pa.Table)
    assert table.column("n").to_pylist() == [3]
    assert round(table.column("avg_confidence").to_pylist()[0], 3) == round(
        (0.82 + 0.66 + 0.51) / 3, 3
    )


def test_duckdb_reads_csv_directly() -> None:
    table = run_sql(
        "SELECT object_id FROM read_csv_auto($path, header = true) WHERE latitude IS NULL",
        {"path": str(FIXTURE)},
    )

    assert table.column("object_id").to_pylist() == ["c456"]
