"""MCP Manager.

Central manager for MCP operations using dependency injection. Coordinates between
different MCP providers via ports.
"""

from __future__ import annotations

import logging
from typing import Any

from pheno.adapters.container import Container, get_container
from pheno.mcp.types import (
    McpServer,
    McpSession,
    McpTool,
    ToolExecution,
    ToolResult,
)
from pheno.ports.mcp import (
    McpProvider,
    MonitoringProvider,
    ResourceProvider,
    SessionManager,
    ToolRegistry,
)

logger = logging.getLogger(__name__)


class McpManager:
    """Central MCP manager.

    Coordinates MCP operations using dependency injection.
    Provides a unified API for all MCP functionality.

    Example:
        >>> manager = McpManager()
        >>>
        >>> # Connect to server
        >>> session = await manager.connect(server)
        >>>
        >>> # Execute tool
        >>> result = await manager.execute_tool("search", {"query": "hello"})
        >>>
        >>> # Access resources
        >>> config = await manager.get_resource("config://app/database")
    """

    def __init__(self, container: Container | None = None):
        """Initialize MCP manager.

        Args:
            container: Optional DI container (uses global if None)
        """
        self.container = container or get_container()
        self._default_session: McpSession | None = None

    def _get_provider(self) -> McpProvider:
        """
        Get MCP provider from container.
        """
        if not self.container.has_service(McpProvider):
            raise RuntimeError(
                "McpProvider not registered. "
                "Register an implementation: container.register(McpProvider, YourProvider)",
            )
        return self.container.resolve(McpProvider)

    def _get_resource_provider(self) -> ResourceProvider:
        """
        Get resource provider from container.
        """
        if not self.container.has_service(ResourceProvider):
            raise RuntimeError(
                "ResourceProvider not registered. "
                "Register an implementation: container.register(ResourceProvider, YourProvider)",
            )
        return self.container.resolve(ResourceProvider)

    def _get_tool_registry(self) -> ToolRegistry:
        """
        Get tool registry from container.
        """
        if not self.container.has_service(ToolRegistry):
            raise RuntimeError(
                "ToolRegistry not registered. "
                "Register an implementation: container.register(ToolRegistry, YourRegistry)",
            )
        return self.container.resolve(ToolRegistry)

    def _get_session_manager(self) -> SessionManager:
        """
        Get session manager from container.
        """
        if not self.container.has_service(SessionManager):
            raise RuntimeError(
                "SessionManager not registered. "
                "Register an implementation: container.register(SessionManager, YourManager)",
            )
        return self.container.resolve(SessionManager)

    def _get_monitoring_provider(self) -> MonitoringProvider | None:
        """
        Get monitoring provider from container (optional).
        """
        if self.container.has_service(MonitoringProvider):
            return self.container.resolve(MonitoringProvider)
        return None

    # Connection Management

    async def connect(self, server: McpServer) -> McpSession:
        """Connect to an MCP server.

        Args:
            server: MCP server configuration

        Returns:
            Active MCP session

        Example:
            >>> server = McpServer(url="http://localhost:8000")
            >>> session = await manager.connect(server)
        """
        session_manager = self._get_session_manager()
        session = await session_manager.create_session(server)

        if self._default_session is None:
            self._default_session = session

        logger.info(f"Connected to MCP server: {server.name}")
        return session

    async def disconnect(self, session: McpSession | None = None) -> None:
        """Disconnect from an MCP server.

        Args:
            session: Session to disconnect (uses default if None)

        Example:
            >>> await manager.disconnect(session)
        """
        session = session or self._default_session
        if session is None:
            return

        session_manager = self._get_session_manager()
        await session_manager.close_session(session)

        if session == self._default_session:
            self._default_session = None

        logger.info(f"Disconnected from MCP server: {session.server.name}")

    # Tool Execution

    async def execute_tool(
        self, tool_name: str, parameters: dict[str, Any], session: McpSession | None = None,
    ) -> ToolResult:
        """Execute an MCP tool.

        Args:
            tool_name: Name of tool to execute
            parameters: Tool parameters
            session: Optional session (uses default if None)

        Returns:
            Tool execution result

        Example:
            >>> result = await manager.execute_tool(
            ...     "search",
            ...     {"query": "hello world"}
            ... )
        """
        session = session or self._default_session

        # Get tool from registry
        registry = self._get_tool_registry()
        tool = registry.get_tool(tool_name)

        # Create execution context
        execution = ToolExecution(
            execution_id="", tool=tool, parameters=parameters, session=session,  # Will be generated
        )
        execution.start()

        # Track with monitoring
        monitor = self._get_monitoring_provider()
        if monitor:
            span_id = await monitor.start_span(
                f"tool.{tool_name}", attributes={"tool": tool_name, "params": parameters},
            )

        try:
            # Execute tool
            provider = self._get_provider()
            result = await provider.execute_tool(tool, parameters, session)

            execution.complete(result)

            if monitor:
                await monitor.end_span(span_id, status="ok")
                await monitor.record_metric(
                    "tool_execution_time",
                    execution.duration_seconds() or 0,
                    tags={"tool": tool_name, "status": "success"},
                )

            return result

        except Exception as e:
            execution.fail(str(e))

            if monitor:
                await monitor.end_span(span_id, status="error")
                await monitor.record_error(e, {"tool": tool_name})

            raise

    def register_tool(self, tool: McpTool, handler: Any | None = None) -> None:
        """Register a tool.

        Args:
            tool: Tool definition
            handler: Optional handler function

        Example:
            >>> manager.register_tool(
            ...     McpTool(name="search", description="Search docs"),
            ...     handler=search_handler
            ... )
        """
        # Attach handler to tool if provided
        if handler and not tool.handler:
            tool.handler = handler

        registry = self._get_tool_registry()
        registry.register_tool(tool, handler)
        logger.info(f"Registered tool: {tool.name}")

    def list_tools(self) -> list[McpTool]:
        """List all registered tools.

        Returns:
            List of tools

        Example:
            >>> tools = manager.list_tools()
            >>> for tool in tools:
            ...     print(f"{tool.name}: {tool.description}")
        """
        registry = self._get_tool_registry()
        return registry.list_tools()

    # Resource Access

    async def get_resource(self, uri: str) -> Any:
        """Get a resource by URI.

        Args:
            uri: Resource URI (e.g., "config://app/database")

        Returns:
            Resource data

        Example:
            >>> config = await manager.get_resource("config://app/database")
            >>> users = await manager.get_resource("db://users?active=true")
        """
        provider = self._get_resource_provider()
        return await provider.get_resource(uri)

    async def list_resources(self, pattern: str) -> list[str]:
        """List resources matching a pattern.

        Args:
            pattern: URI pattern

        Returns:
            List of resource URIs

        Example:
            >>> uris = await manager.list_resources("db://users/*")
        """
        provider = self._get_resource_provider()
        return await provider.list_resources(pattern)

    def register_resource_scheme(self, scheme: str, handler: Any) -> None:
        """Register a resource scheme handler.

        Args:
            scheme: Scheme name (e.g., "db", "storage")
            handler: Scheme handler implementation

        Example:
            >>> manager.register_resource_scheme("db", DbSchemeHandler())
        """
        provider = self._get_resource_provider()
        provider.register_scheme(scheme, handler)
        logger.info(f"Registered resource scheme: {scheme}://")


# Global manager instance
_manager: McpManager | None = None


def get_mcp_manager() -> McpManager:
    """Get the global MCP manager.

    Returns:
        Global MCP manager instance

    Example:
        >>> manager = get_mcp_manager()
        >>> result = await manager.execute_tool("search", {"query": "hello"})
    """
    global _manager
    if _manager is None:
        _manager = McpManager()
    return _manager


def set_mcp_manager(manager: McpManager) -> None:
    """Set the global MCP manager.

    Args:
        manager: MCP manager instance

    Example:
        >>> custom_manager = McpManager(custom_container)
        >>> set_mcp_manager(custom_manager)
    """
    global _manager
    _manager = manager


__all__ = [
    "McpManager",
    "get_mcp_manager",
    "set_mcp_manager",
]
