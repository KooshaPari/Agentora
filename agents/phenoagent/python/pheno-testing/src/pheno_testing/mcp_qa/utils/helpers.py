"""Test Helper Functions and Utilities.

Provides common helper functions for MCP testing, combining best features from both Zen
and Atoms implementations.
"""

import asyncio
import functools
import re
import time
import uuid as uuid_lib
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

# ============================================================================
# Data Generation Utilities
# ============================================================================


class DataGenerator:
    """
    Generate test data for entities with guaranteed uniqueness.
    """

    @staticmethod
    def timestamp() -> str:
        """
        Generate timestamp string for unique identifiers.
        """
        # Use hyphen format for better readability
        return datetime.now().strftime("%Y%m%d-%H%M%S-%f")[:-3]

    @staticmethod
    def unique_id(prefix: str = "") -> str:
        """
        Generate unique identifier with optional prefix.
        """
        ts = DataGenerator.timestamp()
        return f"{prefix}{ts}" if prefix else ts

    @staticmethod
    def uuid() -> str:
        """
        Generate a random UUID string.
        """
        return str(uuid_lib.uuid4())

    @staticmethod
    def slug_from_uuid(prefix: str = "") -> str:
        """Generate a slug-safe unique identifier.

        Ensures compliance with common slug patterns: ^[a-z][a-z0-9-]*$
        """
        unique_slug = str(uuid_lib.uuid4())[:8]
        # Ensure slug matches: starts with letter, only lowercase letters, numbers, hyphens
        unique_slug = re.sub(r"[^a-z0-9-]", "", unique_slug.lower())
        # Ensure starts with letter
        if not unique_slug or not unique_slug[0].isalpha():
            unique_slug = f"{prefix or 'test'}{unique_slug}"
        elif prefix:
            unique_slug = f"{prefix}-{unique_slug}"
        return unique_slug

    @staticmethod
    def organization_data(name: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate organization test data with valid slug.
        """
        unique_slug = DataGenerator.slug_from_uuid("org")

        return {
            "name": name or f"Test Org {unique_slug}",
            "slug": unique_slug,
            "description": "Automated test organization",
            "type": "team",
        }

    @staticmethod
    def project_data(
        name: Optional[str] = None, organization_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate project test data.

        Args:
            name: Optional project name
            organization_id: Organization ID (if required by API)

        Returns:
            Dict with project data
        """
        unique_slug = DataGenerator.slug_from_uuid("proj")
        data = {
            "name": name or f"Test Project {unique_slug}",
            "slug": unique_slug,
            "description": "Automated test project",
        }
        # Only include organization_id if provided
        if organization_id:
            data["organization_id"] = organization_id
        return data

    @staticmethod
    def document_data(
        name: Optional[str] = None, project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate document test data.

        Args:
            name: Optional document name
            project_id: Project ID (if required by API)

        Returns:
            Dict with document data
        """
        unique_slug = DataGenerator.slug_from_uuid("doc")
        data = {
            "name": name or f"Test Document {unique_slug}",
            "slug": unique_slug,
            "description": "Automated test document",
            "type": "specification",
        }
        if project_id:
            data["project_id"] = project_id
        return data

    @staticmethod
    def requirement_data(
        name: Optional[str] = None, document_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate requirement test data.

        Args:
            name: Optional requirement name
            document_id: Document ID (if required by API)

        Returns:
            Dict with requirement data
        """
        unique = DataGenerator.unique_id()
        data = {
            "name": name or f"REQ-TEST-{unique}",
            "description": "Automated test requirement",
            "priority": "medium",
            "status": "active",
        }
        if document_id:
            data["document_id"] = document_id
        return data

    @staticmethod
    def test_data(title: Optional[str] = None, project_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate test case data.

        Args:
            title: Optional test title
            project_id: Project ID (if required by API)

        Returns:
            Dict with test data
        """
        unique = DataGenerator.unique_id()
        data = {
            "title": title or f"Test Case {unique}",
            "description": "Automated test case",
            "status": "pending",
            "priority": "medium",
        }
        if project_id:
            data["project_id"] = project_id
        return data

    @staticmethod
    def batch_data(entity_type: str, count: int = 3, **kwargs) -> List[Dict[str, Any]]:
        """Generate batch test data for entity type.

        Args:
            entity_type: Type of entity (organization, project, document, etc.)
            count: Number of entities to generate
            **kwargs: Additional arguments to pass to generator

        Returns:
            List of entity data dictionaries
        """
        generators = {
            "organization": DataGenerator.organization_data,
            "project": DataGenerator.project_data,
            "document": DataGenerator.document_data,
            "requirement": DataGenerator.requirement_data,
            "test": DataGenerator.test_data,
        }

        generator = generators.get(entity_type)
        if not generator:
            return []

        return [generator(**kwargs) for _ in range(count)]


# ============================================================================
# Response Validation Utilities
# ============================================================================


class ResponseValidator:
    """
    Validates MCP tool responses and extracts data.
    """

    @staticmethod
    def has_fields(response: Dict[str, Any], required_fields: List[str]) -> bool:
        """
        Check if response has all required fields.
        """
        if not isinstance(response, dict):
            return False
        return all(field in response for field in required_fields)

    @staticmethod
    def has_any_fields(response: Dict[str, Any], fields: List[str]) -> bool:
        """
        Check if response has any of the specified fields.
        """
        if not isinstance(response, dict):
            return False
        return any(field in response for field in fields)

    @staticmethod
    def validate_pagination(response: Dict[str, Any]) -> bool:
        """
        Validate pagination structure.
        """
        required = ["total", "limit", "offset"]
        return ResponseValidator.has_fields(response, required)

    @staticmethod
    def validate_list_response(response: Dict[str, Any], data_key: str = "data") -> bool:
        """
        Validate list response structure.
        """
        if not isinstance(response, dict):
            return False
        if data_key not in response:
            return False
        return isinstance(response[data_key], list)

    @staticmethod
    def validate_success_response(result: Dict[str, Any]) -> bool:
        """
        Validate standard success response.
        """
        return result.get("success", False) and result.get("error") is None

    @staticmethod
    def extract_id(response: Dict[str, Any]) -> Optional[str]:
        """Extract ID from response, handling multiple formats.

        Handles:
        - {"id": "..."}
        - {"data": {"id": "..."}}
        """
        if not isinstance(response, dict):
            return None

        # Direct id field
        if "id" in response:
            return response["id"]

        # Nested in data
        if "data" in response and isinstance(response["data"], dict):
            return response["data"].get("id")

        return None


class FieldValidator:
    """
    Validates specific field types and values.
    """

    @staticmethod
    def is_uuid(value: Any) -> bool:
        """
        Check if value is a valid UUID string.
        """
        if not isinstance(value, str):
            return False
        uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        return bool(re.match(uuid_pattern, value, re.IGNORECASE))

    @staticmethod
    def is_iso_timestamp(value: Any) -> bool:
        """
        Check if value is ISO 8601 timestamp.
        """
        if not isinstance(value, str):
            return False
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
            return True
        except (ValueError, AttributeError):
            return False

    @staticmethod
    def is_in_range(
        value: Any, min_val: Optional[float] = None, max_val: Optional[float] = None
    ) -> bool:
        """
        Check if value is within range.
        """
        try:
            num = float(value)
            if min_val is not None and num < min_val:
                return False
            if max_val is not None and num > max_val:
                return False
            return True
        except (ValueError, TypeError):
            return False

    @staticmethod
    def is_valid_slug(value: Any, pattern: str = r"^[a-z][a-z0-9-]*$") -> bool:
        """Check if value is a valid slug.

        Args:
            value: Value to check
            pattern: Regex pattern for valid slug (default: starts with letter, alphanumeric + hyphens)

        Returns:
            True if value matches slug pattern
        """
        if not isinstance(value, str):
            return False
        return bool(re.match(pattern, value))


# ============================================================================
# Timeout Management
# ============================================================================


class TimeoutManager:
    """
    Manages test timeouts and enforces execution limits.
    """

    DEFAULT_TIMEOUT = 30  # 30 seconds default
    SLOW_TEST_THRESHOLD = 5000  # 5 seconds in ms

    @staticmethod
    async def run_with_timeout(
        coro, timeout_seconds: float, test_name: str = "unknown"
    ) -> Dict[str, Any]:
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
                "error": f"Test '{test_name}' timed out after {timeout_seconds}s",
                "timeout": True,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    @staticmethod
    def detect_slow_tests(
        results: List[Dict[str, Any]], threshold_ms: Optional[int] = None
    ) -> List[Tuple[str, int]]:
        """Detect tests that are unusually slow.

        Args:
            results: Test results with duration_ms field
            threshold_ms: Custom threshold in milliseconds

        Returns:
            List of (test_name, duration_ms) tuples for slow tests
        """
        threshold = threshold_ms or TimeoutManager.SLOW_TEST_THRESHOLD
        slow_tests = []

        for result in results:
            duration = result.get("duration_ms", 0)
            if duration > threshold:
                test_name = result.get("test_name", "unknown")
                slow_tests.append((test_name, duration))

        return slow_tests


def timeout_wrapper(timeout_seconds: float = 30):
    """Decorator to add timeout to async test functions.

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
                    "error": f"Test '{func.__name__}' timed out after {timeout_seconds}s",
                    "timeout": True,
                }

        return wrapper

    return decorator


# ============================================================================
# Retry and Backoff Strategies
# ============================================================================


class WaitStrategy:
    """
    Wait strategies for retry delays.
    """

    @staticmethod
    def immediate() -> float:
        """
        No wait.
        """
        return 0.0

    @staticmethod
    def linear(attempt: int, base_delay: float = 1.0) -> float:
        """Linear backoff: delay × attempt."""
        return base_delay * attempt

    @staticmethod
    def exponential(attempt: int, base_delay: float = 1.0, max_delay: float = 30.0) -> float:
        """Exponential backoff: base × 2^attempt."""
        delay = base_delay * (2 ** (attempt - 1))
        return min(delay, max_delay)

    @staticmethod
    def fibonacci(attempt: int, base_delay: float = 1.0) -> float:
        """Fibonacci backoff: base × fib(attempt)."""

        def fib(n):
            if n <= 1:
                return n
            a, b = 0, 1
            for _ in range(n - 1):
                a, b = b, a + b
            return b

        return base_delay * fib(attempt)


def is_connection_error(error: str) -> bool:
    """Check if error is connection-related.

    Args:
        error: Error message string

    Returns:
        True if error appears to be connection-related
    """
    connection_keywords = [
        "connection refused",
        "connection reset",
        "connection timeout",
        "network unreachable",
        "host unreachable",
        "timeout",
        "timed out",
        "connection error",
        "connection failed",
        "broken pipe",
        "cannot connect",
        "httpstatuserror",
        "server error",
        "530",  # Cloudflare custom error
        "502",  # Bad gateway
        "503",  # Service unavailable
        "504",  # Gateway timeout
        "500",  # Internal server error
    ]

    error_lower = error.lower()
    return any(keyword in error_lower for keyword in connection_keywords)


# ============================================================================
# Performance Tracking
# ============================================================================


class PerformanceTracker:
    """
    Track test execution performance metrics.
    """

    def __init__(self):
        self.metrics = []
        self.start_time = None

    def start(self):
        """
        Start tracking.
        """
        self.start_time = time.time()

    def record(self, test_name: str, duration_ms: int, success: bool):
        """
        Record a test execution.
        """
        self.metrics.append(
            {
                "test_name": test_name,
                "duration_ms": duration_ms,
                "success": success,
                "timestamp": time.time(),
            }
        )

    def get_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics.
        """
        if not self.metrics:
            return {}

        durations = [m["duration_ms"] for m in self.metrics]
        successes = sum(1 for m in self.metrics if m["success"])

        return {
            "total_tests": len(self.metrics),
            "successful_tests": successes,
            "failed_tests": len(self.metrics) - successes,
            "total_duration_ms": sum(durations),
            "avg_duration_ms": sum(durations) / len(durations) if durations else 0,
            "min_duration_ms": min(durations) if durations else 0,
            "max_duration_ms": max(durations) if durations else 0,
            "total_elapsed_seconds": time.time() - self.start_time if self.start_time else 0,
        }


__all__ = [
    "DataGenerator",
    "ResponseValidator",
    "FieldValidator",
    "TimeoutManager",
    "timeout_wrapper",
    "WaitStrategy",
    "is_connection_error",
    "PerformanceTracker",
]
