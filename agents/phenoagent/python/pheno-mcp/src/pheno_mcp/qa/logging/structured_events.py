"""Tiny structured event log used by the TUI widgets.

The original project streamed events from running tests; for the consolidated
implementation we keep an in-memory ring buffer that is more than sufficient for CLI
usage and unit tests.
"""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

_EVENTS: deque[dict[str, str]] = deque(maxlen=200)


def record_event(event: dict[str, str]) -> None:
    """
    Append an event to the buffer.
    """
    _EVENTS.append(event)


def get_recent_events(limit: int = 50) -> Iterable[dict[str, str]]:
    """
    Return up to ``limit`` most recently recorded events.
    """
    if limit <= 0:
        return []
    return list(_EVENTS)[-limit:]


__all__ = ["get_recent_events", "record_event"]
