"""Pytest markers for test categorization.

Provides custom markers for organizing and filtering tests.
"""

import pytest

# ============================================================================
# Test Category Markers
# ============================================================================

slow = pytest.mark.slow
"""Mark test as slow.

Use this marker for tests that take a long time to run.

Example:
    @pytest.mark.slow
    def test_large_dataset_processing():
        # Long-running test
        pass

Run only fast tests:
    pytest -m "not slow"
"""


integration = pytest.mark.integration
"""Mark test as integration test.

Use this marker for tests that test integration between components.

Example:
    @pytest.mark.integration
    def test_api_database_integration():
        # Integration test
        pass

Run only integration tests:
    pytest -m integration
"""


unit = pytest.mark.unit
"""Mark test as unit test.

Use this marker for isolated unit tests.

Example:
    @pytest.mark.unit
    def test_function_logic():
        # Unit test
        pass

Run only unit tests:
    pytest -m unit
"""


db = pytest.mark.db
"""Mark test as requiring database.

Use this marker for tests that need database access.

Example:
    @pytest.mark.db
    def test_user_repository():
        # Database test
        pass

Run only database tests:
    pytest -m db

Skip database tests:
    pytest -m "not db"
"""


http = pytest.mark.http
"""Mark test as requiring HTTP.

Use this marker for tests that make HTTP requests.

Example:
    @pytest.mark.http
    def test_api_client():
        # HTTP test
        pass

Run only HTTP tests:
    pytest -m http
"""


# ============================================================================
# Environment Markers
# ============================================================================

requires_env = pytest.mark.requires_env
"""Mark test as requiring specific environment.

Example:
    @pytest.mark.requires_env("production")
    def test_production_config():
        # Production-only test
        pass
"""


skip_in_ci = pytest.mark.skipif(
    pytest.config.getoption("--ci", default=False) if hasattr(pytest, "config") else False,
    reason="Skipped in CI environment",
)
"""Skip test in CI environment.

Example:
    @pytest.mark.skip_in_ci
    def test_local_only():
        # Local-only test
        pass
"""


# ============================================================================
# Performance Markers
# ============================================================================

benchmark = pytest.mark.benchmark
"""Mark test as benchmark.

Use this marker for performance benchmark tests.

Example:
    @pytest.mark.benchmark
    def test_function_performance():
        # Benchmark test
        pass
"""


# ============================================================================
# Flaky Test Markers
# ============================================================================

flaky = pytest.mark.flaky
"""Mark test as flaky.

Use this marker for tests that occasionally fail.

Example:
    @pytest.mark.flaky(reruns=3)
    def test_flaky_operation():
        # Flaky test
        pass
"""


# ============================================================================
# Custom Marker Utilities
# ============================================================================


def skip_if_not_installed(package_name: str):
    """Skip test if package is not installed.

    Args:
        package_name: Name of the package to check

    Example:
        @skip_if_not_installed("redis")
        def test_redis_cache():
            # Test that requires redis
            pass
    """
    try:
        __import__(package_name)
        return pytest.mark.skipif(False, reason=f"{package_name} is installed")
    except ImportError:
        return pytest.mark.skipif(True, reason=f"{package_name} not installed")


def requires_python(version: str):
    """Require specific Python version.

    Args:
        version: Minimum Python version (e.g., "3.10")

    Example:
        @requires_python("3.10")
        def test_new_syntax():
            # Test using Python 3.10+ syntax
            pass
    """
    import sys

    major, minor = map(int, version.split("."))
    current = sys.version_info

    return pytest.mark.skipif(current < (major, minor), reason=f"Requires Python {version}+")


__all__ = [
    "benchmark",
    "db",
    "flaky",
    "http",
    "integration",
    "requires_env",
    "requires_python",
    "skip_if_not_installed",
    "skip_in_ci",
    "slow",
    "unit",
]
