"""
Resource Coordinator - Enhanced resource management with intelligent coordination

Provides sophisticated resource management with:
- Resource dependency resolution
- Lifecycle rule enforcement
- Resource reference caching
- Automatic fallback strategies
- Resource health monitoring
- Project isolation with global resource reuse

This is the main orchestrator for Phase 3 resource coordination.
"""

import asyncio
import contextlib
import hashlib
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .deployment_manager import DeploymentManager
from .global_registry import ResourceMode
from .resource_reference_cache import (
    ResourceDependency,
    ResourceReferenceCache,
    ResourceReuseStrategy,
)

logger = logging.getLogger(__name__)


class LifecycleRule(Enum):
    """
    Rules for resource lifecycle management.
    """

    PROJECT_SCOPED = "project_scoped"  # Always create project-specific resources
    GLOBAL_REUSE = "global_reuse"  # Reuse global resources when possible
    SMART_DECISION = "smart_decision"  # Use heuristics to decide
    DEPENDENCY_DRIVEN = "dependency_driven"  # Decision based on dependencies


@dataclass
class ResourcePolicy:
    """
    Policy for managing a specific resource type.
    """

    resource_type: str
    """
    Type of resource (e.g., 'postgres', 'redis', 'api').
    """

    lifecycle_rule: LifecycleRule
    """
    Lifecycle rule for this resource type.
    """

    reuse_strategy: ResourceReuseStrategy
    """
    Strategy for reusing global resources.
    """

    dependencies: list[str] = field(default_factory=list)
    """
    Default dependencies for this resource type.
    """

    compatibility_requirements: dict[str, Any] = field(default_factory=dict)
    """
    Compatibility requirements for reuse.
    """

    cleanup_timeout: float = 300.0
    """
    Timeout for cleanup in seconds.
    """

    health_check_interval: float = 30.0
    """
    Health check interval in seconds.
    """


@dataclass
class ResourceRequest:
    """
    Request for a resource with context.
    """

    resource_name: str
    project_name: str
    config: dict[str, Any]
    mode: ResourceMode = ResourceMode.TENANTED
    dependencies: list[str] = field(default_factory=list)
    policy_override: ResourcePolicy | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class ResourceCoordinator:
    """
    Enhanced resource coordinator with intelligent management.

    Features:
    - Resource dependency resolution
    - Lifecycle rule enforcement
    - Global resource reuse with reference counting
    - Automatic fallback strategies
    - Resource health monitoring
    - Project isolation
    """

    def __init__(
        self,
        instance_id: str,
        project_name: str | None = None,
        nats_url: str = "nats://localhost:4222",
    ):
        """Initialize resource coordinator.

        Args:
            instance_id: Unique identifier for this instance
            project_name: Project name (for project-scoped coordination)
            nats_url: NATS server URL for global coordination
        """
        self.instance_id = instance_id
        self.project_name = project_name

        # Core components
        self.deployment_manager = DeploymentManager(
            instance_id=instance_id,
            project_name=project_name,
            nats_url=nats_url,
        )

        self.reference_cache = ResourceReferenceCache(
            global_registry=self.deployment_manager.global_registry,
            deployment_manager=self.deployment_manager,
        )

        # Resource policies
        self._policies: dict[str, ResourcePolicy] = {}
        self._default_policy = ResourcePolicy(
            resource_type="default",
            lifecycle_rule=LifecycleRule.SMART_DECISION,
            reuse_strategy=ResourceReuseStrategy.SMART,
        )

        # Resource tracking
        self._active_requests: dict[str, ResourceRequest] = {}
        self._resource_health: dict[str, bool] = {}

        # Health monitoring
        self._health_monitor_task: asyncio.Task | None = None
        self._shutdown = False

        logger.info(
            f"ResourceCoordinator initialized (instance: {instance_id}, project: {project_name})",
        )

    async def initialize(self) -> None:
        """Initialize the coordinator and all components."""
        await self.deployment_manager.initialize()
        await self.reference_cache.initialize()

        # Start health monitoring
        if self._health_monitor_task is None:
            self._health_monitor_task = asyncio.create_task(self._monitor_resource_health())

        logger.info("ResourceCoordinator initialized")

    def set_resource_policy(self, policy: ResourcePolicy) -> None:
        """
        Set policy for a resource type.

        Args:
            policy: Resource policy configuration
        """
        self._policies[policy.resource_type] = policy

        # Update reference cache compatibility rules
        if policy.compatibility_requirements:
            self.reference_cache.set_compatibility_rule(
                policy.resource_type,
                policy.compatibility_requirements,
            )

        logger.info(f"Set policy for {policy.resource_type}: {policy.lifecycle_rule.value}")

    async def request_resource(
        self,
        resource_name: str,
        config: dict[str, Any],
        mode: ResourceMode | None = None,
        dependencies: list[str] | None = None,
        policy_override: ResourcePolicy | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[bool, dict[str, Any] | None]:
        """
        Request a resource with intelligent coordination.

        Args:
            resource_name: Name of the resource
            config: Resource configuration
            mode: Desired resource mode (auto-detected if None)
            dependencies: List of dependency resource names
            policy_override: Override policy for this request
            metadata: Additional metadata

        Returns:
            Tuple of (success, resource_info)
        """
        if not self.project_name:
            logger.error("Cannot request resources without project context")
            return False, None

        # Determine resource type and policy
        resource_type = config.get("type", "unknown")
        policy = policy_override or self._policies.get(resource_type, self._default_policy)

        # Auto-detect mode if not specified
        if mode is None:
            mode = self._determine_resource_mode(resource_type, policy)

        config_signature = self._compute_signature(config)
        metadata = metadata or {}
        metadata.setdefault("resource_type", resource_type)
        metadata.setdefault("config_signature", config_signature)

        # Create resource request
        request = ResourceRequest(
            resource_name=resource_name,
            project_name=self.project_name,
            config=config,
            mode=mode,
            dependencies=dependencies or [],
            policy_override=policy_override,
            metadata=metadata,
        )

        self._active_requests[resource_name] = request

        try:
            # Resolve dependencies first
            if request.dependencies:
                await self._resolve_dependencies(request)

            # Request the resource
            success, handle = await self.reference_cache.get_or_create_resource(
                resource_name=resource_name,
                project_name=self.project_name,
                config=config,
                mode=mode,
                strategy=policy.reuse_strategy,
                dependencies=request.dependencies,
                metadata=request.metadata,
            )

            if success:
                # Start the resource
                start_success = await self.deployment_manager.start_resource(resource_name)
                if start_success:
                    self._resource_health[resource_name] = True

                    # Add dependency information
                    if request.dependencies:
                        dependency_info = ResourceDependency(
                            resource_name=resource_name,
                            dependencies=request.dependencies,
                        )
                        self.reference_cache.add_resource_dependency(resource_name, dependency_info)

                    resource_info = {
                        "name": resource_name,
                        "mode": mode.value,
                        "is_reused": handle is not None,
                        "dependencies": request.dependencies,
                        "health": "healthy",
                        "metadata": request.metadata,
                    }

                    logger.info(f"Successfully requested resource {resource_name}")
                    return True, resource_info
                logger.error(f"Failed to start resource {resource_name}")
                return False, None
            logger.error(f"Failed to create resource {resource_name}")
            return False, None

        except Exception as e:
            logger.exception(f"Error requesting resource {resource_name}: {e}")
            return False, None

    async def release_resource(
        self,
        resource_name: str,
        force_cleanup: bool = False,
    ) -> bool:
        """
        Release a resource and clean up if no longer needed.

        Args:
            resource_name: Name of the resource to release
            force_cleanup: Force cleanup even if other projects are using it

        Returns:
            True if resource was released
        """
        if resource_name not in self._active_requests:
            logger.warning(f"Resource {resource_name} not found in active requests")
            return False

        # Remove from active requests
        del self._active_requests[resource_name]

        # Release from reference cache
        success = await self.reference_cache.release_resource(
            resource_name, self.project_name, force_cleanup,
        )

        if success:
            # Remove from health tracking
            self._resource_health.pop(resource_name, None)
            logger.info(f"Released resource {resource_name}")

        return success

    async def get_resource_status(
        self,
        resource_name: str,
    ) -> dict[str, Any] | None:
        """
        Get status of a resource.

        Args:
            resource_name: Name of the resource

        Returns:
            Resource status information
        """
        if resource_name not in self._active_requests:
            return None

        # Get deployment manager status
        status = await self.deployment_manager.get_resource_status(resource_name)
        if not status:
            return None

        # Add coordinator-specific information
        request = self._active_requests[resource_name]
        status.update(
            {
                "project": self.project_name,
                "dependencies": request.dependencies,
                "mode": request.mode.value,
                "health": (
                    "healthy" if self._resource_health.get(resource_name, False) else "unhealthy"
                ),
                "metadata": request.metadata,
            },
        )

        return status

    async def get_project_resources(self) -> list[dict[str, Any]]:
        """
        Get all resources for the current project.

        Returns:
            List of resource information
        """
        resources = []

        for resource_name in self._active_requests:
            status = await self.get_resource_status(resource_name)
            if status:
                resources.append(status)

        return resources

    async def validate_project_dependencies(self) -> tuple[bool, list[str]]:
        """
        Validate that all project dependencies are satisfied.

        Returns:
            Tuple of (is_valid, missing_dependencies)
        """
        missing = []

        for resource_name in self._active_requests:
            is_valid, missing_deps = await self.reference_cache.validate_dependencies(
                resource_name, self.project_name,
            )
            if not is_valid:
                missing.extend(missing_deps)

        return len(missing) == 0, missing

    async def get_coordination_status(self) -> dict[str, Any]:
        """
        Get overall coordination status.

        Returns:
            Coordination status information
        """
        cache_status = await self.reference_cache.get_cache_status()

        return {
            "instance_id": self.instance_id,
            "project_name": self.project_name,
            "active_requests": len(self._active_requests),
            "resource_health": dict(self._resource_health),
            "policies": {
                name: {
                    "lifecycle_rule": policy.lifecycle_rule.value,
                    "reuse_strategy": policy.reuse_strategy.value,
                    "dependencies": policy.dependencies,
                }
                for name, policy in self._policies.items()
            },
            "cache": cache_status,
        }

    # ========== Private helper methods ==========

    @staticmethod
    def _compute_signature(config: dict[str, Any]) -> str:
        """Compute deterministic fingerprint for a resource config."""
        try:
            normalized = json.dumps(config, sort_keys=True, separators=(",", ":"))
        except TypeError:
            normalized = repr(config)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def _determine_resource_mode(
        self,
        resource_type: str,
        policy: ResourcePolicy,
    ) -> ResourceMode:
        """
        Determine the appropriate resource mode based on policy.
        """
        if policy.lifecycle_rule == LifecycleRule.PROJECT_SCOPED:
            return ResourceMode.TENANTED
        if policy.lifecycle_rule == LifecycleRule.GLOBAL_REUSE:
            return ResourceMode.GLOBAL
        if policy.lifecycle_rule == LifecycleRule.SMART_DECISION:
            # Use heuristics to decide
            if resource_type in ["postgres", "redis", "elasticsearch"]:
                return ResourceMode.GLOBAL  # These are often shared
            return ResourceMode.TENANTED  # Default to project-scoped
        return ResourceMode.TENANTED  # Default fallback

    async def _resolve_dependencies(self, request: ResourceRequest) -> None:
        """
        Resolve and ensure dependencies are available.
        """
        for dep_name in request.dependencies:
            # Check if dependency is already available
            if dep_name not in self._active_requests:
                logger.warning(f"Dependency {dep_name} not found for {request.resource_name}")
                # In a real implementation, you might want to request the dependency
                # or fail the request

    async def _monitor_resource_health(self) -> None:
        """
        Background task to monitor resource health.
        """
        while not self._shutdown:
            try:
                for resource_name in list(self._active_requests.keys()):
                    status = await self.deployment_manager.get_resource_status(resource_name)
                    if status:
                        is_healthy = status.get("local", {}).get("healthy", False)
                        self._resource_health[resource_name] = is_healthy

                        if not is_healthy:
                            logger.warning(f"Resource {resource_name} is unhealthy")

                # Sleep for monitoring interval
                await asyncio.sleep(30.0)  # Check every 30 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Error in health monitoring: {e}")
                await asyncio.sleep(30.0)

    async def shutdown(self) -> None:
        """
        Shutdown the coordinator and cleanup resources.
        """
        self._shutdown = True

        # Cancel health monitoring
        if self._health_monitor_task:
            self._health_monitor_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._health_monitor_task

        # Release all resources
        for resource_name in list(self._active_requests.keys()):
            await self.release_resource(resource_name, force_cleanup=True)

        # Shutdown components
        await self.reference_cache.shutdown()
        await self.deployment_manager.shutdown()

        logger.info("ResourceCoordinator shutdown complete")

    # ========== Context manager support ==========

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.shutdown()

    def __enter__(self):
        """Synchronous context manager entry."""
        asyncio.run(self.initialize())
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Synchronous context manager exit."""
        asyncio.run(self.shutdown())
