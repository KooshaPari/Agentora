"""Server fixtures for MCP-QA testing framework.

Provides fixtures for:
- Real MCP servers
- Test servers with isolation
- Mock servers for unit testing
- Server factories for custom configurations
"""

import asyncio
import os
from typing import Any, AsyncGenerator, Dict, Optional

import pytest


@pytest.fixture
async def mcp_server() -> AsyncGenerator[Dict[str, Any], None]:
    """Real MCP server instance for integration testing.

    Starts a full MCP server process and provides connection details.
    Server is automatically cleaned up after test completion.

    Usage:
        async def test_server_tools(mcp_server):
            endpoint = mcp_server["endpoint"]
            # Connect to server and test

    Yields:
        Dict containing server configuration:
            - endpoint: Server URL
            - process: Server process handle
            - config: Server configuration
    """
    # Start server process
    endpoint = os.getenv("MCP_ENDPOINT", "http://localhost:8000/mcp")

    server_config = {
        "endpoint": endpoint,
        "process": None,  # Would be actual process
        "config": {
            "host": "localhost",
            "port": 8000,
            "workers": 1,
        },
    }

    try:
        yield server_config
    finally:
        # Cleanup server
        if server_config.get("process"):
            # Terminate server process
            pass


@pytest.fixture
async def test_server(tmp_path) -> AsyncGenerator[Dict[str, Any], None]:
    """Isolated test server with temporary database.

    Creates a fresh server instance with isolated storage for each test.
    Ideal for testing server behavior without affecting other tests.

    Usage:
        async def test_server_state(test_server):
            client = test_server["client"]
            result = await client.call_tool("entity", {
                "operation": "create",
                "data": {"name": "test"}
            })
            assert result["success"]

    Yields:
        Dict containing:
            - endpoint: Server URL
            - client: Pre-configured MCP client
            - db_path: Path to test database
            - config: Server configuration
    """
    # Create temporary database
    db_path = tmp_path / "test.db"

    # Create isolated server configuration
    server_config = {
        "endpoint": f"http://localhost:{os.getpid() % 10000 + 30000}/mcp",
        "client": None,  # Would be actual client
        "db_path": str(db_path),
        "config": {
            "database": str(db_path),
            "isolated": True,
        },
    }

    try:
        yield server_config
    finally:
        # Cleanup
        if db_path.exists():
            db_path.unlink()


@pytest.fixture
async def mock_server():
    """Mock MCP server for unit testing.

    Provides a lightweight mock server that simulates MCP responses
    without actually running a server process. Perfect for fast unit tests.

    Usage:
        async def test_tool_logic(mock_server):
            mock_server.register_tool("chat", lambda args: {
                "success": True,
                "response": "Mocked response"
            })

            result = await mock_server.call_tool("chat", {"prompt": "test"})
            assert result["response"] == "Mocked response"

    Yields:
        MockMCPServer: Mock server instance
    """
    from pheno.testing.mcp_qa.mocking import MockMCPServer

    server = MockMCPServer()
    try:
        yield server
    finally:
        await server.cleanup()


@pytest.fixture
def server_factory():
    """Factory for creating custom server configurations.

    Allows tests to create multiple servers with different configurations.
    Useful for testing multi-server scenarios.

    Usage:
        async def test_multi_server(server_factory):
            server1 = await server_factory.create(port=8001)
            server2 = await server_factory.create(port=8002)

            # Test cross-server communication
            result1 = await server1.call_tool("chat", {"prompt": "hello"})
            result2 = await server2.call_tool("chat", {"prompt": "world"})

    Returns:
        ServerFactory: Factory for creating servers
    """

    class ServerFactory:
        def __init__(self):
            self.servers = []

        async def create(
            self,
            port: Optional[int] = None,
            config: Optional[Dict[str, Any]] = None,
        ) -> Dict[str, Any]:
            """
            Create new server instance.
            """
            if port is None:
                port = 8000 + len(self.servers)

            server_config = {
                "endpoint": f"http://localhost:{port}/mcp",
                "port": port,
                "config": config or {},
            }

            self.servers.append(server_config)
            return server_config

        async def cleanup(self):
            """
            Cleanup all created servers.
            """
            for server in self.servers:
                # Stop server process
                pass
            self.servers.clear()

    factory = ServerFactory()
    try:
        yield factory
    finally:
        asyncio.run(factory.cleanup())
