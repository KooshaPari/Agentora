"""
Zen MCP core resource scheme.
"""

from __future__ import annotations

import os
import platform
import time
from typing import TYPE_CHECKING, Any

from .base import ResourceSchemeHandler

if TYPE_CHECKING:
    from ..template_engine import ResourceContext


class ZenResourceScheme(ResourceSchemeHandler):
    """Handler for zen:// resources - core server information."""

    def __init__(self):
        super().__init__("zen")

    async def handle_request(self, context: ResourceContext) -> dict[str, Any]:
        """
        Default handler simply proxies to `get_status`.
        """
        return await self.get_status(context)

    async def get_status(self, context: ResourceContext) -> dict[str, Any]:
        """
        Get overall server status.
        """
        component = context.get_parameter("component", "all")

        status: dict[str, Any] = {
            "status": "healthy",
            "timestamp": int(time.time()),
            "uptime_seconds": context.get_server_info("uptime_seconds", 0),
            "version": context.get_server_info("version", "unknown"),
        }

        if component in ["all", "tools"]:
            status["tools"] = {
                "total": context.get_server_info("tools_count", 0),
                "enabled": context.get_server_info("enabled_tools", []),
                "disabled": context.get_server_info("disabled_tools", []),
            }

        if component in ["all", "auth"]:
            status["authentication"] = {
                "enabled": context.get_server_info("auth_enabled", False),
                "provider": context.get_server_info("auth_provider", "none"),
                "user_authenticated": context.is_authenticated(),
            }

        if component in ["all", "resources"]:
            status["resources"] = {
                "templates": context.get_server_info("resource_templates_count", 0),
                "cache_entries": context.get_server_info("resource_cache_entries", 0),
            }

        return status

    async def get_health(self, context: ResourceContext) -> dict[str, Any]:
        """
        Get detailed health information.
        """
        return {
            "status": "healthy",
            "checks": {
                "server": {"status": "pass", "details": "Server running normally"},
                "auth": {
                    "status": "pass" if context.get_server_info("auth_enabled") else "warn",
                    "details": (
                        "Authentication configured"
                        if context.get_server_info("auth_enabled")
                        else "No authentication"
                    ),
                },
                "tools": {
                    "status": "pass",
                    "details": f"{context.get_server_info('tools_count', 0)} tools available",
                },
            },
            "timestamp": int(time.time()),
        }

    async def get_info(self, context: ResourceContext) -> dict[str, Any]:
        """
        Get comprehensive server information.
        """
        return {
            "name": context.get_server_info("name", "Zen MCP Server"),
            "description": context.get_server_info("description", ""),
            "version": context.get_server_info("version", "unknown"),
            "fastmcp_enabled": context.get_server_info("fastmcp_enabled", True),
            "base_path": context.get_server_info("base_path", "/mcp"),
            "public_url": context.get_server_info("public_url", ""),
            "capabilities": {
                "tools": context.get_server_info("tools_count", 0),
                "resources": True,
                "prompts": True,
                "authentication": context.get_server_info("auth_enabled", False),
                "resource_templates": context.get_server_info("resource_templates_count", 0),
            },
            "runtime": {
                "python_version": platform.python_version(),
                "platform": platform.platform(),
                "pid": os.getpid(),
                "uptime_seconds": context.get_server_info("uptime_seconds", 0),
            },
        }


__all__ = ["ZenResourceScheme"]
