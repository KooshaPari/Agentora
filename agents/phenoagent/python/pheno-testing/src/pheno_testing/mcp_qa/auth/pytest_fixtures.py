"""Pytest Fixtures for Playwright Authentication.

Provides reusable fixtures for all authentication patterns:
- Single authenticated context (shared across tests)
- Worker-scoped contexts (for parallel testing)
- Multi-role contexts (admin + user in same test)
- Session persistence and reuse
- Setup projects and dependencies

Usage:
    # conftest.py
    from pheno.testing.mcp_qa.auth.pytest_fixtures import *

    # test_example.py
    async def test_with_auth(authenticated_context):
        page = await authenticated_context.new_page()
        await page.goto("https://example.com/dashboard")
        # User already authenticated!
"""

import os
from typing import AsyncGenerator

import pytest

try:
    from playwright.async_api import Browser, BrowserContext, Page, async_playwright

    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

from .credential_manager import get_credential_manager
from .mfa_handler import MFAHandler
from .playwright_state_manager import PlaywrightStateManager


# Configuration fixtures
@pytest.fixture(scope="session")
def auth_config():
    """Authentication configuration.

    Override in conftest.py:
        @pytest.fixture(scope="session")
        def auth_config():
            return {
                'provider': 'authkit',
                'email': 'user@example.com',
                'password': 'password',
                'mfa_secret': 'JBSWY3DPEHPK3PXP',  # Optional
            }
    """
    return {
        "provider": os.getenv("AUTH_PROVIDER", "authkit"),
        "email": os.getenv("AUTH_EMAIL", ""),
        "password": os.getenv("AUTH_PASSWORD", ""),
        "mfa_secret": os.getenv("AUTH_MFA_SECRET"),
    }


@pytest.fixture(scope="session")
def credential_manager():
    """
    Get credential manager instance.
    """
    return get_credential_manager()


@pytest.fixture(scope="session")
def state_manager(credential_manager):
    """
    Get Playwright state manager instance.
    """
    return PlaywrightStateManager(credential_manager=credential_manager)


@pytest.fixture(scope="session")
def mfa_handler(credential_manager, auth_config):
    """
    Get MFA handler instance.
    """
    totp_secret = auth_config.get("mfa_secret")
    return MFAHandler(credential_manager, totp_secret=totp_secret)


# Authentication callback fixtures
@pytest.fixture(scope="session")
def auth_callback(auth_config, mfa_handler):
    """Authentication callback for automated login.

    Override in conftest.py for custom authentication:
        @pytest.fixture(scope="session")
        def auth_callback(auth_config, mfa_handler):
            async def do_auth(page):
                # Custom auth logic
                pass
            return do_auth
    """

    async def default_auth(page: Page):
        """
        Default authentication using PlaywrightOAuthAdapter.
        """
        from pheno.testing.mcp_qa.oauth.flow_adapters import OAuthFlowFactory

        flow_adapter = OAuthFlowFactory.create(
            provider=auth_config["provider"],
            email=auth_config["email"],
            password=auth_config["password"],
        )

        # Execute authentication flow
        success = await flow_adapter.execute_flow(page, page.url)

        if not success:
            raise RuntimeError("Authentication failed")

    return default_auth


# Browser and context fixtures
@pytest.fixture(scope="session")
async def browser():
    """
    Session-scoped browser instance.
    """
    if not HAS_PLAYWRIGHT:
        pytest.skip("Playwright not installed")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        yield browser
        await browser.close()


@pytest.fixture(scope="session")
async def authenticated_context(
    browser: Browser, state_manager: PlaywrightStateManager, auth_callback, auth_config
) -> AsyncGenerator[BrowserContext, None]:
    """Session-scoped authenticated context.

    All tests share the same authentication state.
    Fastest option when all tests use same account.

    Usage:
        async def test_dashboard(authenticated_context):
            page = await authenticated_context.new_page()
            await page.goto("https://example.com/dashboard")
    """
    profile_name = f"{auth_config['provider']}_{auth_config['email']}"

    context = await state_manager.get_or_create_state(browser, profile_name, auth_callback)

    yield context

    await context.close()


@pytest.fixture(scope="function")
async def page(authenticated_context: BrowserContext) -> AsyncGenerator[Page, None]:
    """Function-scoped page from authenticated context.

    Each test gets a fresh page, but shares authentication.

    Usage:
        async def test_dashboard(page):
            await page.goto("https://example.com/dashboard")
    """
    page = await authenticated_context.new_page()
    yield page
    await page.close()


# Worker-scoped fixtures for parallel testing
def pytest_configure(config):
    """
    Add worker_id marker for xdist.
    """
    config.addinivalue_line("markers", "worker_id: mark test with specific worker_id")


@pytest.fixture(scope="session")
def worker_id(worker_id="master"):
    """Get pytest-xdist worker ID.

    Returns 'master' for non-parallel runs.
    """
    return worker_id


@pytest.fixture(scope="session")
async def worker_context(
    browser: Browser, state_manager: PlaywrightStateManager, auth_callback, worker_id: str
) -> AsyncGenerator[BrowserContext, None]:
    """Worker-scoped authenticated context for parallel testing.

    Each worker gets its own authentication profile to avoid conflicts.

    Usage (with pytest-xdist):     # Run with: pytest -n 4     async def
    test_parallel(worker_context):         page = await worker_context.new_page()
    await page.goto("
    https://example.com/dashboard")
    """
    context = await state_manager.get_worker_context(browser, worker_id, auth_callback)

    yield context

    await context.close()


# Multi-role fixtures
@pytest.fixture(scope="session")
async def admin_context(
    browser: Browser, state_manager: PlaywrightStateManager
) -> AsyncGenerator[BrowserContext, None]:
    """Authenticated context for admin user.

    Override auth_callback to use admin credentials:
        @pytest.fixture(scope="session")
        def admin_auth_callback():
            async def auth(page):
                # Admin authentication
                pass
            return auth
    """
    # This is a placeholder - implement admin auth
    pytest.skip("Admin authentication not configured")


@pytest.fixture(scope="session")
async def user_context(
    browser: Browser, state_manager: PlaywrightStateManager
) -> AsyncGenerator[BrowserContext, None]:
    """Authenticated context for regular user.

    Same as authenticated_context but explicit for multi-role tests.
    """
    # This is a placeholder - implement user auth
    pytest.skip("User authentication not configured")


@pytest.fixture(scope="function")
async def multi_role_pages(
    admin_context: BrowserContext, user_context: BrowserContext
) -> AsyncGenerator[tuple[Page, Page], None]:
    """Two pages with different roles for same test.

    Usage:
        async def test_admin_can_see_user(multi_role_pages):
            admin_page, user_page = multi_role_pages

            # User creates something
            await user_page.goto("https://example.com/create")
            await user_page.click("button:has-text('Create')")

            # Admin can see it
            await admin_page.goto("https://example.com/admin/items")
            await admin_page.wait_for_selector("text='New Item'")
    """
    admin_page = await admin_context.new_page()
    user_page = await user_context.new_page()

    yield (admin_page, user_page)

    await admin_page.close()
    await user_page.close()


# API token fixtures
@pytest.fixture(scope="session")
async def api_tokens(authenticated_context: BrowserContext):
    """Extract API tokens from authenticated session.

    Usage:
        async def test_api(api_tokens):
            headers = {"Authorization": f"Bearer {api_tokens['access_token']}"}
            response = await httpx.get(url, headers=headers)
    """
    # Get cookies and localStorage
    page = await authenticated_context.new_page()

    # Extract tokens from storage
    tokens = await page.evaluate(
        """() => {
        return {
            access_token: localStorage.getItem('access_token'),
            refresh_token: localStorage.getItem('refresh_token'),
            session_id: document.cookie.match(/session_id=([^;]+)/)?.[1]
        }
    }"""
    )

    await page.close()

    return tokens


@pytest.fixture(scope="session")
async def api_headers(api_tokens):
    """HTTP headers with authentication for API calls.

    Usage:
        async def test_api_endpoint(api_headers):
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=api_headers)
    """
    return {
        "Authorization": f"Bearer {api_tokens['access_token']}",
        "Content-Type": "application/json",
    }


# Cleanup fixtures
@pytest.fixture(scope="session", autouse=True)
async def cleanup_expired_states(state_manager: PlaywrightStateManager):
    """
    Automatically clean up expired authentication states.
    """
    yield
    # Cleanup after all tests
    await state_manager.clear_expired()


__all__ = [
    # Config
    "auth_config",
    "credential_manager",
    "state_manager",
    "mfa_handler",
    # Auth callback
    "auth_callback",
    # Browser & Context
    "browser",
    "authenticated_context",
    "page",
    # Parallel testing
    "worker_id",
    "worker_context",
    # Multi-role
    "admin_context",
    "user_context",
    "multi_role_pages",
    # API
    "api_tokens",
    "api_headers",
    # Cleanup
    "cleanup_expired_states",
]
