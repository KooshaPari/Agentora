"""OAuth Token Caching.

Leverages FastMCP's built-in FileTokenStorage for OAuth token caching. Tokens are
automatically cached at ~/.fastmcp/oauth-mcp-client-cache/

This eliminates the need to re-authenticate on every test run.
"""

import asyncio
from pathlib import Path
from typing import Optional

from fastmcp import Client
from fastmcp.client.auth import OAuth


class CachedOAuthClient:
    """OAuth client that uses FastMCP's built-in token caching.

    Token cache location:
        ~/.fastmcp/oauth-mcp-client-cache/{server_url}_tokens.json

    On first run:
        - Performs OAuth flow (browser or Playwright automation)
        - Saves token to cache

    On subsequent runs:
        - Loads token from cache
        - Auto-refreshes if expired
        - Only re-authenticates if token invalid
    """

    def __init__(
        self,
        mcp_url: str,
        client_name: str = "Zen MCP Test Suite",
        playwright_oauth_handler: Optional[callable] = None,
    ):
        """Initialize cached OAuth client.

        Args:
            mcp_url: MCP server endpoint
            client_name: OAuth client name
            playwright_oauth_handler: Optional async function(oauth_url) -> bool
                                     for automated OAuth login
        """
        self.mcp_url = mcp_url
        self.client_name = client_name
        self.playwright_oauth_handler = playwright_oauth_handler
        self.oauth_url: Optional[str] = None

    def _get_cache_path(self) -> Path:
        """
        Get the path where OAuth tokens are cached.
        """
        from urllib.parse import urlparse

        parsed = urlparse(self.mcp_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        cache_dir = Path.home() / ".fastmcp" / "oauth-mcp-client-cache"
        # FastMCP uses sanitized filename
        safe_name = base_url.replace("://", "_").replace("/", "_").replace(":", "_")
        return cache_dir / f"{safe_name}_tokens.json"

    def is_token_cached(self) -> bool:
        """
        Check if valid OAuth token exists in cache.
        """
        cache_path = self._get_cache_path()
        return cache_path.exists()

    async def create_client(self) -> Client:
        """Create FastMCP client with OAuth authentication.

        Uses cached token if available, otherwise performs OAuth flow.

        Returns:
            Authenticated FastMCP Client instance
        """
        cache_path = self._get_cache_path()

        if cache_path.exists():
            print(f"🔐 Using cached OAuth token from: {cache_path}")
            print("   (Delete this file to force re-authentication)")
        else:
            print("🔐 No cached token found - starting OAuth flow")
            print(f"   Token will be cached at: {cache_path}")

        # Create OAuth provider with custom redirect handler if provided
        if self.playwright_oauth_handler:

            class PlaywrightOAuth(OAuth):
                async def redirect_handler(inner_self, authorization_url: str) -> None:
                    # Capture URL instead of opening browser
                    self.oauth_url = authorization_url

            oauth = PlaywrightOAuth(mcp_url=self.mcp_url, client_name=self.client_name)
        else:
            # Use default OAuth (opens browser)
            oauth = OAuth(mcp_url=self.mcp_url, client_name=self.client_name)

        # Create client with OAuth
        client = Client(self.mcp_url, auth=oauth)

        # If Playwright handler provided, coordinate authentication
        if self.playwright_oauth_handler:
            # Start auth in background
            auth_task = asyncio.create_task(client.__aenter__())

            # Wait for OAuth URL
            for _ in range(20):
                await asyncio.sleep(0.5)
                if self.oauth_url:
                    print("✅ Captured OAuth URL")
                    break

            if self.oauth_url:
                # Run Playwright automation
                automation_task = asyncio.create_task(self.playwright_oauth_handler(self.oauth_url))
                await asyncio.gather(auth_task, automation_task, return_exceptions=True)
            else:
                print("⚠️  No OAuth URL captured, waiting for completion...")
                await auth_task
        else:
            # Standard OAuth flow (opens browser)
            await client.__aenter__()

        return client

    def clear_cache(self):
        """
        Clear cached OAuth token to force re-authentication.
        """
        cache_path = self._get_cache_path()
        if cache_path.exists():
            cache_path.unlink()
            print(f"✅ Cleared OAuth token cache: {cache_path}")
        else:
            print("ℹ️  No cached token to clear")


# Helper function for convenience
async def create_cached_client(
    mcp_url: str,
    client_name: str = "Zen MCP Test Suite",
    playwright_oauth_handler: Optional[callable] = None,
) -> Client:
    """Create authenticated FastMCP client with OAuth token caching.

    Args:
        mcp_url: MCP server endpoint
        client_name: OAuth client name
        playwright_oauth_handler: Optional Playwright automation handler

    Returns:
        Authenticated Client instance

    Example:
        from tests.auth_helper import automate_oauth_login

        client = await create_cached_client(
            mcp_url="https://mcp.zen.tech/api/mcp",
            playwright_oauth_handler=automate_oauth_login
        )

        # First run: Performs OAuth + caches token
        # Second run: Uses cached token (instant!)
    """
    cached_oauth = CachedOAuthClient(mcp_url, client_name, playwright_oauth_handler)
    return await cached_oauth.create_client()
