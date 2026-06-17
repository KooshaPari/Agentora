"""
Service Orchestrator - Multi-service lifecycle management

Provides high-level orchestration for managing multiple services with:
- Sequential or parallel startup
- Graceful shutdown with dependency ordering
- Unified status reporting
- Signal handling
- State persistence
"""

import asyncio
import contextlib
import json
import logging
import os
import signal
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .exceptions import KInfraError
from .service_infra import ServiceInfraManager
from .service_manager import ServiceConfig, ServiceManager, ServiceStatus

logger = logging.getLogger(__name__)


class OrchestrationError(KInfraError):
    """Raised when orchestration operations fail."""


@dataclass
class OrchestratorConfig:
    """Configuration for the orchestrator."""

    project_name: str
    state_dir: Path | None = None
    parallel_startup: bool = False
    startup_timeout: float = 60.0
    shutdown_timeout: float = 30.0
    auto_restart: bool = True
    save_state: bool = True


class ServiceOrchestrator:
    """High-level orchestrator for managing multiple services.

    Features:
    - Multi-service lifecycle management
    - Graceful startup and shutdown
    - Signal handling (SIGINT, SIGTERM)
    - State persistence
    - Status monitoring and reporting
    """

    def __init__(
        self, config: OrchestratorConfig, service_infra: ServiceInfraManager | None = None,
    ):
        """Initialize orchestrator.

        Args:
            config: Orchestrator configuration
            service_infra: Optional ServiceInfraManager instance (creates new if not provided)
        """
        self.config = config
        self.service_infra = service_infra or ServiceInfraManager(domain=config.project_name)
        self.service_manager = ServiceManager(self.service_infra)
        self.kinfra = self.service_manager.kinfra

        # State management
        self.state_dir = config.state_dir or Path.home() / ".kinfra" / "orchestrator"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.state_dir / f"{config.project_name}_state.json"

        # Service ordering for dependencies
        self.startup_order: list[str] = []
        self.shutdown_order: list[str] = []

        # Shutdown flag
        self._shutdown_requested = False
        self._current_task = None

        # Register signal handlers
        self._setup_signal_handlers()

        logger.info(f"Orchestrator initialized for project: {config.project_name}")

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""

        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            self._shutdown_requested = True

            # Cancel current async task if running
            if self._current_task and not self._current_task.done():
                logger.info("Cancelling current async task...")
                self._current_task.cancel()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def add_service(self, config: ServiceConfig, depends_on: list[str] | None = None):
        """Add a service to the orchestrator.

        Args:
            config: Service configuration
            depends_on: List of service names this service depends on
        """
        self.service_manager.register_service(config)

        # Handle startup order based on dependencies
        if depends_on:
            # Ensure dependencies are added first in startup order
            for dep in depends_on:
                if dep not in self.startup_order:
                    self.startup_order.append(dep)

        # Add this service to startup order
        if config.name not in self.startup_order:
            self.startup_order.append(config.name)

        # Shutdown order is reverse of startup
        self.shutdown_order = list(reversed(self.startup_order))

        logger.debug(f"Added service {config.name} with dependencies: {depends_on}")

    async def start_all(self) -> bool:
        """Start all registered services.

        Returns:
            True if all services started successfully

        Raises:
            OrchestrationError: If startup fails
        """
        logger.info(f"Starting {len(self.startup_order)} services...")

        if self.config.parallel_startup:
            return await self._start_parallel()
        return await self._start_sequential()

    async def _start_sequential(self) -> bool:
        """Start services sequentially in dependency order."""
        for service_name in self.startup_order:
            if self._shutdown_requested:
                logger.info("Shutdown requested during startup, aborting...")
                raise RuntimeError("Shutdown requested during startup")

            logger.info(f"Starting service: {service_name}")
            try:
                # Track current task for signal cancellation
                self._current_task = asyncio.current_task()
                success = await self.service_manager.start_service(service_name)
                self._current_task = None

                if not success:
                    logger.error(f"Failed to start {service_name}")
                    if not self.config.auto_restart:
                        return False
            except asyncio.CancelledError:
                logger.info(f"Service startup cancelled for {service_name}")
                self._current_task = None
                raise RuntimeError(f"Service startup cancelled for {service_name}") from None
            except Exception as e:
                logger.exception(f"Error starting {service_name}: {e}")
                self._current_task = None
                raise RuntimeError(f"Error starting {service_name}: {e}") from e

        logger.info("✅ All services started successfully")
        return True

    async def _start_parallel(self) -> bool:
        """Start services in parallel (ignoring dependencies)."""
        tasks = []
        for service_name in self.startup_order:
            task = self.service_manager.start_service(service_name)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Check for failures
        failures = [
            (name, result)
            for name, result in zip(self.startup_order, results, strict=False)
            if isinstance(result, Exception) or not result
        ]

        if failures:
            for name, error in failures:
                logger.error(f"Failed to start {name}: {error}")
            return False

        logger.info("✅ All services started successfully (parallel)")
        return True

    async def stop_all(self):
        """Stop all services and managed resources gracefully."""
        logger.info(f"Stopping {len(self.shutdown_order)} services...")

        # Stop services first (in reverse dependency order)
        for service_name in self.shutdown_order:
            logger.info(f"Stopping service: {service_name}")
            try:
                await self.service_manager.stop_service(service_name)
            except Exception as e:
                logger.warning(f"Error stopping {service_name}: {e}")

        # Stop managed resources (Docker containers, etc.)
        rm = getattr(self.service_manager, "resource_manager", None)
        if rm:
            logger.info("Stopping managed system resources...")
            await rm.stop_all()

        logger.info("✅ All services and resources stopped")

    async def monitor(self):
        """Monitor all services and render a non-interactive Rich TUI panel at the
        bottom.

        Runs until shutdown is requested.
        """
        logger.info("============================================================")
        logger.info("📊 Monitoring services (Ctrl+C to stop)...")

        # Start ServiceManager health/resource monitoring in background
        sm_monitor_task = asyncio.create_task(self.service_manager.monitor())

        # Build Rich TUI if available
        try:
            from .monitoring import MonitorConfig, ServiceMonitor

            have_rich = True
        except Exception:
            have_rich = False

        if have_rich:
            # Gather proxy/fallback ports if available
            fallback_server = getattr(self.service_manager, "fallback_server", None)
            proxy_server = getattr(self.service_manager, "proxy_server", None)
            fallback_p = getattr(fallback_server, "port", None) if fallback_server else None
            proxy_p = getattr(proxy_server, "proxy_port", None) if proxy_server else None

            resources = []
            if fallback_p:
                resources.append({"name": "fallback", "port": fallback_p})
            if proxy_p:
                resources.append({"name": "proxy", "port": proxy_p})

            services = list(self.startup_order)
            if fallback_p:
                services.append("fallback")
            if proxy_p:
                services.append("proxy")

            cfg = MonitorConfig(
                project_name=self.config.project_name,
                services=services,
                domain=self.service_infra.domain,
                resources=resources,
                refresh_interval=1.0,
            )
            monitor = ServiceMonitor(cfg)

            # Attach known processes (best effort)
            for name in self.startup_order:
                proc = self.service_manager.processes.get(name)
                status = self.service_manager.service_status.get(name)
                if proc:
                    monitor.attach_process(
                        name,
                        proc,
                        port=getattr(status, "port", None),
                        tunnel_url=getattr(status, "tunnel_url", None),
                    )

            if fallback_p and fallback_server:
                monitor.attach_process(
                    "fallback",
                    process=None,
                    port=fallback_p,
                    status_getter=lambda server=fallback_server: bool(
                        getattr(server, "site", None),
                    ),
                    pid_getter=os.getpid,
                )

            if proxy_p and proxy_server:
                monitor.attach_process(
                    "proxy",
                    process=None,
                    port=proxy_p,
                    status_getter=lambda server=proxy_server: bool(getattr(server, "site", None))
                    and not getattr(server, "_shutdown", False),
                    pid_getter=os.getpid,
                )

            # Track current task for signal cancellation
            self._current_task = asyncio.current_task()
            try:
                await monitor.run()
            finally:
                monitor.stop()
                self._current_task = None
        else:
            # Fallback simple loop if Rich is unavailable
            try:
                self._current_task = asyncio.current_task()
                while not self._shutdown_requested:
                    await asyncio.sleep(1)
                    if self.config.save_state:
                        self._save_state()
            finally:
                self._current_task = None

        # Stop all on exit
        sm_monitor_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await sm_monitor_task
        await self.stop_all()
        return True

    def get_status(self) -> dict[str, ServiceStatus]:
        """
        Get status of all managed services.
        """
        return self.service_manager.service_status.copy()

    def print_status(self):
        """
        Print formatted status of all services.
        """
        logger.info("=" * 60)
        logger.info("📋 Service Status")
        logger.info("=" * 60)

        for name, status in self.get_status().items():
            logger.info(f"\n{name.upper()}:")
            logger.info(f"  State: {status.state}")
            logger.info(f"  PID: {status.pid or 'N/A'}")
            logger.info(f"  Port: {status.port or 'N/A'}")
            if status.tunnel_url:
                logger.info(f"  Tunnel: {status.tunnel_url}")
            if status.health_status != "unknown":
                logger.info(f"  Health: {status.health_status}")
            if status.error_message:
                logger.info(f"  Error: {status.error_message}")

        logger.info("=" * 60)

    def _save_state(self):
        """
        Save current orchestrator state to disk.
        """
        if not self.config.save_state:
            return

        state = {
            "project_name": self.config.project_name,
            "timestamp": datetime.now().isoformat(),
            "services": {},
        }

        for name, status in self.get_status().items():
            state["services"][name] = {
                "state": status.state,
                "pid": status.pid,
                "port": status.port,
                "tunnel_url": status.tunnel_url,
                "started_at": status.started_at.isoformat() if status.started_at else None,
                "health_status": status.health_status,
            }

        try:
            with open(self.state_file, "w") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save state: {e}")

    def load_state(self) -> dict | None:
        """
        Load saved state from disk.
        """
        if not self.state_file.exists():
            return None

        try:
            with open(self.state_file) as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load state: {e}")
            return None


async def run_orchestrator(
    config: OrchestratorConfig,
    services: list[ServiceConfig],
    dependencies: dict[str, list[str]] | None = None,
):
    """Convenience function to run orchestrator with services.

    Args:
        config: Orchestrator configuration
        services: List of service configurations
        dependencies: Optional dict mapping service names to their dependencies

    Example:
        >>> await run_orchestrator(
        ...     OrchestratorConfig(project_name="myapp"),
        ...     [api_service, frontend_service],
        ...     dependencies={"frontend": ["api"]}
        ... )
    """
    orchestrator = ServiceOrchestrator(config)

    # Add services with dependencies
    for service in services:
        deps = dependencies.get(service.name) if dependencies else None
        orchestrator.add_service(service, depends_on=deps)

    # Start and monitor
    if await orchestrator.start_all():
        orchestrator.print_status()
        await orchestrator.monitor()
    else:
        logger.error("Failed to start services")
        sys.exit(1)
