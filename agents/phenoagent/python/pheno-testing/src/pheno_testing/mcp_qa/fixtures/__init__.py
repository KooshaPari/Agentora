"""
MCP-QA Fixtures - Comprehensive Testing Fixtures for MCP Servers

Provides pytest fixtures for:
- Server management (mcp_server, test_server)
- Client creation (mcp_client, authenticated_client)
- Database isolation (isolated_database, db_pool)
- Worker-scoped resources for parallel testing
- Authentication and OAuth flows
- Tool-specific clients

Usage:
    from pheno.testing.mcp_qa.fixtures import mcp_server, mcp_client, authenticated_client

    async def test_my_tool(mcp_client):
        result = await mcp_client.call_tool("my_tool", {"param": "value"})
        assert result["success"]
"""

from pheno.testing.mcp_qa.fixtures.auth import (
    authenticated_mcp_client,
    clear_oauth_cache,
    oauth_client_factory,
    oauth_tokens,
    session_token_manager,
)
from pheno.testing.mcp_qa.fixtures.clients import (
    fast_http_tools,
    http_client,
    isolated_client,
    mcp_client,
    mcp_client_pool,
)
from pheno.testing.mcp_qa.fixtures.database import (
    db_pool,
    isolated_database,
    test_database,
)
from pheno.testing.mcp_qa.fixtures.servers import (
    mcp_server,
    mock_server,
    server_factory,
    test_server,
)
from pheno.testing.mcp_qa.fixtures.tools import (
    chat_tool_client,
    query_tool_client,
    tool_client_factory,
)
from pheno.testing.mcp_qa.fixtures.workers import (
    worker_cleanup,
    worker_database,
    worker_id,
    worker_port,
)

__all__ = [
    # Authentication
    "session_token_manager",
    "oauth_tokens",
    "authenticated_mcp_client",
    "oauth_client_factory",
    "clear_oauth_cache",
    # Clients
    "http_client",
    "mcp_client",
    "mcp_client_pool",
    "isolated_client",
    "fast_http_tools",
    # Servers
    "mcp_server",
    "test_server",
    "mock_server",
    "server_factory",
    # Database
    "isolated_database",
    "db_pool",
    "test_database",
    # Workers
    "worker_id",
    "worker_port",
    "worker_database",
    "worker_cleanup",
    # Tools
    "tool_client_factory",
    "chat_tool_client",
    "query_tool_client",
]
