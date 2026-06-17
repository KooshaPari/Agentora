"""
Docker Adapter - Generic Docker container management

Handles any Docker container with configurable options.
"""

import asyncio
import logging
import shutil
from typing import Any

from ..utils.health import check_http_health, check_tcp_health
from .base import ResourceAdapter

logger = logging.getLogger(__name__)


class DockerAdapter(ResourceAdapter):
    """Generic Docker container adapter.

    Configuration options:
        image: str - Docker image (required)
        container_name: str - Container name (defaults to kinfra-{name})
        ports: Dict[int, int] - Port mappings {host: container}
        environment: Dict[str, str] - Environment variables
        volumes: Dict[str, str] - Volume mounts {host_path: container_path}
        command: List[str] - Container command override
        network: str - Docker network
        restart_policy: str - Restart policy (no, on-failure, always, unless-stopped)
        health_check: Dict - Health check configuration
            - type: tcp, http, docker, command
            - port: int (for tcp/http)
            - path: str (for http)
            - command: List[str] (for command)
        cleanup_on_stop: bool - Remove container on stop (default: True)
    """

    def __init__(self, name: str, config: dict[str, Any]):
        super().__init__(name, config)

        # Validate required fields
        if "image" not in config:
            raise ValueError("Docker adapter requires 'image' in config")

        self.image = config["image"]
        self.container_name = config.get("container_name", f"kinfra-{name}")
        self.ports = config.get("ports", {})
        self.environment = config.get("environment", {})
        self.volumes = config.get("volumes", {})
        self.command = config.get("command")
        self.network = config.get("network")
        self.restart_policy = config.get("restart_policy", "no")
        self.health_config = config.get("health_check", {})
        self.cleanup_on_stop = config.get("cleanup_on_stop", True)

        # Check Docker availability
        if not shutil.which("docker"):
            raise RuntimeError("Docker not found in PATH")

    async def start(self) -> bool:
        """
        Start Docker container.
        """
        try:
            # Check if already running
            if await self.is_running():
                logger.info(f"Container {self.container_name} already running")
                return True

            # Check if container exists but stopped
            result = await self._run_docker(
                ["ps", "-a", "--filter", f"name={self.container_name}", "--format", "{{.ID}}"],
            )

            if result["stdout"].strip():
                # Start existing container
                logger.info(f"Starting existing container {self.container_name}")
                result = await self._run_docker(["start", self.container_name])

                if result["returncode"] == 0:
                    self.state.container_id = self.container_name
                    self.state.running = True
                    await self._wait_for_health()
                    return True
                # Failed to start, remove and recreate
                await self._run_docker(["rm", "-f", self.container_name])

            # Create new container
            cmd = ["run", "-d", "--name", self.container_name]

            # Restart policy
            if self.restart_policy:
                cmd.extend(["--restart", self.restart_policy])

            # Port mappings
            for host_port, container_port in self.ports.items():
                cmd.extend(["-p", f"{host_port}:{container_port}"])

            # Environment variables
            for key, value in self.environment.items():
                cmd.extend(["-e", f"{key}={value}"])

            # Volume mounts
            for host_path, container_path in self.volumes.items():
                cmd.extend(["-v", f"{host_path}:{container_path}"])

            # Network
            if self.network:
                cmd.extend(["--network", self.network])

            # Image
            cmd.append(self.image)

            # Command override
            if self.command:
                cmd.extend(self.command)

            logger.info(f"Creating container: docker {' '.join(cmd[1:])}")

            result = await self._run_docker(cmd)

            if result["returncode"] == 0:
                self.state.container_id = result["stdout"].strip()
                self.state.running = True
                logger.info(f"✓ Container created: {self.container_name}")

                # Wait for health
                await self._wait_for_health()
                return True
            logger.error(f"Failed to create container: {result['stderr']}")
            self.state.error = result["stderr"]
            return False

        except Exception as e:
            logger.exception(f"Error starting Docker container {self.name}: {e}")
            self.state.error = str(e)
            return False

    async def stop(self) -> bool:
        """
        Stop Docker container.
        """
        try:
            if self.cleanup_on_stop:
                # Stop and remove
                result = await self._run_docker(["rm", "-f", self.container_name])
            else:
                # Just stop
                result = await self._run_docker(["stop", self.container_name])

            self.state.running = False
            self.state.healthy = False
            self.state.container_id = None

            return result["returncode"] == 0

        except Exception as e:
            logger.exception(f"Error stopping Docker container {self.name}: {e}")
            return False

    async def is_running(self) -> bool:
        """
        Check if container is running.
        """
        try:
            result = await self._run_docker(
                ["ps", "--filter", f"name={self.container_name}", "--format", "{{.ID}}"],
            )

            running = bool(result["stdout"].strip())
            self.state.running = running
            return running

        except Exception:
            return False

    async def check_health(self) -> bool:
        """
        Check container health.
        """
        try:
            health_type = self.health_config.get("type", "tcp")

            if health_type == "tcp":
                port = self.health_config.get("port")
                if port:
                    healthy = await asyncio.get_event_loop().run_in_executor(
                        None, check_tcp_health, "localhost", port, 2.0,
                    )
                    self.state.healthy = healthy
                    self.state.port = port
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

            elif health_type == "docker":
                # Use Docker's built-in health check
                result = await self._run_docker(
                    ["inspect", "--format", "{{.State.Health.Status}}", self.container_name],
                )
                if result["returncode"] == 0:
                    status = result["stdout"].strip()
                    healthy = status == "healthy"
                    self.state.healthy = healthy
                    return healthy

            elif health_type == "command":
                cmd = self.health_config.get("command", [])
                if cmd:
                    result = await self._run_command(cmd)
                    healthy = result["returncode"] == 0
                    self.state.healthy = healthy
                    return healthy

            return False

        except Exception as e:
            logger.debug(f"Health check failed for {self.name}: {e}")
            self.state.healthy = False
            return False

    async def _wait_for_health(self, timeout: float = 30.0):
        """
        Wait for container to become healthy.
        """
        if not self.health_config:
            return

        logger.info(f"Waiting for {self.name} to be healthy...")
        start = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start < timeout:
            if await self.check_health():
                logger.info(f"✓ {self.name} is healthy")
                return

            await asyncio.sleep(1.0)

        logger.warning(f"Health check timeout for {self.name}")

    async def _run_docker(self, args: list[str]) -> dict[str, Any]:
        """
        Run docker command.
        """
        proc = await asyncio.create_subprocess_exec(
            "docker", *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        return {
            "returncode": proc.returncode,
            "stdout": stdout.decode().strip(),
            "stderr": stderr.decode().strip(),
        }

    async def _run_command(self, cmd: list[str]) -> dict[str, Any]:
        """
        Run arbitrary command.
        """
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        return {
            "returncode": proc.returncode,
            "stdout": stdout.decode().strip(),
            "stderr": stderr.decode().strip(),
        }
