"""
ServiceManager base and orchestration (hexagonal-inspired split).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from .models import ResourceConfig, ResourceStatus, ServiceConfig, ServiceStatus

if TYPE_CHECKING:
    import asyncio

logger = logging.getLogger(__name__)


@dataclass
class _State:
    services: dict[str, ServiceConfig] = field(default_factory=dict)
    service_status: dict[str, ServiceStatus] = field(default_factory=dict)
    resources: dict[str, ResourceConfig] = field(default_factory=dict)
    resource_status: dict[str, ResourceStatus] = field(default_factory=dict)
    processes: dict[str, asyncio.subprocess.Process] = field(default_factory=dict)
    file_observers: dict[str, object] = field(default_factory=dict)
    _monitor_tasks: list[asyncio.Task] = field(default_factory=list)
    _log_capture_tasks: dict[str, list[asyncio.Task]] = field(default_factory=dict)
    _shutdown: bool = False


class BaseServiceManager:
    def __init__(self, service_infra, enable_fallback_layer: bool = True) -> None:
        self.kinfra = service_infra  # Keep kinfra for backward compatibility
        self.enable_fallback_layer = enable_fallback_layer
        self.state = _State()

    # Ease of access properties to match previous API
    @property
    def services(self):
        return self.state.services

    @property
    def service_status(self):
        return self.state.service_status

    @property
    def resources(self):
        return self.state.resources

    @property
    def resource_status(self):
        return self.state.resource_status

    @property
    def processes(self):
        return self.state.processes

    @property
    def file_observers(self):
        return self.state.file_observers

    @property
    def _monitor_tasks(self):
        return self.state._monitor_tasks

    @property
    def _log_capture_tasks(self):
        return self.state._log_capture_tasks

    @property
    def _shutdown(self) -> bool:
        return self.state._shutdown

    @_shutdown.setter
    def _shutdown(self, value: bool) -> None:
        self.state._shutdown = value

    # --- Registration helpers ---

    def register_service(self, config: ServiceConfig) -> None:
        self.services[config.name] = config
        self.service_status[config.name] = ServiceStatus(
            name=config.name,
            state="stopped",
            started_at=None,
            pid=None,
            port=None,
            tunnel_url=None,
            restart_count=0,
            last_health_check=None,
            health_status="unknown",
            error_message=None,
        )

    # Back-compat aliases (older callers used add_service/add_resource)
    def add_service(self, config: ServiceConfig) -> None:  # pragma: no cover - shim
        self.register_service(config)

    def register_resource(self, config: ResourceConfig) -> None:
        self.resources[config.name] = config
        self.resource_status[config.name] = ResourceStatus(
            name=config.name, available=False, last_check=None, error_message=None,
        )

    def add_resource(self, config: ResourceConfig) -> None:  # pragma: no cover - shim
        self.register_resource(config)

    # --- Helpers for status ---

    def update_status_running(
        self, name: str, pid: int | None, port: int | None, tunnel_url: str | None,
    ) -> None:
        status = self.service_status[name]
        status.state = "running"
        status.started_at = datetime.now()
        status.restart_count = 0
        status.pid = pid
        status.port = port
        status.tunnel_url = tunnel_url

    def update_status_error(self, name: str, message: str) -> None:
        status = self.service_status[name]
        status.state = "error"
        status.error_message = message
