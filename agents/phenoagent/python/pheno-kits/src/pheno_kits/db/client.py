"""
Main Database client interface with tenant context support.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from .adapters.neon import NeonAdapter
from .adapters.postgres import PostgreSQLAdapter
from .adapters.supabase import SupabaseAdapter

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from .adapters.base import DatabaseAdapter


class Database:
    """
    Universal database client with tenant context and RLS support.
    """

    def __init__(self, adapter: DatabaseAdapter):
        """Initialize database client.

        Args:
            adapter: Database adapter implementation
        """
        self.adapter = adapter
        self._tenant_id: str | None = None

    @classmethod
    def supabase(cls, access_token: str | None = None) -> Database:
        """Create a database client with Supabase adapter.

        Args:
            access_token: User JWT for RLS context

        Returns:
            Database instance
        """
        adapter = SupabaseAdapter(access_token=access_token)
        return cls(adapter=adapter)

    @classmethod
    def postgres(
        cls,
        dsn: str | None = None,
        host: str = "localhost",
        port: int = 5432,
        database: str = "postgres",
        **kwargs,
    ) -> Database:
        """Create a database client with PostgreSQL adapter.

        Args:
            dsn: PostgreSQL DSN (optional)
            host: Database host
            port: Database port
            database: Database name
            **kwargs: Additional connection options

        Returns:
            Database instance
        """
        adapter = PostgreSQLAdapter(dsn=dsn, host=host, port=port, database=database, **kwargs)
        return cls(adapter=adapter)

    @classmethod
    def neon(
        cls,
        connection_string: str | None = None,
        api_key: str | None = None,
        project_id: str | None = None,
        **kwargs,
    ) -> Database:
        """Create a database client with Neon adapter.

        Neon is a serverless PostgreSQL platform with database branching support.

        Args:
            connection_string: Neon connection string (from dashboard)
            api_key: Neon API key for management operations
            project_id: Neon project ID
            **kwargs: Additional connection options

        Returns:
            Database instance

        Example:
            ```python
            # Using environment variables
            db = Database.neon()

            # With explicit credentials
            db = Database.neon(
                connection_string="postgresql://...",
                api_key="neon_api_key",
                project_id="project_id"
            )
            ```
        """
        adapter = NeonAdapter(
            connection_string=connection_string, api_key=api_key, project_id=project_id, **kwargs,
        )
        return cls(adapter=adapter)

    def set_access_token(self, token: str):
        """Set user's access token for RLS context.

        Args:
            token: JWT access token
        """
        self.adapter.set_access_token(token)

    @asynccontextmanager
    async def tenant_context(self, tenant_id: str) -> AsyncIterator[Database]:
        """Context manager for tenant-scoped operations.

        Args:
            tenant_id: Tenant identifier

        Yields:
            Database instance with tenant context

        Example:
            async with db.tenant_context("org_123") as tenant_db:
                users = await tenant_db.query("users", filters={"active": True})
        """
        old_tenant_id = self._tenant_id
        self._tenant_id = tenant_id
        try:
            yield self
        finally:
            self._tenant_id = old_tenant_id

    def _add_tenant_filter(self, filters: dict[str, Any] | None) -> dict[str, Any]:
        """
        Add tenant_id filter if in tenant context.
        """
        if self._tenant_id:
            filters = filters or {}
            filters["tenant_id"] = self._tenant_id
        return filters or {}

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
        """Execute a query on a table.

        Args:
            table: Table name
            select: Columns to select (defaults to "*")
            filters: WHERE conditions
            order_by: ORDER BY clause
            limit: LIMIT clause
            offset: OFFSET clause

        Returns:
            List of matching records
        """
        filters = self._add_tenant_filter(filters)
        return await self.adapter.query(
            table, select=select, filters=filters, order_by=order_by, limit=limit, offset=offset,
        )

    async def get_single(
        self, table: str, *, select: str | None = None, filters: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Get a single record from a table.

        Args:
            table: Table name
            select: Columns to select
            filters: WHERE conditions

        Returns:
            Single record or None if not found
        """
        filters = self._add_tenant_filter(filters)
        return await self.adapter.get_single(table, select=select, filters=filters)

    async def insert(
        self,
        table: str,
        data: dict[str, Any] | list[dict[str, Any]],
        *,
        returning: str | None = None,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Insert one or more records.

        Args:
            table: Table name
            data: Record(s) to insert
            returning: Columns to return

        Returns:
            Inserted record(s)
        """
        # Add tenant_id to data if in tenant context
        if self._tenant_id:
            if isinstance(data, dict):
                data["tenant_id"] = self._tenant_id
            else:
                for record in data:
                    record["tenant_id"] = self._tenant_id

        return await self.adapter.insert(table, data, returning=returning)

    async def update(
        self,
        table: str,
        data: dict[str, Any],
        filters: dict[str, Any],
        *,
        returning: str | None = None,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Update records.

        Args:
            table: Table name
            data: Updates to apply
            filters: WHERE conditions
            returning: Columns to return

        Returns:
            Updated record(s)
        """
        filters = self._add_tenant_filter(filters)
        return await self.adapter.update(table, data, filters, returning=returning)

    async def delete(self, table: str, filters: dict[str, Any]) -> int:
        """Delete records.

        Args:
            table: Table name
            filters: WHERE conditions

        Returns:
            Number of deleted records
        """
        filters = self._add_tenant_filter(filters)
        return await self.adapter.delete(table, filters)

    async def count(self, table: str, filters: dict[str, Any] | None = None) -> int:
        """Count records in a table.

        Args:
            table: Table name
            filters: WHERE conditions

        Returns:
            Record count
        """
        filters = self._add_tenant_filter(filters)
        return await self.adapter.count(table, filters)
