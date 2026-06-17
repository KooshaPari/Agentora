"""
Compatibility helpers for MCP QA TUI widgets.
"""

from .widgets_compat import (
    MCPClientAdapter,
    MCPOAuthCacheAdapter,
    OAuthStatusWidget,
    ResourceStatusWidget,
    ServerStatusWidget,
    TunnelStatusWidget,
    check_tui_kit_available,
    create_compatible_widgets,
    get_migration_guide,
)

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
