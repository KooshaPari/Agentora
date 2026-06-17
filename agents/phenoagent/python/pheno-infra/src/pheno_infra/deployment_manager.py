"""
Deployment Manager - Unified orchestration for global and tenanted resources.

Orchestrates:
- ResourceManager - Local resource lifecycle
- TenantManager - Per-project resource isolation
- GlobalRegistry - Distributed coordination

Provides a single interface for deploying resources in either:
- Global mode: Singleton resources shared across projects
- Tenanted mode: Project-scoped resources isolated per tenant
- Local mode: Single-instance resources without coordination
"""

import logging
from typing import Any

from .global_registry import GlobalResourceConfig, GlobalResourceRegistry, ResourceMode
from .resource_manager import ResourceManager

logger = logging.getLogger(__name__)


class DeploymentManager:
    """Unified deployment management for global and tenanted resources.

    Automatically handles:
    - Global resource discovery and coordination
    - Per-tenant resource isolation
    - Resource lifecycle management
    - Health monitoring and failover
    """

    def __init__(
        self,
        instance_id: str,
        project_name: str | None = None,
        nats_url: str = "nats://localhost:4222",
    ):
        """Initialize deployment manager.

        Args:
            instance_id: Unique identifier for this instance/service
            project_name: Project name (for tenanted mode). If None, uses global mode.
            nats_url: NATS server URL for global coordination
        """
        self.instance_id = instance_id
        self.project_name = project_name
        self.nats_url = nats_url

        # Component managers
        self.resource_manager = ResourceManager()
        self.global_registry = GlobalResourceRegistry(
            instance_id=instance_id,
            nats_url=nats_url,
            enable_nats=True,
        )

        # TenantManager is imported dynamically to avoid circular imports
        self.tenant_manager = None

        # Resource tracking
        self._resources: dict[str, dict[str, Any]] = {}  # Maps name -> config + metadata
        self._modes: dict[str, ResourceMode] = {}  # Maps name -> mode
        self._initialized = False

        logger.info(
            f"DeploymentManager initialized (instance: {instance_id}, project: {project_name})",
        )

    async def initialize(self) -> None:
        """
        Initialize all components.
        """
        if self._initialized:
            return

        # Initialize global registry NATS support
        await self.global_registry.initialize_nats()

        # Import and initialize TenantManager if needed
        if self.project_name:
            try:
                from .control_center.multi_tenant import TenantManager

                self.tenant_manager = TenantManager()
                logger.debug(f"Initialized TenantManager for project: {self.project_name}")
            except ImportError:
                logger.warning("TenantManager not available, tenanted mode disabled")

        self._initialized = True
        logger.info("DeploymentManager initialized")

    async def deploy_resource(
        self,
        name: str,
        config: dict[str, Any],
        mode: ResourceMode = ResourceMode.GLOBAL,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Deploy a resource.

        Args:
            name: Resource name
            config: Resource configuration (must include 'type' field)
            mode: Deployment mode (GLOBAL, TENANTED, or LOCAL)
            metadata: Additional metadata

        Returns:
            True if deployment successful

        Example:
            >>> await manager.deploy_resource(
            ...     "postgres",
            ...     {
            ...         "type": "docker",
            ...         "image": "postgres:16",
            ...         "ports": {5432: 5432},
            ...     },
            ...     mode=ResourceMode.GLOBAL,
            ... )
        """
        if not self._initialized:
            await self.initialize()

        logger.info(f"Deploying resource {name} in {mode.value} mode")

        # Store resource info
        self._resources[name] = {
            "config": config,
            "mode": mode,
            "metadata": metadata or {},
        }
        self._modes[name] = mode

        try:
            if mode == ResourceMode.GLOBAL:
                return await self._deploy_global_resource(name, config, metadata)
            if mode == ResourceMode.TENANTED:
                return await self._deploy_tenanted_resource(name, config, metadata)
            return await self._deploy_local_resource(name, config, metadata)

        except Exception as e:
            logger.exception(f"Failed to deploy resource {name}: {e}")
            return False

    async def start_resource(self, name: str) -> bool:
        """Start a resource (auto-detects mode).

        Args:
            name: Resource name

        Returns:
            True if started successfully
        """
        if not self._initialized:
            await self.initialize()

        mode = self._modes.get(name, ResourceMode.LOCAL)

        logger.info(f"Starting resource {name} (mode: {mode.value})")

        try:
            if mode in (ResourceMode.GLOBAL, ResourceMode.TENANTED):
                return await self.resource_manager.start_resource(name)
            return await self.resource_manager.start_resource(name)

        except Exception as e:
            logger.exception(f"Failed to start resource {name}: {e}")
            return False

    async def stop_resource(
        self,
        name: str,
        cleanup_global: bool = False,
    ) -> bool:
        """Stop a resource.

        Args:
            name: Resource name
            cleanup_global: If True, force cleanup of global resource
                          (only effective if this is the manager)

        Returns:
            True if stopped successfully
        """
        if not self._initialized:
            await self.initialize()

        mode = self._modes.get(name, ResourceMode.LOCAL)

        logger.info(f"Stopping resource {name} (mode: {mode.value})")

        try:
            success = await self.resource_manager.stop_resource(name)

            if success and mode == ResourceMode.GLOBAL and cleanup_global:
                # If we're the manager, remove global registration
                handle = self.global_registry._resources.get(name)
                if handle and handle.manager_id == self.instance_id:
                    del self.global_registry._resources[name]
                    logger.info(f"Removed global registration for {name}")

            return success

        except Exception as e:
            logger.exception(f"Failed to stop resource {name}: {e}")
            return False

    async def get_resource_status(self, name: str) -> dict[str, Any] | None:
        """
        Get status of a deployed resource.
        """
        if not self._initialized:
            await self.initialize()

        mode = self._modes.get(name, ResourceMode.LOCAL)

        # Get local status
        local_status = self.resource_manager.get_status(name)

        if mode == ResourceMode.GLOBAL:
            # Also get global registry info
            global_status = await self.global_registry.get_resource_status(name)
            if global_status:
                return {
                    "local": local_status,
                    "global": global_status,
                    "mode": "global",
                }

        return {"local": local_status, "mode": mode.value}

    async def discover_resource(self, name: str) -> dict[str, Any] | None:
        """Discover a resource (primarily for global resources).

        Args:
            name: Resource name

        Returns:
            Resource information if found
        """
        if not self._initialized:
            await self.initialize()

        # Try local registry first
        if name in self.resource_manager.resources:
            return await self.get_resource_status(name)

        # Try global discovery
        handle = await self.global_registry.discover_resource(name)
        if handle:
            return await self.global_registry.get_resource_status(name)

        return None

    async def list_resources(
        self,
        mode: ResourceMode | None = None,
    ) -> list[str]:
        """
        List deployed resources, optionally filtered by mode.
        """
        resources = list(self.resource_manager.resources.keys())

        if mode:
            resources = [r for r in resources if self._modes.get(r) == mode]

        return resources

    async def get_all_status(self) -> dict[str, dict[str, Any]]:
        """
        Get status of all deployed resources.
        """
        if not self._initialized:
            await self.initialize()

        status = {}
        for name in self.resource_manager.resources:
            resource_status = await self.get_resource_status(name)
            if resource_status:
                status[name] = resource_status

        return status

    # ========== Private helper methods ==========

    async def _deploy_global_resource(
        self,
        name: str,
        config: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Deploy a global (singleton) resource.
        """
        try:
            # Register in global registry first
            global_config = GlobalResourceConfig(
                name=name,
                mode=ResourceMode.GLOBAL,
                metadata=metadata or {},
            )

            handle = await self.global_registry.register_resource(global_config, metadata)

            # If we're the manager, also add to local ResourceManager
            if handle.role.value == "manager":
                self.resource_manager.add_resource(name, config)
                logger.info(f"Added global resource to ResourceManager: {name}")

            return True

        except Exception as e:
            logger.exception(f"Failed to deploy global resource {name}: {e}")
            return False

    async def _deploy_tenanted_resource(
        self,
        name: str,
        config: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Deploy a tenanted (project-scoped) resource.
        """
        if not self.project_name:
            logger.error("Cannot deploy tenanted resource without project_name")
            return False

        if not self.tenant_manager:
            logger.error("TenantManager not available")
            return False

        try:
            # Register project if not already done
            from .control_center.config import ProjectConfig

            project_config = ProjectConfig(name=self.project_name)
            self.tenant_manager.register_project(project_config)

            # Add to local ResourceManager
            self.resource_manager.add_resource(name, config)

            # Store metadata for tenanted resource
            if "metadata" not in config:
                config["metadata"] = {}
            config["metadata"]["tenant"] = self.project_name

            logger.info(f"Added tenanted resource: {name} (tenant: {self.project_name})")
            return True

        except Exception as e:
            logger.exception(f"Failed to deploy tenanted resource {name}: {e}")
            return False

    async def _deploy_local_resource(
        self,
        name: str,
        config: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Deploy a local-only resource.
        """
        try:
            self.resource_manager.add_resource(name, config)
            logger.info(f"Added local resource: {name}")
            return True

        except Exception as e:
            logger.exception(f"Failed to deploy local resource {name}: {e}")
            return False

    # ========== Lifecycle management ==========

    async def start_all(self) -> dict[str, bool]:
        """
        Start all deployed resources.
        """
        if not self._initialized:
            await self.initialize()

        return await self.resource_manager.start_all()

    async def stop_all(self) -> None:
        """
        Stop all deployed resources.
        """
        if self._initialized:
            await self.resource_manager.stop_all()

    async def shutdown(self) -> None:
        """
        Shutdown the deployment manager.
        """
        logger.info("Shutting down DeploymentManager")

        # Stop all resources
        await self.stop_all()

        # Shutdown global registry
        await self.global_registry.shutdown()

        logger.info("DeploymentManager shutdown complete")

    # ========== Context manager support ==========

    async def __aenter__(self):
        """
        Async context manager entry.
        """
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Async context manager exit.
        """
        await self.shutdown()
