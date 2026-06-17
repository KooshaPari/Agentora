# MCP Widget Adapters

This module provides MCP-specific adapters that wrap existing MCP components and implement standardized provider protocols. These adapters enable consistent interfaces across different MCP testing scenarios.

## Overview

The adapters implement the **Adapter Pattern**, wrapping existing MCP objects to provide a unified interface that follows protocol definitions. This approach:

- **Decouples** testing code from specific MCP implementations
- **Standardizes** interfaces across different providers
- **Simplifies** integration with testing frameworks
- **Enables** easy mocking and testing
- **Provides** graceful error handling and logging

## Available Adapters

### 1. MCPOAuthCacheAdapter

Wraps `CachedOAuthClient` to implement the `OAuthCacheProvider` protocol.

**Purpose:** Manages OAuth token caching for authenticated MCP clients.

**Methods:**
- `get_cache_path()` - Get path to OAuth token cache file
- `is_token_cached()` - Check if valid token exists
- `clear_cache()` - Clear cached tokens
- `create_client()` - Create authenticated FastMCP client

**Example:**
```python
from mcp_qa.adapters import create_oauth_adapter

# Create adapter
adapter = create_oauth_adapter("https://api.example.com/mcp")

# Check cache
if adapter.is_token_cached():
    print("Using cached token")
else:
    print("Will perform OAuth flow")

# Create authenticated client
client = await adapter.create_client()
```

### 2. MCPClientAdapter

Wraps the core `MCPClientAdapter` to implement the `ClientAdapter` protocol.

**Purpose:** Provides unified interface for MCP tool calls with error handling and statistics.

**Methods:**
- `call_tool(tool_name, arguments)` - Execute MCP tool
- `list_tools()` - Get available tools
- `ping()` - Health check
- `get_stats()` - Get call statistics

**Example:**
```python
from mcp_qa.core.adapters import MCPClientAdapter as CoreAdapter
from mcp_qa.adapters import MCPClientAdapter

# Wrap core adapter
core = CoreAdapter(fastmcp_client)
adapter = MCPClientAdapter(core)

# Call tool
result = await adapter.call_tool("get_organization", {"slug": "test"})
if result["success"]:
    print(f"Success in {result['duration_ms']}ms")

# Get statistics
stats = adapter.get_stats()
print(f"{stats['total_calls']} calls, avg {stats['avg_duration_ms']}ms")
```

### 3. MCPTunnelAdapter

Implements the `TunnelProvider` protocol for managing tunnels (ngrok, cloudflared).

**Purpose:** Exposes local MCP servers publicly for remote testing.

**Methods:**
- `get_public_url()` - Get public tunnel URL
- `get_local_url()` - Get local endpoint
- `is_active()` - Check if tunnel is running
- `start()` - Start tunnel
- `stop()` - Stop tunnel

**Example:**
```python
from mcp_qa.adapters import create_tunnel_adapter

# Create tunnel
adapter = create_tunnel_adapter(
    tunnel_type="ngrok",
    local_url="http://localhost:8000"
)

# Start tunnel
if await adapter.start():
    print(f"Tunnel active: {adapter.get_public_url()}")

# Stop when done
await adapter.stop()
```

### 4. MCPResourceAdapter

Wraps `ProcessMonitor` to implement the `ResourceMonitor` protocol.

**Purpose:** Monitor and track MCP server processes and resources.

**Methods:**
- `find_pid_by_port(port)` - Find process by port
- `get_process_info(pid)` - Get process details
- `register_process(name, port, pid, command_pattern)` - Register for monitoring
- `update_process(name)` - Update process info
- `check_health(name, health_url)` - Check process health

**Example:**
```python
from mcp_qa.adapters import create_resource_adapter

# Create monitor
adapter = create_resource_adapter()

# Register server process
info = adapter.register_process("mcp-server", port=8000)
print(f"Registered: {info.name} (PID: {info.pid})")

# Check health
health = adapter.check_health("mcp-server")
print(f"Health: {health.value}")

# Find process by port
pid = adapter.find_pid_by_port(8000)
if pid:
    info = adapter.get_process_info(pid)
    print(f"CPU: {info.cpu_percent}%, Memory: {info.memory_mb}MB")
```

### 5. MCPDatabaseAdapter

Wraps `DatabaseAdapter` to implement the `DatabaseProvider` protocol.

**Purpose:** Unified interface for database operations (Supabase, PostgreSQL, etc.).

**Methods:**
- `query(table, select, filters, order_by, limit, offset)` - Query records
- `get_single(table, select, filters)` - Get single record
- `insert(table, data, returning)` - Insert records
- `update(table, data, filters, returning)` - Update records
- `delete(table, filters)` - Delete records
- `set_access_token(token)` - Set RLS context

**Example:**
```python
from mcp_qa.utils.database_utils import SupabaseDatabaseAdapter
from mcp_qa.adapters import MCPDatabaseAdapter

# Create database adapter
db = SupabaseDatabaseAdapter()
adapter = MCPDatabaseAdapter(db)

# Set user context for RLS
adapter.set_access_token("user-jwt-token")

# Query records
users = await adapter.query(
    "users",
    filters={"active": True},
    order_by="created_at:desc",
    limit=10
)

# Insert record
new_user = await adapter.insert("users", {
    "name": "Test User",
    "email": "test@example.com"
})
```

## Factory Functions

Convenience functions for creating adapters:

```python
from mcp_qa.adapters import (
    create_oauth_adapter,
    create_resource_adapter,
    create_tunnel_adapter,
)

# Create OAuth adapter
oauth = create_oauth_adapter("https://api.example.com/mcp")

# Create resource monitor
monitor = create_resource_adapter()

# Create tunnel adapter
tunnel = create_tunnel_adapter(
    tunnel_type="manual",
    local_url="http://localhost:8000"
)
```

## Protocol Definitions

All adapters implement clearly defined protocols:

```python
from typing import Protocol

class OAuthCacheProvider(Protocol):
    def get_cache_path(self) -> Path: ...
    def is_token_cached(self) -> bool: ...
    def clear_cache(self) -> None: ...
    async def create_client(self) -> Client: ...

class ClientAdapter(Protocol):
    async def call_tool(self, tool_name: str, arguments: Optional[Dict]) -> Dict: ...
    async def list_tools(self) -> Dict: ...
    async def ping(self) -> Dict: ...
    def get_stats(self) -> Dict: ...

# ... and more (see widget_adapters.py for complete definitions)
```

## Integrated Example

Using multiple adapters together:

```python
from mcp_qa.adapters import (
    create_oauth_adapter,
    create_resource_adapter,
    create_tunnel_adapter,
    MCPClientAdapter
)

async def run_test_suite():
    # 1. Set up resource monitoring
    monitor = create_resource_adapter()
    monitor.register_process("test-server", port=8000)

    # 2. Set up tunnel (if needed)
    tunnel = create_tunnel_adapter(
        tunnel_type="manual",
        local_url="http://localhost:8000"
    )
    await tunnel.start()

    # 3. Create authenticated client
    oauth = create_oauth_adapter("http://localhost:8000/mcp")
    client = await oauth.create_client()

    # 4. Wrap client with adapter
    from mcp_qa.core.adapters import MCPClientAdapter as CoreAdapter
    adapter = MCPClientAdapter(CoreAdapter(client))

    # 5. Run tests
    result = await adapter.call_tool("health_check")

    # 6. Check server health
    health = monitor.check_health("test-server")
    print(f"Server health: {health.value}")

    # 7. Cleanup
    await tunnel.stop()
```

## Error Handling

All adapters include comprehensive error handling:

```python
# Adapters handle errors gracefully
result = await adapter.call_tool("invalid_tool")
if not result["success"]:
    print(f"Error: {result['error']}")
    # Error is logged, but doesn't raise exception

# You can still catch exceptions for critical errors
try:
    await adapter.create_client()
except Exception as e:
    print(f"Critical error: {e}")
```

## Logging

All adapters include built-in logging:

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Adapters will log all operations
adapter = create_oauth_adapter("https://api.example.com/mcp")
# DEBUG: Initialized OAuth cache adapter for https://api.example.com/mcp
# DEBUG: Token cached: True
```

## Testing

The adapters are designed to be easily testable:

```python
from unittest.mock import Mock, AsyncMock

# Mock the underlying client
mock_client = Mock()
mock_client.call_tool = AsyncMock(return_value={
    "success": True,
    "result": {"id": "123"}
})

# Use mock in adapter
adapter = MCPClientAdapter(mock_client)
result = await adapter.call_tool("test_tool")

assert result["success"] is True
```

See `tests/test_widget_adapters.py` for comprehensive test examples.

## Design Principles

1. **Protocol-First**: Define clear protocols that adapters must implement
2. **Composition**: Wrap existing objects rather than inheriting
3. **Error Handling**: Graceful degradation with detailed error messages
4. **Logging**: Comprehensive logging for debugging
5. **Type Safety**: Full type hints for better IDE support
6. **Documentation**: Detailed docstrings for all methods
7. **Testability**: Easy to mock and test

## Benefits

- **Consistency**: Unified interface across different MCP implementations
- **Flexibility**: Easy to swap implementations
- **Maintainability**: Changes to underlying implementations don't break tests
- **Testability**: Protocols enable easy mocking
- **Observability**: Built-in logging and statistics
- **Reliability**: Comprehensive error handling

## Files

- `widget_adapters.py` - Main adapter implementations
- `__init__.py` - Public API exports
- `README.md` - This file
- `../tests/test_widget_adapters.py` - Comprehensive tests
- `../../examples/widget_adapters_example.py` - Usage examples

## Contributing

When adding new adapters:

1. Define the protocol first
2. Implement the adapter class
3. Add comprehensive error handling
4. Include logging for debugging
5. Add type hints and docstrings
6. Create factory function (if appropriate)
7. Write tests
8. Update this README
9. Add usage examples

## License

Part of the mcp-QA testing framework.
