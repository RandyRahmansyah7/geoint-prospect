"""Stable object-key layout.

    raw/<source_id>/<version>/<filename>
    processed/<dataset_id>/<request_id>/<filename>
    manifests/<request_id>.json
    tiles/<region>/<version>.pmtiles

Every component is sanitised: no separators, no traversal, no control characters.
"""

import re

SAFE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
UNSAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]")


class InvalidObjectKey(ValueError):
    """A key component is not safe to use in an object store."""


def safe_component(value: str, *, field: str, max_length: int = 96) -> str:
    """Return ``value`` unchanged when it is already safe, otherwise reject it."""
    if not value or len(value) > max_length or not SAFE.match(value) or ".." in value:
        raise InvalidObjectKey(
            f"unsafe {field} for an object key: {value!r} "
            "(allowed: letters, digits, dot, underscore, hyphen)"
        )
    return value


def slug(value: str, *, max_length: int = 96) -> str:
    """Best-effort sanitised component for values we did not choose (file names, titles)."""
    cleaned = UNSAFE_CHARS.sub("_", value).strip("._-")
    if not cleaned:
        raise InvalidObjectKey(f"cannot build an object key from {value!r}")
    return cleaned[:max_length]


def raw_key(source_id: str, version: str, filename: str) -> str:
    return f"raw/{safe_component(source_id, field='source_id')}/{slug(version)}/{slug(filename)}"


def processed_key(dataset_id: str, request_id: str, filename: str) -> str:
    return (
        f"processed/{safe_component(dataset_id, field='dataset_id')}/"
        f"{safe_component(request_id, field='request_id')}/{slug(filename)}"
    )


def manifest_key(request_id: str) -> str:
    return f"manifests/{safe_component(request_id, field='request_id')}.json"


def tiles_key(region: str, version: str) -> str:
    return f"tiles/{safe_component(region, field='region')}/{slug(version)}.pmtiles"
