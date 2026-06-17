"""
Database-focused provider extension.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from .base import CloudProvider

if TYPE_CHECKING:
    from ..types import Migration, PoolConfig


class DatabaseProvider(CloudProvider):
    """
    Extended cloud provider interface dedicated to database workloads.
    """

    @abstractmethod
    async def get_connection_string(self, resource_id: str) -> str: ...

    @abstractmethod
    async def execute_migration(self, resource_id: str, migration: Migration) -> None: ...

    @abstractmethod
    async def list_migrations(self, resource_id: str) -> list[Migration]: ...

    @abstractmethod
    async def create_database(self, resource_id: str, db_name: str) -> None: ...

    @abstractmethod
    async def list_databases(self, resource_id: str) -> list[str]: ...

    @abstractmethod
    async def set_connection_pooling(self, resource_id: str, config: PoolConfig) -> None: ...


__all__ = ["DatabaseProvider"]
