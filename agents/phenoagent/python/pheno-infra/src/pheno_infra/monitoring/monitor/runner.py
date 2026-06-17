"""
High level service monitor orchestration.
"""

from __future__ import annotations

import asyncio
import time
from asyncio.subprocess import Process as AsyncProcess

from .logs import LogStore
from .panel import build_status_panel
from .process import ProcessInspector

try:  # pragma: no cover - optional dependency
    from rich.console import Console
    from rich.live import Live

    HAS_RICH = True
except ImportError:  # pragma: no cover - degrade gracefully when Rich missing
    Console = None  # type: ignore
    Live = None  # type: ignore
    HAS_RICH = False

import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from .config import MonitorConfig


class ServiceMonitor:
    """
    Rich-based service monitor with scrolling logs and fixed TUI panel.
    """

    def __init__(self, config: MonitorConfig, console: Console | None = None):
        self.config = config
        self._use_rich = bool(config.enable_rich and HAS_RICH)
        self.console = (
            console
            if (self._use_rich and console)
            else (Console() if self._use_rich and console is None else None)
        )

        self.processes: dict[str, subprocess.Popen | AsyncProcess | None] = {}
        self.ports: dict[str, int] = {}
        self.tunnel_urls: dict[str, str] = {}
        self.start_time = time.time()

        self._shutdown = False
        self._exit_reported: dict[str, bool] = {}

        self._inspector = ProcessInspector()
        def stop_checker() -> bool:
            return self._shutdown
        self._logs = LogStore(self.config, self.console, stop_checker)

    def attach_process(
        self,
        service_name: str,
        process: subprocess.Popen | AsyncProcess | None = None,
        port: int | None = None,
        tunnel_url: str | None = None,
        status_getter: Callable[[], bool] | None = None,
        pid_getter: Callable[[], int | None] | None = None,
    ) -> None:
        """
        Attach or update tracking for a service process.
        """
        self.processes[service_name] = process
        self._exit_reported[service_name] = False

        if port is not None:
            self.ports[service_name] = port
        if tunnel_url:
            self.tunnel_urls[service_name] = tunnel_url

        self._inspector.set_overrides(service_name, status_getter, pid_getter)
        self._logs.register_service(service_name)

    def detach_process(self, service_name: str) -> None:
        """
        Detach a service from monitoring.
        """
        self.processes.pop(service_name, None)
        self.ports.pop(service_name, None)
        self.tunnel_urls.pop(service_name, None)
        self._inspector.clear_overrides(service_name)
        self._logs.clear_service(service_name)

    async def run(self) -> None:
        """
        Run the monitor (blocking until shutdown).
        """
        if not self._use_rich or not self.console or Live is None:
            await self._run_simple()
            return

        self._start_log_readers()

        try:
            with Live(
                build_status_panel(
                    self.config,
                    self._inspector,
                    self.processes,
                    self.ports,
                    self.tunnel_urls,
                    self.start_time,
                ),
                console=self.console,
                refresh_per_second=1.0 / self.config.refresh_interval,
                screen=False,
            ) as live:
                while not self._shutdown:
                    await asyncio.sleep(self.config.refresh_interval)
                    live.update(
                        build_status_panel(
                            self.config,
                            self._inspector,
                            self.processes,
                            self.ports,
                            self.tunnel_urls,
                            self.start_time,
                        ),
                    )
                    self._check_process_exits()

        except KeyboardInterrupt:
            timestamp = time.strftime("%H:%M:%S")
            if self.console:
                self.console.print(f"\n[dim]{timestamp}[/dim] [yellow]👋 Shutting down...[/yellow]")
            self._shutdown = True
        finally:
            self._logs.cancel_async_tasks()
            await self._logs.wait_async_shutdown()

    async def _run_simple(self) -> None:
        """
        Fallback polling loop when Rich is unavailable.
        """
        while not self._shutdown:
            await asyncio.sleep(5.0)
            print("\n" + "=" * 60)
            print(f"Project: {self.config.project_name}")
            print("=" * 60)

            for service_name, process in self.processes.items():
                running = self._inspector.is_running(service_name, process)
                status = "Running" if running else "Stopped"
                port = self.ports.get(service_name, "-")
                print(f"{service_name}: {status} | Port: {port}")

            print("=" * 60)

    def _start_log_readers(self) -> None:
        """
        Start log streaming for all attached services.
        """
        for service_name, process in self.processes.items():
            if isinstance(process, subprocess.Popen):
                self._logs.start_subprocess_streams(service_name, process)

        for service_name, process in self.processes.items():
            if isinstance(process, AsyncProcess):
                self._logs.start_async_streams(service_name, process)

    def _check_process_exits(self) -> None:
        """
        Check for newly exited processes and report summaries.
        """
        if not self.console:
            return

        timestamp = time.strftime("%H:%M:%S")

        for service_name, process in list(self.processes.items()):
            return_code = getattr(process, "returncode", None)
            if return_code is None and hasattr(process, "poll") and callable(process.poll):
                return_code = process.poll()

            if return_code is not None:
                if self._exit_reported.get(service_name):
                    continue

                self.console.print(
                    f"\n[dim]{timestamp}[/dim] [red]⚠️  {service_name} exited with code {return_code}[/red]",
                )
                buffer = self._logs.get_buffer(service_name)
                if buffer:
                    n = min(len(buffer), 50)
                    self.console.print(
                        f"[dim]{timestamp}[/dim] [yellow]📝 Last {n} log lines from {service_name}:[/yellow]",
                    )
                    prefix = f"[dim]{timestamp}[/dim] " if self.config.show_timestamps else ""
                    for line in list(buffer)[-n:]:
                        self.console.print(f"{prefix}[{service_name}] {line}")

                self._exit_reported[service_name] = True
            elif self._exit_reported.get(service_name):
                self._exit_reported[service_name] = False

    def stop(self) -> None:
        """
        Signal the monitor to stop.
        """
        self._shutdown = True


__all__ = ["ServiceMonitor"]
