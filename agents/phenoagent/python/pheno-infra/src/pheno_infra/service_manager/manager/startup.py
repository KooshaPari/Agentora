"""
Service startup and shutdown orchestration helpers.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from rich.progress import Progress

from pheno.infra.utils.health import check_http_health
from pheno.infra.utils.identity import get_project_id

from ..watch import WATCHDOG_AVAILABLE, setup_file_watching

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ..models import ServiceConfig, ServiceStatus
    from .core import ServiceManager


class ServiceStartupCoordinator:
    """
    Coordinates service lifecycle operations for ServiceManager.
    """

    def __init__(self, manager: ServiceManager) -> None:
        self.manager = manager

    async def start_service(self, name: str) -> bool:
        config, status = self._prepare_service_startup(name)
        if not config or not status:
            return False

        try:
            await self._execute_service_startup(name, config, status)
            return True
        except asyncio.CancelledError:
            return self._handle_startup_cancellation(name, status)
        except Exception as exc:
            return self._handle_startup_error(name, status, exc)

    async def stop_service(self, name: str) -> bool:
        logger.info("Stopping service: %s", name)
        manager = self.manager
        manager._stop_log_capture(name)  # type: ignore[attr-defined]

        observer = manager.file_observers.pop(name, None)
        if observer:
            observer.stop()
            observer.join(timeout=2)

        proc = manager.processes.pop(name, None)
        if proc and proc.returncode is None:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            except TimeoutError:
                logger.warning("Process %s did not terminate, killing...", name)
                proc.kill()

        await self._cleanup_service_ports(name)

        status = manager.service_status[name]
        status.state = "stopped"
        status.pid = None
        status.port = None
        status.tunnel_url = None
        logger.info("Service %s stopped", name)
        return True

    async def start_all(self) -> dict[str, bool]:
        manager = self.manager
        results: dict[str, bool] = {}
        resource_results = await manager.check_all_resources()  # type: ignore[attr-defined]

        for rname, available in resource_results.items():
            cfg = manager.resources[rname]
            if cfg.required and not available:
                raise RuntimeError(
                    f"Required resource '{rname}' not available at {cfg.host}:{cfg.port}",
                )
            if not available:
                logger.warning("Optional resource '%s' not available", rname)

        for sname in manager.services:
            results[sname] = await self.start_service(sname)

        return results

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _prepare_service_startup(
        self, name: str,
    ) -> tuple[ServiceConfig | None, ServiceStatus | None]:
        manager = self.manager
        config = manager.services.get(name)
        if not config:
            logger.error("Service config not found for %s", name)
            return None, None

        status = manager.service_status[name]
        status.state = "starting"
        return config, status

    async def _execute_service_startup(
        self, name: str, config: ServiceConfig, status: ServiceStatus,
    ) -> None:
        with Progress() as progress:
            task = progress.add_task("[cyan]Starting service...", total=8)

            await self._allocate_port(name, config, status, progress, task)
            await self._launch_process(name, config, status, progress, task)
            await self._configure_fallback(name, config, status, progress, task)
            self.manager._start_log_capture(name)  # type: ignore[attr-defined]
            await self._await_local_health(name, config, status, progress, task)
            await self._setup_tunnel(name, config, status, progress, task)
            self._start_watchers(name, config, progress, task)
            await self._start_health_checks(name, config, progress, task)
            self._finalize_startup(name, config, status)

    def _handle_startup_cancellation(self, name: str, status: ServiceStatus) -> bool:
        logger.info("Service startup cancelled for %s", name)
        status.state = "cancelled"
        return False

    def _handle_startup_error(self, name: str, status: ServiceStatus, exc: Exception) -> bool:
        logger.error("Failed to start service %s: %s", name, exc)
        status.state = "error"
        status.error_message = str(exc)
        return False

    async def _allocate_port(
        self,
        name: str,
        config: ServiceConfig,
        status: ServiceStatus,
        progress: Progress,
        task,
    ) -> None:
        manager = self.manager
        progress.update(task, description="[cyan]Allocating port...", completed=1)
        port = config.port or manager.kinfra.allocate_port(config.name, config.preferred_port)  # type: ignore[attr-defined]
        status.port = port
        try:
            manager.emit_stage(name, "Allocating port", "completed")
        except Exception:
            logger.debug("emit_stage(port) failed", exc_info=True)

        if config.port:
            try:
                manager.kinfra.registry.register_service(config.name, port)  # type: ignore[attr-defined]
            except Exception as exc:
                logger.debug("Registry register failed for %s: %s", name, exc)

    async def _launch_process(
        self,
        name: str,
        config: ServiceConfig,
        status: ServiceStatus,
        progress: Progress,
        task,
    ):
        manager = self.manager
        progress.update(task, description="[cyan]Starting process...", completed=2)
        proc = await manager._spawn(config)  # type: ignore[attr-defined]
        manager.processes[name] = proc
        status.pid = proc.pid
        try:
            manager.emit_stage(name, "Starting process", "active")
        except Exception:
            logger.debug("emit_stage(start process) failed", exc_info=True)
        try:
            manager.kinfra.registry.update_service(config.name, pid=proc.pid)  # type: ignore[attr-defined]
        except Exception as exc:
            logger.debug("Unable to persist PID for %s: %s", name, exc)
        return proc

    async def _configure_fallback(
        self,
        name: str,
        config: ServiceConfig,
        status: ServiceStatus,
        progress: Progress,
        task,
    ) -> None:
        manager = self.manager
        progress.update(task, description="[cyan]Configuring fallback layer...", completed=3)
        if not manager.enable_fallback_layer:
            return
        if not getattr(manager, "_fallback_started", False):
            await manager._start_fallback_layer()  # type: ignore[attr-defined]

        patterns = getattr(config, "log_stage_patterns", None) or getattr(
            manager, "_default_log_stage_patterns", [],
        )
        manager._service_log_stage_patterns[name] = patterns  # type: ignore[attr-defined]
        await manager._configure_service_fallback(name, config, status.port)  # type: ignore[attr-defined]

    async def _await_local_health(
        self,
        name: str,
        config: ServiceConfig,
        status: ServiceStatus,
        progress: Progress,
        task,
    ) -> None:
        manager = self.manager
        progress.update(task, description="[cyan]Waiting for local readiness...", completed=5)
        if not config.health_check_url:
            return

        loop = asyncio.get_event_loop()
        health_url = config.health_check_url.format(port=status.port)
        try:
            manager.emit_stage(name, "Health check", "active")
        except Exception:
            logger.debug("emit_stage health active failed", exc_info=True)
        ok = await loop.run_in_executor(None, check_http_health, health_url, 20.0, 200, "GET")
        if ok:
            try:
                manager.emit_stage(name, "Health check", "completed")
            except Exception:
                logger.debug("emit_stage health completed failed", exc_info=True)
        else:
            manager.console.print(
                f"  ⚠️  Local health check didn't pass yet: {health_url}", style="yellow",
            )

    async def _setup_tunnel(
        self,
        name: str,
        config: ServiceConfig,
        status: ServiceStatus,
        progress: Progress,
        task,
    ) -> None:
        manager = self.manager
        progress.update(task, description="[cyan]Configuring tunnel...", completed=6)
        if not config.enable_tunnel:
            return
        try:
            result = manager.kinfra.create_tunnel(config.name, status.port, domain=config.tunnel_domain)  # type: ignore[attr-defined]
            status.tunnel_url = f"https://{result.hostname}"
            try:
                manager.emit_stage(name, "Configuring tunnel", "active")
            except Exception:
                logger.debug("emit_stage tunnel active failed", exc_info=True)

            ready = await manager._await_tunnel_ready(  # type: ignore[attr-defined]
                result.hostname,
                config.tunnel_health_endpoint,
                config.tunnel_ready_timeout,
            )

            if ready:
                manager.console.print(f"  ✓ Tunnel ready: {status.tunnel_url}", style="green")
                try:
                    manager.emit_stage(name, "Configuring tunnel", "completed")
                except Exception:
                    logger.debug("emit_stage tunnel completed failed", exc_info=True)
            else:
                manager.console.print(
                    "  ⚠️  Tunnel connectivity delayed (DNS propagation in progress)", style="yellow",
                )
        except asyncio.CancelledError:
            logger.info("Tunnel setup cancelled")
            raise
        except Exception as exc:
            if "already exists" not in str(exc).lower():
                manager.console.print(f"  ⚠️  Tunnel failed: {exc}", style="yellow")
            logger.warning("Tunnel setup failed for %s: %s", name, exc)

    def _start_watchers(self, name: str, config: ServiceConfig, progress: Progress, task) -> None:
        manager = self.manager
        progress.update(task, description="[cyan]Configuring watchers...", completed=7)
        if not config.watch_paths:
            return
        if not WATCHDOG_AVAILABLE:
            manager.console.print(
                "  ⚠️  watchdog not installed (auto-reload disabled)", style="yellow",
            )
            return

        def _on_change(event):  # pragma: no cover - file watcher callback
            logger.info("File changed for %s: %s", name, getattr(event, "src_path", ""))
            asyncio.create_task(manager.reload_service(name))  # type: ignore[attr-defined]

        observer = setup_file_watching(name, config.watch_paths, config.watch_patterns, _on_change)
        if observer:
            manager.file_observers[name] = observer

    async def _start_health_checks(
        self, name: str, config: ServiceConfig, progress: Progress, task,
    ) -> None:
        manager = self.manager
        progress.update(task, description="[cyan]Starting health checks...", completed=8)
        if config.health_check_url:
            asyncio.create_task(manager._check_service_health(name))  # type: ignore[attr-defined]

    def _finalize_startup(self, name: str, config: ServiceConfig, status: ServiceStatus) -> None:
        manager = self.manager
        manager.update_status_running(name, status.pid, status.port, status.tunnel_url)

        if getattr(manager, "_fallback_is_remote", False):
            client = getattr(manager, "_fallback_admin_client", None)
            if client:
                tenant = get_project_id()
                client.update_status(
                    tenant=tenant,
                    service_name=config.name,
                    status_message="Service is running",
                    port=status.port,
                    pid=status.pid,
                    uptime="0s",
                    health_status="Healthy",
                    state="running",
                    steps=[
                        {"text": "Allocating port", "status": "completed"},
                        {"text": "Starting process", "status": "completed"},
                        {"text": "Configuring tunnel", "status": "completed"},
                        {"text": "Health check", "status": "completed"},
                    ],
                )
        elif manager.fallback_server:
            manager.fallback_server.update_service_status(  # type: ignore[attr-defined]
                service_name=config.name,
                status_message="Service is running",
                port=status.port,
                pid=status.pid,
                uptime="0s",
                health_status="Healthy",
                state="running",
                steps=[
                    {"text": "Allocating port", "status": "completed"},
                    {"text": "Starting process", "status": "completed"},
                    {"text": "Configuring tunnel", "status": "completed"},
                    {"text": "Health check", "status": "completed"},
                ],
            )

        manager.console.print(
            f"✅ {name} started on port {status.port}"
            + (f" | PID {status.pid}" if status.pid else ""),
            style="bold green",
        )
        if status.tunnel_url:
            manager.console.print(f"   {status.tunnel_url}", style="cyan")
        logger.info("Service %s started successfully on port %s", name, status.port)

    async def _cleanup_service_ports(self, name: str) -> None:
        manager = self.manager
        try:
            manager.kinfra.registry.unregister_service(name)  # type: ignore[attr-defined]
        except Exception:
            logger.debug("Registry cleanup failed for %s", name, exc_info=True)

        if getattr(manager, "_fallback_is_remote", False):
            client = getattr(manager, "_fallback_admin_client", None)
            if client:
                tenant = get_project_id()
                client.delete_status(tenant=tenant, service_name=name)
        elif manager.fallback_server:
            manager.fallback_server.remove_services_with_prefix(name)  # type: ignore[attr-defined]


__all__ = ["ServiceStartupCoordinator"]
