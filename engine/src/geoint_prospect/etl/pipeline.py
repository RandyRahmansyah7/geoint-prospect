"""Smallest useful vertical slice: ingest → provenance → optional validation → Parquet."""

from pathlib import Path
from typing import TYPE_CHECKING

import polars as pl

from geoint_prospect.etl.contracts import DataFormat, DatasetMetadata
from geoint_prospect.etl.ingest import read_dataset
from geoint_prospect.etl.transform import with_provenance
from geoint_prospect.etl.validate import validate_table

if TYPE_CHECKING:
    import pandera.polars as pa


def run_pipeline(
    meta: DatasetMetadata,
    destination: Path,
    *,
    schema: "pa.DataFrameSchema | None" = None,
) -> DatasetMetadata:
    """Write ``meta``'s dataset to Parquet and return metadata describing the result."""
    frame = with_provenance(read_dataset(meta), meta)
    if schema is not None:
        frame = validate_table(frame, schema)

    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    frame.sink_parquet(destination)

    row_count = pl.scan_parquet(destination).select(pl.len()).collect().item()
    return meta.model_copy(
        update={
            "format": DataFormat.parquet,
            "location": destination,
            "row_count": row_count,
        }
    )
