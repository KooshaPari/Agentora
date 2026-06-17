"""
Worker Client Pool - Multiple Independent MCP Clients for True Parallelization

Creates a pool of independent MCP client instances, each with its own
HTTP session, to enable true parallel test execution without bottlenecks.
"""

import asyncio
from typing import Any, Dict, List, Optional

try:
    import httpx

    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


class WorkerClientPool:
    """Manages pool of independent MCP clients for workers.

    Each worker gets its own client with dedicated HTTP session, eliminating the
    bottleneck of shared client state.
    """

    def __init__(self, endpoint: str, auth_headers: Dict[str, str], pool_size: int = 20):
        """Initialize worker client pool.

        Args:
            endpoint: MCP endpoint URL
            auth_headers: Authentication headers to use
            pool_size: Number of independent clients
        """
        self.endpoint = endpoint
        self.auth_headers = auth_headers
        self.pool_size = pool_size
        self._clients: List[httpx.AsyncClient] = []
        self._available: asyncio.Queue = asyncio.Queue(maxsize=pool_size)
        self._lock = asyncio.Lock()

    async def initialize(self):
        """
        Create pool of independent HTTP clients.
        """
        print(f"🔌 Creating {self.pool_size} independent MCP clients...")

        for i in range(self.pool_size):
            # Create independent HTTP client with its own session
            client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
                http2=True,  # Enable HTTP/2 for multiplexing
            )

            self._clients.append(client)
            await self._available.put(client)

            if (i + 1) % 5 == 0:
                print(f"   Created {i + 1}/{self.pool_size} clients...")

        print(f"✅ Client pool ready: {self.pool_size} independent HTTP sessions")

    async def acquire(self, timeout: float = 10.0) -> Optional[httpx.AsyncClient]:
        """
        Acquire client from pool.
        """
        try:
            return await asyncio.wait_for(self._available.get(), timeout=timeout)
        except asyncio.TimeoutError:
            print("⚠️  Timeout acquiring client from pool")
            return None

    async def release(self, client: httpx.AsyncClient):
        """
        Return client to pool.
        """
        await self._available.put(client)

    async def call_tool(
        self, client: httpx.AsyncClient, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call MCP tool using pooled client.

        Args:
            client: HTTP client from pool
            tool_name: MCP tool name
            arguments: Tool arguments

        Returns:
            Tool response
        """
        try:
            response = await client.post(
                self.endpoint,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {"name": tool_name, "arguments": arguments},
                },
                headers=self.auth_headers,
            )

            response.raise_for_status()
            data = response.json()

            return {"success": True, "response": data.get("result"), "error": None}

        except Exception as e:
            return {"success": False, "response": None, "error": str(e)}

    async def close_all(self):
        """
        Close all clients in pool.
        """
        for client in self._clients:
            await client.aclose()

        self._clients.clear()

    def get_stats(self) -> Dict[str, int]:
        """
        Get pool statistics.
        """
        return {
            "total_clients": len(self._clients),
            "available": self._available.qsize(),
            "in_use": self.pool_size - self._available.qsize(),
        }


__all__ = ["WorkerClientPool"]
