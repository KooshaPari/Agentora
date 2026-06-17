"""Pytest plugin for automatic pre-test authentication.

This plugin ensures authentication happens BEFORE test collection, preventing redundant
OAuth flows and improving test execution speed.
"""

import asyncio
import os
from typing import Any, Dict

import pytest


def pytest_addoption(parser):
    """
    Add command-line options for authentication control.
    """
    parser.addoption(
        "--skip-auth",
        action="store_true",
        default=False,
        help="Skip automatic pre-test authentication",
    )
    parser.addoption(
        "--force-auth",
        action="store_true",
        default=False,
        help="Force authentication even if credentials are cached",
    )


@pytest.hookimpl(tryfirst=True)
def pytest_sessionstart(session):
    """Run authentication BEFORE test collection.

    This hook runs with tryfirst=True to ensure it executes before test discovery and
    collection, preventing per-test OAuth flows.
    """
    # Skip auth for --collect-only mode
    if session.config.option.collectonly:
        print("\n📋 Collection-only mode - skipping authentication")
        return

    # Skip auth if explicitly requested
    if session.config.getoption("--skip-auth", default=False):
        print("\n⏭️  Skipping pre-test authentication (--skip-auth)")
        return

    # Check if MCP_ENDPOINT is configured
    endpoint = os.getenv("MCP_ENDPOINT")
    if not endpoint:
        endpoint = session.config.getoption("--mcp-endpoint", default=None)

    if not endpoint:
        print("\n⚠️  MCP_ENDPOINT not set - skipping pre-test authentication")
        print("   Set MCP_ENDPOINT environment variable or use --mcp-endpoint flag")
        return

    # Run authentication
    print("\n" + "=" * 70)
    print("🔐 Pre-Test Authentication")
    print("=" * 70)
    print(f"📡 Endpoint: {endpoint}")

    # Get force-auth flag
    force_auth = session.config.getoption("--force-auth", default=False)

    try:
        # Run authentication in event loop
        credentials = asyncio.run(
            ensure_auth_before_tests(
                endpoint=endpoint,
                provider=session.config.getoption("--oauth-provider", default="authkit"),
                force_refresh=force_auth,
            )
        )

        # Store credentials in session config for later use
        session.config._mcp_credentials = credentials

        print("\n✅ Pre-test authentication complete!")
        print(f"   Email: {credentials.get('email', 'N/A')}")
        print(f"   Provider: {credentials.get('provider', 'N/A')}")
        print("=" * 70 + "\n")

    except Exception as e:
        print(f"\n❌ Pre-test authentication failed: {e}")
        print("=" * 70 + "\n")

        # Exit with error if authentication is required
        pytest.exit(f"Authentication failed: {e}", returncode=1)


async def ensure_auth_before_tests(
    endpoint: str, provider: str = "authkit", force_refresh: bool = False
) -> Dict[str, Any]:
    """Ensure authentication is complete before tests run.

    This function performs OAuth authentication and caches credentials
    for the entire test session.

    Args:
        endpoint: MCP endpoint URL
        provider: OAuth provider (authkit, google, github, etc.)
        force_refresh: Force re-authentication even if cached

    Returns:
        Dict containing authentication credentials

    Raises:
        RuntimeError: If authentication fails
    """
    # Import required modules
    try:
        from pheno.testing.mcp_qa.oauth.interactive_credentials import ensure_oauth_credentials
        from pheno.testing.mcp_qa.oauth.session_oauth_broker import SessionOAuthBroker
    except ImportError as e:
        raise RuntimeError(f"Failed to import authentication modules: {e}")

    # Show progress
    print(f"\n🔄 Authenticating to {endpoint}...")
    print(f"   Provider: {provider}")
    print(f"   Force refresh: {force_refresh}")

    # Step 1: Ensure credentials are available
    print("\n📋 Step 1/3: Checking credentials...")
    try:
        required_creds = ["email", "password"]
        credentials = await ensure_oauth_credentials(provider, required_creds)
        print(f"   ✅ Credentials available for {credentials['email']}")
    except Exception as e:
        raise RuntimeError(
            f"Failed to obtain credentials: {e}\n"
            f"Run: python -m mcp_qa.oauth.interactive_credentials"
        )

    # Step 2: Perform OAuth authentication
    print("\n🔐 Step 2/3: Performing OAuth authentication...")
    broker = SessionOAuthBroker()

    try:
        # Get authenticated client
        await broker.ensure_authenticated_client(
            provider=provider, force_refresh=force_refresh
        )

        # Get OAuth tokens
        tokens = broker.get_oauth_tokens()

        if not tokens:
            raise RuntimeError("OAuth completed but no tokens were returned")

        print("   ✅ OAuth successful")
        print(f"   📝 Token: {tokens.access_token[:20]}...")

    except Exception as e:
        raise RuntimeError(f"OAuth authentication failed: {e}")

    # Step 3: Validate authentication
    print("\n✔️  Step 3/3: Validating authentication...")

    # Get cache status for validation
    cache_status = broker.get_cache_status()

    if not cache_status.get("cached"):
        raise RuntimeError("Authentication completed but session is not cached")

    if cache_status.get("expired"):
        raise RuntimeError("Authentication completed but session is already expired")

    print(f"   ✅ Session valid for {int(cache_status.get('time_left', 0) / 60)} minutes")

    # Return credential info for session storage
    return {
        "email": credentials["email"],
        "provider": provider,
        "endpoint": endpoint,
        "access_token": tokens.access_token[:20] + "...",
        "expires_at": tokens.expires_at,
        "cached": True,
    }


def pytest_configure(config):
    """
    Configure plugin with custom markers.
    """
    config.addinivalue_line("markers", "requires_auth: mark test as requiring authentication")
    config.addinivalue_line("markers", "skip_pre_auth: mark test to skip pre-authentication check")


def pytest_collection_modifyitems(config, items):
    """
    Modify test collection to validate authentication requirements.
    """
    # Get stored credentials from session
    credentials = getattr(config, "_mcp_credentials", None)

    # If no credentials and tests require auth, mark as skip
    for item in items:
        # Check if test requires authentication
        if "requires_auth" in [marker.name for marker in item.iter_markers()]:
            if not credentials and "skip_pre_auth" not in [
                marker.name for marker in item.iter_markers()
            ]:
                item.add_marker(pytest.mark.skip(reason="Pre-test authentication not available"))


# Export plugin components
__all__ = [
    "pytest_addoption",
    "pytest_sessionstart",
    "pytest_configure",
    "pytest_collection_modifyitems",
    "ensure_auth_before_tests",
]
