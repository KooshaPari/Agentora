"""
Health check middleware.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from .templates import TemplateRenderer

logger = logging.getLogger(__name__)


class HealthCheckMiddleware:
    """
    Route to healthy services or fallback based on registered checks.
    """

    def __init__(self, renderer: TemplateRenderer, check_interval: float = 5.0):
        self.renderer = renderer
        self.check_interval = check_interval
        self.service_health: dict[str, bool] = {}
        self.health_callbacks: dict[str, Callable] = {}

    def register_health_check(self, service_name: str, health_check_fn: Callable[[], bool]):
        self.health_callbacks[service_name] = health_check_fn

    def unregister_health_check(self, service_name: str) -> None:
        """
        Unregister a health check for a service if it exists.
        """
        self.health_callbacks.pop(service_name, None)
        self.service_health.pop(service_name, None)

    async def check_health(self, service_name: str) -> bool:
        health_fn = self.health_callbacks.get(service_name)
        if not health_fn:
            logger.warning("No health check registered for %s", service_name)
            return False
        try:
            if asyncio.iscoroutinefunction(health_fn):
                is_healthy = await health_fn()
            else:
                loop = asyncio.get_event_loop()
                is_healthy = await loop.run_in_executor(None, health_fn)
            self.service_health[service_name] = is_healthy
            return is_healthy
        except Exception as e:
            logger.exception("Health check failed for %s: %s", service_name, e)
            self.service_health[service_name] = False
            return False

    def is_healthy(self, service_name: str) -> bool:
        return self.service_health.get(service_name, False)
