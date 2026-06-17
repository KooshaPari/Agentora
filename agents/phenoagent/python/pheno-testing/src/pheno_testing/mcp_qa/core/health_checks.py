"""
Health Checks - Backend Connectivity Validation

Unified health checking from both frameworks:
- NATS KV availability
- Postgres connectivity
- pgvector extension
- Generic health check interface
"""

import asyncio
import logging
import os
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class HealthChecker:
    """Check health of various backends before running tests.

    Enables graceful skipping when infrastructure is unavailable.
    """

    @staticmethod
    async def check_nats() -> Dict[str, Any]:
        """Check NATS KV availability.

        Returns:
            {
                "available": bool,
                "service": str,
                "error": Optional[str]
            }
        """
        try:
            # Try to import and connect to NATS
            # This is framework-specific and should be customized
            from utils.nats_kv_manager import initialize_nats_kv

            connected = await asyncio.wait_for(initialize_nats_kv(), timeout=3.0)
            return {"available": connected, "service": "NATS KV"}
        except asyncio.TimeoutError:
            logger.warning("NATS KV health check timed out (3s)")
            return {"available": False, "service": "NATS KV", "error": "Timeout"}
        except ImportError:
            logger.warning("NATS KV module not found")
            return {"available": False, "service": "NATS KV", "error": "Module not found"}
        except Exception as e:
            logger.warning(f"NATS KV health check failed: {e}")
            return {"available": False, "service": "NATS KV", "error": str(e)}

    @staticmethod
    def check_postgres(dsn: Optional[str] = None) -> Dict[str, Any]:
        """Check Postgres availability.

        Args:
            dsn: Database connection string (uses env var if None)

        Returns:
            {
                "available": bool,
                "service": str,
                "error": Optional[str]
            }
        """
        try:
            import psycopg

            dsn = dsn or os.getenv("DATABASE_URL", "postgresql://localhost:5432/postgres")
            conn = psycopg.connect(dsn, connect_timeout=3)
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.close()
            conn.close()
            return {"available": True, "service": "Postgres"}
        except ImportError:
            logger.warning("psycopg not installed")
            return {"available": False, "service": "Postgres", "error": "psycopg not installed"}
        except Exception as e:
            logger.warning(f"Postgres health check failed: {e}")
            return {"available": False, "service": "Postgres", "error": str(e)}

    @staticmethod
    def check_pgvector(dsn: Optional[str] = None) -> Dict[str, Any]:
        """Check pgvector extension availability.

        Args:
            dsn: Database connection string (uses env var if None)

        Returns:
            {
                "available": bool,
                "service": str,
                "error": Optional[str],
                "note": Optional[str]
            }
        """
        try:
            import psycopg

            dsn = dsn or os.getenv("DATABASE_URL", "postgresql://localhost:5432/postgres")
            conn = psycopg.connect(dsn, connect_timeout=3)
            cur = conn.cursor()

            # Check extension
            cur.execute("SELECT 1 FROM pg_extension WHERE extname='vector'")
            has_vector = cur.fetchone() is not None
            cur.close()
            conn.close()

            if not has_vector:
                return {
                    "available": False,
                    "service": "pgvector",
                    "error": "Extension not installed",
                }

            return {"available": True, "service": "pgvector", "note": "Extension installed"}

        except ImportError:
            logger.warning("psycopg not installed")
            return {"available": False, "service": "pgvector", "error": "psycopg not installed"}
        except Exception as e:
            logger.warning(f"pgvector health check failed: {e}")
            return {"available": False, "service": "pgvector", "error": str(e)}

    @staticmethod
    async def check_custom(
        name: str,
        check_func: Callable[[], Any],
        timeout: float = 3.0,
    ) -> Dict[str, Any]:
        """Run a custom health check.

        Args:
            name: Service name
            check_func: Callable that returns True if healthy
            timeout: Timeout in seconds

        Returns:
            {
                "available": bool,
                "service": str,
                "error": Optional[str]
            }
        """
        try:
            if asyncio.iscoroutinefunction(check_func):
                result = await asyncio.wait_for(check_func(), timeout=timeout)
            else:
                result = check_func()

            return {
                "available": bool(result),
                "service": name,
            }
        except asyncio.TimeoutError:
            return {"available": False, "service": name, "error": "Timeout"}
        except Exception as e:
            return {"available": False, "service": name, "error": str(e)}

    @staticmethod
    async def check_all(
        custom_checks: Optional[Dict[str, Callable]] = None,
        postgres_dsn: Optional[str] = None,
    ) -> Dict[str, Dict]:
        """Run all health checks and return results.

        Args:
            custom_checks: Optional dict of name -> check_func
            postgres_dsn: Optional Postgres DSN

        Returns:
            Dict of service_name -> health_result
        """
        results = {}

        # NATS (async)
        nats_result = await HealthChecker.check_nats()
        results["nats"] = nats_result

        # Postgres (sync)
        postgres_result = HealthChecker.check_postgres(postgres_dsn)
        results["postgres"] = postgres_result

        # pgvector (sync)
        pgvector_result = HealthChecker.check_pgvector(postgres_dsn)
        results["pgvector"] = pgvector_result

        # Custom checks
        if custom_checks:
            for name, check_func in custom_checks.items():
                result = await HealthChecker.check_custom(name, check_func)
                results[name] = result

        return results

    @staticmethod
    def print_health_status(results: Dict[str, Dict]):
        """
        Print health check results in a nice format.
        """
        print("\nBackend Health Check:")
        print("=" * 60)

        for service, result in results.items():
            status = "OK" if result.get("available") else "FAIL"
            service_name = result.get("service", service)
            print(f"{status:4s} {service_name:15s}", end="")

            if not result.get("available"):
                error = result.get("error", "Unknown error")
                print(f" - {error}")
            else:
                note = result.get("note", "")
                if note:
                    print(f" - {note}")
                else:
                    print()

        print("=" * 60)

        # Count available services
        available = sum(1 for r in results.values() if r.get("available"))
        total = len(results)
        print(f"Available: {available}/{total} services\n")
