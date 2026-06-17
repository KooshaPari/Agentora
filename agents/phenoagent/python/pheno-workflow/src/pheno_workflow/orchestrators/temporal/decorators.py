"""
Decorators for workflow activities and signals.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable


def workflow_activity(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Mark a function as a workflow activity.
    """
    func._is_workflow_activity = True  # type: ignore[attr-defined]
    return func


def workflow_signal(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Mark a function as a workflow signal handler.
    """
    func._is_workflow_signal = True  # type: ignore[attr-defined]
    return func


__all__ = ["workflow_activity", "workflow_signal"]
