"""Backward compatibility layer for the historical MCP QA TUI widgets.

The original implementation depended on ``tui-kit``.  For the consolidated code
base we ship lightweight stand-ins so existing dashboards can continue to
instantiate the widgets while we work on a unified UI story.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..core.base.client_adapter import MCPClientAdapter as _CoreClientAdapter


def check_tui_kit_available() -> bool:
    try:  # pragma: no cover - optional import
        import tui_kit  # type: ignore  # noqa: F401

        return True
    except Exception:
        return False


def get_migration_guide() -> str:
    return (
        "MIGRATION STEPS\n"
        "1. Replace imports from 'mcp_qa.tui.widgets' with 'pheno.mcp.qa.tui'.\n"
        "2. Update widget initialisation to use dependency-injected clients.\n"
        "3. Remove legacy tui-kit specific styling hooks.\n"
    )


@dataclass
class MCPOAuthCacheAdapter:
    """
    Small wrapper exposing ``_get_cache_path`` for compatibility.
    """

    oauth_client: Any

    def _get_cache_path(self) -> Path:
        if hasattr(self.oauth_client, "_get_cache_path"):
            return Path(self.oauth_client._get_cache_path())  # type: ignore[attr-defined]
        return Path("/tmp/mcp_oauth_cache.json")


class MCPClientAdapter(_CoreClientAdapter):
    """
    Alias so callers importing from the TUI module continue to work.
    """



@dataclass
class OAuthStatusWidget:
    oauth_cache_client: Any
    suppress_warning: bool = False

    def get_status(self) -> dict[str, Any]:
        adapter = MCPOAuthCacheAdapter(self.oauth_cache_client)
        return {"cache_path": str(adapter._get_cache_path())}


@dataclass
class ServerStatusWidget:
    client_adapter: Any

    def get_status(self) -> dict[str, Any]:
        endpoint = getattr(self.client_adapter, "endpoint", "")
        return {"endpoint": endpoint}


@dataclass
class TunnelStatusWidget:
    tunnel_config: dict[str, Any] = field(default_factory=dict)

    def get_status(self) -> dict[str, Any]:
        return dict(self.tunnel_config)


@dataclass
class ResourceStatusWidget:
    resource_config: dict[str, Any] = field(default_factory=dict)

    def get_status(self) -> dict[str, Any]:
        return dict(self.resource_config)


def create_compatible_widgets(
    *,
    oauth_cache_client: Any,
    client_adapter: Any,
    tunnel_config: dict[str, Any],
    resource_config: dict[str, Any],
    suppress_warnings: bool = False,
) -> dict[str, Any]:
    return {
        "oauth": OAuthStatusWidget(oauth_cache_client, suppress_warning=suppress_warnings),
        "server": ServerStatusWidget(client_adapter),
        "tunnel": TunnelStatusWidget(tunnel_config),
        "resource": ResourceStatusWidget(resource_config),
    }


__all__ = [
    "MCPClientAdapter",
    "MCPOAuthCacheAdapter",
    "OAuthStatusWidget",
    "ResourceStatusWidget",
    "ServerStatusWidget",
    "TunnelStatusWidget",
    "check_tui_kit_available",
    "create_compatible_widgets",
    "get_migration_guide",
]
