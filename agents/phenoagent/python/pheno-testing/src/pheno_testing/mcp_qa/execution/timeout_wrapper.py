"""Timeout Wrapper for Test Execution.

Prevents tests from hanging indefinitely and improves overall speed.
"""

import asyncio
import functools
from typing import Any, Callable, Dict, List


class TimeoutManager:
    """
    Manages test timeouts and enforces execution limits.
    """

    DEFAULT_TIMEOUT = 30  # 30 seconds default
    SLOW_TEST_THRESHOLD = 5000  # 5 seconds in ms

    @staticmethod
    async def run_with_timeout(coro, timeout_seconds: float, test_name: str) -> Dict[str, Any]:
        """Run coroutine with timeout.

        Args:
            coro: Async coroutine to run
            timeout_seconds: Timeout in seconds
            test_name: Test name for logging

        Returns:
            Test result or timeout error
        """
        try:
            result = await asyncio.wait_for(coro, timeout=timeout_seconds)
            return result
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": f"Test timed out after {timeout_seconds}s",
                "timeout": True,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    @staticmethod
    def detect_slow_tests(results: List[Dict[str, Any]]) -> List[str]:
        """Detect tests that are unusually slow.

        Args:
            results: Test results

        Returns:
            List of slow test names
        """
        slow_tests = []
        for result in results:
            if result.get("duration_ms", 0) > TimeoutManager.SLOW_TEST_THRESHOLD:
                slow_tests.append(result["test_name"])

        return slow_tests


def timeout_wrapper(timeout_seconds: float = 30):
    """Decorator to add timeout to test functions.

    Usage:
        @timeout_wrapper(15)
        async def test_something(client):
            # Will timeout after 15 seconds
            pass
    """

    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout_seconds)
            except asyncio.TimeoutError:
                return {
                    "success": False,
                    "error": f"Test timed out after {timeout_seconds}s",
                    "timeout": True,
                }

        return wrapper

    return decorator


__all__ = ["TimeoutManager", "timeout_wrapper"]
