"""Connection Manager with Retry, Restart, and Loss Detection.

Handles:
- Connection loss detection
- Automatic retry with exponential backoff
- Connection restart on persistent failures
- Cache invalidation on connection loss
- Server restart detection
"""

import asyncio
import time
from typing import Any, Dict

try:
    from rich.console import Console
    from rich.panel import Panel

    HAS_RICH = True
except ImportError:
    HAS_RICH = False


class ConnectionState:
    """
    Track connection state and detect restarts.
    """

    def __init__(self):
        self.connected = False
        self.last_successful_call = 0.0
        self.connection_start_time = 0.0
        self.total_disconnections = 0
        self.server_version = None
        self.server_start_time = None

    def mark_connected(self):
        """
        Mark connection as established.
        """
        if not self.connected:
            self.connection_start_time = time.time()
            self.connected = True

    def mark_disconnected(self):
        """
        Mark connection as lost.
        """
        if self.connected:
            self.total_disconnections += 1
            self.connected = False

    def mark_successful_call(self):
        """
        Record successful call.
        """
        self.last_successful_call = time.time()
        self.mark_connected()

    def detect_server_restart(self, server_info: Dict[str, Any]) -> bool:
        """Detect if server has restarted.

        Args:
            server_info: Server metadata (version, start_time, etc.)

        Returns:
            True if server restart detected
        """
        current_version = server_info.get("version")
        current_start_time = server_info.get("start_time")

        # First time seeing server info
        if self.server_version is None:
            self.server_version = current_version
            self.server_start_time = current_start_time
            return False

        # Version changed = deployment/restart
        if current_version != self.server_version:
            print(f"🔄 Server restart detected: {self.server_version} → {current_version}")
            self.server_version = current_version
            self.server_start_time = current_start_time
            return True

        # Start time changed = restart
        if current_start_time != self.server_start_time:
            print("🔄 Server restart detected: start time changed")
            self.server_start_time = current_start_time
            return True

        return False


class ConnectionManager:
    """Manages MCP client connection with retry, restart, and loss detection.

    Features:
    - Automatic retry with exponential backoff (3 attempts)
    - Connection restart on persistent failures
    - Cache invalidation on connection loss
    - Server restart detection
    - Wait strategies (immediate, linear, exponential)
    """

    def __init__(
        self,
        client_adapter: Any,
        cache_instance: Any = None,
        max_retries: int = 3,
        initial_backoff: float = 1.0,
        max_backoff: float = 30.0,
        backoff_multiplier: float = 2.0,
    ):
        self.client_adapter = client_adapter
        self.cache_instance = cache_instance
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self.max_backoff = max_backoff
        self.backoff_multiplier = backoff_multiplier

        self.state = ConnectionState()
        self.console = Console() if HAS_RICH else None

    async def call_with_retry(
        self,
        tool_name: str,
        params: Dict[str, Any],
        test_name: str = "unknown",
    ) -> Dict[str, Any]:
        """Call tool with automatic retry on failure.

        Args:
            tool_name: MCP tool name
            params: Tool parameters
            test_name: Test name for logging

        Returns:
            Tool result or error after all retries exhausted
        """
        last_error = None
        backoff = self.initial_backoff

        for attempt in range(1, self.max_retries + 1):
            try:
                # Attempt the call
                result = await self.client_adapter.call_tool(tool_name, params)

                # Success!
                if result.get("success"):
                    self.state.mark_successful_call()
                    return result

                # Tool returned error (not connection issue)
                last_error = result.get("error", "Unknown error")

                # Don't retry tool errors (only connection errors)
                if not self._is_connection_error(last_error):
                    return result

                # Connection error - retry
                await self._handle_retry(attempt, last_error, backoff, test_name)
                backoff = min(backoff * self.backoff_multiplier, self.max_backoff)

            except Exception as e:
                last_error = str(e)

                # Check if connection error
                if self._is_connection_error(last_error):
                    self.state.mark_disconnected()

                    # Invalidate cache on connection loss (server may have restarted)
                    if self.cache_instance and self.state.total_disconnections > 0:
                        print(
                            "🗑️  Connection lost - invalidating test cache (server may have restarted)"
                        )
                        self.cache_instance.clear()

                    # Retry with backoff
                    if attempt < self.max_retries:
                        await self._handle_retry(attempt, last_error, backoff, test_name)
                        backoff = min(backoff * self.backoff_multiplier, self.max_backoff)
                    else:
                        return {
                            "success": False,
                            "error": f"Connection failed after {self.max_retries} attempts: {last_error}",
                            "duration_ms": 0,
                            "connection_lost": True,
                        }
                else:
                    # Non-connection error - don't retry
                    return {
                        "success": False,
                        "error": str(e),
                        "duration_ms": 0,
                    }

        # All retries exhausted
        return {
            "success": False,
            "error": f"Failed after {self.max_retries} attempts: {last_error}",
            "duration_ms": 0,
            "retries_exhausted": True,
        }

    async def _handle_retry(self, attempt: int, error: str, backoff: float, test_name: str):
        """
        Handle retry with backoff and logging.
        """
        if self.console and HAS_RICH:
            self.console.print(
                Panel(
                    f"[yellow]Attempt {attempt}/{self.max_retries} failed[/yellow]\n"
                    f"Test: {test_name}\n"
                    f"Error: {error[:100]}\n"
                    f"Retrying in {backoff:.1f}s...",
                    title="[bold yellow]Connection Retry[/bold yellow]",
                    border_style="yellow",
                )
            )
        else:
            print(f"⚠️  Attempt {attempt}/{self.max_retries} failed: {error[:100]}")
            print(f"   Retrying in {backoff:.1f}s...")

        await asyncio.sleep(backoff)

    def _is_connection_error(self, error: str) -> bool:
        """
        Check if error is connection-related.
        """
        connection_keywords = [
            "connection refused",
            "connection reset",
            "connection timeout",
            "network unreachable",
            "host unreachable",
            "timeout",
            "timed out",
            "connection error",
            "connection failed",
            "broken pipe",
            "cannot connect",
            "httpstatuserror",  # httpx errors
            "server error",  # HTTP 5xx
            "530",  # Cloudflare custom error
            "502",  # Bad gateway
            "503",  # Service unavailable
            "504",  # Gateway timeout
            "500",  # Internal server error
        ]

        error_lower = error.lower()
        return any(keyword in error_lower for keyword in connection_keywords)

    async def restart_connection(self) -> bool:
        """Restart connection from scratch.

        Returns:
            True if restart successful
        """
        if self.console and HAS_RICH:
            self.console.print(
                Panel(
                    "[yellow]Connection lost - attempting restart...[/yellow]\n"
                    f"Disconnections: {self.state.total_disconnections}\n"
                    "This may take 10-30 seconds...",
                    title="[bold yellow]Connection Restart[/bold yellow]",
                    border_style="yellow",
                )
            )
        else:
            print(
                f"🔄 Restarting connection (disconnections: {self.state.total_disconnections})..."
            )

        try:
            # Re-authenticate if needed
            # This would trigger OAuth flow again
            # For now, just mark as attempting restart
            await asyncio.sleep(2)  # Simulate restart delay

            # Try a test call
            test_result = await self.client_adapter.list_tools()

            if test_result:
                self.state.mark_connected()
                print("✅ Connection restarted successfully")
                return True

        except Exception as e:
            print(f"❌ Connection restart failed: {e}")
            self.state.mark_disconnected()

        return False

    def get_connection_stats(self) -> Dict[str, Any]:
        """
        Get connection statistics.
        """
        return {
            "connected": self.state.connected,
            "uptime_seconds": (
                time.time() - self.state.connection_start_time if self.state.connected else 0
            ),
            "last_successful_call": self.state.last_successful_call,
            "total_disconnections": self.state.total_disconnections,
            "time_since_last_call": (
                time.time() - self.state.last_successful_call
                if self.state.last_successful_call > 0
                else -1
            ),
        }


class WaitStrategy:
    """
    Wait strategies for retry delays.
    """

    @staticmethod
    def immediate() -> float:
        """
        No wait.
        """
        return 0.0

    @staticmethod
    def linear(attempt: int, base_delay: float = 1.0) -> float:
        """Linear backoff: delay × attempt."""
        return base_delay * attempt

    @staticmethod
    def exponential(attempt: int, base_delay: float = 1.0, max_delay: float = 30.0) -> float:
        """Exponential backoff: base × 2^attempt."""
        delay = base_delay * (2 ** (attempt - 1))
        return min(delay, max_delay)

    @staticmethod
    def fibonacci(attempt: int, base_delay: float = 1.0) -> float:
        """Fibonacci backoff: base × fib(attempt)."""

        def fib(n):
            if n <= 1:
                return n
            return fib(n - 1) + fib(n - 2)

        return base_delay * fib(attempt)


__all__ = ["ConnectionManager", "ConnectionState", "WaitStrategy"]
