"""The registered backend pipelines.

Only pipelines listed here can be requested by the desktop app or the backend workflow;
anything else is rejected before any processing happens.
"""

from dataclasses import dataclass, field
from pathlib import Path

import duckdb
import polars as pl
import pyarrow
import pydantic

from geoint_prospect import __version__
from geoint_prospect.etl.contracts import DataFormat, DatasetMetadata
from geoint_prospect.etl.pipeline import run_pipeline
from geoint_prospect.ingestion.acquire import (
    MANIFEST_SUFFIX,
    acquire,
    cleanup_staging,
    idempotency_key,
    sanitise_uri,
    to_dataset_metadata,
    write_manifest,
)
from geoint_prospect.ingestion.connectors import IngestionError
from geoint_prospect.ingestion.contracts import IngestionManifest, IngestionPolicy, SourceDefinition
from geoint_prospect.ingestion.registry import UnknownSourceError, resolve

FORMAT_BY_SUFFIX = {".csv": DataFormat.csv, ".parquet": DataFormat.parquet}


class PipelineError(Exception):
    """Invalid request; reported to the caller as a user error (exit code 2)."""


@dataclass(frozen=True)
class RunRequest:
    pipeline: str
    request_id: str
    input: Path | None = None
    output: Path | None = None
    dataset_id: str | None = None
    source_id: str | None = None
    dry_run: bool = False
    problems: list[str] = field(default_factory=list)


def _healthcheck(request: RunRequest) -> dict[str, object]:
    return {
        "request_id": request.request_id,
        "python_runtime": "actions",
        "engine_version": __version__,
        "polars": pl.__version__,
        "duckdb": duckdb.__version__,
        "pyarrow": pyarrow.__version__,
        "pydantic": pydantic.VERSION,
    }


def _tabular_normalize(request: RunRequest) -> dict[str, object]:
    if request.input is None or request.output is None:
        raise PipelineError("tabular-normalize needs --input and --output")

    suffix = request.input.suffix.lower()
    if suffix not in FORMAT_BY_SUFFIX:
        raise PipelineError(f"unsupported input format: {suffix or request.input.name}")

    meta = DatasetMetadata(
        dataset_id=request.dataset_id or request.input.stem,
        format=FORMAT_BY_SUFFIX[suffix],
        location=request.input,
        licence=None,
        processing_version=__version__,
        provenance={"request_id": request.request_id, "pipeline": request.pipeline},
    )

    result = run_pipeline(meta, request.output)
    return {
        "request_id": request.request_id,
        "dataset_id": result.dataset_id,
        "output": str(result.location),
        "rows": result.row_count,
        "processing_version": result.processing_version,
        "provenance": result.provenance,
    }


def _manifest_path(output: Path) -> Path:
    return output.with_name(output.name + MANIFEST_SUFFIX)


def _source_or_error(source_id: str | None) -> SourceDefinition:
    if not source_id:
        raise PipelineError("ingest-tabular needs --source-id")
    try:
        return resolve(source_id)
    except UnknownSourceError as exc:
        raise PipelineError(str(exc)) from exc


def _write_failure_manifest(
    path: Path, source: SourceDefinition, request: RunRequest, stage: str, reason: str
) -> None:
    """Best-effort record so a failed request is still traceable to its source."""
    manifest = IngestionManifest(
        source_id=source.source_id,
        source_uri=sanitise_uri(source.uri),
        connector=source.connector,
        format=source.format,
        request_id=request.request_id,
        status="failed",
        acquired_at=None,
        licence=source.licence,
        attribution=source.attribution,
        error=f"[{stage}] {reason}",
    )
    try:
        write_manifest(manifest, path)
    except OSError:
        pass  # never mask the original failure


def _ingest_tabular(request: RunRequest) -> dict[str, object]:
    """Acquisition → ETL in one run: the staged file is the ETL input, nothing is transformed twice."""
    source = _source_or_error(request.source_id)
    if request.output is None:
        raise PipelineError("ingest-tabular needs --output")
    manifest_path = _manifest_path(request.output)

    try:
        acquired, staging = acquire(source, request.request_id, IngestionPolicy())
    except IngestionError as exc:
        _write_failure_manifest(manifest_path, source, request, exc.stage, exc.reason)
        raise PipelineError(str(exc)) from exc

    try:
        key = idempotency_key(source, acquired)
        meta = to_dataset_metadata(
            source,
            acquired,
            request.request_id,
            __version__,
            {"pipeline": request.pipeline},
        )
        try:
            result = run_pipeline(meta, request.output)
        except Exception as exc:  # noqa: BLE001 - stage boundaries are what the caller needs
            _write_failure_manifest(manifest_path, source, request, "etl_running", str(exc))
            raise PipelineError(f"[etl_running] source '{source.source_id}': {exc}") from exc

        manifest = IngestionManifest(
            source_id=source.source_id,
            source_uri=sanitise_uri(source.uri),
            connector=source.connector,
            format=source.format,
            request_id=request.request_id,
            status="ingested",
            acquired_at=meta.ingested_at,
            checksum_sha256=acquired.checksum_sha256,
            bytes=acquired.bytes,
            content_type=acquired.content_type,
            licence=source.licence,
            attribution=source.attribution,
            idempotency_key=key,
            etl_output=str(result.location),
            etl_rows=result.row_count,
        )
        write_manifest(manifest, manifest_path)

        return {
            "request_id": request.request_id,
            "source_id": source.source_id,
            "stages": [
                {
                    "stage": "ingesting",
                    "status": "ingested",
                    "checksum_sha256": acquired.checksum_sha256,
                    "bytes": acquired.bytes,
                },
                {"stage": "etl_running", "status": "succeeded", "rows": result.row_count},
            ],
            "status": "succeeded",
            "output": str(result.location),
            "manifest": str(manifest_path),
            "idempotency_key": key,
            "rows": result.row_count,
        }
    finally:
        cleanup_staging(staging)


PIPELINES = {
    "healthcheck": _healthcheck,
    "tabular-normalize": _tabular_normalize,
    "ingest-tabular": _ingest_tabular,
}


def check_request(request: RunRequest) -> None:
    """Raise PipelineError if the request cannot run; used for --dry-run and before running."""
    if request.pipeline not in PIPELINES:
        known = ", ".join(sorted(PIPELINES))
        raise PipelineError(f"unknown pipeline '{request.pipeline}'; available: {known}")
    if not request.request_id.strip():
        raise PipelineError("request_id must not be empty")
    if request.pipeline == "healthcheck":
        return
    if request.pipeline == "ingest-tabular":
        # Dry runs validate the source definition without touching the network or staging.
        _source_or_error(request.source_id)
        if request.output is None:
            raise PipelineError("ingest-tabular needs --output")
        return
    if request.input is None or request.output is None:
        raise PipelineError("tabular-normalize needs --input and --output")
    if not request.input.is_file():
        raise PipelineError(f"input not found: {request.input}")
    if request.input.suffix.lower() not in FORMAT_BY_SUFFIX:
        raise PipelineError(
            f"unsupported input format: {request.input.suffix or request.input.name}"
        )
    # Dry runs must not touch the output path, so only creation is checked when writing.
    if not request.dry_run and not request.output.parent.is_dir():
        request.output.parent.mkdir(parents=True, exist_ok=True)


def execute(request: RunRequest) -> dict[str, object]:
    check_request(request)
    if request.dry_run:
        return {
            "request_id": request.request_id,
            "pipeline": request.pipeline,
            "dry_run": True,
            "validated": True,
            "input": str(request.input) if request.input else None,
            "output": str(request.output) if request.output else None,
        }
    return PIPELINES[request.pipeline](request)
