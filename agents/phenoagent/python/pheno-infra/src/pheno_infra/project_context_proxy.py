"""
Proxy and fallback management helpers for ProjectInfraContext.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .fallback_site.config_manager import FallbackPageConfig
    from .project_context_core import ProjectInfraContext

logger = logging.getLogger(__name__)


class ProxyHelpers:
    """Proxy route and fallback maintenance helpers."""

    def start_proxy(self) -> None:
        """Start the reverse proxy/fallback server for this project."""
        if self._proxy_started:
            return
        if self.proxy_server is None:
            self.proxy_server = self._create_proxy_server()
        self._run_async(self.proxy_server.start())
        self._proxy_started = True
        logger.info(
            "Started project proxy",
            extra=self._log_payload(event="proxy_start", proxy_port=self.proxy_port),
        )

    def stop_proxy(self) -> None:
        """Stop the reverse proxy/fallback server if it was started."""
        if not self._proxy_started or self.proxy_server is None:
            return
        self._run_async(self.proxy_server.stop())
        self._proxy_started = False
        logger.info(
            "Stopped project proxy",
            extra=self._log_payload(event="proxy_stop", proxy_port=self.proxy_port),
        )

    def _create_proxy_server(self):
        from .proxy_gateway.server.core import ProxyServer

        return ProxyServer(
            proxy_port=self.proxy_port,
            fallback_port=self.fallback_port,
        )

    def _ensure_proxy_server(self):
        if not self.enable_proxy:
            return None
        if self.proxy_server is None:
            self.proxy_server = self._create_proxy_server()
        return self.proxy_server

    def register_proxy_route(
        self,
        *,
        path_prefix: str,
        port: int,
        host: str = "localhost",
        service_name: str | None = None,
        auto_managed: bool = False,
        disable_default_route: bool = False,
    ) -> None:
        """Register a reverse proxy route for a project service."""
        if not self.enable_proxy:
            logger.warning("Proxy disabled; cannot register route %s", path_prefix)
            return
        if not self._proxy_started:
            self.start_proxy()
        assert self.proxy_server is not None

        if disable_default_route and service_name:
            self._auto_route_disabled_services.add(service_name)
            self._remove_auto_route(service_name)

        project_service = (
            f"{self.project_name}-{service_name}" if service_name else None
        )
        self.proxy_server.add_upstream(
            path_prefix,
            port=port,
            host=host,
            service_name=project_service,
            tenant=self.project_name,
        )
        if auto_managed and service_name:
            self._auto_registered_routes[service_name] = path_prefix
        logger.info(
            "Registered proxy route",
            extra=self._log_payload(
                event="proxy_route",
                path=path_prefix,
                target=f"{host}:{port}",
                service=project_service or "-",
            ),
        )

    def register_service_route(
        self,
        service_name: str,
        port: int,
        *,
        host: str | None = None,
        path_prefix: str | None = None,
        disable_default_route: bool | None = None,
    ) -> None:
        """Register a service route, defaulting to the routing template."""
        resolved_host = host or self._routing_template.get("host", "localhost")
        default_path = self._format_route_path(service_name, path_prefix)
        should_disable = disable_default_route
        if should_disable is None:
            should_disable = path_prefix is not None

        self.register_proxy_route(
            path_prefix=default_path,
            port=port,
            host=resolved_host,
            service_name=service_name,
            auto_managed=path_prefix is None and not should_disable,
            disable_default_route=bool(should_disable),
        )

    def register_default_routes(
        self,
        services: Sequence[str] | dict[str, int] | list[tuple[str, int]],
        *,
        host: str | None = None,
        path_template: str | None = None,
    ) -> None:
        """Bulk-register routes for services based on the template."""
        if isinstance(services, dict):
            entries = list(services.items())
        else:
            items = list(services)
            if items and all(
                isinstance(item, tuple) and len(item) == 2 for item in items
            ):
                entries = [(str(name), int(port)) for name, port in items]  # type: ignore[arg-type]
            else:
                entries = []
                for service_name in items:
                    scoped_name = f"{self.project_name}-{service_name}"
                    info = self.service_infra.registry.get_service(scoped_name)  # type: ignore[attr-defined]
                    if not info:
                        raise ValueError(
                            f"Service '{service_name}' is not registered for project {self.project_name}",
                        )
                    entries.append((str(service_name), info.assigned_port))

        for service_name, port in entries:
            computed_path = self._format_route_path(
                service_name,
                path_template or self._routing_template.get("path_template"),
            )
            self.register_proxy_route(
                path_prefix=computed_path,
                port=port,
                host=host or self._routing_template.get("host", "localhost"),
                service_name=service_name,
                auto_managed=path_template is None and host is None,
            )

    def enable_maintenance(
        self,
        *,
        message: str | None = None,
        estimated_duration: str | None = None,
        contact_info: str | None = None,
        page_type: str | None = None,
    ) -> None:
        """Enable maintenance mode for the project."""
        self.fallback_config_manager.load_project_config(self.project_name)
        project_config = self.fallback_config_manager.get_or_create_project_config(
            self.project_name,
        )
        self.fallback_config_manager.enable_maintenance(
            self.project_name,
            message=message,
            estimated_duration=estimated_duration,
            contact_info=contact_info,
        )
        if page_type:
            project_config.default_page_type = page_type
        self.fallback_config_manager.save_project_config(self.project_name)

        proxy = self._ensure_proxy_server()
        if proxy:
            proxy.enable_maintenance(message, estimated_duration)
        logger.info(
            "Enabled maintenance mode",
            extra=self._log_payload(event="maintenance_enable", page_type=page_type),
        )

    def disable_maintenance(self) -> None:
        """Disable maintenance mode for the project."""
        self.fallback_config_manager.load_project_config(self.project_name)
        self.fallback_config_manager.disable_maintenance(self.project_name)
        self.fallback_config_manager.save_project_config(self.project_name)

        proxy = self._ensure_proxy_server()
        if proxy:
            proxy.disable_maintenance()
        logger.info(
            "Disabled maintenance mode",
            extra=self._log_payload(event="maintenance_disable"),
        )

    def update_fallback_content(
        self,
        *,
        page_type: str,
        message: str | None = None,
        estimated_duration: str | None = None,
        contact_info: str | None = None,
    ) -> None:
        """Update fallback page content for the project."""
        self.fallback_config_manager.load_project_config(self.project_name)
        project_config = self.fallback_config_manager.get_or_create_project_config(
            self.project_name,
        )

        page_config = project_config.fallback_pages.get(page_type)
        if not page_config:
            from .fallback_site.config_manager import FallbackPageConfig

            page_config = FallbackPageConfig(
                page_type=page_type,
                service_name=self.project_name,
                title=f"{self.project_name} - {page_type.title()}",
                message=message or f"{self.project_name} is {page_type}...",
            )

        if message is not None:
            page_config.message = message

        template_vars = dict(page_config.template_vars)
        if estimated_duration is not None:
            template_vars["estimated_duration"] = estimated_duration
        if contact_info is not None:
            template_vars["contact_info"] = contact_info
        page_config.template_vars = template_vars

        project_config.fallback_pages[page_type] = page_config
        self.fallback_config_manager.update_fallback_page(
            self.project_name, page_type, page_config
        )
        self.fallback_config_manager.save_project_config(self.project_name)

        if page_type == "maintenance" and project_config.maintenance_config.enabled:
            proxy = self._ensure_proxy_server()
            if proxy:
                proxy.enable_maintenance(
                    project_config.maintenance_config.message,
                    project_config.maintenance_config.estimated_duration,
                )

        logger.info(
            "Updated fallback content",
            extra=self._log_payload(event="fallback_update", page_type=page_type),
        )

    def _maybe_register_default_route(self, service_name: str, port: int) -> None:
        if not self.enable_proxy:
            return
        if not self._routing_template.get("enabled", True):
            return
        if service_name in self._auto_route_disabled_services:
            return
        path_prefix = self._format_route_path(service_name, None)
        if self._auto_registered_routes.get(service_name) == path_prefix:
            return
        if service_name in self._auto_registered_routes:
            self._remove_auto_route(service_name)
        self.register_proxy_route(
            path_prefix=path_prefix,
            port=port,
            host=self._routing_template.get("host", "localhost"),
            service_name=service_name,
            auto_managed=True,
        )

    def _remove_auto_route(self, service_name: str) -> None:
        path_prefix = self._auto_registered_routes.pop(service_name, None)
        if not path_prefix:
            return
        if not self._proxy_started or self.proxy_server is None:
            return
        try:
            removed = self.proxy_server.remove_upstream(path_prefix)
            if removed:
                logger.info(
                    "Removed auto proxy route",
                    extra=self._log_payload(
                        event="proxy_route_remove",
                        path=path_prefix,
                        service=service_name,
                    ),
                )
        except Exception as exc:
            logger.warning(
                "Failed to remove auto route %s: %s",
                path_prefix,
                exc,
                extra=self._log_payload(service=service_name),
            )
