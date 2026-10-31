"""CLI wiring for storage: explicit selection, dry-run validation, honest failures."""

import json
from pathlib import Path

import pytest

from geoint_prospect.cli import main
from geoint_prospect.ingestion.acquire import MANIFEST_SUFFIX, staging_dir
from geoint_prospect.storage.contracts import ProviderConfig, ProviderKind
from geoint_prospect.storage.providers import FakeProvider

REQUEST = "req-pub-1"


def _argv(tmp_path: Path, *extra: str) -> list[str]:
    return [
        "run",
        "--pipeline",
        "ingest-tabular",
        "--request-id",
        REQUEST,
        "--source-id",
        "fixtures-observations",
        "--output",
        str(tmp_path / "out" / "observations.parquet"),
        "--json",
        *extra,
    ]


def _payload(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    return json.loads(capsys.readouterr().out)


@pytest.fixture
def fake_storage(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEOINT_STORAGE_FAKE", "1")


def test_publishes_output_manifest_and_raw(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], fake_storage: None
) -> None:
    argv = _argv(tmp_path, "--publish", "fake", "--store-raw")

    assert main(argv) == 0
    data = _payload(capsys)["data"]

    assert data["storage"]["enabled"] is True
    assert data["storage"]["summary"]["ok"] is True
    keys = [entry["key"] for entry in data["storage"]["results"]]
    assert any(key.startswith(f"processed/fixtures-observations/{REQUEST}/") for key in keys)
    assert f"manifests/{REQUEST}.json" in keys
    assert any(key.startswith("raw/fixtures-observations/") for key in keys)
    assert all(entry["status"] in {"verified", "skipped"} for entry in data["storage"]["results"])

    output = Path(argv[argv.index("--output") + 1])
    manifest = json.loads(Path(str(output) + MANIFEST_SUFFIX).read_text(encoding="utf-8"))
    assert manifest["storage"], "manifest must record where the dataset was published"
    assert "secret" not in json.dumps(manifest["storage"]).lower()

    # Staging is still cleaned even though the raw file was published.
    assert not staging_dir(REQUEST, "fixtures-observations").exists()


def test_publishes_nothing_when_not_requested(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    argv = _argv(tmp_path)

    assert main(argv) == 0
    data = _payload(capsys)["data"]

    assert data["storage"]["enabled"] is False
    assert data["storage"]["results"] == []

    manifest = json.loads(
        Path(str(Path(argv[argv.index("--output") + 1])) + MANIFEST_SUFFIX).read_text(
            encoding="utf-8"
        )
    )
    assert manifest["storage"] == []


def test_unknown_provider_is_rejected_before_any_work(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], fake_storage: None
) -> None:
    argv = _argv(tmp_path, "--publish", "dropbox")

    assert main(argv) == 2
    assert "unknown storage provider" in _payload(capsys)["error"]["message"]


def test_missing_secrets_are_reported_with_the_variable_names(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("GEOINT_STORAGE_FAKE", raising=False)
    for name in ("B2_ENDPOINT", "B2_BUCKET", "B2_KEY_ID", "B2_APPLICATION_KEY"):
        monkeypatch.delenv(name, raising=False)

    assert main(_argv(tmp_path, "--publish", "b2")) == 2
    message = _payload(capsys)["error"]["message"]
    assert "B2_ENDPOINT" in message
    assert "B2_APPLICATION_KEY" in message


def test_dry_run_validates_providers_without_uploading(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], fake_storage: None
) -> None:
    argv = _argv(tmp_path, "--publish", "fake", "--dry-run")

    assert main(argv) == 0
    data = _payload(capsys)["data"]

    assert data["storage"]["providers"] == ["fake"]
    assert not Path(argv[argv.index("--output") + 1]).exists()


def test_publish_is_refused_by_pipelines_that_do_not_support_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], fake_storage: None
) -> None:
    code = main(
        [
            "run",
            "--pipeline",
            "healthcheck",
            "--request-id",
            "req-hc",
            "--publish",
            "fake",
            "--json",
        ]
    )

    assert code == 2
    assert "not supported" in _payload(capsys)["error"]["message"]


def test_storage_failure_fails_the_request(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    broken = FakeProvider(
        ProviderConfig(
            provider=ProviderKind.fake,
            endpoint="memory://",
            bucket="broken",
            key_id="fake",
            secret_key="fake",  # noqa: S106 - test-only
        )
    )
    broken.fail_on_upload = True
    monkeypatch.setattr("geoint_prospect.pipelines.build_providers", lambda spec: [broken])

    assert main(_argv(tmp_path, "--publish", "fake")) == 2
    payload = _payload(capsys)
    assert payload["ok"] is False
    assert "[storage] publish failed" in payload["error"]["message"]

    # The failure is recorded, not hidden: the manifest still exists with a failed entry.
    output = Path(_argv(tmp_path)[_argv(tmp_path).index("--output") + 1])
    manifest = json.loads(Path(str(output) + MANIFEST_SUFFIX).read_text(encoding="utf-8"))
    assert manifest["storage"][0]["status"] == "failed"
