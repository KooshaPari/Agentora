"""
pheno.testing - Comprehensive testing utilities

Provides fixtures, factories, mocking utilities, and pytest plugins for:
- Async testing
- Database testing
- HTTP testing
- Factory patterns
- Test markers
- Assertion helpers

Migrated from test-kit into pheno namespace.

Usage:
    # Database fixtures
    from pheno.testing import db_session, async_db_session

    def test_database(db_session):
        # Use database session
        pass

    # HTTP fixtures
    from pheno.testing import http_client, async_http_client

    async def test_api(async_http_client):
        response = await async_http_client.get("/api/users")
        assert response.status_code == 200

    # Factories
    from pheno.testing import BaseFactory, create_factory

    class UserFactory(BaseFactory):
        name = "Test User"
        email = "test@example.com"

    user = UserFactory.create()

    # Markers
    from pheno.testing import slow, integration, unit

    @slow
    def test_slow_operation():
        pass

    @integration
    def test_integration():
        pass

    # Utilities
    from pheno.testing import assert_eventually, wait_for, capture_logs

    async def test_eventually():
        await assert_eventually(lambda: some_condition(), timeout=5.0)
"""

from __future__ import annotations

__version__ = "0.1.0"

# Import factories
from .factories import (
    AsyncFactory,
    BaseFactory,
    create_factory,
)

# Import fixtures
from .fixtures import core as fixtures_core
from .fixtures import tui as fixtures_tui
from .fixtures.async_helpers import async_context, async_timeout, event_loop
from .fixtures.database import (
    async_db_engine,
    async_db_session,
    db_engine,
    db_session,
    db_transaction,
)
from .fixtures.http import (
    async_http_client,
    http_client,
    mock_http_response,
    mock_http_server,
)

# Import markers
from .markers import (
    db,
    http,
    integration,
    slow,
    unit,
)

# Import utilities
from .utils import (
    assert_eventually,
    capture_logs,
    temp_env,
    wait_for,
)

__all__ = [
    "AsyncFactory",
    # Factories
    "BaseFactory",
    # Version
    "__version__",
    # Utilities
    "assert_eventually",
    "async_context",
    "async_db_engine",
    "async_db_session",
    "async_http_client",
    "async_timeout",
    "capture_logs",
    "create_factory",
    "db",
    # Database fixtures
    "db_engine",
    "db_session",
    "db_transaction",
    # Async fixtures
    "event_loop",
    # Fixture modules
    "fixtures_core",
    "fixtures_tui",
    "http",
    # HTTP fixtures
    "http_client",
    "integration",
    "mock_http_response",
    "mock_http_server",
    # Markers
    "slow",
    "temp_env",
    "unit",
    "wait_for",
]
