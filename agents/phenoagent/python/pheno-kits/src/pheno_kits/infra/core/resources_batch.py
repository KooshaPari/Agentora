"""Batch resource operations and convenience helpers."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from ..adapters import resource_from_dict
from .resources_models import (
    ResourceDependency,
    ResourceReference,
    ResourceReuseStrategy,
    ResourceScope,
)
from .resources_manager import ResourceManager

if TYPE_CHECKING:
    from collections.abc import Iterable

logger = logging.getLogger(__name__)


class ResourceManagerBatch(ResourceManager):
    """Extension of ResourceManager with batch operation support.

    This class provides batch-oriented workflows for acquiring and releasing
    multiple resources in a single operation, which is more efficient than
    calling request_resource/release_resource individually.
    """

    # ------------------------------------------------------------------
    # Project-aware resource acquisition
    # ------------------------------------------------------------------
    async def request_resource(
        self,
        project_name: str,
        resource_name: str,
        config: dict[str, Any],
        *,
        reuse_strategy: ResourceReuseStrategy = ResourceReuseStrategy.SMART,
        dependencies: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        auto_start: bool = True,
        monitor_health: bool = True,
    ) -> tuple[bool, dict[str, Any] | None]:
        """Acquire a resource for a project with caching semantics.

        Args:
            project_name: Identifier for the requesting project/tenant.
            resource_name: Friendly name of the resource being requested.
            config: Adapter configuration payload for provisioning the resource if
                it does not already exist.
            reuse_strategy: Strategy controlling how aggressively the manager
                should reuse existing shared resources.
            dependencies: Optional list of resource names that this resource
                depends on.  Stored for validation/observability only.
            metadata: Additional metadata to associate with the allocation.
            auto_start: When ``True`` (default), the manager ensures the adapter
                is running before returning.
            monitor_health: When ``True`` (default), the manager establishes a
                health monitor if the adapter supports it.

        Returns:
            A tuple ``(success, payload)`` where ``payload`` describes the
            allocated resource on success and is ``None`` on failure.
        """
        if not project_name:
            raise ValueError("project_name must be provided")

        metadata = dict(metadata or {})
        dependencies = list(dependencies or [])

        resource_type = config.get("type", "unknown")
        signature = self._compute_signature(config)
        metadata.setdefault("resource_type", resource_type)
        metadata.setdefault("config_signature", signature)

        project_resources = self._project_index.setdefault(project_name, {})
        existing_key = project_resources.get(resource_name)
        if existing_key:
            reference = self._resource_cache.get(existing_key)
            if reference:
                reference.metadata.update(metadata)
                reference.touch()
                adapter = self.resources.get(reference.adapter_name)
                if not adapter:
                    logger.error(
                        "Cache inconsistency: adapter %s missing for %s",
                        reference.adapter_name,
                        resource_name,
                    )
                    project_resources.pop(resource_name, None)
                else:
                    if auto_start:
                        if not await self._ensure_adapter_running(
                            adapter,
                            monitor_health,
                        ):
                            logger.error(
                                "Failed to ensure running state for %s (project=%s)",
                                reference.adapter_name,
                                project_name,
                            )
                            return False, None
                    return True, self._build_resource_report(reference)
            else:
                project_resources.pop(resource_name, None)

        reference = self._select_reusable_entry(
            resource_name,
            config,
            reuse_strategy,
            metadata,
        )

        if reference:
            adapter = self.resources.get(reference.adapter_name)
            if not adapter:
                logger.warning(
                    "Adapter %s missing for cached resource %s; creating new instance",
                    reference.adapter_name,
                    resource_name,
                )
                reference = None
            else:
                reference.reference_count += 1
                reference.projects.add(project_name)
                reference.metadata.update(metadata)
                if dependencies:
                    self._merge_dependencies(reference.cache_key, dependencies)
                    stored = self._resource_dependencies.get(reference.cache_key)
                    if stored:
                        reference.dependencies = list(stored.dependencies)
                reference.touch()
                project_resources[resource_name] = reference.cache_key
                logger.info(
                    "Reused resource %s for project %s (refs=%s)",
                    resource_name,
                    project_name,
                    reference.reference_count,
                )

                if auto_start:
                    if not await self._ensure_adapter_running(adapter, monitor_health):
                        reference.reference_count = max(
                            reference.reference_count - 1,
                            0,
                        )
                        reference.projects.discard(project_name)
                        project_resources.pop(resource_name, None)
                        reference.touch()
                        logger.error(
                            "Failed to start reused resource %s for project %s",
                            resource_name,
                            project_name,
                        )
                        return False, None

                return True, self._build_resource_report(reference)

        scope = (
            ResourceScope.PROJECT
            if reuse_strategy == ResourceReuseStrategy.NEVER
            else ResourceScope.SHARED
        )
        adapter_name = self._generate_adapter_name(
            resource_name,
            project_name,
            scope,
            signature,
        )
        adapter = resource_from_dict(adapter_name, config)
        self.resources[adapter.name] = adapter

        cache_key = self._make_cache_key(resource_name, signature)
        while cache_key in self._resource_cache:
            cache_key = f"{cache_key}:{len(self._resource_cache)}"

        reference = ResourceReference(
            cache_key=cache_key,
            resource_name=resource_name,
            adapter_name=adapter.name,
            scope=scope,
            reference_count=1,
            metadata=dict(metadata),
            projects={project_name},
            resource_type=resource_type,
            config_signature=signature,
            dependencies=list(dict.fromkeys(dependencies)) if dependencies else [],
        )

        self._resource_cache[cache_key] = reference
        self._adapter_cache_index[adapter.name] = cache_key
        project_resources[resource_name] = cache_key
        if dependencies:
            self._resource_dependencies[cache_key] = ResourceDependency(
                resource_name=resource_name,
                dependencies=list(dict.fromkeys(dependencies)),
            )
        self._ensure_cleanup_task()

        logger.info(
            "Provisioned new resource %s for project %s (scope=%s)",
            resource_name,
            project_name,
            scope.value,
        )

        if auto_start:
            if not await self.start_resource(
                adapter.name,
                monitor_health=monitor_health,
            ):
                logger.error(
                    "Failed to start new resource %s for project %s",
                    resource_name,
                    project_name,
                )
                await self._remove_reference(cache_key, adapter.name)
                project_resources.pop(resource_name, None)
                return False, None

        return True, self._build_resource_report(reference)

    async def request_resources(
        self,
        project_name: str,
        resource_requests: dict[str, dict[str, Any]],
        *,
        default_strategy: ResourceReuseStrategy = ResourceReuseStrategy.SMART,
        monitor_health: bool = True,
    ) -> dict[str, tuple[bool, dict[str, Any] | None]]:
        """Acquire multiple resources for a project in a single call.

        The ``resource_requests`` mapping accepts either raw adapter configuration
        dictionaries or dictionaries with additional keys:

        ``config`` (required):
            Configuration payload used when provisioning the resource.
        ``reuse_strategy`` (optional):
            Overrides the ``default_strategy`` for a particular resource.
        ``dependencies`` (optional):
            Explicit dependency list stored in the cache metadata.
        ``metadata`` (optional):
            Additional metadata recorded on the resource reference.
        ``auto_start`` (optional):
            Whether the resource should be started automatically. Defaults to
            ``True``.

        Returns:
            Mapping of resource name to ``(success, payload)`` tuples.
        """
        results: dict[str, tuple[bool, dict[str, Any] | None]] = {}

        for name, request in resource_requests.items():
            if "config" in request:
                config = request["config"]
                strategy = request.get("reuse_strategy", default_strategy)
                dependencies = request.get("dependencies")
                metadata = request.get("metadata")
                auto_start = request.get("auto_start", True)
            else:
                config = request
                strategy = default_strategy
                dependencies = None
                metadata = None
                auto_start = True

            success, payload = await self.request_resource(
                project_name,
                name,
                config,
                reuse_strategy=strategy,
                dependencies=dependencies,
                metadata=metadata,
                auto_start=auto_start,
                monitor_health=monitor_health,
            )
            results[name] = (success, payload)

        return results

    async def release_resource(
        self,
        project_name: str,
        resource_name: str,
        *,
        force_cleanup: bool = False,
    ) -> bool:
        """Release a resource previously requested by a project.

        Args:
            project_name: Project that owns the resource reference.
            resource_name: Friendly resource identifier originally provided to
                ``request_resource``.
            force_cleanup: When ``True`` the resource is immediately torn down
                even if it is marked as shared.

        Returns:
            ``True`` if the reference was successfully released.
        """
        project_resources = self._project_index.get(project_name)
        if not project_resources:
            logger.warning(
                "Project %s has no registered resources to release",
                project_name,
            )
            return False

        cache_key = project_resources.pop(resource_name, None)
        if not cache_key:
            logger.warning(
                "Project %s does not hold resource %s",
                project_name,
                resource_name,
            )
            return False

        reference = self._resource_cache.get(cache_key)
        if not reference:
            logger.warning("Reference %s missing during release", cache_key)
            return False

        reference.reference_count = max(reference.reference_count - 1, 0)
        reference.projects.discard(project_name)
        reference.touch()

        logger.info(
            "Released resource %s from project %s (remaining=%s)",
            resource_name,
            project_name,
            reference.reference_count,
        )

        if reference.reference_count <= 0:
            if force_cleanup or reference.scope == ResourceScope.PROJECT:
                await self._cleanup_reference(reference)
            else:
                reference.reference_count = 0

        if not project_resources:
            self._project_index.pop(project_name, None)

        return True

    async def release_resources(
        self,
        project_name: str,
        resource_names: Iterable[str] | None = None,
        *,
        force_cleanup: bool = False,
    ) -> dict[str, bool]:
        """Release multiple resources for a project.

        Args:
            project_name: Project that owns the resources.
            resource_names: Iterable of resource names to release. When omitted
                all resources held by the project are released.
            force_cleanup: When ``True`` all resources are immediately torn down.

        Returns:
            Mapping of resource name to ``True``/``False`` depending on whether the
            release succeeded.
        """
        project_resources = self._project_index.get(project_name, {})
        if resource_names is None:
            names = list(project_resources.keys())
        else:
            names = list(resource_names)

        results: dict[str, bool] = {}
        for name in names:
            results[name] = await self.release_resource(
                project_name,
                name,
                force_cleanup=force_cleanup,
            )

        return results


async def manage_resources(
    resources_config: dict[str, dict[str, Any]],
    *,
    monitor_health: bool = True,
) -> None:
    """Convenience helper to start and monitor a group of resources.

    Args:
        resources_config: Mapping of resource name to adapter configuration.
        monitor_health: When ``True`` (default) health monitors are started for
            each resource.
    """
    manager = ResourceManager()

    for name, config in resources_config.items():
        manager.add_resource(name, config)

    await manager.start_all()

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await manager.stop_all()
