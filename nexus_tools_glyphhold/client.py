"""Standard-library HTTP client for Glyph Hold."""

from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

try:
    from nexus.config import get_setting as _nexus_get_setting
except ImportError:
    _nexus_get_setting = None

DEFAULT_USER_AGENT = "NexusMCP/0.1 nexus-tools-glyphhold/0.1"


class GlyphHoldClientError(RuntimeError):
    """Raised when Glyph Hold cannot be reached or returns an error."""


def get_setting(name: str) -> Optional[str]:
    if _nexus_get_setting is not None:
        return _nexus_get_setting(name)
    import os

    return os.getenv(name)


def _normalize_base_url(value: Optional[str]) -> str:
    base_url = (value or "").strip()
    if not base_url:
        return ""
    if not base_url.startswith(("http://", "https://")):
        base_url = f"http://{base_url}"
    return base_url.rstrip("/")


def _float_setting(name: str, default: float) -> float:
    raw = get_setting(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _bool_setting(name: str, default: bool) -> bool:
    raw = get_setting(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _compact(values: Dict[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None}


@dataclass
class GlyphHoldClient:
    """Small sync client for the Glyph Hold HTTP API."""

    base_url: str
    api_key: str
    timeout_seconds: float = 20.0
    verify_ssl: bool | str = True

    def __post_init__(self) -> None:
        self.base_url = _normalize_base_url(self.base_url)
        if not self.base_url:
            raise ValueError("GLYPHHOLD_URL is required.")
        if not self.api_key:
            raise ValueError("GLYPHHOLD_API_KEY is required.")

    def _url(self, path: str, params: Optional[Dict[str, Any]] = None) -> str:
        normalized_path = path if path.startswith("/") else f"/{path}"
        url = f"{self.base_url}{normalized_path}"
        clean_params = _compact(params or {})
        if clean_params:
            url = f"{url}?{urllib.parse.urlencode(clean_params, doseq=True)}"
        return url

    def _ssl_context(self) -> ssl.SSLContext | None:
        if not self.base_url.startswith("https://"):
            return None
        if self.verify_ssl is True:
            return None
        if self.verify_ssl is False:
            return ssl._create_unverified_context()  # noqa: S323
        return ssl.create_default_context(cafile=str(self.verify_ssl))

    def request(
        self,
        method: str,
        path: str,
        *,
        payload: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(self._url(path, params), data=body, method=method.upper())
        request.add_header("Accept", "application/json")
        request.add_header("Authorization", f"Bearer {self.api_key}")
        request.add_header("User-Agent", DEFAULT_USER_AGENT)
        if payload is not None:
            request.add_header("Content-Type", "application/json")

        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout_seconds,
                context=self._ssl_context(),
            ) as response:
                response_body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(detail)
                detail = str(parsed.get("detail") or detail)
            except ValueError:
                pass
            raise GlyphHoldClientError(
                f"Glyph Hold returned HTTP {exc.code}: {detail}"
            ) from exc
        except urllib.error.URLError as exc:
            raise GlyphHoldClientError(f"Could not connect to Glyph Hold: {exc.reason}") from exc

        if not response_body:
            return None
        return json.loads(response_body)

    def health(self) -> Dict[str, Any]:
        return self.request("GET", "/api/v1/health")

    def list_categories(self) -> List[Dict[str, Any]]:
        return self.request("GET", "/api/v1/categories")

    def list_memories(
        self,
        *,
        category: Optional[str] = None,
        tag: Optional[str] = None,
        include_archived: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        return self.request(
            "GET",
            "/api/v1/memories",
            params={
                "category": category,
                "tag": tag,
                "include_archived": include_archived,
                "limit": limit,
                "offset": offset,
            },
        )

    def get_memory(self, *, memory_id: str) -> Dict[str, Any]:
        return self.request("GET", f"/api/v1/memories/{memory_id}")

    def search_memories(
        self,
        *,
        query: str,
        category: Optional[str] = None,
        limit: int = 10,
        include_archived: bool = False,
    ) -> Dict[str, Any]:
        return self.request(
            "POST",
            "/api/v1/memories/search",
            payload={
                "query": query,
                "category": category,
                "limit": limit,
                "include_archived": include_archived,
            },
        )

    def prefetch_memories(
        self,
        *,
        message: str,
        agent: Optional[str] = "codex",
        max_memories: int = 3,
        max_chars: int = 1200,
        max_tokens: int = 300,
        summaries_only: bool = True,
    ) -> Dict[str, Any]:
        return self.request(
            "POST",
            "/api/v1/agent/prefetch",
            payload={
                "message": message,
                "agent": agent,
                "max_memories": max_memories,
                "max_chars": max_chars,
                "max_tokens": max_tokens,
                "summaries_only": summaries_only,
            },
        )

    def find_similar_memories(
        self,
        *,
        title: str,
        body: str,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 5,
    ) -> Dict[str, Any]:
        return self.request(
            "POST",
            "/api/v1/memories/find-similar",
            payload={
                "category": category,
                "title": title,
                "body": body,
                "tags": tags or [],
                "limit": limit,
            },
        )

    def prepare_memory_write(
        self,
        *,
        title: str,
        body: str,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 5,
    ) -> Dict[str, Any]:
        return self.request(
            "POST",
            "/api/v1/memories/prepare-write",
            payload={
                "category": category,
                "title": title,
                "body": body,
                "tags": tags or [],
                "limit": limit,
            },
        )

    def create_memory(
        self,
        *,
        category_id: str,
        title: str,
        body: str,
        summary: Optional[str] = None,
        tags: Optional[List[str]] = None,
        confidence: int = 3,
        auto_prefetch_level: str = "normal",
    ) -> Dict[str, Any]:
        return self.request(
            "POST",
            "/api/v1/memories",
            payload={
                "category_id": category_id,
                "title": title,
                "summary": summary,
                "body": body,
                "tags": tags or [],
                "confidence": confidence,
                "auto_prefetch_level": auto_prefetch_level,
            },
        )

    def update_memory(
        self,
        *,
        memory_id: str,
        category_id: Optional[str] = None,
        title: Optional[str] = None,
        summary: Optional[str] = None,
        body: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None,
        confidence: Optional[int] = None,
        auto_prefetch_level: Optional[str] = None,
        archived: Optional[bool] = None,
        superseded_by: Optional[str] = None,
        change_reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self.request(
            "PATCH",
            f"/api/v1/memories/{memory_id}",
            payload=_compact(
                {
                    "category_id": category_id,
                    "title": title,
                    "summary": summary,
                    "body": body,
                    "tags": tags,
                    "metadata": metadata,
                    "source": source,
                    "confidence": confidence,
                    "auto_prefetch_level": auto_prefetch_level,
                    "archived": archived,
                    "superseded_by": superseded_by,
                    "change_reason": change_reason,
                }
            ),
        )

    def delete_memory(self, *, memory_id: str) -> None:
        return self.request("DELETE", f"/api/v1/memories/{memory_id}")

    def update_memory_confidence(
        self,
        *,
        memory_id: str,
        confidence: int,
        change_reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self.request(
            "POST",
            f"/api/v1/memories/{memory_id}/confidence",
            payload=_compact({"confidence": confidence, "change_reason": change_reason}),
        )

    def archive_memory(self, *, memory_id: str) -> Dict[str, Any]:
        return self.request("POST", f"/api/v1/memories/{memory_id}/archive", payload={})

    def supersede_memory(self, *, memory_id: str, superseded_by: str) -> Dict[str, Any]:
        return self.request(
            "POST",
            f"/api/v1/memories/{memory_id}/supersede",
            payload={"superseded_by": superseded_by},
        )

    def list_memory_revisions(self, *, memory_id: str) -> List[Dict[str, Any]]:
        return self.request("GET", f"/api/v1/memories/{memory_id}/revisions")

    def restore_memory_revision(
        self,
        *,
        memory_id: str,
        revision_id: str,
        change_reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self.request(
            "POST",
            f"/api/v1/memories/{memory_id}/revisions/{revision_id}/restore",
            payload=_compact({"change_reason": change_reason}),
        )

    def list_secrets(
        self,
        *,
        query: Optional[str] = None,
        service: Optional[str] = None,
        host: Optional[str] = None,
        scope: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        return self.request(
            "GET",
            "/api/v1/secrets",
            params={
                "query": query,
                "service": service,
                "host": host,
                "scope": scope,
                "limit": limit,
                "offset": offset,
            },
        )

    def get_secret_metadata(self, *, id_or_name: str) -> Dict[str, Any]:
        return self.request("GET", f"/api/v1/secrets/{urllib.parse.quote(id_or_name)}")

    def create_secret(
        self,
        *,
        name: str,
        value: str,
        description: Optional[str] = None,
        value_type: str = "text",
        service: Optional[str] = None,
        host: Optional[str] = None,
        scope: Optional[str] = None,
        tags: Optional[List[str]] = None,
        allowed_agents: Optional[List[str]] = None,
        allowed_tools: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        return self.request(
            "POST",
            "/api/v1/secrets",
            payload={
                "name": name,
                "value": value,
                "description": description,
                "value_type": value_type,
                "service": service,
                "host": host,
                "scope": scope,
                "tags": tags or [],
                "allowed_agents": allowed_agents or [],
                "allowed_tools": allowed_tools or [],
            },
        )

    def update_secret(
        self,
        *,
        id_or_name: str,
        name: Optional[str] = None,
        value: Optional[str] = None,
        description: Optional[str] = None,
        value_type: Optional[str] = None,
        service: Optional[str] = None,
        host: Optional[str] = None,
        scope: Optional[str] = None,
        tags: Optional[List[str]] = None,
        allowed_agents: Optional[List[str]] = None,
        allowed_tools: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        return self.request(
            "PATCH",
            f"/api/v1/secrets/{urllib.parse.quote(id_or_name)}",
            payload=_compact(
                {
                    "name": name,
                    "value": value,
                    "description": description,
                    "value_type": value_type,
                    "service": service,
                    "host": host,
                    "scope": scope,
                    "tags": tags,
                    "allowed_agents": allowed_agents,
                    "allowed_tools": allowed_tools,
                }
            ),
        )

    def delete_secret(self, *, id_or_name: str) -> None:
        return self.request("DELETE", f"/api/v1/secrets/{urllib.parse.quote(id_or_name)}")

    def reveal_secret(
        self,
        *,
        id_or_name: str,
        requesting_agent: Optional[str] = "codex",
        tool: Optional[str] = None,
        purpose: str = "Nexus reveal requested by Codex",
    ) -> Dict[str, Any]:
        return self.request(
            "POST",
            f"/api/v1/secrets/{urllib.parse.quote(id_or_name)}/reveal",
            payload=_compact(
                {"requesting_agent": requesting_agent, "tool": tool, "purpose": purpose}
            ),
        )

    def reveal_secret_env(
        self,
        *,
        scope: Optional[str] = None,
        requesting_agent: Optional[str] = "codex",
        purpose: str = "Nexus env reveal requested by Codex",
    ) -> Dict[str, Any]:
        return self.request(
            "POST",
            "/api/v1/secrets/env",
            payload=_compact(
                {"scope": scope, "requesting_agent": requesting_agent, "purpose": purpose}
            ),
        )


_default_client: Optional[GlyphHoldClient] = None
_default_client_key: Optional[tuple[str, str, float, bool | str]] = None


def get_client() -> GlyphHoldClient:
    """Get or create a Glyph Hold client from Nexus settings."""

    global _default_client, _default_client_key

    base_url = _normalize_base_url(get_setting("GLYPHHOLD_URL"))
    api_key = get_setting("GLYPHHOLD_API_KEY") or ""
    timeout_seconds = _float_setting("GLYPHHOLD_TIMEOUT_SECONDS", 20.0)
    ca_bundle = (get_setting("GLYPHHOLD_CA_BUNDLE") or "").strip()
    verify_ssl: bool | str = ca_bundle or _bool_setting("GLYPHHOLD_VERIFY_SSL", True)
    key = (base_url, api_key, timeout_seconds, verify_ssl)

    if _default_client is None or _default_client_key != key:
        _default_client = GlyphHoldClient(
            base_url=base_url,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
            verify_ssl=verify_ssl,
        )
        _default_client_key = key
    return _default_client
