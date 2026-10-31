"""Publishing behaviour: verification, idempotency, and per-provider failure isolation."""

import json
from pathlib import Path

import pytest

from geoint_prospect.storage.contracts import ProviderConfig, ProviderKind
from geoint_prospect.storage.providers import FakeProvider, file_checksum
from geoint_prospect.storage.publish import publish_file, publish_raw, summarise


def _provider(provider: ProviderKind = ProviderKind.fake, bucket: str = "fake") -> FakeProvider:
    return FakeProvider(
        ProviderConfig(
            provider=provider,
            endpoint="memory://",
            bucket=bucket,
            key_id="fake",
            secret_key="fake",  # noqa: S106 - test-only
        )
    )


@pytest.fixture
def payload(tmp_path: Path) -> Path:
    path = tmp_path / "out.parquet"
    path.write_bytes(b"PAR1-payload")
    return path


def test_upload_is_verified_by_read_back(payload: Path) -> None:
    provider = _provider()

    results = publish_file(payload, "processed/x/req-1/out.parquet", [provider], workspace=None)

    assert len(results) == 1
    assert results[0].status == "verified"
    assert results[0].verified is True
    assert results[0].checksum_sha256 == file_checksum(payload)
    assert provider.objects["processed/x/req-1/out.parquet"] == payload.read_bytes()


def test_read_back_mismatch_fails_instead_of_claiming_success(payload: Path) -> None:
    provider = _provider()
    original_upload = provider.upload

    def upload_then_corrupt(source: Path, key: str, *, checksum_sha256: str):  # type: ignore[no-untyped-def]
        ref = original_upload(source, key, checksum_sha256=checksum_sha256)
        provider.tamper(key, b"corrupted")
        return ref

    provider.upload = upload_then_corrupt  # type: ignore[method-assign]

    results = publish_file(payload, "processed/x/req-1/out.parquet", [provider], workspace=None)

    assert results[0].status == "failed"
    assert results[0].verified is False
    assert "checksum differs" in (results[0].error or "")


def test_matching_object_is_not_rewritten(payload: Path) -> None:
    provider = _provider()
    key = "processed/x/req-1/out.parquet"
    publish_file(payload, key, [provider], workspace=None)

    results = publish_file(payload, key, [provider], workspace=None)

    assert results[0].status == "skipped"
    assert results[0].verified is True


def test_changed_object_is_written_again(payload: Path) -> None:
    provider = _provider()
    key = "processed/x/req-1/out.parquet"
    publish_file(payload, key, [provider], workspace=None)
    payload.write_bytes(b"PAR1-payload-v2")

    results = publish_file(payload, key, [provider], workspace=None)

    assert results[0].status == "verified"
    assert provider.objects[key] == b"PAR1-payload-v2"


def test_one_failing_provider_does_not_hide_behind_another(payload: Path) -> None:
    healthy = _provider(bucket="healthy")
    broken = _provider(bucket="broken")
    broken.fail_on_upload = True

    results = publish_file(
        payload, "processed/x/req-1/out.parquet", [healthy, broken], workspace=None
    )
    summary = summarise(results)

    assert [result.status for result in results] == ["verified", "failed"]
    assert summary["ok"] is False
    assert summary["failed"] == ["fake:processed/x/req-1/out.parquet"]
    assert summary["providers"] == {"fake": ["verified", "failed"]}


def test_raw_and_processed_namespaces_stay_separate(payload: Path) -> None:
    provider = _provider()

    raw = publish_raw(
        payload, source_id="obs", version="0.1.0", providers=[provider], workspace=None
    )

    assert raw[0].key.startswith("raw/obs/0.1.0/")
    assert list(provider.objects) == [raw[0].key]


def test_provider_error_message_stays_short(payload: Path, tmp_path: Path) -> None:
    provider = _provider()

    def explode(source: Path, key: str, *, checksum_sha256: str):  # type: ignore[no-untyped-def]
        raise RuntimeError("x" * 500)

    provider.upload = explode  # type: ignore[method-assign]

    results = publish_file(payload, "processed/x/req-1/out.parquet", [provider], workspace=None)

    assert results[0].status == "failed"
    assert len(results[0].error or "") <= 200


def test_manifest_storage_entries_carry_no_credentials(payload: Path) -> None:
    provider = _provider()
    results = publish_file(payload, "processed/x/req-1/out.parquet", [provider], workspace=None)

    serialised = json.dumps([result.model_dump() for result in results])

    assert "secret" not in serialised.lower()
    assert "fake" in serialised  # provider name is fine
