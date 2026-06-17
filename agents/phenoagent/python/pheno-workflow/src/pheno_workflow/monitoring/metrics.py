"""
Workflow execution metrics.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime


@dataclass
class WorkflowExecution:
    """
    Workflow execution record.
    """

    workflow_name: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str = "running"
    error: Optional[str] = None
    duration_seconds: float = 0.0


class WorkflowMetrics:
    """Collect and report workflow metrics.

    Example:
        metrics = WorkflowMetrics()

        metrics.record_start("process_order", "exec-123")
        # ... workflow executes ...
        metrics.record_complete("exec-123", status="success")

        stats = metrics.get_stats("process_order")
        print(f"Success rate: {stats['success_rate']}")
    """

    def __init__(self):
        self._executions: dict[str, WorkflowExecution] = {}
        self._workflow_stats: dict[str, dict] = defaultdict(
            lambda: {
                "total": 0,
                "success": 0,
                "failed": 0,
                "running": 0,
                "avg_duration": 0.0,
            },
        )

    def record_start(self, workflow_name: str, execution_id: str):
        """
        Record workflow start.
        """
        self._executions[execution_id] = WorkflowExecution(
            workflow_name=workflow_name,
            started_at=datetime.utcnow(),
        )
        self._workflow_stats[workflow_name]["total"] += 1
        self._workflow_stats[workflow_name]["running"] += 1

    def record_complete(
        self,
        execution_id: str,
        status: str = "success",
        error: Optional[str] = None,
    ):
        """
        Record workflow completion.
        """
        if execution_id not in self._executions:
            return

        execution = self._executions[execution_id]
        execution.completed_at = datetime.utcnow()
        execution.status = status
        execution.error = error

        duration = (execution.completed_at - execution.started_at).total_seconds()
        execution.duration_seconds = duration

        workflow_name = execution.workflow_name
        stats = self._workflow_stats[workflow_name]

        stats["running"] -= 1

        if status == "success":
            stats["success"] += 1
        else:
            stats["failed"] += 1

        # Update average duration
        total_executions = stats["success"] + stats["failed"]
        if total_executions > 0:
            current_avg = stats["avg_duration"]
            stats["avg_duration"] = (
                current_avg * (total_executions - 1) + duration
            ) / total_executions

    def get_stats(self, workflow_name: str) -> dict:
        """
        Get statistics for a workflow.
        """
        stats = self._workflow_stats[workflow_name].copy()

        total_completed = stats["success"] + stats["failed"]
        if total_completed > 0:
            stats["success_rate"] = stats["success"] / total_completed
        else:
            stats["success_rate"] = 0.0

        return stats

    def get_all_stats(self) -> dict[str, dict]:
        """
        Get statistics for all workflows.
        """
        return {name: self.get_stats(name) for name in self._workflow_stats}

    def get_execution(self, execution_id: str) -> Optional[WorkflowExecution]:
        """
        Get execution record.
        """
        return self._executions.get(execution_id)
