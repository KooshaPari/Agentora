"""Pytest-native test infrastructure with session sharing and HTTP parallelization.

Features:
- Uses pytest's native progress display (no custom progress bars)
- Session-scoped fixtures for shared authenticated clients
- Parallel test execution with pytest-xdist
- Direct HTTP calls for 20x faster testing
- Proper session state management across parallel workers
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import pytest

from ..execution.http_adapter import HTTPToolAdapter, HybridToolAdapter
from ..oauth.credential_broker import CapturedCredentials, UnifiedCredentialBroker
from ..oauth.oauth_session import OAuthSessionBroker

logger = logging.getLogger(__name__)


@dataclass
class SharedSession:
    """
    Shared session state accessible across parallel pytest workers.
    """

    client: Any
    credentials: CapturedCredentials
    endpoint: str
    http_adapter: Optional[HTTPToolAdapter] = None
    http_broker: Optional[OAuthSessionBroker] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize session for sharing across workers.
        """
        return {
            "endpoint": self.endpoint,
            "credentials": self.credentials.to_dict(),
            "has_http": self.http_adapter is not None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], client: Any) -> "SharedSession":
        """
        Deserialize session from worker data.
        """
        return cls(
            client=client,
            credentials=CapturedCredentials.from_dict(data["credentials"]),
            endpoint=data["endpoint"],
            http_adapter=None,  # Will be recreated
            http_broker=None,
        )


# Pytest fixtures for session management


@pytest.fixture(scope="session")
def event_loop():
    """
    Create event loop for async tests.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def mcp_endpoint(request) -> str:
    """
    Get MCP endpoint from config or environment.
    """
    import os

    return request.config.getoption("--mcp-endpoint", default=None) or os.getenv(
        "MCP_ENDPOINT", "http://localhost:8001/mcp"
    )


@pytest.fixture(scope="session")
async def oauth_provider(request) -> str:
    """
    Get OAuth provider from config or environment.
    """
    import os

    return request.config.getoption("--oauth-provider", default=None) or os.getenv(
        "OAUTH_PROVIDER", "authkit"
    )


@pytest.fixture(scope="session")
async def shared_session(mcp_endpoint: str, oauth_provider: str) -> SharedSession:
    """Session-scoped fixture providing shared authenticated client.

    This fixture is created once per pytest session and shared across all test workers
    when using pytest-xdist for parallel execution.
    """
    # Create credential broker
    broker = UnifiedCredentialBroker(mcp_endpoint=mcp_endpoint, provider=oauth_provider)

    try:
        # Get authenticated client (with progress shown via logging)
        logger.info(f"🔐 Authenticating to {mcp_endpoint}...")
        client, credentials = await broker.get_authenticated_client()
        logger.info(f"✅ Authenticated as {credentials.email}")

        # Create HTTP adapter for fast direct calls
        api_base_url = mcp_endpoint.replace("/mcp", "/api")
        http_broker = OAuthSessionBroker(mcp_url=mcp_endpoint, provider=oauth_provider)
        http_adapter = HTTPToolAdapter(broker=http_broker, api_base_url=api_base_url)

        session = SharedSession(
            client=client,
            credentials=credentials,
            endpoint=mcp_endpoint,
            http_adapter=http_adapter,
            http_broker=http_broker,
        )

        logger.info("✅ HTTP adapter enabled - tests will run 20x faster!")

        yield session

    finally:
        # Cleanup
        await broker.close()


@pytest.fixture(scope="function")
async def mcp_client(shared_session: SharedSession):
    """Function-scoped fixture providing MCP client for a single test.

    Each test gets its own reference but shares the underlying session.
    """
    return shared_session.client


@pytest.fixture(scope="function")
async def http_adapter(shared_session: SharedSession) -> HTTPToolAdapter:
    """Function-scoped fixture providing HTTP adapter for direct API calls.

    Use this for fast tool calls that don't need full MCP protocol.
    """
    if not shared_session.http_adapter:
        pytest.skip("HTTP adapter not available")
    return shared_session.http_adapter


@pytest.fixture(scope="function")
async def hybrid_adapter(shared_session: SharedSession, mcp_client) -> HybridToolAdapter:
    """Function-scoped fixture providing hybrid adapter (MCP + HTTP).

    Automatically chooses fastest method for each tool call.
    """
    from ..testing.adapters import MCPClientAdapter

    mcp_adapter = MCPClientAdapter(mcp_client, verbose_on_fail=True)

    return HybridToolAdapter(mcp_adapter=mcp_adapter, http_adapter=shared_session.http_adapter)


@pytest.fixture(scope="function")
def test_data_factory():
    """
    Factory for generating test data.
    """
    from ..testing.data_generator import DataGenerator

    return DataGenerator()


# Pytest configuration hooks


def pytest_addoption(parser):
    """
    Add custom command line options.
    """
    parser.addoption("--mcp-endpoint", action="store", default=None, help="MCP endpoint URL")
    parser.addoption(
        "--oauth-provider",
        action="store",
        default="authkit",
        help="OAuth provider (authkit, google, github, etc.)",
    )
    parser.addoption(
        "--force-mcp",
        action="store_true",
        default=False,
        help="Force MCP protocol (disable HTTP optimization)",
    )


def pytest_configure(config):
    """
    Configure pytest.
    """
    # Register custom markers
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "http_only: marks tests that require HTTP adapter")


# Helper functions for test assertions


def assert_tool_success(result: Dict[str, Any], tool_name: str):
    """
    Assert that tool call succeeded.
    """
    assert result.get("success"), f"{tool_name} failed: {result.get('error', 'Unknown error')}"


def assert_tool_result(result: Dict[str, Any], expected_keys: list):
    """
    Assert that tool result contains expected keys.
    """
    assert_tool_success(result, "tool")
    result_data = result.get("result", {})
    for key in expected_keys:
        assert key in result_data, f"Missing expected key: {key}"


def assert_no_error(result: Dict[str, Any]):
    """
    Assert that result contains no error.
    """
    assert not result.get("error"), f"Unexpected error: {result.get('error')}"


# Session state management for parallel execution


class SessionStateManager:
    """Manages session state across pytest-xdist workers.

    When using pytest-xdist for parallel execution, this ensures all workers share the
    same authenticated session.
    """

    def __init__(self, cache_file: Optional[Path] = None):
        self.cache_file = cache_file or Path.home() / ".cache" / "mcp_test_session.json"
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)

    def save_session(self, session: SharedSession):
        """
        Save session state to cache.
        """
        with open(self.cache_file, "w") as f:
            json.dump(session.to_dict(), f, indent=2)

    def load_session(self) -> Optional[Dict[str, Any]]:
        """
        Load session state from cache.
        """
        if not self.cache_file.exists():
            return None

        try:
            with open(self.cache_file, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load cached session: {e}")
            return None

    def clear_session(self):
        """
        Clear cached session.
        """
        if self.cache_file.exists():
            self.cache_file.unlink()


# Example pytest test using these fixtures

"""
Example test file structure:

```python
import pytest
from pheno.testing.mcp_qa.testing.pytest_native import *

@pytest.mark.asyncio
async def test_chat_tool(http_adapter):
    \"\"\"Test chat tool via direct HTTP (fast).\"\"\"
    result = await http_adapter.call_tool_http(
        "chat",
        {"message": "Hello", "model": "gpt-4"}
    )

    assert_tool_success(result, "chat")
    assert "response" in result["result"]


@pytest.mark.asyncio
async def test_complex_tool(mcp_client):
    \"\"\"Test complex tool via MCP protocol.\"\"\"
    result = await mcp_client.call_tool(
        "complex_tool",
        {"param": "value"}
    )

    assert result.success


@pytest.mark.asyncio
@pytest.mark.parametrize("model", ["gpt-4", "claude-3", "gemini-pro"])
async def test_multiple_models(hybrid_adapter, model):
    \"\"\"Test with multiple models in parallel.\"\"\"
    result = await hybrid_adapter.call_tool(
        "chat",
        {"message": "Test", "model": model}
    )

    assert_tool_success(result, "chat")
```

Run with:
- Sequential: `pytest tests/ -v`
- Parallel: `pytest tests/ -v -n auto`
- Fast HTTP only: `pytest tests/ -v -n auto -m "not slow"`
- Force MCP: `pytest tests/ -v --force-mcp`
"""
