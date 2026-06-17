"""
Tunnel governance persistence layer.

Handles loading and saving tunnels and credentials to disk.
"""

import json
import logging
from pathlib import Path

from .models import TunnelCredentialScope, TunnelCredentials, TunnelInfo

logger = logging.getLogger(__name__)


class TunnelPersistence:
    """
    Persistence layer for tunnel governance.

    Handles JSON serialization/deserialization of tunnels and credentials.
    """

    def __init__(self, config_dir: Path):
        """Initialize persistence layer.

        Args:
            config_dir: Configuration directory for storing tunnel data.
        """
        self.config_dir = config_dir
        self._tunnels_file = config_dir / "tunnels.json"
        self._credentials_file = config_dir / "credentials.json"

    def load_tunnels(self) -> dict[str, TunnelInfo]:
        """Load tunnels from disk.

        Returns:
            Dictionary of tunnel_id -> TunnelInfo
        """
        if not self._tunnels_file.exists():
            return {}

        try:
            with open(self._tunnels_file) as f:
                data = json.load(f)

            tunnels = {}
            for tunnel_data in data.get("tunnels", []):
                tunnel = TunnelInfo(**tunnel_data)
                tunnels[tunnel.tunnel_id] = tunnel

            logger.info(f"Loaded {len(tunnels)} tunnels from disk")
            return tunnels

        except Exception as e:
            logger.exception(f"Failed to load tunnels: {e}")
            return {}

    def save_tunnels(self, tunnels: dict[str, TunnelInfo]) -> None:
        """Save tunnels to disk.

        Args:
            tunnels: Dictionary of tunnel_id -> TunnelInfo
        """
        try:
            data = {
                "tunnels": [
                    {
                        "tunnel_id": tunnel.tunnel_id,
                        "project": tunnel.project,
                        "service": tunnel.service,
                        "hostname": tunnel.hostname,
                        "port": tunnel.port,
                        "provider": tunnel.provider,
                        "status": tunnel.status,
                        "created_at": tunnel.created_at,
                        "last_seen": tunnel.last_seen,
                        "metadata": tunnel.metadata,
                        "credentials_scope": tunnel.credentials_scope.value,
                    }
                    for tunnel in tunnels.values()
                ],
            }

            with open(self._tunnels_file, "w") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.exception(f"Failed to save tunnels: {e}")

    def load_credentials(self) -> dict[str, TunnelCredentials]:
        """Load credentials from disk.

        Returns:
            Dictionary of credential_id -> TunnelCredentials
        """
        if not self._credentials_file.exists():
            return {}

        try:
            with open(self._credentials_file) as f:
                data = json.load(f)

            credentials = {}
            for cred_data in data.get("credentials", []):
                cred_data["scope"] = TunnelCredentialScope(cred_data["scope"])
                cred = TunnelCredentials(**cred_data)
                credential_id = f"{cred.project}:{cred.service}:{cred.provider}"
                credentials[credential_id] = cred

            logger.info(f"Loaded {len(credentials)} credentials from disk")
            return credentials

        except Exception as e:
            logger.exception(f"Failed to load credentials: {e}")
            return {}

    def save_credentials(self, credentials: dict[str, TunnelCredentials]) -> None:
        """Save credentials to disk.

        Args:
            credentials: Dictionary of credential_id -> TunnelCredentials
        """
        try:
            data = {
                "credentials": [
                    {
                        "scope": cred.scope.value,
                        "project": cred.project,
                        "service": cred.service,
                        "provider": cred.provider,
                        "credentials": cred.credentials,
                        "created_at": cred.created_at,
                        "last_used": cred.last_used,
                        "expires_at": cred.expires_at,
                        "is_active": cred.is_active,
                    }
                    for cred in credentials.values()
                ],
            }

            with open(self._credentials_file, "w") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.exception(f"Failed to save credentials: {e}")
