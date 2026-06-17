"""
Lifecycle helpers that power the unified startup framework.

This module provides small, composable utilities used by
``pheno.kits.infra.startup.framework`` to orchestrate infrastructure tasks:

* Cleaning up stale processes and registry entries before boot.
* Creating and configuring :class:`~pheno.kits.infra.kinfra.KInfra`.
* Resolving resource definitions into running adapters.
* Managing lifecycle hooks for startup and shutdown events.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from functools import partial
from typing import TYPE_CHECKING, Any

from ..kinfra import KInfra
from ..port_registry import PortRegistry
from ..resource_manager import ResourceManager
from ..utils.dns import dns_safe_slug
from ..utils.process import (
    cleanup_orphaned_processes,
    get_port_occupant,
    kill_processes_on_port,
)

if TYPE_CHECKING:
    from ..tunnel_sync import TunnelInfo
    from .config import StartupConfig, StartupHook


try:
    _native_to_thread = asyncio.to_thread  # type: ignore[attr-defined]
except AttributeError:  # pragma: no cover - fallback for Python < 3.9

    async def _to_thread(func: Callable[..., Any], /, *args: Any, **kwargs: Any) -> Any:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, partial(func, *args, **kwargs))
else:

    async def _to_thread(func: Callable[..., Any], /, *args: Any, **kwargs: Any) -> Any:
        return await _native_to_thread(func, *args, **kwargs)


@dataclass(slots=True)
class CleanupReport:
    """Summary of pre-startup cleanup activities.

    Attributes
    ----------
    project_name:
        Name of the project being bootstrapped.
    reclaimed_port:
        Port number that was freed during cleanup, if any.
    port_process:
        Information about the process originally occupying the preferred port.
    tunnel_processes:
        Statistics returned by :func:`cleanup_orphaned_processes`.
    registry_pruned:
        Number of stale registry entries removed for this project.
    """

    project_name: str
    reclaimed_port: int | None = None
    port_process: dict[str, Any] | None = None
    tunnel_processes: dict[str, int] = field(default_factory=dict)
    registry_pruned: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Render the cleanup summary as a serialisable dictionary."""
        return {
            "project_name": self.project_name,
            "reclaimed_port": self.reclaimed_port,
            "port_process": self.port_process,
            "tunnel_processes": self.tunnel_processes,
            "registry_pruned": self.registry_pruned,
        }


@dataclass(slots=True)
class ResourceStatusRecord:
    """Status descriptor for a managed resource."""

    name: str
    mode: str
    scope: str
    status: str
    connection: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly representation."""
        return {
            "name": self.name,
            "mode": self.mode,
            "scope": self.scope,
            "status": self.status,
            "connection": self.connection,
            "details": self.details,
        }


@dataclass(slots=True)
class ResourceResolution:
    """Container returned by :func:`resolve_project_resources`."""

    statuses: dict[str, ResourceStatusRecord] = field(default_factory=dict)
    manager: ResourceManager | None = None

    def to_dict(self) -> dict[str, Any]:
        """Expose the resolution outcome as a dictionary."""
        return {name: record.to_dict() for name, record in self.statuses.items()}


async def cleanup_stale_infrastructure(
    config: StartupConfig, *, logger: logging.Logger | None = None,
) -> CleanupReport:
    """Clean up stale infrastructure artifacts before startup.

    The cleanup sequence performs three key tasks:

    1. Ensure the preferred port is available by terminating orphaned processes.
    2. Remove stale tunnel processes (``cloudflared``) to prevent duplicate tunnels.
    3. Prune outdated entries from the port registry for the target project.

    Parameters
    ----------
    config:
        Startup configuration for the current project.
    logger:
        Optional logger for emitting diagnostic information.

    Returns
    -------
    CleanupReport
        Structured summary of the cleanup activities.
    """

    log = logger or logging.getLogger(__name__)
    report = CleanupReport(project_name=config.project_name)

    # Step 1: Ensure preferred port is free.
    occupant = get_port_occupant(config.preferred_port)
    if occupant:
        report.port_process = occupant
        log.warning(
            "Preferred port %s is occupied by PID %s (%s); attempting reclamation",
            config.preferred_port,
            occupant.get("pid"),
            occupant.get("name"),
        )
        try:
            reclaimed = await _to_thread(kill_processes_on_port, config.preferred_port)
        except Exception as exc:  # pragma: no cover - safety catch
            log.exception("Failed to reclaim port %s: %s", config.preferred_port, exc)
            reclaimed = False

        if reclaimed:
            report.reclaimed_port = config.preferred_port
            log.info("Port %s reclaimed successfully", config.preferred_port)
        else:
            log.warning(
                "Could not reclaim port %s; continue with dynamic allocation",
                config.preferred_port,
            )

    # Step 2: Terminate orphaned tunnel processes.
    try:
        tunnel_stats = await _to_thread(cleanup_orphaned_processes, process_name_pattern="cloudflared")
    except Exception as exc:  # pragma: no cover - safety catch
        log.exception("Tunnel cleanup failed: %s", exc)
        tunnel_stats = {"inspected": 0, "terminated": 0, "force_killed": 0, "skipped": 0}
    report.tunnel_processes = tunnel_stats

    # Step 3: Remove stale registry entries.
    registry = PortRegistry()
    service_identifier = build_service_identifier(config.project_name)
    removed = 0

    for service_name, info in list(registry.get_all_services().items()):
        same_project = info.project == config.project_name if info.project else False
        if service_name == service_identifier or (same_project and info.is_stale(300)):
            if registry.unregister_service(service_name):
                removed += 1

    report.registry_pruned = removed
    if removed:
        log.info("Pruned %s stale registry entr%s", removed, "y" if removed == 1 else "ies")

    return report


def create_kinfra(config: StartupConfig) -> KInfra:
    """Instantiate :class:`KInfra` using configuration defaults."""
    return KInfra(domain=config.domain)


async def allocate_service_port(
    kinfra: KInfra, service_name: str, preferred_port: int | None,
) -> int:
    """Allocate a port for the primary service using :class:`KInfra`."""
    return await _to_thread(kinfra.allocate_port, service_name, preferred_port)


async def establish_project_tunnel(
    kinfra: KInfra,
    service_name: str,
    port: int,
    *,
    domain: str | None,
    logger: logging.Logger | None = None,
) -> TunnelInfo:
    """Create or update a tunnel for the project service."""

    log = logger or logging.getLogger(__name__)
    log.info(
        "Establishing tunnel for service '%s' on port %s%s",
        service_name,
        port,
        f" (domain={domain})" if domain else "",
    )
    return await _to_thread(kinfra.start_tunnel, service_name, port, domain)


async def resolve_project_resources(
    project_name: str,
    resource_defs: dict[str, dict[str, Any]],
    *,
    kinfra: KInfra | None = None,
    logger: logging.Logger | None = None,
) -> ResourceResolution:
    """Resolve project-defined resources into active connections."""

    log = logger or logging.getLogger(__name__)
    if not resource_defs:
        return ResourceResolution()

    coordinator_cls = _load_resource_coordinator()
    if coordinator_cls:
        coordinator = coordinator_cls(kinfra) if kinfra else coordinator_cls()  # type: ignore[call-arg]
        resolved = await coordinator.resolve_resources(project_name, resource_defs)  # type: ignore[attr-defined]
        if resolved is None:
            resolved = {}
        if not isinstance(resolved, dict):
            log.warning(
                "Resource coordinator returned %s, expected dict – ignoring result",
                type(resolved).__name__,
            )
            resolved = {}

        statuses: dict[str, ResourceStatusRecord] = {}
        for name, outcome in resolved.items():
            definition = resource_defs.get(name, {})
            mode = str(definition.get("mode", "local"))
            scope = str(definition.get("scope", "project"))

            if isinstance(outcome, dict):
                url = outcome.get("url") or outcome.get("connection") or outcome.get("dsn")
                statuses[name] = ResourceStatusRecord(
                    name=name,
                    mode=mode,
                    scope=scope,
                    status=outcome.get("status", "ready"),
                    connection=url,
                    details={k: v for k, v in outcome.items() if k not in {"url", "connection", "dsn", "status"}},
                )
            else:
                statuses[name] = ResourceStatusRecord(
                    name=name,
                    mode=mode,
                    scope=scope,
                    status="ready",
                    connection=str(outcome),
                    details={"value": outcome},
                )

        manager = getattr(coordinator, "manager", None)
        return ResourceResolution(statuses=statuses, manager=manager)

    # Fallback: directly manage resources via ResourceManager.
    manager = ResourceManager()
    statuses: dict[str, ResourceStatusRecord] = {}
    local_configs: dict[str, dict[str, Any]] = {}

    for name, definition in resource_defs.items():
        mode = str(definition.get("mode", "local"))
        scope = str(definition.get("scope", "project"))

        if mode == "prod":
            connection = definition.get("prod_url") or definition.get("url")
            statuses[name] = ResourceStatusRecord(
                name=name,
                mode=mode,
                scope=scope,
                status="external" if connection else "defined",
                connection=connection,
                details={"message": "Using externally managed resource"},
            )
            continue

        config = {
            key: value
            for key, value in definition.items()
            if key not in {"mode", "scope", "prod_url", "metadata"}
        }

        record = ResourceStatusRecord(
            name=name,
            mode=mode,
            scope=scope,
            status="pending",
            details={"adapter": config.get("type")},
        )
        statuses[name] = record

        try:
            manager.add_resource(name, config)
            local_configs[name] = config
        except Exception as exc:  # pragma: no cover - adapter creation failure
            record.status = "error"
            record.details["error"] = str(exc)
            log.exception("Failed to add resource '%s': %s", name, exc)

    if local_configs:
        start_results = await manager.start_all()
        for name, success in start_results.items():
            record = statuses[name]
            record.status = "ready" if success else "error"
            if success:
                record.connection = _infer_connection(local_configs[name])
            else:
                record.details.setdefault("error", "Startup failed")
                log.error("Resource '%s' failed to start", name)

    return ResourceResolution(statuses=statuses, manager=manager if manager.resources else None)


async def run_lifecycle_hook(hook: StartupHook | None, startup: Any) -> None:
    """Execute a lifecycle hook if provided."""

    if not hook:
        return

    try:
        result = hook(startup)
        if asyncio.iscoroutine(result) or isinstance(result, Awaitable):
            await result  # type: ignore[func-returns-value]
    except Exception as exc:  # pragma: no cover - hook errors should surface prominently
        raise RuntimeError(f"Startup lifecycle hook failed: {exc}") from exc


def build_service_identifier(project_name: str, suffix: str = "service") -> str:
    """Create a deterministic, DNS-safe service identifier."""
    base = f"{project_name}-{suffix}" if suffix else project_name
    return dns_safe_slug(base)


def _load_resource_coordinator():
    """Attempt to load the optional ResourceCoordinator implementation."""
    try:
        from ..resources.coordinator import ResourceCoordinator  # type: ignore

        return ResourceCoordinator
    except Exception:
        return None


def _infer_connection(config: dict[str, Any]) -> str | None:
    """Best-effort inference of a resource connection string."""
    ports = config.get("ports")
    if isinstance(ports, dict) and ports:
        host_port = next(iter(ports.keys()))
        return f"localhost:{host_port}"

    for key in ("url", "uri", "endpoint", "dsn"):
        value = config.get(key)
        if value:
            return str(value)

    return None
