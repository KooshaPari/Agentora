"""
Compatibility layer for Temporal SDK.

Provides graceful fallbacks when Temporal is not installed.
"""


# Try to import Temporal SDK
try:
    from temporalio import workflow
    from temporalio.client import Client, TLSConfig
    from temporalio.common import RetryPolicy
    from temporalio.worker import Worker

    TEMPORAL_AVAILABLE = True

except ImportError:
    # Temporal not available, provide mock classes
    TEMPORAL_AVAILABLE = False

    class Client:
        """Mock Temporal client."""

        def __init__(self, *args, **kwargs):
            raise RuntimeError("Temporal SDK not installed. Install with: pip install temporalio")

    class TLSConfig:
        """Mock TLS config."""

        def __init__(self, *args, **kwargs):
            raise RuntimeError("Temporal SDK not installed. Install with: pip install temporalio")

    class RetryPolicy:
        """Mock retry policy."""

        def __init__(self, *args, **kwargs):
            raise RuntimeError("Temporal SDK not installed. Install with: pip install temporalio")

    class Worker:
        """Mock worker."""

        def __init__(self, *args, **kwargs):
            raise RuntimeError("Temporal SDK not installed. Install with: pip install temporalio")

    class workflow:
        """Mock workflow decorator."""

        @staticmethod
        def defn(*args, **kwargs):
            def decorator(func):
                return func

            return decorator

        @staticmethod
        def run(*args, **kwargs):
            raise RuntimeError("Temporal SDK not installed. Install with: pip install temporalio")


__all__ = [
    "TEMPORAL_AVAILABLE",
    "Client",
    "RetryPolicy",
    "TLSConfig",
    "Worker",
    "workflow",
]
