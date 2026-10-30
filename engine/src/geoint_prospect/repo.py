"""Locating the repository root.

The engine always runs from a checkout (Actions checks the repository out), so paths in source
definitions can be repository-relative regardless of the working directory of the process.
"""

import os
from pathlib import Path


def repo_root() -> Path:
    """Repository root, or ``GEOINT_REPO_ROOT`` when a caller overrides it."""
    override = os.environ.get("GEOINT_REPO_ROOT")
    if override:
        return Path(override).resolve()
    # engine/src/geoint_prospect/repo.py → parents[3] is the repository root.
    return Path(__file__).resolve().parents[3]
