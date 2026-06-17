"""Backward Compatibility Layer for mcp-QA TUI Widgets.

This module provides backward-compatible wrappers around tui-kit widgets,
allowing existing mcp-QA code to work without modification while internally
using the enhanced tui-kit widgets via protocol-based adapters.

The wrapper classes maintain the exact same API as the original dashboard.py widgets,
but delegate to tui-kit widgets for rendering and functionality. This provides:

1. Zero-code-change migration path
2. Immediate access to tui-kit enhancements
3. Protocol-based dependency injection (no hard dependencies)
4. Deprecation warnings guiding users to new API
5. Full backward compatibility with existing code

Author: pheno-sdk team
Created: 2025
"""

import warnings
from typing import Any, Dict, Optional

# Try to import tui-kit widgets (gracefully handle missing dependency)
try:
    from tui_kit.widgets import OAuthStatusWidget as TuiOAuthWidget
    from tui_kit.widgets import ResourceStatusWidget as TuiResourceWidget
    from tui_kit.widgets import ServerStatusWidget as TuiServerWidget
    from tui_kit.widgets import TunnelStatusWidget as TuiTunnelWidget

    HAS_TUI_KIT = True
except ImportError:
    HAS_TUI_KIT = False
    # Fallback to basic Textual widgets if tui-kit not available
    from textual.widgets import Static

    TuiOAuthWidget = Static
    TuiServerWidget = Static
    TuiTunnelWidget = Static
    TuiResourceWidget = Static

__all__ = [
    "OAuthStatusWidget",
    "ServerStatusWidget",
    "TunnelStatusWidget",
    "ResourceStatusWidget",
]


# ============================================================================
# Deprecation Warnings
# ============================================================================


def _emit_deprecation_warning(old_class: str, new_class: str, migration_guide: str) -> None:
    """Emit a deprecation warning for legacy widget usage.

    Args:
        old_class: Name of the legacy class
        new_class: Name of the new tui-kit class
        migration_guide: Brief migration instructions
    """
    warnings.warn(
        f"\n{old_class} is deprecated and will be removed in a future version.\n"
        f"Please migrate to tui_kit.widgets.{new_class}.\n\n"
        f"Migration guide:\n{migration_guide}\n\n"
        f"The legacy API continues to work through compatibility wrappers,\n"
        f"but you'll get better performance and features with the new API.",
        DeprecationWarning,
        stacklevel=3,
    )


# ============================================================================
# Protocol Adapters for mcp-QA Clients
# ============================================================================


class MCPClientAdapter:
    """Adapter to make mcp-QA client compatible with tui-kit ServerStatusWidget
    protocol.

    This adapter wraps any mcp-QA client and exposes the protocol interface
    expected by tui-kit widgets, enabling protocol-based dependency injection.

    Example:
        >>> from pheno.testing.mcp_qa.core.adapters import AtomsMCPClientAdapter
        >>> from fastmcp import Client
        >>>
        >>> client = Client("http://localhost:8000")
        >>> mcp_client_adapter = AtomsMCPClientAdapter(client)
        >>>
        >>> # Create protocol adapter for tui-kit
        >>> adapter = MCPClientAdapter(mcp_client_adapter)
        >>>
        >>> # Use with tui-kit widget
        >>> widget = ServerStatusWidget(client_adapter=adapter)
    """

    def __init__(self, mcp_client_adapter: Optional[Any] = None):
        """Initialize MCP client adapter.

        Args:
            mcp_client_adapter: Any mcp-QA client adapter with list_tools() method
        """
        self.mcp_client = mcp_client_adapter
        self._endpoint = ""

        # Try to extract endpoint from client
        if mcp_client_adapter:
            if hasattr(mcp_client_adapter, "endpoint"):
                self._endpoint = mcp_client_adapter.endpoint
            elif hasattr(mcp_client_adapter, "client"):
                client = mcp_client_adapter.client
                if hasattr(client, "endpoint"):
                    self._endpoint = client.endpoint
                elif hasattr(client, "_endpoint"):
                    self._endpoint = client._endpoint

    @property
    def endpoint(self) -> str:
        """
        Get the server endpoint URL.
        """
        return self._endpoint

    async def list_tools(self) -> list:
        """Perform health check by listing tools.

        Returns:
            List of available tools

        Raises:
            Exception: If client is not configured or connection fails
        """
        if not self.mcp_client:
            raise RuntimeError("No MCP client configured")

        # Call the underlying client's list_tools method
        if hasattr(self.mcp_client, "list_tools"):
            result = await self.mcp_client.list_tools()
            # Handle different return types
            if isinstance(result, list):
                return result
            elif hasattr(result, "tools"):
                return result.tools
            return []

        raise RuntimeError("MCP client does not support list_tools()")


class MCPOAuthCacheAdapter:
    """Adapter to make mcp-QA OAuth cache client compatible with tui-kit protocol.

    This adapter exposes the minimal interface needed by OAuthStatusWidget
    while wrapping the mcp-QA OAuth cache client.

    Example:
        >>> from pheno.testing.mcp_qa.oauth_cache import CachedOAuthClient
        >>>
        >>> oauth_client = CachedOAuthClient("https://api.example.com")
        >>> adapter = MCPOAuthCacheAdapter(oauth_client)
        >>>
        >>> # Use with tui-kit widget
        >>> widget = OAuthStatusWidget(oauth_cache_client=adapter)
    """

    def __init__(self, oauth_cache_client: Optional[Any] = None):
        """Initialize OAuth cache adapter.

        Args:
            oauth_cache_client: mcp-QA OAuth cache client with _get_cache_path() method
        """
        self.oauth_client = oauth_cache_client

    def _get_cache_path(self):
        """Get the path to the OAuth token cache file.

        Returns:
            Path to cache file
        """
        if not self.oauth_client:
            from pathlib import Path

            return Path("/tmp/oauth_cache_not_configured.json")

        if hasattr(self.oauth_client, "_get_cache_path"):
            return self.oauth_client._get_cache_path()
        elif hasattr(self.oauth_client, "cache_path"):
            return self.oauth_client.cache_path

        # Fallback: try to construct path from client properties
        from pathlib import Path

        return Path.home() / ".cache" / "mcp_qa" / "oauth_token.json"


# ============================================================================
# Backward Compatible Widget Wrappers
# ============================================================================


class OAuthStatusWidget(TuiOAuthWidget):
    """Backward-compatible wrapper for OAuth status monitoring.

    Maintains exact API compatibility with original mcp-QA dashboard.py
    OAuthStatusWidget while internally using enhanced tui-kit widget.

    Original API:
        >>> oauth_client = CachedOAuthClient("https://api.example.com")
        >>> widget = OAuthStatusWidget(oauth_cache_client=oauth_client)
        >>> await widget.refresh_status()

    New API (recommended):
        >>> from tui_kit.widgets import OAuthStatusWidget
        >>> widget = OAuthStatusWidget(
        ...     oauth_cache_client=oauth_client,
        ...     show_metrics=True,
        ...     show_sparklines=True,
        ...     auto_refresh_interval=60.0
        ... )

    Migration Guide:
        1. Import from tui_kit.widgets instead of mcp_qa.tui.dashboard
        2. Optional: Enable new features (metrics, sparklines)
        3. Optional: Customize auto-refresh interval
        4. Optional: Add progress widget integration for refresh tracking
    """

    def __init__(self, oauth_cache_client: Optional[Any] = None, **kwargs):
        """Initialize OAuth status widget with backward compatibility.

        Args:
            oauth_cache_client: mcp-QA OAuth cache client instance
            **kwargs: Additional arguments passed to tui-kit widget
        """
        # Emit deprecation warning
        if not kwargs.get("_skip_deprecation_warning", False):
            _emit_deprecation_warning(
                old_class="mcp_qa.tui.dashboard.OAuthStatusWidget",
                new_class="OAuthStatusWidget",
                migration_guide=(
                    "# Old code (still works):\n"
                    "from pheno.testing.mcp_qa.tui.dashboard import OAuthStatusWidget\n"
                    "widget = OAuthStatusWidget(oauth_cache_client=client)\n\n"
                    "# New code (recommended):\n"
                    "from tui_kit.widgets import OAuthStatusWidget\n"
                    "widget = OAuthStatusWidget(\n"
                    "    oauth_cache_client=client,\n"
                    "    show_metrics=True,  # Enhanced metrics\n"
                    "    show_sparklines=True,  # Trend visualization\n"
                    "    auto_refresh_interval=60.0  # Configurable refresh\n"
                    ")"
                ),
            )

        # Remove internal flag before passing to parent
        kwargs.pop("_skip_deprecation_warning", None)

        if not HAS_TUI_KIT:
            # Fallback: Create basic static widget
            from textual.widgets import Static

            Static.__init__(self, **kwargs)
            self.oauth_cache_client = oauth_cache_client
            warnings.warn(
                "tui-kit not installed. Install with: pip install tui-kit\n"
                "Falling back to basic display without enhanced features.",
                RuntimeWarning,
            )
            return

        # Create adapter if client provided
        if oauth_cache_client is not None:
            # Wrap in adapter if not already an adapter
            if (
                not hasattr(oauth_cache_client, "__class__")
                or oauth_cache_client.__class__.__name__ != "MCPOAuthCacheAdapter"
            ):
                oauth_cache_client = MCPOAuthCacheAdapter(oauth_cache_client)

        # Call parent with adapted client
        super().__init__(oauth_cache_client=oauth_cache_client, **kwargs)


class ServerStatusWidget(TuiServerWidget):
    """Backward-compatible wrapper for MCP server status monitoring.

    Maintains exact API compatibility with original mcp-QA dashboard.py
    ServerStatusWidget while internally using enhanced tui-kit widget.

    Original API:
        >>> from pheno.testing.mcp_qa.core.adapters import AtomsMCPClientAdapter
        >>> client_adapter = AtomsMCPClientAdapter(client)
        >>> widget = ServerStatusWidget(client_adapter=client_adapter)
        >>> await widget.refresh_status()

    New API (recommended):
        >>> from tui_kit.widgets import ServerStatusWidget
        >>> widget = ServerStatusWidget(
        ...     client_adapter=protocol_adapter,  # Uses protocol
        ...     check_interval=10.0,
        ...     stream_capture=capture,  # Optional log integration
        ...     max_history=50  # Configurable history size
        ... )

    Migration Guide:
        1. Import from tui_kit.widgets instead of mcp_qa.tui.dashboard
        2. Wrap your client adapter with MCPClientAdapter for protocol compatibility
        3. Optional: Add StreamCapture integration for log tracking
        4. Optional: Customize check interval and history size
    """

    def __init__(self, client_adapter: Optional[Any] = None, endpoint: str = "", **kwargs):
        """Initialize server status widget with backward compatibility.

        Args:
            client_adapter: mcp-QA client adapter instance
            endpoint: Server endpoint URL (used if no adapter provided)
            **kwargs: Additional arguments passed to tui-kit widget
        """
        # Emit deprecation warning
        if not kwargs.get("_skip_deprecation_warning", False):
            _emit_deprecation_warning(
                old_class="mcp_qa.tui.dashboard.ServerStatusWidget",
                new_class="ServerStatusWidget",
                migration_guide=(
                    "# Old code (still works):\n"
                    "from pheno.testing.mcp_qa.tui.dashboard import ServerStatusWidget\n"
                    "widget = ServerStatusWidget(client_adapter=adapter)\n\n"
                    "# New code (recommended):\n"
                    "from tui_kit.widgets import ServerStatusWidget\n"
                    "from pheno.testing.mcp_qa.tui.widgets_compat import MCPClientAdapter\n\n"
                    "# Wrap adapter for protocol compatibility\n"
                    "protocol_adapter = MCPClientAdapter(mcp_client_adapter)\n\n"
                    "widget = ServerStatusWidget(\n"
                    "    client_adapter=protocol_adapter,\n"
                    "    check_interval=10.0,  # Configurable interval\n"
                    "    max_history=50  # Enhanced history tracking\n"
                    ")"
                ),
            )

        # Remove internal flag before passing to parent
        kwargs.pop("_skip_deprecation_warning", None)

        if not HAS_TUI_KIT:
            # Fallback: Create basic static widget
            from textual.widgets import Static

            Static.__init__(self, **kwargs)
            self.client_adapter = client_adapter
            self.endpoint = endpoint
            warnings.warn(
                "tui-kit not installed. Install with: pip install tui-kit\n"
                "Falling back to basic display without enhanced features.",
                RuntimeWarning,
            )
            return

        # Create protocol adapter if client provided
        if client_adapter is not None:
            # Wrap in protocol adapter if not already wrapped
            if (
                not hasattr(client_adapter, "__class__")
                or client_adapter.__class__.__name__ != "MCPClientAdapter"
            ):
                client_adapter = MCPClientAdapter(client_adapter)

        # Call parent with protocol adapter
        super().__init__(client_adapter=client_adapter, endpoint=endpoint, **kwargs)


class TunnelStatusWidget(TuiTunnelWidget):
    """Backward-compatible wrapper for tunnel status monitoring.

    Maintains exact API compatibility with original mcp-QA dashboard.py
    TunnelStatusWidget while internally using enhanced tui-kit widget.

    Original API:
        >>> tunnel_config = {"type": "ngrok", "port": 4040}
        >>> widget = TunnelStatusWidget(tunnel_config=tunnel_config)
        >>> await widget.refresh_status()

    New API (recommended):
        >>> from tui_kit.widgets import TunnelStatusWidget
        >>> widget = TunnelStatusWidget(
        ...     tunnel_config=tunnel_config,
        ...     enable_bandwidth_tracking=True,  # Enhanced metrics
        ...     enable_latency_tracking=True,  # Latency sparklines
        ...     latency_history_size=50  # Configurable history
        ... )

    Migration Guide:
        1. Import from tui_kit.widgets instead of mcp_qa.tui.dashboard
        2. Optional: Enable bandwidth tracking for upload/download metrics
        3. Optional: Enable latency tracking with sparkline visualization
        4. Optional: Customize history size for trend analysis
    """

    def __init__(self, tunnel_config: Optional[Dict[str, Any]] = None, **kwargs):
        """Initialize tunnel status widget with backward compatibility.

        Args:
            tunnel_config: Tunnel configuration dictionary
            **kwargs: Additional arguments passed to tui-kit widget
        """
        # Emit deprecation warning
        if not kwargs.get("_skip_deprecation_warning", False):
            _emit_deprecation_warning(
                old_class="mcp_qa.tui.dashboard.TunnelStatusWidget",
                new_class="TunnelStatusWidget",
                migration_guide=(
                    "# Old code (still works):\n"
                    "from pheno.testing.mcp_qa.tui.dashboard import TunnelStatusWidget\n"
                    "widget = TunnelStatusWidget(tunnel_config=config)\n\n"
                    "# New code (recommended):\n"
                    "from tui_kit.widgets import TunnelStatusWidget\n"
                    "widget = TunnelStatusWidget(\n"
                    "    tunnel_config=config,\n"
                    "    enable_bandwidth_tracking=True,  # Upload/download metrics\n"
                    "    enable_latency_tracking=True,  # Latency sparklines\n"
                    "    latency_history_size=50  # Enhanced history\n"
                    ")"
                ),
            )

        # Remove internal flag before passing to parent
        kwargs.pop("_skip_deprecation_warning", None)

        if not HAS_TUI_KIT:
            # Fallback: Create basic static widget
            from textual.widgets import Static

            Static.__init__(self, **kwargs)
            self.tunnel_config = tunnel_config or {}
            warnings.warn(
                "tui-kit not installed. Install with: pip install tui-kit\n"
                "Falling back to basic display without enhanced features.",
                RuntimeWarning,
            )
            return

        # Call parent with tunnel config
        # No adapter needed - tunnel_config is already in correct format
        super().__init__(tunnel_config=tunnel_config, **kwargs)


class ResourceStatusWidget(TuiResourceWidget):
    """Backward-compatible wrapper for resource status monitoring.

    Maintains exact API compatibility with original mcp-QA dashboard.py
    ResourceStatusWidget while internally using enhanced tui-kit widget.

    Original API:
        >>> resource_config = {
        ...     "check_db": True,
        ...     "check_redis": True,
        ...     "check_api_limits": True
        ... }
        >>> widget = ResourceStatusWidget(resource_config=resource_config)
        >>> await widget.refresh_status()

    New API (recommended):
        >>> from tui_kit.widgets import ResourceStatusWidget
        >>> widget = ResourceStatusWidget(
        ...     resource_config=resource_config,
        ...     enable_sparklines=True,  # Trend visualization
        ...     enable_system_monitoring=True,  # CPU, memory, disk, network
        ...     history_size=50,  # Enhanced history
        ...     check_interval=5.0  # Configurable interval
        ... )

    Migration Guide:
        1. Import from tui_kit.widgets instead of mcp_qa.tui.dashboard
        2. Optional: Enable sparklines for visual trend analysis
        3. Optional: Enable system monitoring for CPU/memory/disk/network
        4. Optional: Customize history size and check interval
        5. Optional: Set custom thresholds for alerts
    """

    def __init__(self, resource_config: Optional[Dict[str, Any]] = None, **kwargs):
        """Initialize resource status widget with backward compatibility.

        Args:
            resource_config: Resource monitoring configuration dictionary
            **kwargs: Additional arguments passed to tui-kit widget
        """
        # Emit deprecation warning
        if not kwargs.get("_skip_deprecation_warning", False):
            _emit_deprecation_warning(
                old_class="mcp_qa.tui.dashboard.ResourceStatusWidget",
                new_class="ResourceStatusWidget",
                migration_guide=(
                    "# Old code (still works):\n"
                    "from pheno.testing.mcp_qa.tui.dashboard import ResourceStatusWidget\n"
                    "widget = ResourceStatusWidget(resource_config=config)\n\n"
                    "# New code (recommended):\n"
                    "from tui_kit.widgets import ResourceStatusWidget\n"
                    "widget = ResourceStatusWidget(\n"
                    "    resource_config=config,\n"
                    "    enable_sparklines=True,  # Trend visualization\n"
                    "    enable_system_monitoring=True,  # CPU/memory/disk/network\n"
                    "    history_size=50,  # Enhanced history\n"
                    "    check_interval=5.0  # Auto-refresh interval\n"
                    ")\n\n"
                    "# Optional: Set custom thresholds\n"
                    "widget.set_thresholds('cpu', warning=70.0, critical=90.0)"
                ),
            )

        # Remove internal flag before passing to parent
        kwargs.pop("_skip_deprecation_warning", None)

        if not HAS_TUI_KIT:
            # Fallback: Create basic static widget
            from textual.widgets import Static

            Static.__init__(self, **kwargs)
            self.resource_config = resource_config or {}
            warnings.warn(
                "tui-kit not installed. Install with: pip install tui-kit\n"
                "Falling back to basic display without enhanced features.",
                RuntimeWarning,
            )
            return

        # Call parent with resource config
        # No adapter needed - resource_config is already in correct format
        super().__init__(resource_config=resource_config, **kwargs)


# ============================================================================
# Helper Functions
# ============================================================================


def create_compatible_widgets(
    oauth_cache_client: Optional[Any] = None,
    client_adapter: Optional[Any] = None,
    tunnel_config: Optional[Dict[str, Any]] = None,
    resource_config: Optional[Dict[str, Any]] = None,
    suppress_warnings: bool = False,
) -> Dict[str, Any]:
    """Create all compatible status widgets at once.

    This is a convenience function for creating all four status widgets
    with backward-compatible parameters.

    Args:
        oauth_cache_client: OAuth cache client for token monitoring
        client_adapter: MCP client adapter for server monitoring
        tunnel_config: Tunnel configuration for tunnel monitoring
        resource_config: Resource configuration for resource monitoring
        suppress_warnings: If True, suppress deprecation warnings

    Returns:
        Dictionary mapping widget names to widget instances

    Example:
        >>> widgets = create_compatible_widgets(
        ...     oauth_cache_client=oauth_client,
        ...     client_adapter=mcp_adapter,
        ...     tunnel_config={"type": "ngrok"},
        ...     resource_config={"check_db": True}
        ... )
        >>> oauth_widget = widgets['oauth']
        >>> server_widget = widgets['server']
    """
    kwargs = {"_skip_deprecation_warning": suppress_warnings}

    return {
        "oauth": OAuthStatusWidget(oauth_cache_client=oauth_cache_client, **kwargs),
        "server": ServerStatusWidget(client_adapter=client_adapter, **kwargs),
        "tunnel": TunnelStatusWidget(tunnel_config=tunnel_config, **kwargs),
        "resource": ResourceStatusWidget(resource_config=resource_config, **kwargs),
    }


# ============================================================================
# Migration Utilities
# ============================================================================


def check_tui_kit_available() -> bool:
    """Check if tui-kit is available.

    Returns:
        True if tui-kit is installed and available
    """
    return HAS_TUI_KIT


def get_migration_guide() -> str:
    """Get comprehensive migration guide for moving from legacy to new API.

    Returns:
        Multi-line string with detailed migration instructions
    """
    return """
=============================================================================
MCP-QA TUI Widgets Migration Guide
=============================================================================

The mcp-QA TUI widgets have been extracted into the standalone tui-kit
package for better reusability and enhanced features. Your existing code
continues to work through backward-compatible wrappers, but migrating to
the new API provides:

1. Enhanced metrics and sparkline visualizations
2. Configurable auto-refresh intervals
3. Better performance and memory efficiency
4. Protocol-based dependency injection (no hard dependencies)
5. Integration with unified progress tracking
6. Comprehensive history tracking and trend analysis

-----------------------------------------------------------------------------
MIGRATION STEPS
-----------------------------------------------------------------------------

1. Install tui-kit (if not already installed):

   pip install tui-kit

2. Update imports:

   # Before:
   from pheno.testing.mcp_qa.tui.dashboard import (
       OAuthStatusWidget,
       ServerStatusWidget,
       TunnelStatusWidget,
       ResourceStatusWidget
   )

   # After:
   from tui_kit.widgets import (
       OAuthStatusWidget,
       ServerStatusWidget,
       TunnelStatusWidget,
       ResourceStatusWidget
   )

3. Wrap client adapters for protocol compatibility:

   # Before:
   from pheno.testing.mcp_qa.core.adapters import AtomsMCPClientAdapter
   widget = ServerStatusWidget(client_adapter=mcp_adapter)

   # After:
   from tui_kit.widgets import ServerStatusWidget
   from pheno.testing.mcp_qa.tui.widgets_compat import MCPClientAdapter

   protocol_adapter = MCPClientAdapter(mcp_adapter)
   widget = ServerStatusWidget(client_adapter=protocol_adapter)

4. Enable new features (optional):

   # OAuth widget with enhanced features
   oauth_widget = OAuthStatusWidget(
       oauth_cache_client=client,
       show_metrics=True,  # Token refresh metrics
       show_sparklines=True,  # Latency trends
       auto_refresh_interval=60.0  # Configurable refresh
   )

   # Server widget with enhanced features
   server_widget = ServerStatusWidget(
       client_adapter=protocol_adapter,
       check_interval=10.0,  # Auto health checks
       max_history=50,  # Enhanced history
       stream_capture=capture  # Log integration
   )

   # Tunnel widget with enhanced features
   tunnel_widget = TunnelStatusWidget(
       tunnel_config=config,
       enable_bandwidth_tracking=True,  # Upload/download metrics
       enable_latency_tracking=True,  # Latency sparklines
       latency_history_size=50
   )

   # Resource widget with enhanced features
   resource_widget = ResourceStatusWidget(
       resource_config=config,
       enable_sparklines=True,  # Trend visualization
       enable_system_monitoring=True,  # CPU/memory/disk
       history_size=50,
       check_interval=5.0
   )

-----------------------------------------------------------------------------
COMPATIBILITY NOTES
-----------------------------------------------------------------------------

- Backward-compatible wrappers preserve exact API compatibility
- Deprecation warnings guide you to new API (can be suppressed)
- All existing code continues to work without modification
- Enhanced features are opt-in via new parameters
- Protocol adapters enable flexible dependency injection

For more information, see: https://docs.pheno-sdk.dev/migration/tui-widgets
=============================================================================
"""


if __name__ == "__main__":
    # Print migration guide when run as script
    print(get_migration_guide())
