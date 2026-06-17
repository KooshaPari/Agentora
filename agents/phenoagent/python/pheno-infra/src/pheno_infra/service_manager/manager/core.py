"""
High level service manager orchestrating mixins.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from rich.console import Console

from pheno.infra.utils.identity import get_project_id

from ...tunnel_sync import TunnelManager  # type: ignore
from ..base import BaseServiceManager
from ..fallback import FallbackMixin
from ..health import HealthMixin
from ..monitor import MonitorMixin
from ..processes import ProcessMixin
from ..resources import ResourcesMixin
from .startup import ServiceStartupCoordinator

if TYPE_CHECKING:
    from ...service_infra import ServiceInfraManager

logger = logging.getLogger(__name__)


class ServiceManager(
    BaseServiceManager,
    ProcessMixin,
    HealthMixin,
    ResourcesMixin,
    MonitorMixin,
    FallbackMixin,
):
    """
    Concrete service manager coordinating lifecycle operations.
    """

    def __init__(
        self, service_infra: ServiceInfraManager, enable_fallback_layer: bool = True,
    ) -> None:
        super().__init__(service_infra, enable_fallback_layer)
        self.console = Console()
        self.fallback_server = None
        self.proxy_server = None
        self.tunnel_manager = TunnelManager() if callable(TunnelManager) else None
        self._lifecycle_steps: dict[str, list] = {}
        self._default_log_stage_patterns: list[tuple[str, str, str]] = [
            ("npm install", "Downloading dependencies", "active"),
            ("pnpm install", "Downloading dependencies", "active"),
            ("yarn install", "Downloading dependencies", "active"),
            ("pip install", "Downloading dependencies", "active"),
            ("uv pip install", "Downloading dependencies", "active"),
            ("pip-compile", "Resolving dependencies", "active"),
            ("installing", "Downloading dependencies", "active"),
            ("resolving packages", "Resolving dependencies", "active"),
            ("next build", "Building service", "active"),
            ("vite", "Building service", "active"),
            ("webpack", "Building service", "active"),
            ("tsc -p", "Building service", "active"),
            ("go build", "Building service", "active"),
            ("mvn package", "Building service", "active"),
            ("gradle build", "Building service", "active"),
            ("cargo build", "Building service", "active"),
            ("compiled successfully", "Building service", "completed"),
            ("build complete", "Building service", "completed"),
            ("starting server", "Starting server", "active"),
            ("uvicorn", "Starting server", "active"),
            ("gunicorn", "Starting server", "active"),
            ("go run", "Starting server", "active"),
            ("cargo run", "Starting server", "active"),
            ("listening on", "Starting server", "completed"),
            ("server started", "Starting server", "completed"),
            ("ready in", "Starting server", "completed"),
            ("server listening", "Starting server", "completed"),
            ("now listening", "Starting server", "completed"),
            ("application started", "Starting server", "completed"),
            ("started server process", "Starting server", "active"),
            ("alembic", "Running migrations", "active"),
            ("flyway", "Running migrations", "active"),
            ("liquibase", "Running migrations", "active"),
            ("migrat", "Running migrations", "active"),
            ("migration", "Running migrations", "active"),
            ("migration complete", "Running migrations", "completed"),
            ("docker build", "Building container image", "active"),
            ("docker pull", "Pulling container image", "active"),
            ("buildx", "Building container image", "active"),
            ("tomcat started on", "Starting server", "completed"),
            ("started application", "Starting server", "completed"),
            ("starting development server at", "Starting server", "completed"),
            ("statreloader", "Starting server", "active"),
            ("booting puma", "Starting server", "active"),
            ("listening on tcp://", "Starting server", "completed"),
        ]
        self._service_log_stage_patterns: dict[str, list] = {}
        self._fallback_is_remote = False
        self._startup = ServiceStartupCoordinator(self)

    async def start_service(self, name: str) -> bool:
        return await self._startup.start_service(name)

    async def stop_service(self, name: str) -> bool:
        return await self._startup.stop_service(name)

    async def start_all(self) -> dict[str, bool]:
        return await self._startup.start_all()

    def emit_stage(self, name: str, text: str, status: str) -> None:
        steps = self._lifecycle_steps.get(name) or []
        found = next((step for step in steps if step.get("text") == text), None)
        if found:
            found["status"] = status
        else:
            steps.append({"text": text, "status": status})
        self._lifecycle_steps[name] = steps
        payload = {"status_message": text, "state": "starting", "steps": steps}
        self._publish_status(name, payload)

    def emit_status(self, name: str, **fields: Any) -> None:
        self._publish_status(name, fields)

    def emit_and_log(self, name: str, text: str, status: str) -> None:
        self.console.print(f"  • {text} [{status}]")
        self.emit_stage(name, text, status)

    def _publish_status(self, name: str, payload: dict[str, Any]) -> None:
        try:
            service_cfg = self.services.get(name)
            service_name = service_cfg.name if service_cfg else name
            if getattr(self, "_fallback_is_remote", False):
                client = getattr(self, "_fallback_admin_client", None)
                if client:
                    tenant = get_project_id()
                    client.update_status(tenant=tenant, service_name=service_name, **payload)
            elif self.fallback_server:
                self.fallback_server.update_service_status(service_name=service_name, **payload)  # type: ignore[attr-defined]
        except Exception:
            logger.debug("emit_status failed", exc_info=True)


__all__ = ["ServiceManager"]
