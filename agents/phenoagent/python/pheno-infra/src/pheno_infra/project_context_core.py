"""
Project Infrastructure Context - Lightweight project-scoped infrastructure management.

This module provides a small wrapper around ``ServiceInfraManager`` that makes it easy to
allocate ports, manage tunnels, hook into the smart proxy/fallback stack, and export
project-specific environment variables without running a long-lived daemon.
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Self

from .fallback_site.config_manager import FallbackConfigManager, FallbackPageConfig
from .proxy_gateway.server.core import ProxyServer
from .resource_coordinator import (
    LifecycleRule,
    ResourceCoordinator,
    ResourcePolicy,
)
from .resource_reference_cache import ResourceReuseStrategy
from .service_infra import ServiceInfraManager

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from .global_registry import ResourceMode

from .project_context_services import ServiceHelpers
from .project_context_proxy import ProxyHelpers

logger = logging.getLogger(__name__)


class ProjectInfraContext(ServiceHelpers, ProxyHelpers):
    """
    Project-scoped infrastructure context.

    Features provided in Phase 2:
    - Project-aware port allocation with metadata propagation
    - Convenience helpers for tunnel management
    - Optional reverse-proxy wiring with per-project routing
    - Environment-variable export for downstream processes
    - Structured logging payloads for metrics/observability
    """

    DEFAULT_ROUTING_TEMPLATE: dict[str, Any] = {
        "enabled": True,
        "host": "localhost",
        "path_template": "/{project}/{service}",
    }

    def __init__(
        self,
        project_name: str,
        *,
        domain: str = "kooshapari.com",
        config_dir: str | None = None,
        enable_proxy: bool = True,
        proxy_port: int = 9100,
        fallback_port: int = 9000,
        routing_template: dict[str, Any] | None = None,
    ) -> None:
        self.project_name = project_name
        self.domain = domain
        self.config_dir = config_dir
        self.enable_proxy = enable_proxy
        self.proxy_port = proxy_port
        self.fallback_port = fallback_port

        fallback_config_dir = Path(config_dir).expanduser() if config_dir else None
        self.fallback_config_manager = FallbackConfigManager(fallback_config_dir)

        template = dict(self.DEFAULT_ROUTING_TEMPLATE)
        if routing_template:
            template.update(routing_template)
        self._routing_template = template

        self._auto_route_disabled_services: set[str] = set()
        self._auto_registered_routes: dict[str, str] = {}

        self.service_infra = ServiceInfraManager(domain=domain, config_dir=config_dir)
        try:
            self.service_infra.project_id = project_name  # type: ignore[attr-defined]
        except Exception:
            pass

        self.resource_coordinator = ResourceCoordinator(
            instance_id=f"{project_name}-{os.getpid()}",
            project_name=project_name,
        )
        self._sync_await(self.resource_coordinator.initialize())

        self.proxy_server: ProxyServer | None = None
        self._proxy_started = False

        self._project_services: set[str] = set()
        logger.info(
            "Initialized ProjectInfraContext", extra=self._log_payload(event="init")
        )

    @property
    def registry(self):
        return self.service_infra.registry

    @property
    def allocator(self):
        return self.service_infra.allocator

    @property
    def tunnel_manager(self):
        return self.service_infra.tunnel_manager

    def __enter__(self) -> Self:
        if self.enable_proxy:
            self.start_proxy()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.cleanup_project_services()
        if self.enable_proxy:
            self.stop_proxy()
        self._sync_await(self.resource_coordinator.shutdown())
        logger.info(
            "Closed ProjectInfraContext", extra=self._log_payload(event="close")
        )

    def _log_payload(self, **extra: Any) -> dict[str, Any]:
        payload = {
            "project": self.project_name,
            "domain": self.domain,
        }
        payload.update(extra)
        return payload

    def _format_route_path(
        self,
        service_name: str,
        path_or_template: str | None,
    ) -> str:
        template = path_or_template or self._routing_template.get(
            "path_template",
            "/{project}/{service}",
        )
        if "{" in template:
            path = template.format(
                project=self.project_name,
                service=service_name,
                scoped_service=f"{self.project_name}-{service_name}",
                service_slug=service_name.replace("_", "-"),
            )
        else:
            path = template
        if not path.startswith("/"):
            path = f"/{path}"
        return path.rstrip("/") or "/"

    @staticmethod
    def _run_async(coro: asyncio.coroutines) -> None:
        """Run an awaitable, handling the case where no loop is running."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(coro)
        else:
            loop.create_task(coro)

    @staticmethod
    def _sync_await(coro: asyncio.coroutines) -> Any:
        """Synchronously wait for an awaitable and return its result."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)
        raise RuntimeError(
            "Synchronous ProjectInfraContext helpers cannot be used inside an active event loop.",
        )
