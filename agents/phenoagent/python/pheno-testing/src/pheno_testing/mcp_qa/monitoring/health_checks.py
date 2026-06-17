"""Health Checks for Test Framework.

Validates backend connectivity before running tests to enable graceful skipping when
infrastructure is unavailable.
"""

import asyncio
import logging
import os
from typing import Dict

logger = logging.getLogger(__name__)


class HealthChecker:
    """
    Check health of various backends before running tests.
    """

    @staticmethod
    async def check_nats() -> Dict[str, bool]:
        """
        Check NATS KV availability.
        """
        try:
            from utils.nats_kv_manager import initialize_nats_kv

            connected = await asyncio.wait_for(initialize_nats_kv(), timeout=3.0)
            return {"available": connected, "service": "NATS KV"}
        except asyncio.TimeoutError:
            logger.warning("NATS KV health check timed out (3s)")
            return {"available": False, "service": "NATS KV", "error": "Timeout"}
        except Exception as e:
            logger.warning(f"NATS KV health check failed: {e}")
            return {"available": False, "service": "NATS KV", "error": str(e)}

    @staticmethod
    def check_postgres() -> Dict[str, bool]:
        """
        Check Postgres availability.
        """
        try:
            import psycopg

            dsn = os.getenv("ZEN_PG_DSN", "postgresql://zen:zen@localhost:5432/zen_mcp")
            conn = psycopg.connect(dsn, connect_timeout=3)
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.close()
            conn.close()
            return {"available": True, "service": "Postgres"}
        except Exception as e:
            logger.warning(f"Postgres health check failed: {e}")
            return {"available": False, "service": "Postgres", "error": str(e)}

    @staticmethod
    def check_pgvector() -> Dict[str, bool]:
        """
        Check pgvector extension availability.
        """
        try:
            import psycopg

            dsn = os.getenv("ZEN_PG_DSN", "postgresql://zen:zen@localhost:5432/zen_mcp")
            conn = psycopg.connect(dsn, connect_timeout=3)
            cur = conn.cursor()
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

            # Check if document_embeddings table exists
            conn = psycopg.connect(dsn, connect_timeout=3)
            cur = conn.cursor()
            cur.execute(
                """
                SELECT 1 FROM information_schema.tables
                WHERE table_name='document_embeddings'
            """
            )
            has_tables = cur.fetchone() is not None
            cur.close()
            conn.close()

            return {
                "available": has_tables,
                "service": "pgvector",
                "note": "Extension installed" if has_vector else "Tables missing",
            }
        except Exception as e:
            logger.warning(f"pgvector health check failed: {e}")
            return {"available": False, "service": "pgvector", "error": str(e)}

    @staticmethod
    async def check_all() -> Dict[str, Dict]:
        """
        Run all health checks and return results.
        """
        results = {}

        # NATS (async)
        nats_result = await HealthChecker.check_nats()
        results["nats"] = nats_result

        # Postgres (sync)
        postgres_result = HealthChecker.check_postgres()
        results["postgres"] = postgres_result

        # pgvector (sync)
        pgvector_result = HealthChecker.check_pgvector()
        results["pgvector"] = pgvector_result

        return results

    @staticmethod
    def print_health_status(results: Dict[str, Dict]):
        """
        Print health check results in a nice format.
        """
        print("\n🏥 Backend Health Check:")
        print("=" * 60)

        for service, result in results.items():
            status = "✅" if result.get("available") else "❌"
            service_name = result.get("service", service)
            print(f"{status} {service_name:15s}", end="")

            if not result.get("available"):
                error = result.get("error", "Unknown error")
                print(f" - {error}")
            else:
                note = result.get("note", "")
                if note:
                    print(f" - {note}")
                else:
                    print(" - OK")

        print("=" * 60)

        # Count available services
        available = sum(1 for r in results.values() if r.get("available"))
        total = len(results)
        print(f"Available: {available}/{total} services\n")
