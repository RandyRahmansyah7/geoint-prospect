"""Read tabular files into a Polars LazyFrame (nothing is materialised yet)."""

from pathlib import Path

import polars as pl

from geoint_prospect.etl.contracts import DataFormat, DatasetMetadata


def read_dataset(meta: DatasetMetadata) -> pl.LazyFrame:
    """Scan the dataset described by ``meta``. Raises FileNotFoundError if it is missing."""
    path = Path(meta.location)
    if not path.is_file():
        raise FileNotFoundError(f"dataset '{meta.dataset_id}' not found at {path}")

    match meta.format:
        case DataFormat.csv:
            return pl.scan_csv(path, infer_schema_length=1000, try_parse_dates=True)
        case DataFormat.parquet:
            return pl.scan_parquet(path)
        case _:  # pragma: no cover - DataFormat is closed, guards future additions
            raise ValueError(f"unsupported format: {meta.format}")
