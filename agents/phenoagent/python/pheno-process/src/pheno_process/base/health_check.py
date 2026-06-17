"""
Health check protocol.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class HealthCheck(Protocol):
    """
    Protocol for health check implementations.
    """

    async def check(self) -> bool:
        """Perform health check.

        Returns:
            True if healthy, False otherwise
        """
        ...

    def get_name(self) -> str:
        """Get health check name.

        Returns:
            Name of the health check
        """
        ...
