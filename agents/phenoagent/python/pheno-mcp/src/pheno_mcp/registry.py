"""
Generic MCP Tools Registry

Provides a base registry class for managing MCP tool adapters.
This is a reusable infrastructure component extracted from atoms_mcp-old.

Pattern extracted:
- Centralized tool adapter registration
- Port injection (database, auth, etc.)
- Adapter lifecycle management
- Clean interface for server initialization

Usage:
    class MyToolsRegistry(MCPToolsRegistry):
        def __init__(self, database_port, auth_port):
            super().__init__(database_port, auth_port)

            # Register your adapters
            self.entity_adapter = EntityToolAdapter(database_port, auth_port)
            self.query_adapter = QueryToolAdapter(database_port)

        def get_adapters(self):
            return [
                self.entity_adapter,
                self.query_adapter,
            ]
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fastmcp import FastMCP


class MCPToolsRegistry(ABC):
    """
    Base class for MCP tool adapter registries.

    This class provides a standard pattern for:
    1. Initializing tool adapters with required ports
    2. Managing adapter lifecycle
    3. Providing a clean registration interface

    Subclasses should:
    1. Initialize their specific adapters in __init__
    2. Implement get_adapters() to return list of adapters
    3. Optionally override register_all() for custom registration logic
    """

    def __init__(self, **ports: Any):
        """
        Initialize registry with dependency injection ports.

        Args:
            **ports: Named ports (database_port, auth_port, etc.)
        """
        self.ports = ports

    @abstractmethod
    def get_adapters(self) -> list[Any]:
        """
        Get all tool adapters managed by this registry.

        Returns:
            List of tool adapter instances
        """

    def register_all(self, mcp: FastMCP) -> None:
        """
        Register all tool adapters with the MCP server.

        This method calls register() on each adapter returned by get_adapters().
        Override this method if you need custom registration logic.

        Args:
            mcp: FastMCP server instance
        """
        for adapter in self.get_adapters():
            if hasattr(adapter, "register"):
                adapter.register(mcp)


class SimpleMCPToolsRegistry(MCPToolsRegistry):
    """
    Simple registry implementation that stores adapters in a list.

    This is a concrete implementation for cases where you don't need
    custom logic - just add adapters and register them.

    Usage:
        registry = SimpleMCPToolsRegistry(
            database_port=db_port,
            auth_port=auth_port
        )
        registry.add_adapter(EntityToolAdapter(db_port, auth_port))
        registry.add_adapter(QueryToolAdapter(db_port))
        registry.register_all(mcp)
    """

    def __init__(self, **ports: Any):
        """Initialize with ports and empty adapter list."""
        super().__init__(**ports)
        self._adapters: list[Any] = []

    def add_adapter(self, adapter: Any) -> None:
        """
        Add an adapter to the registry.

        Args:
            adapter: Tool adapter instance to register
        """
        self._adapters.append(adapter)

    def get_adapters(self) -> list[Any]:
        """
        Get all registered adapters.

        Returns:
            List of tool adapter instances
        """
        return self._adapters
