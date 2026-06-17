"""Agent Metrics Collector for MCP.

Collects and tracks comprehensive metrics for MCP agent executions. Adapted from zen-
mcp-server for use as a reusable SDK component.
"""

import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any


@dataclass
class AgentExecutionMetric:
    """
    Single agent execution metric.
    """

    agent_type: str
    task_id: str
    started_at: datetime
    completed_at: datetime | None = None
    duration_seconds: float = 0.0
    success: bool = False
    error: str | None = None
    output_length: int = 0
    xml_tags_found: int = 0
    timeout_used: int = 0
    timeout_optimal: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentMetricsSummary:
    """
    Summary of agent metrics.
    """

    agent_type: str
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    total_duration_seconds: float = 0.0
    avg_duration_seconds: float = 0.0
    min_duration_seconds: float = 0.0
    max_duration_seconds: float = 0.0
    success_rate: float = 0.0
    error_rate: float = 0.0
    avg_output_length: int = 0
    avg_xml_tags: float = 0.0
    recent_errors: list[str] = field(default_factory=list)


class AgentMetricsCollector:
    """
    Collect and analyze MCP agent execution metrics.
    """

    def __init__(self):
        self.metrics: list[AgentExecutionMetric] = []
        self.metrics_by_agent: dict[str, list[AgentExecutionMetric]] = defaultdict(list)
        self.active_executions: dict[str, AgentExecutionMetric] = {}

    def start_execution(
        self,
        agent_type: str,
        task_id: str,
        timeout_seconds: int = 0,
        optimal_timeout: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Record the start of an agent execution.
        """
        metric = AgentExecutionMetric(
            agent_type=agent_type,
            task_id=task_id,
            started_at=datetime.utcnow(),
            timeout_used=timeout_seconds,
            timeout_optimal=optimal_timeout,
            metadata=metadata or {},
        )
        self.active_executions[task_id] = metric

    def complete_execution(
        self,
        task_id: str,
        success: bool,
        output_length: int = 0,
        xml_tags_found: int = 0,
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Record the completion of an agent execution.
        """
        if task_id not in self.active_executions:
            return

        metric = self.active_executions.pop(task_id)
        metric.completed_at = datetime.utcnow()
        metric.duration_seconds = (metric.completed_at - metric.started_at).total_seconds()
        metric.success = success
        metric.output_length = output_length
        metric.xml_tags_found = xml_tags_found
        metric.error = error

        if metadata:
            metric.metadata.update(metadata)

        self.metrics.append(metric)
        self.metrics_by_agent[metric.agent_type].append(metric)

    def get_summary(self, agent_type: str | None = None) -> dict[str, AgentMetricsSummary]:
        """
        Get summary of metrics.
        """
        if agent_type:
            return {agent_type: self._calculate_summary(agent_type)}

        summaries = {}
        for agent in self.metrics_by_agent:
            summaries[agent] = self._calculate_summary(agent)

        return summaries

    def _calculate_summary(self, agent_type: str) -> AgentMetricsSummary:
        """
        Calculate summary for a specific agent type.
        """
        metrics = self.metrics_by_agent.get(agent_type, [])

        if not metrics:
            return AgentMetricsSummary(agent_type=agent_type)

        successful = [m for m in metrics if m.success]
        failed = [m for m in metrics if not m.success]

        durations = [m.duration_seconds for m in metrics if m.duration_seconds > 0]

        return AgentMetricsSummary(
            agent_type=agent_type,
            total_executions=len(metrics),
            successful_executions=len(successful),
            failed_executions=len(failed),
            total_duration_seconds=sum(durations),
            avg_duration_seconds=sum(durations) / len(durations) if durations else 0.0,
            min_duration_seconds=min(durations) if durations else 0.0,
            max_duration_seconds=max(durations) if durations else 0.0,
            success_rate=len(successful) / len(metrics) if metrics else 0.0,
            error_rate=len(failed) / len(metrics) if metrics else 0.0,
            avg_output_length=(
                sum(m.output_length for m in metrics) // len(metrics) if metrics else 0
            ),
            avg_xml_tags=sum(m.xml_tags_found for m in metrics) / len(metrics) if metrics else 0.0,
            recent_errors=[m.error for m in failed[-5:] if m.error],  # Last 5 errors
        )


    def get_recent_metrics(
        self, agent_type: str | None = None, limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Get recent execution metrics.
        """
        if agent_type:
            metrics = self.metrics_by_agent.get(agent_type, [])
        else:
            metrics = self.metrics

        recent = sorted(metrics, key=lambda m: m.started_at, reverse=True)[:limit]

        return [
            {
                "agent_type": m.agent_type,
                "task_id": m.task_id,
                "started_at": m.started_at.isoformat(),
                "duration_seconds": m.duration_seconds,
                "success": m.success,
                "output_length": m.output_length,
                "xml_tags_found": m.xml_tags_found,
                "error": m.error,
                "metadata": m.metadata,
            }
            for m in recent
        ]

    def get_performance_trends(self, agent_type: str, hours: int = 24) -> dict[str, Any]:
        """
        Get performance trends over time.
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        metrics = [m for m in self.metrics_by_agent.get(agent_type, []) if m.started_at >= cutoff]

        if not metrics:
            return {"agent_type": agent_type, "no_data": True}

        # Group by hour
        hourly_data = defaultdict(lambda: {"count": 0, "success": 0, "total_duration": 0.0})

        for m in metrics:
            hour_key = m.started_at.strftime("%Y-%m-%d %H:00")
            hourly_data[hour_key]["count"] += 1
            if m.success:
                hourly_data[hour_key]["success"] += 1
            hourly_data[hour_key]["total_duration"] += m.duration_seconds

        # Calculate trends
        trends = []
        for hour, data in sorted(hourly_data.items()):
            trends.append(
                {
                    "hour": hour,
                    "executions": data["count"],
                    "success_rate": data["success"] / data["count"] if data["count"] > 0 else 0.0,
                    "avg_duration": (
                        data["total_duration"] / data["count"] if data["count"] > 0 else 0.0
                    ),
                },
            )

        return {
            "agent_type": agent_type,
            "period_hours": hours,
            "total_executions": len(metrics),
            "trends": trends,
        }

    def export_metrics(self, filepath: str) -> None:
        """
        Export metrics to JSON file.
        """
        data = {
            "exported_at": datetime.utcnow().isoformat(),
            "total_metrics": len(self.metrics),
            "summaries": {
                agent: {
                    **self._calculate_summary(agent).__dict__,
                    "recent_errors": self._calculate_summary(agent).recent_errors,
                }
                for agent in self.metrics_by_agent
            },
            "recent_metrics": self.get_recent_metrics(limit=100),
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def get_dashboard_data(self) -> dict[str, Any]:
        """
        Get data formatted for dashboard display.
        """
        summaries = self.get_summary()

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total_executions": len(self.metrics),
            "active_executions": len(self.active_executions),
            "agent_summaries": {
                agent: {
                    "total": summary.total_executions,
                    "success_rate": f"{summary.success_rate * 100:.1f}%",
                    "avg_duration": f"{summary.avg_duration_seconds:.2f}s",
                    "avg_xml_tags": f"{summary.avg_xml_tags:.1f}",
                }
                for agent, summary in summaries.items()
            },
            "recent_executions": self.get_recent_metrics(limit=5),
        }

    def clear_old_metrics(self, days: int = 7) -> int:
        """
        Clear metrics older than specified days.
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        initial_count = len(self.metrics)

        # Filter metrics
        self.metrics = [m for m in self.metrics if m.started_at >= cutoff]

        # Rebuild metrics_by_agent
        self.metrics_by_agent.clear()
        for metric in self.metrics:
            self.metrics_by_agent[metric.agent_type].append(metric)

        return initial_count - len(self.metrics)


# Global metrics collector instance
_metrics_collector: AgentMetricsCollector | None = None


def get_metrics_collector() -> AgentMetricsCollector:
    """
    Get the global metrics collector instance.
    """
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = AgentMetricsCollector()
    return _metrics_collector
