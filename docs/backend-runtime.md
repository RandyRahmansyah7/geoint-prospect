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
| `pipeline` | Choice of registered pipelines (`healthcheck`, `tabular-normalize`) — see `python -m geoint_prospect pipelines list`. |
| `request_id` | App-generated id (UUID recommended). Names the run as `backend <request_id>` so the app can match it, and forms the concurrency group. |
| `input_path` | Repository-relative path; absolute paths and `..` are rejected. |
| `dry_run` | Default `true`: validates the request and the input, writes nothing, publishes nothing. |

Arbitrary shell commands are impossible by design: pipeline names are looked up in a registry, and
values reach the process as quoted arguments, never as evaluated shell text.

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

## Not implemented yet

- Production B2/Filebase connector inside the engine (the workflow uses `aws s3 cp` against the
  S3-compatible endpoint; it needs real credentials to be exercised).
- Cancellation and retry buttons in the UI.
- Any pipeline beyond `healthcheck` and `tabular-normalize`.
- Surfacing job status inside the Gaia workspace (the panel currently lives on System Status).
