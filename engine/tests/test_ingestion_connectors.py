"""Connector tests: a loopback test server stands in for a public source, no internet, no credentials."""

import hashlib
import threading
import time
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from pydantic import ValidationError

from geoint_prospect.etl.contracts import DataFormat
from geoint_prospect.ingestion.connectors import (
    FileConnector,
    HttpConnector,
    IngestionError,
    validate_staged_file,
)
from geoint_prospect.ingestion.contracts import IngestionPolicy, SourceDefinition

FIXTURE = Path("engine/tests/fixtures/observations.csv")
CSV_BODY = b"object_id,confidence\na123,0.82\n"


def _policy(**overrides: object) -> IngestionPolicy:
    defaults: dict[str, object] = {
        "allow_insecure_http": True,
        "timeout_seconds": 5,
        "max_attempts": 2,
        "backoff_seconds": 0,
        "max_bytes": 10_000,
    }
    defaults.update(overrides)
    return IngestionPolicy(**defaults)


def _source(**overrides: object) -> SourceDefinition:
    defaults: dict[str, object] = {
        "source_id": "test-source",
        "connector": "http",
        "uri": "https://example.invalid/data.csv",
        "format": DataFormat.csv,
    }
    defaults.update(overrides)
    return SourceDefinition(**defaults)


class _Handler(BaseHTTPRequestHandler):
    behavior = "csv"
    hits = 0

    def do_GET(self) -> None:  # noqa: N802 - http.server API
        type(self).hits += 1
        if self.behavior == "csv":
            self._send(200, "text/csv", CSV_BODY)
        elif self.behavior == "fail-then-ok" and type(self).hits == 1:
            self._send(500, "text/plain", b"boom")
        elif self.behavior == "fail-then-ok":
            self._send(200, "text/csv", CSV_BODY)
        elif self.behavior == "missing":
            self._send(404, "text/plain", b"nope")
        elif self.behavior == "empty":
            self._send(200, "text/csv", b"")
        elif self.behavior == "big":
            self._send(200, "text/csv", b"a,b\n" + b"x,y\n" * 5000)
        elif self.behavior == "binary":
            self._send(200, "text/csv", b"\x00\x01\x02binary")
        elif self.behavior == "wrong-type":
            self._send(200, "application/octet-stream", CSV_BODY)
        elif self.behavior == "slow":
            time.sleep(2)
            self._send(200, "text/csv", CSV_BODY)
        elif self.behavior == "redirect-away":
            self.send_response(302)
            self.send_header("Location", "http://example.com/other.csv")
            self.end_headers()
        else:  # pragma: no cover - guards future test additions
            self._send(500, "text/plain", b"unknown behavior")

    def _send(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: object) -> None:  # keep pytest output clean
        return


@pytest.fixture
def server() -> Iterator[str]:
    _Handler.behavior = "csv"
    _Handler.hits = 0
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_address[1]}/data.csv"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)


def test_http_download_streams_and_hashes(server: str, tmp_path: Path) -> None:
    source = _source(uri=server)

    acquired = HttpConnector().acquire(source, tmp_path / "staged.csv", _policy())

    assert Path(acquired.path).read_bytes() == CSV_BODY
    assert acquired.bytes == len(CSV_BODY)
    assert acquired.content_type == "text/csv"
    assert len(acquired.checksum_sha256) == 64


def test_checksum_matches_the_downloaded_bytes(server: str, tmp_path: Path) -> None:
    acquired = HttpConnector().acquire(_source(uri=server), tmp_path / "staged.csv", _policy())

    assert acquired.checksum_sha256 == hashlib.sha256(CSV_BODY).hexdigest()


def test_timeout_is_enforced(server: str, tmp_path: Path) -> None:
    _Handler.behavior = "slow"

    started = time.monotonic()
    with pytest.raises(IngestionError, match="failed after 2 attempts"):
        HttpConnector().acquire(
            _source(uri=server),
            tmp_path / "staged.csv",
            _policy(timeout_seconds=0.5, max_attempts=2),
        )

    assert time.monotonic() - started < 2  # the slow handler was cut off, not awaited
    assert not (tmp_path / "staged.csv").exists()


def test_retry_succeeds_after_server_error(server: str, tmp_path: Path) -> None:
    _Handler.behavior = "fail-then-ok"

    acquired = HttpConnector().acquire(
        _source(uri=server, source_id="retry"), tmp_path / "staged.csv", _policy(max_attempts=3)
    )

    assert acquired.bytes == len(CSV_BODY)
    assert _Handler.hits == 2


def test_client_error_is_not_retried(server: str, tmp_path: Path) -> None:
    _Handler.behavior = "missing"

    with pytest.raises(IngestionError, match="HTTP 404"):
        HttpConnector().acquire(_source(uri=server), tmp_path / "staged.csv", _policy())

    assert _Handler.hits == 1


def test_size_limit_aborts_the_download(server: str, tmp_path: Path) -> None:
    _Handler.behavior = "big"

    with pytest.raises(IngestionError, match="size limit"):
        HttpConnector().acquire(
            _source(uri=server), tmp_path / "staged.csv", _policy(max_bytes=1024)
        )

    assert not (tmp_path / "staged.csv").exists()


def test_empty_download_is_rejected(server: str, tmp_path: Path) -> None:
    _Handler.behavior = "empty"

    with pytest.raises(IngestionError, match="empty file"):
        HttpConnector().acquire(_source(uri=server), tmp_path / "staged.csv", _policy())


def test_unexpected_content_type_is_rejected(server: str, tmp_path: Path) -> None:
    _Handler.behavior = "wrong-type"

    with pytest.raises(IngestionError, match="unexpected content type"):
        HttpConnector().acquire(
            _source(uri=server, expected_content_types=("text/csv",)),
            tmp_path / "staged.csv",
            _policy(),
        )


def test_binary_file_is_not_accepted_as_csv(server: str, tmp_path: Path) -> None:
    _Handler.behavior = "binary"

    with pytest.raises(IngestionError, match="looks binary"):
        HttpConnector().acquire(_source(uri=server), tmp_path / "staged.csv", _policy())


def test_redirect_leaving_the_allowed_hosts_is_refused(server: str, tmp_path: Path) -> None:
    _Handler.behavior = "redirect-away"

    with pytest.raises(IngestionError):
        HttpConnector().acquire(_source(uri=server), tmp_path / "staged.csv", _policy())


def test_plain_http_is_refused_by_default(tmp_path: Path) -> None:
    with pytest.raises(IngestionError, match="plain http is refused"):
        HttpConnector().acquire(
            _source(uri="http://example.org/data.csv"),
            tmp_path / "staged.csv",
            _policy(allow_insecure_http=False),
        )


def test_private_and_loopback_hosts_are_blocked(tmp_path: Path) -> None:
    guard = _policy(allow_insecure_http=False)

    with pytest.raises(IngestionError, match="blocked address"):
        HttpConnector().acquire(
            _source(uri="https://127.0.0.1/data.csv"), tmp_path / "a.csv", guard
        )
    with pytest.raises(IngestionError, match="blocked address"):
        HttpConnector().acquire(
            _source(uri="https://169.254.169.254/latest/meta-data"), tmp_path / "b.csv", guard
        )


def test_connection_failure_reports_attempts(tmp_path: Path) -> None:
    with pytest.raises(IngestionError, match="failed after 2 attempts"):
        HttpConnector().acquire(
            _source(uri="http://127.0.0.1:9/data.csv"),
            tmp_path / "staged.csv",
            _policy(max_attempts=2),
        )


def test_file_connector_stages_a_repository_file(tmp_path: Path) -> None:
    source = _source(connector="file", uri=str(FIXTURE))
    original = (Path(__file__).parent / "fixtures" / "observations.csv").read_bytes()

    acquired = FileConnector().acquire(source, tmp_path / "staged.csv", _policy())

    assert Path(acquired.path).read_bytes() == original
    assert acquired.bytes == len(original)
    assert acquired.checksum_sha256 == hashlib.sha256(original).hexdigest()


def test_policy_bounds_are_validated() -> None:
    for overrides in (
        {"max_attempts": 0},
        {"max_attempts": 9},
        {"max_bytes": 0},
        {"timeout_seconds": 0},
    ):
        with pytest.raises(ValidationError):
            IngestionPolicy(**overrides)


def test_file_connector_rejects_paths_outside_the_repository(tmp_path: Path) -> None:
    for uri in ("/etc/passwd", "../../etc/passwd", "https://example.org/x.csv"):
        with pytest.raises(IngestionError):
            FileConnector().acquire(
                _source(connector="file", uri=uri), tmp_path / "staged.csv", _policy()
            )


def test_parquet_magic_is_required() -> None:
    from geoint_prospect.ingestion.contracts import AcquiredFile

    source = _source(connector="file", format=DataFormat.parquet, uri=str(FIXTURE))
    acquired = AcquiredFile(
        path=str(Path(__file__).parent / "fixtures" / "observations.csv"),
        bytes=1,
        checksum_sha256="x",
    )

    with pytest.raises(IngestionError, match="not Parquet"):
        validate_staged_file(acquired, source)
