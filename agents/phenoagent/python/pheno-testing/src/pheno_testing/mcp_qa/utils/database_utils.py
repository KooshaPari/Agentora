"""Unified Database Utilities for MCP Projects.

Provides database connection management, query building, caching,
and RLS context for Supabase and other databases.

Usage:
    from pheno.testing.mcp_qa.utils.database_utils import DatabaseAdapter, QueryBuilder

    adapter = get_database_adapter()
    results = await adapter.query("users", filters={"active": True})
"""

from __future__ import annotations

import hashlib
import json
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

from pheno.testing.mcp_qa.utils.logging_utils import get_logger

logger = get_logger(__name__)


# ============================================================================
# Query Builder
# ============================================================================


class QueryFilter:
    """Fluent query filter builder.

    Example:
        filters = QueryFilter()
        filters.eq("status", "active").gt("created_at", "2024-01-01")
    """

    def __init__(self):
        self._filters: Dict[str, Any] = {}

    def eq(self, field: str, value: Any) -> QueryFilter:
        """
        Equal to.
        """
        self._filters[field] = value
        return self

    def neq(self, field: str, value: Any) -> QueryFilter:
        """
        Not equal to.
        """
        self._filters[field] = {"neq": value}
        return self

    def gt(self, field: str, value: Any) -> QueryFilter:
        """
        Greater than.
        """
        self._filters[field] = {"gt": value}
        return self

    def gte(self, field: str, value: Any) -> QueryFilter:
        """
        Greater than or equal.
        """
        self._filters[field] = {"gte": value}
        return self

    def lt(self, field: str, value: Any) -> QueryFilter:
        """
        Less than.
        """
        self._filters[field] = {"lt": value}
        return self

    def lte(self, field: str, value: Any) -> QueryFilter:
        """
        Less than or equal.
        """
        self._filters[field] = {"lte": value}
        return self

    def like(self, field: str, pattern: str) -> QueryFilter:
        """
        Like pattern (case-sensitive).
        """
        self._filters[field] = {"like": pattern}
        return self

    def ilike(self, field: str, pattern: str) -> QueryFilter:
        """
        Like pattern (case-insensitive).
        """
        self._filters[field] = {"ilike": pattern}
        return self

    def in_(self, field: str, values: List[Any]) -> QueryFilter:
        """
        In list.
        """
        self._filters[field] = {"in": values}
        return self

    def is_null(self, field: str) -> QueryFilter:
        """
        Is null.
        """
        self._filters[field] = None
        return self

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary.
        """
        return self._filters.copy()


# ============================================================================
# Query Cache
# ============================================================================


class QueryCache:
    """Simple in-memory query cache with TTL.

    Example:
        cache = QueryCache(ttl=30)
        cache.set("key", data)
        result = cache.get("key")
    """

    def __init__(self, ttl: int = 30, max_size: int = 1000):
        """Initialize cache.

        Args:
            ttl: Time-to-live in seconds
            max_size: Maximum number of cached items
        """
        self.ttl = ttl
        self.max_size = max_size
        self._cache: Dict[str, tuple[Any, float]] = {}

    def get(self, key: str) -> Optional[Any]:
        """
        Get cached value if still valid.
        """
        if key in self._cache:
            data, timestamp = self._cache[key]
            if time.time() - timestamp < self.ttl:
                return data
            else:
                del self._cache[key]
        return None

    def set(self, key: str, value: Any):
        """
        Cache value with current timestamp.
        """
        self._cache[key] = (value, time.time())

        # Limit cache size
        if len(self._cache) > self.max_size:
            # Remove oldest entries
            items = sorted(self._cache.items(), key=lambda x: x[1][1])
            for k, _ in items[: len(items) - self.max_size]:
                del self._cache[k]

    def invalidate(self, pattern: Optional[str] = None):
        """Invalidate cache entries.

        Args:
            pattern: If provided, only invalidate keys containing pattern
        """
        if pattern is None:
            self._cache.clear()
        else:
            keys_to_remove = [k for k in self._cache if pattern in k]
            for k in keys_to_remove:
                del self._cache[k]

    def clear(self):
        """
        Clear all cached entries.
        """
        self._cache.clear()

    @staticmethod
    def make_key(operation: str, **kwargs) -> str:
        """Generate cache key from operation and parameters.

        Args:
            operation: Operation name
            **kwargs: Operation parameters

        Returns:
            MD5 hash of operation + parameters
        """
        key_data = {"op": operation, **kwargs}
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_str.encode()).hexdigest()


# ============================================================================
# Database Adapter Base
# ============================================================================


class DatabaseAdapter(ABC):
    """Abstract base class for database adapters.

    Provides common interface for different database backends (Supabase, PostgreSQL,
    SQLite, etc.)
    """

    def __init__(self, cache_ttl: int = 30):
        """Initialize adapter.

        Args:
            cache_ttl: Cache time-to-live in seconds
        """
        self._cache = QueryCache(ttl=cache_ttl)
        self._access_token: Optional[str] = None

    def set_access_token(self, token: str):
        """Set user access token for RLS context.

        Args:
            token: User's JWT access token
        """
        self._access_token = token

    @abstractmethod
    async def query(
        self,
        table: str,
        *,
        select: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Execute a query on a table.
        """
        pass

    @abstractmethod
    async def get_single(
        self,
        table: str,
        *,
        select: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get a single record from a table.
        """
        pass

    @abstractmethod
    async def insert(
        self,
        table: str,
        data: Union[Dict[str, Any], List[Dict[str, Any]]],
        *,
        returning: Optional[str] = None,
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Insert one or more records.
        """
        pass

    @abstractmethod
    async def update(
        self,
        table: str,
        data: Dict[str, Any],
        filters: Dict[str, Any],
        *,
        returning: Optional[str] = None,
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Update records.
        """
        pass

    @abstractmethod
    async def delete(self, table: str, filters: Dict[str, Any]) -> int:
        """
        Delete records.
        """
        pass

    @abstractmethod
    async def count(self, table: str, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count records in a table.
        """
        pass


# ============================================================================
# Supabase Adapter
# ============================================================================


class SupabaseDatabaseAdapter(DatabaseAdapter):
    """Supabase database adapter with caching and RLS support.

    Example:
        adapter = SupabaseDatabaseAdapter()
        adapter.set_access_token(user_token)

        results = await adapter.query(
            "users",
            filters={"active": True},
            order_by="created_at:desc",
            limit=10
        )
    """

    def __init__(self, supabase_client=None, cache_ttl: int = 30):
        """Initialize Supabase adapter.

        Args:
            supabase_client: Supabase client instance (optional)
            cache_ttl: Cache time-to-live in seconds
        """
        super().__init__(cache_ttl)
        self._client = supabase_client

    def _get_client(self):
        """
        Get Supabase client with user's JWT for RLS context.
        """
        if self._client is not None:
            return self._client

        # Try to import and get client
        try:
            from db_kit.supabase_client import get_supabase

            return get_supabase(access_token=self._access_token)
        except ImportError:
            raise RuntimeError(
                "Supabase client not available. "
                "Either pass supabase_client to constructor or ensure "
                "supabase_client module is available."
            )

    def _apply_filters(self, query, filters: Optional[Dict[str, Any]]):
        """
        Apply filters to a Supabase query.
        """
        if not filters:
            return query

        for key, value in filters.items():
            if value is None:
                query = query.is_(key, None)
            elif isinstance(value, dict):
                # Handle operators
                for op, val in value.items():
                    if op == "eq":
                        query = query.eq(key, val)
                    elif op == "neq":
                        query = query.neq(key, val)
                    elif op == "gt":
                        query = query.gt(key, val)
                    elif op == "gte":
                        query = query.gte(key, val)
                    elif op == "lt":
                        query = query.lt(key, val)
                    elif op == "lte":
                        query = query.lte(key, val)
                    elif op == "like":
                        query = query.like(key, val)
                    elif op == "ilike":
                        query = query.ilike(key, val)
                    elif op == "in":
                        query = query.in_(key, val)
                    elif op == "not_in":
                        query = query.not_.in_(key, val)
            else:
                query = query.eq(key, value)

        return query

    async def query(
        self,
        table: str,
        *,
        select: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Execute a query on a table with caching.
        """
        # Check cache
        cache_key = QueryCache.make_key(
            "query",
            table=table,
            select=select,
            filters=filters,
            order_by=order_by,
            limit=limit,
            offset=offset,
        )
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            client = self._get_client()
            query = client.from_(table).select(select or "*")

            query = self._apply_filters(query, filters)

            if order_by:
                parts = order_by.split(":")
                col = parts[0]
                desc = len(parts) > 1 and parts[1].lower() == "desc"
                query = query.order(col, desc=desc)

            if offset:
                query = query.range(offset, (offset + limit - 1) if limit else None)
            elif limit:
                query = query.limit(limit)

            result = query.execute()
            data = getattr(result, "data", []) or []

            # Cache result
            self._cache.set(cache_key, data)

            return data

        except Exception as e:
            logger.error(f"Query failed on table {table}: {e}")
            raise

    async def get_single(
        self,
        table: str,
        *,
        select: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get a single record from a table.
        """
        try:
            client = self._get_client()
            query = client.from_(table).select(select or "*")

            query = self._apply_filters(query, filters)

            result = query.single().execute()
            return getattr(result, "data", None)

        except Exception as e:
            # Supabase raises exception for not found
            if hasattr(e, "code") and e.code == "PGRST116":
                return None
            logger.error(f"Get single failed on table {table}: {e}")
            raise

    async def insert(
        self,
        table: str,
        data: Union[Dict[str, Any], List[Dict[str, Any]]],
        *,
        returning: Optional[str] = None,
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Insert one or more records with cache invalidation.
        """
        try:
            client = self._get_client()
            query = client.from_(table).insert(data)
            result = query.execute()
            result_data = getattr(result, "data", None)

            if result_data is None:
                raise ValueError("Insert operation returned no data")

            # Invalidate cache
            self._cache.invalidate(table)

            # Return single dict or list
            if isinstance(data, dict):
                return result_data[0] if result_data else {}
            return result_data

        except Exception as e:
            logger.error(f"Insert failed on table {table}: {e}")
            raise

    async def update(
        self,
        table: str,
        data: Dict[str, Any],
        filters: Dict[str, Any],
        *,
        returning: Optional[str] = None,
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Update records with cache invalidation.
        """
        try:
            client = self._get_client()
            query = client.from_(table).update(data)
            query = self._apply_filters(query, filters)

            result = query.execute()
            result_data = getattr(result, "data", []) or []

            # Invalidate cache
            self._cache.invalidate(table)

            # Return single dict or list
            if len(result_data) == 1:
                return result_data[0]
            return result_data

        except Exception as e:
            logger.error(f"Update failed on table {table}: {e}")
            raise

    async def delete(self, table: str, filters: Dict[str, Any]) -> int:
        """
        Delete records with cache invalidation.
        """
        try:
            client = self._get_client()
            query = client.from_(table).delete()
            query = self._apply_filters(query, filters)

            result = query.execute()
            deleted_rows = getattr(result, "data", []) or []

            # Invalidate cache
            self._cache.invalidate(table)

            return len(deleted_rows)

        except Exception as e:
            logger.error(f"Delete failed on table {table}: {e}")
            raise

    async def count(self, table: str, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count records in a table with caching.
        """
        # Check cache
        cache_key = QueryCache.make_key("count", table=table, filters=filters)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            client = self._get_client()
            query = client.from_(table).select("*", count="exact", head=True)

            query = self._apply_filters(query, filters)

            result = query.execute()
            count = getattr(result, "count", 0) or 0

            # Cache result
            self._cache.set(cache_key, count)

            return count

        except Exception as e:
            logger.error(f"Count failed on table {table}: {e}")
            raise


__all__ = [
    "QueryFilter",
    "QueryCache",
    "DatabaseAdapter",
    "SupabaseDatabaseAdapter",
]
