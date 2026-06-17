"""
Integration helpers for event bus and storage backends.
"""

from __future__ import annotations

from typing import Any

try:  # pragma: no cover - optional dependency
    from workflow_kit.event_bus import get_event_bus  # type: ignore
except ImportError:  # pragma: no cover - fallback for environments without workflow_kit

    def get_event_bus() -> Any:
        return None


try:  # pragma: no cover - optional dependency
    from workflow_kit.storage_backend import get_storage_backend  # type: ignore
except ImportError:  # pragma: no cover - fallback for environments without workflow_kit

    def get_storage_backend() -> Any:
        return None


__all__ = ["get_event_bus", "get_storage_backend"]
