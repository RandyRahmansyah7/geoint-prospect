"""Connectors that stream a source into a staging file.

Two kinds exist: ``file`` (a repository file) and ``http`` (public HTTPS). Both stream in chunks,
hash while streaming, enforce the size cap, and never load the dataset into memory. The HTTP
connector is a trust boundary: it refuses plain http, private/loopback/metadata addresses, and
redirects that leave the allowed host set.
"""

import hashlib
import ipaddress
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from geoint_prospect.ingestion.contracts import (
    AcquiredFile,
    ConnectorKind,
    IngestionPolicy,
    SourceDefinition,
)
from geoint_prospect.repo import repo_root

CHUNK_BYTES = 64 * 1024
PARQUET_MAGIC = b"PAR1"


class IngestionError(Exception):
    """Structured acquisition failure; the message names the stage and the source."""

    def __init__(self, stage: str, source_id: str, reason: str) -> None:
        super().__init__(f"[{stage}] source '{source_id}': {reason}")
        self.stage = stage
        self.source_id = source_id
        self.reason = reason


class Connector(Protocol):
    kind: ConnectorKind

    def acquire(
        self, source: SourceDefinition, destination: Path, policy: IngestionPolicy
    ) -> AcquiredFile: ...


def _copy_stream(
    read: Callable[[int], bytes],
    destination: Path,
    source: SourceDefinition,
    policy: IngestionPolicy,
) -> AcquiredFile:
    """Stream into ``destination``, hashing as we go and refusing anything over the cap."""
    digest = hashlib.sha256()
    total = 0
    destination.parent.mkdir(parents=True, exist_ok=True)

    with destination.open("wb") as target:
        while True:
            chunk = read(CHUNK_BYTES)
            if not chunk:
                break
            total += len(chunk)
            if total > policy.max_bytes:
                target.close()
                destination.unlink(missing_ok=True)
                raise IngestionError(
                    "ingesting",
                    source.source_id,
                    f"size limit of {policy.max_bytes} bytes exceeded",
                )
            digest.update(chunk)
            target.write(chunk)

    if total == 0:
        destination.unlink(missing_ok=True)
        raise IngestionError("ingesting", source.source_id, "source returned an empty file")

    return AcquiredFile(path=str(destination), bytes=total, checksum_sha256=digest.hexdigest())


def validate_staged_file(acquired: AcquiredFile, source: SourceDefinition) -> None:
    """Cheap format check before the file is handed to the ETL stage."""
    path = Path(acquired.path)
    head = path.open("rb").read(4096)

    if source.format.value == "parquet" and not head.startswith(PARQUET_MAGIC):
        raise IngestionError(
            "ingesting", source.source_id, "file is not Parquet (missing PAR1 magic)"
        )

    if source.format.value == "csv":
        if b"\x00" in head:
            raise IngestionError("ingesting", source.source_id, "file looks binary, not CSV")
        first_line = head.split(b"\n", 1)[0]
        if b"," not in first_line:
            raise IngestionError("ingesting", source.source_id, "CSV header has no comma separator")


class FileConnector:
    """Copy a repository-relative file. The path must stay inside the repository."""

    kind = ConnectorKind.file

    def acquire(
        self, source: SourceDefinition, destination: Path, policy: IngestionPolicy
    ) -> AcquiredFile:
        uri = source.uri
        if uri.startswith("/") or ".." in Path(uri).parts or ":" in uri:
            raise IngestionError("ingesting", source.source_id, "path must be repository-relative")

        root = repo_root()
        origin = (root / uri).resolve()
        if not origin.is_relative_to(root):
            raise IngestionError("ingesting", source.source_id, "path escapes the repository")
        if not origin.is_file():
            raise IngestionError("ingesting", source.source_id, f"file not found: {uri}")

        with origin.open("rb") as handle:
            acquired = _copy_stream(handle.read, destination, source, policy)

        validate_staged_file(acquired, source)
        return acquired


def _is_blocked_address(host: str) -> bool:
    """True for addresses a public source must never resolve to (SSRF guard)."""
    try:
        addresses = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return True  # unresolvable is not fetchable

    for _family, _, _, _, sockaddr in addresses:
        ip = ipaddress.ip_address(sockaddr[0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            return True
    return False


class _GuardedRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Only follow redirects that stay on https and inside the allowed host set."""

    def __init__(self, allowed_hosts: set[str], allow_insecure_http: bool) -> None:
        super().__init__()
        self.allowed_hosts = allowed_hosts
        self.allow_insecure_http = allow_insecure_http

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        parsed = urllib.parse.urlsplit(newurl)
        if parsed.scheme != "https" and not self.allow_insecure_http:
            raise urllib.error.HTTPError(
                newurl, code, "redirect to insecure scheme refused", headers, fp
            )
        if parsed.hostname not in self.allowed_hosts:
            raise urllib.error.HTTPError(
                newurl, code, "redirect to a host that is not allowed", headers, fp
            )
        if not self.allow_insecure_http and _is_blocked_address(parsed.hostname or ""):
            raise urllib.error.HTTPError(newurl, code, "redirect to a blocked address", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class HttpConnector:
    """Stream a public HTTPS source with retries, timeout, size cap, and SSRF guards."""

    kind = ConnectorKind.http

    def acquire(
        self, source: SourceDefinition, destination: Path, policy: IngestionPolicy
    ) -> AcquiredFile:
        parsed = urllib.parse.urlsplit(source.uri)
        if parsed.scheme not in {"https", "http"}:
            raise IngestionError("ingesting", source.source_id, "only http(s) URIs are supported")
        if parsed.scheme == "http" and not policy.allow_insecure_http:
            raise IngestionError("ingesting", source.source_id, "plain http is refused; use https")
        if not parsed.hostname:
            raise IngestionError("ingesting", source.source_id, "URI has no host")
        if not policy.allow_insecure_http and _is_blocked_address(parsed.hostname):
            raise IngestionError(
                "ingesting",
                source.source_id,
                f"host '{parsed.hostname}' resolves to a blocked address",
            )

        allowed_hosts = {parsed.hostname, *policy.allowed_hosts}
        opener = urllib.request.build_opener(
            _GuardedRedirectHandler(allowed_hosts, policy.allow_insecure_http)
        )

        last_error: Exception | None = None
        for attempt in range(1, policy.max_attempts + 1):
            try:
                with opener.open(source.uri, timeout=policy.timeout_seconds) as response:
                    content_type = response.headers.get_content_type()
                    if (
                        source.expected_content_types
                        and content_type not in source.expected_content_types
                    ):
                        raise IngestionError(
                            "ingesting",
                            source.source_id,
                            f"unexpected content type '{content_type}'",
                        )
                    acquired = _copy_stream(response.read, destination, source, policy)
                validate_staged_file(acquired, source)
                return acquired.model_copy(update={"content_type": content_type})
            except urllib.error.HTTPError as exc:
                last_error = exc
                if exc.code < 500:
                    raise IngestionError(
                        "ingesting", source.source_id, f"HTTP {exc.code} from the source"
                    ) from exc
            except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
                last_error = exc
            except IngestionError:
                raise

            if attempt < policy.max_attempts:
                time.sleep(policy.backoff_seconds * (2 ** (attempt - 1)))

        raise IngestionError(
            "ingesting",
            source.source_id,
            f"failed after {policy.max_attempts} attempts: {last_error}",
        )


def connector_for(kind: ConnectorKind) -> Connector:
    return FileConnector() if kind is ConnectorKind.file else HttpConnector()
