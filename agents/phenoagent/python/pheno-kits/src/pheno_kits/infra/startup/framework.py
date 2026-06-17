"""
Unified startup framework.

The :class:`UnifiedStartup` orchestrates end-to-end infrastructure startup for
projects. It handles cleanup, port allocation, resource management, tunnel
creation, and optional lifecycle hooks, allowing project entry points to stay
minimal and declarative.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from . import lifecycle

if TYPE_CHECKING:
    from ..kinfra import KInfra
    from ..resource_manager import ResourceManager
    from ..tunnel_sync import TunnelInfo
    from .config import StartupConfig
    from .lifecycle import CleanupReport, ResourceStatusRecord


class UnifiedStartup:
    """High-level orchestrator for project infrastructure startup."""

    def __init__(
        self,
        config: StartupConfig,
        *,
        logger: logging.Logger | None = None,
        ui: Any | None = None,
    ):
        self.config = config
        self.logger = logger or logging.getLogger(f"pheno.kits.infra.startup.{config.project_name}")
        self.ui = ui or self._resolve_ui()

        self.kinfra: KInfra | None = None
        self.service_name = lifecycle.build_service_identifier(config.project_name, suffix="service")
        self.port: int | None = None
        self.tunnel_info: TunnelInfo | None = None
        self.resource_manager: ResourceManager | None = None
        self.resource_status: dict[str, ResourceStatusRecord] = {}
        self.cleanup_report: CleanupReport | None = None
        self._shutdown = False

    async def startup(self) -> dict[str, Any]:
        """Bootstrap infrastructure according to :class:`StartupConfig`."""

        self.logger.info("Starting unified infrastructure bootstrap for %s", self.config.project_name)

        # 1. Pre-start cleanup
        self.cleanup_report = await lifecycle.cleanup_stale_infrastructure(
            self.config, logger=self.logger,
        )

        # 2. Instantiate KInfra
        self.kinfra = lifecycle.create_kinfra(self.config)
        self.logger.debug("KInfra ready for domain %s", self.config.domain)

        # 3. Allocate port for primary service
        self.port = await lifecycle.allocate_service_port(
            self.kinfra, self.service_name, self.config.preferred_port,
        )
        self.logger.info("Allocated port %s for service %s", self.port, self.service_name)

        # 4. Resolve resources
        resolution = await lifecycle.resolve_project_resources(
            self.config.project_name,
            self.config.resources,
            kinfra=self.kinfra,
            logger=self.logger,
        )
        self.resource_manager = resolution.manager
        self.resource_status = resolution.statuses

        # 5. Optional infrastructure extras
        await self._setup_optional_components()

        # 6. Create tunnel if requested
        if self.config.enable_tunnel:
            tunnel_domain = self._determine_tunnel_domain()
            self.tunnel_info = await lifecycle.establish_project_tunnel(
                self.kinfra,
                self.service_name,
                self.port,
                domain=tunnel_domain,
                logger=self.logger,
            )
            self.logger.info("Tunnel active at https://%s", self.tunnel_info.hostname)

        # 7. Invoke startup hook
        await lifecycle.run_lifecycle_hook(self.config.on_startup, self)

        status = self._build_status_payload()
        self._display_status(status)
        return status

    async def shutdown(self) -> None:
        """Tear down managed resources and trigger shutdown hooks."""

        if self._shutdown:
            return

        self._shutdown = True
        self.logger.info("Shutting down unified infrastructure for %s", self.config.project_name)

        if self.resource_manager:
            await self.resource_manager.stop_all()

        await lifecycle.run_lifecycle_hook(self.config.on_shutdown, self)

    def _determine_tunnel_domain(self) -> str | None:
        """Compute the desired tunnel domain."""
        if not self.config.enable_tunnel:
            return None
        if self.config.tunnel_subdomain:
            return f"{self.config.tunnel_subdomain}.{self.config.domain}".lower()
        return self.config.domain.lower()

    async def _setup_optional_components(self) -> None:
        """Placeholder for fallback and proxy configuration."""

        if self.config.enable_fallback:
            self.logger.debug("Fallback server setup deferred to later phase")

        if self.config.enable_proxy:
            self.logger.debug("Proxy server setup deferred to later phase")

    def _build_status_payload(self) -> dict[str, Any]:
        """Aggregate runtime information into a serialisable payload."""

        resources = {name: record.to_dict() for name, record in self.resource_status.items()}
        tunnel_payload: dict[str, Any] | None = None

        if self.tunnel_info:
            tunnel_payload = {
                "hostname": self.tunnel_info.hostname,
                "url": f"https://{self.tunnel_info.hostname}",
                "status": self.tunnel_info.status,
            }

        return {
            "project": self.config.project_name,
            "service": {
                "name": self.service_name,
                "port": self.port,
                "domain": self.config.domain,
                "tunnel": {
                    "enabled": self.config.enable_tunnel,
                    "info": tunnel_payload,
                },
            },
            "resources": resources,
            "cleanup": self.cleanup_report.to_dict() if self.cleanup_report else None,
        }

    def _display_status(self, status: dict[str, Any]) -> None:
        """Display final status via UI or logger."""

        if self.ui and hasattr(self.ui, "show_final_status"):
            try:
                self.ui.show_final_status(status)
                return
            except Exception as exc:  # pragma: no cover - UI failures should not block startup
                self.logger.warning("Startup UI failed to render status: %s", exc)

        payload = json.dumps(status, indent=2)
        self.logger.info("Startup completed:\n%s", payload)

    @staticmethod
    def _resolve_ui() -> Any | None:
        """Lazy import of optional console UI."""
        try:
            from ..ui.console import StartupUI  # type: ignore

            return StartupUI()
        except Exception:
            return None

