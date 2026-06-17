"""
Tool metadata resource scheme.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from .base import ResourceSchemeHandler

if TYPE_CHECKING:
    from ..template_engine import ResourceContext


class ToolsResourceScheme(ResourceSchemeHandler):
    """Handler for tools:// resources - tool information."""

    def __init__(self):
        super().__init__("tools")

    async def handle_request(self, context: ResourceContext) -> dict[str, Any]:
        """
        Default to listing tools.
        """
        return await self.list_tools(context)

    async def get_tool_info(self, context: ResourceContext) -> dict[str, Any]:
        """
        Get detailed information about a specific tool.
        """
        tool_name = context.get_parameter("tool_name")

        if not tool_name:
            return {"error": "tool_name parameter is required"}

        available_tools = context.get_server_info("available_tools", {})
        tool_info = available_tools.get(tool_name)

        if not tool_info:
            return {"error": f"Tool '{tool_name}' not found"}

        tool_stats = context.get_server_info("tool_usage_stats", {})
        usage_stats = tool_stats.get(tool_name, {})

        return {
            "tool": {
                "name": tool_name,
                "description": tool_info.get("description", ""),
                "schema": tool_info.get("input_schema", {}),
                "tags": tool_info.get("tags", []),
                "enabled": tool_info.get("enabled", True),
                "annotations": tool_info.get("annotations", {}),
            },
            "usage": {
                "executions": usage_stats.get("executions", 0),
                "last_used": usage_stats.get("last_used"),
                "average_duration_ms": usage_stats.get("average_duration_ms", 0),
                "success_rate": usage_stats.get("success_rate", 1.0),
            },
            "timestamp": int(time.time()),
        }

    async def list_tools(self, context: ResourceContext) -> dict[str, Any]:
        """
        List all available tools with optional filtering.
        """
        domain = context.get_parameter("domain")
        enabled_only = context.get_parameter("enabled_only", "true").lower() == "true"

        available_tools = context.get_server_info("available_tools", {})
        tools_by_domain = context.get_server_info("tools_by_domain", {})

        filtered_tools = []
        for tool_name, tool_info in available_tools.items():
            if enabled_only and not tool_info.get("enabled", True):
                continue

            if domain:
                tool_domains = tools_by_domain.get(tool_name, [])
                if domain not in tool_domains:
                    continue

            filtered_tools.append(
                {
                    "name": tool_name,
                    "description": tool_info.get("description", ""),
                    "domains": tools_by_domain.get(tool_name, []),
                    "tags": tool_info.get("tags", []),
                    "enabled": tool_info.get("enabled", True),
                },
            )

        filtered_tools.sort(key=lambda entry: entry["name"])

        return {
            "tools": filtered_tools,
            "total": len(filtered_tools),
            "domain_filter": domain,
            "enabled_only": enabled_only,
            "available_domains": list(tools_by_domain.keys()),
            "timestamp": int(time.time()),
        }


__all__ = ["ToolsResourceScheme"]
