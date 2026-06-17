"""In-Memory Tool Registry.

Implementation of ToolRegistry for managing MCP tools. Uses BaseRegistry for common
functionality.
"""

import logging
from collections.abc import Callable
from typing import Any

from pheno.adapters.base_registry import BaseRegistry
from pheno.mcp.types import McpTool
from pheno.ports.mcp import ToolRegistry

logger = logging.getLogger(__name__)


class InMemoryToolRegistry(BaseRegistry[McpTool], ToolRegistry):
    """In-memory tool registry implementation.

    Stores tools and their handlers in memory.

    Example:
        >>> registry = InMemoryToolRegistry()
        >>> registry.register_tool(
        ...     McpTool(name="search", description="Search docs"),
        ...     handler=search_handler
        ... )
        >>> tool = registry.get_tool("search")
    """

    def __init__(self):
        self._tools: dict[str, McpTool] = {}
        self._handlers: dict[str, Callable] = {}
        self._categories: dict[str, list[str]] = {}  # category -> tool names

    def register_tool(self, tool: McpTool, handler: Callable | None = None) -> None:
        """
        Register a tool in the registry.
        """
        self._tools[tool.name] = tool

        if handler:
            self._handlers[tool.name] = handler
        elif tool.handler:
            self._handlers[tool.name] = tool.handler

        # Register in category
        if tool.category:
            if tool.category not in self._categories:
                self._categories[tool.category] = []
            if tool.name not in self._categories[tool.category]:
                self._categories[tool.category].append(tool.name)

        logger.info(f"Registered tool: {tool.name}")

    def unregister_tool(self, name: str) -> None:
        """
        Unregister a tool from the registry.
        """
        if name in self._tools:
            tool = self._tools[name]

            # Remove from category
            if tool.category and tool.category in self._categories:
                if name in self._categories[tool.category]:
                    self._categories[tool.category].remove(name)

            del self._tools[name]

            if name in self._handlers:
                del self._handlers[name]

            logger.info(f"Unregistered tool: {name}")

    def get_tool(self, name: str) -> McpTool:
        """
        Get a tool by name.
        """
        if name not in self._tools:
            raise ValueError(f"Tool not found: {name}")
        return self._tools[name]

    def has_tool(self, name: str) -> bool:
        """
        Check if a tool is registered.
        """
        return name in self._tools

    def list_tools(
        self, category: str | None = None, tags: list[str] | None = None,
    ) -> list[McpTool]:
        """
        List registered tools.
        """
        tools = list(self._tools.values())

        # Filter by category
        if category:
            tools = [t for t in tools if t.category == category]

        # Filter by tags
        if tags:
            tools = [t for t in tools if any(tag in t.tags for tag in tags)]

        return tools

    def get_tool_handler(self, name: str) -> Callable:
        """
        Get the handler function for a tool.
        """
        if name not in self._tools:
            raise ValueError(f"Tool not found: {name}")

        if name not in self._handlers:
            raise ValueError(f"Tool has no handler: {name}")

        return self._handlers[name]

    def list_categories(self) -> list[str]:
        """
        List all tool categories.
        """
        return list(self._categories.keys())

    def get_tool_metadata(self, name: str) -> dict[str, Any]:
        """
        Get metadata for a tool.
        """
        tool = self.get_tool(name)
        return {
            "name": tool.name,
            "description": tool.description,
            "category": tool.category,
            "tags": tool.tags,
            "version": tool.version,
            "parameters": tool.parameters,
            "metadata": tool.metadata,
            "has_handler": name in self._handlers,
        }

    def search_tools(self, query: str) -> list[McpTool]:
        """
        Search for tools by name or description.
        """
        query_lower = query.lower()
        results = []

        for tool in self._tools.values():
            if (
                query_lower in tool.name.lower()
                or query_lower in tool.description.lower()
                or any(query_lower in tag.lower() for tag in tool.tags)
            ):
                results.append(tool)

        return results


__all__ = ["InMemoryToolRegistry"]
