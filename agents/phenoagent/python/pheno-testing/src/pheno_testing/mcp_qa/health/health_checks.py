"""Flexible Health Check System for MCP QA.

Provides a registry-based pattern for health checks that can be:
- Registered by projects
- Run individually or in groups
- Cached for performance
- Reported with rich output

Usage:
    from pheno.testing.mcp_qa.health import HealthCheckRegistry, HealthCheck

    # Register a check
    @HealthCheckRegistry.register("database")
    async def check_postgres():
        # Your check logic
        return HealthCheck(
            name="PostgreSQL",
            status="healthy",
            details={"version": "15.0"}
        )

    # Run checks
    results = await HealthCheckRegistry.run_all()
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional

from pheno.testing.mcp_qa.logging import get_logger


class HealthStatus(Enum):
    """
    Health check status.
    """

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"
    SKIPPED = "skipped"


@dataclass
class HealthCheck:
    """
    Result of a health check.
    """

    name: str
    status: HealthStatus
    message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0
    timestamp: datetime = field(default_factory=datetime.now)
    category: Optional[str] = None

    @property
    def is_healthy(self) -> bool:
        """
        Check if status is healthy.
        """
        return self.status == HealthStatus.HEALTHY

    @property
    def emoji(self) -> str:
        """
        Get emoji for status.
        """
        return {
            HealthStatus.HEALTHY: "✅",
            HealthStatus.UNHEALTHY: "❌",
            HealthStatus.DEGRADED: "⚠️",
            HealthStatus.UNKNOWN: "❓",
            HealthStatus.SKIPPED: "⏭️",
        }.get(self.status, "❓")

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary.
        """
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
            "category": self.category,
        }


@dataclass
class HealthCheckDefinition:
    """
    Definition of a health check.
    """

    name: str
    check_fn: Callable[[], Awaitable[HealthCheck]]
    category: str = "general"
    enabled: bool = True
    cache_ttl_seconds: int = 60
    timeout_seconds: int = 10
    dependencies: List[str] = field(default_factory=list)


class HealthCheckRegistry:
    """Registry for health checks.

    Allows projects to register custom health checks and run them individually or in
    groups.
    """

    _checks: Dict[str, HealthCheckDefinition] = {}
    _cache: Dict[str, tuple[HealthCheck, float]] = {}  # (result, timestamp)
    _logger = get_logger(__name__)

    @classmethod
    def register(
        cls,
        category: str = "general",
        name: Optional[str] = None,
        enabled: bool = True,
        cache_ttl: int = 60,
        timeout: int = 10,
        dependencies: Optional[List[str]] = None,
    ):
        """Decorator to register a health check.

        Args:
            category: Category for grouping checks
            name: Custom name (defaults to function name)
            enabled: Whether check is enabled
            cache_ttl: Cache time-to-live in seconds
            timeout: Timeout in seconds
            dependencies: List of check names this depends on

        Example:
            @HealthCheckRegistry.register("database")
            async def check_postgres():
                return HealthCheck(
                    name="PostgreSQL",
                    status=HealthStatus.HEALTHY
                )
        """

        def decorator(func: Callable[[], Awaitable[HealthCheck]]):
            check_name = name or func.__name__
            cls._checks[check_name] = HealthCheckDefinition(
                name=check_name,
                check_fn=func,
                category=category,
                enabled=enabled,
                cache_ttl_seconds=cache_ttl,
                timeout_seconds=timeout,
                dependencies=dependencies or [],
            )
            cls._logger.debug(f"Registered health check: {check_name}", category=category)
            return func

        return decorator

    @classmethod
    def register_check(
        cls,
        name: str,
        check_fn: Callable[[], Awaitable[HealthCheck]],
        category: str = "general",
        **kwargs,
    ):
        """Register a health check programmatically.

        Args:
            name: Check name
            check_fn: Async function that returns HealthCheck
            category: Category for grouping
            **kwargs: Additional options (enabled, cache_ttl, timeout, dependencies)
        """
        cls._checks[name] = HealthCheckDefinition(
            name=name,
            check_fn=check_fn,
            category=category,
            enabled=kwargs.get("enabled", True),
            cache_ttl_seconds=kwargs.get("cache_ttl", 60),
            timeout_seconds=kwargs.get("timeout", 10),
            dependencies=kwargs.get("dependencies", []),
        )
        cls._logger.debug(f"Registered health check: {name}", category=category)

    @classmethod
    async def run_check(cls, name: str, use_cache: bool = True, force: bool = False) -> HealthCheck:
        """Run a single health check.

        Args:
            name: Check name
            use_cache: Use cached result if available
            force: Force run even if disabled

        Returns:
            HealthCheck result
        """
        if name not in cls._checks:
            return HealthCheck(
                name=name, status=HealthStatus.UNKNOWN, message=f"Check '{name}' not registered"
            )

        definition = cls._checks[name]

        # Check if disabled
        if not definition.enabled and not force:
            return HealthCheck(
                name=definition.name,
                status=HealthStatus.SKIPPED,
                message="Check disabled",
                category=definition.category,
            )

        # Check cache
        if use_cache and name in cls._cache:
            cached_result, cache_time = cls._cache[name]
            age = time.time() - cache_time
            if age < definition.cache_ttl_seconds:
                cls._logger.debug(f"Using cached result for {name}", age_seconds=age)
                return cached_result

        # Run dependencies first
        for dep_name in definition.dependencies:
            dep_result = await cls.run_check(dep_name, use_cache=use_cache)
            if not dep_result.is_healthy:
                return HealthCheck(
                    name=definition.name,
                    status=HealthStatus.SKIPPED,
                    message=f"Dependency '{dep_name}' is unhealthy",
                    category=definition.category,
                )

        # Run the check
        start_time = time.time()
        try:
            result = await asyncio.wait_for(
                definition.check_fn(), timeout=definition.timeout_seconds
            )
            result.duration_ms = (time.time() - start_time) * 1000
            result.category = result.category or definition.category

            # Cache result
            cls._cache[name] = (result, time.time())

            return result

        except asyncio.TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            cls._logger.warning(f"Health check timeout: {name}", timeout=definition.timeout_seconds)
            return HealthCheck(
                name=definition.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Timeout after {definition.timeout_seconds}s",
                duration_ms=duration_ms,
                category=definition.category,
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            cls._logger.error(f"Health check error: {name}", error=str(e))
            return HealthCheck(
                name=definition.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Error: {str(e)}",
                duration_ms=duration_ms,
                category=definition.category,
            )

    @classmethod
    async def run_category(
        cls, category: str, use_cache: bool = True, parallel: bool = True
    ) -> List[HealthCheck]:
        """Run all checks in a category.

        Args:
            category: Category name
            use_cache: Use cached results
            parallel: Run checks in parallel

        Returns:
            List of HealthCheck results
        """
        checks = [
            name
            for name, definition in cls._checks.items()
            if definition.category == category and definition.enabled
        ]

        if not checks:
            cls._logger.warning(f"No checks found in category: {category}")
            return []

        if parallel:
            tasks = [cls.run_check(name, use_cache=use_cache) for name in checks]
            return await asyncio.gather(*tasks)
        else:
            results = []
            for name in checks:
                result = await cls.run_check(name, use_cache=use_cache)
                results.append(result)
            return results

    @classmethod
    async def run_all(
        cls, use_cache: bool = True, parallel: bool = True, categories: Optional[List[str]] = None
    ) -> Dict[str, List[HealthCheck]]:
        """Run all health checks.

        Args:
            use_cache: Use cached results
            parallel: Run checks in parallel
            categories: Only run specific categories

        Returns:
            Dictionary mapping category to list of results
        """
        # Get all categories
        all_categories = set(
            definition.category for definition in cls._checks.values() if definition.enabled
        )

        if categories:
            all_categories = all_categories.intersection(categories)

        if not all_categories:
            cls._logger.warning("No enabled health checks found")
            return {}

        # Run checks by category
        results = {}
        for category in sorted(all_categories):
            category_results = await cls.run_category(
                category, use_cache=use_cache, parallel=parallel
            )
            results[category] = category_results

        return results

    @classmethod
    def clear_cache(cls, name: Optional[str] = None):
        """Clear cached results.

        Args:
            name: Specific check to clear, or None for all
        """
        if name:
            cls._cache.pop(name, None)
            cls._logger.debug(f"Cleared cache for: {name}")
        else:
            cls._cache.clear()
            cls._logger.debug("Cleared all health check cache")

    @classmethod
    def list_checks(cls, category: Optional[str] = None, enabled_only: bool = False) -> List[str]:
        """List registered health checks.

        Args:
            category: Filter by category
            enabled_only: Only show enabled checks

        Returns:
            List of check names
        """
        checks = []
        for name, definition in cls._checks.items():
            if category and definition.category != category:
                continue
            if enabled_only and not definition.enabled:
                continue
            checks.append(name)
        return sorted(checks)

    @classmethod
    def get_categories(cls) -> List[str]:
        """
        Get all registered categories.
        """
        return sorted(set(definition.category for definition in cls._checks.values()))

    @classmethod
    def enable_check(cls, name: str):
        """
        Enable a health check.
        """
        if name in cls._checks:
            cls._checks[name].enabled = True
            cls._logger.info(f"Enabled health check: {name}")

    @classmethod
    def disable_check(cls, name: str):
        """
        Disable a health check.
        """
        if name in cls._checks:
            cls._checks[name].enabled = False
            cls._logger.info(f"Disabled health check: {name}")

    @classmethod
    def unregister(cls, name: str):
        """
        Unregister a health check.
        """
        if name in cls._checks:
            del cls._checks[name]
            cls._cache.pop(name, None)
            cls._logger.info(f"Unregistered health check: {name}")

    @classmethod
    def reset(cls):
        """
        Reset registry (clear all checks and cache).
        """
        cls._checks.clear()
        cls._cache.clear()
        cls._logger.info("Reset health check registry")


# Convenience functions


async def run_health_checks(
    categories: Optional[List[str]] = None, use_cache: bool = True
) -> Dict[str, List[HealthCheck]]:
    """Convenience function to run health checks.

    Args:
        categories: Specific categories to run
        use_cache: Use cached results

    Returns:
        Dictionary of results by category
    """
    return await HealthCheckRegistry.run_all(use_cache=use_cache, categories=categories)


def register_health_check(
    name: str, check_fn: Callable[[], Awaitable[HealthCheck]], category: str = "general", **kwargs
):
    """Convenience function to register a health check.

    Args:
        name: Check name
        check_fn: Check function
        category: Category
        **kwargs: Additional options
    """
    HealthCheckRegistry.register_check(name=name, check_fn=check_fn, category=category, **kwargs)
