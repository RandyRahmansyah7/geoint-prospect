# GEOINT Prospect Engine

Python package for data ingest, transformation, and analysis. It has no dependency on the desktop
shell or the frontend.

## Runtime contract

**The engine runs in GitHub Actions, never on the workstation.** The desktop app only triggers
workflows and reads their status (see `docs/backend-runtime.md`). There is deliberately no API
server, worker, or localhost mode, and no local-run instructions here: the Actions runner is the
supported environment.

- Python 3.12, matching `.github/workflows/ci.yml` and the backend workflow.
- Code quality and tests are verified by the CI `Engine` job; a developer may run them locally for
  feedback, but the result that counts is the one from CI.
- Dependencies are declared in `pyproject.toml`. Polars, DuckDB, PyArrow, and Pydantic are always
  installed; **Pandera is optional** (`pip install -e ".[validate]"`) and only imported when a schema
  is validated.

## Command line

```
python -m geoint_prospect pipelines list [--json]
python -m geoint_prospect run --pipeline <name> --request-id <id> [--input PATH] [--output PATH]
                                [--dataset-id ID] [--dry-run] [--json]
```

Every answer is one envelope: `{"ok": bool, "data": ..., "error": ...}` with exit codes 0 (success),
2 (invalid request), 1 (unexpected). Only pipelines listed by `pipelines list` can be requested —
the name is looked up in a registry, so it can never become a shell command.

| Pipeline | Does |
| --- | --- |
| `healthcheck` | Reports Python and library versions of the runner. |
| `tabular-normalize` | Reads a CSV/Parquet file, adds provenance, writes Parquet. |

## Modules

## Modules

| Module | Responsibility |
| --- | --- |
| `geoint_prospect.cli` | The stable command line contract described above. |
| `geoint_prospect.pipelines` | Registry of requestable pipelines; unknown names are rejected before processing. |
| `geoint_prospect.etl.contracts` | Pydantic metadata contract (`DatasetMetadata`): identifier, format, location, ingest time, licence, processing version, provenance. Unknown values stay `None`. |
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

- `shortcut:` only CSV and Parquet are supported, and only files already present in the runner
  workspace (repo fixtures or files fetched by the workflow). Remote sources arrive with a connector
  issue (#14 keeps production connectors out of scope).
- `shortcut:` the workstation CPU (Intel Celeron N4020) has no AVX2, so current polars/duckdb wheels
  cannot run there. That is fine: the engine is not a supported local runtime. Guards in CI catch
  breakage.
- `shortcut:` metadata is one model for both source and dataset. Split it when remote connectors
  need their own fields.
- No type-checking (mypy) yet; ruff lint and format are the checks that run.
