"""
Parallel Client Manager - Multiple Independent FastMCP Clients

Creates separate FastMCP client instances to enable true parallel execution
without lock contention.
"""

import asyncio
from typing import Dict, List, Optional

from fastmcp import Client
from fastmcp.client.auth import OAuth


class ParallelClientManager:
    """Manages multiple independent FastMCP clients for parallel execution.

    Each client has its own:
    - HTTP session
    - Auth context
    - Internal locks
    - Token storage

    This eliminates lock contention between workers.
    """

    def __init__(
        self,
        endpoint: str,
        client_name: str,
        num_clients: int,
        oauth_handler: Optional[callable] = None,
    ):
        """Initialize parallel client manager.

        Args:
            endpoint: MCP endpoint URL
            client_name: OAuth client name
            num_clients: Number of independent clients to create
            oauth_handler: Optional Playwright OAuth handler
        """
        self.endpoint = endpoint
        self.client_name = client_name
        self.num_clients = num_clients
        self.oauth_handler = oauth_handler

        self._clients: List[Client] = []
        self._available: asyncio.Queue = asyncio.Queue(maxsize=num_clients)
        self._lock = asyncio.Lock()
        self._initialized = False

    async def initialize(self):
        """Create and authenticate multiple independent clients.

        This is the key optimization:
        - First client: Full OAuth flow (10-30 seconds)
        - Remaining clients: Reuse cached token (instant!)
        """
        if self._initialized:
            return

        print(f"\n🔌 Creating {self.num_clients} independent MCP clients...")
        print("   This enables TRUE parallel execution without lock contention")

        # Create first client with full OAuth
        print(f"\n   Client 1/{self.num_clients}: Authenticating (may take 10-30s)...")
        first_client = await self._create_and_auth_client(client_id=0)

        if not first_client:
            raise RuntimeError("Failed to create first client")

        self._clients.append(first_client)
        await self._available.put(first_client)
        print("   ✅ Client 1 authenticated")

        # Now token is cached - remaining clients are instant!
        print(f"\n   Creating clients 2-{self.num_clients} (using cached token)...")

        remaining_tasks = []
        for i in range(1, self.num_clients):
            task = self._create_and_auth_client(client_id=i)
            remaining_tasks.append(task)

        # Create remaining clients in parallel (fast with cached token)
        remaining_clients = await asyncio.gather(*remaining_tasks, return_exceptions=True)

        for i, client in enumerate(remaining_clients, start=2):
            if isinstance(client, Exception):
                print(f"   ⚠️  Client {i} creation failed: {client}")
            elif client:
                self._clients.append(client)
                await self._available.put(client)

                if i % 5 == 0:  # Progress every 5 clients
                    print(f"   Created {i}/{self.num_clients} clients...")

        print(f"\n✅ Client pool ready: {len(self._clients)} independent authenticated clients")
        print("   Each client has its own session - NO lock contention!")

        self._initialized = True

    async def _create_and_auth_client(self, client_id: int) -> Optional[Client]:
        """Create and authenticate a single independent client.

        First client does full OAuth, rest reuse cached token.

        Args:
            client_id: Client identifier for logging

        Returns:
            Authenticated Client instance or None
        """
        try:
            # All clients share same OAuth cache (first client creates it)
            oauth = OAuth(
                mcp_url=self.endpoint,
                client_name=f"{self.client_name}",
            )

            # Create client
            client = Client(self.endpoint, auth=oauth)

            # Authenticate (first client = slow, rest = fast with cached token)
            await client.__aenter__()

            return client

        except Exception as e:
            print(f"   ❌ Failed to create client {client_id}: {e}")
            return None

    async def acquire(self, timeout: float = 30.0) -> Optional[Client]:
        """Acquire an available client from the pool.

        Args:
            timeout: Max seconds to wait

        Returns:
            Client instance or None
        """
        try:
            client = await asyncio.wait_for(self._available.get(), timeout=timeout)
            return client
        except asyncio.TimeoutError:
            print("⚠️  Timeout acquiring client (pool exhausted)")
            return None

    async def release(self, client: Client):
        """
        Return client to available pool.
        """
        await self._available.put(client)

    async def close_all(self):
        """
        Close all clients in pool.
        """
        print(f"\n🔌 Closing {len(self._clients)} client connections...")

        for client in self._clients:
            try:
                await client.__aexit__(None, None, None)
            except Exception as e:
                print(f"   ⚠️  Error closing client: {e}")

        self._clients.clear()
        print("✅ All clients closed")

    def get_stats(self) -> Dict[str, int]:
        """
        Get pool statistics.
        """
        return {
            "total_clients": len(self._clients),
            "available": self._available.qsize(),
            "in_use": len(self._clients) - self._available.qsize(),
            "max_clients": self.num_clients,
        }


__all__ = ["ParallelClientManager"]
