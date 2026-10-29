"""Analytical SQL through DuckDB, so large files are never converted to Python objects."""

from collections.abc import Mapping

import duckdb
import pyarrow as pa


def run_sql(query: str, params: Mapping[str, object] | None = None) -> pa.Table:
    """Execute ``query`` and return an Arrow table.

    Reference files as parameters instead of pasting paths into SQL:

        run_sql("SELECT count(*) FROM read_parquet($path)", {"path": str(path)})
    """
    connection = duckdb.connect()
    try:
        # shortcut: the full result is materialised as one Arrow table. Use
        # fetch_record_batch() when a result no longer fits in memory.
        return connection.execute(query, dict(params or {})).to_arrow_table()
    finally:
        connection.close()
