"""
Quick tunnels and event queue helpers.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import re
import subprocess
import time

from ..exceptions import TunnelError
from .models import TunnelEvent, TunnelInfo

logger = logging.getLogger(__name__)


class QuickMixin:
    def create_quick_tunnel(
        self, service_name: str, port: int, protocol: str = "http",
    ) -> TunnelInfo:
        self._log_tunnel(
            "Creating quick tunnel for '%s' on port %s", service_name, port, verbose=True,
        )
        cmd = ["cloudflared", "tunnel", "--url", f"{protocol}://127.0.0.1:{port}"]
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )
        except OSError as e:
            raise TunnelError(f"Failed to start quick tunnel: {e}")
        self._running_processes[service_name] = process
        self.registry.register_service(service_name, port, pid=process.pid)
        self._emit(
            TunnelEvent(
                tunnel_id=f"quick:{process.pid}",
                status="starting",
                message=f"Starting quick tunnel {cmd}",
            ),
        )
        url = self._wait_for_quick_url(process, timeout=self.tunnel_startup_timeout)
        if not url:
            with contextlib.suppress(Exception):
                process.terminate()
            raise TunnelError("Quick tunnel URL not found in output")
        hostname = url.replace("https://", "").split("/")[0]
        self.registry.update_service(
            service_name,
            tunnel_id=f"quick:{process.pid}",
            tunnel_hostname=hostname,
            config_path="",
            pid=process.pid,
        )
        self._emit(
            TunnelEvent(
                tunnel_id=f"quick:{process.pid}",
                status="ready",
                url=url,
                message="Quick tunnel ready",
            ),
        )
        return TunnelInfo(
            tunnel_id=f"quick:{process.pid}",
            hostname=hostname,
            config_path="",
            port=port,
            process_pid=process.pid,
            status="running",
        )

    def wait_for_ready(self, service_name: str, timeout: float = 30.0) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            status = self.get_tunnel_status(service_name)  # type: ignore[attr-defined]
            if status.get("tunnel_running") and status.get("hostname"):
                return True
            time.sleep(0.5)
        return False

    def events(self):
        return self._get_event_queue()

    # --- internals ---
    def _get_event_queue(self):
        if not hasattr(self, "_event_queue"):
            self._event_queue = asyncio.Queue(maxsize=1000)
        return self._event_queue

    def _emit(self, ev: TunnelEvent):
        try:
            self._get_event_queue().put_nowait(ev)
        except Exception:
            logger.debug("Event queue full or unavailable")

    def _wait_for_quick_url(
        self, process: subprocess.Popen, timeout: float = 30.0,
    ) -> str | None:
        pattern = re.compile(r"https://[a-z0-9\.-]+", re.IGNORECASE)
        deadline = time.time() + timeout
        if not process.stdout:
            return None
        while time.time() < deadline:
            line = process.stdout.readline()
            if not line:
                time.sleep(0.1)
                continue
            m = pattern.search(line)
            if m:
                url = m.group(0)
                self._log_tunnel("Quick tunnel URL: %s", url, verbose=True)
                return url
        return None
