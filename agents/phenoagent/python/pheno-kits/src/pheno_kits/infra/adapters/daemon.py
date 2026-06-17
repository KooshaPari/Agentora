"""
System Daemon Adapter - Generic systemd/launchd management
"""

import asyncio
import logging
import shutil
from typing import Any

from ..utils.health import check_http_health, check_tcp_health
from .base import ResourceAdapter

logger = logging.getLogger(__name__)


class SystemDaemonAdapter(ResourceAdapter):
    """Generic system daemon adapter for systemd/launchd.

    Configuration:
        service_name: str - Service name (required)
        daemon_type: str - "systemd" or "launchd" (auto-detected if not specified)
        use_sudo: bool - Use sudo for commands (default: True for systemd)
        health_check: Dict - Health check configuration
    """

    def __init__(self, name: str, config: dict[str, Any]):
        super().__init__(name, config)

        self.service_name = config.get("service_name", name)
        self.use_sudo = config.get("use_sudo", True)

        # Auto-detect daemon type
        daemon_type = config.get("daemon_type")
        if not daemon_type:
            if shutil.which("systemctl"):
                daemon_type = "systemd"
            elif shutil.which("launchctl"):
                daemon_type = "launchd"
            else:
                raise RuntimeError("No supported daemon manager found")

        self.daemon_type = daemon_type
        self.health_config = config.get("health_check", {})

    async def start(self) -> bool:
        """
        Start system daemon.
        """
        try:
            if self.daemon_type == "systemd":
                cmd = ["systemctl", "start", self.service_name]
                if self.use_sudo:
                    cmd = ["sudo", *cmd]
            elif self.daemon_type == "launchd":
                cmd = ["launchctl", "start", self.service_name]
            else:
                return False

            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()

            if proc.returncode == 0:
                self.state.running = True
                logger.info(f"✓ Started {self.daemon_type} service: {self.service_name}")
                return True
            return False

        except Exception as e:
            logger.exception(f"Failed to start daemon {self.name}: {e}")
            self.state.error = str(e)
            return False

    async def stop(self) -> bool:
        """
        Stop system daemon.
        """
        try:
            if self.daemon_type == "systemd":
                cmd = ["systemctl", "stop", self.service_name]
                if self.use_sudo:
                    cmd = ["sudo", *cmd]
            elif self.daemon_type == "launchd":
                cmd = ["launchctl", "stop", self.service_name]
            else:
                return False

            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()

            self.state.running = False
            self.state.healthy = False
            return proc.returncode == 0

        except Exception as e:
            logger.exception(f"Failed to stop daemon {self.name}: {e}")
            return False

    async def is_running(self) -> bool:
        """
        Check if daemon is running.
        """
        try:
            if self.daemon_type == "systemd":
                cmd = ["systemctl", "is-active", self.service_name]
            elif self.daemon_type == "launchd":
                cmd = ["launchctl", "list", self.service_name]
            else:
                return False

            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            _stdout, _ = await proc.communicate()

            running = proc.returncode == 0
            self.state.running = running
            return running

        except Exception:
            return False

    async def check_health(self) -> bool:
        """
        Check daemon health using configured strategy.
        """
        if not await self.is_running():
            self.state.healthy = False
            return False

        # Use health check from config if specified
        health_type = self.health_config.get("type", "tcp")

        if health_type == "tcp":
            port = self.health_config.get("port")
            if port:
                healthy = await asyncio.get_event_loop().run_in_executor(
                    None, check_tcp_health, "localhost", port, 2.0,
                )
                self.state.healthy = healthy
                return healthy

        elif health_type == "http":
            port = self.health_config.get("port")
            path = self.health_config.get("path", "/health")
            if port:
                url = f"http://localhost:{port}{path}"
                healthy = await asyncio.get_event_loop().run_in_executor(
                    None, check_http_health, url, 2.0,
                )
                self.state.healthy = healthy
                return healthy

        # Default: assume healthy if running
        self.state.healthy = True
        return True
