"""
Base monitor class for process orchestration.
"""

from __future__ import annotations

import signal
from abc import ABC, abstractmethod
from typing import Any


class BaseMonitor(ABC):
    """Abstract base class for process monitors.

    Provides lifecycle management, signal handling, and multiple run modes. Subclass to
    create custom monitors with specific behavior.
    """

    def __init__(
        self,
        name: str,
        processes: list[dict[str, Any]] | None = None,
        health_checks: list[dict[str, Any]] | None = None,
    ):
        """Initialize monitor.

        Args:
            name: Monitor name
            processes: List of process configurations
            health_checks: List of health check configurations
        """
        self.name = name
        self.processes = processes or []
        self.health_checks = health_checks or []
        self.running = False
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """
        Setup signal handlers for graceful shutdown.
        """
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def _handle_signal(self, signum, frame):
        """
        Handle shutdown signals.
        """
        print(f"\n🛑 Received signal {signum}, shutting down gracefully...")
        self.stop()

    @abstractmethod
    def start(self):
        """Start all monitored processes.

        Implementation should:
        1. Start each process
        2. Setup health checks
        3. Set self.running = True
        """

    @abstractmethod
    def stop(self):
        """Stop all monitored processes.

        Implementation should:
        1. Stop all processes gracefully
        2. Cleanup resources
        3. Set self.running = False
        """

    @abstractmethod
    def get_status(self) -> dict[str, Any]:
        """Get current status of all processes.

        Returns:
            Status dictionary with process states
        """

    def run_with_tui(self):
        """Run monitor with rich TUI dashboard.

        Uses rich library for interactive monitoring with live updates.
        """
        try:
            import datetime
            import time

            from rich.align import Align
            from rich.console import Console
            from rich.layout import Layout
            from rich.live import Live
            from rich.panel import Panel
            from rich.table import Table
            from rich.text import Text

            console = Console()

            # Print startup banner
            console.print(f"\n🚀 Starting [bold cyan]{self.name}[/bold cyan] monitor...\n")

            self.start()

            start_time = time.time()

            def generate_dashboard():
                """
                Generate enhanced dashboard with process, health, and metrics.
                """
                # Create layout
                layout = Layout()
                layout.split_column(
                    Layout(name="header", size=3),
                    Layout(name="main"),
                    Layout(name="metrics", size=8),
                    Layout(name="footer", size=3),
                )

                # Header
                elapsed = time.time() - start_time
                elapsed_str = str(datetime.timedelta(seconds=int(elapsed)))
                header_text = Text()
                header_text.append(f"⚡ {self.name} Monitor", style="bold cyan")
                header_text.append(f" | Uptime: {elapsed_str}", style="dim")
                layout["header"].update(Align.center(Panel(header_text, style="bold")))

                # Process table
                table = Table(show_header=True, header_style="bold magenta", box=None)
                table.add_column("Process", style="cyan", no_wrap=True)
                table.add_column("Status", style="white")
                table.add_column("Port", style="yellow")
                table.add_column("PID", style="dim")
                table.add_column("Health", style="white")

                status = self.get_status()
                health_status = status.get("health", {})

                for proc in status.get("processes", []):
                    # Determine status with color
                    is_running = proc.get("running", False)
                    pid = proc.get("pid")

                    if is_running and pid:
                        status_text = Text("● running", style="bold bright_green")
                    elif pid and not is_running:
                        status_text = Text("✗ stopped", style="bold bright_red")
                    else:
                        status_text = Text("○ not started", style="dim")

                    # Format port
                    port = proc.get("port")
                    port_str = str(port) if port else "None"

                    # Format PID
                    pid_str = str(pid) if pid else ""

                    # Health status
                    proc_name = proc.get("name", "unknown")
                    health_info = health_status.get(proc_name, {})
                    if health_info.get("healthy"):
                        health_text = Text("✓ healthy", style="green")
                    elif is_running:
                        health_text = Text("◐ checking", style="yellow")
                    else:
                        health_text = Text("", style="dim")

                    table.add_row(proc_name, status_text, port_str, pid_str, health_text)

                layout["main"].update(
                    Panel(table, title="[bold]Processes[/bold]", border_style="cyan"),
                )

                # Metrics panel
                try:
                    import psutil

                    cpu_percent = psutil.cpu_percent(interval=0.1)
                    memory = psutil.virtual_memory()

                    metrics_table = Table.grid(padding=(0, 2))
                    metrics_table.add_column(style="bold bright_cyan")
                    metrics_table.add_column()

                    metrics_table.add_row("CPU Usage:", f"{cpu_percent:.1f}%")
                    metrics_table.add_row(
                        "Memory:",
                        f"{memory.percent:.1f}% ({memory.used // (1024**3)}GB / {memory.total // (1024**3)}GB)",
                    )
                    metrics_table.add_row("Monitor Uptime:", elapsed_str)
                    metrics_table.add_row(
                        "Active Processes:",
                        str(len([p for p in status.get("processes", []) if p.get("running")])),
                    )

                    layout["metrics"].update(
                        Panel(
                            metrics_table,
                            title="[bold bright_magenta]System Metrics[/bold bright_magenta]",
                            border_style="bright_blue",
                        ),
                    )
                except ImportError:
                    # psutil not available
                    layout["metrics"].update(
                        Panel(
                            Text("Install psutil for system metrics", style="dim"),
                            title="[bold]Metrics[/bold]",
                            border_style="dim",
                        ),
                    )

                # Footer with controls
                footer_text = Text()
                footer_text.append("Press ", style="dim")
                footer_text.append("Ctrl+C", style="bold yellow")
                footer_text.append(" to stop", style="dim")
                layout["footer"].update(Align.center(Panel(footer_text, style="dim")))

                return layout

            with Live(generate_dashboard(), refresh_per_second=2, console=console) as live:
                while self.running:
                    live.update(generate_dashboard())
                    time.sleep(0.5)

        except ImportError:
            print("⚠️  rich library not installed. Install with: pip install rich")
            self.run_headless()
        except KeyboardInterrupt:
            self.stop()

    def run_headless(self):
        """Run monitor in headless mode (no TUI).

        Suitable for production/background execution.
        """
        import time

        self.start()

        print(f"✅ {self.name} monitor started (headless mode)")
        print("Press Ctrl+C to stop")

        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    async def run_with_api(self, host: str = "0.0.0.0", port: int = 3737):
        """Run monitor with REST + WebSocket API.

        Args:
            host: API host
            port: API port
        """
        try:
            import uvicorn
            from fastapi import FastAPI, WebSocket
            from fastapi.responses import JSONResponse

            app = FastAPI(title=f"{self.name} Monitor API")

            @app.get("/status")
            async def status():
                """
                Get current status.
                """
                return JSONResponse(self.get_status())

            @app.post("/start")
            async def start_endpoint():
                """
                Start monitoring.
                """
                self.start()
                return {"status": "started"}

            @app.post("/stop")
            async def stop_endpoint():
                """
                Stop monitoring.
                """
                self.stop()
                return {"status": "stopped"}

            @app.websocket("/ws")
            async def websocket_endpoint(websocket: WebSocket):
                """
                WebSocket for real-time status updates.
                """
                await websocket.accept()
                import asyncio

                while self.running:
                    status = self.get_status()
                    await websocket.send_json(status)
                    await asyncio.sleep(1)

            self.start()

            config = uvicorn.Config(app, host=host, port=port, log_level="info")
            server = uvicorn.Server(config)
            await server.serve()

        except ImportError:
            print("⚠️  fastapi/uvicorn not installed. Install with: pip install fastapi uvicorn")
            self.run_headless()
