"""
DB-Kit: Universal database abstraction with RLS and multi-tenancy.

This kit provides a unified interface for working with multiple database backends:
- Supabase (PostgreSQL with built-in auth, storage, and realtime)
- PostgreSQL (direct connections)
- Neon (serverless PostgreSQL)

Features:
- Adapter pattern for multiple backends
- Connection pooling (sync and async)
- Row-level security (RLS) support
- Multi-tenancy patterns
- Realtime subscriptions
- Storage abstractions
- Migration management
- Query builders
- Vector/embeddings support
"""

from .adapters.base import DatabaseAdapter
from .adapters.neon import NeonAdapter
from .adapters.postgres import PostgreSQLAdapter
from .adapters.supabase import SupabaseAdapter

# Core database client and adapters
from .client import Database

# Migrations
from .migrations import (
    Migration,
    MigrationEngine,
    MigrationStatus,
)

# Connection pooling
from .pooling import (
    AsyncConnectionPool,
    ConnectionPoolConfig,
    ConnectionPoolManager,
    ConnectionStats,
    SyncConnectionPool,
    cleanup_all_pools,
    get_pool_manager,
    get_provider_pool,
)

# Query builders - QueryBuilder is not implemented yet
# from .query import QueryBuilder
# Realtime
from .realtime import RealtimeAdapter, SupabaseRealtimeAdapter

# Storage
from .storage import StorageAdapter, SupabaseStorageAdapter

# Supabase client utilities
from .supabase_client import MissingSupabaseConfig, get_supabase

# Multi-tenancy
from .tenancy import TenancyAdapter

# Vector/embeddings support
from .vector import VectorAdapter

__version__ = "0.1.0"
__kit_name__ = "db"

__all__ = [
    # Connection pooling
    "AsyncConnectionPool",
    "ConnectionPoolConfig",
    "ConnectionPoolManager",
    "ConnectionStats",
    # Core
    "Database",
    "DatabaseAdapter",
    # Migrations
    "Migration",
    "MigrationEngine",
    "MigrationStatus",
    "MissingSupabaseConfig",
    "NeonAdapter",
    "PostgreSQLAdapter",
    # Realtime
    "RealtimeAdapter",
    # Storage
    "StorageAdapter",
    "SupabaseAdapter",
    "SupabaseRealtimeAdapter",
    "SupabaseStorageAdapter",
    "SyncConnectionPool",
    # Multi-tenancy
    "TenancyAdapter",
    # Query builders - QueryBuilder is not implemented yet
    # "QueryBuilder",
    # Vector/embeddings
    "VectorAdapter",
    "cleanup_all_pools",
    "get_pool_manager",
    "get_provider_pool",
    # Supabase utilities
    "get_supabase",
]
