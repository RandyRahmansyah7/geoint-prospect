"""Optional Pandera validation layer.

Validation is opt-in per pipeline: ingest and transform do not import Pandera.
Install it with ``pip install -e ".[validate]"``.
"""

from typing import TYPE_CHECKING

import polars as pl

if TYPE_CHECKING:
    import pandera.polars as pa


def _pandera() -> object:
    try:
        import pandera.polars as pa
    except ImportError as exc:  # pragma: no cover - depends on installed extras
        raise RuntimeError('pandera is not installed; run: pip install -e ".[validate]"') from exc
    return pa


def validate_table(
    frame: pl.LazyFrame,
    schema: "pa.DataFrameSchema",
    *,
    checks: bool = False,
) -> pl.LazyFrame:
    """Validate a lazy frame against a Pandera schema.

    By default only the schema itself is checked (columns and dtypes) and everything stays
    lazy. Pass ``checks=True`` to also run row-level checks and nullability — Pandera then
    needs the data:

    shortcut: checks=True materialises the whole frame; switch to batched validation when a
    dataset no longer fits in memory.
    """
    pa = _pandera()
    if not isinstance(schema, pa.DataFrameSchema):
        raise TypeError("schema must be a pandera.polars.DataFrameSchema")
    if not checks:
        return schema.validate(frame)
    return schema.validate(frame.collect()).lazy()
