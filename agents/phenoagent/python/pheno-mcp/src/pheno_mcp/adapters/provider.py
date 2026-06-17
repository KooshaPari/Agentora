"""In-Memory MCP Provider.

Simple in-memory implementation of McpProvider for testing and development. For
production, replace with HTTP-based or other real implementation.
"""

import logging
from typing import Any

from pheno.mcp.types import McpServer, McpSession, McpTool, SessionStatus, ToolResult
from pheno.ports.mcp import McpProvider

logger = logging.getLogger(__name__)


class InMemoryMcpProvider(McpProvider):
    """In-memory MCP provider implementation.

    Stores sessions and tools in memory. Useful for testing and development.

    Example:
        >>> provider = InMemoryMcpProvider()
        >>> session = await provider.connect(server)
        >>> result = await provider.execute_tool(tool, {"param": "value"})
    """

    def __init__(self):
        self._sessions: dict[str, McpSession] = {}
        self._tools: dict[str, McpTool] = {}

    async def connect(self, server: McpServer) -> McpSession:
        """
        Connect to an MCP server (simulated).
        """
        session = McpSession(
            session_id="", server=server, status=SessionStatus.CONNECTED,  # Will be auto-generated
        )

        self._sessions[session.session_id] = session
        logger.info(f"Connected to MCP server: {server.name}")

        return session

    async def disconnect(self, session: McpSession) -> None:
        """
        Disconnect from an MCP server.
        """
        if session.session_id in self._sessions:
            session.status = SessionStatus.DISCONNECTED
            del self._sessions[session.session_id]
            logger.info(f"Disconnected from MCP server: {session.server.name}")

    async def execute_tool(
        self, tool: McpTool, params: dict[str, Any], session: McpSession | None = None,
    ) -> ToolResult:
        """
        Execute an MCP tool.
        """
        # If tool has a handler, execute it
        if tool.handler:
            try:
                # Check if handler is async
                import inspect

                if inspect.iscoroutinefunction(tool.handler):
                    output = await tool.handler(**params)
                else:
                    output = tool.handler(**params)

                return ToolResult(
                    output=output, success=True, metadata={"tool": tool.name, "params": params},
                )
            except Exception as e:
                logger.exception(f"Tool execution failed: {e}")
                # Re-raise the exception so it can be caught by the manager
                raise

        # Default: return echo of parameters
        return ToolResult(
            output={"echo": params}, success=True, metadata={"tool": tool.name, "params": params},
        )

    async def list_tools(self, session: McpSession) -> list[McpTool]:
        """
        List available tools.
        """
        return list(self._tools.values())

    async def get_server_info(self, session: McpSession) -> dict[str, Any]:
        """
        Get server information.
        """
        return {
            "name": session.server.name,
            "url": session.server.url,
            "version": "1.0.0",
            "provider": "InMemoryMcpProvider",
        }

    def is_connected(self, session: McpSession) -> bool:
        """
        Check if session is connected.
        """
        return session.session_id in self._sessions and session.status == SessionStatus.CONNECTED

    def register_tool(self, tool: McpTool) -> None:
        """
        Register a tool (helper method).
        """
        self._tools[tool.name] = tool


__all__ = ["InMemoryMcpProvider"]
