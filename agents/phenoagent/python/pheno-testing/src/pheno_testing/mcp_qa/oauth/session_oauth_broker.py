"""Session-scoped OAuth broker for pytest test suite.

This ensures ALL tests get proper OAuth session handling with TUI integration.
"""

import asyncio
import os
import time
from typing import Any, Dict, Optional

# Try to import from mcp_qa modules
try:
    from pheno.testing.mcp_qa.oauth.cache import (
        OAuthTokens,
        SessionTokenManager,
        get_session_manager,
    )
except ImportError:
    # Fallback to project-specific imports
    try:
        from framework.oauth_automation.cache import (
            OAuthTokens,
            SessionTokenManager,
            get_session_manager,
        )
    except ImportError:
        # Create minimal stubs if neither available
        class OAuthTokens:
            def __init__(self, access_token, provider, expires_at, token_type, scope):
                self.access_token = access_token
                self.provider = provider
                self.expires_at = expires_at
                self.token_type = token_type
                self.scope = scope

        from contextlib import asynccontextmanager

        class SessionTokenManager:
            """
            Fallback SessionTokenManager when imports fail.
            """

            def __init__(self):
                self._tokens = {}

            async def get_tokens(self, provider: str):
                """
                Get tokens for provider.
                """
                return self._tokens.get(provider)

            async def store_tokens(self, provider: str, tokens):
                """
                Store tokens for provider.
                """
                self._tokens[provider] = tokens

            async def get_lock(self, provider: str):
                """
                Get lock for provider.
                """
                import asyncio
                return asyncio.Lock()

            @asynccontextmanager
            async def ensure_tokens(self, provider: str, oauth_callback):
                """
                Context manager that ensures valid tokens exist.
                """
                tokens = await self.get_tokens(provider)
                if tokens:
                    yield tokens
                    return

                # Need to authenticate
                new_tokens = await oauth_callback(provider)
                if new_tokens:
                    await self.store_tokens(provider, new_tokens)
                    yield new_tokens
                else:
                    raise RuntimeError(f"OAuth failed for provider: {provider}")

        def get_session_manager():
            return SessionTokenManager()

# Import adapter from SDK
try:
    from pheno.testing.mcp_qa.core import MCPClientAdapter
except ImportError:
    # Fallback to project-specific adapter
    try:
        # AtomsMCPClientAdapter is project-specific - import from your project instead as MCPClientAdapter
    except ImportError:
        MCPClientAdapter = None

# TUI integration (optional)
try:
    from pheno.testing.mcp_qa.tui import OAuthProgressFlow, OAuthStatusWidget, oauth_with_progress
    HAS_TUI = True
except ImportError:
    try:
        from framework.oauth_progress import OAuthProgressFlow, oauth_with_progress
        from framework.tui import OAuthStatusWidget
        HAS_TUI = True
    except ImportError:
        HAS_TUI = False
        OAuthProgressFlow = None
        oauth_with_progress = None
        OAuthStatusWidget = None

# OAuth adapter (required for OAuth flows)
try:
    from pheno.testing.mcp_qa.oauth.playwright_adapter import PlaywrightOAuthAdapter
except ImportError:
    try:
        from framework.oauth_automation.playwright_adapter import PlaywrightOAuthAdapter
    except ImportError:
        PlaywrightOAuthAdapter = None


class SessionOAuthBroker:
    """Centralized OAuth broker for pytest session.

    Handles session-scoped OAuth authentication with TUI integration, token caching, and
    provides authenticated clients to all tests.
    """

    def __init__(self):
        self.session_manager = get_session_manager()
        self.authenticated_client: Optional[MCPClientAdapter] = None
        self.oauth_tokens: Optional[OAuthTokens] = None
        self._client_lock = asyncio.Lock()
        self._is_authenticated = False

    async def ensure_authenticated_client(
        self,
        provider: str = "authkit",
        force_refresh: bool = False
    ) -> MCPClientAdapter:
        """Ensure we have an authenticated MCP client for the session.

        This is called by all test fixtures to get the session OAuth client. OAuth only
        runs once per session, then cached client is reused.
        """
        async with self._client_lock:
            if self.authenticated_client and self._is_authenticated and not force_refresh:
                return self.authenticated_client

            print("\n🔐 Session OAuth Broker - Initializing Authentication")
            print(f"   Provider: {provider}")
            print(f"   Force refresh: {force_refresh}")

            # Get or create OAuth tokens
            self.oauth_tokens = await self._get_session_tokens(provider)

            # Create authenticated MCP client using tokens
            self.authenticated_client = await self._create_authenticated_client(self.oauth_tokens)

            self._is_authenticated = True

            print("   ✅ Session OAuth broker ready!")
            print("   📊 All tests will use this authenticated client")
            print("   🚀 OAuth bottleneck eliminated!\n")

            return self.authenticated_client

    async def _get_session_tokens(self, provider: str) -> OAuthTokens:
        """
        Get or create session OAuth tokens with TUI progress.
        """

        async def perform_session_oauth(provider: str) -> OAuthTokens:
            """
            Perform the actual OAuth flow with interactive credential setup.
            """

            # Use interactive credential manager to ensure credentials are available
            from pheno.testing.mcp_qa.interactive_credentials import ensure_oauth_credentials

            print(f"   🔐 Ensuring credentials for {provider}...")

            try:
                # Get credentials interactively if missing
                required_creds = ["email", "password"]
                credentials = await ensure_oauth_credentials(provider, required_creds)

                email = credentials["email"]
                password = credentials["password"]
                endpoint = os.getenv("ZEN_MCP_ENDPOINT", "https://zen.kooshapari.com/mcp")

            except Exception as e:
                raise RuntimeError(
                    f"Failed to obtain credentials for {provider}: {e}\n"
                    "Run: python tests/framework/interactive_credentials.py"
                ) from e

            print(f"   📧 Email: {email}")
            print(f"   🌐 Endpoint: {endpoint}")
            print("   🔒 Using secure OAuth automation...")

            # Set up MFA if available
            from pheno.testing.mcp_qa.interactive_credentials import get_credential_manager
            credential_manager = get_credential_manager()
            mfa_config = await credential_manager.setup_mfa_automation(provider)

            # Create OAuth adapter with MFA support
            oauth_adapter = PlaywrightOAuthAdapter(email, password)

            # Add MFA handler if available
            if mfa_config and mfa_config.get("type") == "totp":
                print("   🔐 TOTP MFA automation enabled")
                oauth_adapter.mfa_handler = mfa_config["get_code"]
            elif mfa_config and mfa_config.get("type") == "vm_simulator":
                print("   🤖 VM Simulator MFA enabled")
                # Future: Set up VM simulator MFA
            else:
                print("   ⚠️ MFA will require manual entry if prompted")

            client, auth_task = oauth_adapter.create_oauth_client(endpoint)

            try:
                oauth_url = await oauth_adapter.wait_for_oauth_url(timeout_seconds=15)

                if oauth_url:
                    print(f"   🔗 OAuth URL captured: {oauth_url[:50]}...")

                    # Use TUI progress if available
                    if HAS_TUI and OAuthProgressFlow:
                        print("   🎨 Using TUI progress display...")

                        async def oauth_handler(url):
                            return await oauth_adapter.automate_login_with_retry(url)

                        success = await oauth_with_progress(oauth_handler, oauth_url)
                        if not success:
                            raise RuntimeError("OAuth authentication failed")

                        # Complete auth task
                        try:
                            await asyncio.wait_for(auth_task, timeout=10.0)
                        except asyncio.TimeoutError:
                            pass  # Auth might complete during automation
                    else:
                        # Fallback to basic OAuth
                        print("   🔄 Running OAuth automation (no TUI)...")
                        automation_task = asyncio.create_task(
                            oauth_adapter.automate_login_with_retry(oauth_url)
                        )
                        await asyncio.gather(auth_task, automation_task, return_exceptions=True)

                else:
                    print("   ⚠️ No OAuth URL, waiting for auth task...")
                    await asyncio.wait_for(auth_task, timeout=10.0)

                # Create session tokens
                current_time = time.time()
                tokens = OAuthTokens(
                    access_token=f"session_{provider}_{int(current_time)}",
                    provider=provider,
                    expires_at=current_time + 3600,  # 1 hour
                    token_type="Bearer",
                    scope="mcp:tools mcp:resources",
                )

                print("   ✅ OAuth tokens created!")
                print(f"   ⏰ Expires: {time.ctime(tokens.expires_at)}")

                return tokens

            except Exception as e:
                print(f"   ❌ OAuth failed: {e}")
                raise RuntimeError(f"Session OAuth failed: {e}") from e
            finally:
                # Keep client for session use
                pass

        # Use session token manager
        async with self.session_manager.ensure_tokens(provider, perform_session_oauth) as tokens:
            return tokens

    async def _create_authenticated_client(self, tokens: OAuthTokens) -> MCPClientAdapter:
        """
        Create authenticated MCP client using session tokens.
        """

        print("   🔗 Creating session MCP client...")
        print(f"   🎫 Token: {tokens.access_token[:20]}... ({tokens.provider})")

        email = os.getenv("ZEN_TEST_EMAIL", "kooshapari@gmail.com")
        password = os.getenv("ZEN_TEST_PASSWORD")
        endpoint = os.getenv("ZEN_MCP_ENDPOINT", "https://zen.kooshapari.com/mcp")

        # Create client with existing authentication
        # In production, you'd configure the client directly with tokens
        oauth_adapter = PlaywrightOAuthAdapter(email, password)
        client, auth_task = oauth_adapter.create_oauth_client(endpoint)

        try:
            # Quick verification that client is authenticated
            # In real implementation, you'd inject the tokens directly
            oauth_url = await oauth_adapter.wait_for_oauth_url(timeout_seconds=2)
            if oauth_url:
                # Fast re-authentication since we have valid session
                automation_task = asyncio.create_task(
                    oauth_adapter.automate_login_with_retry(oauth_url)
                )
                await asyncio.gather(auth_task, automation_task, return_exceptions=True)
            else:
                await asyncio.wait_for(auth_task, timeout=3.0)

            # Create the client adapter
            client_adapter = MCPClientAdapter(client, verbose_on_fail=True)

            print("   ✅ Session MCP client created successfully!")

            return client_adapter

        except Exception as e:
            print(f"   ❌ MCP client creation failed: {e}")
            raise RuntimeError(f"Failed to create session MCP client: {e}") from e

    def get_oauth_tokens(self) -> Optional[OAuthTokens]:
        """
        Get current OAuth tokens (for HTTP clients).
        """
        return self.oauth_tokens

    def get_cache_status(self) -> Dict[str, Any]:
        """
        Get OAuth cache status (for TUI integration).
        """
        if not self.oauth_tokens:
            return {
                "cached": False,
                "expired": True,
                "provider": "unknown",
                "expires_at": None,
                "time_left": 0,
            }

        current_time = time.time()
        time_left = self.oauth_tokens.expires_at - current_time if self.oauth_tokens.expires_at else 0

        return {
            "cached": True,
            "expired": self.oauth_tokens.is_expired,
            "provider": self.oauth_tokens.provider,
            "expires_at": self.oauth_tokens.expires_at,
            "time_left": max(0, time_left),
            "access_token": self.oauth_tokens.access_token[:20] + "..." if self.oauth_tokens.access_token else None,
        }

    async def clear_session(self):
        """
        Clear session OAuth (for testing or refresh).
        """
        async with self._client_lock:
            if self.authenticated_client:
                try:
                    # Close the client properly
                    if hasattr(self.authenticated_client, '_client'):
                        await self.authenticated_client._client.__aexit__(None, None, None)
                except Exception:
                    pass

            self.authenticated_client = None
            self.oauth_tokens = None
            self._is_authenticated = False

            # Clear session manager cache
            self.session_manager.clear_session()

            print("🔄 Session OAuth cleared")


# Global session broker instance
_session_broker: Optional[SessionOAuthBroker] = None


def get_session_oauth_broker() -> SessionOAuthBroker:
    """
    Get the global session OAuth broker.
    """
    global _session_broker
    if _session_broker is None:
        _session_broker = SessionOAuthBroker()
    return _session_broker


async def ensure_session_oauth_client(provider: str = "authkit") -> MCPClientAdapter:
    """Convenience function to get session-authenticated MCP client.

    This is used by all test fixtures to ensure OAuth happens once per session.
    """
    broker = get_session_oauth_broker()
    return await broker.ensure_authenticated_client(provider)


def get_session_oauth_tokens() -> Optional[OAuthTokens]:
    """
    Get session OAuth tokens for HTTP clients.
    """
    broker = get_session_oauth_broker()
    return broker.get_oauth_tokens()


def clear_session_oauth():
    """
    Clear session OAuth (for CLI usage).
    """
    broker = get_session_oauth_broker()
    asyncio.run(broker.clear_session())
    print("✅ Session OAuth cleared")


# Backward compatibility alias
OAuthSessionBroker = SessionOAuthBroker


if __name__ == "__main__":
    # CLI usage
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "clear":
        clear_session_oauth()
    else:
        print("Usage: python session_oauth_broker.py clear")
