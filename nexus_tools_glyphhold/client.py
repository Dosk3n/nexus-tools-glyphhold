"""Standard-library HTTP client for Glyph Hold."""

from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

try:
    from nexus.config import get_setting as _nexus_get_setting
except ImportError:
    _nexus_get_setting = None

DEFAULT_USER_AGENT = "NexusMCP/0.1 nexus-tools-glyphhold/2.2.0"


SAFE_VAULT_ERRORS = {
    "vault_item_not_found": "Vault item not found; search again and use a current ID",
    "vault_unavailable": "External vault unavailable; test the saved connection.",
    "secret_values_differ": "Values differ; both secrets retained. Ask the user.",
    "vault_status_failed": "Vault status failed. Test the saved connection or repeat this read.",
    "vault_config_failed": "Vault config failed. Test the saved connection or repeat this read.",
    "vault_login_failed": "Vault login failed. Test the saved connection or repeat this read.",
    "vault_unlock_failed": "Vault unlock failed. Test the saved connection or repeat this read.",
    "vault_sync_failed": "Vault sync failed. Test the saved connection or repeat this read.",
    "vault_get_failed": "Vault get failed. Test the saved connection or repeat this read.",
    "vault_list_failed": "Vault list failed. Test the saved connection or repeat this read.",
    "vault_create_failed": "Vault create failed. Check the destination before retrying.",
    "vault_edit_failed": "Vault edit failed. Check the destination before retrying.",
    "vault_operation_failed": "Vault operation failed. Test the saved connection.",
}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class GlyphHoldClientError(RuntimeError):
    """Raised when Glyph Hold cannot be reached or returns an error."""


def get_setting(name: str) -> str | None:
    if _nexus_get_setting is not None:
        return _nexus_get_setting(name)
    import os

    return os.getenv(name)


def _normalize_base_url(value: str | None) -> str:
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


def _compact(values: dict[str, Any]) -> dict[str, Any]:
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

    def _url(self, path: str, params: dict[str, Any] | None = None) -> str:
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
            return ssl._create_unverified_context()
        return ssl.create_default_context(cafile=str(self.verify_ssl))

    def _open(self, request, *, timeout):
        opener = urllib.request.build_opener(
            _NoRedirect(), urllib.request.HTTPSHandler(context=self._ssl_context())
        )
        return opener.open(request, timeout=timeout)

    def request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(self._url(path, params), data=body, method=method.upper())
        request.add_header("Accept", "application/json")
        request.add_header("Authorization", f"Bearer {self.api_key}")
        request.add_header("User-Agent", DEFAULT_USER_AGENT)
        if payload is not None:
            request.add_header("Content-Type", "application/json")

        try:
            with self._open(
                request,
                timeout=max(self.timeout_seconds, 90)
                if path.startswith("/api/v2/secrets")
                else self.timeout_seconds,
            ) as response:
                raw = response.read(8 * 1024 * 1024 + 1)
                if len(raw) > 8 * 1024 * 1024:
                    raise GlyphHoldClientError(
                        "Glyph Hold response exceeds 8 MiB; request fewer records"
                    )
                try:
                    response_body = raw.decode("utf-8")
                except UnicodeError as exc:
                    raise GlyphHoldClientError("Glyph Hold returned invalid text") from exc
        except urllib.error.HTTPError as exc:
            hint = (
                SAFE_VAULT_ERRORS.get(exc.headers.get("X-GlyphHold-Error", ""))
                if exc.headers
                else None
            )
            if hint:
                raise GlyphHoldClientError(f"Glyph Hold HTTP {exc.code}: {hint}") from exc

            raise GlyphHoldClientError(
                f"Glyph Hold returned HTTP {exc.code}; check permissions, versions and server status"
            ) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise GlyphHoldClientError("Could not connect to Glyph Hold") from exc

        if not response_body:
            return None
        try:
            return json.loads(response_body)
        except ValueError as exc:
            raise GlyphHoldClientError("Glyph Hold returned invalid JSON") from exc

    def health(self) -> dict[str, Any]:
        return self.request("GET", "/api/v1/health")

    def list_categories(self) -> list[dict[str, Any]]:
        return self.request("GET", "/api/v1/categories")

    def search_memories(
        self, *, query: str, space_id: str | None = None, broaden: bool = False, limit: int = 10
    ):
        return self.request(
            "POST",
            "/api/v2/search",
            payload={"query": query, "space_id": space_id, "broaden": broaden, "limit": limit},
        )


_default_client: GlyphHoldClient | None = None
_default_client_key: tuple[str, str, float, bool | str] | None = None


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
