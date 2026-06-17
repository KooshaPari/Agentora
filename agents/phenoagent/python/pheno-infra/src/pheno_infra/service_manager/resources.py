"""
Resource availability checks and simple monitoring.
"""

from __future__ import annotations

import asyncio
import logging
import socket
from datetime import datetime

from .models import ResourceStatus

logger = logging.getLogger(__name__)


class ResourcesMixin:
    async def check_resource(self, name: str) -> bool:
        config = self.resources.get(name)  # type: ignore[attr-defined]
        if not config:
            return False
        available = await self._tcp_check(config.host, config.port)
        status = self.resource_status.get(name)  # type: ignore[attr-defined]
        if not status:
            status = ResourceStatus(name=name, available=available, last_check=datetime.now())
            self.resource_status[name] = status  # type: ignore[attr-defined]
        status.available = available
        status.last_check = datetime.now()
        status.error_message = (
            None if available else f"Connection failed to {config.host}:{config.port}"
        )
        logger.debug(
            "Resource '%s' availability: %s (host=%s port=%s)",
            name,
            available,
            config.host,
            config.port,
        )
        return available

    async def check_all_resources(self) -> dict[str, bool]:
        results: dict[str, bool] = {}
        for name in self.resources:  # type: ignore[attr-defined]
            results[name] = await self.check_resource(name)
        return results

    async def _tcp_check(self, host: str, port: int) -> bool:
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._blocking_tcp_check, host, port)
        except Exception:
            return False

    @staticmethod
    def _blocking_tcp_check(host: str, port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1.0)
            try:
                sock.connect((host, port))
                return True
            except OSError:
                return False
