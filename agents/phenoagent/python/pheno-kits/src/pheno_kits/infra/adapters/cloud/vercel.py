"""
Vercel Adapter - Native SDK with CLI fallback

Manages Vercel deployments using native Python SDK or CLI.
"""

import asyncio
import logging
import os
import shutil
from typing import Any

from vercel import Vercel as VercelClient

from ..base import ResourceAdapter

# Try importing Vercel SDK
try:
    from vercel import Vercel as VercelClient

    HAS_VERCEL_SDK = True
except ImportError:
    HAS_VERCEL_SDK = False
    VercelClient = None


logger = logging.getLogger(__name__)


class VercelAdapter(ResourceAdapter):
    """Vercel deployment adapter with native SDK support.

    Configuration:
        deployment_id: str - Deployment ID (optional if project_name provided)
        project_name: str - Project name (optional if deployment_id provided)
        team_id: str - Team ID (optional)
        access_token: str - Vercel access token (required)
        use_sdk: bool - Prefer SDK over CLI (default: True)
        target: str - Deployment target (production, preview, development)
        auto_promote: bool - Auto-promote deployments to production

    Features:
    - Deploy projects
    - Promote/cancel deployments
    - Check deployment status
    - Get deployment URLs
    - SDK with CLI fallback
    """

    def __init__(self, name: str, config: dict[str, Any]):
        super().__init__(name, config)

        # Authentication
        self.access_token = config.get("access_token") or os.getenv("VERCEL_TOKEN")
        if not self.access_token:
            raise ValueError("Vercel adapter requires 'access_token' or VERCEL_TOKEN env var")

        self.deployment_id = config.get("deployment_id")
        self.project_name = config.get("project_name")
        self.team_id = config.get("team_id")
        self.target = config.get("target", "production")
        self.auto_promote = config.get("auto_promote", False)
        self.use_sdk = config.get("use_sdk", True)

        # Initialize SDK client if available
        self.client: VercelClient | None = None
        if HAS_VERCEL_SDK and self.use_sdk:
            try:
                self.client = VercelClient(token=self.access_token)
                logger.info(f"Using Vercel SDK for {name}")
            except Exception as e:
                logger.warning(f"Failed to initialize Vercel SDK, falling back to CLI: {e}")
                self.use_sdk = False

        # Check CLI availability
        if not self.use_sdk and not shutil.which("vercel"):
            logger.warning("Vercel CLI not found. Install: npm install -g vercel")

    async def start(self) -> bool:
        """
        Deploy or promote Vercel deployment.
        """
        logger.info(f"Starting Vercel deployment: {self.project_name or self.deployment_id}")

        try:
            if self.client:
                return await self._start_via_sdk()
            return await self._start_via_cli()

        except Exception as e:
            logger.exception(f"Failed to start Vercel deployment: {e}")
            self.state.error = str(e)
            return False

    async def stop(self) -> bool:
        """
        Cancel Vercel deployment (not commonly used).
        """
        logger.info(f"Canceling Vercel deployment: {self.deployment_id}")

        try:
            if self.client:
                return await self._stop_via_sdk()
            return await self._stop_via_cli()

        except Exception as e:
            logger.exception(f"Failed to stop Vercel deployment: {e}")
            return False

    async def is_running(self) -> bool:
        """
        Check if deployment is ready.
        """
        try:
            if self.client:
                return await self._is_running_via_sdk()
            return await self._is_running_via_cli()

        except Exception:
            return False

    async def check_health(self) -> bool:
        """
        Check deployment health.
        """
        if not await self.is_running():
            self.state.healthy = False
            return False

        # If deployment URL available, check it
        if "deployment_url" in self.state.metadata:
            from ..utils.health import check_http_health

            url = f"https://{self.state.metadata['deployment_url']}"

            healthy = await asyncio.get_event_loop().run_in_executor(
                None, check_http_health, url, 5.0,
            )
            self.state.healthy = healthy
            return healthy

        # Assume healthy if running
        self.state.healthy = True
        return True

    async def _start_via_sdk(self) -> bool:
        """
        Deploy via SDK.
        """
        loop = asyncio.get_event_loop()

        try:
            # Get or create deployment
            if self.project_name:
                # Create new deployment
                deployment = await loop.run_in_executor(
                    None,
                    self.client.deployments.create,
                    {"name": self.project_name, "target": self.target, "teamId": self.team_id},
                )
            elif self.deployment_id:
                # Promote existing deployment
                deployment = await loop.run_in_executor(
                    None, self.client.deployments.get, self.deployment_id,
                )

                if self.auto_promote:
                    await loop.run_in_executor(
                        None, self.client.deployments.promote, self.deployment_id,
                    )

            self.state.running = True
            self.state.metadata["deployment_url"] = deployment.get("url")
            self.state.metadata["deployment_id"] = deployment.get("uid")

            logger.info(f"✓ Vercel deployment ready: {deployment.get('url')}")
            return True

        except Exception as e:
            logger.exception(f"SDK deployment failed: {e}")
            return False

    async def _stop_via_sdk(self) -> bool:
        """
        Cancel deployment via SDK.
        """
        loop = asyncio.get_event_loop()

        try:
            if self.deployment_id:
                await loop.run_in_executor(None, self.client.deployments.cancel, self.deployment_id)

            self.state.running = False
            self.state.healthy = False
            return True

        except Exception as e:
            logger.exception(f"SDK cancel failed: {e}")
            return False

    async def _is_running_via_sdk(self) -> bool:
        """
        Check status via SDK.
        """
        loop = asyncio.get_event_loop()

        try:
            deployment = await loop.run_in_executor(
                None, self.client.deployments.get, self.deployment_id or self.project_name,
            )

            state = deployment.get("readyState")
            running = state in ("READY", "QUEUED", "BUILDING")
            self.state.running = running

            if running:
                self.state.metadata["deployment_url"] = deployment.get("url")

            return running

        except Exception as e:
            logger.debug(f"SDK status check failed: {e}")
            return False

    async def _start_via_cli(self) -> bool:
        """
        Deploy via CLI.
        """
        cmd = ["vercel", "deploy"]

        if self.target == "production":
            cmd.append("--prod")

        if self.team_id:
            cmd.extend(["--scope", self.team_id])

        # Set token via env
        env = os.environ.copy()
        env["VERCEL_TOKEN"] = self.access_token

        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=env,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode == 0:
            # Extract URL from output
            output = stdout.decode()
            for line in output.split("\n"):
                if "https://" in line:
                    url = line.strip().split()[-1]
                    self.state.metadata["deployment_url"] = url
                    break

            self.state.running = True
            logger.info("✓ Vercel deployed via CLI")
            return True
        logger.error(f"CLI deploy failed: {stderr.decode()}")
        return False

    async def _stop_via_cli(self) -> bool:
        """
        Cancel deployment via CLI.
        """
        if not self.deployment_id:
            logger.warning("Cannot cancel deployment without deployment_id")
            return False

        cmd = ["vercel", "remove", self.deployment_id, "--yes"]

        if self.team_id:
            cmd.extend(["--scope", self.team_id])

        env = os.environ.copy()
        env["VERCEL_TOKEN"] = self.access_token

        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=env,
        )
        await proc.communicate()

        self.state.running = False
        return proc.returncode == 0

    async def _is_running_via_cli(self) -> bool:
        """
        Check status via CLI.
        """
        cmd = ["vercel", "list"]

        if self.project_name:
            cmd.append(self.project_name)

        if self.team_id:
            cmd.extend(["--scope", self.team_id])

        env = os.environ.copy()
        env["VERCEL_TOKEN"] = self.access_token

        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=env,
        )
        stdout, _ = await proc.communicate()

        if proc.returncode == 0:
            output = stdout.decode()
            # Simple check: if project appears in list, it's running
            running = self.project_name in output if self.project_name else False
            self.state.running = running
            return running

        return False

    def get_deployment_url(self) -> str | None:
        """
        Get deployment URL.
        """
        return self.state.metadata.get("deployment_url")
