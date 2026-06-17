"""
Tunnel governance manager.

Main entry point for tunnel lifecycle management.
"""

import logging
import time
from pathlib import Path
from typing import Any

from .models import (
    TunnelCredentialScope,
    TunnelCredentials,
    TunnelGovernanceConfig,
    TunnelInfo,
    TunnelLifecyclePolicy,
)
from .persistence import TunnelPersistence

logger = logging.getLogger(__name__)


class TunnelGovernanceManager:
    """
    Enhanced tunnel governance with lifecycle management.

    Features:
    - Project-specific tunnel credentials
    - Tunnel lifecycle management (reuse vs recreate)
    - Shared credentials per project
    - Tunnel health monitoring
    - Stale tunnel cleanup
    """

    def __init__(
        self,
        config: TunnelGovernanceConfig | None = None,
        config_dir: Path | None = None,
    ):
        """Initialize tunnel governance manager.

        Args:
            config: Tunnel governance configuration
            config_dir: Configuration directory
        """
        self.config = config or TunnelGovernanceConfig()
        self.config_dir = config_dir or Path.home() / ".kinfra" / "tunnels"
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self._persistence = TunnelPersistence(self.config_dir)
        self._tunnels: dict[str, TunnelInfo] = {}
        self._credentials: dict[str, TunnelCredentials] = {}
        self._project_tunnels: dict[str, set[str]] = {}
        self._service_tunnels: dict[str, set[str]] = {}
        self._tunnel_stats = {
            "created": 0,
            "reused": 0,
            "recreated": 0,
            "cleaned_up": 0,
            "errors": 0,
        }

        self._load_tunnels()
        self._load_credentials()

        logger.info(
            f"TunnelGovernanceManager initialized (policy: {self.config.lifecycle_policy.value})",
        )

    def create_tunnel(
        self,
        project: str,
        service: str,
        port: int,
        provider: str = "cloudflare",
        hostname: str | None = None,
        reuse_existing: bool = True,
    ) -> TunnelInfo:
        """Create or reuse a tunnel for a service.

        Args:
            project: Project name
            service: Service name
            port: Local port to tunnel
            provider: Tunnel provider
            hostname: Optional hostname for the tunnel
            reuse_existing: Whether to reuse existing tunnels

        Returns:
            Tunnel information
        """
        tunnel_key = f"{project}:{service}:{port}"

        if reuse_existing and self.config.enable_tunnel_reuse:
            existing_tunnel = self._find_reusable_tunnel(
                project, service, port, provider
            )
            if existing_tunnel:
                logger.info(f"Reusing existing tunnel for {tunnel_key}")
                existing_tunnel.last_seen = time.time()
                self._tunnel_stats["reused"] += 1
                return existing_tunnel

        tunnel_id = f"{project}-{service}-{port}-{int(time.time())}"

        tunnel_info = TunnelInfo(
            tunnel_id=tunnel_id,
            project=project,
            service=service,
            port=port,
            provider=provider,
            hostname=hostname or f"{tunnel_id}.tunnel.local",
            status="creating",
            credentials_scope=self.config.credential_scope,
        )

        credentials = self._get_or_create_credentials(project, service, provider)
        if credentials:
            tunnel_info.metadata["credentials_id"] = credentials.credentials.get("id")

        self._tunnels[tunnel_id] = tunnel_info

        if project not in self._project_tunnels:
            self._project_tunnels[project] = set()
        self._project_tunnels[project].add(tunnel_id)

        if service not in self._service_tunnels:
            self._service_tunnels[service] = set()
        self._service_tunnels[service].add(tunnel_id)

        tunnel_info.status = "active"
        tunnel_info.last_seen = time.time()

        self._save_tunnels()

        self._tunnel_stats["created"] += 1
        logger.info(f"Created tunnel {tunnel_id} for {tunnel_key}")

        return tunnel_info

    def get_tunnel(self, tunnel_id: str) -> TunnelInfo | None:
        """Get tunnel information by ID.

        Args:
            tunnel_id: Tunnel ID

        Returns:
            Tunnel information or None
        """
        return self._tunnels.get(tunnel_id)

    def get_project_tunnels(self, project: str) -> list[TunnelInfo]:
        """Get all tunnels for a project.

        Args:
            project: Project name

        Returns:
            List of tunnel information
        """
        project_tunnel_ids = self._project_tunnels.get(project, set())
        return [
            self._tunnels[tid] for tid in project_tunnel_ids if tid in self._tunnels
        ]

    def get_service_tunnels(self, service: str) -> list[TunnelInfo]:
        """Get all tunnels for a service.

        Args:
            service: Service name

        Returns:
            List of tunnel information
        """
        service_tunnel_ids = self._service_tunnels.get(service, set())
        return [
            self._tunnels[tid] for tid in service_tunnel_ids if tid in self._tunnels
        ]

    def update_tunnel_status(
        self,
        tunnel_id: str,
        status: str,
        hostname: str | None = None,
    ) -> bool:
        """Update tunnel status.

        Args:
            tunnel_id: Tunnel ID
            status: New status
            hostname: Optional new hostname

        Returns:
            True if tunnel was updated
        """
        tunnel = self._tunnels.get(tunnel_id)
        if not tunnel:
            return False

        tunnel.status = status
        tunnel.last_seen = time.time()

        if hostname:
            tunnel.hostname = hostname

        self._save_tunnels()

        logger.debug(f"Updated tunnel {tunnel_id} status to {status}")
        return True

    def stop_tunnel(self, tunnel_id: str) -> bool:
        """Stop a tunnel.

        Args:
            tunnel_id: Tunnel ID

        Returns:
            True if tunnel was stopped
        """
        tunnel = self._tunnels.get(tunnel_id)
        if not tunnel:
            return False

        tunnel.status = "stopped"
        tunnel.last_seen = time.time()

        self._save_tunnels()

        logger.info(f"Stopped tunnel {tunnel_id}")
        return True

    def cleanup_tunnel(self, tunnel_id: str) -> bool:
        """Clean up a tunnel completely.

        Args:
            tunnel_id: Tunnel ID

        Returns:
            True if tunnel was cleaned up
        """
        tunnel = self._tunnels.get(tunnel_id)
        if not tunnel:
            return False

        if tunnel.project and tunnel.project in self._project_tunnels:
            self._project_tunnels[tunnel.project].discard(tunnel_id)
            if not self._project_tunnels[tunnel.project]:
                del self._project_tunnels[tunnel.project]

        if tunnel.service and tunnel.service in self._service_tunnels:
            self._service_tunnels[tunnel.service].discard(tunnel_id)
            if not self._service_tunnels[tunnel.service]:
                del self._service_tunnels[tunnel.service]

        del self._tunnels[tunnel_id]

        self._save_tunnels()

        self._tunnel_stats["cleaned_up"] += 1
        logger.info(f"Cleaned up tunnel {tunnel_id}")
        return True

    def cleanup_stale_tunnels(self, max_age: float | None = None) -> int:
        """Clean up stale tunnels.

        Args:
            max_age: Maximum age for tunnels (uses config default if None)

        Returns:
            Number of tunnels cleaned up
        """
        max_age = max_age or self.config.max_tunnel_age
        current_time = time.time()

        stale_tunnel_ids = []
        for tunnel_id, tunnel in self._tunnels.items():
            if current_time - tunnel.last_seen > max_age:
                stale_tunnel_ids.append(tunnel_id)

        cleaned_up = 0
        for tunnel_id in stale_tunnel_ids:
            if self.cleanup_tunnel(tunnel_id):
                cleaned_up += 1

        if cleaned_up > 0:
            logger.info(f"Cleaned up {cleaned_up} stale tunnels")

        return cleaned_up

    def cleanup_project_tunnels(self, project: str) -> int:
        """Clean up all tunnels for a project.

        Args:
            project: Project name

        Returns:
            Number of tunnels cleaned up
        """
        project_tunnel_ids = self._project_tunnels.get(project, set()).copy()

        cleaned_up = 0
        for tunnel_id in project_tunnel_ids:
            if self.cleanup_tunnel(tunnel_id):
                cleaned_up += 1

        if cleaned_up > 0:
            logger.info(f"Cleaned up {cleaned_up} tunnels for project '{project}'")

        return cleaned_up

    def set_credentials(
        self,
        project: str,
        service: str,
        provider: str,
        credentials: dict[str, Any],
    ) -> str:
        """Set credentials for a project/service.

        Args:
            project: Project name
            service: Service name
            provider: Tunnel provider
            credentials: Provider-specific credentials

        Returns:
            Credential ID
        """
        credential_id = f"{project}:{service}:{provider}"

        credential_info = TunnelCredentials(
            scope=TunnelCredentialScope.SERVICE,
            project=project,
            service=service,
            provider=provider,
            credentials=credentials,
        )

        self._credentials[credential_id] = credential_info

        self._save_credentials()

        logger.info(f"Set credentials for {credential_id}")
        return credential_id

    def get_credentials(
        self,
        project: str,
        service: str,
        provider: str,
    ) -> TunnelCredentials | None:
        """Get credentials for a project/service.

        Args:
            project: Project name
            service: Service name
            provider: Tunnel provider

        Returns:
            Credentials or None
        """
        service_credential_id = f"{project}:{service}:{provider}"
        if service_credential_id in self._credentials:
            return self._credentials[service_credential_id]

        project_credential_id = f"{project}:*:{provider}"
        if project_credential_id in self._credentials:
            return self._credentials[project_credential_id]

        global_credential_id = f"*:*:{provider}"
        if global_credential_id in self._credentials:
            return self._credentials[global_credential_id]

        return None

    def get_tunnel_stats(self) -> dict[str, Any]:
        """Get tunnel statistics.

        Returns:
            Tunnel statistics
        """
        stats = self._tunnel_stats.copy()
        stats.update(
            {
                "total_tunnels": len(self._tunnels),
                "active_tunnels": len(
                    [t for t in self._tunnels.values() if t.status == "active"]
                ),
                "projects": len(self._project_tunnels),
                "services": len(self._service_tunnels),
                "credentials": len(self._credentials),
            },
        )
        return stats

    def _find_reusable_tunnel(
        self,
        project: str,
        service: str,
        port: int,
        provider: str,
    ) -> TunnelInfo | None:
        """Find a reusable tunnel for the given parameters."""
        for tunnel in self._tunnels.values():
            if (
                tunnel.project == project
                and tunnel.service == service
                and tunnel.port == port
                and tunnel.provider == provider
                and tunnel.status == "active"
                and time.time() - tunnel.last_seen < self.config.tunnel_reuse_threshold
            ):
                return tunnel
        return None

    def _get_or_create_credentials(
        self,
        project: str,
        service: str,
        provider: str,
    ) -> TunnelCredentials | None:
        """Get or create credentials for the given parameters."""
        credentials = self.get_credentials(project, service, provider)
        if credentials:
            return credentials

        if provider == "cloudflare":
            default_credentials = {
                "provider": provider,
                "created_at": time.time(),
            }

            credential_id = f"{project}:{service}:{provider}"
            credentials = TunnelCredentials(
                scope=TunnelCredentialScope.SERVICE,
                project=project,
                service=service,
                provider=provider,
                credentials=default_credentials,
            )

            self._credentials[credential_id] = credentials
            self._save_credentials()

            return credentials

        return None

    def _load_tunnels(self) -> None:
        """Load tunnels from persistence."""
        loaded = self._persistence.load_tunnels()
        self._tunnels = loaded

        for tunnel in self._tunnels.values():
            if tunnel.project:
                if tunnel.project not in self._project_tunnels:
                    self._project_tunnels[tunnel.project] = set()
                self._project_tunnels[tunnel.project].add(tunnel.tunnel_id)

            if tunnel.service:
                if tunnel.service not in self._service_tunnels:
                    self._service_tunnels[tunnel.service] = set()
                self._service_tunnels[tunnel.service].add(tunnel.tunnel_id)

    def _load_credentials(self) -> None:
        """Load credentials from persistence."""
        self._credentials = self._persistence.load_credentials()

    def _save_tunnels(self) -> None:
        """Save tunnels to persistence."""
        self._persistence.save_tunnels(self._tunnels)

    def _save_credentials(self) -> None:
        """Save credentials to persistence."""
        self._persistence.save_credentials(self._credentials)
