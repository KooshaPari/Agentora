"""
Core proxy server orchestration.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from aiohttp import ClientSession, ClientTimeout, web

from pheno.infra.utils.aiohttp_otel import apply_aiohttp_otel_kwargs
from pheno.infra.utils.health import check_tcp_health

from ...middleware import KInfraMiddleware, ServiceState, create_middleware
from .admin import AdminAPI
from .events import log_health_transition
from .health import HealthMonitor
from .registry import UpstreamRegistry
from .router import RequestRouter

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


class ProxyServer:
    """
    Health-aware reverse proxy with automatic fallback.
    """

    def __init__(
        self,
        proxy_port: int = 9100,
        fallback_port: int = 9000,
        default_upstream_port: int = 8000,
        fallback_server: object | None = None,
        middleware: KInfraMiddleware | None = None,
        templates_dir: Path | None = None,
    ):
        self.proxy_port = proxy_port
        self.fallback_port = fallback_port
        self.default_upstream_port = default_upstream_port
        self.fallback_server = fallback_server
        self.middleware = middleware or create_middleware(templates_dir=templates_dir)

        self.session: ClientSession | None = None
        self.runner: web.AppRunner | None = None
        self.site: web.TCPSite | None = None

        self._app = web.Application()
        self._shutdown = False

        self._registry = UpstreamRegistry(
            on_register=self._register_health_check,
            on_unregister=self._unregister_health_check,
        )
        self._router = RequestRouter(
            self._registry,
            session_getter=lambda: self.session,
            fallback_port=self.fallback_port,
            fallback_server=self.fallback_server,
            middleware=self.middleware,
        )
        self._admin_api = AdminAPI(self._registry)
        self._health_monitor = HealthMonitor(
            self._registry,
            self.fallback_server,
            on_transition=self._handle_health_transition,
        )

        self._configure_routes()
        logger.info("ProxyServer initialized on port %s", proxy_port)

    @property
    def app(self) -> web.Application:
        """
        Expose the aiohttp application for external customization.
        """
        return self._app

    def _configure_routes(self) -> None:
        self._app.router.add_post("/__admin__/tenant/upstream", self._admin_api.add_upstream)
        self._app.router.add_delete("/__admin__/tenant/upstream", self._admin_api.remove_upstream)
        self._app.router.add_get("/__admin__/tenant/upstreams", self._admin_api.list_upstreams)
        self._app.router.add_post("/__admin__/tenant/deregister", self._admin_api.deregister_tenant)
        self._app.router.add_route("*", "/{path:.*}", self._router.handle_request)

    def add_upstream(
        self,
        path_prefix: str,
        port: int,
        host: str = "localhost",
        service_name: str | None = None,
        tenant: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Register an upstream service.
        """
        self._registry.add_upstream(
            path_prefix,
            host=host,
            port=port,
            service_name=service_name,
            tenant=tenant,
            metadata=metadata,
        )
        logger.info(
            "Added upstream: %s -> http://%s:%s tenant=%s", path_prefix, host, port, tenant or "-",
        )

    @property
    def health_snapshot(self) -> dict[str, Any]:
        """Expose the current registry snapshot for dashboards/consumers."""

        return self._registry.snapshot()

    def remove_upstream(self, path_prefix: str) -> bool:
        removed = self._registry.remove_upstream(path_prefix)
        if removed:
            logger.info("Removed upstream for prefix: %s", path_prefix)
        return removed

    def set_service_starting(self, service_name: str, **kwargs) -> None:
        if self.middleware and self.middleware.loading:
            self.middleware.loading.set_service_state(service_name, ServiceState.STARTING, **kwargs)

    def set_service_running(self, service_name: str, **kwargs) -> None:
        if self.middleware and self.middleware.loading:
            self.middleware.loading.set_service_state(service_name, ServiceState.RUNNING, **kwargs)

    def set_service_error(self, service_name: str, **kwargs) -> None:
        if self.middleware and self.middleware.loading:
            self.middleware.loading.set_service_state(service_name, ServiceState.ERROR, **kwargs)

    def enable_maintenance(
        self, message: str | None = None, estimated_duration: str | None = None,
    ) -> None:
        if self.middleware and self.middleware.maintenance:
            self.middleware.maintenance.enable(message, estimated_duration)

    def disable_maintenance(self) -> None:
        if self.middleware and self.middleware.maintenance:
            self.middleware.maintenance.disable()

    def _handle_health_transition(self, state: dict[str, Any], previous: bool | None) -> None:
        """Emit structured health transition events for observability."""

        log_health_transition(state, previous)

    async def start(self) -> None:
        """
        Start the proxy server.
        """
        try:
            timeout = ClientTimeout(total=30)
            self.session = ClientSession(**apply_aiohttp_otel_kwargs({"timeout": timeout}))
            self.runner = web.AppRunner(self._app)
            await self.runner.setup()
            self.site = web.TCPSite(self.runner, "127.0.0.1", self.proxy_port)
            await self.site.start()
            logger.info("Smart proxy server started on http://127.0.0.1:%s", self.proxy_port)
            self._health_monitor.start()
        except Exception as exc:
            logger.exception("Failed to start proxy server: %s", exc)
            raise

    async def stop(self) -> None:
        """
        Stop the proxy server and cleanup resources.
        """
        self._shutdown = True
        await self._health_monitor.stop()

        if self.session:
            await self.session.close()
            self.session = None

        if self.site:
            await self.site.stop()
            logger.info("Proxy server site stopped")
            self.site = None

        if self.runner:
            await self.runner.cleanup()
            logger.info("Proxy server runner cleaned up")
            self.runner = None

    def _register_health_check(self, service_name: str, upstream) -> None:
        if self.middleware and self.middleware.health_check:
            self.middleware.health_check.register_health_check(
                service_name,
                lambda: check_tcp_health(
                    upstream.host, upstream.port, upstream.health_check_timeout,
                ),
            )

    def _unregister_health_check(self, service_name: str) -> None:
        if self.middleware and self.middleware.health_check:
            try:
                self.middleware.health_check.unregister_health_check(service_name)  # type: ignore[attr-defined]
            except Exception:
                logger.debug(
                    "Unable to unregister health check for %s", service_name, exc_info=True,
                )


async def run_smart_proxy(
    proxy_port: int = 9100,
    fallback_port: int = 9000,
    upstreams: dict[str, int] | None = None,
) -> None:
    """
    Convenience helper to run the proxy server with basic configuration.
    """
    proxy = ProxyServer(proxy_port=proxy_port, fallback_port=fallback_port)
    if upstreams:
        for path_prefix, port in upstreams.items():
            proxy.add_upstream(path_prefix, port)
    await proxy.start()
    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Shutting down proxy server...")
        await proxy.stop()


__all__ = ["ProxyServer", "run_smart_proxy"]
