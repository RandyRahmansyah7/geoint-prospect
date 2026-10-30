"""Locating the repository root.

The engine runs from a checkout (Actions checks the repository out), so source definitions can use
repository-relative paths. A non-editable install would put this file in site-packages, so the
working directory is checked first and the package location is only a fallback.
"""

import os
from pathlib import Path

MARKER = Path("engine") / "pyproject.toml"


def _walk_up(start: Path) -> Path | None:
    for candidate in (start, *start.parents):
        if (candidate / MARKER).is_file():
            return candidate
    return None


def repo_root() -> Path:
    """Repository root, or ``GEOINT_REPO_ROOT`` when a caller overrides it."""
    override = os.environ.get("GEOINT_REPO_ROOT")
    if override:
        return Path(override).resolve()

    found = _walk_up(Path.cwd().resolve()) or _walk_up(Path(__file__).resolve().parent)
    if found is not None:
        return found

    # No checkout in sight (installed package running outside the repository).
    return Path(__file__).resolve().parents[3]
