"""Allowlisted source registry, loaded from ``configs/sources/*.toml``.

One source per file, top-level keys only, validated by :class:`SourceDefinition`. A workflow input
can only name a ``source_id`` that exists here — no arbitrary URLs, no commands.
"""

import os
import tomllib
from pathlib import Path

from pydantic import ValidationError

from geoint_prospect.ingestion.contracts import SourceDefinition
from geoint_prospect.repo import repo_root

DEFAULT_SOURCES_DIR = Path("configs/sources")


class UnknownSourceError(LookupError):
    """The requested source id is not registered or not enabled."""


def sources_dir() -> Path:
    override = os.environ.get("GEOINT_SOURCES_DIR")
    return Path(override) if override else repo_root() / DEFAULT_SOURCES_DIR


def load_sources(directory: Path | None = None) -> dict[str, SourceDefinition]:
    """Return enabled sources by id. Raises ValueError for malformed or duplicate entries."""
    directory = directory or sources_dir()
    if not directory.is_dir():
        return {}

    sources: dict[str, SourceDefinition] = {}
    for path in sorted(directory.glob("*.toml")):
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as exc:
            raise ValueError(f"{path.name}: invalid TOML: {exc}") from exc

        try:
            source = SourceDefinition(**data)
        except ValidationError as exc:
            raise ValueError(f"{path.name}: invalid source definition: {exc}") from exc

        if source.source_id in sources:
            raise ValueError(f"{path.name}: duplicate source id '{source.source_id}'")
        if source.enabled:
            sources[source.source_id] = source

    return sources


def resolve(source_id: str, directory: Path | None = None) -> SourceDefinition:
    """Look up one source; unknown or disabled ids are rejected."""
    directory = directory or sources_dir()
    sources = load_sources(directory)
    try:
        return sources[source_id]
    except KeyError:
        known = ", ".join(sorted(sources)) or "none registered"
        raise UnknownSourceError(
            f"unknown source '{source_id}'; registered: {known} (sources dir: {directory})"
        ) from None
