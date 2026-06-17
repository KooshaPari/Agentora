"""
System information resource scheme.
"""

from __future__ import annotations

import os
import platform
import time
from typing import TYPE_CHECKING, Any

from .base import ResourceSchemeHandler
from .common import LOGGER, PSUTIL_AVAILABLE, psutil

if TYPE_CHECKING:
    from ..template_engine import ResourceContext


class SystemResourceScheme(ResourceSchemeHandler):
    """Handler for system:// resources - system information."""

    def __init__(self):
        super().__init__("system")

    async def handle_request(self, context: ResourceContext) -> dict[str, Any]:
        """
        Fallback handler proxies to status.
        """
        return await self.get_status(context)

    async def get_status(self, context: ResourceContext) -> dict[str, Any]:
        """
        Get system status information.
        """
        try:
            if not PSUTIL_AVAILABLE:
                return {
                    "system": {
                        "platform": platform.platform(),
                        "python_version": platform.python_version(),
                        "architecture": platform.architecture()[0],
                        "hostname": platform.node(),
                    },
                    "process": {
                        "pid": os.getpid(),
                    },
                    "error": "psutil not available - install with 'pip install psutil' for detailed system info",
                    "timestamp": int(time.time()),
                }

            assert psutil is not None  # For type checkers

            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()

            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            process = psutil.Process(os.getpid())
            process_memory = process.memory_info()

            return {
                "system": {
                    "platform": platform.platform(),
                    "python_version": platform.python_version(),
                    "architecture": platform.architecture()[0],
                    "hostname": platform.node(),
                },
                "cpu": {
                    "count": cpu_count,
                    "usage_percent": cpu_percent,
                    "load_average": os.getloadavg() if hasattr(os, "getloadavg") else None,
                },
                "memory": {
                    "total_bytes": memory.total,
                    "available_bytes": memory.available,
                    "used_bytes": memory.used,
                    "usage_percent": memory.percent,
                },
                "disk": {
                    "total_bytes": disk.total,
                    "free_bytes": disk.free,
                    "used_bytes": disk.used,
                    "usage_percent": (disk.used / disk.total) * 100 if disk.total else None,
                },
                "process": {
                    "pid": os.getpid(),
                    "memory_rss_bytes": process_memory.rss,
                    "memory_vms_bytes": process_memory.vms,
                    "threads": process.num_threads(),
                    "cpu_percent": process.cpu_percent(),
                    "create_time": process.create_time(),
                },
                "timestamp": int(time.time()),
            }
        except Exception as exc:  # pragma: no cover - defensive logging
            LOGGER.error("Error getting system status: %s", exc)
            return {"error": str(exc), "timestamp": int(time.time())}

    async def get_environment(self, context: ResourceContext) -> dict[str, Any]:
        """
        Get environment variables (filtered for security).
        """
        safe_prefixes = [
            "PATH",
            "HOME",
            "USER",
            "SHELL",
            "LANG",
            "LC_",
            "PYTHON",
            "PIP",
            "NODE",
            "NPM",
            "HTTP",
            "HTTPS",
            "MCP_",
            "FASTMCP_",
            "ZEN_",
            "HOST",
            "PORT",
        ]

        safe_env: dict[str, Any] = {}
        for key, value in os.environ.items():
            if any(key.startswith(prefix) for prefix in safe_prefixes):
                if any(token in key for token in ("TOKEN", "KEY", "SECRET")):
                    safe_env[key] = "***MASKED***"
                else:
                    safe_env[key] = value

        return {
            "environment": safe_env,
            "total_vars": len(os.environ),
            "shown_vars": len(safe_env),
            "timestamp": int(time.time()),
        }


__all__ = ["SystemResourceScheme"]
