# Source registry

One TOML file per source, top-level keys only. The ingestion stage loads every `*.toml` in this
directory and validates it against `geoint_prospect.ingestion.SourceDefinition`; unknown keys are a
hard error. Workflows may only request a `source_id` that is registered here — never a URL or a
command.

| Key | Required | Notes |
| --- | --- | --- |
| `source_id` | yes | Must be unique across files. |
| `connector` | yes | `file` (repository-relative path) or `http` (public HTTPS). |
| `uri` | yes | Path for `file`, absolute `https://` URL for `http`. |
| `format` | yes | `csv` or `parquet`. |
| `licence` | no | Kept as-is; unknown stays empty. |
| `attribution` | no | Carried into the manifest and the ETL provenance. |
| `description` | no | Human note. |
| `expected_content_types` | no | Content types accepted from an HTTP source. |
| `enabled` | no | Defaults to `true`; set `false` to keep a definition without admitting it. |

Rules enforced by the connector, not by reviewers:

- HTTPS only (plain `http` is refused unless a test policy allows loopback).
- Hosts resolving to private, loopback, link-local, reserved, or multicast addresses are refused.
- Redirects must stay on HTTPS and inside the source host (plus `allowed_hosts` when a policy sets it).
- Downloads stream in 64 KB chunks and abort past the size cap (50 MB default); nothing is buffered whole.
- Checksums are computed while streaming; empty files are rejected.
- CSV must have a comma-separated header, Parquet must start with the `PAR1` magic.

Add a source by copying `fixtures-observations.toml` and editing it; then run the smoke path in
`docs/backend-runtime.md` before pointing a real workflow at it.
