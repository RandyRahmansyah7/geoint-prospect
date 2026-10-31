"""Provider configuration and selection, with no credentials and no network."""

from pathlib import Path

import pytest

from geoint_prospect.storage.contracts import ProviderConfig, ProviderKind
from geoint_prospect.storage.providers import (
    ENV_KEYS,
    FakeProvider,
    StorageError,
    build_providers,
    config_from_env,
    file_checksum,
    parse_providers,
)


def test_parse_providers_keeps_order_and_rejects_junk() -> None:
    assert parse_providers("") == []
    assert parse_providers("none") == []
    assert parse_providers("b2") == [ProviderKind.b2]
    assert parse_providers("b2,filebase") == [ProviderKind.b2, ProviderKind.filebase]

    with pytest.raises(StorageError, match="unknown storage provider"):
        parse_providers("dropbox")
    with pytest.raises(StorageError, match="listed twice"):
        parse_providers("b2,b2")
    with pytest.raises(StorageError, match="test-only"):
        parse_providers("fake")


def test_missing_secrets_name_the_variable_not_a_value() -> None:
    with pytest.raises(StorageError) as excinfo:
        config_from_env(ProviderKind.b2, env={})

    message = str(excinfo.value)
    assert "B2_ENDPOINT" in message
    assert "B2_BUCKET" in message
    assert "B2_APPLICATION_KEY" in message
    # Only variable names are reported, never a value.
    assert "=" not in message


def test_config_from_env_builds_each_provider_independently() -> None:
    b2 = config_from_env(
        ProviderKind.b2,
        env={
            "B2_ENDPOINT": "https://s3.us-west-004.backblazeb2.com",
            "B2_BUCKET": "geoint-b2",
            "B2_KEY_ID": "key-id-b2",
            "B2_APPLICATION_KEY": "application-key-b2",
        },
    )
    filebase = config_from_env(
        ProviderKind.filebase,
        env={
            "FILEBASE_ENDPOINT": "https://s3.filebase.com",
            "FILEBASE_BUCKET": "geoint-filebase",
            "FILEBASE_REGION": "us-east-1",
            "FILEBASE_ACCESS_KEY": "access-filebase",
            "FILEBASE_SECRET_KEY": "secret-filebase",
        },
    )

    assert b2.provider is ProviderKind.b2
    assert b2.bucket == "geoint-b2"
    assert filebase.provider is ProviderKind.filebase
    assert filebase.region == "us-east-1"


def test_secrets_never_appear_in_repr_or_dump() -> None:
    config = config_from_env(
        ProviderKind.b2,
        env={
            "B2_ENDPOINT": "https://s3.example",
            "B2_BUCKET": "bucket",
            "B2_KEY_ID": "key-id",
            "B2_APPLICATION_KEY": "super-secret-value",
        },
    )

    assert "super-secret-value" not in repr(config)
    assert "super-secret-value" not in str(config.model_dump())
    assert "super-secret-value" not in config.model_dump_json()


def test_build_providers_uses_the_fake_only_when_explicitly_allowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GEOINT_STORAGE_FAKE", "1")

    providers = build_providers("fake")

    assert len(providers) == 1
    assert isinstance(providers[0], FakeProvider)


def test_env_names_are_documented_for_both_providers() -> None:
    assert ENV_KEYS[ProviderKind.b2]["secret"] == "B2_APPLICATION_KEY"
    assert ENV_KEYS[ProviderKind.filebase]["secret"] == "FILEBASE_SECRET_KEY"


def test_file_checksum_matches_hashlib(tmp_path: Path) -> None:
    import hashlib

    payload = b"object-identity"
    path = tmp_path / "blob.bin"
    path.write_bytes(payload)

    assert file_checksum(path) == hashlib.sha256(payload).hexdigest()


def test_fake_provider_round_trip() -> None:
    provider = FakeProvider(
        ProviderConfig(
            provider=ProviderKind.fake,
            endpoint="memory://",
            bucket="fake",
            key_id="fake",
            secret_key="fake",  # noqa: S106 - test-only
        )
    )
    source = Path(__file__).parent / "fixtures" / "observations.csv"

    ref = provider.upload(source, "raw/x/source.csv", checksum_sha256=file_checksum(source))

    assert ref.key == "raw/x/source.csv"
    assert provider.head("raw/x/source.csv") is not None
    assert provider.head("nope") is None
    provider.delete("raw/x/source.csv")
    assert provider.head("raw/x/source.csv") is None
