"""
Distributed cache for team-wide test data sharing.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional


class SharedCache:
    """
    Distributed cache for team-wide test data.
    """

    def __init__(self):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.locks: Dict[str, asyncio.Lock] = {}
        self.ttl: Dict[str, float] = {}

    def _get_lock(self, key: str) -> asyncio.Lock:
        """
        Get or create lock for a key.
        """
        if key not in self.locks:
            self.locks[key] = asyncio.Lock()
        return self.locks[key]

    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Set a value in the cache.
        """
        async with self._get_lock(key):
            self.cache[key] = {"value": value, "timestamp": time.time()}
            if ttl:
                self.ttl[key] = time.time() + ttl

    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.
        """
        async with self._get_lock(key):
            if key in self.ttl and time.time() > self.ttl[key]:
                self.cache.pop(key, None)
                self.ttl.pop(key, None)
                return None

            entry = self.cache.get(key)
            return entry["value"] if entry else None

    async def delete(self, key: str):
        """
        Delete a value from the cache.
        """
        async with self._get_lock(key):
            self.cache.pop(key, None)
            self.ttl.pop(key, None)

    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in the cache.
        """
        value = await self.get(key)
        return value is not None

    async def clear(self):
        """
        Clear all cache entries.
        """
        self.cache.clear()
        self.ttl.clear()

    async def get_all_keys(self) -> List[str]:
        """
        Get all cache keys.
        """
        current_time = time.time()
        expired = [k for k, exp in self.ttl.items() if current_time > exp]
        for key in expired:
            await self.delete(key)
        return list(self.cache.keys())

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        """
        return {
            "total_keys": len(self.cache),
            "with_ttl": len(self.ttl),
            "oldest_entry": min((e["timestamp"] for e in self.cache.values()), default=None),
        }
