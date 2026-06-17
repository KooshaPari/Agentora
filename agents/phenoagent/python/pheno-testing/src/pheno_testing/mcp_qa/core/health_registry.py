"""Registry-Based Health Check System.

Flexible health check system that allows projects to register their own checks.

Usage:
    from pheno.testing.mcp_qa.core.health_registry import HealthCheckRegistry

    # Create registry
    registry = HealthCheckRegistry()

    # Register custom checks
    registry.register("postgres", check_postgres_func)
    registry.register("redis", check_redis_func)

    # Or use built-in helpers
    registry.register_postgres(dsn="postgresql://...")

    # Run all checks
    results = await registry.run_all()

    # Print results
    registry.print_results(results)
"""

import asyncio
import logging
import os
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class HealthCheckRegistry:
    """Registry-based health checker for backend services.

    Projects register their own health checks instead of being forced to use hardcoded
    checks for services they don't use.
    """

    def __init__(self):
        self._checks: Dict[str, Callable] = {}
        self._check_metadata: Dict[str, Dict[str, Any]] = {}

    def register(
        self,
        name: str,
        check_func: Callable,
        *,
        timeout: float = 3.0,
        critical: bool = True,
        description: Optional[str] = None,
    ) -> None:
        """Register a health check function.

        Args:
            name: Unique name for the check
            check_func: Callable that returns True if healthy, can be sync or async
            timeout: Timeout in seconds (default: 3.0)
            critical: Whether failure should block tests (default: True)
            description: Optional description of what's being checked

        Example:
            async def check_db():
                conn = await asyncpg.connect(...)
                return True

            registry.register("postgres", check_db, timeout=5.0)
        """
        self._checks[name] = check_func
        self._check_metadata[name] = {
            "timeout": timeout,
            "critical": critical,
            "description": description or name,
        }
        logger.debug(f"Registered health check: {name}")

    def unregister(self, name: str) -> None:
        """
        Remove a health check from the registry.
        """
        self._checks.pop(name, None)
        self._check_metadata.pop(name, None)

    def clear(self) -> None:
        """
        Clear all registered health checks.
        """
        self._checks.clear()
        self._check_metadata.clear()

    def list_checks(self) -> List[str]:
        """
        Return list of registered check names.
        """
        return list(self._checks.keys())

    async def run_check(self, name: str) -> Dict[str, Any]:
        """Run a single health check.

        Returns:
            {
                "name": str,
                "available": bool,
                "error": Optional[str],
                "duration_ms": float,
                "critical": bool
            }
        """
        import time

        if name not in self._checks:
            return {
                "name": name,
                "available": False,
                "error": "Check not registered",
                "duration_ms": 0,
                "critical": False,
            }

        check_func = self._checks[name]
        metadata = self._check_metadata[name]
        timeout = metadata["timeout"]

        start = time.time()
        try:
            if asyncio.iscoroutinefunction(check_func):
                result = await asyncio.wait_for(check_func(), timeout=timeout)
            else:
                result = check_func()

            duration_ms = (time.time() - start) * 1000

            return {
                "name": name,
                "available": bool(result),
                "error": None if result else "Check returned False",
                "duration_ms": duration_ms,
                "critical": metadata["critical"],
                "description": metadata["description"],
            }

        except asyncio.TimeoutError:
            duration_ms = (time.time() - start) * 1000
            return {
                "name": name,
                "available": False,
                "error": f"Timeout ({timeout}s)",
                "duration_ms": duration_ms,
                "critical": metadata["critical"],
                "description": metadata["description"],
            }

        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            return {
                "name": name,
                "available": False,
                "error": str(e),
                "duration_ms": duration_ms,
                "critical": metadata["critical"],
                "description": metadata["description"],
            }

    async def run_all(self, fail_fast: bool = False) -> Dict[str, Dict[str, Any]]:
        """Run all registered health checks.

        Args:
            fail_fast: Stop on first critical failure (default: False)

        Returns:
            Dict mapping check name to result dict
        """
        results = {}

        for name in self._checks:
            result = await self.run_check(name)
            results[name] = result

            # Stop on first critical failure if fail_fast is enabled
            if fail_fast and not result["available"] and result["critical"]:
                logger.warning(f"Critical health check failed: {name}")
                break

        return results

    def print_results(self, results: Dict[str, Dict[str, Any]]) -> None:
        """
        Print health check results in a nice format.
        """
        print("\n🏥 Backend Health Check:")
        print("=" * 70)

        for name, result in results.items():
            status = "✅" if result["available"] else "❌"
            description = result.get("description", name)
            duration = f"{result['duration_ms']:.0f}ms"
            critical = "🔴" if result.get("critical") else "⚪"

            print(f"{status} {critical} {description:25s} {duration:>8s}", end="")

            if not result["available"]:
                error = result.get("error", "Unknown error")
                print(f" - {error}")
            else:
                print()

        print("=" * 70)

        # Summary
        available = sum(1 for r in results.values() if r["available"])
        total = len(results)
        critical_failures = sum(
            1 for r in results.values() if not r["available"] and r.get("critical")
        )

        print(f"Available: {available}/{total} services")
        if critical_failures > 0:
            print(f"⚠️  {critical_failures} critical failures")
        print()

    # Built-in helper methods for common checks

    def register_postgres(
        self, dsn: Optional[str] = None, *, timeout: float = 3.0, critical: bool = True
    ) -> None:
        """Register a Postgres health check.

        Args:
            dsn: Database connection string (uses DATABASE_URL env var if None)
            timeout: Timeout in seconds
            critical: Whether failure should block tests
        """

        def check_postgres() -> bool:
            try:
                import psycopg

                conn_dsn = dsn or os.getenv("DATABASE_URL", "postgresql://localhost:5432/postgres")
                conn = psycopg.connect(conn_dsn, connect_timeout=int(timeout))
                cur = conn.cursor()
                cur.execute("SELECT 1")
                cur.close()
                conn.close()
                return True
            except ImportError:
                logger.warning("psycopg not installed - skipping Postgres check")
                return False
            except Exception as e:
                logger.debug(f"Postgres check failed: {e}")
                return False

        self.register(
            "postgres",
            check_postgres,
            timeout=timeout,
            critical=critical,
            description="PostgreSQL Database",
        )

    def register_pgvector(
        self, dsn: Optional[str] = None, *, timeout: float = 3.0, critical: bool = False
    ) -> None:
        """Register a pgvector extension health check.

        Args:
            dsn: Database connection string (uses DATABASE_URL env var if None)
            timeout: Timeout in seconds
            critical: Whether failure should block tests (default: False)
        """

        def check_pgvector() -> bool:
            try:
                import psycopg

                conn_dsn = dsn or os.getenv("DATABASE_URL", "postgresql://localhost:5432/postgres")
                conn = psycopg.connect(conn_dsn, connect_timeout=int(timeout))
                cur = conn.cursor()
                cur.execute("SELECT 1 FROM pg_extension WHERE extname='vector'")
                has_vector = cur.fetchone() is not None
                cur.close()
                conn.close()
                return has_vector
            except ImportError:
                return False
            except Exception:
                return False

        self.register(
            "pgvector",
            check_pgvector,
            timeout=timeout,
            critical=critical,
            description="pgvector Extension",
        )

    def register_redis(
        self, url: Optional[str] = None, *, timeout: float = 3.0, critical: bool = True
    ) -> None:
        """Register a Redis health check.

        Args:
            url: Redis connection URL (uses REDIS_URL env var if None)
            timeout: Timeout in seconds
            critical: Whether failure should block tests
        """

        async def check_redis() -> bool:
            try:
                import redis.asyncio as redis

                redis_url = url or os.getenv("REDIS_URL", "redis://localhost:6379")
                client = redis.from_url(redis_url, socket_connect_timeout=timeout)
                await client.ping()
                await client.close()
                return True
            except ImportError:
                return False
            except Exception:
                return False

        self.register(
            "redis", check_redis, timeout=timeout, critical=critical, description="Redis Cache"
        )

    def register_http_endpoint(
        self,
        name: str,
        url: str,
        *,
        timeout: float = 5.0,
        critical: bool = True,
        expected_status: int = 200,
    ) -> None:
        """Register an HTTP endpoint health check.

        Args:
            name: Name for this check
            url: URL to check
            timeout: Timeout in seconds
            critical: Whether failure should block tests
            expected_status: Expected HTTP status code (default: 200)
        """

        async def check_http() -> bool:
            try:
                import httpx

                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.get(url)
                    return response.status_code == expected_status
            except ImportError:
                return False
            except Exception:
                return False

        self.register(
            name,
            check_http,
            timeout=timeout,
            critical=critical,
            description=f"HTTP Endpoint: {url}",
        )


# Global registry instance for convenience
_global_registry = HealthCheckRegistry()


def get_registry() -> HealthCheckRegistry:
    """
    Get the global health check registry.
    """
    return _global_registry


# Backward compatibility wrapper
class HealthChecker:
    """Backward compatibility wrapper for the old HealthChecker API.

    Delegates to HealthCheckRegistry internally.
    """

    @staticmethod
    async def check_all(
        custom_checks: Optional[Dict[str, Callable]] = None,
        postgres_dsn: Optional[str] = None,
    ) -> Dict[str, Dict]:
        """Run all health checks (backward compatible).

        Automatically registers Postgres and pgvector checks. Projects should migrate to
        using HealthCheckRegistry directly.
        """
        registry = HealthCheckRegistry()

        # Only register checks that have their dependencies available
        try:
            import psycopg  # noqa: F401 - Used to check availability

            registry.register_postgres(dsn=postgres_dsn, critical=False)
            registry.register_pgvector(dsn=postgres_dsn, critical=False)
        except ImportError:
            pass

        # Add custom checks
        if custom_checks:
            for name, check_func in custom_checks.items():
                registry.register(name, check_func, critical=False)

        return await registry.run_all()

    @staticmethod
    def print_health_status(results: Dict[str, Dict]):
        """
        Print health check results (backward compatible).
        """
        registry = HealthCheckRegistry()
        registry.print_results(results)
