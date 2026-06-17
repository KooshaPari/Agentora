"""
Logging-related data structures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from datetime import datetime


@dataclass
class LogOptions:
    """
    Options controlling how logs are fetched from providers.
    """

    since: datetime | None = None
    until: datetime | None = None
    tail: int | None = None
    follow: bool = False
    filter: str | None = None
    instance_id: str | None = None


@dataclass
class LogEntry:
    """
    Structured log entry returned from provider log streams.
    """

    timestamp: datetime
    message: str
    level: str | None = None
    instance_id: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)


class LogStream(Protocol):
    """
    Protocol for log streams.
    """

    def __next__(self) -> LogEntry: ...

    def __iter__(self): ...

    def close(self) -> None: ...


__all__ = ["LogEntry", "LogOptions", "LogStream"]
