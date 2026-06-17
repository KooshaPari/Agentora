"""
Monitoring loops and shutdown, plus aggregate status.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class MonitorMixin:
    async def _monitor_service_health(self, name: str):
        config = self.services.get(name)  # type: ignore[attr-defined]
        if not config:
            return
        while not self._shutdown:  # type: ignore[attr-defined]
            await asyncio.sleep(config.health_check_interval)
            status = self.service_status[name]  # type: ignore[attr-defined]
            if status.state != "running":
                continue
            proc = self.processes.get(name)  # type: ignore[attr-defined]
            if proc and proc.returncode is not None:
                logger.error("Service %s process died with code %s", name, proc.returncode)
                status.state = "error"
                if config.restart_on_failure and status.restart_count < config.max_restart_attempts:
                    status.restart_count += 1
                    logger.info(
                        "Restarting %s (attempt %d/%d)",
                        name,
                        status.restart_count,
                        config.max_restart_attempts,
                    )
                    await asyncio.sleep(config.restart_delay)
                    await self.start_service(name)  # type: ignore[misc]
                    continue
            if getattr(config, "health_check_url", None):
                healthy = await self._check_service_health(name)  # type: ignore[misc]
                if not healthy:
                    logger.warning("Health check failed for %s", name)

    async def monitor(self):
        logger.info("Starting continuous monitoring")
        for name in self.services:  # type: ignore[attr-defined]
            task = asyncio.create_task(self._monitor_service_health(name))
            self._monitor_tasks.append(task)  # type: ignore[attr-defined]
        if hasattr(self, "_monitor_resources"):
            task = asyncio.create_task(self._monitor_resources())  # type: ignore[misc]
            self._monitor_tasks.append(task)  # type: ignore[attr-defined]
        with contextlib.suppress(asyncio.CancelledError):
            await asyncio.sleep(float("inf"))

    async def shutdown(self):
        logger.info("Shutting down ServiceManager")
        self._shutdown = True  # type: ignore[attr-defined]
        for task in self._monitor_tasks:  # type: ignore[attr-defined]
            task.cancel()
        await asyncio.gather(*self._monitor_tasks, return_exceptions=True)  # type: ignore[attr-defined]
        for name in list(self.services.keys()):  # type: ignore[attr-defined]
            await self.stop_service(name)  # type: ignore[misc]
        # Stop fallback/proxy layer and unregister ports for this project
        try:
            if hasattr(self, "_stop_fallback_layer"):
                await self._stop_fallback_layer()  # type: ignore[misc]
        except Exception:
            logger.debug("Error during fallback/proxy shutdown", exc_info=True)
        logger.info("ServiceManager shutdown complete")

    def get_status(self) -> dict[str, Any]:
        return {
            "services": {
                name: {
                    "state": status.state,
                    "pid": status.pid,
                    "port": status.port,
                    "tunnel_url": status.tunnel_url,
                    "uptime": (
                        str(datetime.now() - status.started_at) if status.started_at else None
                    ),
                    "restart_count": status.restart_count,
                    "health_status": status.health_status,
                    "last_health_check": (
                        status.last_health_check.isoformat() if status.last_health_check else None
                    ),
                    "error_message": status.error_message,
                    "logs": status.logs[-50:] if status.logs else [],
                    "last_output": status.last_output,
                }
                for name, status in self.service_status.items()  # type: ignore[attr-defined]
            },
            "resources": {
                name: {
                    "available": status.available,
                    "last_check": status.last_check.isoformat() if status.last_check else None,
                    "error_message": status.error_message,
                }
                for name, status in self.resource_status.items()  # type: ignore[attr-defined]
            },
        }
