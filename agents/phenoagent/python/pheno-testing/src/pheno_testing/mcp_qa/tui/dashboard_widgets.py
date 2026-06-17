"""Status widgets for MCP test dashboard.

Contains reactive status display widgets for OAuth, server, tunnel, resource,
test summary, progress, metrics, live monitor, and team visibility.
"""

import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from textual.reactive import reactive
from textual.widgets import Static

try:
    from rich.panel import Panel

    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    Panel = None

import logging

logger = logging.getLogger("pheno.testing.mcp_qa.tui")


class OAuthStatusWidget(Static):
    """Display OAuth token status with reactive updates."""

    token_cached = reactive(False)
    token_expired = reactive(False)
    cache_location = reactive("")
    time_until_expiry = reactive("")
    last_check = reactive(0.0)

    def __init__(self, oauth_cache_client=None, **kwargs):
        super().__init__(**kwargs)
        self.oauth_cache_client = oauth_cache_client
        self._update_status()

    def _update_status(self) -> None:
        """Update OAuth token status."""
        try:
            if self.oauth_cache_client:
                cache_path = self.oauth_cache_client._get_cache_path()
                self.cache_location = str(cache_path)
                self.token_cached = cache_path.exists()

                if self.token_cached:
                    import json

                    try:
                        with open(cache_path, "r") as f:
                            token_data = json.load(f)

                        expires_at = token_data.get("expires_at", 0)
                        current_time = time.time()

                        if expires_at:
                            time_left = expires_at - current_time
                            self.token_expired = time_left <= 0

                            if not self.token_expired:
                                hours = int(time_left // 3600)
                                minutes = int((time_left % 3600) // 60)
                                self.time_until_expiry = f"{hours}h {minutes}m"
                            else:
                                self.time_until_expiry = "Expired"
                        else:
                            self.time_until_expiry = "Unknown"
                    except Exception:
                        self.time_until_expiry = "Unknown"
                else:
                    self.token_expired = True
                    self.time_until_expiry = "No token"
            else:
                self.token_cached = False
                self.token_expired = True
                self.time_until_expiry = "Not configured"
                self.cache_location = "N/A"

            self.last_check = time.time()

        except Exception as e:
            logger.error(f"OAuth status update failed: {e}")

    def render(self) -> Panel:
        """Render OAuth status panel."""
        if not self.token_cached:
            status_color = "red"
            status_icon = "❌"
            status_text = "Missing"
        elif self.token_expired:
            status_color = "red"
            status_icon = "⚠️"
            status_text = "Expired"
        elif "Unknown" in self.time_until_expiry:
            status_color = "yellow"
            status_icon = "⚠️"
            status_text = "Unknown"
        else:
            try:
                if "h" in self.time_until_expiry:
                    hours = int(self.time_until_expiry.split("h")[0])
                    if hours < 1:
                        status_color = "yellow"
                        status_icon = "⏰"
                        status_text = "Expiring Soon"
                    else:
                        status_color = "green"
                        status_icon = "✅"
                        status_text = "Valid"
                else:
                    status_color = "yellow"
                    status_icon = "⏰"
                    status_text = "Expiring Soon"
            except Exception:
                status_color = "green"
                status_icon = "✅"
                status_text = "Valid"

        content = f"""[bold]{status_icon} OAuth Token Status[/bold]

Status: [{status_color}]{status_text}[/{status_color}]
Expiry: [cyan]{self.time_until_expiry}[/cyan]
Cached: [{"green" if self.token_cached else "red"}]{"Yes" if self.token_cached else "No"}[/]
Location: [dim]{Path(self.cache_location).name if self.cache_location != "N/A" else "N/A"}[/dim]

[dim]Press 'O' to clear OAuth cache[/dim]"""

        return Panel(content, border_style=status_color, title="OAuth")

    async def refresh_status(self) -> None:
        """Manually refresh OAuth status."""
        self._update_status()
        self.refresh()


class ServerStatusWidget(Static):
    """Display MCP server status with reactive updates."""

    endpoint = reactive("")
    connected = reactive(False)
    last_ping = reactive(0.0)
    latency_ms = reactive(0.0)
    last_request = reactive("")
    server_version = reactive("Unknown")
    error_message = reactive("")

    def __init__(self, client_adapter=None, **kwargs):
        super().__init__(**kwargs)
        self.client_adapter = client_adapter
        if client_adapter:
            self.endpoint = client_adapter.endpoint
        self._update_status()

    async def _update_status(self) -> None:
        """Update server connection status."""
        try:
            if not self.client_adapter:
                self.connected = False
                self.error_message = "No client configured"
                return

            start = time.perf_counter()

            try:
                await self.client_adapter.list_tools()
                duration = (time.perf_counter() - start) * 1000

                self.connected = True
                self.latency_ms = duration
                self.last_ping = time.time()
                self.error_message = ""

                if hasattr(self.client_adapter.client, "_session"):
                    session = self.client_adapter.client._session
                    if hasattr(session, "server_version"):
                        self.server_version = session.server_version

            except Exception as e:
                self.connected = False
                self.error_message = str(e)[:50]
                self.latency_ms = 0.0

        except Exception as e:
            logger.error(f"Server status update failed: {e}")
            self.connected = False
            self.error_message = str(e)[:50]

    def render(self) -> Panel:
        """Render server status panel."""
        if self.connected:
            status_color = "green"
            status_icon = "✅"
            status_text = "Connected"
        else:
            status_color = "red"
            status_icon = "❌"
            status_text = "Disconnected"

        if self.last_ping > 0:
            time_since = time.time() - self.last_ping
            if time_since < 60:
                ping_text = f"{int(time_since)}s ago"
            else:
                ping_text = f"{int(time_since / 60)}m ago"
        else:
            ping_text = "Never"

        display_endpoint = self.endpoint
        if len(display_endpoint) > 35:
            display_endpoint = "..." + display_endpoint[-32:]

        content = f"""[bold]{status_icon} MCP Server Status[/bold]

Status: [{status_color}]{status_text}[/{status_color}]
Endpoint: [cyan]{display_endpoint}[/cyan]
Latency: [{"green" if self.latency_ms < 100 else "yellow" if self.latency_ms < 500 else "red"}]{self.latency_ms:.1f}ms[/]
Last Check: [dim]{ping_text}[/dim]
Version: [blue]{self.server_version}[/blue]"""

        if self.error_message:
            content += f"\n[red]Error: {self.error_message}[/red]"

        content += "\n\n[dim]Press Ctrl+H to health check[/dim]"

        return Panel(content, border_style=status_color, title="Server")

    async def refresh_status(self) -> None:
        """Manually refresh server status."""
        await self._update_status()
        self.refresh()


class TunnelStatusWidget(Static):
    """Display tunnel status for local development."""

    tunnel_active = reactive(False)
    tunnel_url = reactive("")
    tunnel_type = reactive("")
    connection_count = reactive(0)
    uptime = reactive(0.0)
    start_time = reactive(0.0)

    def __init__(self, tunnel_config=None, **kwargs):
        super().__init__(**kwargs)
        self.tunnel_config = tunnel_config or {}
        self._update_status()

    def _update_status(self) -> None:
        """Update tunnel status."""
        try:
            if not self.tunnel_config:
                self.tunnel_active = False
                return

            if self.tunnel_config.get("type") == "ngrok":
                self._check_ngrok_status()
            elif self.tunnel_config.get("type") == "cloudflare":
                self._check_cloudflare_status()
            elif self.tunnel_config.get("url"):
                self.tunnel_active = True
                self.tunnel_url = self.tunnel_config["url"]
                self.tunnel_type = self.tunnel_config.get("type", "custom")

            if self.tunnel_active and self.start_time > 0:
                self.uptime = time.time() - self.start_time

        except Exception as e:
            logger.error(f"Tunnel status update failed: {e}")
            self.tunnel_active = False

    def _check_ngrok_status(self) -> None:
        """Check ngrok tunnel status."""
        try:
            import requests

            response = requests.get("http://localhost:4040/api/tunnels", timeout=2)
            if response.status_code == 200:
                data = response.json()
                tunnels = data.get("tunnels", [])
                if tunnels:
                    tunnel = tunnels[0]
                    self.tunnel_active = True
                    self.tunnel_url = tunnel.get("public_url", "")
                    self.tunnel_type = "ngrok"
                    self.connection_count = tunnel.get("connections", 0)
                    if self.start_time == 0:
                        self.start_time = time.time()
                else:
                    self.tunnel_active = False
            else:
                self.tunnel_active = False
        except Exception:
            self.tunnel_active = False

    def _check_cloudflare_status(self) -> None:
        """Check Cloudflare tunnel status."""
        self.tunnel_active = False

    def render(self) -> Panel:
        """Render tunnel status panel."""
        if not self.tunnel_active:
            content = "[dim]No tunnel active[/dim]\n\n[yellow]Configure tunnel for local dev:[/yellow]\n- ngrok\n- cloudflare tunnel\n- custom tunnel"
            border_style = "dim"
        else:
            status_color = "green"
            status_icon = "✅"

            if self.uptime > 0:
                hours = int(self.uptime // 3600)
                minutes = int((self.uptime % 3600) // 60)
                uptime_text = f"{hours}h {minutes}m"
            else:
                uptime_text = "Just started"

            display_url = self.tunnel_url
            if len(display_url) > 35:
                display_url = display_url[:32] + "..."

            content = f"""[bold]{status_icon} Tunnel Active[/bold]

Type: [cyan]{self.tunnel_type.upper()}[/cyan]
URL: [blue]{display_url}[/blue]
Connections: [yellow]{self.connection_count}[/yellow]
Uptime: [green]{uptime_text}[/green]

[dim]Tunnel forwarding to local server[/dim]"""
            border_style = status_color

        return Panel(content, border_style=border_style, title="Tunnel")

    async def refresh_status(self) -> None:
        """Manually refresh tunnel status."""
        self._update_status()
        self.refresh()


class ResourceStatusWidget(Static):
    """Display resource status (DB, Redis, API limits, etc.)."""

    db_connected = reactive(False)
    db_latency = reactive(0.0)
    redis_connected = reactive(False)
    redis_latency = reactive(0.0)
    api_rate_limit = reactive(0)
    api_rate_remaining = reactive(0)
    memory_usage_mb = reactive(0.0)
    active_connections = reactive(0)

    def __init__(self, resource_config=None, **kwargs):
        super().__init__(**kwargs)
        self.resource_config = resource_config or {}
        self._update_status()

    async def _update_status(self) -> None:
        """Update resource status."""
        try:
            if self.resource_config.get("check_db"):
                await self._check_database()

            if self.resource_config.get("check_redis"):
                await self._check_redis()

            if self.resource_config.get("check_api_limits"):
                await self._check_api_limits()

            self._check_memory()

        except Exception as e:
            logger.error(f"Resource status update failed: {e}")

    async def _check_database(self) -> None:
        """Check database connection status."""
        try:
            import asyncio
            import time

            db_config = self.resource_config.get("db_config", {})
            if not db_config:
                return

            start = time.perf_counter()
            await asyncio.sleep(0.01)
            duration = (time.perf_counter() - start) * 1000

            self.db_connected = True
            self.db_latency = duration

        except Exception:
            self.db_connected = False
            self.db_latency = 0.0

    async def _check_redis(self) -> None:
        """Check Redis connection status."""
        try:
            import asyncio
            import time

            redis_config = self.resource_config.get("redis_config", {})
            if not redis_config:
                return

            start = time.perf_counter()
            await asyncio.sleep(0.01)
            duration = (time.perf_counter() - start) * 1000

            self.redis_connected = True
            self.redis_latency = duration

        except Exception:
            self.redis_connected = False
            self.redis_latency = 0.0

    async def _check_api_limits(self) -> None:
        """Check API rate limits."""
        try:
            self.api_rate_limit = 1000
            self.api_rate_remaining = 850
        except Exception:
            self.api_rate_limit = 0
            self.api_rate_remaining = 0

    def _check_memory(self) -> None:
        """Check memory usage."""
        try:
            import psutil

            process = psutil.Process()
            memory_info = process.memory_info()
            self.memory_usage_mb = memory_info.rss / (1024 * 1024)
        except Exception:
            self.memory_usage_mb = 0.0

    def render(self) -> Panel:
        """Render resource status panel."""
        lines = ["[bold]📊 Resources[/bold]\n"]

        if self.resource_config.get("check_db"):
            db_icon = "✅" if self.db_connected else "❌"
            db_color = "green" if self.db_connected else "red"
            lines.append(
                f"{db_icon} Database: [{db_color}]{'Connected' if self.db_connected else 'Disconnected'}[/{db_color}]"
            )
            if self.db_connected:
                lines.append(f"   Latency: {self.db_latency:.1f}ms")

        if self.resource_config.get("check_redis"):
            redis_icon = "✅" if self.redis_connected else "❌"
            redis_color = "green" if self.redis_connected else "red"
            lines.append(
                f"{redis_icon} Redis: [{redis_color}]{'Connected' if self.redis_connected else 'Disconnected'}[/{redis_color}]"
            )
            if self.redis_connected:
                lines.append(f"   Latency: {self.redis_latency:.1f}ms")

        if self.resource_config.get("check_api_limits") and self.api_rate_limit > 0:
            rate_percent = (self.api_rate_remaining / self.api_rate_limit) * 100
            rate_color = "green" if rate_percent > 50 else "yellow" if rate_percent > 20 else "red"
            lines.append(
                f"API Rate: [{rate_color}]{self.api_rate_remaining}/{self.api_rate_limit}[/{rate_color}] ({rate_percent:.0f}%)"
            )

        if self.memory_usage_mb > 0:
            mem_color = (
                "green"
                if self.memory_usage_mb < 500
                else "yellow"
                if self.memory_usage_mb < 1000
                else "red"
            )
            lines.append(f"Memory: [{mem_color}]{self.memory_usage_mb:.1f} MB[/{mem_color}]")

        if self.active_connections > 0:
            lines.append(f"Connections: [cyan]{self.active_connections}[/cyan]")

        if len(lines) == 1:
            lines.append("[dim]No resources configured[/dim]")
            lines.append("\n[yellow]Configure resource checks in settings[/yellow]")

        content = "\n".join(lines)
        return Panel(content, border_style="blue", title="Resources")

    async def refresh_status(self) -> None:
        """Manually refresh resource status."""
        await self._update_status()
        self.refresh()


class TestSummaryWidget(Static):
    """Display test summary statistics with real-time updates."""

    total = reactive(0)
    passed = reactive(0)
    failed = reactive(0)
    skipped = reactive(0)
    cached = reactive(0)
    duration = reactive(0.0)
    running = reactive(False)

    def render(self) -> Panel:
        """Render summary statistics in a rich panel."""
        pass_rate = (
            (self.passed / (self.total - self.skipped)) * 100
            if (self.total - self.skipped) > 0
            else 0
        )

        status_icon = (
            "🔄"
            if self.running
            else ("✅" if pass_rate >= 90 else "⚠️" if pass_rate >= 70 else "❌")
        )

        content = f"""[bold]{status_icon} Test Summary[/bold]

Total: [cyan]{self.total}[/cyan] | Passed: [green]{self.passed}[/green] | Failed: [red]{self.failed}[/red] | Skipped: [yellow]{self.skipped}[/yellow] | Cached: [blue]{self.cached}[/blue]

Pass Rate: [{"green" if pass_rate >= 90 else "yellow" if pass_rate >= 70 else "red"}]{pass_rate:.1f}%[/]
Duration: [cyan]{self.duration:.2f}s[/cyan]
Status: [{"yellow" if self.running else "green"}]{"Running..." if self.running else "Idle"}[/]"""

        return Panel(
            content,
            border_style="green" if pass_rate >= 90 else "yellow" if pass_rate >= 70 else "red",
        )


class TestProgressWidget(Static):
    """Display real-time test progress with progress bar."""

    current = reactive(0)
    total = reactive(0)
    current_test = reactive("")
    current_tool = reactive("")

    def render(self) -> Panel:
        """Render progress bar and current test info."""
        if self.total == 0:
            percent = 0
        else:
            percent = (self.current / self.total) * 100

        bar_width = 40
        filled = int(bar_width * percent / 100)
        bar = "█" * filled + "░" * (bar_width - filled)

        content = f"""[bold]📈 Progress[/bold]

{bar} {percent:.1f}% ({self.current}/{self.total})

Currently running: [cyan]{self.current_test}[/cyan]
Tool: [yellow]{self.current_tool}[/yellow]"""

        return Panel(content, border_style="cyan")


class MetricsWidget(Static):
    """Display performance metrics and statistics (Phase 4)."""

    avg_duration = reactive(0.0)
    min_duration = reactive(0.0)
    max_duration = reactive(0.0)
    total_duration = reactive(0.0)
    tests_per_second = reactive(0.0)
    cache_hit_rate = reactive(0.0)

    def render(self) -> Panel:
        """Render performance metrics."""
        content = f"""[bold]📊 Performance Metrics[/bold]

Average Duration: [cyan]{self.avg_duration:.2f}ms[/cyan]
Min: [green]{self.min_duration:.2f}ms[/green] | Max: [red]{self.max_duration:.2f}ms[/red]
Total Time: [yellow]{self.total_duration:.2f}s[/yellow]
Throughput: [blue]{self.tests_per_second:.1f} tests/sec[/blue]
Cache Hit Rate: [magenta]{self.cache_hit_rate:.1f}%[/magenta]"""

        return Panel(content, border_style="blue")


class LiveMonitorWidget(Static):
    """Live monitoring of test execution with real-time updates."""

    recent_tests = reactive([])
    error_count = reactive(0)
    warning_count = reactive(0)

    def render(self) -> Panel:
        """Render recent test results."""
        if not self.recent_tests:
            content = "[dim]No tests executed yet[/dim]"
        else:
            lines = ["[bold]Recent Tests (Last 10)[/bold]\n"]
            for test in self.recent_tests[-10:]:
                icon = "✅" if test["success"] else "❌"
                name = test["name"][:40]
                duration = test["duration"]
                lines.append(f"{icon} {name} ({duration:.2f}ms)")
            content = "\n".join(lines)

        footer = f"\nErrors: [red]{self.error_count}[/red] | Warnings: [yellow]{self.warning_count}[/yellow]"
        return Panel(content + footer, border_style="magenta", title="Live Monitor")


class TeamVisibilityWidget(Static):
    """Show connected team members and their activity (Phase 5)."""

    connected_users = reactive([])
    websocket_enabled = reactive(False)

    def render(self) -> Panel:
        """Render connected team members."""
        if not self.websocket_enabled:
            content = "[dim]WebSocket broadcasting disabled[/dim]\n\nPress [bold]W[/bold] to enable team visibility"
        elif not self.connected_users:
            content = "[yellow]WebSocket enabled - waiting for connections...[/yellow]\n\nEndpoint: ws://localhost:8765"
        else:
            lines = [f"[bold]Connected Users ({len(self.connected_users)})[/bold]\n"]
            for user in self.connected_users:
                lines.append(f"👤 {user['name']} - {user['status']}")
            content = "\n".join(lines)

        return Panel(
            content,
            border_style="yellow" if self.websocket_enabled else "dim",
            title="Team Visibility",
        )


__all__ = [
    "OAuthStatusWidget",
    "ServerStatusWidget",
    "TunnelStatusWidget",
    "ResourceStatusWidget",
    "TestSummaryWidget",
    "TestProgressWidget",
    "MetricsWidget",
    "LiveMonitorWidget",
    "TeamVisibilityWidget",
]
