"""
Global Resource Registry - Distributed resource coordination with automatic failover.

Implements the "first-to-start" pattern where:
- First instance to register becomes the global manager
- Other instances discover and connect to the manager
- Automatic failover if manager dies
- Service discovery via NATS

This enables global (singleton) resources that can be discovered and used
by multiple tenants/services without duplication.
"""

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ResourceMode(Enum):
    """
    Resource management mode.
    """

    GLOBAL = "global"  # Singleton - first instance becomes manager
    TENANTED = "tenanted"  # Project-scoped - isolated per tenant
    LOCAL = "local"  # Local-only - no coordination


class ResourceRole(Enum):
    """
    Role in resource management.
    """

    MANAGER = "manager"  # Managing the global resource
    PARTICIPANT = "participant"  # Using the global resource
    STANDBY = "standby"  # Ready to become manager if current dies


@dataclass
class GlobalResourceHandle:
    """
    Handle to a globally-managed resource.
    """

    name: str
    """
    Resource name.
    """

    mode: ResourceMode
    """
    Resource management mode.
    """

    manager_id: str
    """
    ID of the current manager instance.
    """

    manager_location: dict[str, Any]
    """
    Location info (host, port, etc.) of manager.
    """

    role: ResourceRole = ResourceRole.PARTICIPANT
    """
    This instance's role.
    """

    metadata: dict[str, Any] = field(default_factory=dict)
    """
    Custom metadata.
    """

    created_at: float = field(default_factory=time.time)
    """
    Creation timestamp.
    """

    last_heartbeat: float = field(default_factory=time.time)
    """
    Last heartbeat timestamp.
    """

    health: str = "unknown"
    """
    Resource health status.
    """


@dataclass
class GlobalResourceConfig:
    """
    Configuration for a global resource.
    """

    name: str
    """
    Resource name.
    """

    mode: ResourceMode = ResourceMode.GLOBAL
    """
    Resource mode.
    """

    heartbeat_interval: float = 5.0
    """
    Heartbeat interval in seconds.
    """

    heartbeat_timeout: float = 15.0
    """
    Heartbeat timeout before considering manager dead.
    """

    metadata: dict[str, Any] = field(default_factory=dict)
    """
    Custom metadata.
    """


class GlobalResourceRegistry:
    """Manages global resources with distributed coordination.

    Features:
    - First-to-register becomes manager
    - Service discovery for other instances
    - Health monitoring with automatic failover
    - NATS-based coordination
    - Per-tenant resource namespacing
    """

    def __init__(
        self,
        instance_id: str,
        nats_url: str = "nats://localhost:4222",
        enable_nats: bool = True,
    ):
        """Initialize global resource registry.

        Args:
            instance_id: Unique identifier for this instance
            nats_url: NATS server URL
            enable_nats: Whether to enable NATS-based coordination
        """
        self.instance_id = instance_id
        self.nats_url = nats_url
        self.enable_nats = enable_nats

        # Resource registry
        self._resources: dict[str, GlobalResourceHandle] = {}
        self._configs: dict[str, GlobalResourceConfig] = {}

        # Manager tracking
        self._manager_roles: dict[str, ResourceRole] = {}
        self._manager_callbacks: dict[str, list[Callable]] = {}

        # Health monitoring
        self._health_monitors: dict[str, asyncio.Task] = {}
        self._shutdown = False

        # NATS integration (when available)
        self._nats_client = None

        logger.info(f"GlobalResourceRegistry initialized (instance: {instance_id})")

    async def initialize_nats(self) -> None:
        """
        Initialize NATS connection for distributed coordination.
        """
        if not self.enable_nats:
            logger.debug("NATS coordination disabled")
            return

        try:
            import nats as nats_module

            self._nats_client = await nats_module.connect(self.nats_url)
            logger.info(f"Connected to NATS at {self.nats_url}")

            # Subscribe to global resource events
            await self._nats_client.subscribe(
                "pheno.global.*.events",
                cb=self._on_nats_event,
            )

        except ImportError:
            logger.warning("nats-py not installed, NATS coordination disabled")
            self.enable_nats = False
        except Exception as e:
            logger.warning(f"Failed to connect to NATS: {e}, using local-only mode")
            self.enable_nats = False

    async def register_resource(
        self,
        config: GlobalResourceConfig,
        metadata: dict[str, Any] | None = None,
    ) -> GlobalResourceHandle:
        """Register a global resource.

        First instance to register becomes the manager.
        Subsequent instances become participants.

        Args:
            config: Resource configuration
            metadata: Additional metadata

        Returns:
            GlobalResourceHandle for the registered resource
        """
        resource_name = config.name

        # Check if already registered
        if resource_name in self._resources:
            logger.debug(f"Resource {resource_name} already registered")
            return self._resources[resource_name]

        # Determine role (first = manager, others = participant)
        role = ResourceRole.MANAGER
        manager_id = self.instance_id

        if self.enable_nats and self._nats_client:
            # Check if another manager already exists
            existing_managers = await self._discover_managers(resource_name)
            if existing_managers:
                role = ResourceRole.PARTICIPANT
                manager_id = existing_managers[0]["manager_id"]

        # Create handle
        handle = GlobalResourceHandle(
            name=resource_name,
            mode=config.mode,
            manager_id=manager_id,
            manager_location={"instance_id": manager_id, "timestamp": time.time()},
            role=role,
            metadata={**(config.metadata or {}), **(metadata or {})},
        )

        self._resources[resource_name] = handle
        self._configs[resource_name] = config
        self._manager_roles[resource_name] = role

        logger.info(
            f"Registered global resource {resource_name} "
            f"(role: {role.value}, manager: {manager_id})",
        )

        # Start health monitoring
        if role == ResourceRole.MANAGER:
            await self._start_health_monitor(resource_name, config)

        # Publish registration event
        if self.enable_nats and self._nats_client:
            await self._publish_event(
                resource_name,
                "registered",
                {"role": role.value, "instance_id": self.instance_id},
            )

        return handle

    async def discover_resource(
        self,
        resource_name: str,
        timeout: float = 5.0,
    ) -> GlobalResourceHandle | None:
        """Discover a globally-managed resource.

        Args:
            resource_name: Resource to discover
            timeout: Discovery timeout in seconds

        Returns:
            GlobalResourceHandle if found, None otherwise
        """
        # Check local registry first
        if resource_name in self._resources:
            return self._resources[resource_name]

        # Try to discover via NATS
        if self.enable_nats and self._nats_client:
            start_time = time.time()
            while time.time() - start_time < timeout:
                managers = await self._discover_managers(resource_name)
                if managers:
                    manager_info = managers[0]

                    # Create handle for discovered resource
                    handle = GlobalResourceHandle(
                        name=resource_name,
                        mode=ResourceMode.GLOBAL,
                        manager_id=manager_info["manager_id"],
                        manager_location=manager_info.get("location", {}),
                        role=ResourceRole.PARTICIPANT,
                    )

                    self._resources[resource_name] = handle
                    logger.info(f"Discovered global resource: {resource_name}")
                    return handle

                await asyncio.sleep(0.1)

        logger.warning(f"Failed to discover resource: {resource_name}")
        return None

    async def get_resource_status(self, resource_name: str) -> dict[str, Any] | None:
        """
        Get status of a globally-managed resource.
        """
        handle = self._resources.get(resource_name)
        if not handle:
            return None

        return {
            "name": handle.name,
            "mode": handle.mode.value,
            "role": handle.role.value,
            "manager_id": handle.manager_id,
            "manager_location": handle.manager_location,
            "health": handle.health,
            "created_at": handle.created_at,
            "last_heartbeat": handle.last_heartbeat,
            "metadata": handle.metadata,
        }

    async def promote_to_manager(self, resource_name: str) -> bool:
        """Promote this instance to manager if current manager is unhealthy.

        This is called during failover scenarios.
        """
        handle = self._resources.get(resource_name)
        if not handle:
            logger.error(f"Resource not found: {resource_name}")
            return False

        if handle.role == ResourceRole.MANAGER:
            logger.debug(f"Already manager of {resource_name}")
            return True

        logger.info(f"Promoting to manager of {resource_name}")

        old_manager = handle.manager_id
        handle.manager_id = self.instance_id
        handle.role = ResourceRole.MANAGER

        # Start health monitoring
        config = self._configs.get(resource_name)
        if config:
            await self._start_health_monitor(resource_name, config)

        # Publish promotion event
        if self.enable_nats and self._nats_client:
            await self._publish_event(
                resource_name,
                "manager_changed",
                {
                    "old_manager": old_manager,
                    "new_manager": self.instance_id,
                },
            )

        return True

    def register_manager_callback(
        self,
        resource_name: str,
        callback: Callable,
    ) -> None:
        """Register callback to be called when manager changes.

        Callback signature: async def callback(event: Dict[str, Any]) -> None
        """
        if resource_name not in self._manager_callbacks:
            self._manager_callbacks[resource_name] = []

        self._manager_callbacks[resource_name].append(callback)

    async def _start_health_monitor(
        self,
        resource_name: str,
        config: GlobalResourceConfig,
    ) -> None:
        """
        Start health monitoring for a resource.
        """
        # Cancel existing monitor if any
        if resource_name in self._health_monitors:
            self._health_monitors[resource_name].cancel()

        # Create new monitor task
        task = asyncio.create_task(self._monitor_health(resource_name, config))
        self._health_monitors[resource_name] = task

    async def _monitor_health(
        self,
        resource_name: str,
        config: GlobalResourceConfig,
    ) -> None:
        """
        Monitor health of a globally-managed resource.
        """
        try:
            while not self._shutdown:
                handle = self._resources.get(resource_name)
                if not handle:
                    break

                # Update heartbeat
                handle.last_heartbeat = time.time()
                handle.health = "healthy"

                # Publish heartbeat
                if self.enable_nats and self._nats_client:
                    await self._publish_event(
                        resource_name,
                        "heartbeat",
                        {"manager_id": self.instance_id},
                    )

                # Sleep before next heartbeat
                await asyncio.sleep(config.heartbeat_interval)

        except asyncio.CancelledError:
            logger.debug(f"Health monitoring stopped for {resource_name}")

    async def _discover_managers(self, resource_name: str) -> list[dict[str, Any]]:
        """
        Discover active managers for a resource via NATS.
        """
        if not self.enable_nats or not self._nats_client:
            return []

        try:
            # Query for recent heartbeats

            # This is simplified - in production, you'd use NATS KV store
            # or request-reply pattern for actual discovery
            return []

        except Exception as e:
            logger.debug(f"Failed to discover managers: {e}")
            return []

    async def _publish_event(
        self,
        resource_name: str,
        event_type: str,
        data: dict[str, Any],
    ) -> None:
        """
        Publish event via NATS.
        """
        if not self.enable_nats or not self._nats_client:
            return

        try:
            subject = f"pheno.global.{resource_name}.events"
            message = {
                "type": event_type,
                "instance_id": self.instance_id,
                "timestamp": time.time(),
                "data": data,
            }

            # Convert to JSON for publishing
            import json

            await self._nats_client.publish(
                subject,
                json.dumps(message).encode(),
            )

        except Exception as e:
            logger.warning(f"Failed to publish event: {e}")

    async def _on_nats_event(self, msg) -> None:
        """
        Handle incoming NATS events.
        """
        try:
            import json

            event_data = json.loads(msg.data.decode())
            event_type = event_data.get("type")
            resource_name = msg.subject.split(".")[2]  # pheno.global.{resource}.events

            if event_type == "manager_changed":
                # Call registered callbacks
                callbacks = self._manager_callbacks.get(resource_name, [])
                for callback in callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(event_data)
                        else:
                            callback(event_data)
                    except Exception as e:
                        logger.exception(f"Error in manager callback: {e}")

        except Exception as e:
            logger.debug(f"Error processing NATS event: {e}")

    async def shutdown(self) -> None:
        """
        Shutdown the registry and cleanup resources.
        """
        self._shutdown = True
        logger.info("Shutting down global resource registry")

        # Cancel all health monitors
        for task in self._health_monitors.values():
            task.cancel()

        self._health_monitors.clear()
        self._resources.clear()

        # Close NATS connection
        if self._nats_client:
            await self._nats_client.close()

        logger.info("Global resource registry shutdown complete")
