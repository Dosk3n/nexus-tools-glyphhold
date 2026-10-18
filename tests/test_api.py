from __future__ import annotations

import importlib
import sys
import types


def load_api(monkeypatch):
    registry = types.ModuleType("nexus.tool_registry")
    registry.register_tool = lambda **kwargs: lambda fn: fn
    monkeypatch.setitem(sys.modules, "nexus", types.ModuleType("nexus"))
    monkeypatch.setitem(sys.modules, "nexus.tool_registry", registry)
    sys.modules.pop("nexus_tools_glyphhold.api", None)
    return importlib.import_module("nexus_tools_glyphhold.api")


class FakeClient:
    def __init__(self):
        self.calls = []

    def request(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return {"ok": True}


def test_scoped_recall_and_broader_search(monkeypatch):
    api = load_api(monkeypatch)
    fake = FakeClient()
    monkeypatch.setattr(api, "get_client", lambda: fake)
    api.prefetch_memories("Jess", space_id="space_personal", session_id="chat")
    assert fake.calls[0][0] == ("POST", "/api/v2/recall")
    assert fake.calls[0][1]["payload"]["session_id"] == "chat"
    api.search_memories("server", broaden=True)
    assert fake.calls[1][1]["payload"]["broaden"] is True


def test_write_versions_idempotency_and_safe_path(monkeypatch):
    api = load_api(monkeypatch)
    fake = FakeClient()
    monkeypatch.setattr(api, "get_client", lambda: fake)
    api.create_memory("Title", "Body", "stable-key", space_id="space_work")
    assert fake.calls[0][1]["payload"]["idempotency_key"] == "stable-key"
    api.update_memory("mem/1", 3, body="Changed")
    assert fake.calls[1][0][1] == "/api/v2/memories/mem%2F1"
    assert fake.calls[1][1]["payload"]["expected_version"] == 3
    assert not hasattr(api, "reveal_secret_env")


def test_secret_tools_use_provider_neutral_v2(monkeypatch):
    api = load_api(monkeypatch)
    fake = FakeClient()
    monkeypatch.setattr(api, "get_client", lambda: fake)
    api.reveal_secret("SSH key", space_id="space_personal")
    assert fake.calls[0][0] == ("POST", "/api/v2/secrets/SSH%20key/reveal")
    assert fake.calls[0][1]["params"] == {"space_id": "space_personal"}


def test_reveal_forwards_optional_legacy_context(monkeypatch):
    api = load_api(monkeypatch)
    fake = FakeClient()
    monkeypatch.setattr(api, "get_client", lambda: fake)
    api.reveal_secret("SSH_PASSWORD", requesting_agent="Melchior", tool="ssh")
    assert fake.calls[0][1]["payload"] == {"requesting_agent": "Melchior", "tool": "ssh"}


def test_optional_secret_folders_field_updates_and_transfer(monkeypatch):
    api = load_api(monkeypatch)
    fake = FakeClient()
    monkeypatch.setattr(api, "get_client", lambda: fake)
    api.create_secret("Token", "test-value", folder_id="home")
    api.list_secret_folders()
    api.reveal_secret("vw:account:item", field="login.username")
    api.update_secret("vw:account:item", "version", "test-new", field="login.password")
    api.migrate_secret("sec_local", 1, target_id="vw:account:item", field="login.password")
    assert fake.calls[0][1]["payload"]["folder_id"] == "home"
    assert "space_id" not in fake.calls[0][1]["payload"]
    assert fake.calls[1][0] == ("GET", "/api/v2/secrets/folders")
    assert fake.calls[2][1]["payload"] == {"field": "login.username"}
    assert fake.calls[3][1]["payload"]["expected_version"] == "version"
    assert fake.calls[4][0][1] == "/api/v2/secrets/sec_local/migrate"
