"""
Supabase Adapter - Native SDK with CLI fallback

Manages Supabase projects using native Python SDK or CLI.
"""

import asyncio
import logging
import os
import shutil
from typing import Any

from supabase_management import Client as SupabaseManagementClient

from ..base import ResourceAdapter

# Try importing Supabase Management API SDK
try:
    from supabase_management import Client as SupabaseManagementClient

    HAS_SUPABASE_SDK = True
except ImportError:
    HAS_SUPABASE_SDK = False
    SupabaseManagementClient = None


logger = logging.getLogger(__name__)


class SupabaseAdapter(ResourceAdapter):
    """Supabase project adapter with native SDK support.

    Configuration:
        project_id: str - Supabase project ID (required)
        access_token: str - Supabase access token (required)
        use_sdk: bool - Prefer SDK over CLI (default: True)
        region: str - Project region (optional)
        database_password: str - Database password (for connection string)
        org_id: str - Organization ID (optional)

    Features:
    - Pause/restore projects
    - Check project status
    - Get connection strings
    - Manage branches
    - SDK with CLI fallback
    """

    def __init__(self, name: str, config: dict[str, Any]):
        super().__init__(name, config)

        # Required fields
        if "project_id" not in config:
            raise ValueError("Supabase adapter requires 'project_id'")
        if "access_token" not in config and "SUPABASE_ACCESS_TOKEN" not in os.environ:
            raise ValueError(
                "Supabase adapter requires 'access_token' or SUPABASE_ACCESS_TOKEN env var",
            )

        self.project_id = config["project_id"]
        self.access_token = config.get("access_token") or os.getenv("SUPABASE_ACCESS_TOKEN")
        self.use_sdk = config.get("use_sdk", True)
        self.region = config.get("region")
        self.org_id = config.get("org_id")
        self.database_password = config.get("database_password")

        # Initialize SDK client if available and preferred
        self.client: SupabaseManagementClient | None = None
        if HAS_SUPABASE_SDK and self.use_sdk:
            try:
                self.client = SupabaseManagementClient(access_token=self.access_token)
                logger.info(f"Using Supabase SDK for {name}")
            except Exception as e:
                logger.warning(f"Failed to initialize Supabase SDK, falling back to CLI: {e}")
                self.use_sdk = False

        # Check CLI availability if SDK not used
        if not self.use_sdk:
            if not shutil.which("supabase"):
                logger.warning("Supabase CLI not found. Install: npm install -g supabase")
            else:
                logger.info(f"Using Supabase CLI for {name}")

    async def start(self) -> bool:
        """
        Restore/unpause Supabase project.
        """
        logger.info(f"Restoring Supabase project: {self.project_id}")

        try:
            if self.client:
                # Use SDK
                return await self._start_via_sdk()
            # Use CLI
            return await self._start_via_cli()

        except Exception as e:
            logger.exception(f"Failed to restore Supabase project: {e}")
            self.state.error = str(e)
            return False

    async def stop(self) -> bool:
        """
        Pause Supabase project.
        """
        logger.info(f"Pausing Supabase project: {self.project_id}")

        try:
            if self.client:
                return await self._stop_via_sdk()
            return await self._stop_via_cli()

        except Exception as e:
            logger.exception(f"Failed to pause Supabase project: {e}")
            return False

    async def is_running(self) -> bool:
        """
        Check if Supabase project is running.
        """
        try:
            if self.client:
                return await self._is_running_via_sdk()
            return await self._is_running_via_cli()

        except Exception:
            return False

    async def check_health(self) -> bool:
        """
        Check Supabase project health.
        """
        # Check if project is running
        if not await self.is_running():
            self.state.healthy = False
            return False

        # Project is running, assume healthy
        # Could add more sophisticated health checks here
        self.state.healthy = True
        return True

    async def _start_via_sdk(self) -> bool:
        """
        Start project using SDK.
        """
        loop = asyncio.get_event_loop()

        # Run SDK call in executor (blocking call)
        try:
            await loop.run_in_executor(None, self.client.restore_project, self.project_id)

            self.state.running = True
            logger.info(f"✓ Supabase project {self.project_id} restored via SDK")
            return True

        except Exception as e:
            logger.exception(f"SDK restore failed: {e}")
            return False

    async def _stop_via_sdk(self) -> bool:
        """
        Stop project using SDK.
        """
        loop = asyncio.get_event_loop()

        try:
            await loop.run_in_executor(None, self.client.pause_project, self.project_id)

            self.state.running = False
            self.state.healthy = False
            logger.info(f"✓ Supabase project {self.project_id} paused via SDK")
            return True

        except Exception as e:
            logger.exception(f"SDK pause failed: {e}")
            return False

    async def _is_running_via_sdk(self) -> bool:
        """
        Check project status using SDK.
        """
        loop = asyncio.get_event_loop()

        try:
            project = await loop.run_in_executor(None, self.client.get_project, self.project_id)

            status = project.get("status")
            running = status in ("ACTIVE_HEALTHY", "ACTIVE", "COMING_UP")
            self.state.running = running

            # Store connection info in metadata
            if running and "database" in project:
                self.state.metadata["connection_string"] = project["database"].get(
                    "connection_string",
                )

            return running

        except Exception as e:
            logger.debug(f"SDK status check failed: {e}")
            return False

    async def _start_via_cli(self) -> bool:
        """
        Start project using CLI.
        """
        proc = await asyncio.create_subprocess_exec(
            "supabase",
            "projects",
            "restore",
            self.project_id,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _stdout, stderr = await proc.communicate()

        if proc.returncode == 0:
            self.state.running = True
            logger.info(f"✓ Supabase project {self.project_id} restored via CLI")
            return True
        logger.error(f"CLI restore failed: {stderr.decode()}")
        return False

    async def _stop_via_cli(self) -> bool:
        """
        Stop project using CLI.
        """
        proc = await asyncio.create_subprocess_exec(
            "supabase",
            "projects",
            "pause",
            self.project_id,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()

        if proc.returncode == 0:
            self.state.running = False
            self.state.healthy = False
            logger.info(f"✓ Supabase project {self.project_id} paused via CLI")
            return True
        return False

    async def _is_running_via_cli(self) -> bool:
        """
        Check project status using CLI.
        """
        proc = await asyncio.create_subprocess_exec(
            "supabase",
            "projects",
            "list",
            "--output",
            "json",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _stderr = await proc.communicate()

        if proc.returncode == 0:
            import json

            projects = json.loads(stdout.decode())

            for project in projects:
                if project.get("id") == self.project_id:
                    status = project.get("status", "").upper()
                    running = "ACTIVE" in status or "HEALTHY" in status
                    self.state.running = running
                    return running

        return False

    def get_connection_string(self) -> str | None:
        """
        Get PostgreSQL connection string for the project.
        """
        if "connection_string" in self.state.metadata:
            return self.state.metadata["connection_string"]

        # Construct from project ID
        if self.database_password:
            return f"postgresql://postgres:{self.database_password}@db.{self.project_id}.supabase.co:5432/postgres"

        return None
