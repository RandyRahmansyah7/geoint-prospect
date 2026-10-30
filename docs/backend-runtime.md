# Backend runtime: GitHub Actions

GEOINT Prospect has no backend server. **GitHub Actions is the only backend runtime.** The desktop
app (Next.js + Tauri) collects parameters, asks the GitHub API to dispatch a workflow, and then reads
the run status back. The workstation never runs Python pipelines.

```
desktop app ──dispatch workflow──▶ GitHub Actions ──engine CLI──▶ result (Parquet)
     ▲                                   │
     └──────── poll run status ──────────┘
```

GitHub Actions is a **job-based** runtime, not an always-on API: requests queue, a run can take
minutes, and the app must show progress instead of waiting for a synchronous answer.

## Workflows

| Workflow | Trigger | Purpose |
| --- | --- | --- |
| `ci.yml` | push / pull request | Validation only: frontend lint/typecheck/build, engine ruff/pytest, Rust fmt/clippy. No storage credentials. |
| `backend.yml` | `workflow_dispatch` only | Production job path: runs one registered engine pipeline. |

`backend.yml` never runs on push or on a schedule. It starts only when the app (or you, explicitly)
dispatches it.

## Inputs

| Input | Rules |
| --- | --- |
| `pipeline` | Choice of registered pipelines (`healthcheck`, `tabular-normalize`, `ingest-tabular`) — see `python -m geoint_prospect pipelines list`. |
| `request_id` | App-generated id (UUID recommended). Names the run as `backend <request_id>` so the app can match it, and forms the concurrency group. |
| `input_path` | Repository-relative path for `tabular-normalize`; absolute paths and `..` are rejected. |
| `source_id` | Registered id from `configs/sources/` for `ingest-tabular`. Unknown ids are rejected by the engine with the list of registered ones. |
| `dry_run` | Default `true`: validates the request and the source definition without fetching, writing, or publishing. |

Arbitrary shell commands are impossible by design: pipeline names are looked up in a registry, and
values reach the process as quoted arguments, never as evaluated shell text.

## Ingestion stage

`ingest-tabular` adds acquisition in front of the same ETL:

```
source (configs/sources) ─▶ connector streams to $RUNNER_TEMP ─▶ format check + sha256
                                                                      │
                                          DatasetMetadata (licence, attribution, provenance)
                                                                      ▼
                                                        ETL scan → Parquet + <output>.manifest.json
```

- Only registered source ids are accepted; a workflow input can never carry a URL or a command.
- Connectors refuse plain http, hosts resolving to private/loopback/link-local/reserved addresses, and
  redirects that leave the source host. Downloads stream in 64 KB chunks with a 50 MB cap, a 30 s
  timeout, and up to 3 attempts with backoff.
- Stage statuses reported by the engine: `ingesting` → `ingested` → `etl_running` → `succeeded`/`failed`.
  The GitHub run itself is `queued`/`in_progress`/`completed` — the app shows both.
- Staging lives under `$RUNNER_TEMP` and is deleted by the engine on both the success and failure
  paths; the Parquet output and its manifest live outside staging.
- The manifest records source id, sanitised URI (no credentials or query string), connector, format,
  request id, checksum, size, content type, licence, attribution, idempotency key, and the ETL output
  path/row count. Unknown attributes stay `null`.

## Status and result flow

1. The app calls `POST /repos/{owner}/{repo}/actions/workflows/backend.yml/dispatches` with the inputs
   above (Tauri command `dispatch_backend_job`).
2. Actions names the run `backend <request_id>`.
3. The app polls `GET /repos/{owner}/{repo}/actions/runs?event=workflow_dispatch` and matches
   `display_title` against `backend <request_id>` (Tauri command `backend_job_status`).
4. States reported to the UI: `queued`, `in_progress`, `completed` plus the conclusion
   (`success`, `failure`, `cancelled`, `timed_out`). The app shows the run URL so the logs are one
   click away.

## Secrets and variables

Set as **repository secrets** (Settings → Secrets and variables → Actions):

| Secret | Purpose |
| --- | --- |
| `GEOINT_STORAGE_BUCKET` | Bucket for persistent results (Backblaze B2 / Filebase). |
| `GEOINT_STORAGE_ENDPOINT` | S3-compatible endpoint URL of that bucket. |
| `GEOINT_STORAGE_KEY_ID` | Access key id (minimum permission: write to that bucket only). |
| `GEOINT_STORAGE_SECRET` | Secret key. |

The publish step only runs for non-dry runs; when the secrets are absent it logs a warning and the
run stays "debug artifact only". Secrets are scoped to that single step and never printed.

## Credentials on the workstation

The desktop app needs a **fine-grained personal access token** for this repository:

- Actions: read and write (dispatch a workflow, read run status).
- Repository contents: read is enough — nothing else is needed.
- Stored in the operating system keychain (secret-service / Keychain / Credential Manager) through
  the Tauri command `set_github_token`. It is never written to the repository, the bundle,
  `localStorage`, or a config file, and it is never sent to the web UI.
- Rotate or revoke it in GitHub settings at any time; `clear_github_token` removes it from the keychain.

## Limits to expect

- Queueing: a run waits for a runner; expect seconds to minutes of latency.
- Run timeout: 15 minutes per job (see `timeout-minutes` in `backend.yml`).
- Runner filesystem is ephemeral. Persistent results belong in object storage; GitHub artifacts are
  debug-only and expire after 7 days.
- API rate limits apply to dispatch/poll calls; the app polls at a slow interval and stops when the
  run completes.
- Concurrency: one run per `request_id`; a duplicate dispatch queues.

## Smoke path

```bash
# validate the source definition and the request, no fetching
gh workflow run backend.yml -f pipeline=ingest-tabular -f request_id=dry-1 -f dry_run=true

# real acquisition + ETL from the fixture source
gh workflow run backend.yml -f pipeline=ingest-tabular -f request_id=run-1 -f dry_run=false
gh run list --workflow=backend.yml --limit 1
```

The job summary lists the stage statuses, and the debug artifact holds the Parquet output plus its
manifest for 7 days.

## Not implemented yet

- Production B2/Filebase connector inside the engine (the workflow uses `aws s3 cp` against the
  S3-compatible endpoint; it needs real credentials to be exercised). Uploading the manifest alongside
  the Parquet is part of that work.
- HTTP sources that need authentication or pagination; only a single-request download is supported.
- Only the `file` and `http` connectors exist; API connectors arrive when a real source needs one.
- Cancellation and retry buttons in the UI.
- Any pipeline beyond `healthcheck` and `tabular-normalize`.
- Surfacing job status inside the Gaia workspace (the panel currently lives on System Status).
