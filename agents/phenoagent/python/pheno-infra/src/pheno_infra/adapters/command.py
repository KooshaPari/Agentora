"""
Command Adapter - Generic CLI/API-based resource management

Handles resources managed via command-line tools or API calls.
"""

import asyncio
import logging
from typing import Any

from ..utils.health import check_http_health, check_tcp_health
from .base import ResourceAdapter

logger = logging.getLogger(__name__)


class CommandAdapter(ResourceAdapter):
    """Generic command-based resource adapter.

    Configuration:
        start_command: List[str] - Command to start resource (required)
        stop_command: List[str] - Command to stop resource (required)
        status_command: List[str] - Command to check status (optional)
        health_check: Dict - Health check configuration
        run_in_background: bool - Run start command in background (default: True)
    """

    def __init__(self, name: str, config: dict[str, Any]):
        super().__init__(name, config)

        # Validate required fields
        if "start_command" not in config:
            raise ValueError("Command adapter requires 'start_command'")
        if "stop_command" not in config:
            raise ValueError("Command adapter requires 'stop_command'")

        self.start_cmd = config["start_command"]
        self.stop_cmd = config["stop_command"]
        self.status_cmd = config.get("status_command")
        self.health_config = config.get("health_check", {})
        self.run_in_background = config.get("run_in_background", True)

        # Track process if running in background
        self.process: asyncio.subprocess.Process | None = None

    async def start(self) -> bool:
        """
        Start resource via command.
        """
        try:
            logger.info(f"Starting {self.name}: {' '.join(self.start_cmd)}")

            if self.run_in_background:
                # Start and don't wait
                self.process = await asyncio.create_subprocess_exec(
                    *self.start_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                )
                self.state.pid = self.process.pid
                self.state.running = True
                logger.info(f"✓ Started {self.name} (PID: {self.process.pid})")
            else:
                # Run and wait for completion
                proc = await asyncio.create_subprocess_exec(
                    *self.start_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                )
                _stdout, stderr = await proc.communicate()

                if proc.returncode == 0:
                    self.state.running = True
                    logger.info(f"✓ {self.name} command completed successfully")
                else:
                    logger.error(f"Start command failed: {stderr.decode()}")
                    self.state.error = stderr.decode()
                    return False

            # Wait for health if configured
            await self._wait_for_health()
            return True

        except Exception as e:
            logger.exception(f"Failed to start {self.name}: {e}")
            self.state.error = str(e)
            return False

    async def stop(self) -> bool:
        """
        Stop resource via command.
        """
        try:
            logger.info(f"Stopping {self.name}: {' '.join(self.stop_cmd)}")

            proc = await asyncio.create_subprocess_exec(
                *self.stop_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()

            # Kill background process if exists
            if self.process and self.process.returncode is None:
                self.process.terminate()
                try:
                    await asyncio.wait_for(self.process.wait(), timeout=5.0)
                except TimeoutError:
                    self.process.kill()

            self.state.running = False
            self.state.healthy = False
            self.state.pid = None

            return proc.returncode == 0

        except Exception as e:
            logger.exception(f"Failed to stop {self.name}: {e}")
            return False

    async def is_running(self) -> bool:
        """
        Check if resource is running.
        """
        # If we have a background process, check if it's alive
        if self.process:
            running = self.process.returncode is None
            self.state.running = running
            return running

        # If we have a status command, use it
        if self.status_cmd:
            try:
                proc = await asyncio.create_subprocess_exec(
                    *self.status_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                )
                await proc.communicate()

                running = proc.returncode == 0
                self.state.running = running
                return running
            except Exception:
                return False

        # Otherwise, rely on state
        return self.state.running

    async def check_health(self) -> bool:
        """
        Check resource health.
        """
        if not await self.is_running():
            self.state.healthy = False
            return False

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
            path = self.health_config.get("path", "/")
            if port:
                url = f"http://localhost:{port}{path}"
                healthy = await asyncio.get_event_loop().run_in_executor(
                    None, check_http_health, url, 2.0,
                )
                self.state.healthy = healthy
                return healthy

        elif health_type == "command":
            cmd = self.health_config.get("command", [])
            if cmd:
                proc = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                )
                await proc.communicate()

                healthy = proc.returncode == 0
                self.state.healthy = healthy
                return healthy

        # Assume healthy if running
        self.state.healthy = True
        return True

    async def _wait_for_health(self, timeout: float = 30.0):
        """
        Wait for resource to become healthy.
        """
        if not self.health_config:
            return

        start = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start < timeout:
            if await self.check_health():
                return

            await asyncio.sleep(1.0)

        logger.warning(f"Health check timeout for {self.name}")
