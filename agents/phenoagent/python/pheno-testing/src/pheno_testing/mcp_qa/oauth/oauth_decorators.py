"""
OAuth decorators and context managers for easy test integration.
"""

import asyncio
import functools
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Callable, Optional

import pytest

from pheno.testing.mcp_qa.adapters import MCPClientAdapter, PlaywrightOAuthAdapter
from pheno.testing.mcp_qa.oauth_automation.cache import OAuthTokens, get_session_manager


def requires_oauth(provider: str = "authkit"):
    """Decorator that ensures OAuth authentication for a provider.

    Usage:
        @requires_oauth("authkit")
        async def test_my_tool():
            # Test has access to authenticated client
            pass

        @requires_oauth("github")
        async def test_github_integration():
            # Test runs with GitHub OAuth
            pass
    """

    def decorator(test_func):
        @functools.wraps(test_func)
        async def wrapper(*args, **kwargs):
            manager = get_session_manager()

            async def perform_oauth(provider: str) -> OAuthTokens:
                """
                Perform OAuth for the specified provider.
                """
                # This would be implemented to do actual OAuth
                # For now, placeholder
                return OAuthTokens(
                    access_token=f"{provider}_test_token",
                    provider=provider,
                )

            async with manager.ensure_tokens(provider, perform_oauth) as tokens:
                # Inject tokens into test context if needed
                kwargs["oauth_tokens"] = tokens
                return await test_func(*args, **kwargs)

        # Add pytest marker
        wrapper = pytest.mark.auth(wrapper)
        return wrapper

    return decorator


def fast_test(test_func):
    """Decorator for fast unit tests that should run in parallel.

    Usage:
        @fast_test
        async def test_chat_basic():
            # This test is marked as fast and parallel-safe
            pass
    """

    @functools.wraps(test_func)
    def wrapper(*args, **kwargs):
        return test_func(*args, **kwargs)

    # Add pytest markers
    wrapper = pytest.mark.fast(wrapper)
    wrapper = pytest.mark.parallel(wrapper)
    return wrapper


def integration_test(test_func):
    """Decorator for integration tests that use session OAuth.

    Usage:
        @integration_test
        async def test_full_workflow():
            # This test is marked as integration and uses session auth
            pass
    """

    @functools.wraps(test_func)
    def wrapper(*args, **kwargs):
        return test_func(*args, **kwargs)

    # Add pytest markers
    wrapper = pytest.mark.integration(wrapper)
    wrapper = pytest.mark.auth(wrapper)
    return wrapper


def tool_test(tool_name: str):
    """Decorator for tool-specific tests.

    Usage:
        @tool_test("chat")
        async def test_chat_feature():
            # This test is marked with the tool name
            pass
    """

    def decorator(test_func):
        @functools.wraps(test_func)
        def wrapper(*args, **kwargs):
            return test_func(*args, **kwargs)

        # Add custom marker for tool
        marker = getattr(pytest.mark, tool_name, pytest.mark.tool)
        wrapper = marker(wrapper)
        return wrapper

    return decorator


@asynccontextmanager
async def oauth_session(
    provider: str = "authkit", endpoint: Optional[str] = None
) -> AsyncGenerator[MCPClientAdapter, None]:
    """Context manager for OAuth-authenticated MCP sessions.

    Usage:
        async with oauth_session("authkit") as client:
            result = await client.call_tool("chat", {"prompt": "test"})
            assert result["success"]

        async with oauth_session("github") as client:
            tools = await client.list_tools()
            assert len(tools) > 0
    """
    manager = get_session_manager()

    async def perform_oauth(provider: str) -> OAuthTokens:
        """
        Perform OAuth authentication for provider.
        """
        import os

        email = os.getenv("ZEN_TEST_EMAIL", "kooshapari@gmail.com")
        password = os.getenv("ZEN_TEST_PASSWORD")
        endpoint_url = endpoint or os.getenv("ZEN_MCP_ENDPOINT", "https://zen.kooshapari.com/mcp")

        if not password:
            raise RuntimeError("ZEN_TEST_PASSWORD required for OAuth")

        oauth_adapter = PlaywrightOAuthAdapter(email, password)
        client, auth_task = oauth_adapter.create_oauth_client(endpoint_url)

        try:
            oauth_url = await oauth_adapter.wait_for_oauth_url(timeout_seconds=15)
            if oauth_url:
                automation_task = asyncio.create_task(
                    oauth_adapter.automate_login_with_retry(oauth_url)
                )
                await asyncio.gather(auth_task, automation_task, return_exceptions=True)
            else:
                await asyncio.wait_for(auth_task, timeout=10.0)

            # Extract real tokens from client
            return OAuthTokens(
                access_token="session_authenticated",  # Placeholder
                provider=provider,
                expires_at=None,
            )
        finally:
            # Don't close client here - we'll use it
            pass

    async with manager.ensure_tokens(provider, perform_oauth):
        # Create client adapter using the tokens
        # In real implementation, this would create an authenticated client

        import os

        email = os.getenv("ZEN_TEST_EMAIL", "kooshapari@gmail.com")
        password = os.getenv("ZEN_TEST_PASSWORD")
        endpoint_url = endpoint or os.getenv("ZEN_MCP_ENDPOINT", "https://zen.kooshapari.com/mcp")

        oauth_adapter = PlaywrightOAuthAdapter(email, password)
        client, auth_task = oauth_adapter.create_oauth_client(endpoint_url)

        # In practice, we'd configure the client with cached tokens
        # instead of re-running OAuth
        client_adapter = MCPClientAdapter(client, verbose_on_fail=True)

        try:
            yield client_adapter
        finally:
            if client:
                await client.__aexit__(None, None, None)


@asynccontextmanager
async def tool_session(tool_name: str, provider: str = "authkit") -> AsyncGenerator[Callable, None]:
    """Context manager for tool-specific testing sessions.

    Usage:
        async with tool_session("chat") as chat:
            result = await chat("Hello world")
            assert result["success"]

        async with tool_session("deploy") as deploy:
            result = await deploy({"target": "staging"})
            assert result["success"]
    """
    async with oauth_session(provider) as client:

        async def tool_call(*args, **kwargs):
            """
            Make tool call with the authenticated client.
            """
            if len(args) == 1 and len(kwargs) == 0 and isinstance(args[0], dict):
                # Single dict argument - use as-is
                return await client.call_tool(tool_name, args[0])
            elif len(args) == 1 and len(kwargs) == 0:
                # Single non-dict argument - wrap appropriately
                if tool_name == "chat":
                    return await client.call_tool(tool_name, {"prompt": args[0]})
                else:
                    return await client.call_tool(tool_name, {"input": args[0]})
            else:
                # Multiple args or kwargs - combine
                params = dict(kwargs)
                if args:
                    params.update({"args": args})
                return await client.call_tool(tool_name, params)

        yield tool_call


# Example usage functions for documentation
async def example_usage():
    """
    Example usage of OAuth context managers and decorators.
    """

    # Using context manager
    async with oauth_session("authkit") as client:
        result = await client.call_tool("chat", {"prompt": "Hello"})
        print(f"Chat result: {result}")

    # Using tool session
    async with tool_session("chat") as chat:
        result = await chat("What is Python?")
        print(f"Tool result: {result}")

    # Using decorators in tests
    @requires_oauth("authkit")
    @fast_test
    async def test_example():
        """
        Example test with decorators.
        """
        pass

    @integration_test
    @tool_test("deploy")
    async def test_deploy_workflow():
        """
        Example integration test.
        """
        pass
