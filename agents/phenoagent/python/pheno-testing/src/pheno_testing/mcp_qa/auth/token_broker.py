"""Multi-Consumer Token Broker.

Distributes authentication tokens across different consumers:
- Playwright contexts (via storage state)
- FastMCP clients (via OAuth tokens)
- API test frameworks (via Bearer tokens)
- CLI tools (via environment variables)
- Direct HTTP clients (via Authorization headers)

Usage:
    broker = TokenBroker(credential_manager)

    # Authenticate once
    await broker.authenticate_with_oauth(
        provider="authkit",
        email="user@example.com",
        password="password"
    )

    # Distribute to consumers
    playwright_context = await broker.create_playwright_context(browser)
    mcp_client = await broker.create_mcp_client("https://mcp.example.com")
    headers = broker.get_api_headers()
    env_vars = broker.export_to_env()
"""

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

try:
    from playwright.async_api import Browser, BrowserContext

    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False
    Browser = Any
    BrowserContext = Any

try:
    from fastmcp import Client
    from fastmcp.client.auth import OAuth

    HAS_FASTMCP = True
except ImportError:
    HAS_FASTMCP = False
    Client = Any

from .credential_manager import Credential, CredentialManager, CredentialType
from .playwright_state_manager import PlaywrightStateManager


@dataclass
class AuthTokens:
    """
    Authentication tokens for distribution.
    """

    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_at: Optional[datetime] = None
    scope: Optional[str] = None

    # Additional metadata
    provider: str = ""
    email: str = ""
    session_id: Optional[str] = None

    def is_expired(self) -> bool:
        """
        Check if token has expired.
        """
        if not self.expires_at:
            return False
        return datetime.now() >= self.expires_at

    def to_bearer_header(self) -> str:
        """
        Get Bearer token header value.
        """
        return f"{self.token_type} {self.access_token}"


class TokenBroker:
    """Broker for distributing authentication tokens across consumers.

    Features:
    - Single authentication, multiple consumers
    - Token refresh management
    - Playwright context creation
    - MCP client creation
    - API header generation
    - Environment variable export
    """

    def __init__(
        self,
        credential_manager: Optional[CredentialManager] = None,
        state_manager: Optional[PlaywrightStateManager] = None,
    ):
        """Initialize token broker.

        Args:
            credential_manager: CredentialManager instance
            state_manager: PlaywrightStateManager instance
        """
        self.credential_manager = credential_manager
        self.state_manager = state_manager or PlaywrightStateManager(
            credential_manager=credential_manager
        )

        self._tokens: Optional[AuthTokens] = None
        self._credentials: Optional[Credential] = None

    async def authenticate_with_oauth(
        self, provider: str, email: str, password: str, mcp_endpoint: Optional[str] = None, **kwargs
    ) -> AuthTokens:
        """Authenticate using OAuth flow and capture tokens.

        Args:
            provider: Provider name (e.g., "authkit", "google")
            email: User email
            password: User password
            mcp_endpoint: MCP endpoint (if using MCP OAuth)
            **kwargs: Additional provider-specific arguments

        Returns:
            Captured authentication tokens
        """
        from pheno.testing.mcp_qa.oauth.credential_broker import UnifiedCredentialBroker

        # Use credential broker to perform OAuth
        broker = UnifiedCredentialBroker(
            mcp_endpoint=mcp_endpoint or os.getenv("MCP_ENDPOINT"), provider=provider
        )

        # This will perform OAuth and capture credentials
        client, creds = await broker.get_authenticated_client()

        # Store tokens
        self._tokens = AuthTokens(
            access_token=creds.access_token,
            refresh_token=creds.refresh_token,
            expires_at=creds.expires_at,
            provider=provider,
            email=email,
            session_id=creds.session_id,
        )

        # Store credentials in credential manager if available
        if self.credential_manager:
            self.credential_manager.store_credential(
                name=f"{provider}_{email}",
                credential_type=CredentialType.OAUTH_TOKEN,
                provider=provider,
                value=creds.access_token,
                email=email,
                expires_at=creds.expires_at,
                metadata={"refresh_token": creds.refresh_token, "session_id": creds.session_id},
            )

        return self._tokens

    async def authenticate_with_password(self, provider: str, email: str, password: str):
        """Store password credentials for later use.

        Args:
            provider: Provider name
            email: User email
            password: User password
        """
        if self.credential_manager:
            self._credentials = self.credential_manager.store_credential(
                name=f"{provider}_{email}",
                credential_type=CredentialType.PASSWORD,
                provider=provider,
                value=password,
                email=email,
            )

    async def create_playwright_context(
        self, browser: Browser, profile_name: Optional[str] = None, **context_kwargs
    ) -> BrowserContext:
        """Create Playwright context with authentication.

        Args:
            browser: Playwright Browser instance
            profile_name: Optional profile name (auto-generated if not provided)
            **context_kwargs: Additional context options

        Returns:
            Authenticated BrowserContext
        """
        if not HAS_PLAYWRIGHT:
            raise RuntimeError("Playwright not installed")

        # Use profile name from tokens if available
        if not profile_name and self._tokens:
            profile_name = f"{self._tokens.provider}_{self._tokens.email}"

        if not profile_name:
            raise ValueError("Profile name required when no tokens available")

        # Check if we have saved state
        context = await self.state_manager.create_context_with_state(
            browser, profile_name, **context_kwargs
        )

        if context:
            return context

        # Need to authenticate
        # This requires implementing the actual login flow
        raise RuntimeError(
            "No saved authentication state. "
            "Authenticate first using authenticate_with_oauth() or save state manually."
        )

    async def create_mcp_client(self, mcp_url: str, client_name: str = "MCP Client") -> Client:
        """Create FastMCP client with authentication.

        Args:
            mcp_url: MCP server URL
            client_name: Client name

        Returns:
            Authenticated FastMCP Client
        """
        if not HAS_FASTMCP:
            raise RuntimeError("FastMCP not installed")

        if not self._tokens:
            raise RuntimeError("No tokens available. Authenticate first.")

        # Create client with OAuth tokens
        # TODO: Implement custom OAuth handler that uses stored tokens
        # For now, use standard OAuth flow

        oauth = OAuth(mcp_url=mcp_url, client_name=client_name)
        client = Client(mcp_url, auth=oauth)

        return client

    def get_api_headers(self) -> Dict[str, str]:
        """Get HTTP headers for API calls.

        Returns:
            Dictionary of headers
        """
        if not self._tokens:
            raise RuntimeError("No tokens available. Authenticate first.")

        return {
            "Authorization": self._tokens.to_bearer_header(),
            "Content-Type": "application/json",
        }

    def export_to_env(self, prefix: str = "AUTH") -> Dict[str, str]:
        """Export tokens as environment variables.

        Args:
            prefix: Variable name prefix

        Returns:
            Dictionary of environment variables
        """
        if not self._tokens:
            raise RuntimeError("No tokens available. Authenticate first.")

        env_vars = {
            f"{prefix}_ACCESS_TOKEN": self._tokens.access_token,
            f"{prefix}_TOKEN_TYPE": self._tokens.token_type,
        }

        if self._tokens.refresh_token:
            env_vars[f"{prefix}_REFRESH_TOKEN"] = self._tokens.refresh_token

        if self._tokens.email:
            env_vars[f"{prefix}_EMAIL"] = self._tokens.email

        if self._tokens.provider:
            env_vars[f"{prefix}_PROVIDER"] = self._tokens.provider

        return env_vars

    def set_env_vars(self, prefix: str = "AUTH"):
        """Set environment variables in current process.

        Args:
            prefix: Variable name prefix
        """
        env_vars = self.export_to_env(prefix)
        os.environ.update(env_vars)

    async def refresh_tokens(self) -> AuthTokens:
        """Refresh authentication tokens.

        Returns:
            Refreshed tokens
        """
        if not self._tokens:
            raise RuntimeError("No tokens to refresh")

        if not self._tokens.refresh_token:
            raise RuntimeError("No refresh token available")

        # TODO: Implement token refresh logic
        # This is provider-specific

        raise NotImplementedError("Token refresh not yet implemented")

    def get_tokens(self) -> Optional[AuthTokens]:
        """
        Get current tokens.
        """
        return self._tokens

    def has_valid_tokens(self) -> bool:
        """
        Check if we have valid, non-expired tokens.
        """
        if not self._tokens:
            return False
        return not self._tokens.is_expired()


# Singleton instance
_token_broker: Optional[TokenBroker] = None


def get_token_broker(
    credential_manager: Optional[CredentialManager] = None, force_new: bool = False
) -> TokenBroker:
    """Get global token broker instance.

    Args:
        credential_manager: CredentialManager instance
        force_new: Force creation of new instance

    Returns:
        TokenBroker instance
    """
    global _token_broker

    if force_new or _token_broker is None:
        _token_broker = TokenBroker(credential_manager)

    return _token_broker


__all__ = [
    "TokenBroker",
    "AuthTokens",
    "get_token_broker",
]
