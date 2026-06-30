from __future__ import annotations

from typing import Any

import pytest

nexus_tool_registry = pytest.importorskip("nexus.tool_registry")

from nexus_tools_glyphhold import api  # noqa: E402


class FakeClient:
    def __init__(self) -> None:
        self.deleted_memories: list[str] = []
        self.deleted_secrets: list[str] = []

    def get_memory(self, *, memory_id: str) -> dict[str, Any]:
        return {"id": memory_id, "title": "Deploy host"}

    def delete_memory(self, *, memory_id: str) -> None:
        self.deleted_memories.append(memory_id)

    def get_secret_metadata(self, *, id_or_name: str) -> dict[str, Any]:
        return {"id": "sec_123", "name": id_or_name}

    def delete_secret(self, *, id_or_name: str) -> None:
        self.deleted_secrets.append(id_or_name)


def test_registers_glyphhold_tools() -> None:
    names = {tool.name for tool in nexus_tool_registry.iter_tools()}

    assert {
        "glyphhold.health",
        "glyphhold.search_memories",
        "glyphhold.create_memory",
        "glyphhold.search_secrets",
        "glyphhold.reveal_secret",
    }.issubset(names)


def test_validation_rejects_invalid_confidence() -> None:
    with pytest.raises(ValueError, match="confidence"):
        api.create_memory("cat_123", "Title", "Body", confidence=6)


def test_delete_memory_requires_matching_title(monkeypatch: pytest.MonkeyPatch) -> None:
    client = FakeClient()
    monkeypatch.setattr(api, "get_client", lambda: client)

    with pytest.raises(Exception, match="confirmation"):
        api.delete_memory("mem_123", "Wrong title")

    result = api.delete_memory("mem_123", "Deploy host")

    assert result == {"deleted": "mem_123"}
    assert client.deleted_memories == ["mem_123"]


def test_delete_secret_requires_matching_name(monkeypatch: pytest.MonkeyPatch) -> None:
    client = FakeClient()
    monkeypatch.setattr(api, "get_client", lambda: client)

    with pytest.raises(Exception, match="confirmation"):
        api.delete_secret("github-token", "wrong")

    result = api.delete_secret("github-token", "github-token")

    assert result == {"deleted": "github-token"}
    assert client.deleted_secrets == ["github-token"]
