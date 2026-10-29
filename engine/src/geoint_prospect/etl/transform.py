"""Polars transforms. Pure, lazy, and never invent values for missing data."""

from datetime import datetime

import polars as pl

from geoint_prospect.etl.contracts import DatasetMetadata

PROVENANCE_COLUMNS = ("dataset_id", "ingested_at")


def with_provenance(frame: pl.LazyFrame, meta: DatasetMetadata) -> pl.LazyFrame:
    """Attach provenance columns from ``meta``.

    ``ingested_at`` stays null when the metadata does not carry a timestamp.
    """
    return frame.with_columns(
        pl.lit(meta.dataset_id).alias("dataset_id"),
        pl.lit(meta.ingested_at).alias("ingested_at"),
    )


def filter_time(
    frame: pl.LazyFrame,
    column: str,
    start: datetime | None = None,
    end: datetime | None = None,
) -> pl.LazyFrame:
    """Keep rows within ``[start, end]`` on a timestamp column; both bounds are optional."""
    if column not in frame.collect_schema().names():
        raise ValueError(f"unknown time column: {column}")
    if start is not None:
        frame = frame.filter(pl.col(column) >= start)
    if end is not None:
        frame = frame.filter(pl.col(column) <= end)
    return frame
