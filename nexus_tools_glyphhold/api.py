"""GH2 Nexus tools: scoped reads, explicit versioned writes and secret reveal."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from nexus.tool_registry import register_tool

from .client import get_client


def path(memory_id: str):
    return "/api/v2/memories/" + quote(memory_id, safe="")


@register_tool(
    namespace="glyphhold",
    description="Discover GH2 features, permitted spaces and connection default.",
)
def capabilities() -> dict[str, Any]:
    return get_client().request("GET", "/api/v2/capabilities")


@register_tool(namespace="glyphhold", aliases=["glyphhold_health"], description="Check GH2 health.")
def health() -> dict[str, Any]:
    return get_client().health()


@register_tool(
    namespace="glyphhold",
    description="List categories; categories classify facts and do not grant access.",
)
def list_categories() -> list[dict[str, Any]]:
    return get_client().list_categories()


@register_tool(
    namespace="glyphhold",
    description="Retrieve bounded traceable memory from active and permitted General spaces.",
)
def prefetch_memories(
    message: str,
    *,
    space_id: str | None = None,
    session_id: str | None = None,
    max_memories: int = 5,
    max_chars: int = 2400,
) -> dict[str, Any]:
    return get_client().request(
        "POST",
        "/api/v2/recall",
        payload={
            "query": message,
            "space_id": space_id,
            "session_id": session_id,
            "limit": max_memories,
            "max_chars": max_chars,
        },
    )


@register_tool(
    namespace="glyphhold",
    aliases=["search_memory"],
    description="Search active space; explicitly broaden across other permitted spaces when needed. Does not change write destination.",
)
def search_memories(
    query: str,
    *,
    space_id: str | None = None,
    session_id: str | None = None,
    broaden: bool = False,
    limit: int = 10,
    max_chars: int = 12000,
) -> dict[str, Any]:
    return get_client().request(
        "POST",
        "/api/v2/search",
        payload={
            "query": query,
            "space_id": space_id,
            "session_id": session_id,
            "broaden": broaden,
            "limit": limit,
            "max_chars": max_chars,
        },
    )


@register_tool(
    namespace="glyphhold", description="List permitted memories with versions and space ownership."
)
def list_memories(
    *,
    space_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
    include_archived: bool = False,
) -> dict[str, Any]:
    return get_client().request(
        "GET",
        "/api/v2/memories",
        params={
            "space_id": space_id,
            "limit": limit,
            "offset": offset,
            "include_archived": str(include_archived).lower(),
        },
    )


@register_tool(
    namespace="glyphhold",
    description="Get memory by ID including version, provenance and freshness.",
)
def get_memory(memory_id: str) -> dict[str, Any]:
    return get_client().request("GET", path(memory_id))


@register_tool(
    namespace="glyphhold",
    description="Create durable memory after search; reuse idempotency key for retries.",
)
def create_memory(
    title: str,
    body: str,
    idempotency_key: str,
    *,
    space_id: str | None = None,
    session_id: str | None = None,
    category_id: str | None = None,
    summary: str | None = None,
    tags: list[str] | None = None,
    source: str | None = None,
    metadata: dict[str, Any] | None = None,
    auto_prefetch_level: str = "normal",
) -> dict[str, Any]:
    data = {
        "title": title,
        "body": body,
        "idempotency_key": idempotency_key,
        "space_id": space_id,
        "session_id": session_id,
        "category_id": category_id,
        "summary": summary,
        "tags": tags or [],
        "source": source,
        "metadata": metadata or {},
        "auto_prefetch_level": auto_prefetch_level,
    }
    return get_client().request("POST", "/api/v2/memories", payload=data)


@register_tool(
    namespace="glyphhold",
    description="Update a memory using its last-read expected_version; on conflict reread and reconcile.",
)
def update_memory(
    memory_id: str,
    expected_version: int,
    *,
    title: str | None = None,
    body: str | None = None,
    summary: str | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    last_verified_at: str | None = None,
    change_reason: str | None = None,
) -> dict[str, Any]:
    data = {k: v for k, v in locals().items() if k != "memory_id" and v is not None}
    return get_client().request("PATCH", path(memory_id), payload=data)


@register_tool(
    namespace="glyphhold",
    tool_class="write",
    description="Archive a memory reversibly with concurrency protection.",
)
def archive_memory(memory_id: str, expected_version: int) -> dict[str, Any]:
    return get_client().request(
        "POST", path(memory_id) + "/archive", payload={"expected_version": expected_version}
    )


@register_tool(
    namespace="glyphhold",
    tool_class="write",
    description="Explicitly move memory; both source and destination require write grants.",
)
def move_memory(memory_id: str, space_id: str, expected_version: int) -> dict[str, Any]:
    return get_client().request(
        "POST",
        path(memory_id) + "/move",
        payload={"space_id": space_id, "expected_version": expected_version},
    )


@register_tool(namespace="glyphhold", description="Inspect permitted historical memory snapshots.")
def list_memory_revisions(memory_id: str) -> dict[str, Any]:
    return get_client().request("GET", path(memory_id) + "/revisions")


@register_tool(
    namespace="glyphhold",
    tool_class="write",
    description="Restore a permitted revision without overwriting concurrent edits.",
)
def restore_memory_revision(
    memory_id: str, revision_id: str, expected_version: int
) -> dict[str, Any]:
    return get_client().request(
        "POST",
        path(memory_id) + "/restore",
        payload={"revision_id": revision_id, "expected_version": expected_version},
    )


@register_tool(
    namespace="glyphhold",
    description="Read conversation-scoped active space and owner-confirmed guidance.",
)
def get_context(session_id: str) -> dict[str, Any]:
    return get_client().request("GET", "/api/v2/context", params={"session_id": session_id})


@register_tool(
    namespace="glyphhold",
    description="Set active context for one conversation; connection default remains unchanged.",
)
def set_context(session_id: str, space_id: str) -> dict[str, Any]:
    return get_client().request(
        "PUT", "/api/v2/context", payload={"session_id": session_id, "space_id": space_id}
    )


@register_tool(
    namespace="glyphhold",
    description="Read confirmed space-classification guidance before placing a memory.",
)
def placement_guidance(space_id: str | None = None) -> dict[str, Any]:
    return get_client().request("GET", "/api/v2/guidance", params={"space_id": space_id})


@register_tool(
    namespace="glyphhold",
    description="Search global secret metadata in the active vault and built-in storage. provider_name=builtin permits local-only access during vault outages; never returns values.",
)
def search_secrets(
    query: str = "", *, space_id: str | None = None, provider_name: str | None = None
) -> dict[str, Any]:
    return get_client().request(
        "GET",
        "/api/v2/secrets",
        params={
            "query": query,
            "space_id": space_id,
            **({"provider_name": provider_name} if provider_name else {}),
        },
    )


@register_tool(
    namespace="glyphhold",
    description="Inspect one secret metadata record without revealing its value.",
)
def get_secret_metadata(id_or_name: str, *, space_id: str | None = None) -> dict[str, Any]:
    return get_client().request(
        "GET", "/api/v2/secrets/" + quote(id_or_name, safe=""), params={"space_id": space_id}
    )


@register_tool(
    namespace="glyphhold",
    description="Create a global secret in the active provider after searching for duplicates. Optional folder_id; empty string means unfiled, omission uses default.",
)
def create_secret(
    name: str,
    value: str,
    space_id: str | None = None,
    *,
    description: str | None = None,
    value_type: str = "text",
    folder_id: str | None = None,
    username: str | None = None,
    uri: str | None = None,
) -> dict[str, Any]:
    return get_client().request(
        "POST",
        "/api/v2/secrets",
        payload={
            k: v
            for k, v in {
                "name": name,
                "value": value,
                "space_id": space_id,
                "description": description,
                "value_type": value_type,
                "folder_id": folder_id,
                "username": username,
                "uri": uri,
            }.items()
            if v is not None
        },
    )


@register_tool(
    namespace="glyphhold",
    description="Explicitly reveal one secret field for an authorised task. Choose field from metadata for username, password, SSH key, notes or custom fields.",
)
def reveal_secret(
    id_or_name: str,
    *,
    space_id: str | None = None,
    requesting_agent: str | None = None,
    tool: str | None = None,
    field: str | None = None,
) -> dict[str, Any]:
    return get_client().request(
        "POST",
        "/api/v2/secrets/" + quote(id_or_name, safe="") + "/reveal",
        params={"space_id": space_id},
        payload={
            k: v
            for k, v in {"requesting_agent": requesting_agent, "tool": tool, "field": field}.items()
            if v is not None
        },
    )


@register_tool(
    namespace="glyphhold",
    description="List optional Vaultwarden folders. Built-in storage returns supported=false.",
)
def list_secret_folders() -> dict[str, Any]:
    return get_client().request("GET", "/api/v2/secrets/folders")


@register_tool(
    namespace="glyphhold",
    description="Create a vault folder after checking existing folders.",
    tool_class="write",
)
def create_secret_folder(name: str) -> dict[str, Any]:
    return get_client().request("POST", "/api/v2/secrets/folders", payload={"name": name})


@register_tool(
    namespace="glyphhold",
    description="Update one explicitly selected secret field with its current metadata version; never overwrite conflicts without authorisation.",
    tool_class="write",
)
def update_secret(
    id_or_name: str, expected_version: int | str, value: str, *, field: str | None = None
) -> dict[str, Any]:
    return get_client().request(
        "PATCH",
        "/api/v2/secrets/" + quote(id_or_name, safe=""),
        payload={
            k: v
            for k, v in {
                "expected_version": expected_version,
                "value": value,
                "field": field,
            }.items()
            if v is not None
        },
    )


@register_tool(
    namespace="glyphhold",
    description="Transfer a built-in secret server-to-server. Search first; target_id+field verifies identical existing values, otherwise creation requires an unused name. Conflicts retain both values; no plaintext export.",
    tool_class="write",
)
def migrate_secret(
    id_or_name: str,
    expected_version: int,
    *,
    target_id: str | None = None,
    field: str | None = None,
    folder_id: str | None = None,
) -> dict[str, Any]:
    return get_client().request(
        "POST",
        "/api/v2/secrets/" + quote(id_or_name, safe="") + "/migrate",
        payload={
            k: v
            for k, v in {
                "expected_version": expected_version,
                "target_id": target_id,
                "field": field,
                "folder_id": folder_id,
            }.items()
            if v is not None
        },
    )
