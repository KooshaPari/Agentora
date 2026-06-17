"""
KInfra middleware stack composition and factory.
"""

from __future__ import annotations

import logging

try:
    from aiohttp import web
except Exception:
    web = None  # type: ignore

from typing import TYPE_CHECKING

from .fallback import FallbackMiddleware, MaintenanceMiddleware
from .health import HealthCheckMiddleware
from .loading import LoadingMiddleware
from .templates import TemplateRenderer
from .types import MiddlewareConfig

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

logger = logging.getLogger(__name__)


class KInfraMiddleware:
    def __init__(self, config: MiddlewareConfig | None = None):
        if web is None:
            raise ImportError(
                "aiohttp is required for KInfraMiddleware. Install with: pip install aiohttp",
            )
        self.config = config or MiddlewareConfig()
        self.renderer = TemplateRenderer(self.config.templates_dir)
        self.loading = (
            LoadingMiddleware(self.renderer, timeout=self.config.loading_timeout)
            if self.config.enable_loading
            else None
        )
        self.fallback = FallbackMiddleware(self.renderer) if self.config.enable_fallback else None
        self.health_check = (
            HealthCheckMiddleware(self.renderer, check_interval=self.config.health_check_interval)
            if self.config.enable_health_check
            else None
        )
        self.maintenance = MaintenanceMiddleware(self.renderer)
        logger.info("KInfraMiddleware initialized")

    async def handle_request(
        self, request: web.Request, handler: Callable, service_name: str = "Service",
    ) -> web.Response:
        maintenance_response = await self.maintenance.handle(service_name)
        if maintenance_response:
            return maintenance_response
        if self.loading:
            loading_response = await self.loading.handle(request, service_name)
            if loading_response:
                return loading_response
        if self.health_check and not self.health_check.is_healthy(service_name):
            if self.fallback:
                return await self.fallback.handle_error(
                    503,
                    service_name=service_name,
                    message="Service is currently unavailable. Please try again in a few moments.",
                )
        try:
            return await handler(request)
        except web.HTTPException as e:  # type: ignore[attr-defined]
            if self.fallback:
                return await self.fallback.handle_error(
                    e.status_code,
                    service_name=service_name,
                    message=str(e.reason) if hasattr(e, "reason") else None,
                )
            raise
        except Exception as e:
            logger.error("Handler error: %s", e, exc_info=True)
            if self.fallback:
                return await self.fallback.handle_error(
                    500,
                    service_name=service_name,
                    message=f"An unexpected error occurred: {e!s}",
                )
            raise


def create_middleware(templates_dir: Path | None = None, **kwargs) -> KInfraMiddleware:
    from pathlib import Path

    config = MiddlewareConfig(
        templates_dir=templates_dir or Path(__file__).parent / "../templates/error_pages", **kwargs,
    )
    return KInfraMiddleware(config)
