"""
pheno.mcp - Model Context Protocol Unified API

Consolidated MCP functionality with hexagonal architecture:
- Domain types and manager (pheno.mcp)
- Port protocols (pheno.ports.mcp)
- Adapter implementations (mcp-sdk-kit, mcp-infra-sdk)

Features:
- Unified MCP manager for all operations
- Resource access via URIs (config://, db://, storage://, etc.)
- Tool registry and execution
- Session management
- Workflow monitoring and metrics
- Resource templates and project graphs

Usage:
    from pheno.mcp import McpManager, McpServer, McpTool

    # Create manager
    manager = McpManager()

    # Connect to server
    server = McpServer(url="http://localhost:8000")
    session = await manager.connect(server)

    # Execute tool
    result = await manager.execute_tool("search", {"query": "hello"})

    # Access resources
    config = await manager.get_resource("config://app/database")
"""

from __future__ import annotations

__version__ = "0.2.0"

# Adapters (for custom implementations)
from .adapter_base import CRUDToolAdapterBase, MCPToolAdapterBase
from .adapters import (
    InMemoryMcpProvider,
    InMemoryMonitoringProvider,
    InMemoryResourceProvider,
    InMemorySessionManager,
    InMemoryToolRegistry,
)

# Manager
from .manager import McpManager, get_mcp_manager, set_mcp_manager
from .registry import MCPToolsRegistry, SimpleMCPToolsRegistry

# Setup utilities
from .setup import register_custom_scheme, setup_mcp, setup_mcp_with_config

# Domain types
from .types import (
    McpServer,
    McpSession,
    McpTool,
    Resource,
    SessionStatus,
    ToolExecution,
    ToolResult,
    ToolStatus,
    WorkflowExecution,
)

# Legacy modules removed - no longer needed

__all__ = [
    "CRUDToolAdapterBase",
    # Adapters (NEW)
    "InMemoryMcpProvider",
    "InMemoryMonitoringProvider",
    "InMemoryResourceProvider",
    "InMemorySessionManager",
    "InMemoryToolRegistry",
    "MCPToolAdapterBase",
    # MCP Tool Infrastructure (Phase 2.5)
    "MCPToolsRegistry",
    # Core API (NEW - Consolidated)
    "McpManager",
    # Domain Types (NEW)
    "McpServer",
    "McpSession",
    "McpTool",
    "Resource",
    "SessionStatus",
    "SimpleMCPToolsRegistry",
    "ToolExecution",
    "ToolResult",
    "ToolStatus",
    "WorkflowExecution",
    "get_mcp_manager",
    "register_custom_scheme",
    "set_mcp_manager",
    # Setup utilities (NEW)
    "setup_mcp",
    "setup_mcp_with_config",
]

# Legacy exports removed - no backward compatibility needed
