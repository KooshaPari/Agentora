"""
Service management helpers for ProjectInfraContext: port allocation, tunnels, env vars, and resources.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from .global_registry import ResourceMode
    from .project_context_core import ProjectInfraContext

logger = logging.getLogger(__name__)


class ServiceHelpers:
    """Port/tunnel allocation, env, cleanup, and resource management helpers."""

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

    def cleanup_project_services(self) -> None:
        """Clean up all services registered under this project."""
        for scoped_name in list(self._project_services):
            try:
                self.service_infra.cleanup(scoped_name)
                logger.info(
                    "Cleaned project service",
                    extra=self._log_payload(
                        event="cleanup_service", service=scoped_name
                    ),
                )
            except Exception as exc:
                logger.exception(
                    "Failed to clean service %s: %s",
                    scoped_name,
                    exc,
                    extra=self._log_payload(),
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

    def set_resource_policy(
        self,
        resource_type: str,
        *,
        lifecycle_rule: Any = None,
        reuse_strategy: Any = None,
        dependencies: list[str] | None = None,
        compatibility_requirements: dict[str, Any] | None = None,
    ) -> None:
        """Define or update a resource policy for this project."""
        from .resource_coordinator import LifecycleRule, ResourcePolicy
        from .resource_reference_cache import ResourceReuseStrategy

        if lifecycle_rule is None:
            lifecycle_rule = LifecycleRule.SMART_DECISION
        if reuse_strategy is None:
            reuse_strategy = ResourceReuseStrategy.SMART

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
            extra=self._log_payload(
                event="resource_start", resource=resource_name, info=info
            ),
        )
        return info

    def release_resource(self, resource_name: str, *, force: bool = False) -> bool:
        """Release a resource reference."""
        result = self._sync_await(
            self.resource_coordinator.release_resource(
                resource_name, force_cleanup=force
            ),
        )
        logger.info(
            "Released resource",
            extra=self._log_payload(
                event="resource_stop", resource=resource_name, force=force
            ),
        )
        return result

    def list_resources(self) -> list[dict[str, Any]]:
        """Return resource status for the current project."""
        return self._sync_await(self.resource_coordinator.get_project_resources())

    def resource_status(self, resource_name: str) -> dict[str, Any] | None:
        """Return detailed status for a single resource."""
        return self._sync_await(
            self.resource_coordinator.get_resource_status(resource_name)
        )

    def validate_dependencies(self) -> tuple[bool, list[str]]:
        """Validate that declared dependencies are satisfied."""
        return self._sync_await(
            self.resource_coordinator.validate_project_dependencies()
        )

    def coordination_status(self) -> dict[str, Any]:
        """Return aggregated coordination status."""
        return self._sync_await(self.resource_coordinator.get_coordination_status())
