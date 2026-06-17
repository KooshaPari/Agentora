"""
PostgreSQL database adapter using asyncpg.
"""

from __future__ import annotations

import os
from typing import Any

from .base import DatabaseAdapter


class PostgreSQLAdapter(DatabaseAdapter):
    """
    PostgreSQL adapter with connection pooling.
    """

    def __init__(
        self,
        dsn: str | None = None,
        host: str = "localhost",
        port: int = 5432,
        database: str = "postgres",
        user: str | None = None,
        password: str | None = None,
        min_pool_size: int = 10,
        max_pool_size: int = 20,
    ):
        """Initialize PostgreSQL adapter.

        Args:
            dsn: PostgreSQL DSN (optional, overrides other params)
            host: Database host
            port: Database port
            database: Database name
            user: Database user (defaults to env var)
            password: Database password (defaults to env var)
            min_pool_size: Minimum pool connections
            max_pool_size: Maximum pool connections
        """
        self._dsn = dsn or self._build_dsn(host, port, database, user, password)
        self._min_pool_size = min_pool_size
        self._max_pool_size = max_pool_size
        self._pool = None

    def _build_dsn(
        self, host: str, port: int, database: str, user: str | None, password: str | None,
    ) -> str:
        """Build PostgreSQL DSN.

        Args:
            host: Database host
            port: Database port
            database: Database name
            user: Database user
            password: Database password

        Returns:
            DSN string
        """
        user = user or os.getenv("POSTGRES_USER", "postgres")
        password = password or os.getenv("POSTGRES_PASSWORD", "")

        return f"postgresql://{user}:{password}@{host}:{port}/{database}"

    async def _get_pool(self):
        """
        Get connection pool, creating if needed.
        """
        if self._pool is None:
            try:
                import asyncpg

                self._pool = await asyncpg.create_pool(
                    self._dsn, min_size=self._min_pool_size, max_size=self._max_pool_size,
                )
            except ImportError:
                raise ImportError("asyncpg not installed. Install with: pip install asyncpg")

        return self._pool

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
        Execute a SELECT query.
        """
        pool = await self._get_pool()

        # Build query
        columns = select or "*"
        sql = f"SELECT {columns} FROM {table}"
        params = []

        # Add WHERE clause
        if filters:
            where_parts = []
            for i, (key, value) in enumerate(filters.items(), 1):
                where_parts.append(f"{key} = ${i}")
                params.append(value)
            sql += " WHERE " + " AND ".join(where_parts)

        # Add ORDER BY
        if order_by:
            parts = order_by.split(":")
            col = parts[0]
            direction = "DESC" if len(parts) > 1 and parts[1].lower() == "desc" else "ASC"
            sql += f" ORDER BY {col} {direction}"

        # Add LIMIT/OFFSET
        if limit:
            sql += f" LIMIT {limit}"
        if offset:
            sql += f" OFFSET {offset}"

        # Execute query
        async with pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [dict(row) for row in rows]

    async def get_single(
        self, table: str, filters: dict[str, Any], *, select: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Get a single row.
        """
        results = await self.query(table, select=select, filters=filters, limit=1)
        return results[0] if results else None

    async def insert(
        self,
        table: str,
        data: dict[str, Any] | list[dict[str, Any]],
        *,
        returning: str | None = None,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """
        Insert rows.
        """
        pool = await self._get_pool()
        is_single = isinstance(data, dict)
        rows = [data] if is_single else data

        if not rows:
            return [] if not is_single else {}

        # Build INSERT query
        columns = list(rows[0].keys())
        placeholders = ", ".join(f"${i+1}" for i in range(len(columns)))
        col_list = ", ".join(columns)

        sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"

        if returning:
            sql += f" RETURNING {returning}"
        else:
            sql += " RETURNING *"

        # Execute
        async with pool.acquire() as conn:
            if len(rows) == 1:
                values = [rows[0][col] for col in columns]
                row = await conn.fetchrow(sql, *values)
                result = dict(row) if row else {}
                return result if is_single else [result]
            # Batch insert
            results = []
            for row_data in rows:
                values = [row_data[col] for col in columns]
                row = await conn.fetchrow(sql, *values)
                if row:
                    results.append(dict(row))
            return results[0] if is_single else results

    async def update(
        self,
        table: str,
        filters: dict[str, Any],
        data: dict[str, Any],
        *,
        returning: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Update rows.
        """
        pool = await self._get_pool()

        # Build UPDATE query
        set_parts = []
        params = []
        param_num = 1

        for key, value in data.items():
            set_parts.append(f"{key} = ${param_num}")
            params.append(value)
            param_num += 1

        sql = f"UPDATE {table} SET {', '.join(set_parts)}"

        # Add WHERE clause
        if filters:
            where_parts = []
            for key, value in filters.items():
                where_parts.append(f"{key} = ${param_num}")
                params.append(value)
                param_num += 1
            sql += " WHERE " + " AND ".join(where_parts)

        if returning:
            sql += f" RETURNING {returning}"
        else:
            sql += " RETURNING *"

        # Execute
        async with pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [dict(row) for row in rows]

    async def delete(
        self, table: str, filters: dict[str, Any], *, returning: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Delete rows.
        """
        pool = await self._get_pool()

        sql = f"DELETE FROM {table}"
        params = []

        if filters:
            where_parts = []
            for i, (key, value) in enumerate(filters.items(), 1):
                where_parts.append(f"{key} = ${i}")
                params.append(value)
            sql += " WHERE " + " AND ".join(where_parts)

        if returning:
            sql += f" RETURNING {returning}"
        else:
            sql += " RETURNING *"

        async with pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [dict(row) for row in rows]

    async def upsert(
        self,
        table: str,
        data: dict[str, Any] | list[dict[str, Any]],
        *,
        conflict_columns: list[str] | None = None,
        returning: str | None = None,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """
        Insert or update rows (ON CONFLICT).
        """
        pool = await self._get_pool()
        is_single = isinstance(data, dict)
        rows = [data] if is_single else data

        if not rows:
            return [] if not is_single else {}

        # Build upsert query
        columns = list(rows[0].keys())
        placeholders = ", ".join(f"${i+1}" for i in range(len(columns)))
        col_list = ", ".join(columns)

        sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"

        # Add ON CONFLICT clause
        if conflict_columns:
            conflict_cols = ", ".join(conflict_columns)
            update_parts = [
                f"{col} = EXCLUDED.{col}" for col in columns if col not in conflict_columns
            ]
            sql += f" ON CONFLICT ({conflict_cols}) DO UPDATE SET {', '.join(update_parts)}"
        else:
            sql += " ON CONFLICT DO NOTHING"

        if returning:
            sql += f" RETURNING {returning}"
        else:
            sql += " RETURNING *"

        # Execute
        async with pool.acquire() as conn:
            if len(rows) == 1:
                values = [rows[0][col] for col in columns]
                row = await conn.fetchrow(sql, *values)
                result = dict(row) if row else {}
                return result if is_single else [result]
            results = []
            for row_data in rows:
                values = [row_data[col] for col in columns]
                row = await conn.fetchrow(sql, *values)
                if row:
                    results.append(dict(row))
            return results[0] if is_single else results

    async def execute(self, sql: str, params: list | dict | None = None) -> Any:
        """
        Execute raw SQL.
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            if params:
                if isinstance(params, dict):
                    # Named parameters - convert to positional
                    params_list = list(params.values())
                    return await conn.fetch(sql, *params_list)
                return await conn.fetch(sql, *params)
            return await conn.fetch(sql)

    async def count(self, table: str, filters: dict[str, Any] | None = None) -> int:
        """
        Count rows.
        """
        pool = await self._get_pool()

        sql = f"SELECT COUNT(*) FROM {table}"
        params = []

        if filters:
            where_parts = []
            for i, (key, value) in enumerate(filters.items(), 1):
                where_parts.append(f"{key} = ${i}")
                params.append(value)
            sql += " WHERE " + " AND ".join(where_parts)

        async with pool.acquire() as conn:
            row = await conn.fetchrow(sql, *params)
            return row[0] if row else 0

    async def close(self):
        """
        Close connection pool.
        """
        if self._pool:
            await self._pool.close()
            self._pool = None
