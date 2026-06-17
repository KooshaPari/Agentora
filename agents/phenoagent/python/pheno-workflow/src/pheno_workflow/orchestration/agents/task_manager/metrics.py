"""Task Metrics and Telemetry.

Provides metrics collection and event recording for agent tasks.
"""

import contextlib
import logging
from typing import Any

logger = logging.getLogger(__name__)


def record_task_metric(task_context: Any, event: str) -> None:
    """Record an agent task status event into the event store.

    Captures timestamps and duration alongside agent/model metadata to feed
    duration estimators and operational metrics. No-op if event store disabled.

    Args:
        task_context: Task execution context with task details
        event: Event type (e.g., "task_started", "task_completed", "task_failed")
    """
    try:
        # Try to import event store
        try:
            from utils.event_store_sql import append_event
        except ImportError:
            logger.debug("Event store not available, skipping metric recording")
            return

        # Extract task information
        task_id = getattr(task_context, "task_id", None)
        if not task_id:
            task_id = getattr(getattr(task_context, "config", None), "task_id", None)

        status = getattr(task_context, "status", None)
        started_at = getattr(task_context, "started_at", None)
        completed_at = getattr(task_context, "completed_at", None)

        # Calculate duration
        duration_sec = None
        if started_at and completed_at:
            with contextlib.suppress(Exception):
                duration_sec = (completed_at - started_at).total_seconds()

        # Extract workflow parameters
        workflow_params = {}
        config = getattr(task_context, "config", None)
        if config:
            workflow_params = getattr(config, "workflow_params", {}) or {}
            agent_type = getattr(config, "agent_type", None)
            working_dir = getattr(config, "working_directory", None)
            model = getattr(config, "model", None)
            task_desc = getattr(config, "task_description", None)
            workflow = getattr(config, "workflow", None)
        else:
            agent_type = None
            working_dir = None
            model = None
            task_desc = None
            workflow = None

        # Extract project context
        project_id = workflow_params.get("project_id")
        item_id = workflow_params.get("item_id")

        # Extract task category and story points
        task_category = workflow_params.get("category") or workflow
        story_points = workflow_params.get("story_points")

        # If story points not in workflow params, try to get from project graph
        if story_points is None and project_id and item_id:
            try:
                from utils.project_graph import get_project_graph

                graph = get_project_graph(project_id)
                node = graph.nodes.get(item_id)
                if node:
                    story_points = getattr(node, "story_points", None)
            except Exception:
                pass

        # Build event payload
        payload = {
            "agent_type": agent_type.value if hasattr(agent_type, "value") else str(agent_type),
            "status": status.value if hasattr(status, "value") else str(status),
            "task_id": task_id,
            "started_at": started_at.isoformat() if started_at else None,
            "completed_at": completed_at.isoformat() if completed_at else None,
            "duration_sec": duration_sec,
            "working_dir": working_dir,
            "model": model,
            "action": task_desc,
            "event": event,
            "task_category": task_category,
            "story_points": story_points,
        }

        # Append event (project context not always applicable)
        append_event(
            project_id=project_id or "__global__",
            event_type="agent_task_status",
            node_id=item_id or task_id,
            payload=payload,
        )

    except Exception:
        # Never break main path
        logger.debug("Failed to record agent task metric", exc_info=True)


def record_task_performance(
    task_id: str,
    execution_time: float,
    memory_usage: int | None = None,
    cpu_usage: float | None = None,
    **kwargs,
) -> None:
    """Record task performance metrics.

    Args:
        task_id: Task identifier
        execution_time: Execution time in seconds
        memory_usage: Memory usage in bytes (optional)
        cpu_usage: CPU usage percentage (optional)
        **kwargs: Additional performance metrics
    """
    try:
        from utils.event_store_sql import append_event

        payload = {
            "task_id": task_id,
            "execution_time_seconds": execution_time,
            "memory_usage_bytes": memory_usage,
            "cpu_usage_percent": cpu_usage,
            **kwargs,
        }

        append_event(
            project_id="__global__",
            event_type="agent_task_performance",
            node_id=task_id,
            payload=payload,
        )

    except Exception:
        logger.debug("Failed to record task performance metrics", exc_info=True)


def get_task_metrics(task_id: str) -> dict[str, Any]:
    """Get aggregated metrics for a task.

    Args:
        task_id: Task identifier

    Returns:
        Dictionary of metrics
    """
    try:
        from utils.event_store_sql import get_events

        events = get_events(event_type="agent_task_status", node_id=task_id, limit=100)

        # Aggregate metrics
        metrics = {
            "total_events": len(events),
            "events": events,
        }

        # Calculate averages if multiple executions
        durations = [
            e["payload"]["duration_sec"]
            for e in events
            if e.get("payload", {}).get("duration_sec") is not None
        ]

        if durations:
            metrics["avg_duration_seconds"] = sum(durations) / len(durations)
            metrics["min_duration_seconds"] = min(durations)
            metrics["max_duration_seconds"] = max(durations)

        return metrics

    except Exception as e:
        logger.debug(f"Failed to get task metrics: {e}")
        return {}


class MetricsCollector:
    """
    Collector for aggregating task metrics over time.
    """

    def __init__(self):
        self.metrics: dict[str, list] = {
            "execution_times": [],
            "success_count": 0,
            "failure_count": 0,
            "total_tasks": 0,
        }

    def record_task_completion(self, task_id: str, success: bool, execution_time: float, **kwargs):
        """
        Record task completion for metrics.
        """
        self.metrics["total_tasks"] += 1
        self.metrics["execution_times"].append(execution_time)

        if success:
            self.metrics["success_count"] += 1
        else:
            self.metrics["failure_count"] += 1

    def get_summary(self) -> dict[str, Any]:
        """
        Get summary of collected metrics.
        """
        execution_times = self.metrics["execution_times"]

        summary = {
            "total_tasks": self.metrics["total_tasks"],
            "success_count": self.metrics["success_count"],
            "failure_count": self.metrics["failure_count"],
            "success_rate": (
                self.metrics["success_count"] / self.metrics["total_tasks"]
                if self.metrics["total_tasks"] > 0
                else 0.0
            ),
        }

        if execution_times:
            summary["avg_execution_time"] = sum(execution_times) / len(execution_times)
            summary["min_execution_time"] = min(execution_times)
            summary["max_execution_time"] = max(execution_times)

        return summary

    def reset(self):
        """
        Reset collected metrics.
        """
        self.metrics = {
            "execution_times": [],
            "success_count": 0,
            "failure_count": 0,
            "total_tasks": 0,
        }
