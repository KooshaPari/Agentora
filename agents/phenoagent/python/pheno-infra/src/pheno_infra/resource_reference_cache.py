"""
Resource Reference Cache - Conditional global resource reuse

Implements intelligent resource sharing where:
- Global resources can be conditionally reused by projects
- Reference counting prevents premature cleanup
- Resource discovery and dependency resolution
- Automatic fallback to project-scoped resources

This enables efficient resource utilization while maintaining project isolation.
"""

import asyncio
import contextlib
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .global_registry import GlobalResourceHandle, ResourceMode

logger = logging.getLogger(__name__)


class ResourceReuseStrategy(Enum):
    """
    Strategy for reusing global resources.
    """

    ALWAYS = "always"  # Always try to reuse if available
    CONDITIONAL = "conditional"  # Reuse based on compatibility checks
    NEVER = "never"  # Never reuse, always create project-scoped
    SMART = "smart"  # Use heuristics to determine best strategy


@dataclass
class ResourceReference:
    """
    Reference to a resource with metadata about usage.
    """

    resource_name: str
    """
    Name of the referenced resource.
    """

    mode: ResourceMode
    """
    Resource mode (GLOBAL, TENANTED, LOCAL).
    """

    reference_count: int = 1
    """
    Number of references to this resource.
    """

    created_at: float = field(default_factory=time.time)
    """
    When this reference was created.
    """

    last_accessed: float = field(default_factory=time.time)
    """
    When this resource was last accessed.
    """

    metadata: dict[str, Any] = field(default_factory=dict)
    """
    Additional metadata about the reference.
    """

    compatibility_score: float = 1.0
    """
    Compatibility score (0.0 to 1.0) for conditional reuse.
    """

    is_healthy: bool = True
    """
    Whether the referenced resource is healthy.
    """

    projects: set[str] = field(default_factory=set)
    """
    Projects currently referencing this resource.
    """

    resource_type: str | None = None
    """
    Declared resource type (e.g., postgres, redis).
    """

    config_signature: str | None = None
    """
    Fingerprint of the configuration used to create the resource.
    """


@dataclass
class ResourceDependency:
    """
    Dependency relationship between resources.
    """

    resource_name: str
    """
    Name of the resource that has dependencies.
    """

    dependencies: list[str]
    """
    List of resource names this resource depends on.
    """

    optional_dependencies: list[str] = field(default_factory=list)
    """
    Optional dependencies that can be missing.
    """

    compatibility_requirements: dict[str, dict[str, Any]] = field(default_factory=dict)
    """
    Compatibility requirements for each dependency.
    """


class ResourceReferenceCache:
    """
    Manages resource references and conditional reuse.

    Features:
    - Reference counting for global resources
    - Compatibility checking for conditional reuse
    - Dependency resolution and validation
    - Automatic cleanup of unused resources
    - Resource discovery and fallback strategies
    """

    def __init__(
        self,
        global_registry,
        deployment_manager,
        default_strategy: ResourceReuseStrategy = ResourceReuseStrategy.SMART,
    ):
        """Initialize resource reference cache.

        Args:
            global_registry: GlobalResourceRegistry instance
            deployment_manager: DeploymentManager instance
            default_strategy: Default reuse strategy
        """
        self.global_registry = global_registry
        self.deployment_manager = deployment_manager
        self.default_strategy = default_strategy

        # Reference tracking
        self._references: dict[str, ResourceReference] = {}  # resource_name -> reference
        self._project_references: dict[str, set[str]] = {}  # project -> set of resources
        self._resource_dependencies: dict[str, ResourceDependency] = {}  # resource -> dependencies

        # Compatibility rules
        self._compatibility_rules: dict[str, dict[str, Any]] = {}

        # Cleanup tracking
        self._cleanup_threshold = 300.0  # 5 minutes
        self._cleanup_task: asyncio.Task | None = None
        self._shutdown = False

        logger.info(f"ResourceReferenceCache initialized (strategy: {default_strategy.value})")

    async def initialize(self) -> None:
        """Initialize the cache and start background tasks."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_unused_references())

        logger.info("ResourceReferenceCache initialized")

    async def get_or_create_resource(
        self,
        resource_name: str,
        project_name: str,
        config: dict[str, Any],
        mode: ResourceMode = ResourceMode.TENANTED,
        strategy: ResourceReuseStrategy | None = None,
        dependencies: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[bool, GlobalResourceHandle | None]:
        """
        Get existing resource or create new one based on strategy.

        Args:
            resource_name: Name of the resource
            project_name: Project requesting the resource
            config: Resource configuration
            mode: Desired resource mode
            strategy: Reuse strategy (uses default if None)
            dependencies: List of resource dependencies

        Returns:
            Tuple of (is_reused, resource_handle)
        """
        strategy = strategy or self.default_strategy
        metadata = metadata or {}
        resource_type = config.get("type")
        config_signature = self._compute_signature(config)
        metadata.setdefault("resource_type", resource_type)
        metadata.setdefault("config_signature", config_signature)

        # Check if we can reuse an existing global resource
        if mode == ResourceMode.TENANTED and strategy != ResourceReuseStrategy.NEVER:
            existing_handle = await self._try_reuse_global_resource(
                resource_name, project_name, config, strategy, metadata,
            )
            if existing_handle:
                await self._add_reference(resource_name, project_name, mode, metadata)
                logger.info(f"Reusing global resource {resource_name} for project {project_name}")
                return True, existing_handle

        # Create new project-scoped resource
        resource_metadata = {"project": project_name, **metadata}
        success = await self.deployment_manager.deploy_resource(
            resource_name, config, mode, resource_metadata,
        )

        if success:
            await self._add_reference(resource_name, project_name, mode, metadata)
            logger.info(
                f"Created new {mode.value} resource {resource_name} for project {project_name}",
            )
            return False, None

        return False, None

    async def release_resource(
        self,
        resource_name: str,
        project_name: str,
        force_cleanup: bool = False,
    ) -> bool:
        """
        Release a resource reference.

        Args:
            resource_name: Name of the resource to release
            project_name: Project releasing the resource
            force_cleanup: Force cleanup even if other projects are using it

        Returns:
            True if resource was released/cleaned up
        """
        reference = self._references.get(resource_name)
        if not reference:
            logger.warning(f"No reference found for resource {resource_name}")
            return False

        # Remove project reference
        if resource_name in self._project_references.get(project_name, set()):
            self._project_references[project_name].discard(resource_name)
            if project_name in reference.projects:
                reference.projects.discard(project_name)
            reference.reference_count = max(reference.reference_count - 1, 0)

        # Check if resource can be cleaned up
        if reference.reference_count <= 0 or force_cleanup:
            await self._cleanup_resource(resource_name)
            return True

        logger.info(
            f"Released reference to {resource_name} (remaining: {reference.reference_count})",
        )
        return True

    async def get_project_resources(self, project_name: str) -> list[str]:
        """
        Get all resources used by a project.

        Args:
            project_name: Project name

        Returns:
            List of resource names
        """
        return list(self._project_references.get(project_name, set()))

    async def get_resource_dependencies(
        self,
        resource_name: str,
        project_name: str,
    ) -> list[str]:
        """
        Get dependencies for a resource within a project context.

        Args:
            resource_name: Resource name
            project_name: Project name

        Returns:
            List of dependency resource names
        """
        dependency_info = self._resource_dependencies.get(resource_name)
        if not dependency_info:
            return []

        # Filter dependencies based on project context
        project_resources = await self.get_project_resources(project_name)
        return [
            dep for dep in dependency_info.dependencies if dep in project_resources
        ]


    async def validate_dependencies(
        self,
        resource_name: str,
        project_name: str,
    ) -> tuple[bool, list[str]]:
        """
        Validate that all required dependencies are available.

        Args:
            resource_name: Resource name
            project_name: Project name

        Returns:
            Tuple of (is_valid, missing_dependencies)
        """
        dependency_info = self._resource_dependencies.get(resource_name)
        if not dependency_info:
            return True, []

        project_resources = await self.get_project_resources(project_name)
        missing = [dep for dep in dependency_info.dependencies if dep not in project_resources]

        return len(missing) == 0, missing

    def set_compatibility_rule(
        self,
        resource_type: str,
        rule: dict[str, Any],
    ) -> None:
        """
        Set compatibility rule for a resource type.

        Args:
            resource_type: Type of resource (e.g., 'postgres', 'redis')
            rule: Compatibility rule configuration
        """
        self._compatibility_rules[resource_type] = rule
        logger.info(f"Set compatibility rule for {resource_type}")

    def add_resource_dependency(
        self,
        resource_name: str,
        dependency: ResourceDependency,
    ) -> None:
        """
        Add dependency information for a resource.

        Args:
            resource_name: Resource name
            dependency: Dependency information
        """
        self._resource_dependencies[resource_name] = dependency
        logger.info(f"Added dependencies for {resource_name}: {dependency.dependencies}")

    async def get_cache_status(self) -> dict[str, Any]:
        """
        Get current cache status and statistics.

        Returns:
            Cache status information
        """
        total_references = len(self._references)
        project_count = len(self._project_references)

        resource_stats = {}
        for resource_name, reference in self._references.items():
            resource_stats[resource_name] = {
                "reference_count": reference.reference_count,
                "mode": reference.mode.value,
                "is_healthy": reference.is_healthy,
                "last_accessed": reference.last_accessed,
                "compatibility_score": reference.compatibility_score,
                "projects": sorted(reference.projects),
                "resource_type": reference.resource_type,
                "config_signature": reference.config_signature,
            }

        return {
            "total_references": total_references,
            "project_count": project_count,
            "resources": resource_stats,
            "dependencies": {
                name: {
                    "dependencies": dep.dependencies,
                    "optional_dependencies": dep.optional_dependencies,
                }
                for name, dep in self._resource_dependencies.items()
            },
        }

    # ========== Private helper methods ==========

    async def _try_reuse_global_resource(
        self,
        resource_name: str,
        project_name: str,
        config: dict[str, Any],
        strategy: ResourceReuseStrategy,
        metadata: dict[str, Any],
    ) -> GlobalResourceHandle | None:
        """
        Try to reuse an existing global resource.
        """
        # Discover existing global resource
        handle = await self.global_registry.discover_resource(resource_name)
        if not handle:
            return None

        # Check compatibility based on strategy
        if strategy == ResourceReuseStrategy.ALWAYS:
            return handle
        if strategy == ResourceReuseStrategy.NEVER:
            return None
        if strategy == ResourceReuseStrategy.CONDITIONAL:
            if await self._check_compatibility(resource_name, config, handle, metadata):
                return handle
            return None
        if strategy == ResourceReuseStrategy.SMART:
            if await self._smart_reuse_check(resource_name, config, handle, metadata):
                return handle
            return None

        return None

    async def _check_compatibility(
        self,
        resource_name: str,
        config: dict[str, Any],
        handle: GlobalResourceHandle,
        metadata: dict[str, Any],
    ) -> bool:
        """
        Check if a global resource is compatible with the requested config.
        """
        # Basic compatibility checks
        resource_type = config.get("type")
        if not resource_type:
            return False

        config_signature = metadata.get("config_signature")
        if config_signature:
            existing_sig = handle.metadata.get("config_signature") if handle.metadata else None
            if existing_sig and existing_sig != config_signature:
                return False
        reference = self._references.get(resource_name)
        if reference and reference.config_signature and config_signature:
            if reference.config_signature != config_signature:
                return False

        # Check against compatibility rules
        rule = self._compatibility_rules.get(resource_type, {})
        if not rule:
            return True  # No specific rules, assume compatible

        # Check version compatibility
        required_version = config.get("version")
        if required_version and "version" in rule:
            if not self._check_version_compatibility(required_version, rule["version"]):
                return False

        # Check configuration compatibility
        required_config = config.get("config", {})
        if "required_config" in rule:
            for key, expected_value in rule["required_config"].items():
                if key not in required_config or required_config[key] != expected_value:
                    return False

        return True

    async def _smart_reuse_check(
        self,
        resource_name: str,
        config: dict[str, Any],
        handle: GlobalResourceHandle,
        metadata: dict[str, Any],
    ) -> bool:
        """
        Smart reuse check using heuristics.
        """
        # Check basic compatibility first
        if not await self._check_compatibility(resource_name, config, handle, metadata):
            return False

        # Check resource health
        if handle.health != "healthy":
            return False

        # Check if resource is underutilized
        reference = self._references.get(resource_name)
        if reference:
            if reference.reference_count > 5:  # Arbitrary threshold
                return False
            signature = metadata.get("config_signature")
            if signature and reference.config_signature and signature != reference.config_signature:
                reference.compatibility_score = max(reference.compatibility_score - 0.2, 0.0)
                return False
            reference.compatibility_score = min(reference.compatibility_score + 0.1, 1.0)

        # Check resource age (prefer newer resources)
        age_hours = (time.time() - handle.created_at) / 3600
        if age_hours > 24:  # Prefer resources less than 24 hours old
            return False

        return True

    def _check_version_compatibility(
        self,
        required_version: str,
        rule_version: str,
    ) -> bool:
        """
        Check version compatibility using semantic versioning.
        """
        # Simple version check - in production, use proper semver
        try:
            required_parts = [int(x) for x in required_version.split(".")]
            rule_parts = [int(x) for x in rule_version.split(".")]

            # Check major version compatibility
            return required_parts[0] == rule_parts[0]
        except (ValueError, IndexError):
            return False

    async def _add_reference(
        self,
        resource_name: str,
        project_name: str,
        mode: ResourceMode,
        metadata: dict[str, Any],
    ) -> None:
        """
        Add a reference to a resource.
        """
        reference = self._references.get(resource_name)
        if reference:
            reference.reference_count += 1
            reference.last_accessed = time.time()
            reference.metadata.update(metadata)
            reference.projects.add(project_name)
            if metadata.get("config_signature"):
                reference.config_signature = metadata["config_signature"]
            if metadata.get("resource_type"):
                reference.resource_type = metadata["resource_type"]
            reference.compatibility_score = min(reference.compatibility_score + 0.05, 1.0)
        else:
            reference = ResourceReference(
                resource_name=resource_name,
                mode=mode,
                metadata=dict(metadata),
                projects={project_name},
                resource_type=metadata.get("resource_type"),
                config_signature=metadata.get("config_signature"),
                compatibility_score=1.0,
            )
            self._references[resource_name] = reference

        # Track project references
        if project_name not in self._project_references:
            self._project_references[project_name] = set()
        self._project_references[project_name].add(resource_name)

    async def _cleanup_resource(self, resource_name: str) -> None:
        """
        Clean up a resource when no longer referenced.
        """
        reference = self._references.get(resource_name)
        if not reference:
            return

        # Stop the backing resource when appropriate
        if reference.mode == ResourceMode.TENANTED:
            await self.deployment_manager.stop_resource(resource_name, cleanup_global=False)
            logger.info(f"Cleaned up unused resource: {resource_name}")
        elif reference.mode == ResourceMode.GLOBAL:
            await self.deployment_manager.stop_resource(resource_name, cleanup_global=True)
            logger.info(f"Released global resource manager for: {resource_name}")

        # Remove from tracking
        del self._references[resource_name]

        # Remove from all project references
        for project_resources in self._project_references.values():
            project_resources.discard(resource_name)

    async def _cleanup_unused_references(self) -> None:
        """
        Background task to clean up unused references.
        """
        while not self._shutdown:
            try:
                current_time = time.time()
                to_cleanup = []

                for resource_name, reference in self._references.items():
                    # Clean up if not accessed recently and no references
                    if (
                        reference.reference_count <= 0
                        and current_time - reference.last_accessed > self._cleanup_threshold
                    ):
                        to_cleanup.append(resource_name)

                for resource_name in to_cleanup:
                    await self._cleanup_resource(resource_name)

                # Sleep for cleanup interval
                await asyncio.sleep(60.0)  # Check every minute

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Error in cleanup task: {e}")
                await asyncio.sleep(60.0)

    async def shutdown(self) -> None:
        """
        Shutdown the cache and cleanup resources.
        """
        self._shutdown = True

        if self._cleanup_task:
            self._cleanup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._cleanup_task

        # Cleanup all resources
        for resource_name in list(self._references.keys()):
            await self._cleanup_resource(resource_name)

        logger.info("ResourceReferenceCache shutdown complete")

    # ========== Internal helpers ==========

    @staticmethod
    def _compute_signature(config: dict[str, Any]) -> str:
        """Compute a deterministic fingerprint for a resource configuration."""
        try:
            normalized = json.dumps(config, sort_keys=True, separators=(",", ":"))
        except TypeError:
            normalized = repr(config)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
