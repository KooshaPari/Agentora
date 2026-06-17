"""Shared OAuth Session Manager for Pytest.

Manages OAuth authentication sessions across test runs:
- Session-scoped authentication (authenticate once per test run)
- Token caching for faster subsequent runs
- Automatic token refresh
- Shared across all MCP projects
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

from pheno.testing.mcp_qa.logging import get_logger
from pheno.testing.mcp_qa.oauth.credential_broker import (
    CapturedCredentials,
    UnifiedCredentialBroker,
)

logger = get_logger(__name__)


class SharedSessionManager:
    """Manages shared OAuth sessions for testing.

    Features:
    - Single authentication per test session
    - Token caching between test runs
    - Automatic token validation and refresh
    - Per-endpoint session management
    """

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        provider: str = "authkit",
    ):
        """Initialize session manager.

        Args:
            cache_dir: Directory for token cache (default: ~/.mcp_test_cache)
            provider: OAuth provider name
        """
        self.cache_dir = cache_dir or Path.home() / ".mcp_test_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.provider = provider

        # Active sessions (in-memory for current run)
        self._sessions: Dict[str, Tuple[object, CapturedCredentials]] = {}
        self._brokers: Dict[str, UnifiedCredentialBroker] = {}

    def _get_cache_file(self, endpoint: str) -> Path:
        """
        Get cache file path for endpoint.
        """
        # Sanitize endpoint for filename
        safe_endpoint = endpoint.replace("://", "_").replace("/", "_").replace(":", "_")
        return self.cache_dir / f"{safe_endpoint}_session.json"

    def _load_cached_token(self, endpoint: str) -> Optional[Dict]:
        """
        Load cached token if valid.
        """
        cache_file = self._get_cache_file(endpoint)

        if not cache_file.exists():
            logger.debug("No cached token found", endpoint=endpoint, emoji="📭")
            return None

        try:
            with open(cache_file, "r") as f:
                cached = json.load(f)

            # Check if token is expired
            if "expires_at" in cached:
                expires_at = datetime.fromisoformat(cached["expires_at"])
                if datetime.now() >= expires_at:
                    logger.warning("Cached token expired", endpoint=endpoint, emoji="⏰")
                    return None

            logger.info("Using cached token", endpoint=endpoint, emoji="♻️")
            return cached

        except Exception as e:
            logger.error(f"Failed to load cached token: {e}", endpoint=endpoint, emoji="❌")
            return None

    def _save_token_cache(self, endpoint: str, credentials: CapturedCredentials):
        """
        Save token to cache.
        """
        cache_file = self._get_cache_file(endpoint)

        try:
            cache_data = {
                "access_token": credentials.access_token,
                "refresh_token": getattr(credentials, "refresh_token", None),
                "expires_at": (
                    credentials.expires_at.isoformat() if credentials.expires_at else None
                ),
                "email": credentials.email,
                "cached_at": datetime.now().isoformat(),
            }

            with open(cache_file, "w") as f:
                json.dump(cache_data, f, indent=2)

            logger.info("Token cached", endpoint=endpoint, emoji="💾")

        except Exception as e:
            logger.error(f"Failed to cache token: {e}", endpoint=endpoint, emoji="❌")

    async def get_session(
        self,
        mcp_endpoint: str,
        force_refresh: bool = False,
    ) -> Tuple[object, CapturedCredentials]:
        """Get authenticated MCP session.

        Args:
            mcp_endpoint: MCP server endpoint URL
            force_refresh: Force new authentication even if cached

        Returns:
            Tuple of (client, credentials)
        """
        # Check if we already have an active session
        if mcp_endpoint in self._sessions and not force_refresh:
            logger.debug("Reusing active session", endpoint=mcp_endpoint, emoji="♻️")
            return self._sessions[mcp_endpoint]

        # Try to use cached token
        if not force_refresh:
            cached = self._load_cached_token(mcp_endpoint)
            if cached and cached.get("access_token"):
                # TODO: Create client from cached token
                # For now, fall through to full OAuth
                pass

        # Create new broker if needed
        if mcp_endpoint not in self._brokers:
            logger.info(
                "Creating OAuth broker", endpoint=mcp_endpoint, provider=self.provider, emoji="🔧"
            )
            self._brokers[mcp_endpoint] = UnifiedCredentialBroker(
                mcp_endpoint=mcp_endpoint,
                provider=self.provider,
            )

        broker = self._brokers[mcp_endpoint]

        # Authenticate
        logger.info("Authenticating", endpoint=mcp_endpoint, emoji="🔐")
        client, credentials = await broker.get_authenticated_client()

        # Cache the session
        self._sessions[mcp_endpoint] = (client, credentials)

        # Save token to disk cache
        self._save_token_cache(mcp_endpoint, credentials)

        logger.info(
            "Session established", endpoint=mcp_endpoint, user=credentials.email, emoji="✅"
        )

        return client, credentials

    async def close_all(self):
        """
        Close all active sessions.
        """
        logger.info(f"Closing {len(self._brokers)} session(s)", emoji="🚪")

        for endpoint, broker in self._brokers.items():
            try:
                await broker.close()
                logger.debug("Closed session", endpoint=endpoint, emoji="✅")
            except Exception as e:
                logger.error(f"Error closing session: {e}", endpoint=endpoint, emoji="❌")

        self._sessions.clear()
        self._brokers.clear()

    def clear_cache(self, endpoint: Optional[str] = None):
        """Clear cached tokens.

        Args:
            endpoint: Specific endpoint to clear, or None for all
        """
        if endpoint:
            cache_file = self._get_cache_file(endpoint)
            if cache_file.exists():
                cache_file.unlink()
                logger.info("Cleared cache", endpoint=endpoint, emoji="🗑️")
        else:
            # Clear all cache files
            for cache_file in self.cache_dir.glob("*_session.json"):
                cache_file.unlink()
            logger.info("Cleared all cache files", emoji="🗑️")


# Global session manager instance
_global_session_manager: Optional[SharedSessionManager] = None


def get_session_manager(
    cache_dir: Optional[Path] = None,
    provider: str = "authkit",
) -> SharedSessionManager:
    """Get global session manager instance.

    Args:
        cache_dir: Directory for token cache
        provider: OAuth provider name

    Returns:
        SharedSessionManager instance
    """
    global _global_session_manager

    if _global_session_manager is None:
        _global_session_manager = SharedSessionManager(
            cache_dir=cache_dir,
            provider=provider,
        )

    return _global_session_manager


async def close_global_session_manager():
    """
    Close global session manager.
    """
    global _global_session_manager

    if _global_session_manager:
        await _global_session_manager.close_all()
        _global_session_manager = None


# Pytest fixture for shared session
def pytest_configure(config):
    """
    Register pytest hooks.
    """
    config.addinivalue_line("markers", "shared_session: use shared OAuth session across tests")


def pytest_sessionfinish(session, exitstatus):
    """
    Clean up shared sessions at end of test session.
    """
    import asyncio

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Schedule cleanup
            asyncio.ensure_future(close_global_session_manager())
        else:
            # Run cleanup
            loop.run_until_complete(close_global_session_manager())
    except Exception as e:
        logger.error(f"Error closing sessions: {e}", emoji="❌")
