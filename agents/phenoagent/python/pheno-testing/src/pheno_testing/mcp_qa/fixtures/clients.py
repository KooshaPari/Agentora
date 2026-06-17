"""Client fixtures for MCP-QA testing framework.

Provides various client configurations:
- HTTP clients with OAuth
- MCP client pools for parallel testing
- Isolated clients for test isolation
- Fast HTTP tool wrappers
"""

import asyncio
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict

import pytest

try:
    import httpx

    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False
    httpx = None

from pheno.testing.mcp_qa.auth.adapters import MCPClientAdapter
from pheno.testing.mcp_qa.auth.cache import OAuthTokens


@pytest.fixture
async def http_client(oauth_tokens: OAuthTokens) -> AsyncGenerator:
    """Direct HTTP client with session OAuth tokens.

    Bypasses MCP layer for ultra-fast testing. Automatically includes
    authentication headers from session OAuth.

    Usage:
        async def test_chat_http(http_client):
            response = await http_client.post("/tools/chat",
                json={"prompt": "What is 2+2?"}
            )
            assert response.status_code == 200
            result = response.json()
            assert result["success"]

    Yields:
        httpx.AsyncClient: HTTP client with authentication
    """
    if not HAS_HTTPX:
        pytest.skip("httpx not installed - install with: pip install httpx")

    endpoint = os.getenv("MCP_ENDPOINT", "http://localhost:8000/mcp")

    headers = {"Content-Type": "application/json"}

    # Add auth header if we have tokens
    if oauth_tokens and oauth_tokens.access_token:
        headers["Authorization"] = f"Bearer {oauth_tokens.access_token}"

    async with httpx.AsyncClient(
        base_url=endpoint,
        headers=headers,
        timeout=30.0,
    ) as client:
        yield client


@pytest.fixture
async def mcp_client(oauth_tokens: OAuthTokens) -> AsyncGenerator[MCPClientAdapter, None]:
    """Standard MCP client fixture.

    Similar to authenticated_mcp_client but function-scoped for tests
    that need isolation.

    Usage:
        async def test_tool(mcp_client):
            result = await mcp_client.call_tool("chat", {"prompt": "test"})
            assert result["success"]

    Yields:
        MCPClientAdapter: MCP client for testing
    """
    # Use oauth_tokens to create client
    # Implementation would create actual MCP client
    client = None  # Placeholder
    adapter = MCPClientAdapter(client, verbose_on_fail=True) if client else None

    try:
        yield adapter
    finally:
        if client and hasattr(client, "__aexit__"):
            await client.__aexit__(None, None, None)


@pytest.fixture
async def mcp_client_pool(oauth_tokens: OAuthTokens):
    """Pool of MCP clients for parallel testing.

    Maintains a pool of authenticated clients that can be reused
    across multiple concurrent tests, reducing overhead.

    Usage:
        async def test_parallel_tools(mcp_client_pool):
            tasks = []
            for i in range(5):
                client = await mcp_client_pool.get_client()
                tasks.append(
                    client.call_tool("chat", {"prompt": f"Test {i}"})
                )

            results = await asyncio.gather(*tasks)
            assert all(r["success"] for r in results)

    Yields:
        ClientPool: Pool manager for MCP clients
    """

    class ClientPool:
        def __init__(self, max_size: int = 5):
            self.max_size = max_size
            self._clients = []
            self._available = asyncio.Queue()
            self._lock = asyncio.Lock()
            self.oauth_tokens = oauth_tokens

        async def get_client(self) -> MCPClientAdapter:
            """
            Get available client from pool.
            """
            try:
                # Try to get from available queue (non-blocking)
                return self._available.get_nowait()
            except asyncio.QueueEmpty:
                pass

            async with self._lock:
                # Check if we can create new client
                if len(self._clients) < self.max_size:
                    # Create new authenticated client
                    client = await self._create_client()
                    self._clients.append(client)
                    return client
                else:
                    # Wait for available client
                    return await self._available.get()

        async def _create_client(self) -> MCPClientAdapter:
            """
            Create new authenticated client.
            """
            # Use oauth_tokens to create client
            # Placeholder implementation
            return MCPClientAdapter(None, verbose_on_fail=True)

        async def return_client(self, client: MCPClientAdapter):
            """
            Return client to pool.
            """
            self._available.put_nowait(client)

        async def close_all(self):
            """
            Close all clients in pool.
            """
            for client in self._clients:
                if hasattr(client, "__aexit__"):
                    await client.__aexit__(None, None, None)

    pool = ClientPool()
    try:
        yield pool
    finally:
        await pool.close_all()


@pytest.fixture
async def isolated_client(oauth_tokens: OAuthTokens) -> AsyncGenerator[MCPClientAdapter, None]:
    """Isolated MCP client for individual tests.

    Each test gets a completely fresh client instance with no
    shared state. Use this when testing client lifecycle or
    state management.

    Usage:
        async def test_tool_isolation(isolated_client):
            # This client is unique to this test
            result = await isolated_client.call_tool("chat", {"prompt": "test"})
            assert result["success"]

    Yields:
        MCPClientAdapter: Isolated client instance
    """
    # Create isolated client using OAuth tokens
    client = None  # Placeholder - would create real client
    adapter = MCPClientAdapter(client, verbose_on_fail=True) if client else None

    try:
        yield adapter
    finally:
        if client and hasattr(client, "__aexit__"):
            await client.__aexit__(None, None, None)


@pytest.fixture
def fast_http_tools(http_client):
    """High-level tool helpers using direct HTTP calls.

    Provides convenient methods for common tools without the
    MCP overhead. Useful for rapid integration testing.

    Usage:
        async def test_multiple_tools(fast_http_tools):
            chat_result = await fast_http_tools.chat("Hello")
            assert chat_result["success"]

            models = await fast_http_tools.list_models()
            assert len(models) > 0

    Returns:
        FastToolClient: High-level tool client
    """

    class FastToolClient:
        def __init__(self, client):
            self.client = client

        async def chat(self, prompt: str, model: str = "auto") -> Dict[str, Any]:
            """
            Direct chat tool call.
            """
            response = await self.client.post(
                "/tools/chat", json={"prompt": prompt, "model": model}
            )
            response.raise_for_status()
            return response.json()

        async def thinkdeep(self, step: str, **kwargs) -> Dict[str, Any]:
            """
            Direct thinkdeep tool call.
            """
            payload = {"step": step, **kwargs}
            response = await self.client.post("/tools/thinkdeep", json=payload)
            response.raise_for_status()
            return response.json()

        async def consensus(self, step: str, models: list, **kwargs) -> Dict[str, Any]:
            """
            Direct consensus tool call.
            """
            payload = {"step": step, "models": models, **kwargs}
            response = await self.client.post("/tools/consensus", json=payload)
            response.raise_for_status()
            return response.json()

        async def list_models(self) -> Dict[str, Any]:
            """
            Direct listmodels tool call.
            """
            response = await self.client.post("/tools/listmodels", json={})
            response.raise_for_status()
            return response.json()

        async def query(self, query: str, **kwargs) -> Dict[str, Any]:
            """
            Direct query tool call.
            """
            payload = {"query": query, **kwargs}
            response = await self.client.post("/tools/query", json=payload)
            response.raise_for_status()
            return response.json()

        async def entity(self, operation: str, **kwargs) -> Dict[str, Any]:
            """
            Direct entity tool call.
            """
            payload = {"operation": operation, **kwargs}
            response = await self.client.post("/tools/entity", json=payload)
            response.raise_for_status()
            return response.json()

    return FastToolClient(http_client)


@asynccontextmanager
async def oauth_session(provider: str = "authkit"):
    """Context manager for OAuth sessions.

    Useful for creating temporary authenticated sessions in tests:

    Usage:
        async def test_auth_flow():
            async with oauth_session("github") as client:
                tools = await client.list_tools()
                result = await client.call_tool("chat", {"prompt": "test"})
                assert result["success"]

    Args:
        provider: OAuth provider name

    Yields:
        MCPClientAdapter: Authenticated client for the session
    """
    # Create session-scoped OAuth client
    client = None  # Placeholder
    adapter = MCPClientAdapter(client, verbose_on_fail=True) if client else None

    try:
        yield adapter
    finally:
        if client and hasattr(client, "__aexit__"):
            await client.__aexit__(None, None, None)
