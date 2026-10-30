from pathlib import Path

import pytest

from geoint_prospect.ingestion.contracts import ConnectorKind
from geoint_prospect.ingestion.registry import UnknownSourceError, load_sources, resolve

VALID = """
source_id = "obs"
connector = "file"
uri = "engine/tests/fixtures/observations.csv"
format = "csv"
licence = "internal-fixture"
attribution = "GEOINT Prospect test fixture"
"""


def _write(directory: Path, name: str, body: str) -> Path:
    path = directory / name
    path.write_text(body, encoding="utf-8")
    return path


def test_repository_registry_contains_the_fixture_source() -> None:
    sources = load_sources()

    assert "fixtures-observations" in sources
    assert sources["fixtures-observations"].connector is ConnectorKind.file


def test_loads_valid_source(tmp_path: Path) -> None:
    _write(tmp_path, "obs.toml", VALID)

    source = load_sources(tmp_path)["obs"]

    assert source.format.value == "csv"
    assert source.licence == "internal-fixture"
    assert source.enabled is True


def test_unknown_keys_are_rejected(tmp_path: Path) -> None:
    _write(tmp_path, "obs.toml", VALID + '\narbitrary_command = "rm -rf /"\n')

    with pytest.raises(ValueError, match="invalid source definition"):
        load_sources(tmp_path)


def test_disabled_source_is_not_registered(tmp_path: Path) -> None:
    _write(tmp_path, "obs.toml", VALID + "\nenabled = false\n")

    assert load_sources(tmp_path) == {}
    with pytest.raises(UnknownSourceError, match="unknown source 'obs'"):
        resolve("obs", tmp_path)


def test_duplicate_ids_are_rejected(tmp_path: Path) -> None:
    _write(tmp_path, "a.toml", VALID)
    _write(tmp_path, "b.toml", VALID.replace('"obs"', '"obs"'))

    with pytest.raises(ValueError, match="duplicate source id"):
        load_sources(tmp_path)


def test_invalid_toml_is_reported_with_the_file_name(tmp_path: Path) -> None:
    _write(tmp_path, "broken.toml", "source_id = \n")

    with pytest.raises(ValueError, match="broken.toml"):
        load_sources(tmp_path)


def test_error_lists_registered_ids(tmp_path: Path) -> None:
    _write(tmp_path, "obs.toml", VALID)

    with pytest.raises(UnknownSourceError, match="registered: obs"):
        resolve("nope", tmp_path)


def test_missing_directory_yields_no_sources(tmp_path: Path) -> None:
    assert load_sources(tmp_path / "absent") == {}
