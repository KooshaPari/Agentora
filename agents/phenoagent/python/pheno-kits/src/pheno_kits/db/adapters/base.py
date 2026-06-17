"""
Abstract adapter interface for database operations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class DatabaseAdapter(ABC):
    """
    Abstract interface for database adapters.
    """

    @abstractmethod
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
        """Execute a SELECT query on a table.

        Args:
            table: Table name
            select: Columns to select (default: "*")
            filters: Filter conditions
            order_by: Order by clause (e.g., "created_at:desc")
            limit: Maximum rows to return
            offset: Number of rows to skip

        Returns:
            List of row dictionaries
        """

    @abstractmethod
    async def get_single(
        self, table: str, filters: dict[str, Any], *, select: str | None = None,
    ) -> dict[str, Any] | None:
        """Get a single row matching filters.

        Args:
            table: Table name
            filters: Filter conditions
            select: Columns to select (default: "*")

        Returns:
            Row dictionary or None if not found
        """

    @abstractmethod
    async def insert(
        self,
        table: str,
        data: dict[str, Any] | list[dict[str, Any]],
        *,
        returning: str | None = None,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Insert one or more rows.

        Args:
            table: Table name
            data: Row data (single dict or list of dicts)
            returning: Columns to return (default: "*")

        Returns:
            Inserted row(s)
        """

    @abstractmethod
    async def update(
        self,
        table: str,
        filters: dict[str, Any],
        data: dict[str, Any],
        *,
        returning: str | None = None,
    ) -> list[dict[str, Any]]:
        """Update rows matching filters.

        Args:
            table: Table name
            filters: Filter conditions
            data: Update data
            returning: Columns to return (default: "*")

        Returns:
            Updated rows
        """

    @abstractmethod
    async def delete(
        self, table: str, filters: dict[str, Any], *, returning: str | None = None,
    ) -> list[dict[str, Any]]:
        """Delete rows matching filters.

        Args:
            table: Table name
            filters: Filter conditions
            returning: Columns to return (default: "*")

        Returns:
            Deleted rows
        """

    @abstractmethod
    async def upsert(
        self,
        table: str,
        data: dict[str, Any] | list[dict[str, Any]],
        *,
        conflict_columns: list[str] | None = None,
        returning: str | None = None,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Insert or update rows.

        Args:
            table: Table name
            data: Row data (single dict or list of dicts)
            conflict_columns: Columns to check for conflicts
            returning: Columns to return (default: "*")

        Returns:
            Upserted row(s)
        """

    @abstractmethod
    async def execute(self, sql: str, params: list | dict | None = None) -> Any:
        """Execute raw SQL query.

        Args:
            sql: SQL query string
            params: Query parameters

        Returns:
            Query result
        """

    @abstractmethod
    async def count(self, table: str, filters: dict[str, Any] | None = None) -> int:
        """Count rows matching filters.

        Args:
            table: Table name
            filters: Filter conditions

        Returns:
            Row count
        """
