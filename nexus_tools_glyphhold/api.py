"""Nexus tools for Glyph Hold memory and secrets."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from nexus.tool_registry import register_tool

from .client import GlyphHoldClientError, get_client

PrefetchLevel = str
SecretValueType = str


def _check_range(name: str, value: int, minimum: int, maximum: int) -> None:
    if value < minimum or value > maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}.")


def _check_choice(name: str, value: Optional[str], choices: set[str]) -> None:
    if value is not None and value not in choices:
        allowed = ", ".join(sorted(choices))
        raise ValueError(f"{name} must be one of: {allowed}.")


@register_tool(
    namespace="glyphhold",
    aliases=["glyphhold_health"],
    description="Check the configured Glyph Hold service health and version.",
    examples=['load_tool("glyphhold.health")()'],
)
def health() -> Dict[str, Any]:
    return get_client().health()


@register_tool(
    namespace="glyphhold",
    description="List available Glyph Hold memory categories.",
    examples=['load_tool("glyphhold.list_categories")()'],
)
def list_categories() -> List[Dict[str, Any]]:
    return get_client().list_categories()


@register_tool(
    namespace="glyphhold",
    description="List Glyph Hold memories, optionally filtered by category, tag, and archive state.",
    examples=['load_tool("glyphhold.list_memories")(category="ops", limit=20)'],
)
def list_memories(
    *,
    category: Optional[str] = None,
    tag: Optional[str] = None,
    include_archived: bool = False,
    limit: int = 100,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    _check_range("limit", limit, 1, 500)
    _check_range("offset", offset, 0, 1_000_000_000)
    return get_client().list_memories(
        category=category,
        tag=tag,
        include_archived=include_archived,
        limit=limit,
        offset=offset,
    )


@register_tool(
    namespace="glyphhold",
    description="Get one Glyph Hold memory by id.",
    examples=['load_tool("glyphhold.get_memory")("mem_123")'],
)
def get_memory(memory_id: str) -> Dict[str, Any]:
    return get_client().get_memory(memory_id=memory_id)


@register_tool(
    namespace="glyphhold",
    aliases=["search_memory"],
    description="Search Glyph Hold memories with deterministic SQLite FTS.",
    examples=['load_tool("glyphhold.search_memories")("deployment host", limit=5)'],
)
def search_memories(
    query: str,
    *,
    category: Optional[str] = None,
    limit: int = 10,
    include_archived: bool = False,
) -> Dict[str, Any]:
    _check_range("limit", limit, 1, 100)
    return get_client().search_memories(
        query=query,
        category=category,
        limit=limit,
        include_archived=include_archived,
    )


@register_tool(
    namespace="glyphhold",
    description="Ask Glyph Hold for conservative memory context relevant to a message.",
    examples=['load_tool("glyphhold.prefetch_memories")("What should I remember for deploys?")'],
)
def prefetch_memories(
    message: str,
    *,
    agent: Optional[str] = "codex",
    max_memories: int = 3,
    max_chars: int = 1200,
    max_tokens: int = 300,
    summaries_only: bool = True,
) -> Dict[str, Any]:
    _check_range("max_memories", max_memories, 1, 10)
    _check_range("max_chars", max_chars, 100, 8000)
    _check_range("max_tokens", max_tokens, 25, 2000)
    return get_client().prefetch_memories(
        message=message,
        agent=agent,
        max_memories=max_memories,
        max_chars=max_chars,
        max_tokens=max_tokens,
        summaries_only=summaries_only,
    )


@register_tool(
    namespace="glyphhold",
    description="Find existing memories that may duplicate or overlap proposed memory content.",
    examples=[
        'load_tool("glyphhold.find_similar_memories")("Deploy host", "The deploy host is hermes")',
    ],
)
def find_similar_memories(
    title: str,
    body: str,
    *,
    category: Optional[str] = None,
    tags: Optional[List[str]] = None,
    limit: int = 5,
) -> Dict[str, Any]:
    _check_range("limit", limit, 1, 20)
    return get_client().find_similar_memories(
        title=title,
        body=body,
        category=category,
        tags=tags,
        limit=limit,
    )


@register_tool(
    namespace="glyphhold",
    description="Check likely duplicates and conflicts before creating a durable memory.",
    examples=[
        'load_tool("glyphhold.prepare_memory_write")("Deploy host", "The deploy host is hermes")',
    ],
)
def prepare_memory_write(
    title: str,
    body: str,
    *,
    category: Optional[str] = None,
    tags: Optional[List[str]] = None,
    limit: int = 5,
) -> Dict[str, Any]:
    _check_range("limit", limit, 1, 20)
    return get_client().prepare_memory_write(
        title=title,
        body=body,
        category=category,
        tags=tags,
        limit=limit,
    )


@register_tool(
    namespace="glyphhold",
    description=(
        "Create a Glyph Hold memory after confirming it should be stored durably. "
        "Search or prepare the write first when practical to avoid duplicates."
    ),
    examples=[
        'load_tool("glyphhold.create_memory")("cat_ops", "Deploy host", "The deploy host is hermes")',
    ],
)
def create_memory(
    category_id: str,
    title: str,
    body: str,
    *,
    summary: Optional[str] = None,
    tags: Optional[List[str]] = None,
    confidence: int = 3,
    auto_prefetch_level: PrefetchLevel = "normal",
) -> Dict[str, Any]:
    _check_range("confidence", confidence, 1, 5)
    _check_choice("auto_prefetch_level", auto_prefetch_level, {"never", "low", "normal", "high", "pinned"})
    return get_client().create_memory(
        category_id=category_id,
        title=title,
        body=body,
        summary=summary,
        tags=tags,
        confidence=confidence,
        auto_prefetch_level=auto_prefetch_level,
    )


@register_tool(
    namespace="glyphhold",
    description="Update an existing memory only when the user intends to change stored long-term context.",
    examples=[
        'load_tool("glyphhold.update_memory")("mem_123", body="Updated value", change_reason="User correction")',
    ],
)
def update_memory(
    memory_id: str,
    *,
    category_id: Optional[str] = None,
    title: Optional[str] = None,
    summary: Optional[str] = None,
    body: Optional[str] = None,
    tags: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    source: Optional[str] = None,
    confidence: Optional[int] = None,
    auto_prefetch_level: Optional[PrefetchLevel] = None,
    archived: Optional[bool] = None,
    superseded_by: Optional[str] = None,
    change_reason: Optional[str] = None,
) -> Dict[str, Any]:
    if confidence is not None:
        _check_range("confidence", confidence, 1, 5)
    _check_choice("auto_prefetch_level", auto_prefetch_level, {"never", "low", "normal", "high", "pinned"})
    return get_client().update_memory(
        memory_id=memory_id,
        category_id=category_id,
        title=title,
        summary=summary,
        body=body,
        tags=tags,
        metadata=metadata,
        source=source,
        confidence=confidence,
        auto_prefetch_level=auto_prefetch_level,
        archived=archived,
        superseded_by=superseded_by,
        change_reason=change_reason,
    )


@register_tool(
    namespace="glyphhold",
    description="Update a memory confidence score from 1 to 5.",
    examples=['load_tool("glyphhold.update_memory_confidence")("mem_123", 4)'],
)
def update_memory_confidence(
    memory_id: str,
    confidence: int,
    *,
    change_reason: Optional[str] = None,
) -> Dict[str, Any]:
    _check_range("confidence", confidence, 1, 5)
    return get_client().update_memory_confidence(
        memory_id=memory_id,
        confidence=confidence,
        change_reason=change_reason,
    )


@register_tool(
    namespace="glyphhold",
    description="Archive a memory so normal searches and prefetches exclude it.",
    examples=['load_tool("glyphhold.archive_memory")("mem_123")'],
)
def archive_memory(memory_id: str) -> Dict[str, Any]:
    return get_client().archive_memory(memory_id=memory_id)


@register_tool(
    namespace="glyphhold",
    description="Mark one memory as superseded by another memory id.",
    examples=['load_tool("glyphhold.supersede_memory")("mem_old", "mem_new")'],
)
def supersede_memory(memory_id: str, superseded_by: str) -> Dict[str, Any]:
    return get_client().supersede_memory(memory_id=memory_id, superseded_by=superseded_by)


@register_tool(
    namespace="glyphhold",
    description="List revision history for one memory.",
    examples=['load_tool("glyphhold.list_memory_revisions")("mem_123")'],
)
def list_memory_revisions(memory_id: str) -> List[Dict[str, Any]]:
    return get_client().list_memory_revisions(memory_id=memory_id)


@register_tool(
    namespace="glyphhold",
    description="Restore a memory from a previous revision.",
    examples=['load_tool("glyphhold.restore_memory_revision")("mem_123", "rev_456")'],
)
def restore_memory_revision(
    memory_id: str,
    revision_id: str,
    *,
    change_reason: Optional[str] = None,
) -> Dict[str, Any]:
    return get_client().restore_memory_revision(
        memory_id=memory_id,
        revision_id=revision_id,
        change_reason=change_reason,
    )


@register_tool(
    namespace="glyphhold",
    description="Permanently delete a memory after confirm_title exactly matches the current title.",
    examples=['load_tool("glyphhold.delete_memory")("mem_123", "Deploy host")'],
)
def delete_memory(memory_id: str, confirm_title: str) -> Dict[str, str]:
    client = get_client()
    memory = client.get_memory(memory_id=memory_id)
    if memory["title"] != confirm_title:
        raise GlyphHoldClientError("Memory title confirmation did not match; delete was not performed.")
    client.delete_memory(memory_id=memory_id)
    return {"deleted": memory_id}


@register_tool(
    namespace="glyphhold",
    description="Search/list secret metadata only. Secret values are not returned by this tool.",
    examples=['load_tool("glyphhold.search_secrets")(service="github")'],
)
def search_secrets(
    *,
    query: Optional[str] = None,
    service: Optional[str] = None,
    host: Optional[str] = None,
    scope: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    _check_range("limit", limit, 1, 500)
    _check_range("offset", offset, 0, 1_000_000_000)
    return get_client().list_secrets(
        query=query,
        service=service,
        host=host,
        scope=scope,
        limit=limit,
        offset=offset,
    )


@register_tool(
    namespace="glyphhold",
    description="Get secret metadata only by id or name. The secret value is not returned.",
    examples=['load_tool("glyphhold.get_secret_metadata")("github-token")'],
)
def get_secret_metadata(id_or_name: str) -> Dict[str, Any]:
    return get_client().get_secret_metadata(id_or_name=id_or_name)


@register_tool(
    namespace="glyphhold",
    description="Create encrypted Glyph Hold secret metadata and value.",
    examples=['load_tool("glyphhold.create_secret")("github-token", "ghp_...", value_type="token")'],
)
def create_secret(
    name: str,
    value: str,
    *,
    description: Optional[str] = None,
    value_type: SecretValueType = "text",
    service: Optional[str] = None,
    host: Optional[str] = None,
    scope: Optional[str] = None,
    tags: Optional[List[str]] = None,
    allowed_agents: Optional[List[str]] = None,
    allowed_tools: Optional[List[str]] = None,
) -> Dict[str, Any]:
    _check_choice(
        "value_type",
        value_type,
        {"text", "api_key", "password", "token", "webhook_url", "username", "json"},
    )
    return get_client().create_secret(
        name=name,
        value=value,
        description=description,
        value_type=value_type,
        service=service,
        host=host,
        scope=scope,
        tags=tags,
        allowed_agents=allowed_agents,
        allowed_tools=allowed_tools,
    )


@register_tool(
    namespace="glyphhold",
    description="Update secret metadata, access restrictions, or value only when the user intends it.",
    examples=['load_tool("glyphhold.update_secret")("github-token", description="GitHub API token")'],
)
def update_secret(
    id_or_name: str,
    *,
    name: Optional[str] = None,
    value: Optional[str] = None,
    description: Optional[str] = None,
    value_type: Optional[SecretValueType] = None,
    service: Optional[str] = None,
    host: Optional[str] = None,
    scope: Optional[str] = None,
    tags: Optional[List[str]] = None,
    allowed_agents: Optional[List[str]] = None,
    allowed_tools: Optional[List[str]] = None,
) -> Dict[str, Any]:
    _check_choice(
        "value_type",
        value_type,
        {"text", "api_key", "password", "token", "webhook_url", "username", "json"},
    )
    return get_client().update_secret(
        id_or_name=id_or_name,
        name=name,
        value=value,
        description=description,
        value_type=value_type,
        service=service,
        host=host,
        scope=scope,
        tags=tags,
        allowed_agents=allowed_agents,
        allowed_tools=allowed_tools,
    )


@register_tool(
    namespace="glyphhold",
    description="Permanently delete a secret after confirm_name exactly matches the current secret name.",
    examples=['load_tool("glyphhold.delete_secret")("github-token", "github-token")'],
)
def delete_secret(id_or_name: str, confirm_name: str) -> Dict[str, str]:
    client = get_client()
    secret = client.get_secret_metadata(id_or_name=id_or_name)
    if secret["name"] != confirm_name:
        raise GlyphHoldClientError("Secret name confirmation did not match; delete was not performed.")
    client.delete_secret(id_or_name=id_or_name)
    return {"deleted": secret["name"]}


@register_tool(
    namespace="glyphhold",
    description="Reveal a secret value only when the user explicitly asks for the secret value.",
    examples=['load_tool("glyphhold.reveal_secret")("github-token", purpose="Use token for requested API call")'],
)
def reveal_secret(
    id_or_name: str,
    *,
    requesting_agent: Optional[str] = "codex",
    tool: Optional[str] = None,
    purpose: str = "Nexus reveal requested by Codex",
) -> Dict[str, Any]:
    return get_client().reveal_secret(
        id_or_name=id_or_name,
        requesting_agent=requesting_agent,
        tool=tool,
        purpose=purpose,
    )


@register_tool(
    namespace="glyphhold",
    description="Reveal multiple secret values as env-style values only when the user explicitly asks.",
    examples=['load_tool("glyphhold.reveal_secret_env")(scope="github")'],
)
def reveal_secret_env(
    *,
    scope: Optional[str] = None,
    requesting_agent: Optional[str] = "codex",
    purpose: str = "Nexus env reveal requested by Codex",
) -> Dict[str, Any]:
    return get_client().reveal_secret_env(
        scope=scope,
        requesting_agent=requesting_agent,
        purpose=purpose,
    )
