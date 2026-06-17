"""
Log handling utilities for the service monitor.
"""

from __future__ import annotations

import asyncio
import threading
import time
from collections import deque
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from .config import MonitorConfig

try:  # pragma: no cover - optional dependency
    from rich.console import Console
except ImportError:  # pragma: no cover - fallback when Rich is unavailable
    Console = None  # type: ignore


class LogStore:
    """
    Manage rolling log buffers and stream readers for monitored services.
    """

    def __init__(
        self,
        config: MonitorConfig,
        console: Console | None,
        stop_checker: Callable[[], bool],
    ):
        self._config = config
        self._console = console
        self._stop_checker = stop_checker
        self._buffers: dict[str, deque[str]] = {}
        self._async_tasks: dict[str, asyncio.Task] = {}
        self._threads: list[threading.Thread] = []

    def register_service(self, service_name: str) -> None:
        """
        Ensure a buffer exists for the provided service.
        """
        self._buffers.setdefault(service_name, deque(maxlen=200))

    def clear_service(self, service_name: str) -> None:
        """
        Remove buffer state for a detached service.
        """
        self._buffers.pop(service_name, None)

    def emit(self, service_name: str, line: Any) -> None:
        """
        Render a log line and append it to the rolling buffer.
        """
        text = line.decode("utf-8", errors="replace") if isinstance(line, bytes) else str(line)
        text = text.rstrip("\n")
        if not text:
            return

        buffer = self._buffers.setdefault(service_name, deque(maxlen=200))
        buffer.append(text)

        timestamp = time.strftime("%H:%M:%S") if self._config.show_timestamps else ""
        if not self._console:
            prefix = f"{timestamp} [{service_name}] " if timestamp else f"[{service_name}] "
            print(f"{prefix}{text}")
            return

        prefix = f"[dim]{timestamp}[/dim] " if timestamp else ""
        if not self._config.colorize_logs:
            self._console.print(f"{prefix}[{service_name}] {text}")
            return

        lowered = text.lower()
        if "error" in lowered:
            self._console.print(f"{prefix}[red][{service_name}][/red] {text}")
        elif "warn" in lowered:
            self._console.print(f"{prefix}[yellow][{service_name}][/yellow] {text}")
        elif "info" in lowered:
            self._console.print(f"{prefix}[blue][{service_name}][/blue] {text}")
        else:
            self._console.print(f"{prefix}[cyan][{service_name}][/cyan] {text}")

    def start_subprocess_streams(self, service_name: str, process) -> None:
        """
        Spawn background readers for a subprocess' stdout/stderr.
        """
        stdout = getattr(process, "stdout", None)
        if stdout:
            self._spawn_thread(service_name, process, "stdout")

        stderr = getattr(process, "stderr", None)
        if stderr:
            self._spawn_thread(service_name, process, "stderr")

    def _spawn_thread(self, service_name: str, process, stream_name: str) -> None:
        stream = getattr(process, stream_name)
        if stream is None:
            return

        def reader():
            while not self._stop_checker():
                try:
                    line = stream.readline()
                    if not line:
                        poll = getattr(process, "poll", None)
                        exited = poll() is not None if callable(poll) else True
                        if exited:
                            break
                        time.sleep(0.01)
                        continue
                    self.emit(service_name, line)
                except Exception:
                    time.sleep(0.1)

        thread = threading.Thread(target=reader, daemon=True)
        thread.start()
        self._threads.append(thread)

    def start_async_streams(self, service_name: str, process) -> None:
        """
        Attach asyncio readers for stdout/stderr streams.
        """
        if getattr(process, "stdout", None):
            task = asyncio.create_task(
                self._read_async_stream(service_name, process.stdout, process),
            )
            self._async_tasks[f"{service_name}:stdout"] = task
        if getattr(process, "stderr", None):
            task = asyncio.create_task(
                self._read_async_stream(service_name, process.stderr, process),
            )
            self._async_tasks[f"{service_name}:stderr"] = task

    async def _read_async_stream(self, service_name: str, reader, process) -> None:
        """
        Coroutine to consume an asyncio stream until shutdown.
        """
        while not self._stop_checker():
            try:
                line = await reader.readline()
                if not line:
                    if getattr(process, "returncode", None) is not None:
                        break
                    await asyncio.sleep(0.05)
                    continue
                self.emit(service_name, line)
            except asyncio.CancelledError:  # pragma: no cover - cooperative shutdown
                break
            except Exception:
                await asyncio.sleep(0.1)

    def cancel_async_tasks(self) -> None:
        """
        Cancel any active asyncio log reader tasks.
        """
        for task in self._async_tasks.values():
            task.cancel()

    async def wait_async_shutdown(self) -> None:
        """
        Await cancellation of all async tasks.
        """
        for key, task in list(self._async_tasks.items()):
            try:
                await task
            except asyncio.CancelledError:
                pass
            finally:
                self._async_tasks.pop(key, None)

    def get_buffer(self, service_name: str) -> deque[str] | None:
        """
        Return the rolling buffer for a service, if present.
        """
        return self._buffers.get(service_name)


__all__ = ["LogStore"]
