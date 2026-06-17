"""Worker fixtures for parallel test execution.

Provides worker-specific resources to avoid conflicts in pytest-xdist:
- Worker IDs
- Isolated ports
- Worker-specific databases
- Resource cleanup
"""

import os
import socket
import tempfile
from pathlib import Path

import pytest


@pytest.fixture(scope="function")
def worker_id(request) -> str:
    """Get current pytest-xdist worker ID.

    Returns "master" if running without xdist, or worker ID like "gw0", "gw1", etc.

    Usage:
        def test_worker_info(worker_id):
            print(f"Running in worker: {worker_id}")
            # Use worker_id to create worker-specific resources

    Returns:
        str: Worker ID or "master"
    """
    if hasattr(request.config, "workerinput"):
        return request.config.workerinput.get("workerid", "master")
    return "master"


@pytest.fixture(scope="function")
def worker_port(worker_id: str) -> int:
    """Get worker-specific port for parallel testing.

    Allocates a unique port for each worker to avoid port conflicts
    when running tests in parallel.

    Usage:
        async def test_server_on_port(worker_port):
            server = start_server(port=worker_port)
            # Test server on worker-specific port

    Returns:
        int: Unique port number for this worker
    """
    if worker_id == "master":
        return 8000

    # Extract worker number from ID (e.g., "gw0" -> 0)
    try:
        worker_num = int(worker_id.replace("gw", ""))
        base_port = 9000
        return base_port + worker_num
    except ValueError:
        # Fallback to hash-based port
        return 9000 + hash(worker_id) % 1000


@pytest.fixture(scope="function")
def worker_database(worker_id: str, tmp_path) -> str:
    """Get worker-specific database path.

    Creates isolated database for each worker to prevent conflicts
    in parallel test execution.

    Usage:
        def test_with_db(worker_database):
            conn = sqlite3.connect(worker_database)
            # Use worker-specific database

    Returns:
        str: Path to worker-specific database file
    """
    db_name = f"test_{worker_id}.db"
    db_path = tmp_path / db_name
    return str(db_path)


@pytest.fixture(scope="session", autouse=True)
def worker_cleanup(request):
    """Cleanup worker resources at end of test session.

    Automatically runs at the end of each worker's test session to clean up any leftover
    resources.

    This fixture is autouse=True, so it runs automatically.
    """
    # Setup phase
    if hasattr(request.config, "workerinput"):
        request.config.workerinput.get("workerid", "master")

    yield

    # Cleanup phase
    # Clean up temporary files, ports, etc. for this worker
    pass


def allocate_free_port() -> int:
    """Allocate a free port on the system.

    Useful for creating test servers without hardcoding ports.

    Returns:
        int: Available port number
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


def get_worker_database_path(db_name: str) -> str:
    """Get worker-specific database path.

    Args:
        db_name: Base name for the database file

    Returns:
        str: Worker-specific database path
    """
    worker_id = os.environ.get("PYTEST_XDIST_WORKER", "master")
    temp_dir = Path(tempfile.gettempdir())
    worker_db = temp_dir / f"{worker_id}_{db_name}"
    return str(worker_db)


def cleanup_worker_resources():
    """Clean up all worker-specific resources.

    Should be called at the end of test session to clean up temporary files, databases,
    etc. created by this worker.
    """
    worker_id = os.environ.get("PYTEST_XDIST_WORKER", "master")
    temp_dir = Path(tempfile.gettempdir())

    # Clean up worker-specific files
    for file in temp_dir.glob(f"{worker_id}_*"):
        try:
            file.unlink()
        except Exception:
            pass
