# Storage layer

Four places can hold bytes. Only two of them are persistent, and the difference matters.

| Tier | Lifetime | Used for | Configured by |
| --- | --- | --- | --- |
| GitHub Actions runner workspace (`$RUNNER_TEMP`) | only for the running job | ingestion staging, ETL scratch, read-back checks | nothing — it is scratch space |
| GitHub Actions artifact | 7 days (`retention-days`) | debugging and hand-off of a run | automatic, never permanent storage |
| Backblaze B2 | persistent | `raw/`, `processed/`, `manifests/`, `tiles/` | secrets + `providers` input |
| Filebase | persistent | same namespaces, its own bucket | secrets + `providers` input |

B2 and Filebase are separate providers. Nothing is uploaded twice unless `providers` names both
(`b2,filebase`); each provider then gets its own status, and a failure on one is never hidden by a
success on the other.

## How publishing is requested

Publishing is explicit and off by default:

```bash
# dry run: validates the provider configuration (secrets present) without uploading
gh workflow run backend.yml -f pipeline=ingest-tabular -f request_id=dry-1 -f providers=b2 -f dry_run=true

# real run: acquire → ETL → publish Parquet + manifest
gh workflow run backend.yml -f pipeline=ingest-tabular -f request_id=run-1 -f providers=b2 -f dry_run=false

# also keep the acquired raw file, and publish to both providers
gh workflow run backend.yml -f pipeline=ingest-tabular -f request_id=run-2 \
  -f providers=b2,filebase -f store_raw=true -f dry_run=false
```

The workflow passes `--publish <providers>` to the engine CLI; the storage module does the upload, so
there is no provider-specific upload code in the workflow. An unknown provider name, a duplicate, or a
missing secret is rejected before any data is touched.

## Secrets

Repository secrets (Settings → Secrets and variables → Actions). Never commit them, never paste them
into an issue or chat; the app does not need them.

| Backblaze B2 | Filebase | Notes |
| --- | --- | --- |
| `B2_ENDPOINT` | `FILEBASE_ENDPOINT` | S3-compatible endpoint, e.g. `https://s3.us-west-004.backblazeb2.com` |
| `B2_BUCKET` | `FILEBASE_BUCKET` | bucket name (not a secret, but kept next to its keys) |
| `B2_REGION` | `FILEBASE_REGION` | optional |
| `B2_KEY_ID` | `FILEBASE_ACCESS_KEY` | application key id / access key |
| `B2_APPLICATION_KEY` | `FILEBASE_SECRET_KEY` | application key / secret key |

Give each key write access to its own bucket only. The engine reports missing variables by name,
never by value, and provider errors are trimmed before they reach a log or a manifest.

## Object layout

```
raw/<source_id>/<version>/<filename>
processed/<dataset_id>/<request_id>/<filename>
manifests/<request_id>.json
tiles/<region>/<version>.pmtiles
test/<request_id>/smoke.json          # smoke test only
```

Every component is validated: no separators, no `..`, no control characters. Values we did not choose
(file names) are sanitised; values we did choose (`source_id`, `request_id`) are rejected when unsafe.

## Publishing rules

1. SHA-256 is computed before upload and stored as object metadata (`sha256`).
2. After upload the object is downloaded again and the checksum re-computed. `status: verified` means
   the read-back matched; a mismatch is `failed`, never a success.
3. An object whose size and checksum already match is skipped (`status: skipped`), so retries cannot
   duplicate or overwrite data silently. Overwriting requires the checksum to differ.
4. Multi-provider runs report one result per provider per object; the request fails if any provider
   failed, and the manifest keeps the per-provider truth.
5. Nothing is deleted automatically: there is no retention policy yet, so old raw data and results stay
   until a policy is implemented and tested. Only `test/` smoke objects are removed after verification.
6. The manifest records provider, bucket, key, size, checksum, and status — never a credential. It also
   carries the ETL output key and row count, keeping source → request → output → object linked.

## Smoke test

`storage-smoke.yml` (manual) proves a provider really works end to end:

```bash
gh workflow run storage-smoke.yml -f providers=b2 -f request_id=smoke-1
```

It uploads a tiny JSON object to `test/<request_id>/smoke.json`, downloads it again, compares the
checksum, and deletes it. Use `keep=true` to leave it for inspection. B2 and Filebase must be smoke
tested **separately**; a provider that has not been tested is unverified, and this document says so
until the repository owner fills in the secrets and runs it.

## Errors you may hit

| Symptom | Meaning | What to do |
| --- | --- | --- |
| `missing configuration in Actions secrets: B2_ENDPOINT, …` | provider not configured | add the secrets, or leave `providers` empty |
| `unknown storage provider 'dropbox'` | typo or unsupported provider | use `b2`, `filebase`, or both separated by a comma |
| `status: failed` with a provider error | permission, bucket, endpoint, timeout, or network | read the trimmed message in the summary/artifact; retry the run |
| `read-back checksum differs` | upload corrupted or a proxy rewrote the object | treat as a real failure; re-run after checking the endpoint |
| `planned` in a manifest | dry run, or the manifest's own status (its verification is in the run summary) | nothing |

## Status today

- Implemented and covered by tests with a fake provider: key layout, provider selection, upload,
  read-back verification, idempotent skip, per-provider failure isolation, staging cleanup, smoke path.
- **Not yet verified with real credentials**: no B2 or Filebase upload/read-back has been executed, so
  neither provider may be described as production-ready. Run `storage-smoke.yml` for each provider and
  record the result in the issue before relying on it.
