"""MCP Adapters Module.

Provides adapter implementations for wrapping existing MCP objects
to implement standardized provider protocols.

This module contains:
- Protocol definitions for providers
- Adapter implementations wrapping MCP components
- Factory functions for creating adapters

Example:
    from pheno.testing.mcp_qa.adapters import (
        create_oauth_adapter,
        create_resource_adapter,
        MCPClientAdapter
    )

    # Create OAuth adapter
    oauth_adapter = create_oauth_adapter("https://api.example.com/mcp")

    # Create resource monitor
    resource_monitor = create_resource_adapter()
    resource_monitor.register_process("server", port=8000)

    # Wrap client adapter
    from pheno.testing.mcp_qa.core.adapters import MCPClientAdapter as CoreAdapter
    client_adapter = MCPClientAdapter(CoreAdapter(client))
"""

from pheno.testing.mcp_qa.adapters.adapters_base import (
    ClientAdapter,
    DatabaseProvider,
    OAuthCacheProvider,
    ResourceMonitor,
    TunnelProvider,
)
from pheno.testing.mcp_qa.adapters.adapters_integration import (
    MCPClientAdapter,
    MCPDatabaseAdapter,
    MCPResourceAdapter,
    create_resource_adapter,
)
from pheno.testing.mcp_qa.adapters.adapters_widgets import (
    MCPOAuthCacheAdapter,
    MCPTunnelAdapter,
    create_oauth_adapter,
    create_tunnel_adapter,
)
from pheno.testing.mcp_qa.adapters.fast_http_client import FastHTTPClient

__all__ = [
    # Protocols
    "OAuthCacheProvider",
    "ClientAdapter",
    "TunnelProvider",
    "ResourceMonitor",
    "DatabaseProvider",
    # Adapters
    "MCPOAuthCacheAdapter",
    "MCPClientAdapter",
    "MCPTunnelAdapter",
    "MCPResourceAdapter",
    "MCPDatabaseAdapter",
    "FastHTTPClient",
    # Factory functions
    "create_oauth_adapter",
    "create_resource_adapter",
    "create_tunnel_adapter",
]
