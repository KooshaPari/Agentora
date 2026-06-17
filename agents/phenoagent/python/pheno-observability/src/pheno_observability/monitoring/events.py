"""Event Collection and Emission.

Unified event system that consolidates functionality from infra/monitoring, MCP QA, and
observability stacks.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import uuid4

from ..logging import get_logger

logger = get_logger(__name__)


@dataclass
class Event:
    """
    A structured event.
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    type: str = ""
    source: str = ""
    timestamp: float = field(default_factory=time.time)
    data: dict[str, Any] = field(default_factory=dict)
    labels: dict[str, str] = field(default_factory=dict)
    severity: str = "info"  # debug, info, warning, error, critical

    def to_dict(self) -> dict[str, Any]:
        """
        Convert event to dictionary.
        """
        return {
            "id": self.id,
            "type": self.type,
            "source": self.source,
            "timestamp": self.timestamp,
            "data": self.data,
            "labels": self.labels,
            "severity": self.severity,
        }

    def to_json(self) -> str:
        """
        Convert event to JSON string.
        """
        return json.dumps(self.to_dict(), default=str)


class EventHandler(Protocol):
    """
    Protocol for event handlers.
    """

    async def handle(self, event: Event) -> None:
        """
        Handle an event.
        """
        ...


class EventEmitter:
    """Emits events to registered handlers.

    Consolidates event emission from infra/monitoring, MCP QA, and observability stacks
    into a unified interface.
    """

    def __init__(self, buffer_size: int = 1000):
        """Initialize event emitter.

        Args:
            buffer_size: Maximum number of events to keep in buffer
        """
        self.buffer_size = buffer_size
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")

        # Event handling
        self._handlers: list[EventHandler] = []
        self._event_buffer: deque = deque(maxlen=buffer_size)

        # State
        self._emitting = False
        self._emit_tasks: list[asyncio.Task] = []

    async def start(self) -> None:
        """
        Start event emission.
        """
        if self._emitting:
            self.logger.warning("Event emitter already started")
            return

        self._emitting = True
        self.logger.info("Started event emitter")

    async def stop(self) -> None:
        """
        Stop event emission.
        """
        if not self._emitting:
            return

        # Cancel emit tasks
        for task in self._emit_tasks:
            task.cancel()

        if self._emit_tasks:
            await asyncio.gather(*self._emit_tasks, return_exceptions=True)

        self._emitting = False
        self.logger.info("Stopped event emitter")

    def emit(
        self,
        event_type: str,
        data: dict[str, Any] | None = None,
        source: str = "",
        labels: dict[str, str] | None = None,
        severity: str = "info",
    ) -> Event:
        """Emit an event.

        Args:
            event_type: Type of event
            data: Event data
            source: Event source
            labels: Event labels
            severity: Event severity

        Returns:
            The created event
        """
        event = Event(
            type=event_type,
            source=source,
            data=data or {},
            labels=labels or {},
            severity=severity,
        )

        # Add to buffer
        self._event_buffer.append(event)

        # Emit to handlers asynchronously
        if self._emitting and self._handlers:
            task = asyncio.create_task(self._emit_to_handlers(event))
            self._emit_tasks.append(task)
            # Clean up completed tasks
            self._emit_tasks = [t for t in self._emit_tasks if not t.done()]

        self.logger.debug(f"Emitted event: {event_type} from {source}")
        return event

    async def _emit_to_handlers(self, event: Event) -> None:
        """
        Emit event to all handlers.
        """
        for handler in self._handlers:
            try:
                await handler.handle(event)
            except Exception as e:
                self.logger.exception(
                    f"Error handling event {event.id} with {handler.__class__.__name__}: {e}",
                )

    def add_handler(self, handler: EventHandler) -> None:
        """
        Add an event handler.
        """
        self._handlers.append(handler)
        self.logger.info(f"Added event handler: {handler.__class__.__name__}")

    def remove_handler(self, handler: EventHandler) -> None:
        """
        Remove an event handler.
        """
        if handler in self._handlers:
            self._handlers.remove(handler)
            self.logger.info(f"Removed event handler: {handler.__class__.__name__}")

    def get_recent_events(self, limit: int = 100) -> list[Event]:
        """
        Get recent events from buffer.
        """
        return list(self._event_buffer)[-limit:]

    def get_events_by_type(self, event_type: str) -> list[Event]:
        """
        Get events by type.
        """
        return [event for event in self._event_buffer if event.type == event_type]

    def get_events_by_severity(self, severity: str) -> list[Event]:
        """
        Get events by severity.
        """
        return [event for event in self._event_buffer if event.severity == severity]

    def clear_buffer(self) -> None:
        """
        Clear event buffer.
        """
        self._event_buffer.clear()
        self.logger.info("Cleared event buffer")


class EventCollector:
    """Collects events from multiple sources.

    Provides a centralized way to collect and process events from different components
    and services.
    """

    def __init__(self, buffer_size: int = 1000):
        """Initialize event collector.

        Args:
            buffer_size: Maximum number of events to keep in memory
        """
        self.buffer_size = buffer_size
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")

        # Event storage
        self._events: deque = deque(maxlen=buffer_size)
        self._emitters: list[EventEmitter] = []

        # Collection state
        self._collecting = False
        self._collection_tasks: list[asyncio.Task] = []

    async def start(self) -> None:
        """
        Start event collection.
        """
        if self._collecting:
            self.logger.warning("Event collector already started")
            return

        self._collecting = True

        # Start collection from emitters
        for emitter in self._emitters:
            task = asyncio.create_task(self._collect_from_emitter(emitter))
            self._collection_tasks.append(task)

        self.logger.info("Started event collector")

    async def stop(self) -> None:
        """
        Stop event collection.
        """
        if not self._collecting:
            return

        # Cancel collection tasks
        for task in self._collection_tasks:
            task.cancel()

        if self._collection_tasks:
            await asyncio.gather(*self._collection_tasks, return_exceptions=True)

        self._collecting = False
        self.logger.info("Stopped event collector")

    def add_emitter(self, emitter: EventEmitter) -> None:
        """
        Add an event emitter to collect from.
        """
        self._emitters.append(emitter)
        self.logger.info(f"Added event emitter: {emitter.__class__.__name__}")

    def remove_emitter(self, emitter: EventEmitter) -> None:
        """
        Remove an event emitter.
        """
        if emitter in self._emitters:
            self._emitters.remove(emitter)
            self.logger.info(f"Removed event emitter: {emitter.__class__.__name__}")

    async def _collect_from_emitter(self, emitter: EventEmitter) -> None:
        """
        Collect events from an emitter.
        """
        while self._collecting:
            try:
                await self._collect_events_from_emitter(emitter)
                await asyncio.sleep(1.0)  # Collect every second
            except asyncio.CancelledError:
                break
            except Exception as e:
                await self._handle_collection_error(emitter, e)

    async def _collect_events_from_emitter(self, emitter: EventEmitter) -> None:
        """
        Collect and process events from the emitter.
        """
        events = emitter.get_recent_events(limit=100)
        self._add_new_events(events)

    def _add_new_events(self, events: list[Event]) -> None:
        """
        Add new events to the collection.
        """
        for event in events:
            if event not in self._events:
                self._events.append(event)

    async def _handle_collection_error(self, emitter: EventEmitter, error: Exception) -> None:
        """
        Handle errors during event collection.
        """
        self.logger.error(f"Error collecting from emitter {emitter.__class__.__name__}: {error}")
        await asyncio.sleep(1.0)

    def get_all_events(self) -> list[Event]:
        """
        Get all collected events.
        """
        return list(self._events)

    def get_recent_events(self, limit: int = 100) -> list[Event]:
        """
        Get recent events.
        """
        return list(self._events)[-limit:]

    def get_events_by_type(self, event_type: str) -> list[Event]:
        """
        Get events by type.
        """
        return [event for event in self._events if event.type == event_type]

    def get_events_by_source(self, source: str) -> list[Event]:
        """
        Get events by source.
        """
        return [event for event in self._events if event.source == source]

    def get_events_by_severity(self, severity: str) -> list[Event]:
        """
        Get events by severity.
        """
        return [event for event in self._events if event.severity == severity]

    def get_event_summary(self) -> dict[str, Any]:
        """
        Get a summary of collected events.
        """
        if not self._events:
            return {
                "total_events": 0,
                "event_types": {},
                "sources": {},
                "severities": {},
            }

        # Count by type
        event_types = {}
        sources = {}
        severities = {}

        for event in self._events:
            event_types[event.type] = event_types.get(event.type, 0) + 1
            sources[event.source] = sources.get(event.source, 0) + 1
            severities[event.severity] = severities.get(event.severity, 0) + 1

        return {
            "total_events": len(self._events),
            "event_types": event_types,
            "sources": sources,
            "severities": severities,
            "oldest_event": min(event.timestamp for event in self._events),
            "newest_event": max(event.timestamp for event in self._events),
        }

    def clear_events(self) -> None:
        """
        Clear all collected events.
        """
        self._events.clear()
        self.logger.info("Cleared all events")
