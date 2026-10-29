# GEOINT Prospect Engine

Python package for data ingest, transformation, and analysis. It has no dependency on the desktop
shell or the frontend.

## Install and check

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"     # adds pytest, ruff, and pandera
pytest
ruff check .
ruff format --check .
```

Dependencies are declared in `pyproject.toml`. Polars, DuckDB, PyArrow, and Pydantic are always
installed; **Pandera is optional** (`pip install -e ".[validate]"`) and only imported when a schema
is validated.

## Modules

| Module | Responsibility |
| --- | --- |
| `geoint_prospect.etl.contracts` | Pydantic metadata contract (`DatasetMetadata`): identifier, format, location, ingest time, provenance. Unknown values stay `None`. |
| `geoint_prospect.etl.ingest` | Scans CSV/Parquet into a **Polars `LazyFrame`** — no eager load, no full copy. |
| `geoint_prospect.etl.transform` | Lazy Polars transforms: provenance columns, time-window filtering. Never fills missing values. |
| `geoint_prospect.etl.query` | Analytical SQL through DuckDB over CSV/Parquet, returning an Arrow table. |
| `geoint_prospect.etl.validate` | Opt-in Pandera validation. `validate_table` checks schema/dtypes lazily; `checks=True` also runs row-level checks and nullability (materialises the frame). |
| `geoint_prospect.etl.pipeline` | The vertical slice: ingest → provenance → optional validation → Parquet out. |

## Data flow and boundaries

```
CSV/Parquet ──scan──▶ Polars LazyFrame ──transform──▶ sink_parquet ─▶ Parquet
                             │
                             └──▶ DuckDB SQL (read_csv_auto/read_parquet) ──▶ Arrow table
```

- Polars handles row-wise transformation; DuckDB handles aggregation/filtering in SQL.
- Arrow is the exchange format between components; Parquet is the on-disk format for derived data.
- Nothing converts a whole dataset into Python objects: `run_sql` returns an Arrow table and
  ingestion stays lazy until a sink or `collect()`.
- Provenance is attached, never invented: if `DatasetMetadata.ingested_at` is unknown, the column
  stays null; missing cells are not filled.

## Known limits

- `shortcut:` polars and DuckDB are pinned below the AVX2 boundary (`polars-lts-cpu`, `duckdb<2`)
  because the development machine (Intel Celeron N4020) traps with SIGILL on the newer wheels. Import
  names and APIs are identical — raise the pins when the hardware changes. CI runners (AVX2) run
  either build.
- `shortcut:` only CSV and Parquet are supported, and only local files. Add remote sources and more
  formats when a connector issue needs them.
- `shortcut:` metadata is one model for both source and dataset. Split it when remote connectors
  need their own fields.
- No type-checking (mypy) yet; ruff lint and format are the checks that run.
