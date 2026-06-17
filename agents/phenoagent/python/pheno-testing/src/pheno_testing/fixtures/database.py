"""Database fixtures for testing.

Provides fixtures for both sync and async database testing with SQLAlchemy. Supports
PostgreSQL, SQLite, and other SQLAlchemy-compatible databases.
"""

from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager, contextmanager
from typing import Any

import pytest

try:
    from sqlalchemy import Engine, create_engine, event
    from sqlalchemy.ext.asyncio import (
        AsyncEngine,
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )
    from sqlalchemy.orm import Session, sessionmaker
    from sqlalchemy.pool import StaticPool

    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    Engine = Any
    AsyncEngine = Any
    Session = Any
    AsyncSession = Any


# ============================================================================
# Sync Database Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def db_engine() -> Generator[Engine, None, None]:
    """Create a database engine for testing.

    By default, creates an in-memory SQLite database.
    Override by setting DATABASE_URL environment variable.

    Example:
        def test_with_db(db_engine):
            # Use engine
            with db_engine.connect() as conn:
                result = conn.execute("SELECT 1")
    """
    if not SQLALCHEMY_AVAILABLE:
        pytest.skip("SQLAlchemy not installed")

    import os

    # Get database URL from environment or use in-memory SQLite
    database_url = os.getenv("DATABASE_URL", "sqlite:///:memory:")

    # Create engine with appropriate settings
    if "sqlite" in database_url:
        engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False,
        )
    else:
        engine = create_engine(database_url, echo=False)

    yield engine

    # Cleanup
    engine.dispose()


@pytest.fixture
def db_session(db_engine: Engine) -> Generator[Session, None, None]:
    """Create a database session for testing.

    Automatically rolls back changes after each test.

    Example:
        def test_with_session(db_session):
            user = User(name="Test")
            db_session.add(user)
            db_session.commit()
            # Changes rolled back after test
    """
    if not SQLALCHEMY_AVAILABLE:
        pytest.skip("SQLAlchemy not installed")

    # Create session factory
    SessionLocal = sessionmaker(bind=db_engine)
    session = SessionLocal()

    yield session

    # Rollback and close
    session.rollback()
    session.close()


@pytest.fixture
def db_transaction(db_engine: Engine) -> Generator[Session, None, None]:
    """Create a database session with transaction rollback.

    Uses nested transactions for complete isolation.
    All changes are rolled back after the test.

    Example:
        def test_with_transaction(db_transaction):
            # All changes rolled back automatically
            user = User(name="Test")
            db_transaction.add(user)
            db_transaction.commit()
    """
    if not SQLALCHEMY_AVAILABLE:
        pytest.skip("SQLAlchemy not installed")

    # Start a connection
    connection = db_engine.connect()

    # Begin a transaction
    transaction = connection.begin()

    # Create session bound to connection
    SessionLocal = sessionmaker(bind=connection)
    session = SessionLocal()

    # Enable nested transactions
    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, transaction):
        if transaction.nested and not transaction._parent.nested:
            session.begin_nested()

    session.begin_nested()

    yield session

    # Rollback everything
    session.close()
    transaction.rollback()
    connection.close()


# ============================================================================
# Async Database Fixtures
# ============================================================================


@pytest.fixture(scope="session")
async def async_db_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create an async database engine for testing.

    By default, creates an in-memory SQLite database with aiosqlite.
    Override by setting ASYNC_DATABASE_URL environment variable.

    Example:
        async def test_with_async_db(async_db_engine):
            async with async_db_engine.connect() as conn:
                result = await conn.execute("SELECT 1")
    """
    if not SQLALCHEMY_AVAILABLE:
        pytest.skip("SQLAlchemy async not installed")

    import os

    # Get database URL from environment or use in-memory SQLite
    database_url = os.getenv("ASYNC_DATABASE_URL", "sqlite+aiosqlite:///:memory:")

    # Create async engine
    if "sqlite" in database_url:
        engine = create_async_engine(
            database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False,
        )
    else:
        engine = create_async_engine(database_url, echo=False)

    yield engine

    # Cleanup
    await engine.dispose()


@pytest.fixture
async def async_db_session(async_db_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Create an async database session for testing.

    Automatically rolls back changes after each test.

    Example:
        async def test_with_async_session(async_db_session):
            user = User(name="Test")
            async_db_session.add(user)
            await async_db_session.commit()
            # Changes rolled back after test
    """
    if not SQLALCHEMY_AVAILABLE:
        pytest.skip("SQLAlchemy async not installed")

    # Create async session factory
    AsyncSessionLocal = async_sessionmaker(
        async_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()


# ============================================================================
# Helper Context Managers
# ============================================================================


@contextmanager
def temp_db_session(engine: Engine):
    """Context manager for temporary database session.

    Example:
        with temp_db_session(engine) as session:
            user = User(name="Test")
            session.add(user)
            session.commit()
    """
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@asynccontextmanager
async def temp_async_db_session(engine: AsyncEngine):
    """Context manager for temporary async database session.

    Example:
        async with temp_async_db_session(engine) as session:
            user = User(name="Test")
            session.add(user)
            await session.commit()
    """
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


__all__ = [
    "async_db_engine",
    "async_db_session",
    "db_engine",
    "db_session",
    "db_transaction",
    "temp_async_db_session",
    "temp_db_session",
]
