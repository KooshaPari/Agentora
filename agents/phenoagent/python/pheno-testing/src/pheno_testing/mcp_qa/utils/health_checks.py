"""Health Checks for MCP Test Framework.

Validates backend connectivity and tool availability before running tests to enable
graceful skipping when infrastructure is unavailable.

Unified implementation combining best features from Zen and Atoms frameworks.
"""

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

try:
    from rich.console import Console
    from rich.table import Table

    HAS_RICH = True
except ImportError:
    HAS_RICH = False

logger = logging.getLogger(__name__)


class HealthCheckResult:
    """
    Result of a health check operation.
    """

    def __init__(
        self,
        service: str,
        available: bool,
        error: Optional[str] = None,
        note: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.service = service
        self.available = available
        self.error = error
        self.note = note
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary representation.
        """
        result = {
            "service": self.service,
            "available": self.available,
        }
        if self.error:
            result["error"] = self.error
        if self.note:
            result["note"] = self.note
        if self.details:
            result["details"] = self.details
        return result


class HealthChecker:
    """
    Check health of various backends and services before running tests.
    """

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.console = Console() if HAS_RICH and verbose else None

    async def check_nats(self) -> HealthCheckResult:
        """
        Check NATS KV availability.
        """
        try:
            from utils.nats_kv_manager import initialize_nats_kv

            connected = await asyncio.wait_for(initialize_nats_kv(), timeout=3.0)
            return HealthCheckResult(
                service="NATS KV",
                available=connected,
                note="Connected" if connected else "Not available",
            )
        except asyncio.TimeoutError:
            logger.warning("NATS KV health check timed out (3s)")
            return HealthCheckResult(
                service="NATS KV",
                available=False,
                error="Timeout after 3s",
            )
        except ImportError:
            return HealthCheckResult(
                service="NATS KV",
                available=False,
                error="nats_kv_manager module not found",
            )
        except Exception as e:
            logger.warning(f"NATS KV health check failed: {e}")
            return HealthCheckResult(
                service="NATS KV",
                available=False,
                error=str(e),
            )

    def check_postgres(self, dsn: Optional[str] = None) -> HealthCheckResult:
        """
        Check Postgres availability.
        """
        try:
            import psycopg

            dsn = dsn or os.getenv("ZEN_PG_DSN", "postgresql://zen:zen@localhost:5432/zen_mcp")
            conn = psycopg.connect(dsn, connect_timeout=3)
            cur = conn.cursor()
            cur.execute("SELECT version()")
            version = cur.fetchone()
            cur.close()
            conn.close()

            return HealthCheckResult(
                service="Postgres",
                available=True,
                note="Connected",
                details={"version": version[0] if version else "unknown"},
            )
        except ImportError:
            return HealthCheckResult(
                service="Postgres",
                available=False,
                error="psycopg module not installed",
            )
        except Exception as e:
            logger.warning(f"Postgres health check failed: {e}")
            return HealthCheckResult(
                service="Postgres",
                available=False,
                error=str(e),
            )

    def check_pgvector(self, dsn: Optional[str] = None) -> HealthCheckResult:
        """
        Check pgvector extension availability.
        """
        try:
            import psycopg

            dsn = dsn or os.getenv("ZEN_PG_DSN", "postgresql://zen:zen@localhost:5432/zen_mcp")
            conn = psycopg.connect(dsn, connect_timeout=3)
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM pg_extension WHERE extname='vector'")
            has_vector = cur.fetchone() is not None
            cur.close()
            conn.close()

            if not has_vector:
                return HealthCheckResult(
                    service="pgvector",
                    available=False,
                    error="Extension not installed",
                )

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

            return HealthCheckResult(
                service="pgvector",
                available=has_tables,
                note="Extension installed, tables " + ("present" if has_tables else "missing"),
            )
        except ImportError:
            return HealthCheckResult(
                service="pgvector",
                available=False,
                error="psycopg module not installed",
            )
        except Exception as e:
            logger.warning(f"pgvector health check failed: {e}")
            return HealthCheckResult(
                service="pgvector",
                available=False,
                error=str(e),
            )

    async def check_mcp_server(
        self,
        client,
        expected_tools: Optional[List[str]] = None,
    ) -> HealthCheckResult:
        """Check MCP server connectivity and tool availability.

        Args:
            client: MCP client instance
            expected_tools: Optional list of tool names to verify

        Returns:
            HealthCheckResult with server status
        """
        try:
            # Try to list tools
            tools = await asyncio.wait_for(client.list_tools(), timeout=5.0)

            if not tools:
                return HealthCheckResult(
                    service="MCP Server",
                    available=False,
                    error="No tools available",
                )

            tool_names = [tool.name for tool in tools] if hasattr(tools[0], "name") else tools

            # Check for expected tools if provided
            missing_tools = []
            if expected_tools:
                missing_tools = [t for t in expected_tools if t not in tool_names]

            if missing_tools:
                return HealthCheckResult(
                    service="MCP Server",
                    available=False,
                    error=f"Missing required tools: {', '.join(missing_tools)}",
                    details={
                        "available_tools": len(tool_names),
                        "missing_tools": missing_tools,
                    },
                )

            return HealthCheckResult(
                service="MCP Server",
                available=True,
                note=f"{len(tool_names)} tools available",
                details={"tool_count": len(tool_names), "tools": tool_names},
            )

        except asyncio.TimeoutError:
            return HealthCheckResult(
                service="MCP Server",
                available=False,
                error="Timeout after 5s",
            )
        except Exception as e:
            logger.warning(f"MCP server health check failed: {e}")
            return HealthCheckResult(
                service="MCP Server",
                available=False,
                error=str(e),
            )

    async def check_oauth_session(self, session_broker) -> HealthCheckResult:
        """Check OAuth session validity.

        Args:
            session_broker: OAuthSessionBroker instance

        Returns:
            HealthCheckResult with session status
        """
        try:
            # Try to get token payload
            token_payload = await asyncio.wait_for(session_broker.get_token_payload(), timeout=3.0)

            if not token_payload.get("access_token"):
                return HealthCheckResult(
                    service="OAuth Session",
                    available=False,
                    error="Token exists but missing access_token",
                )

            # Check token expiration if available
            expires_at = token_payload.get("expires_at")
            if expires_at:
                import time

                is_expired = time.time() > expires_at
                if is_expired:
                    return HealthCheckResult(
                        service="OAuth Session",
                        available=False,
                        error="Token expired",
                        details={"expired_at": expires_at},
                    )

            return HealthCheckResult(
                service="OAuth Session",
                available=True,
                note="Valid token cached",
                details={"token_type": token_payload.get("token_type", "Bearer")},
            )

        except FileNotFoundError:
            return HealthCheckResult(
                service="OAuth Session",
                available=False,
                error="No cached token found",
                note="First run or cache cleared",
            )
        except asyncio.TimeoutError:
            return HealthCheckResult(
                service="OAuth Session",
                available=False,
                error="Timeout reading token cache",
            )
        except Exception as e:
            logger.warning(f"OAuth session health check failed: {e}")
            return HealthCheckResult(
                service="OAuth Session",
                available=False,
                error=str(e),
            )

    async def check_all(
        self,
        checks: List[str] = None,
        mcp_client=None,
        session_broker=None,
        postgres_dsn: Optional[str] = None,
    ) -> Dict[str, HealthCheckResult]:
        """Run multiple health checks.

        Args:
            checks: List of check names to run. If None, runs all available checks.
                   Available: ['nats', 'postgres', 'pgvector', 'mcp_server', 'oauth_session']
            mcp_client: MCP client for server checks
            session_broker: OAuth session broker for OAuth checks
            postgres_dsn: Custom Postgres DSN

        Returns:
            Dictionary mapping check names to HealthCheckResult objects
        """
        if checks is None:
            checks = ["postgres", "pgvector"]
            if mcp_client:
                checks.append("mcp_server")
            if session_broker:
                checks.append("oauth_session")

        results = {}

        for check in checks:
            if check == "nats":
                results["nats"] = await self.check_nats()
            elif check == "postgres":
                results["postgres"] = self.check_postgres(postgres_dsn)
            elif check == "pgvector":
                results["pgvector"] = self.check_pgvector(postgres_dsn)
            elif check == "mcp_server" and mcp_client:
                results["mcp_server"] = await self.check_mcp_server(mcp_client)
            elif check == "oauth_session" and session_broker:
                results["oauth_session"] = await self.check_oauth_session(session_broker)

        return results

    def print_health_status(self, results: Dict[str, HealthCheckResult]):
        """
        Print health check results in a nice format.
        """
        if self.console and HAS_RICH:
            self._print_rich_status(results)
        else:
            self._print_simple_status(results)

    def _print_rich_status(self, results: Dict[str, HealthCheckResult]):
        """
        Print health status using Rich formatting.
        """
        table = Table(title="Backend Health Check", show_header=True)
        table.add_column("Service", style="cyan", no_wrap=True)
        table.add_column("Status", style="bold")
        table.add_column("Details")

        for key, result in results.items():
            status = (
                "[green]✓ Available[/green]" if result.available else "[red]✗ Unavailable[/red]"
            )
            details = result.note or result.error or ""

            table.add_row(result.service, status, details)

        self.console.print(table)

        # Summary
        available = sum(1 for r in results.values() if r.available)
        total = len(results)
        self.console.print(f"\n[bold]Summary:[/bold] {available}/{total} services available\n")

    def _print_simple_status(self, results: Dict[str, HealthCheckResult]):
        """
        Print health status using simple text formatting.
        """
        print("\nBackend Health Check:")
        print("=" * 70)

        for key, result in results.items():
            status = "✓" if result.available else "✗"
            service_name = result.service
            print(f"{status} {service_name:20s}", end="")

            if not result.available:
                error = result.error or "Unknown error"
                print(f" - {error}")
            else:
                note = result.note or "OK"
                print(f" - {note}")

        print("=" * 70)

        # Count available services
        available = sum(1 for r in results.values() if r.available)
        total = len(results)
        print(f"Available: {available}/{total} services\n")


__all__ = ["HealthChecker", "HealthCheckResult"]
