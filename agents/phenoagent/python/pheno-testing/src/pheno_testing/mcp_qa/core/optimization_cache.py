"""LRU cache for MCP responses with TTL support."""

import hashlib
import json
import time
from collections import OrderedDict
from dataclasses import dataclass
from threading import Lock
from typing import Any, Dict, Optional

from utils.logging_setup import get_logger

logger = get_logger(__name__)


@dataclass
class CacheEntry:
    """
    Cache entry with TTL support.
    """

    value: Any
    timestamp: float
    ttl: int

    def is_expired(self) -> bool:
        """
        Check if cache entry has expired.
        """
        return time.time() - self.timestamp > self.ttl


class ResponseCacheLayer:
    """
    LRU cache for MCP responses with TTL support.
    """

    def __init__(self, max_size: int = 1000, default_ttl: int = 60):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = Lock()
        self._hits = 0
        self._misses = 0

    def _generate_key(self, method: str, params: Dict[str, Any]) -> str:
        """
        Generate cache key from method and parameters.
        """
        key_data = json.dumps({"method": method, "params": params}, sort_keys=True)
        return hashlib.sha256(key_data.encode()).hexdigest()

    def get(self, method: str, params: Dict[str, Any]) -> Optional[Any]:
        """
        Get value from cache if exists and not expired.
        """
        key = self._generate_key(method, params)

        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if not entry.is_expired():
                    self._cache.move_to_end(key)
                    self._hits += 1
                    logger.debug(f"Cache hit for {method}")
                    return entry.value
                else:
                    del self._cache[key]

            self._misses += 1
            return None

    def set(
        self, method: str, params: Dict[str, Any], value: Any, ttl: Optional[int] = None
    ) -> None:
        """
        Store value in cache with TTL.
        """
        key = self._generate_key(method, params)
        ttl = ttl or self.default_ttl

        with self._lock:
            while len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)

            self._cache[key] = CacheEntry(value=value, timestamp=time.time(), ttl=ttl)

    def clear(self) -> None:
        """
        Clear all cache entries.
        """
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        """
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0
            return {
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": f"{hit_rate:.2f}%",
                "entries": len(self._cache),
                "max_size": self.max_size,
            }
