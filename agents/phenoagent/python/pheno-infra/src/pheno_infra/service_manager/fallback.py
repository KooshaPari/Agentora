"""
Fallback server and smart proxy orchestration.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class FallbackMixin:
    enable_fallback_layer: bool = True
    _fallback_started: bool = False
    _proxy_started: bool = False

    async def _start_fallback_layer(self) -> None:
        try:
            from pheno.infra.utils.identity import (
                base_ports_from_env,
                get_project_id,
                stable_offset,
            )

            from ..fallback_site import FallbackServer
            from ..fallback_site.admin_client import FallbackAdminClient
            from ..port_allocator import SmartPortAllocator
            from ..port_registry import PortRegistry
            from ..proxy_gateway import ProxyServer

            project_id = get_project_id()
            base_fb, base_px = base_ports_from_env()
            offset = stable_offset(project_id, modulo=50)
            preferred_fallback = base_fb + offset
            preferred_proxy = base_px + offset

            registry = PortRegistry()
            # Detect an existing shared fallback (not ours)
            shared_fallback_port: int | None = None
            for name, info in registry.get_all_services().items():
                if name.startswith("fallback:") and not name.endswith(f":{project_id}"):
                    shared_fallback_port = info.assigned_port
                    break

            allocator = SmartPortAllocator(registry=registry)

            if shared_fallback_port:
                # Reuse shared fallback; do not start local fallback server
                fallback_port = shared_fallback_port
                self.fallback_server = None
                self._fallback_started = False
                self._fallback_is_remote = True  # type: ignore[attr-defined]
                self._fallback_admin_client = FallbackAdminClient(port=fallback_port)  # type: ignore[attr-defined]
                logger.info("Using shared fallback server on port %s", fallback_port)
            else:
                # Allocate and start our own fallback server
                fallback_port = allocator.allocate_port(
                    f"fallback:{project_id}", preferred_fallback,
                )
                self.fallback_server = FallbackServer(port=fallback_port)
                self.fallback_server.service_manager = self  # type: ignore[attr-defined]
                await self.fallback_server.start()
                self._fallback_started = True
                self._fallback_is_remote = False  # type: ignore[attr-defined]
                logger.info("Fallback server started on port %s", fallback_port)

            # Always allocate a per-project proxy port
            proxy_port = allocator.allocate_port(f"proxy:{project_id}", preferred_proxy)
            self.proxy_server = ProxyServer(
                proxy_port=proxy_port,
                fallback_port=fallback_port,
                fallback_server=self.fallback_server,
            )
            await self.proxy_server.start()
            self._proxy_started = True
            logger.info("Smart proxy started on port %s", proxy_port)
        except Exception as e:
            logger.warning("Failed to start fallback layer: %s", e)
            self.enable_fallback_layer = False

    async def _configure_service_fallback(self, name, config, port):
        if not self._proxy_started or not getattr(self, "fallback_server", None):
            return
        try:
            from pheno.infra.utils.identity import get_project_id

            tenant_id = get_project_id()
        except Exception:
            tenant_id = None
        self.proxy_server.add_upstream(config.path_prefix, port, tenant=tenant_id)  # type: ignore[attr-defined]

        status = self.service_status.get(name)
        if status:
            if getattr(self, "_fallback_is_remote", False):
                try:
                    from pheno.infra.utils.identity import get_project_id

                    tenant = get_project_id()
                    client = getattr(self, "_fallback_admin_client", None)
                    if client:
                        client.update_status(
                            tenant=tenant,
                            service_name=config.name,
                            status_message="Service is starting...",
                            port=port,
                            pid=status.pid,
                            uptime="0s",
                            health_status="Starting",
                            state="starting",
                            steps=[
                                {"text": "Allocating port", "status": "completed"},
                                {"text": "Starting process", "status": "active"},
                                {"text": "Configuring tunnel", "status": "pending"},
                                {"text": "Health check", "status": "pending"},
                            ],
                        )
                except Exception:
                    logger.debug("Remote fallback status update failed", exc_info=True)
            else:
                # Local fallback server path
                self.fallback_server.set_page(page_type=config.fallback_page, service_name=config.name, refresh_interval=config.fallback_refresh_interval, message=config.fallback_message)  # type: ignore[attr-defined]
                self.fallback_server.update_service_status(  # type: ignore[attr-defined]
                    service_name=config.name,
                    status_message="Service is starting...",
                    port=port,
                    pid=status.pid,
                    uptime="0s",
                    health_status="Starting",
                    state="starting",
                    steps=[
                        {"text": "Allocating port", "status": "completed"},
                        {"text": "Starting process", "status": "active"},
                        {"text": "Configuring tunnel", "status": "pending"},
                        {"text": "Health check", "status": "pending"},
                    ],
                )
        logger.info("Configured fallback for %s at path %s", name, config.path_prefix)

    async def _stop_fallback_layer(self) -> None:
        """
        Stop proxy/fallback servers and unregister port ownership for this project.
        """
        try:
            # Stop servers first
            if getattr(self, "_proxy_started", False) and getattr(self, "proxy_server", None):
                try:
                    await self.proxy_server.stop()  # type: ignore[attr-defined]
                except Exception:
                    logger.debug("Proxy stop encountered an error", exc_info=True)
                self._proxy_started = False
            if getattr(self, "_fallback_started", False) and getattr(self, "fallback_server", None):
                try:
                    await self.fallback_server.stop()  # type: ignore[attr-defined]
                except Exception:
                    logger.debug("Fallback stop encountered an error", exc_info=True)
                self._fallback_started = False

            # Unregister ports in the registry
            try:
                from pheno.infra.utils.identity import get_project_id

                from ..port_registry import PortRegistry

                registry = PortRegistry()
                project_id = get_project_id()
                registry.unregister_service(f"fallback:{project_id}")
                registry.unregister_service(f"proxy:{project_id}")
            except Exception:
                logger.debug("Registry cleanup skipped", exc_info=True)
        except Exception:
            logger.debug("Error during fallback layer shutdown", exc_info=True)
