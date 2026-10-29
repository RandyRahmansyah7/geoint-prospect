import json
from pathlib import Path

import polars as pl
import pytest

from geoint_prospect import __version__
from geoint_prospect.cli import main
from geoint_prospect.pipelines import PIPELINES

FIXTURE = Path(__file__).parent / "fixtures" / "observations.csv"


def _envelope(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    return json.loads(capsys.readouterr().out)


def test_pipelines_list_reports_only_implemented_pipelines(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["pipelines", "list", "--json"]) == 0

    payload = _envelope(capsys)
    assert payload["ok"] is True
    names = [entry["name"] for entry in payload["data"]["pipelines"]]  # type: ignore[index]
    assert names == sorted(PIPELINES)


def test_healthcheck_reports_runtime_versions(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["run", "--pipeline", "healthcheck", "--request-id", "req-1", "--json"]) == 0

    data = _envelope(capsys)["data"]
    assert data["request_id"] == "req-1"  # type: ignore[index]
    assert data["engine_version"] == __version__  # type: ignore[index]
    assert data["python_runtime"] == "actions"  # type: ignore[index]


def test_dry_run_validates_without_writing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output = tmp_path / "never-written.parquet"

    code = main(
        [
            "run",
            "--pipeline",
            "tabular-normalize",
            "--request-id",
            "req-2",
            "--input",
            str(FIXTURE),
            "--output",
            str(output),
            "--dry-run",
            "--json",
        ]
    )

    assert code == 0
    assert _envelope(capsys)["data"]["dry_run"] is True  # type: ignore[index]
    assert not output.exists()


def test_run_writes_parquet_with_provenance(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output = tmp_path / "observations.parquet"

    code = main(
        [
            "run",
            "--pipeline",
            "tabular-normalize",
            "--request-id",
            "req-3",
            "--input",
            str(FIXTURE),
            "--output",
            str(output),
            "--dataset-id",
            "observations",
            "--json",
        ]
    )

    assert code == 0
    payload = _envelope(capsys)
    assert payload["data"]["rows"] == 3  # type: ignore[index]
    written = pl.read_parquet(output)
    assert written["dataset_id"].unique().to_list() == ["observations"]
    assert written["ingested_at"].null_count() == 3  # no invented timestamps


def test_unknown_pipeline_is_rejected(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["run", "--pipeline", "rm -rf /", "--request-id", "req-4", "--json"])

    assert code == 2
    payload = _envelope(capsys)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "invalid_request"  # type: ignore[index]


def test_missing_input_is_rejected(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = main(
        [
            "run",
            "--pipeline",
            "tabular-normalize",
            "--request-id",
            "req-5",
            "--input",
            str(tmp_path / "absent.csv"),
            "--output",
            str(tmp_path / "out.parquet"),
            "--json",
        ]
    )

    assert code == 2
    assert "input not found" in _envelope(capsys)["error"]["message"]  # type: ignore[index]


def test_unsupported_format_is_rejected(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    weird = tmp_path / "notes.txt"
    weird.write_text("hello")

    code = main(
        [
            "run",
            "--pipeline",
            "tabular-normalize",
            "--request-id",
            "req-6",
            "--input",
            str(weird),
            "--output",
            str(tmp_path / "out.parquet"),
            "--json",
        ]
    )

    assert code == 2
    assert "unsupported input format" in _envelope(capsys)["error"]["message"]  # type: ignore[index]


def test_human_output_is_plain_data(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["pipelines", "list"]) == 0

    names = [entry["name"] for entry in _envelope(capsys)["pipelines"]]
    assert "healthcheck" in names
