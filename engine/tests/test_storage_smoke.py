"""Smoke test path: proves upload + read-back, and cleans up after itself."""

import json
from pathlib import Path

import pytest

from geoint_prospect.cli import main
from geoint_prospect.storage.contracts import ProviderConfig, ProviderKind
from geoint_prospect.storage.providers import FakeProvider
from geoint_prospect.storage.smoke import smoke_key, smoke_test


def _provider(bucket: str = "fake") -> FakeProvider:
    return FakeProvider(
        ProviderConfig(
            provider=ProviderKind.fake,
            endpoint="memory://",
            bucket=bucket,
            key_id="fake",
            secret_key="fake",  # noqa: S106 - test-only
        )
    )


def test_smoke_verifies_then_removes_the_test_object() -> None:
    provider = _provider()

    results = smoke_test([provider], "smoke-1")

    assert results[0].status == "verified"
    assert results[0].verified is True
    assert provider.objects == {}, "smoke object must not be left behind"


def test_smoke_can_keep_the_object_for_inspection() -> None:
    provider = _provider()

    smoke_test([provider], "smoke-2", keep=True)

    assert list(provider.objects) == [smoke_key("smoke-2")]
    payload = json.loads(provider.objects[smoke_key("smoke-2")])
    assert payload["kind"] == "storage-smoke"
    assert payload["request_id"] == "smoke-2"


def test_smoke_uses_the_test_namespace_only() -> None:
    provider = _provider()

    smoke_test([provider], "smoke-3", keep=True)

    assert all(key.startswith("test/") for key in provider.objects)


def test_smoke_reports_failure_without_hiding_it() -> None:
    broken = _provider()
    broken.fail_on_upload = True

    results = smoke_test([broken], "smoke-4")

    assert results[0].status == "failed"
    assert broken.objects == {}


def test_cli_smoke_dry_run_validates_configuration(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GEOINT_STORAGE_FAKE", "1")

    assert (
        main(
            ["storage", "smoke", "--providers", "fake", "--request-id", "s1", "--dry-run", "--json"]
        )
        == 0
    )

    data = json.loads(capsys.readouterr().out)["data"]
    assert data["dry_run"] is True
    assert data["providers"] == ["fake"]
    assert data["key"] == "test/s1/smoke.json"


def test_cli_smoke_fails_when_secrets_are_missing(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    for name in ("B2_ENDPOINT", "B2_BUCKET", "B2_KEY_ID", "B2_APPLICATION_KEY"):
        monkeypatch.delenv(name, raising=False)

    assert main(["storage", "smoke", "--providers", "b2", "--request-id", "s2", "--json"]) == 2
    assert "B2_ENDPOINT" in json.loads(capsys.readouterr().out)["error"]["message"]


def test_cli_smoke_rejects_unsafe_request_ids(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GEOINT_STORAGE_FAKE", "1")

    assert (
        main(["storage", "smoke", "--providers", "fake", "--request-id", "../etc", "--json"]) == 2
    )
    assert "unsafe request_id" in json.loads(capsys.readouterr().out)["error"]["message"]


def test_smoke_object_path_is_built_from_a_safe_component(tmp_path: Path) -> None:
    provider = _provider()

    smoke_test([provider], "safe-id_1.2", keep=True, workspace=tmp_path)

    assert list(provider.objects) == ["test/safe-id_1.2/smoke.json"]
