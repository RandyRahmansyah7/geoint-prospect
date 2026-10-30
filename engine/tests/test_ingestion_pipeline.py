"""End-to-end: ingestion → ETL in one run, with a real manifest and readable Parquet."""

import json
from pathlib import Path

import polars as pl
import pytest

from geoint_prospect.cli import main
from geoint_prospect.ingestion.acquire import MANIFEST_SUFFIX, staging_dir


def _run(tmp_path: Path, *extra: str) -> tuple[Path, list[str]]:
    output = tmp_path / "out" / "observations.parquet"
    argv = [
        "run",
        "--pipeline",
        "ingest-tabular",
        "--request-id",
        "req-ingest-1",
        "--source-id",
        "fixtures-observations",
        "--output",
        str(output),
        "--json",
        *extra,
    ]
    return output, argv


def test_ingestion_feeds_etl_and_writes_a_readable_result(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output, argv = _run(tmp_path)

    assert main(argv) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["ok"] is True
    data = payload["data"]
    assert data["status"] == "succeeded"
    assert data["rows"] == 3
    assert [stage["stage"] for stage in data["stages"]] == ["ingesting", "etl_running"]
    assert data["stages"][0]["status"] == "ingested"
    assert data["stages"][1]["status"] == "succeeded"

    written = pl.read_parquet(output)
    assert written.height == 3
    # Provenance from the acquisition stage survives into the ETL output.
    assert written["dataset_id"].unique().to_list() == ["fixtures-observations"]
    assert written["observed_at"].null_count() == 1  # unknown stays unknown


def test_manifest_links_source_request_and_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output, argv = _run(tmp_path)

    assert main(argv) == 0
    capsys.readouterr()

    manifest = json.loads(Path(str(output) + MANIFEST_SUFFIX).read_text(encoding="utf-8"))
    assert manifest["source_id"] == "fixtures-observations"
    assert manifest["source_uri"] == "engine/tests/fixtures/observations.csv"
    assert manifest["request_id"] == "req-ingest-1"
    assert manifest["status"] == "ingested"
    assert manifest["etl_output"] == str(output)
    assert manifest["etl_rows"] == 3
    assert manifest["licence"] == "internal-fixture"
    assert len(manifest["checksum_sha256"]) == 64
    assert len(manifest["idempotency_key"]) == 64
    assert manifest["error"] is None
    # Nothing that was not provided is invented.
    assert manifest["source_updated_at"] is None


def test_same_content_produces_the_same_idempotency_key(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _, argv = _run(tmp_path)
    assert main(argv) == 0
    first = json.loads(capsys.readouterr().out)["data"]["idempotency_key"]

    _, argv_again = _run(tmp_path)
    assert main(argv_again) == 0
    second = json.loads(capsys.readouterr().out)["data"]["idempotency_key"]

    assert first == second


def test_staging_is_cleaned_up(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _, argv = _run(tmp_path)

    assert main(argv) == 0
    capsys.readouterr()

    assert not staging_dir("req-ingest-1", "fixtures-observations").exists()


def test_dry_run_validates_the_source_without_fetching(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output, argv = _run(tmp_path, "--dry-run")

    assert main(argv) == 0
    data = json.loads(capsys.readouterr().out)["data"]

    assert data["dry_run"] is True
    assert not output.exists()
    assert not Path(str(output) + MANIFEST_SUFFIX).exists()


def test_unknown_source_is_rejected_with_the_registered_ids(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output = tmp_path / "out.parquet"
    code = main(
        [
            "run",
            "--pipeline",
            "ingest-tabular",
            "--request-id",
            "req-ingest-2",
            "--source-id",
            "arbitrary-url",
            "--output",
            str(output),
            "--json",
        ]
    )

    assert code == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"]["code"] == "invalid_request"
    assert "registered: fixtures-observations" in payload["error"]["message"]
    assert not output.exists()


def test_failed_ingestion_stops_the_etl_and_records_the_stage(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    broken = tmp_path / "broken.toml"
    broken.write_text(
        "\n".join(
            [
                'source_id = "broken"',
                'connector = "file"',
                'uri = "does/not/exist.csv"',
                'format = "csv"',
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("GEOINT_SOURCES_DIR", str(tmp_path))

    output = tmp_path / "out" / "never.parquet"
    code = main(
        [
            "run",
            "--pipeline",
            "ingest-tabular",
            "--request-id",
            "req-ingest-3",
            "--source-id",
            "broken",
            "--output",
            str(output),
            "--json",
        ]
    )

    assert code == 2
    payload = json.loads(capsys.readouterr().out)
    assert "[ingesting] source 'broken'" in payload["error"]["message"]

    # ETL never ran and the failure is traceable through the manifest.
    assert not output.exists()
    manifest = json.loads(Path(str(output) + MANIFEST_SUFFIX).read_text(encoding="utf-8"))
    assert manifest["status"] == "failed"
    assert manifest["error"].startswith("[ingesting]")
