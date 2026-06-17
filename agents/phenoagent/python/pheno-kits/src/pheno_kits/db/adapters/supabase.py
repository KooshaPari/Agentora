"""
Supabase database adapter with RLS support.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any

from .base import DatabaseAdapter


class SupabaseAdapter(DatabaseAdapter):
    """
    Supabase-based database adapter with RLS and caching.
    """

    def __init__(self, client=None, access_token: str | None = None, cache_ttl: int = 30):
        """Initialize Supabase adapter.

        Args:
            client: Supabase client instance (optional, will auto-initialize)
            access_token: User JWT for RLS context
            cache_ttl: Cache TTL in seconds (default: 30)
        """
        self._client = client
        self._access_token = access_token
        self._cache_ttl = cache_ttl
        self._query_cache: dict[str, tuple[Any, float]] = {}

    def set_access_token(self, token: str):
        """
        Set user's access token for RLS context.
        """
        self._access_token = token
        self._query_cache.clear()  # Invalidate cache when token changes

    def _get_client(self):
        """
        Get Supabase client with user's JWT for RLS.
        """
        if self._client is None:
            try:
                from supabase import create_client

                url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
                key = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
                if not url or not key:
                    raise ValueError(
                        "Missing NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY",
                    )
                self._client = create_client(url, key)
            except ImportError:
                raise ImportError("supabase-py not installed. Install with: pip install supabase")

        # Apply access token if available
        if self._access_token and hasattr(self._client, "auth"):
            self._client.auth.set_session(self._access_token)

        return self._client

    def _get_cache_key(self, operation: str, **kwargs) -> str:
        """
        Generate cache key for operation.
        """
        key_data = {"op": operation, **kwargs}
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()

    def _get_cached(self, cache_key: str) -> Any | None:
        """
        Get cached result if still valid.
        """
        if cache_key in self._query_cache:
            data, timestamp = self._query_cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                return data
            del self._query_cache[cache_key]
        return None

    def _set_cache(self, cache_key: str, data: Any):
        """
        Cache result with timestamp.
        """
        self._query_cache[cache_key] = (data, time.time())
        # Limit cache size to prevent memory issues
        if len(self._query_cache) > 1000:
            self._query_cache.clear()

    def _apply_filters(self, query, filters: dict[str, Any] | None):
        """
        Apply filters to a Supabase query.
        """
        if not filters:
            return query

        for key, value in filters.items():
            if value is None:
                query = query.is_(key, None)
            elif isinstance(value, dict):
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
        select: str | None = None,
        filters: dict[str, Any] | None = None,
        order_by: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Execute a SELECT query on a table with caching.
        """
        # Check cache for read-only queries
        cache_key = self._get_cache_key(
            "query",
            table=table,
            select=select,
            filters=filters,
            order_by=order_by,
            limit=limit,
            offset=offset,
        )
        cached = self._get_cached(cache_key)
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

            # Cache the result
            self._set_cache(cache_key, data)

            return data

        except Exception as e:
            raise RuntimeError(f"Failed to query table {table}: {e}")

    async def get_single(
        self, table: str, filters: dict[str, Any], *, select: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Get a single row matching filters.
        """
        try:
            client = self._get_client()
            query = client.from_(table).select(select or "*")
            query = self._apply_filters(query, filters)
            query = query.limit(1).single()

            result = query.execute()
            return getattr(result, "data", None)

        except Exception:
            return None

    async def insert(
        self,
        table: str,
        data: dict[str, Any] | list[dict[str, Any]],
        *,
        returning: str | None = None,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """
        Insert one or more rows.
        """
        try:
            client = self._get_client()
            query = client.from_(table).insert(data)

            result = query.execute()
            inserted = getattr(result, "data", [])

            return inserted[0] if isinstance(data, dict) else inserted

        except Exception as e:
            raise RuntimeError(f"Failed to insert into table {table}: {e}")

    async def update(
        self,
        table: str,
        filters: dict[str, Any],
        data: dict[str, Any],
        *,
        returning: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Update rows matching filters.
        """
        try:
            client = self._get_client()
            query = client.from_(table).update(data)
            query = self._apply_filters(query, filters)

            result = query.execute()
            return getattr(result, "data", []) or []

        except Exception as e:
            raise RuntimeError(f"Failed to update table {table}: {e}")

    async def delete(
        self, table: str, filters: dict[str, Any], *, returning: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Delete rows matching filters.
        """
        try:
            client = self._get_client()
            query = client.from_(table).delete()
            query = self._apply_filters(query, filters)

            result = query.execute()
            return getattr(result, "data", []) or []

        except Exception as e:
            raise RuntimeError(f"Failed to delete from table {table}: {e}")

    async def upsert(
        self,
        table: str,
        data: dict[str, Any] | list[dict[str, Any]],
        *,
        conflict_columns: list[str] | None = None,
        returning: str | None = None,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """
        Insert or update rows.
        """
        try:
            client = self._get_client()
            query = client.from_(table).upsert(data)

            result = query.execute()
            upserted = getattr(result, "data", [])

            return upserted[0] if isinstance(data, dict) else upserted

        except Exception as e:
            raise RuntimeError(f"Failed to upsert into table {table}: {e}")

    async def execute(self, sql: str, params: list | dict | None = None) -> Any:
        """
        Execute raw SQL query.
        """
        try:
            client = self._get_client()
            result = client.rpc("exec_sql", {"query": sql, "params": params or {}})
            return getattr(result, "data", None)

        except Exception as e:
            raise RuntimeError(f"Failed to execute SQL: {e}")

    async def count(self, table: str, filters: dict[str, Any] | None = None) -> int:
        """
        Count rows matching filters.
        """
        try:
            client = self._get_client()
            query = client.from_(table).select("*", count="exact")
            query = self._apply_filters(query, filters)

            result = query.execute()
            return getattr(result, "count", 0)

        except Exception as e:
            raise RuntimeError(f"Failed to count rows in table {table}: {e}")
