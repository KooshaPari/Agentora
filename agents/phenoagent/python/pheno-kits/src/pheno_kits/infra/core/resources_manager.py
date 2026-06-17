"""Core resource manager with caching, health monitoring, and lifecycle orchestration."""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import logging
import time
from typing import TYPE_CHECKING, Any, Self

from ..adapters import ResourceAdapter, resource_from_dict
from .resources_models import (
    ResourceDependency,
    ResourceReference,
    ResourceReuseStrategy,
    ResourceScope,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

logger = logging.getLogger(__name__)


class ResourceManager:
    """High-level resource coordinator with caching and batch operations.

    The manager retains the thin adapter-based orchestration of the original
    ``kits.resource_manager`` while incorporating the advanced behaviours that
    lived in ``infra.resource_coordinator`` and ``infra.resource_reference_cache``.
    Most teams interact with the following surface area:

    * ``add_resource`` / ``add_resource_adapter`` for pre-provisioned resources.
    * ``request_resource`` for project-aware resource acquisition with caching.
    * ``request_resources`` and ``release_resources`` for batch workflows.
    * ``get_project_resources`` and ``get_cache_snapshot`` for observability.

    Internally the manager keeps a reference-counted cache that can reuse
    running resources when compatibility permits.  Idle shared resources are
    cleaned up automatically after a configurable grace period.  Health
    monitoring continues to leverage adapter-provided checks so the behaviour
    matches the previous implementation.
    """

    def __init__(
        self,
        cleanup_interval: float = 60.0,
        idle_ttl: float = 300.0,
    ) -> None:
        """Create a new resource manager instance.

        Args:
            cleanup_interval: Frequency (in seconds) for scanning idle resources
                that may be eligible for cleanup.
            idle_ttl: How long (in seconds) a shared resource is kept alive after
                its final reference is released before the manager tears it down.
        """
        self.resources: dict[str, ResourceAdapter] = {}
        self._resource_cache: dict[str, ResourceReference] = {}
        self._project_index: dict[str, dict[str, str]] = {}
        self._adapter_cache_index: dict[str, str] = {}
        self._resource_dependencies: dict[str, ResourceDependency] = {}
        self._compatibility_rules: dict[str, dict[str, Any]] = {}
        self._health_monitor_tasks: dict[str, asyncio.Task] = {}
        self._cleanup_task: asyncio.Task | None = None
        self._cleanup_interval = cleanup_interval
        self._idle_ttl = idle_ttl
        self._shutdown = False

        logger.info(
            "ResourceManager initialized (cleanup_interval=%s idle_ttl=%s)",
            cleanup_interval,
            idle_ttl,
        )

    # ------------------------------------------------------------------
    # Public registration helpers
    # ------------------------------------------------------------------
    def add_resource(
        self,
        name: str,
        config: dict[str, Any],
        *,
        scope: ResourceScope = ResourceScope.SHARED,
        metadata: dict[str, Any] | None = None,
    ) -> ResourceAdapter:
        """Register a resource from configuration without binding it to a project.

        This mirrors the legacy ``add_resource`` behaviour so that existing call
        sites continue to function.  The resource can later be referenced by
        projects through ``request_resource`` which will reuse the pre-provisioned
        adapter.

        Args:
            name: Friendly identifier for the resource.
            config: Adapter configuration payload. Must include a ``type`` field.
            scope: Whether the resource should be treated as shared or
                project-specific when claimed by projects.
            metadata: Optional metadata that will be attached to the cached entry.

        Returns:
            The instantiated :class:`ResourceAdapter`.
        """
        adapter = resource_from_dict(name, config)
        self.resources[adapter.name] = adapter

        signature = self._compute_signature(config)
        entry_metadata = dict(metadata or {})
        entry_metadata.setdefault("resource_type", config.get("type"))
        entry_metadata.setdefault("config_signature", signature)

        cache_key = self._make_cache_key(name, signature)
        reference = ResourceReference(
            cache_key=cache_key,
            resource_name=name,
            adapter_name=adapter.name,
            scope=scope,
            reference_count=0,
            metadata=entry_metadata,
            resource_type=entry_metadata.get("resource_type"),
            config_signature=signature,
        )

        self._resource_cache[cache_key] = reference
        self._adapter_cache_index[adapter.name] = cache_key
        self._ensure_cleanup_task()

        logger.info("Registered resource %s (scope=%s)", name, scope.value)
        return adapter

    def add_resource_adapter(
        self,
        adapter: ResourceAdapter,
        *,
        scope: ResourceScope = ResourceScope.SHARED,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Attach an adapter that was constructed elsewhere.

        Args:
            adapter: Pre-configured adapter instance.
            scope: Whether the resource should be shared across projects.
            metadata: Optional metadata describing the resource.
        """
        self.resources[adapter.name] = adapter

        signature = self._compute_signature(adapter.config)
        entry_metadata = dict(metadata or {})
        entry_metadata.setdefault("resource_type", adapter.config.get("type"))
        entry_metadata.setdefault("config_signature", signature)

        cache_key = self._make_cache_key(adapter.name, signature)
        reference = ResourceReference(
            cache_key=cache_key,
            resource_name=adapter.name,
            adapter_name=adapter.name,
            scope=scope,
            reference_count=0,
            metadata=entry_metadata,
            resource_type=entry_metadata.get("resource_type"),
            config_signature=signature,
        )

        self._resource_cache[cache_key] = reference
        self._adapter_cache_index[adapter.name] = cache_key
        self._ensure_cleanup_task()

        logger.info("Attached external resource adapter %s", adapter.name)

    # ------------------------------------------------------------------
    # Status and observability helpers
    # ------------------------------------------------------------------
    async def get_project_resources(self, project_name: str) -> list[dict[str, Any]]:
        """Return detailed status for all resources assigned to a project."""
        project_resources = self._project_index.get(project_name, {})
        results: list[dict[str, Any]] = []

        for cache_key in project_resources.values():
            reference = self._resource_cache.get(cache_key)
            if reference:
                status = self.get_status(reference.adapter_name)
                if status:
                    results.append(status)

        return results

    def get_cache_snapshot(self) -> dict[str, Any]:
        """Expose a read-only snapshot of the resource cache for diagnostics."""
        return {
            "resources": {
                name: self._describe_reference(ref)
                for name, ref in self._resource_cache.items()
            },
            "projects": {
                project: dict(mapping)
                for project, mapping in self._project_index.items()
            },
        }

    def set_compatibility_rule(self, resource_type: str, rule: dict[str, Any]) -> None:
        """Define compatibility requirements for conditional/smart reuse."""
        self._compatibility_rules[resource_type] = rule
        logger.info("Set compatibility rule for %s", resource_type)

    async def validate_project_dependencies(
        self,
        project_name: str,
    ) -> tuple[bool, list[str]]:
        """Validate that all declared dependencies for a project are satisfied."""
        project_resources = self._project_index.get(project_name, {})
        held_resources = set(project_resources.values())
        missing: list[str] = []

        for cache_key in held_resources:
            dependency = self._resource_dependencies.get(cache_key)
            if not dependency:
                continue
            required = set(dependency.dependencies)
            if not required:
                continue
            available = {
                self._resource_cache[key].resource_name
                for key in held_resources
                if key in self._resource_cache
            }
            for dep in required:
                if dep not in available:
                    missing.append(dep)

        return len(missing) == 0, missing

    # ------------------------------------------------------------------
    # Core lifecycle methods (adapter parity with legacy manager)
    # ------------------------------------------------------------------
    async def start_resource(self, name: str, monitor_health: bool = True) -> bool:
        """Start a resource adapter and optionally enable health monitoring."""
        adapter = self.resources.get(name)
        if not adapter:
            logger.error("Resource %s not found", name)
            return False

        try:
            success = await adapter.start()
        except Exception as exc:
            logger.exception("Failed to start resource %s: %s", name, exc)
            return False

        if not success:
            return False

        if monitor_health:
            task = asyncio.create_task(self._monitor_health(name))
            self._health_monitor_tasks[name] = task

        cache_key = self._adapter_cache_index.get(name)
        if cache_key:
            reference = self._resource_cache.get(cache_key)
            if reference:
                reference.is_healthy = True
                reference.touch()

        return True

    async def stop_resource(self, name: str) -> bool:
        """Stop a running resource adapter and cancel health monitoring."""
        adapter = self.resources.get(name)
        if not adapter:
            return False

        task = self._health_monitor_tasks.pop(name, None)
        if task:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

        try:
            success = await adapter.stop()
        except Exception as exc:
            logger.exception("Failed to stop resource %s: %s", name, exc)
            return False

        cache_key = self._adapter_cache_index.get(name)
        if cache_key:
            reference = self._resource_cache.get(cache_key)
            if reference:
                reference.is_healthy = False
                reference.touch()

        return success

    async def start_all(self) -> dict[str, bool]:
        """Start every registered resource."""
        results: dict[str, bool] = {}
        for name in list(self.resources):
            results[name] = await self.start_resource(name)
        return results

    async def stop_all(self) -> None:
        """Stop all managed resources and cancel background tasks."""
        self._shutdown = True

        for name in list(self.resources.keys()):
            await self.stop_resource(name)

        if self._cleanup_task:
            self._cleanup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._cleanup_task
            self._cleanup_task = None

    async def _monitor_health(self, name: str) -> None:
        """Continuously monitor adapter health until shutdown or cancellation."""
        adapter = self.resources.get(name)
        if not adapter:
            return

        try:
            while not self._shutdown:
                healthy = await adapter.check_health()
                cache_key = self._adapter_cache_index.get(name)
                if cache_key:
                    reference = self._resource_cache.get(cache_key)
                    if reference:
                        reference.is_healthy = healthy
                        reference.touch()

                if not healthy:
                    logger.warning("Resource %s reported unhealthy; restarting", name)
                    await adapter.restart()

                await asyncio.sleep(5.0)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.exception("Health monitor error for %s: %s", name, exc)

    def get_status(self, name: str) -> dict[str, Any] | None:
        """Return the most recent status information for a resource."""
        adapter = self.resources.get(name)
        if not adapter:
            return None

        state = adapter.get_state()
        status = {
            "name": state.name,
            "running": state.running,
            "healthy": state.healthy,
            "pid": state.pid,
            "container_id": state.container_id,
            "port": state.port,
            "error": state.error,
            "metadata": state.metadata,
        }

        cache_key = self._adapter_cache_index.get(name)
        if cache_key:
            reference = self._resource_cache.get(cache_key)
            if reference:
                status.update(
                    {
                        "scope": reference.scope.value,
                        "projects": sorted(reference.projects),
                        "reference_count": reference.reference_count,
                        "resource_type": reference.resource_type,
                        "config_signature": reference.config_signature,
                        "cached_metadata": dict(reference.metadata),
                        "is_healthy": reference.is_healthy,
                    },
                )

        return status

    def get_all_status(self) -> dict[str, dict[str, Any]]:
        """Return status for every managed resource."""
        return {
            name: status
            for name in self.resources
            if (status := self.get_status(name)) is not None
        }

    # ------------------------------------------------------------------
    # Shutdown + context manager helpers
    # ------------------------------------------------------------------
    async def shutdown(self) -> None:
        """Stop all resources and tear down background tasks."""
        await self.stop_all()
        self.resources.clear()
        self._resource_cache.clear()
        self._project_index.clear()
        self._adapter_cache_index.clear()
        self._resource_dependencies.clear()

    async def __aenter__(self) -> Self:
        await self.start_all()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.shutdown()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _ensure_cleanup_task(self) -> None:
        """Ensure the idle cleanup background task is running."""
        if self._cleanup_task and not self._cleanup_task.done():
            return

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return

        self._cleanup_task = loop.create_task(self._cleanup_idle_resources())

    async def _cleanup_idle_resources(self) -> None:
        """Background task that tears down unused shared resources."""
        try:
            while not self._shutdown:
                now = time.time()
                for _cache_key, reference in list(self._resource_cache.items()):
                    if reference.reference_count > 0:
                        continue
                    if reference.scope != ResourceScope.SHARED:
                        continue
                    if now - reference.last_accessed < self._idle_ttl:
                        continue
                    await self._cleanup_reference(reference)

                await asyncio.sleep(self._cleanup_interval)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.exception("Error during idle cleanup: %s", exc)

    async def _cleanup_reference(self, reference: ResourceReference) -> None:
        """Stop and remove a resource reference from the cache."""
        await self.stop_resource(reference.adapter_name)
        cache_key = reference.cache_key
        await self._remove_reference(cache_key, reference.adapter_name)

    async def _remove_reference(self, cache_key: str, adapter_name: str) -> None:
        """Remove cache and adapter bookkeeping for a specific resource."""
        self.resources.pop(adapter_name, None)
        self._adapter_cache_index.pop(adapter_name, None)
        self._resource_cache.pop(cache_key, None)
        self._resource_dependencies.pop(cache_key, None)

    def _select_reusable_entry(
        self,
        resource_name: str,
        config: dict[str, Any],
        strategy: ResourceReuseStrategy,
        metadata: dict[str, Any],
    ) -> ResourceReference | None:
        """Return a reusable reference if strategy and compatibility allow."""
        if strategy == ResourceReuseStrategy.NEVER:
            return None

        signature = metadata.get("config_signature")
        candidates = [
            ref
            for ref in self._resource_cache.values()
            if ref.resource_name == resource_name and ref.scope == ResourceScope.SHARED
        ]

        if not candidates:
            return None

        if strategy == ResourceReuseStrategy.ALWAYS:
            for ref in candidates:
                if ref.config_signature == signature:
                    return ref
            return candidates[0]

        for ref in candidates:
            if strategy == ResourceReuseStrategy.CONDITIONAL:
                if self._check_compatibility(ref, config, metadata):
                    return ref
            elif strategy == ResourceReuseStrategy.SMART:
                if self._smart_reuse_check(ref, config, metadata):
                    return ref

        return None

    def _check_compatibility(
        self,
        reference: ResourceReference,
        config: dict[str, Any],
        metadata: dict[str, Any],
    ) -> bool:
        """Determine whether an existing resource matches the requested config."""
        resource_type = metadata.get("resource_type")
        if reference.resource_type and resource_type:
            if reference.resource_type != resource_type:
                return False

        signature = metadata.get("config_signature")
        if reference.config_signature and signature:
            if reference.config_signature != signature:
                return False

        rule = self._compatibility_rules.get(resource_type or "", {})
        if not rule:
            return True

        if "version" in rule:
            required_version = config.get("version")
            if required_version and not self._check_version(
                rule["version"],
                required_version,
            ):
                return False

        required_config = config.get("config", {})
        required_fields = rule.get("required_config", {})
        for key, expected in required_fields.items():
            if required_config.get(key) != expected:
                return False

        return True

    def _smart_reuse_check(
        self,
        reference: ResourceReference,
        config: dict[str, Any],
        metadata: dict[str, Any],
    ) -> bool:
        """Heuristic that balances compatibility, health, and utilisation."""
        if not self._check_compatibility(reference, config, metadata):
            reference.compatibility_score = max(
                reference.compatibility_score - 0.1,
                0.0,
            )
            return False

        if not reference.is_healthy:
            return False

        if reference.reference_count > 5:
            reference.compatibility_score = max(
                reference.compatibility_score - 0.05,
                0.0,
            )
            return False

        reference.compatibility_score = min(reference.compatibility_score + 0.05, 1.0)
        return True

    @staticmethod
    def _check_version(rule_version: str, required_version: str) -> bool:
        """Basic semantic version compatibility check (major version equality)."""
        try:
            rule_major = int(rule_version.split(".", maxsplit=1)[0])
            required_major = int(required_version.split(".", maxsplit=1)[0])
            return rule_major == required_major
        except (ValueError, IndexError):
            return False

    def _merge_dependencies(self, cache_key: str, dependencies: list[str]) -> None:
        """Merge dependency information for an existing cached resource."""
        if not dependencies:
            return

        reference = self._resource_cache.get(cache_key)
        if not reference:
            return

        dependency = self._resource_dependencies.get(cache_key)
        if not dependency:
            merged = list(dict.fromkeys(dependencies))
            reference.dependencies = merged
            self._resource_dependencies[cache_key] = ResourceDependency(
                resource_name=reference.resource_name,
                dependencies=merged,
            )
        else:
            merged = list(dict.fromkeys([*dependency.dependencies, *dependencies]))
            dependency.dependencies = merged
            reference.dependencies = merged

    async def _ensure_adapter_running(
        self,
        adapter: ResourceAdapter,
        monitor_health: bool,
    ) -> bool:
        """Ensure the adapter is running, starting it if necessary."""
        try:
            running = await adapter.is_running()
        except Exception as exc:
            logger.exception("Failed to query adapter %s state: %s", adapter.name, exc)
            running = False

        if running:
            return True

        return await self.start_resource(adapter.name, monitor_health=monitor_health)

    def _build_resource_report(self, reference: ResourceReference) -> dict[str, Any]:
        """Construct a serialisable description of a cached resource."""
        return {
            "resource_name": reference.resource_name,
            "adapter_name": reference.adapter_name,
            "scope": reference.scope.value,
            "projects": sorted(reference.projects),
            "reference_count": reference.reference_count,
            "metadata": dict(reference.metadata),
            "resource_type": reference.resource_type,
            "config_signature": reference.config_signature,
            "dependencies": list(reference.dependencies),
            "is_healthy": reference.is_healthy,
        }

    def _describe_reference(self, reference: ResourceReference) -> dict[str, Any]:
        """Helper used by ``get_cache_snapshot`` to describe a cache entry."""
        return {
            "adapter_name": reference.adapter_name,
            "scope": reference.scope.value,
            "reference_count": reference.reference_count,
            "projects": sorted(reference.projects),
            "metadata": dict(reference.metadata),
            "resource_type": reference.resource_type,
            "config_signature": reference.config_signature,
            "compatibility_score": reference.compatibility_score,
            "is_healthy": reference.is_healthy,
            "created_at": reference.created_at,
            "last_accessed": reference.last_accessed,
        }

    @staticmethod
    def _compute_signature(config: dict[str, Any]) -> str:
        """Compute a deterministic fingerprint for a configuration mapping."""
        try:
            payload = json.dumps(config, sort_keys=True, separators=(",", ":"))
        except TypeError:
            payload = repr(config)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _make_cache_key(resource_name: str, signature: str | None) -> str:
        """Generate a cache key using the resource name and config signature."""
        if signature:
            return f"{resource_name}:{signature}"
        return resource_name

    def _generate_adapter_name(
        self,
        resource_name: str,
        project_name: str,
        scope: ResourceScope,
        signature: str | None,
    ) -> str:
        """Generate a stable adapter name that avoids collisions."""
        base = resource_name.replace(" ", "-")
        suffix = (signature or "local")[:8]

        if scope == ResourceScope.SHARED:
            candidate = base
            if candidate not in self.resources:
                return candidate
        else:
            project_slug = project_name.replace(" ", "-")
            candidate = f"{project_slug}-{base}-{suffix}"

        index = 1
        unique_candidate = f"{candidate}-{suffix}"
        while unique_candidate in self.resources:
            index += 1
            unique_candidate = f"{candidate}-{suffix}-{index}"

        return unique_candidate
