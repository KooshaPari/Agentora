"""Widget adapters for OAuth, tunnel, and related components.

This module implements adapters for:
- MCPOAuthCacheAdapter: OAuth cache operations using CachedOAuthClient
- MCPTunnelAdapter: Tunnel configuration and management
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from fastmcp import Client

from pheno.testing.mcp_qa.oauth.cache import CachedOAuthClient

logger = logging.getLogger(__name__)


class MCPOAuthCacheAdapter:
    """Adapter for OAuth cache operations using CachedOAuthClient.

    Wraps mcp-QA OAuth cache client to implement OAuthCacheProvider protocol.

    Example:
        oauth_client = CachedOAuthClient(mcp_url="https://api.example.com/mcp")
        adapter = MCPOAuthCacheAdapter(oauth_client)

        if adapter.is_token_cached():
            client = await adapter.create_client()
        else:
            logger.info("No cached token, will perform OAuth flow")
    """

    def __init__(self, oauth_cache_client: CachedOAuthClient):
        """Initialize OAuth cache adapter.

        Args:
            oauth_cache_client: CachedOAuthClient instance to wrap
        """
        self._client = oauth_cache_client
        logger.debug(f"Initialized OAuth cache adapter for {oauth_cache_client.mcp_url}")

    def get_cache_path(self) -> Path:
        """Get the path where OAuth tokens are cached.

        Returns:
            Path to the OAuth token cache file
        """
        try:
            path = self._client._get_cache_path()
            logger.debug(f"OAuth cache path: {path}")
            return path
        except Exception as e:
            logger.error(f"Failed to get cache path: {e}")
            raise

    def is_token_cached(self) -> bool:
        """Check if valid OAuth token exists in cache.

        Returns:
            True if cached token exists, False otherwise
        """
        try:
            cached = self._client.is_token_cached()
            logger.debug(f"Token cached: {cached}")
            return cached
        except Exception as e:
            logger.warning(f"Error checking token cache: {e}")
            return False

    def clear_cache(self) -> None:
        """Clear cached OAuth token to force re-authentication.

        This will remove the cached token file, forcing a new OAuth flow on the next
        client creation.
        """
        try:
            self._client.clear_cache()
            logger.info("OAuth cache cleared successfully")
        except Exception as e:
            logger.error(f"Failed to clear OAuth cache: {e}")
            raise

    async def create_client(self) -> Client:
        """Create authenticated client using cached token.

        If no cached token exists, this will trigger the OAuth flow
        (either browser-based or Playwright automation).

        Returns:
            Authenticated FastMCP Client instance

        Raises:
            Exception: If client creation fails
        """
        try:
            logger.info("Creating OAuth client...")
            client = await self._client.create_client()
            logger.info("OAuth client created successfully")
            return client
        except Exception as e:
            logger.error(f"Failed to create OAuth client: {e}")
            raise


class MCPTunnelAdapter:
    """Adapter for tunnel configuration and management.

    Provides a simple interface for managing tunnels (ngrok, cloudflared, etc.)
    for exposing local MCP servers publicly during testing.

    Example:
        config = {
            "type": "ngrok",
            "local_url": "http://localhost:8000",
            "public_url": None  # Will be set when tunnel starts
        }
        adapter = MCPTunnelAdapter(config)

        if await adapter.start():
            print(f"Tunnel active: {adapter.get_public_url()}")
    """

    def __init__(self, tunnel_config: Dict[str, Any]):
        """Initialize tunnel adapter.

        Args:
            tunnel_config: Tunnel configuration dictionary with keys:
                - type: str (e.g., "ngrok", "cloudflared", "manual")
                - local_url: str (local endpoint to tunnel)
                - public_url: Optional[str] (public URL if already known)
                - auth_token: Optional[str] (for ngrok, etc.)
        """
        self._config = tunnel_config
        self._active = False
        self._public_url = tunnel_config.get("public_url")
        logger.debug(f"Initialized tunnel adapter: {tunnel_config.get('type', 'unknown')}")

    def get_public_url(self) -> Optional[str]:
        """Get the public URL for the tunnel.

        Returns:
            Public URL if tunnel is active, None otherwise
        """
        return self._public_url if self._active else None

    def get_local_url(self) -> str:
        """Get the local URL being tunneled.

        Returns:
            Local URL string
        """
        return self._config.get("local_url", "http://localhost:8000")

    def is_active(self) -> bool:
        """Check if tunnel is currently active.

        Returns:
            True if tunnel is active, False otherwise
        """
        return self._active

    async def start(self) -> bool:
        """Start the tunnel.

        This is a placeholder implementation. In a real scenario, this would:
        - Launch the tunnel process (ngrok, cloudflared)
        - Wait for tunnel to establish
        - Extract the public URL
        - Set _active = True

        Returns:
            True if tunnel started successfully, False otherwise
        """
        try:
            tunnel_type = self._config.get("type", "manual")
            logger.info(f"Starting {tunnel_type} tunnel...")

            if tunnel_type == "manual":
                self._active = True
                logger.info(f"Manual tunnel mode: using {self._public_url or 'local URL'}")
                return True

            logger.warning(f"Tunnel type '{tunnel_type}' not implemented - using manual mode")
            self._active = True
            return True

        except Exception as e:
            logger.error(f"Failed to start tunnel: {e}")
            return False

    async def stop(self) -> bool:
        """Stop the tunnel.

        This is a placeholder implementation. In a real scenario, this would:
        - Terminate the tunnel process
        - Clean up resources
        - Set _active = False

        Returns:
            True if tunnel stopped successfully, False otherwise
        """
        try:
            if not self._active:
                logger.debug("Tunnel already stopped")
                return True

            logger.info("Stopping tunnel...")
            self._active = False
            logger.info("Tunnel stopped")
            return True

        except Exception as e:
            logger.error(f"Failed to stop tunnel: {e}")
            return False


def create_oauth_adapter(mcp_url: str, **kwargs) -> MCPOAuthCacheAdapter:
    """Create an OAuth cache adapter for the given MCP URL.

    Args:
        mcp_url: MCP server endpoint URL
        **kwargs: Additional arguments for CachedOAuthClient

    Returns:
        MCPOAuthCacheAdapter instance

    Example:
        adapter = create_oauth_adapter("https://api.example.com/mcp")
        client = await adapter.create_client()
    """
    oauth_client = CachedOAuthClient(mcp_url, **kwargs)
    return MCPOAuthCacheAdapter(oauth_client)


def create_tunnel_adapter(
    tunnel_type: str = "manual",
    local_url: str = "http://localhost:8000",
    public_url: Optional[str] = None,
    **kwargs,
) -> MCPTunnelAdapter:
    """Create a tunnel adapter.

    Args:
        tunnel_type: Type of tunnel (manual, ngrok, cloudflared)
        local_url: Local URL to tunnel
        public_url: Public URL (for manual mode)
        **kwargs: Additional tunnel configuration

    Returns:
        MCPTunnelAdapter instance

    Example:
        adapter = create_tunnel_adapter(
            tunnel_type="ngrok",
            local_url="http://localhost:8000"
        )
        await adapter.start()
    """
    config = {"type": tunnel_type, "local_url": local_url, "public_url": public_url, **kwargs}
    return MCPTunnelAdapter(config)


__all__ = [
    "MCPOAuthCacheAdapter",
    "MCPTunnelAdapter",
    "create_oauth_adapter",
    "create_tunnel_adapter",
]
