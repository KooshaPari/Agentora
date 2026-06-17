"""
Process and resource inspection helpers.
"""

from __future__ import annotations

import socket
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

try:  # pragma: no cover - optional dependency
    import psutil  # type: ignore
except Exception:  # pragma: no cover - allow monitor to run without psutil
    psutil = None  # type: ignore


class ProcessInspector:
    """
    Encapsulate process status and resource probing logic.
    """

    def __init__(self):
        self._status_overrides: dict[str, Callable[[], bool]] = {}
        self._pid_overrides: dict[str, Callable[[], int | None]] = {}
        self._cloudflared_cache: dict[int, tuple[float, int | None]] = {}

    def set_overrides(
        self,
        service_name: str,
        status_getter: Callable[[], bool] | None = None,
        pid_getter: Callable[[], int | None] | None = None,
    ) -> None:
        """
        Register optional override callbacks for status/pid resolution.
        """
        if status_getter:
            self._status_overrides[service_name] = status_getter
        else:
            self._status_overrides.pop(service_name, None)

        if pid_getter:
            self._pid_overrides[service_name] = pid_getter
        else:
            self._pid_overrides.pop(service_name, None)

    def clear_overrides(self, service_name: str) -> None:
        """
        Remove overrides for the supplied service.
        """
        self._status_overrides.pop(service_name, None)
        self._pid_overrides.pop(service_name, None)

    def is_running(self, service_name: str, process) -> bool:
        """
        Determine whether a monitored process (or override) is running.
        """
        override = self._status_overrides.get(service_name)
        if override:
            try:
                return bool(override())
            except Exception:
                return False

        if process is None:
            return False

        try:
            if hasattr(process, "poll") and callable(process.poll):
                return process.poll() is None
        except Exception:
            return getattr(process, "returncode", None) is None

        if hasattr(process, "returncode"):
            return process.returncode is None

        poll = getattr(process, "poll", None)
        if callable(poll):
            try:
                return poll() is None
            except Exception:
                return False

        return getattr(process, "returncode", None) is None

    def get_pid(self, service_name: str, process) -> int | None:
        """
        Return the PID for a monitored process, honoring overrides.
        """
        override = self._pid_overrides.get(service_name)
        if override:
            try:
                return override()
            except Exception:
                return None
        if process is None:
            return None
        return getattr(process, "pid", None)

    def cloudflared_pid_for_port(self, port: int) -> int | None:
        """
        Locate a cloudflared process bound to the provided localhost port.
        """
        cache = self._cloudflared_cache.get(port)
        now = time.time()
        if cache and now - cache[0] < 5:
            return cache[1]

        pid = self._lookup_cloudflared_pid(port)
        self._cloudflared_cache[port] = (now, pid)
        return pid

    def _lookup_cloudflared_pid(self, port: int) -> int | None:
        if not psutil:
            return None
        try:
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                info = proc.info
                if info.get("name") != "cloudflared":
                    continue
                cmdline = info.get("cmdline") or []
                if isinstance(cmdline, str):
                    cmdline = cmdline.split()
                for idx, arg in enumerate(cmdline):
                    if arg == "--url" and idx + 1 < len(cmdline):
                        target = cmdline[idx + 1]
                        if f":{port}" in target:
                            return info.get("pid")
            return None
        except Exception:
            return None

    @staticmethod
    def check_port(port: int, host: str = "127.0.0.1") -> bool:
        """
        Quick TCP port availability check.
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(0.5)
                return sock.connect_ex((host, port)) == 0
        except Exception:
            return False


__all__ = ["ProcessInspector"]
