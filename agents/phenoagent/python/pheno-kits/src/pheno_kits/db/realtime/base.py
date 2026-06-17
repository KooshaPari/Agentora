"""
Abstract base class for realtime adapters.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class RealtimeAdapter(ABC):
    """
    Abstract interface for real-time subscriptions.
    """

    @abstractmethod
    async def subscribe(
        self,
        table: str,
        callback: callable,
        *,
        filters: dict[str, Any] | None = None,
        events: list[str] | None = None,
    ) -> str:
        """Subscribe to real-time changes.

        Args:
            table: Table to watch
            callback: Function to call on changes
            filters: Filter conditions
            events: Event types to watch (INSERT, UPDATE, DELETE)

        Returns:
            Subscription ID
        """

    @abstractmethod
    async def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from real-time changes.

        Args:
            subscription_id: Subscription to cancel

        Returns:
            True if unsubscribed, False if not found
        """
