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
import json
import logging
import signal
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .exceptions import KInfraError
from .kinfra import KInfra
from .service_manager import ServiceConfig, ServiceManager, ServiceStatus

logger = logging.getLogger(__name__)


class OrchestrationError(KInfraError):
    """
    Raised when orchestration operations fail.
    """



@dataclass
class OrchestratorConfig:
    """
    Configuration for the orchestrator.
    """

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

    def __init__(self, config: OrchestratorConfig, kinfra: KInfra | None = None):
        """Initialize orchestrator.

        Args:
            config: Orchestrator configuration
            kinfra: Optional KInfra instance (creates new if not provided)
        """
        self.config = config
        self.kinfra = kinfra or KInfra(project_name=config.project_name)
        self.service_manager = ServiceManager(self.kinfra)

        # State management
        self.state_dir = config.state_dir or Path.home() / ".kinfra" / "orchestrator"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.state_dir / f"{config.project_name}_state.json"

        # Service ordering for dependencies
        self.startup_order: list[str] = []
        self.shutdown_order: list[str] = []

        # Shutdown flag
        self._shutdown_requested = False

        # Register signal handlers
        self._setup_signal_handlers()

        logger.info(f"Orchestrator initialized for project: {config.project_name}")

    def _setup_signal_handlers(self):
        """
        Setup signal handlers for graceful shutdown.
        """

        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            self._shutdown_requested = True

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def add_service(self, config: ServiceConfig, depends_on: list[str] | None = None):
        """Add a service to the orchestrator.

        Args:
            config: Service configuration
            depends_on: List of service names this service depends on
        """
        self.service_manager.add_service(config)

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
        """
        Start services sequentially in dependency order.
        """
        for service_name in self.startup_order:
            if self._shutdown_requested:
                logger.info("Shutdown requested during startup, aborting...")
                return False

            logger.info(f"Starting service: {service_name}")
            try:
                success = await self.service_manager.start_service(service_name)
                if not success:
                    logger.error(f"Failed to start {service_name}")
                    if not self.config.auto_restart:
                        return False
            except Exception as e:
                logger.exception(f"Error starting {service_name}: {e}")
                return False

        logger.info("✅ All services started successfully")
        return True

    async def _start_parallel(self) -> bool:
        """
        Start services in parallel (ignoring dependencies).
        """
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
        """
        Stop all services and managed resources gracefully.
        """
        logger.info(f"Stopping {len(self.shutdown_order)} services...")

        # Stop services first (in reverse dependency order)
        for service_name in self.shutdown_order:
            logger.info(f"Stopping service: {service_name}")
            try:
                await self.service_manager.stop_service(service_name)
            except Exception as e:
                logger.warning(f"Error stopping {service_name}: {e}")

        # Stop managed resources (Docker containers, etc.)
        if self.service_manager.resource_manager:
            logger.info("Stopping managed system resources...")
            await self.service_manager.resource_manager.stop_all()

        logger.info("✅ All services and resources stopped")

    async def monitor(self):
        """Monitor all services and handle failures.

        Runs until shutdown is requested.
        """
        logger.info("📊 Monitoring services (Ctrl+C to stop)...")

        try:
            while not self._shutdown_requested:
                # Let service manager handle monitoring
                await asyncio.sleep(1)

                # Save state periodically
                if self.config.save_state:
                    self._save_state()

        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        finally:
            await self.stop_all()

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
