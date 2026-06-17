"""
Neon Adapter - Native SDK with CLI fallback

Manages Neon serverless Postgres using native Python SDK or CLI.
"""

import asyncio
import logging
import os
import shutil
from typing import Any

from pheno.infra.utils.health import check_tcp_health
from pheno.infra.utils.httpx_otel import apply_httpx_otel_event_hooks

from ..base import ResourceAdapter

# Try importing Neon API SDK
try:
    import httpx

    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False
    httpx = None

logger = logging.getLogger(__name__)


class NeonAdapter(ResourceAdapter):
    """Neon serverless Postgres adapter.

    Configuration:
        project_id: str - Neon project ID (required)
        api_key: str - Neon API key (required)
        use_sdk: bool - Prefer SDK over CLI (default: True)
        branch_name: str - Branch name (default: main)
        region: str - AWS region (optional)
        compute_units: float - Compute units (0.25 to 7, optional)

    Features:
    - Start/stop compute endpoints
    - Manage branches
    - Get connection strings
    - Check project status
    - SDK with CLI fallback
    """

    def __init__(self, name: str, config: dict[str, Any]):
        super().__init__(name, config)

        # Required fields
        if "project_id" not in config:
            raise ValueError("Neon adapter requires 'project_id'")

        self.project_id = config["project_id"]
        self.api_key = config.get("api_key") or os.getenv("NEON_API_KEY")

        if not self.api_key:
            raise ValueError("Neon adapter requires 'api_key' or NEON_API_KEY env var")

        self.branch_name = config.get("branch_name", "main")
        self.region = config.get("region")
        self.compute_units = config.get("compute_units")
        self.use_sdk = config.get("use_sdk", True) and HAS_HTTPX

        # API base URL
        self.api_base = "https://console.neon.tech/api/v2"

        # Check CLI availability
        if not self.use_sdk and not shutil.which("neonctl"):
            logger.warning("Neon CLI not found. Install: npm install -g neonctl")

        logger.info(f"Using Neon {'SDK' if self.use_sdk else 'CLI'} for {name}")

    async def start(self) -> bool:
        """
        Start Neon compute endpoint.
        """
        logger.info(f"Starting Neon project: {self.project_id}")

        try:
            if self.use_sdk:
                return await self._start_via_sdk()
            return await self._start_via_cli()

        except Exception as e:
            logger.exception(f"Failed to start Neon project: {e}")
            self.state.error = str(e)
            return False

    async def stop(self) -> bool:
        """
        Stop Neon compute endpoint (suspend).
        """
        logger.info(f"Suspending Neon project: {self.project_id}")

        try:
            if self.use_sdk:
                return await self._stop_via_sdk()
            return await self._stop_via_cli()

        except Exception as e:
            logger.exception(f"Failed to suspend Neon project: {e}")
            return False

    async def is_running(self) -> bool:
        """
        Check if Neon endpoint is active.
        """
        try:
            if self.use_sdk:
                return await self._is_running_via_sdk()
            return await self._is_running_via_cli()

        except Exception:
            return False

    async def check_health(self) -> bool:
        """
        Check Neon endpoint health.
        """
        if not await self.is_running():
            self.state.healthy = False
            return False

        # Check PostgreSQL connection if we have connection string
        if "connection_string" in self.state.metadata:
            # Extract host and port from connection string
            # Format: postgresql://user:pass@host:port/db
            try:
                import urllib.parse

                parsed = urllib.parse.urlparse(self.state.metadata["connection_string"])
                host = parsed.hostname
                port = parsed.port or 5432

                healthy = await asyncio.get_event_loop().run_in_executor(
                    None, check_tcp_health, host, port, 5.0,
                )
                self.state.healthy = healthy
                return healthy

            except Exception as e:
                logger.debug(f"Health check failed: {e}")

        # Assume healthy if running
        self.state.healthy = True
        return True

    async def _start_via_sdk(self) -> bool:
        """
        Start via Neon API.
        """
        async with httpx.AsyncClient(**apply_httpx_otel_event_hooks({})) as client:
            headers = {"Authorization": f"Bearer {self.api_key}"}

            # Get project endpoints
            response = await client.get(
                f"{self.api_base}/projects/{self.project_id}/endpoints", headers=headers,
            )

            if response.status_code != 200:
                logger.error(f"Failed to get endpoints: {response.text}")
                return False

            endpoints = response.json().get("endpoints", [])

            if not endpoints:
                logger.error("No endpoints found for project")
                return False

            # Start first endpoint (or find branch-specific endpoint)
            endpoint_id = None
            for ep in endpoints:
                if ep.get("branch_name") == self.branch_name:
                    endpoint_id = ep["id"]
                    break

            if not endpoint_id and endpoints:
                endpoint_id = endpoints[0]["id"]

            if not endpoint_id:
                return False

            # Start endpoint
            response = await client.post(
                f"{self.api_base}/projects/{self.project_id}/endpoints/{endpoint_id}/start",
                headers=headers,
            )

            if response.status_code in (200, 201):
                endpoint_data = response.json().get("endpoint", {})
                self.state.running = True
                self.state.metadata["endpoint_id"] = endpoint_id
                self.state.metadata["host"] = endpoint_data.get("host")

                # Get connection string
                conn_str = await self._get_connection_string()
                if conn_str:
                    self.state.metadata["connection_string"] = conn_str

                logger.info(f"✓ Neon endpoint {endpoint_id} started")
                return True
            logger.error(f"Failed to start endpoint: {response.text}")
            return False

    async def _stop_via_sdk(self) -> bool:
        """
        Stop via Neon API.
        """
        endpoint_id = self.state.metadata.get("endpoint_id")
        if not endpoint_id:
            return False

        async with httpx.AsyncClient(**apply_httpx_otel_event_hooks({})) as client:
            headers = {"Authorization": f"Bearer {self.api_key}"}

            response = await client.post(
                f"{self.api_base}/projects/{self.project_id}/endpoints/{endpoint_id}/suspend",
                headers=headers,
            )

            if response.status_code in (200, 201):
                self.state.running = False
                self.state.healthy = False
                logger.info("✓ Neon endpoint suspended")
                return True
            return False

    async def _is_running_via_sdk(self) -> bool:
        """
        Check status via API.
        """
        async with httpx.AsyncClient(**apply_httpx_otel_event_hooks({})) as client:
            headers = {"Authorization": f"Bearer {self.api_key}"}

            response = await client.get(
                f"{self.api_base}/projects/{self.project_id}", headers=headers,
            )

            if response.status_code == 200:
                project = response.json().get("project", {})
                # Neon projects don't really "stop", they suspend compute
                # Check if project is active
                running = project.get("state") == "active"
                self.state.running = running
                return running

        return False

    async def _start_via_cli(self) -> bool:
        """
        Start via CLI.
        """
        # Set API key via env
        env = os.environ.copy()
        env["NEON_API_KEY"] = self.api_key

        # Start endpoint
        proc = await asyncio.create_subprocess_exec(
            "neonctl",
            "projects",
            "start",
            self.project_id,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        _stdout, stderr = await proc.communicate()

        if proc.returncode == 0:
            self.state.running = True
            logger.info("✓ Neon project started via CLI")
            return True
        logger.error(f"CLI start failed: {stderr.decode()}")
        return False

    async def _stop_via_cli(self) -> bool:
        """
        Stop via CLI.
        """
        env = os.environ.copy()
        env["NEON_API_KEY"] = self.api_key

        proc = await asyncio.create_subprocess_exec(
            "neonctl",
            "projects",
            "suspend",
            self.project_id,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        await proc.communicate()

        self.state.running = False
        return proc.returncode == 0

    async def _is_running_via_cli(self) -> bool:
        """
        Check status via CLI.
        """
        env = os.environ.copy()
        env["NEON_API_KEY"] = self.api_key

        proc = await asyncio.create_subprocess_exec(
            "neonctl",
            "projects",
            "list",
            "--output",
            "json",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        stdout, _ = await proc.communicate()

        if proc.returncode == 0:
            import json

            projects = json.loads(stdout.decode())

            for project in projects:
                if project.get("id") == self.project_id:
                    running = project.get("state") == "active"
                    self.state.running = running
                    return running

        return False

    async def _get_connection_string(self) -> str | None:
        """
        Get PostgreSQL connection string.
        """
        if not HAS_HTTPX:
            return None

        async with httpx.AsyncClient(**apply_httpx_otel_event_hooks({})) as client:
            headers = {"Authorization": f"Bearer {self.api_key}"}

            response = await client.get(
                f"{self.api_base}/projects/{self.project_id}/connection_uri",
                headers=headers,
                params={"branch_name": self.branch_name},
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("uri")

        return None

    def get_connection_string(self) -> str | None:
        """
        Get connection string from metadata.
        """
        return self.state.metadata.get("connection_string")
