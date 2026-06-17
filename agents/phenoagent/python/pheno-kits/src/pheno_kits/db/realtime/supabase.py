"""
Supabase realtime adapter implementation.
"""

from __future__ import annotations

import os
import uuid
from typing import Any

from .base import RealtimeAdapter


class SupabaseRealtimeAdapter(RealtimeAdapter):
    """
    Supabase-based realtime adapter.
    """

    def __init__(self, client=None):
        """Initialize Supabase realtime adapter.

        Args:
            client: Supabase client instance (optional, will auto-initialize)
        """
        self._client = client
        self._subscriptions: dict[str, Any] = {}

    def _get_client(self):
        """
        Get Supabase client, auto-initializing if needed.
        """
        if self._client is None:
            try:
                from supabase import create_client

                url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
                key = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
                if not url or not key:
                    raise ValueError(
                        "Missing NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY",
                    )
                self._client = create_client(url, key)
            except ImportError:
                raise ImportError("supabase-py not installed. Install with: pip install supabase")
        return self._client

    async def subscribe(
        self,
        table: str,
        callback: callable,
        *,
        filters: dict[str, Any] | None = None,
        events: list[str] | None = None,
    ) -> str:
        """
        Subscribe to real-time changes on a table.
        """
        try:
            client = self._get_client()
            subscription_id = str(uuid.uuid4())

            # Default to all events if not specified
            if events is None:
                events = ["INSERT", "UPDATE", "DELETE"]

            # Create subscription configuration
            subscription_config = {
                "event": "*",  # Listen to all events by default
                "schema": "public",
                "table": table,
            }

            # Apply filters if provided
            if filters:
                subscription_config["filter"] = filters

            # Note: This is a simplified implementation
            # In a real implementation, you'd need to handle Supabase's
            # realtime subscription API properly
            subscription = (
                client.table(table).on(subscription_config["event"], callback).subscribe()
            )

            self._subscriptions[subscription_id] = {
                "subscription": subscription,
                "table": table,
                "callback": callback,
            }

            return subscription_id

        except Exception as e:
            raise RuntimeError(f"Failed to subscribe to {table}: {e}")

    async def unsubscribe(self, subscription_id: str) -> bool:
        """
        Unsubscribe from real-time changes.
        """
        try:
            if subscription_id not in self._subscriptions:
                return False

            subscription_info = self._subscriptions[subscription_id]
            subscription = subscription_info["subscription"]

            # Unsubscribe from Supabase
            client = self._get_client()
            client.remove_subscription(subscription)

            # Remove from our tracking
            del self._subscriptions[subscription_id]

            return True

        except Exception:
            return False

    def list_subscriptions(self) -> list[str]:
        """
        List active subscription IDs (utility method).
        """
        return list(self._subscriptions.keys())

    def get_subscription_info(self, subscription_id: str) -> dict[str, Any] | None:
        """
        Get info about a subscription (utility method).
        """
        if subscription_id not in self._subscriptions:
            return None

        info = self._subscriptions[subscription_id]
        return {"subscription_id": subscription_id, "table": info["table"], "active": True}
