"""Credential Caching Layer.

Provides caching and session state management for OAuth credentials.
"""

import json
from pathlib import Path
from typing import Dict, Optional

from pheno.testing.mcp_qa.logging import get_logger

from .broker_core import CapturedCredentials


class BrokerCache:
    """Cache for OAuth credentials."""

    def __init__(self, cache_file: Path):
        self.cache_file = cache_file
        self.logger = get_logger(__name__).bind(component="BrokerCache")

    def load(self) -> Optional[CapturedCredentials]:
        """Load cached credentials if valid."""
        if not self.cache_file.exists():
            return None

        try:
            with open(self.cache_file, "r") as f:
                data = json.load(f)
            credentials = CapturedCredentials.from_dict(data)
            if credentials.is_valid():
                return credentials
            else:
                self.logger.debug("Cached credentials expired or invalid")
                return None
        except Exception as e:
            self.logger.debug(f"Failed to load cached credentials: {e}")
            return None

    def save(self, credentials: CapturedCredentials) -> None:
        """Save credentials to cache."""
        self.cache_file.parent.mkdir(exist_ok=True)
        with open(self.cache_file, "w") as f:
            json.dump(credentials.to_dict(), f, indent=2)
        self.logger.debug("Credentials cached", cache_file=str(self.cache_file))

    def clear(self) -> None:
        """Clear cached credentials."""
        if self.cache_file.exists():
            self.cache_file.unlink()
            self.logger.debug("Cache cleared")


class SessionState:
    """In-memory session state for credentials (per-endpoint)."""

    def __init__(self):
        self._authenticated: Dict[str, bool] = {}
        self._credentials: Dict[str, CapturedCredentials] = {}

    def is_authenticated(self, endpoint: str) -> bool:
        """Check if endpoint is authenticated."""
        return self._authenticated.get(endpoint, False)

    def set_authenticated(self, endpoint: str, authenticated: bool) -> None:
        """Set authentication state for endpoint."""
        self._authenticated[endpoint] = authenticated

    def get_credentials(self, endpoint: str) -> Optional[CapturedCredentials]:
        """Get credentials for endpoint."""
        return self._credentials.get(endpoint)

    def set_credentials(self, endpoint: str, credentials: CapturedCredentials) -> None:
        """Set credentials for endpoint."""
        self._credentials[endpoint] = credentials

    def clear(self, endpoint: Optional[str] = None) -> None:
        """Clear session state."""
        if endpoint:
            self._authenticated.pop(endpoint, None)
            self._credentials.pop(endpoint, None)
        else:
            self._authenticated.clear()
            self._credentials.clear()
