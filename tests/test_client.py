from __future__ import annotations

import json
from typing import Any

import pytest

from nexus_tools_glyphhold.client import GlyphHoldClient, GlyphHoldClientError


class FakeResponse:
    def __init__(self, payload: Any):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self, size=-1) -> bytes:
        if self.payload is None:
            return b""
        return json.dumps(self.payload).encode("utf-8")


def test_request_sends_json_auth_and_query_params(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, Any] = {}

    def fake_urlopen(self, request, timeout=None, context=None):
        seen["url"] = request.full_url
        seen["method"] = request.get_method()
        seen["timeout"] = timeout
        seen["context"] = context
        seen["headers"] = dict(request.header_items())
        seen["body"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse({"ok": True})

    monkeypatch.setattr(GlyphHoldClient, "_open", fake_urlopen)
    client = GlyphHoldClient(base_url="https://glyphhold.test", api_key="secret", timeout_seconds=7)

    result = client.request(
        "POST",
        "/api/v1/example",
        payload={"a": 1},
        params={"query": "hello world", "empty": None},
    )

    assert result == {"ok": True}
    assert seen["url"] == "https://glyphhold.test/api/v1/example?query=hello+world"
    assert seen["method"] == "POST"
    assert seen["timeout"] == 7
    assert seen["headers"]["Authorization"] == "Bearer secret"
    assert seen["headers"]["Content-type"] == "application/json"
    assert seen["body"] == {"a": 1}


def test_search_memories_uses_expected_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, Any] = {}

    def fake_urlopen(self, request, timeout=None, context=None):
        seen["url"] = request.full_url
        seen["method"] = request.get_method()
        seen["body"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse({"matches": []})

    monkeypatch.setattr(GlyphHoldClient, "_open", fake_urlopen)
    client = GlyphHoldClient(base_url="http://glyphhold.test", api_key="secret")

    client.search_memories(query="deploy host", space_id="space_work", limit=3)

    assert seen["url"] == "http://glyphhold.test/api/v2/search"
    assert seen["method"] == "POST"
    assert seen["body"]["query"] == "deploy host"
    assert seen["body"]["space_id"] == "space_work"
    assert seen["body"]["limit"] == 3


def test_client_requires_url_and_api_key() -> None:
    with pytest.raises(ValueError, match="GLYPHHOLD_URL"):
        GlyphHoldClient(base_url="", api_key="secret")
    with pytest.raises(ValueError, match="GLYPHHOLD_API_KEY"):
        GlyphHoldClient(base_url="http://glyphhold.test", api_key="")


def test_http_errors_are_wrapped(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeHttpError(Exception):
        code = 403

        def read(self, size=-1) -> bytes:
            return b'{"detail":"no access"}'

    import urllib.error

    error = urllib.error.HTTPError(
        "http://glyphhold.test",
        403,
        "Forbidden",
        hdrs=None,
        fp=None,
    )
    error.read = FakeHttpError().read  # type: ignore[method-assign]

    def fake_urlopen(self, request, timeout=None, context=None):
        raise error

    monkeypatch.setattr(GlyphHoldClient, "_open", fake_urlopen)
    client = GlyphHoldClient(base_url="http://glyphhold.test", api_key="secret")

    with pytest.raises(GlyphHoldClientError, match="HTTP 403"):
        client.health()


def test_redirects_never_forward_credentials():
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from threading import Thread

    reached = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            if self.path == "/redirect":
                self.send_response(302)
                self.send_header("Location", "/destination")
                self.end_headers()
            else:
                reached.append(self.headers.get("Authorization"))
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"{}")

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        client = GlyphHoldClient(f"http://127.0.0.1:{server.server_port}", "private-key")
        with pytest.raises(GlyphHoldClientError, match="HTTP 302"):
            client.request("GET", "/redirect")
        assert reached == []
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_error_response_does_not_echo_secret_material(monkeypatch):
    import io
    import urllib.error

    def fail(self, request, **kwargs):
        raise urllib.error.HTTPError(
            request.full_url, 400, "Bad request", None, io.BytesIO(b'{"detail":"private-password"}')
        )

    monkeypatch.setattr(GlyphHoldClient, "_open", fail)
    with pytest.raises(GlyphHoldClientError) as error:
        GlyphHoldClient("http://gh", "key").request(
            "POST", "/api/v2/secrets", payload={"value": "private-password"}
        )
    assert "private-password" not in str(error.value)


@pytest.mark.parametrize(
    "body,reason",
    [
        (b"x" * (8 * 1024 * 1024 + 1), "exceeds 8 MiB"),
        (b"\xff", "invalid text"),
        (b"not-json", "invalid JSON"),
    ],
)
def test_unusable_responses_have_safe_errors(monkeypatch, body, reason):
    class Response(FakeResponse):
        def read(self, size=-1):
            return body if size < 0 else body[:size]

    monkeypatch.setattr(GlyphHoldClient, "_open", lambda *a, **kw: Response(None))
    with pytest.raises(GlyphHoldClientError, match=reason):
        GlyphHoldClient("http://gh", "key").health()
