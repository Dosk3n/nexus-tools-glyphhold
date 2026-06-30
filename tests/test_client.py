from __future__ import annotations

import json
from typing import Any

import pytest

from nexus_tools_glyphhold.client import GlyphHoldClient, GlyphHoldClientError


class FakeResponse:
    def __init__(self, payload: Any):
        self.payload = payload

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        if self.payload is None:
            return b""
        return json.dumps(self.payload).encode("utf-8")


def test_request_sends_json_auth_and_query_params(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, Any] = {}

    def fake_urlopen(request, timeout=None, context=None):  # noqa: ANN001
        seen["url"] = request.full_url
        seen["method"] = request.get_method()
        seen["timeout"] = timeout
        seen["context"] = context
        seen["headers"] = dict(request.header_items())
        seen["body"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse({"ok": True})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
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

    def fake_urlopen(request, timeout=None, context=None):  # noqa: ANN001, ARG001
        seen["url"] = request.full_url
        seen["method"] = request.get_method()
        seen["body"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse({"matches": []})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    client = GlyphHoldClient(base_url="http://glyphhold.test", api_key="secret")

    client.search_memories(query="deploy host", category="ops", limit=3)

    assert seen["url"] == "http://glyphhold.test/api/v1/memories/search"
    assert seen["method"] == "POST"
    assert seen["body"]["query"] == "deploy host"
    assert seen["body"]["category"] == "ops"
    assert seen["body"]["limit"] == 3


def test_client_requires_url_and_api_key() -> None:
    with pytest.raises(ValueError, match="GLYPHHOLD_URL"):
        GlyphHoldClient(base_url="", api_key="secret")
    with pytest.raises(ValueError, match="GLYPHHOLD_API_KEY"):
        GlyphHoldClient(base_url="http://glyphhold.test", api_key="")


def test_http_errors_are_wrapped(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeHttpError(Exception):
        code = 403

        def read(self) -> bytes:
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

    def fake_urlopen(request, timeout=None, context=None):  # noqa: ANN001, ARG001
        raise error

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    client = GlyphHoldClient(base_url="http://glyphhold.test", api_key="secret")

    with pytest.raises(GlyphHoldClientError, match="HTTP 403: no access"):
        client.health()
