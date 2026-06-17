"""
Workflow execution context helpers.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


class WorkflowContext:
    """
    Context object available during workflow execution.
    """

    def __init__(self, workflow_id: str):
        self.workflow_id = workflow_id
        self.signals: dict[str, Any] = {}
        self.activities_completed: list[str] = []
        self.start_time = datetime.utcnow()

    def set_signal(self, signal_name: str, value: Any) -> None:
        """
        Set a signal value.
        """
        self.signals[signal_name] = value

    def get_signal(self, signal_name: str) -> Any | None:
        """
        Get a signal value.
        """
        return self.signals.get(signal_name)

    def mark_activity_completed(self, activity_name: str) -> None:
        """
        Mark an activity as completed.
        """
        if activity_name not in self.activities_completed:
            self.activities_completed.append(activity_name)


__all__ = ["WorkflowContext"]
