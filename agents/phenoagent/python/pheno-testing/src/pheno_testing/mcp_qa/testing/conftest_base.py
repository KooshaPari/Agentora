"""Base Pytest Configuration for MCP Projects.

Provides reusable pytest fixtures, hooks, and configuration that can be imported into
project conftest.py files.

Usage in project conftest.py:     from pheno.testing.mcp_qa.testing.conftest_base import
*

# Add project-specific fixtures below
"""

import asyncio
import os
from pathlib import Path
from typing import Generator

import pytest

# ============================================================================
# Pytest Configuration
# ============================================================================


def pytest_configure(config):
    """
    Configure pytest with MCP-specific markers and settings.
    """
    # Register custom markers
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
    config.addinivalue_line("markers", "mcp: marks tests that require MCP server")
    config.addinivalue_line("markers", "oauth: marks tests that require OAuth authentication")
    config.addinivalue_line("markers", "db: marks tests that require database access")


# ============================================================================
# Event Loop Configuration
# ============================================================================


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests.

    Provides a session-scoped event loop that's reused across all async tests.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Environment Configuration
# ============================================================================


@pytest.fixture(scope="session")
def test_env() -> dict:
    """Provide test environment configuration.

    Returns:
        Dict with common test environment variables
    """
    return {
        "TEST_MODE": "true",
        "CI": os.getenv("CI", "false"),
        "DEBUG": os.getenv("DEBUG", "false"),
    }


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Get project root directory.

    Returns:
        Path to project root
    """
    # Try to find project root by looking for common markers
    current = Path.cwd()
    for parent in [current] + list(current.parents):
        if (parent / "pyproject.toml").exists() or (parent / "setup.py").exists():
            return parent
    return current


@pytest.fixture(scope="session")
def sdk_path() -> Path:
    """Get pheno-SDK path.

    Returns:
        Path to pheno-SDK directory
    """
    # Assuming SDK is at ../../pheno-sdk relative to project
    project = Path.cwd()
    sdk = project.parent.parent / "pheno-sdk"
    if sdk.exists():
        return sdk
    # Fallback: try to find it
    for parent in project.parents:
        sdk_candidate = parent / "pheno-sdk"
        if sdk_candidate.exists():
            return sdk_candidate
    raise FileNotFoundError("Could not locate pheno-SDK directory")


# ============================================================================
# Test Data Fixtures
# ============================================================================


@pytest.fixture
def sample_test_data() -> dict:
    """Provide sample test data.

    Returns:
        Dict with common test data
    """
    return {
        "test_string": "test_value",
        "test_int": 42,
        "test_list": [1, 2, 3],
        "test_dict": {"key": "value"},
    }


@pytest.fixture
def temp_test_file(tmp_path) -> Path:
    """Create temporary test file.

    Args:
        tmp_path: Pytest's tmp_path fixture

    Returns:
        Path to temporary file
    """
    test_file = tmp_path / "test_file.txt"
    test_file.write_text("test content")
    return test_file


# ============================================================================
# Logging Configuration
# ============================================================================


@pytest.fixture(scope="session", autouse=True)
def configure_test_logging():
    """Configure logging for tests.

    Reduces noise from third-party libraries during tests.
    """
    import logging

    # Quiet noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("fastmcp").setLevel(logging.WARNING)
    logging.getLogger("mcp").setLevel(logging.WARNING)

    # Set root logger to INFO
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


# ============================================================================
# Test Collection Hooks
# ============================================================================


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers and skip conditions.

    Args:
        config: Pytest config
        items: Collected test items
    """
    for item in items:
        # Add markers based on test path/name
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)

        # Mark slow tests
        if "slow" in item.name or "comprehensive" in item.name:
            item.add_marker(pytest.mark.slow)


# ============================================================================
# Session Management
# ============================================================================


@pytest.fixture(scope="session")
def session_id() -> str:
    """Generate unique session ID for test run.

    Returns:
        Unique session identifier
    """
    import time

    return f"test_session_{int(time.time())}"


# ============================================================================
# Cleanup Hooks
# ============================================================================


@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Cleanup after each test.

    Runs after every test to ensure clean state.
    """
    yield
    # Cleanup logic here (if needed)
    pass


# ============================================================================
# Skip Conditions
# ============================================================================


def requires_env_var(var_name: str):
    """Decorator to skip test if environment variable is not set.

    Usage:
        @requires_env_var("API_KEY")
        def test_api():
            pass

    Args:
        var_name: Environment variable name

    Returns:
        Pytest skip marker
    """
    return pytest.mark.skipif(
        not os.getenv(var_name), reason=f"Environment variable {var_name} not set"
    )


def requires_file(file_path: str):
    """Decorator to skip test if file does not exist.

    Usage:
        @requires_file("/path/to/file")
        def test_file_processing():
            pass

    Args:
        file_path: Path to required file

    Returns:
        Pytest skip marker
    """
    return pytest.mark.skipif(
        not Path(file_path).exists(), reason=f"Required file {file_path} not found"
    )


# Export all fixtures and utilities
__all__ = [
    "event_loop",
    "test_env",
    "project_root",
    "sdk_path",
    "sample_test_data",
    "temp_test_file",
    "configure_test_logging",
    "session_id",
    "cleanup_after_test",
    "requires_env_var",
    "requires_file",
]
