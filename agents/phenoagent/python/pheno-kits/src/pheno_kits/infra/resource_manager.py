"""
Resource Manager V2 - Adapter-based resource management

Simplified resource manager using the generic adapter pattern.
All resource-specific logic is in adapters, making this class thin and extensible.
"""

import asyncio
import logging
from typing import Any

from .adapters import ResourceAdapter, resource_from_dict

logger = logging.getLogger(__name__)


class ResourceManager:
    """Manages system resources using adapter pattern.

    This is now a thin orchestration layer. All resource-specific logic is in adapters
    (Docker, systemd, command, etc.).
    """

    def __init__(self):
        """
        Initialize resource manager.
        """
        self.resources: dict[str, ResourceAdapter] = {}
        self._health_monitor_tasks: dict[str, asyncio.Task] = {}
        self._shutdown = False

        logger.info("ResourceManager initialized (adapter-based)")

    def add_resource(self, name: str, config: dict[str, Any]) -> ResourceAdapter:
        """Add a resource from configuration dictionary.

        Args:
            name: Resource name
            config: Resource configuration (must include 'type' field)

        Returns:
            Created ResourceAdapter instance

        Example:
            >>> manager.add_resource("postgres", {
            ...     "type": "docker",
            ...     "image": "postgres:16",
            ...     "ports": {5432: 5432},
            ...     "environment": {"POSTGRES_PASSWORD": "secret"}
            ... })
        """
        adapter = resource_from_dict(name, config)
        self.resources[name] = adapter
        logger.info(f"Added resource: {name} ({config.get('type')})")
        return adapter

    def add_resource_adapter(self, adapter: ResourceAdapter):
        """Add a pre-configured resource adapter.

        Args:
            adapter: ResourceAdapter instance

        Example:
            >>> from kinfra.adapters.docker import DockerAdapter
            >>> adapter = DockerAdapter("my-db", {...})
            >>> manager.add_resource_adapter(adapter)
        """
        self.resources[adapter.name] = adapter
        logger.info(f"Added resource adapter: {adapter.name}")

    async def start_resource(self, name: str, monitor_health: bool = True) -> bool:
        """Start a resource.

        Args:
            name: Resource name
            monitor_health: Enable continuous health monitoring (default: True)

        Returns:
            True if started successfully
        """
        adapter = self.resources.get(name)
        if not adapter:
            logger.error(f"Resource {name} not found")
            return False

        logger.info(f"Starting resource: {name}")

        try:
            success = await adapter.start()

            if success and monitor_health:
                # Start health monitoring task
                task = asyncio.create_task(self._monitor_health(name))
                self._health_monitor_tasks[name] = task

            return success

        except Exception as e:
            logger.exception(f"Failed to start resource {name}: {e}")
            return False

    async def stop_resource(self, name: str) -> bool:
        """
        Stop a resource.
        """
        adapter = self.resources.get(name)
        if not adapter:
            return False

        # Stop health monitoring
        if name in self._health_monitor_tasks:
            self._health_monitor_tasks[name].cancel()
            del self._health_monitor_tasks[name]

        logger.info(f"Stopping resource: {name}")

        try:
            return await adapter.stop()
        except Exception as e:
            logger.exception(f"Failed to stop resource {name}: {e}")
            return False

    async def start_all(self) -> dict[str, bool]:
        """
        Start all configured resources.
        """
        results = {}

        for name in self.resources:
            success = await self.start_resource(name)
            results[name] = success

        return results

    async def stop_all(self):
        """
        Stop all managed resources.
        """
        self._shutdown = True

        logger.info("Stopping all managed resources...")

        for name in list(self.resources.keys()):
            await self.stop_resource(name)

        logger.info("All resources stopped")

    async def _monitor_health(self, name: str):
        """
        Monitor resource health continuously.
        """
        adapter = self.resources.get(name)
        if not adapter:
            return

        try:
            while not self._shutdown:
                healthy = await adapter.check_health()

                if not healthy:
                    logger.warning(f"Resource {name} unhealthy, attempting restart...")
                    await adapter.restart()

                await asyncio.sleep(5.0)  # Check every 5 seconds

        except asyncio.CancelledError:
            logger.debug(f"Health monitoring stopped for {name}")

    def get_status(self, name: str) -> dict[str, Any] | None:
        """
        Get status of a resource.
        """
        adapter = self.resources.get(name)
        if not adapter:
            return None

        state = adapter.get_state()

        return {
            "name": state.name,
            "running": state.running,
            "healthy": state.healthy,
            "pid": state.pid,
            "container_id": state.container_id,
            "port": state.port,
            "error": state.error,
            "metadata": state.metadata,
        }

    def get_all_status(self) -> dict[str, dict[str, Any]]:
        """
        Get status of all resources.
        """
        return {name: self.get_status(name) for name in self.resources}


# Convenience function
async def manage_resources(resources_config: dict[str, dict[str, Any]]):
    """Manage multiple resources from configuration.

    Args:
        resources_config: Dict mapping resource names to their configs

    Example:
        >>> await manage_resources({
        ...     "postgres": {"type": "docker", "image": "postgres:16", ...},
        ...     "redis": {"type": "docker", "image": "redis:7", ...}
        ... })
    """
    manager = ResourceManager()

    for name, config in resources_config.items():
        manager.add_resource(name, config)

    await manager.start_all()

    try:
        # Keep running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await manager.stop_all()
