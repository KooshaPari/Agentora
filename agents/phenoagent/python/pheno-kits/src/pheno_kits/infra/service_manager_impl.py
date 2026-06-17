"""
Service Manager Implementation - Complete service lifecycle management.

This module contains the full ServiceManager implementation.
"""

import asyncio
import contextlib
import logging
import os
import socket
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from watchdog.events import FileSystemEvent, FileSystemEventHandler
    from watchdog.observers import Observer

    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    Observer = None

    class FileSystemEventHandler:
        pass

    class FileSystemEvent:
        pass


from .exceptions import ServiceError
from .kinfra import KInfra
from .utils.health import check_http_health
from .utils.process import kill_processes_on_port

logger = logging.getLogger(__name__)


@dataclass
class ServiceConfig:
    """Configuration for a managed service."""

    name: str
    command: list[str]
    cwd: Path | None = None
    env: dict[str, str] | None = None
    port: int | None = None
    preferred_port: int | None = None
    enable_tunnel: bool = False
    tunnel_domain: str | None = None
    watch_paths: list[Path] | None = None
    watch_patterns: list[str] | None = None
    restart_on_failure: bool = True
    max_restart_attempts: int = 3
    restart_delay: float = 2.0
    health_check_url: str | None = None
    health_check_interval: float = 10.0
    enable_fallback: bool = True
    fallback_page: str = "loading"
    fallback_refresh_interval: int = 5
    fallback_message: str | None = None
    path_prefix: str = "/"


@dataclass
class ResourceConfig:
    """Configuration for a resource dependency."""

    name: str
    host: str = "localhost"
    port: int = 5432
    check_interval: float = 10.0
    required: bool = True


@dataclass
class ServiceStatus:
    """Current status of a managed service."""

    name: str
    state: str
    pid: int | None = None
    port: int | None = None
    tunnel_url: str | None = None
    started_at: datetime | None = None
    restart_count: int = 0
    last_health_check: datetime | None = None
    health_status: str = "unknown"
    error_message: str | None = None


@dataclass
class ResourceStatus:
    """Current status of a resource dependency."""

    name: str
    available: bool
    last_check: datetime | None = None
    error_message: str | None = None


class FileChangeHandler(FileSystemEventHandler):
    """Handles file system events for auto-reload."""

    def __init__(self, callback: Callable[[Any], None], patterns: list[str]):
        super().__init__()
        self.callback = callback
        self.patterns = patterns or ["*.py"]
        self._debounce_timer: asyncio.TimerHandle | None = None
        self._debounce_delay = 1.0

    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        if not any(file_path.match(pattern) for pattern in self.patterns):
            return

        logger.debug(f"File changed: {file_path}")
        self.callback(event)


class ServiceManager:
    """Complete service lifecycle manager with health monitoring and auto-reload.

    Features:
    - Process startup with port allocation
    - Cloudflare tunnel management
    - Continuous health monitoring
    - Resource dependency checking
    - File watching with auto-reload
    - Automatic restart on failure
    """

    def __init__(
        self,
        kinfra: KInfra,
        enable_fallback_layer: bool = True,
        enable_resource_management: bool = True,
    ):
        """Initialize service manager."""
        self.kinfra = kinfra
        self.services: dict[str, ServiceConfig] = {}
        self.resources: dict[str, ResourceConfig] = {}
        self.service_status: dict[str, ServiceStatus] = {}
        self.resource_status: dict[str, ResourceStatus] = {}
        self.processes: dict[str, asyncio.subprocess.Process] = {}
        self.file_observers: dict[str, Any] = {}
        self._shutdown = False
        self._monitor_tasks: list[asyncio.Task] = []

        self.enable_fallback_layer = enable_fallback_layer
        self.fallback_server = None
        self.proxy_server = None
        self._fallback_started = False
        self._proxy_started = False

        self.enable_resource_management = enable_resource_management
        self.resource_manager = None
        if enable_resource_management:
            from .resource_manager import ResourceManager

            self.resource_manager = ResourceManager()

        logger.info("ServiceManager initialized")

    def add_service(self, config: ServiceConfig):
        """Add a service configuration."""
        self.services[config.name] = config
        self.service_status[config.name] = ServiceStatus(
            name=config.name, state="stopped"
        )
        logger.info(f"Added service: {config.name}")

    def add_resource(self, config: ResourceConfig):
        """Add a resource dependency configuration."""
        self.resources[config.name] = config
        self.resource_status[config.name] = ResourceStatus(
            name=config.name, available=False
        )
        logger.info(f"Added resource dependency: {config.name}")

    def add_managed_resource(self, config: Any):
        """Add a managed resource (Docker, systemd, etc.) that will be auto-started."""
        if not self.resource_manager:
            logger.warning("Resource management not enabled, ignoring managed resource")
            return

        self.resource_manager.add_resource(config)
        logger.info(f"Added managed resource: {config.name} ({config.type.value})")

    async def kill_port_processes(self, port: int) -> bool:
        """Kill any processes listening on the specified port."""
        logger.info(f"Checking for processes on port {port}")

        loop = asyncio.get_event_loop()
        killed = await loop.run_in_executor(None, kill_processes_on_port, port, 5.0)

        if killed:
            await asyncio.sleep(1.0)

        return killed

    async def check_resource(self, name: str) -> bool:
        """Check if a resource is available."""
        config = self.resources.get(name)
        if not config:
            return False

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2.0)
            result = sock.connect_ex((config.host, config.port))
            sock.close()

            available = result == 0

            self.resource_status[name] = ResourceStatus(
                name=name,
                available=available,
                last_check=datetime.now(),
                error_message=(
                    None
                    if available
                    else f"Connection failed to {config.host}:{config.port}"
                ),
            )

            return available

        except Exception as e:
            logger.exception(f"Error checking resource {name}: {e}")
            self.resource_status[name] = ResourceStatus(
                name=name,
                available=False,
                last_check=datetime.now(),
                error_message=str(e),
            )
            return False

    async def check_all_resources(self) -> dict[str, bool]:
        """Check all configured resources."""
        if not self.resources:
            return {}

        results = {}
        for name in self.resources:
            available = await self.check_resource(name)
            results[name] = available

        return results

    async def start_service(self, name: str) -> bool:
        """Start a service with full lifecycle management."""
        config = self.services.get(name)
        if not config:
            raise ServiceError(f"Service '{name}' not configured")

        status = self.service_status[name]
        status.state = "starting"

        logger.info(f"Starting service: {name}")

        from rich.console import Console
        from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn

        console = Console()

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]{task.description}"),
                BarColumn(),
                console=console,
                transient=True,
            ) as progress:
                task = progress.add_task(f"Starting {name}...", total=7)

                if config.preferred_port:
                    progress.update(
                        task,
                        description=f"[cyan]Checking port {config.preferred_port}...",
                        completed=1,
                    )
                    killed = await self.kill_port_processes(config.preferred_port)
                    if killed:
                        console.print(
                            f"  ✓ Killed existing process on port {config.preferred_port}",
                            style="yellow",
                        )

                progress.update(
                    task, description="[cyan]Allocating port...", completed=2
                )
                port = self.kinfra.allocate_port(name, config.preferred_port)
                status.port = port
                logger.info(f"Allocated port {port} for {name}")

                if (
                    self.enable_fallback_layer
                    and config.enable_fallback
                    and not self._fallback_started
                ):
                    progress.update(
                        task,
                        description="[cyan]Starting fallback server...",
                        completed=3,
                    )
                    await self._start_fallback_layer()

                progress.update(
                    task, description="[cyan]Starting process...", completed=4
                )
                env = os.environ.copy()
                if config.env:
                    env.update(config.env)

                env["PORT"] = str(port)

                command = config.command.copy()

                logger.info(f"Starting process: {' '.join(command)}")

                proc = await asyncio.create_subprocess_exec(
                    *command,
                    cwd=str(config.cwd) if config.cwd else None,
                    env=env,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                self.processes[name] = proc
                status.pid = proc.pid

                await asyncio.sleep(2.0)

                if proc.returncode is not None:
                    stderr = await proc.stderr.read()
                    error_msg = stderr.decode("utf-8", errors="ignore")[:500]
                    console.print("\n❌ Process died immediately!", style="bold red")
                    console.print(f"Error: {error_msg}", style="red")
                    raise ServiceError(f"Process died immediately: {error_msg}")

                if self.enable_fallback_layer and config.enable_fallback:
                    progress.update(
                        task, description="[cyan]Configuring fallback...", completed=5
                    )
                    await self._configure_service_fallback(name, config, port)

                progress.update(
                    task, description="[cyan]Setting up tunnel...", completed=6
                )
                if config.enable_tunnel:
                    logger.info(f"Starting tunnel for {name}")

                    try:
                        await self._kill_existing_tunnel(name)
                    except Exception:
                        pass

                    try:
                        tunnel_info = self.kinfra.start_tunnel(
                            name,
                            port,
                            domain=config.tunnel_domain,
                        )
                        status.tunnel_url = f"https://{tunnel_info.hostname}"
                        console.print(f"  ✓ Tunnel: {status.tunnel_url}", style="cyan")
                        logger.info(f"Tunnel available at: {status.tunnel_url}")
                    except Exception as e:
                        error_msg = str(e)
                        if "already exists" not in error_msg.lower():
                            console.print(
                                f"  ⚠️  Tunnel failed: {error_msg}", style="yellow"
                            )
                        logger.warning(f"Tunnel setup failed for {name}: {e}")

                progress.update(
                    task, description="[cyan]Configuring watchers...", completed=7
                )
                if config.watch_paths and WATCHDOG_AVAILABLE:
                    self._setup_file_watching(name, config)
                elif config.watch_paths and not WATCHDOG_AVAILABLE:
                    console.print(
                        "  ⚠️  watchdog not installed (auto-reload disabled)",
                        style="yellow",
                    )

                if config.health_check_url:
                    asyncio.create_task(self._check_service_health(name))

                status.state = "running"
                status.started_at = datetime.now()
                status.restart_count = 0

                if self.fallback_server:
                    self.fallback_server.update_service_status(
                        service_name=config.name,
                        status_message="Service is running",
                        port=port,
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

            console.print(
                f"✅ {name} started on port {port}"
                + (f" | PID {status.pid}" if status.pid else ""),
                style="bold green",
            )
            if status.tunnel_url:
                console.print(f"   {status.tunnel_url}", style="cyan")
            logger.info(f"Service {name} started successfully on port {port}")

            return True

        except Exception as e:
            logger.exception(f"Failed to start service {name}: {e}")
            status.state = "error"
            status.error_message = str(e)
            return False

    async def _kill_existing_tunnel(self, name: str):
        """Kill existing cloudflare tunnel and delete it from Cloudflare."""
        try:
            result = subprocess.run(
                ["pgrep", "-f", "cloudflared"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split("\n")
                for pid_str in pids:
                    try:
                        pid = int(pid_str)
                        subprocess.run(["kill", "-9", str(pid)], timeout=5)
                        logger.info(f"Killed cloudflared process {pid}")
                    except Exception:
                        pass
        except Exception as e:
            logger.debug(f"Error killing cloudflared processes: {e}")

        try:
            service_slug = name.lower().replace("_", "-")
            tunnel_name = f"{service_slug}-tunnel"

            result = subprocess.run(
                ["cloudflared", "tunnel", "list", "--output", "json"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0 and result.stdout.strip():
                import json

                tunnels = json.loads(result.stdout)
                for tunnel in tunnels:
                    if tunnel.get("name") == tunnel_name:
                        tunnel_id = tunnel.get("id")
                        logger.info(
                            f"Deleting existing tunnel: {tunnel_name} ({tunnel_id})"
                        )
                        subprocess.run(
                            ["cloudflared", "tunnel", "delete", "-f", tunnel_id],
                            capture_output=True,
                            timeout=10,
                        )
        except Exception as e:
            logger.debug(f"Error deleting tunnel from Cloudflare: {e}")

        await asyncio.sleep(2.0)

    def _setup_file_watching(self, name: str, config: ServiceConfig):
        """Set up file watching for auto-reload."""
        if not WATCHDOG_AVAILABLE:
            logger.warning(f"Watchdog not available, file watching disabled for {name}")
            return

        def on_file_change(event):
            logger.info(f"File changed for {name}: {event.src_path}")
            asyncio.create_task(self.reload_service(name))

        handler = FileChangeHandler(on_file_change, config.watch_patterns or ["*.py"])
        observer = Observer()

        for watch_path in config.watch_paths:
            if watch_path.exists():
                observer.schedule(handler, str(watch_path), recursive=True)
                logger.info(f"Watching {watch_path} for {name}")

        observer.start()
        self.file_observers[name] = observer

    async def reload_service(self, name: str) -> bool:
        """Reload a service (stop and start)."""
        logger.info(f"Reloading service: {name}")
        status = self.service_status[name]
        status.state = "reloading"

        await self.stop_service(name)
        await asyncio.sleep(1.0)
        return await self.start_service(name)

    async def _start_fallback_layer(self):
        """Start fallback server and proxy layer."""
        try:
            from .fallback_server import FallbackServer
            from .proxy_server import SmartProxyServer

            self.fallback_server = FallbackServer(port=9000)
            self.fallback_server.service_manager = self

            await self.fallback_server.start()
            self._fallback_started = True
            logger.info("Fallback server started on port 9000")

            self.proxy_server = SmartProxyServer(
                proxy_port=9100,
                fallback_port=9000,
                fallback_server=self.fallback_server,
            )
            await self.proxy_server.start()
            self._proxy_started = True
            logger.info("Smart proxy started on port 9100")

        except Exception as e:
            logger.warning(f"Failed to start fallback layer: {e}")
            self.enable_fallback_layer = False

    async def _configure_service_fallback(
        self, name: str, config: ServiceConfig, port: int
    ):
        """Configure fallback for a specific service."""
        if not self._proxy_started or not self.fallback_server:
            return

        self.proxy_server.add_upstream(config.path_prefix, port)

        self.fallback_server.set_page(
            page_type=config.fallback_page,
            service_name=config.name,
            refresh_interval=config.fallback_refresh_interval,
            message=config.fallback_message,
        )

        status = self.service_status.get(name)
        if status:
            self.fallback_server.update_service_status(
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

        logger.info(f"Configured fallback for {name} at path {config.path_prefix}")

    async def stop_service(self, name: str) -> bool:
        """Stop a service gracefully."""
        logger.info(f"Stopping service: {name}")

        if name in self.file_observers:
            self.file_observers[name].stop()
            self.file_observers[name].join(timeout=2)
            del self.file_observers[name]

        if name in self.processes:
            proc = self.processes[name]
            if proc.returncode is None:
                proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=5.0)
                except TimeoutError:
                    logger.warning(f"Process {name} did not terminate, killing...")
                    proc.kill()
            del self.processes[name]

        self.kinfra.cleanup(name)

        status = self.service_status[name]
        status.state = "stopped"
        status.pid = None
        status.port = None
        status.tunnel_url = None

        logger.info(f"Service {name} stopped")
        return True

    async def start_all(self) -> dict[str, bool]:
        """Start all configured services."""
        logger.info("Starting all services")

        if self.resource_manager and self.resource_manager.resources:
            logger.info("Starting managed system resources...")
            resource_results = await self.resource_manager.start_all()

            for resource_name, success in resource_results.items():
                if success:
                    logger.info(f"✓ Resource {resource_name} started")
                else:
                    managed_resource = self.resource_manager.resources.get(
                        resource_name
                    )
                    if managed_resource and managed_resource.config.required:
                        logger.error(
                            f"Required resource {resource_name} failed to start, aborting"
                        )
                        return dict.fromkeys(self.services, False)

        logger.info("Checking resource dependencies")
        resource_results = await self.check_all_resources()

        for name, available in resource_results.items():
            cfg = self.resources[name]
            if cfg.required and not available:
                logger.error(f"Required resource '{name}' not available")
                raise ServiceError(
                    f"Required resource '{name}' not available at {cfg.host}:{cfg.port}",
                )
            if not available:
                logger.warning(f"Optional resource '{name}' not available")

        results = {}
        for name in self.services:
            results[name] = await self.start_service(name)

        return results

    async def _check_service_health(self, name: str) -> bool:
        """Check service health via HTTP (both localhost and tunnel)."""
        config = self.services.get(name)
        status = self.service_status[name]

        if not config.health_check_url:
            return True

        localhost_healthy = False
        tunnel_healthy = False

        loop = asyncio.get_event_loop()
        url = config.health_check_url.format(port=status.port)
        localhost_healthy = await loop.run_in_executor(
            None,
            check_http_health,
            url,
            2.0,
            200,
            "GET",
        )

        if status.tunnel_url:
            tunnel_url = f"{status.tunnel_url}/health"
            tunnel_healthy = await loop.run_in_executor(
                None,
                check_http_health,
                tunnel_url,
                5.0,
                200,
                "GET",
            )

        status.last_health_check = datetime.now()

        if localhost_healthy:
            if tunnel_healthy or not status.tunnel_url:
                status.health_status = "healthy"
            else:
                status.health_status = "degraded"
        else:
            status.health_status = "unhealthy"

        return localhost_healthy

    async def _monitor_service_health(self, name: str):
        """Continuously monitor service health."""
        config = self.services.get(name)
        if not config:
            return

        while not self._shutdown:
            await asyncio.sleep(config.health_check_interval)

            status = self.service_status[name]
            if status.state != "running":
                continue

            proc = self.processes.get(name)
            if proc and proc.returncode is not None:
                logger.error(f"Service {name} process died with code {proc.returncode}")
                status.state = "error"

                if (
                    config.restart_on_failure
                    and status.restart_count < config.max_restart_attempts
                ):
                    status.restart_count += 1
                    logger.info(
                        f"Restarting {name} (attempt {status.restart_count}/{config.max_restart_attempts})",
                    )
                    await asyncio.sleep(config.restart_delay)
                    await self.start_service(name)
                    continue

            if config.health_check_url:
                healthy = await self._check_service_health(name)
                if not healthy:
                    logger.warning(f"Health check failed for {name}")

    async def _monitor_resources(self):
        """Continuously monitor resource availability."""
        while not self._shutdown:
            for name, config in self.resources.items():
                await self.check_resource(name)
                await asyncio.sleep(config.check_interval / len(self.resources))

    async def monitor(self):
        """Start continuous monitoring of services and resources."""
        logger.info("Starting continuous monitoring")

        for name in self.services:
            task = asyncio.create_task(self._monitor_service_health(name))
            self._monitor_tasks.append(task)

        task = asyncio.create_task(self._monitor_resources())
        self._monitor_tasks.append(task)

        with contextlib.suppress(asyncio.CancelledError):
            await asyncio.sleep(float("inf"))

    async def shutdown(self):
        """Shutdown all services and cleanup."""
        logger.info("Shutting down ServiceManager")
        self._shutdown = True

        for task in self._monitor_tasks:
            task.cancel()
        await asyncio.gather(*self._monitor_tasks, return_exceptions=True)

        for name in list(self.services.keys()):
            await self.stop_service(name)

        logger.info("ServiceManager shutdown complete")

    def get_status(self) -> dict[str, Any]:
        """Get comprehensive status of all services and resources."""
        return {
            "services": {
                name: {
                    "state": status.state,
                    "pid": status.pid,
                    "port": status.port,
                    "tunnel_url": status.tunnel_url,
                    "uptime": (
                        str(datetime.now() - status.started_at)
                        if status.started_at
                        else None
                    ),
                    "restart_count": status.restart_count,
                    "health_status": status.health_status,
                    "last_health_check": (
                        status.last_health_check.isoformat()
                        if status.last_health_check
                        else None
                    ),
                    "error_message": status.error_message,
                }
                for name, status in self.service_status.items()
            },
            "resources": {
                name: {
                    "available": status.available,
                    "last_check": status.last_check.isoformat()
                    if status.last_check
                    else None,
                    "error_message": status.error_message,
                }
                for name, status in self.resource_status.items()
            },
        }
