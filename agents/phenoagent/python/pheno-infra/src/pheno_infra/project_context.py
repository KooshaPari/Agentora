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
from contextlib import contextmanager
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

logger = logging.getLogger(__name__)


class ProjectInfraContext:
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
            # Inform lower layers so registry/cleanup uses the project identifier.
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
        logger.info("Initialized ProjectInfraContext", extra=self._log_payload(event="init"))

    @property
    def registry(self):
        return self.service_infra.registry

    @property
    def allocator(self):
        return self.service_infra.allocator

    @property
    def tunnel_manager(self):
        return self.service_infra.tunnel_manager

    # --------------------------------------------------------------------- #
    # Context management
    # --------------------------------------------------------------------- #
    def __enter__(self) -> Self:
        if self.enable_proxy:
            self.start_proxy()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.cleanup_project_services()
        if self.enable_proxy:
            self.stop_proxy()
        self._sync_await(self.resource_coordinator.shutdown())
        logger.info("Closed ProjectInfraContext", extra=self._log_payload(event="close"))

    # --------------------------------------------------------------------- #
    # Proxy helpers
    # --------------------------------------------------------------------- #
    def start_proxy(self) -> None:
        """Start the reverse proxy/fallback server for this project."""
        if self._proxy_started:
            return
        if self.proxy_server is None:
            self.proxy_server = ProxyServer(
                proxy_port=self.proxy_port,
                fallback_port=self.fallback_port,
            )
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

    def _ensure_proxy_server(self) -> ProxyServer | None:
        if not self.enable_proxy:
            return None
        if self.proxy_server is None:
            self.proxy_server = ProxyServer(
                proxy_port=self.proxy_port,
                fallback_port=self.fallback_port,
            )
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
        assert self.proxy_server is not None  # appease type-checkers

        if disable_default_route and service_name:
            self._auto_route_disabled_services.add(service_name)
            self._remove_auto_route(service_name)

        project_service = f"{self.project_name}-{service_name}" if service_name else None
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
        services: Sequence[str] | dict[str, int] | Iterable[tuple[str, int]],
        *,
        host: str | None = None,
        path_template: str | None = None,
    ) -> None:
        """Bulk-register routes for services based on the template."""

        if isinstance(services, dict):
            entries = list(services.items())
        else:
            items = list(services)
            if items and all(isinstance(item, tuple) and len(item) == 2 for item in items):
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

    # --------------------------------------------------------------------- #
    # Fallback & maintenance helpers
    # --------------------------------------------------------------------- #
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
            "Disabled maintenance mode", extra=self._log_payload(event="maintenance_disable"),
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
        self.fallback_config_manager.update_fallback_page(self.project_name, page_type, page_config)
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

    # --------------------------------------------------------------------- #
    # Port/tunnel helpers
    # --------------------------------------------------------------------- #
    def allocate_port(
        self,
        service_name: str,
        *,
        preferred_port: int | None = None,
        service_type: str = "service",
        scope: str | None = None,
        resource_type: str = "service",
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """Allocate a port for a project service with metadata propagation."""
        scoped_name = f"{self.project_name}-{service_name}"
        port = self.service_infra.allocate_port(
            scoped_name,
            preferred_port=preferred_port,
            project=self.project_name,
            service_type=service_type,
            scope=scope,
            resource_type=resource_type,
            metadata=metadata,
        )
        self._project_services.add(scoped_name)
        logger.info(
            "Allocated port",
            extra=self._log_payload(
                event="allocate_port",
                service=scoped_name,
                port=port,
                service_type=service_type,
                scope=scope or ("project" if self.project_name else "local"),
            ),
        )
        return port

    def start_tunnel(
        self,
        service_name: str,
        port: int,
        *,
        domain: str | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        """Start a tunnel for a project service."""
        scoped_name = f"{self.project_name}-{service_name}"
        tunnel_info = self.service_infra.tunnel_manager.start_tunnel(
            scoped_name,
            port,
            domain=domain,
        )
        if metadata:
            self.service_infra.registry.update_service(scoped_name, metadata=metadata)  # type: ignore[attr-defined]
        logger.info(
            "Started tunnel",
            extra=self._log_payload(
                event="tunnel_start",
                service=scoped_name,
                port=port,
                hostname=tunnel_info.hostname,
            ),
        )
        return tunnel_info

    def allocate_and_tunnel(
        self,
        service_name: str,
        *,
        preferred_port: int | None = None,
        domain: str | None = None,
        service_type: str = "service",
        scope: str | None = None,
        resource_type: str = "service",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Convenience helper that allocates a port and immediately creates a tunnel."""
        port = self.allocate_port(
            service_name,
            preferred_port=preferred_port,
            service_type=service_type,
            scope=scope,
            resource_type=resource_type,
            metadata=metadata,
        )
        tunnel_info = self.start_tunnel(
            service_name,
            port,
            domain=domain or self.domain,
            metadata=metadata,
        )
        self._maybe_register_default_route(service_name, port)
        return {
            "project": self.project_name,
            "service": service_name,
            "scoped_service": f"{self.project_name}-{service_name}",
            "port": port,
            "tunnel": tunnel_info,
            "url": f"https://{tunnel_info.hostname}",
        }

    # --------------------------------------------------------------------- #
    # Cleanup & env helpers
    # --------------------------------------------------------------------- #
    def cleanup_project_services(self) -> None:
        """Clean up all services registered under this project."""
        for scoped_name in list(self._project_services):
            try:
                self.service_infra.cleanup(scoped_name)
                logger.info(
                    "Cleaned project service",
                    extra=self._log_payload(event="cleanup_service", service=scoped_name),
                )
            except Exception as exc:
                logger.exception(
                    "Failed to clean service %s: %s", scoped_name, exc, extra=self._log_payload(),
                )
        self._project_services.clear()

    def export_environment_variables(self) -> dict[str, str]:
        """Return environment variables describing current project allocations."""
        env: dict[str, str] = {
            "KINFRA_PROJECT": self.project_name,
            "KINFRA_DOMAIN": self.domain,
        }
        if self.enable_proxy:
            env["KINFRA_PROXY_PORT"] = str(self.proxy_port)
            env["KINFRA_FALLBACK_PORT"] = str(self.fallback_port)

        for name, info in self.service_infra.registry.get_all_services().items():  # type: ignore[attr-defined]
            if info.project != self.project_name:
                continue
            alias = name.replace(f"{self.project_name}-", "").upper().replace("-", "_")
            env[f"KINFRA_{alias}_PORT"] = str(info.assigned_port)
            if info.tunnel_hostname:
                env[f"KINFRA_{alias}_URL"] = f"https://{info.tunnel_hostname}"
        return env

    def set_environment_variables(self) -> None:
        """Apply exported variables to ``os.environ``."""
        env_vars = self.export_environment_variables()
        for key, value in env_vars.items():
            os.environ[key] = value
        logger.info(
            "Set project environment variables",
            extra=self._log_payload(event="set_env", count=len(env_vars)),
        )

    # --------------------------------------------------------------------- #
    # Observability helpers
    # --------------------------------------------------------------------- #
    def metrics_payload(self) -> dict[str, Any]:
        """Return a metrics-friendly snapshot of project services."""
        services = []
        for name, info in self.service_infra.registry.get_all_services().items():  # type: ignore[attr-defined]
            if info.project == self.project_name:
                services.append(
                    {
                        "service": name,
                        "port": info.assigned_port,
                        "service_type": info.service_type,
                        "scope": info.scope,
                        "resource_type": info.resource_type,
                        "tunnel": info.tunnel_hostname,
                    },
                )
        resources = self._sync_await(self.resource_coordinator.get_project_resources())
        return {
            "project": self.project_name,
            "services": services,
            "resources": resources,
        }

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
            "path_template", "/{project}/{service}",
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
                        event="proxy_route_remove", path=path_prefix, service=service_name,
                    ),
                )
        except Exception as exc:
            logger.warning(
                "Failed to remove auto route %s: %s",
                path_prefix,
                exc,
                extra=self._log_payload(service=service_name),
            )

    def set_resource_policy(
        self,
        resource_type: str,
        *,
        lifecycle_rule: LifecycleRule = LifecycleRule.SMART_DECISION,
        reuse_strategy: ResourceReuseStrategy = ResourceReuseStrategy.SMART,
        dependencies: list[str] | None = None,
        compatibility_requirements: dict[str, Any] | None = None,
    ) -> None:
        """Define or update a resource policy for this project."""
        policy = ResourcePolicy(
            resource_type=resource_type,
            lifecycle_rule=lifecycle_rule,
            reuse_strategy=reuse_strategy,
            dependencies=dependencies or [],
            compatibility_requirements=compatibility_requirements or {},
        )
        self.resource_coordinator.set_resource_policy(policy)
        logger.info(
            "Updated resource policy",
            extra=self._log_payload(
                event="policy",
                resource_type=resource_type,
                rule=lifecycle_rule.value,
                reuse=reuse_strategy.value,
            ),
        )

    def request_resource(
        self,
        resource_name: str,
        config: dict[str, Any],
        *,
        mode: ResourceMode | None = None,
        dependencies: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Request a resource via the coordinator."""
        success, info = self._sync_await(
            self.resource_coordinator.request_resource(
                resource_name=resource_name,
                config=config,
                mode=mode,
                dependencies=dependencies,
                metadata=metadata,
            ),
        )
        if not success or info is None:
            raise RuntimeError(f"Failed to provision resource '{resource_name}'")
        logger.info(
            "Provisioned resource",
            extra=self._log_payload(event="resource_start", resource=resource_name, info=info),
        )
        return info

    def release_resource(self, resource_name: str, *, force: bool = False) -> bool:
        """Release a resource reference."""
        result = self._sync_await(
            self.resource_coordinator.release_resource(resource_name, force_cleanup=force),
        )
        logger.info(
            "Released resource",
            extra=self._log_payload(event="resource_stop", resource=resource_name, force=force),
        )
        return result

    def list_resources(self) -> list[dict[str, Any]]:
        """Return resource status for the current project."""
        return self._sync_await(self.resource_coordinator.get_project_resources())

    def resource_status(self, resource_name: str) -> dict[str, Any] | None:
        """Return detailed status for a single resource."""
        return self._sync_await(self.resource_coordinator.get_resource_status(resource_name))

    def validate_dependencies(self) -> tuple[bool, list[str]]:
        """Validate that declared dependencies are satisfied."""
        return self._sync_await(self.resource_coordinator.validate_project_dependencies())

    def coordination_status(self) -> dict[str, Any]:
        """Return aggregated coordination status."""
        return self._sync_await(self.resource_coordinator.get_coordination_status())

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


@contextmanager
def project_infra_context(
    project_name: str,
    *,
    domain: str = "kooshapari.com",
    config_dir: str | None = None,
    enable_proxy: bool = True,
    proxy_port: int = 9100,
    fallback_port: int = 9000,
    set_env_vars: bool = True,
    routing_template: dict[str, Any] | None = None,
):
    """Synchronous context-manager variant for quick scripts."""
    ctx = ProjectInfraContext(
        project_name,
        domain=domain,
        config_dir=config_dir,
        enable_proxy=enable_proxy,
        proxy_port=proxy_port,
        fallback_port=fallback_port,
        routing_template=routing_template,
    )
    try:
        with ctx:
            if set_env_vars:
                ctx.set_environment_variables()
            yield ctx
    finally:
        ctx.cleanup_project_services()
        if enable_proxy:
            ctx.stop_proxy()


def quick_project_setup(
    project_name: str,
    services: dict[str, dict[str, Any]],
    *,
    domain: str = "kooshapari.com",
    enable_proxy: bool = True,
) -> dict[str, Any]:
    """
    Convenience helper to spin up a project, allocate ports/tunnels, and (optionally) register
    proxy routes for a dictionary of services.
    """
    results: dict[str, Any] = {}
    with project_infra_context(
        project_name,
        domain=domain,
        enable_proxy=enable_proxy,
        set_env_vars=False,
    ) as ctx:
        for service_name, cfg in services.items():
            try:
                result = ctx.allocate_and_tunnel(
                    service_name,
                    preferred_port=cfg.get("preferred_port"),
                    service_type=cfg.get("service_type", "service"),
                    scope=cfg.get("scope"),
                    resource_type=cfg.get("resource_type", "service"),
                    metadata=cfg.get("metadata"),
                )
                results[service_name] = result
                proxy_path = cfg.get("proxy_path")
                if proxy_path:
                    ctx.register_proxy_route(
                        path_prefix=proxy_path,
                        port=result["port"],
                        service_name=service_name,
                    )
            except Exception as exc:
                logger.exception(
                    "Failed to set up service %s: %s", service_name, exc, extra=ctx._log_payload(),
                )
                results[service_name] = {"error": str(exc)}
    return results
