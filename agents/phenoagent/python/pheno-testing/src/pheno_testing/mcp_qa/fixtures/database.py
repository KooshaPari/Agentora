"""Database fixtures for MCP-QA testing framework.

Provides database isolation for parallel testing:
- Worker-specific databases
- Database pools
- Temporary test databases
"""

import sqlite3
import tempfile

import pytest


@pytest.fixture(scope="function")
def isolated_database(tmp_path) -> str:
    """Worker-specific database for parallel test isolation.

    Each test gets a fresh database file, ensuring complete isolation
    between tests. Database is automatically cleaned up after test.

    Usage:
        def test_database_operations(isolated_database):
            conn = sqlite3.connect(isolated_database)
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE test (id INTEGER)")
            conn.close()

    Returns:
        str: Path to isolated database file
    """
    db_path = tmp_path / "test.db"
    yield str(db_path)

    # Cleanup
    if db_path.exists():
        try:
            db_path.unlink()
        except Exception:
            pass


@pytest.fixture(scope="session")
async def db_pool():
    """Database connection pool for parallel testing.

    Maintains a pool of database connections that can be shared
    across tests, reducing connection overhead.

    Usage:
        async def test_with_pool(db_pool):
            async with db_pool.acquire() as conn:
                cursor = await conn.cursor()
                await cursor.execute("SELECT 1")

    Yields:
        DatabasePool: Connection pool manager
    """

    class DatabasePool:
        def __init__(self, max_size: int = 10):
            self.max_size = max_size
            self.connections = []
            self.available = []

        async def acquire(self):
            """
            Acquire connection from pool.
            """
            if self.available:
                return self.available.pop()

            if len(self.connections) < self.max_size:
                # Create new connection
                db_path = tempfile.mktemp(suffix=".db")
                conn = sqlite3.connect(db_path)
                self.connections.append(conn)
                return conn

            # Wait for available connection
            # In real implementation, would use asyncio.Queue
            return None

        async def release(self, conn):
            """
            Release connection back to pool.
            """
            self.available.append(conn)

        async def close_all(self):
            """
            Close all connections.
            """
            for conn in self.connections:
                conn.close()
            self.connections.clear()
            self.available.clear()

    pool = DatabasePool()
    try:
        yield pool
    finally:
        await pool.close_all()


@pytest.fixture
def test_database(tmp_path):
    """Pre-configured test database with sample data.

    Creates a database with common tables and sample data for testing.
    Useful for tests that need realistic database state.

    Usage:
        def test_query(test_database):
            conn = sqlite3.connect(test_database["path"])
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users")
            users = cursor.fetchall()
            assert len(users) > 0

    Returns:
        Dict containing:
            - path: Database file path
            - schema: Database schema info
            - sample_data: Sample data info
    """
    db_path = tmp_path / "test_data.db"

    # Create database with sample schema
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create sample tables
    cursor.execute(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE entities (
            id INTEGER PRIMARY KEY,
            type TEXT NOT NULL,
            data TEXT
        )
    """
    )

    # Insert sample data
    cursor.execute(
        "INSERT INTO users (name, email) VALUES (?, ?)", ("Test User", "test@example.com")
    )

    cursor.execute(
        "INSERT INTO entities (type, data) VALUES (?, ?)", ("organization", '{"name": "Test Org"}')
    )

    conn.commit()
    conn.close()

    config = {
        "path": str(db_path),
        "schema": {
            "tables": ["users", "entities"],
        },
        "sample_data": {
            "users": 1,
            "entities": 1,
        },
    }

    yield config

    # Cleanup
    if db_path.exists():
        db_path.unlink()
