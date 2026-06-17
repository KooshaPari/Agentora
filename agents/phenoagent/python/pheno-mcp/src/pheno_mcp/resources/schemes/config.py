"""
Configuration resource scheme.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from .base import ResourceSchemeHandler

if TYPE_CHECKING:
    from ..template_engine import ResourceContext


class ConfigResourceScheme(ResourceSchemeHandler):
    """Handler for config:// resources - configuration information."""

    def __init__(self):
        super().__init__("config")

    async def handle_request(self, context: ResourceContext) -> dict[str, object]:
        """
        Default to server config when direct call.
        """
        return await self.get_server_config(context)

    async def get_server_config(self, context: ResourceContext) -> dict[str, object]:
        """
        Get server configuration.
        """
        section = context.get_parameter("section", "all")

        config: dict[str, object] = {}

        if section in ["all", "server"]:
            config["server"] = {
                "name": context.get_server_info("name"),
                "host": context.get_server_info("host"),
                "port": context.get_server_info("port"),
                "base_path": context.get_server_info("base_path"),
                "public_url": context.get_server_info("public_url"),
                "log_level": context.get_server_info("log_level"),
            }

        if section in ["all", "auth"]:
            config["auth"] = {
                "enabled": context.get_server_info("auth_enabled"),
                "provider": context.get_server_info("auth_provider"),
                "user_authenticated": context.is_authenticated(),
            }

        if section in ["all", "tools"]:
            config["tools"] = {
                "total": context.get_server_info("tools_count"),
                "disabled": context.get_server_info("disabled_tools", []),
                "domains": context.get_server_info("tools_by_domain", {}),
            }

        if section in ["all", "middleware"]:
            config["middleware"] = context.get_server_info("middleware_config", {})

        return {
            "config": config,
            "section": section,
            "timestamp": int(time.time()),
        }

    async def get_tool_config(self, context: ResourceContext) -> dict[str, object]:
        """
        Get tool-specific configuration.
        """
        tool_name = context.get_parameter("tool")

        if not tool_name:
            return {"error": "tool parameter is required"}

        tools = context.get_server_info("available_tools", {})
        tool_info = tools.get(tool_name)

        if not tool_info:
            return {"error": f"Tool '{tool_name}' not found"}

        return {
            "tool": tool_name,
            "config": tool_info,
            "timestamp": int(time.time()),
        }


__all__ = ["ConfigResourceScheme"]
