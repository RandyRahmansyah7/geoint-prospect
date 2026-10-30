"""The registry must be findable from any working directory, installed or not."""

import os
from pathlib import Path

import pytest

from geoint_prospect.ingestion.registry import sources_dir
from geoint_prospect.repo import repo_root


def test_repo_root_is_the_checkout() -> None:
    root = repo_root()

    assert (root / "engine" / "pyproject.toml").is_file()
    assert (root / "configs" / "sources").is_dir()


def test_sources_dir_follows_the_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GEOINT_SOURCES_DIR", str(tmp_path))

    assert sources_dir() == tmp_path


def test_repo_root_survives_an_installed_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Simulate site-packages: the package path has no checkout, so cwd must win."""
    fake_site_packages = tmp_path / "site-packages" / "geoint_prospect"
    fake_site_packages.mkdir(parents=True)
    monkeypatch.delenv("GEOINT_REPO_ROOT", raising=False)
    monkeypatch.chdir(repo_root())

    from geoint_prospect import repo as repo_module

    monkeypatch.setattr(repo_module, "__file__", str(fake_site_packages / "repo.py"))
    assert repo_module.repo_root() == repo_root()
    assert os.path.samefile(repo_module.repo_root(), repo_root())
