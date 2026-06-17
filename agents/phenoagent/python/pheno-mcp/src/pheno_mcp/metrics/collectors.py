"""Metric Collection Utilities for MCP.

Additional metric collection and aggregation utilities for MCP agents.
"""

import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class PerformanceSnapshot:
    """
    Snapshot of performance metrics at a point in time.
    """

    timestamp: datetime
    agent_type: str
    requests_per_second: float = 0.0
    avg_response_time: float = 0.0
    error_rate: float = 0.0
    active_requests: int = 0
    cpu_usage: float = 0.0
    memory_usage_mb: float = 0.0


class MetricsAggregator:
    """
    Aggregate metrics across multiple agents and time periods.
    """

    def __init__(self):
        self.snapshots: list[PerformanceSnapshot] = []
        self.aggregated_data: dict[str, dict[str, Any]] = defaultdict(dict)

    def add_snapshot(self, snapshot: PerformanceSnapshot) -> None:
        """
        Add a performance snapshot.
        """
        self.snapshots.append(snapshot)

        # Update aggregated data
        agent_type = snapshot.agent_type
        if agent_type not in self.aggregated_data:
            self.aggregated_data[agent_type] = {
                "total_snapshots": 0,
                "avg_rps": 0.0,
                "avg_response_time": 0.0,
                "avg_error_rate": 0.0,
                "peak_active_requests": 0,
            }

        data = self.aggregated_data[agent_type]
        count = data["total_snapshots"]

        # Update rolling averages
        data["avg_rps"] = (data["avg_rps"] * count + snapshot.requests_per_second) / (count + 1)
        data["avg_response_time"] = (
            data["avg_response_time"] * count + snapshot.avg_response_time
        ) / (count + 1)
        data["avg_error_rate"] = (data["avg_error_rate"] * count + snapshot.error_rate) / (
            count + 1
        )
        data["peak_active_requests"] = max(data["peak_active_requests"], snapshot.active_requests)
        data["total_snapshots"] = count + 1

    def get_aggregated_metrics(self, agent_type: str | None = None) -> dict[str, dict[str, Any]]:
        """
        Get aggregated metrics.
        """
        if agent_type:
            return {agent_type: self.aggregated_data.get(agent_type, {})}
        return dict(self.aggregated_data)

    def get_time_series(
        self, agent_type: str, metric: str = "requests_per_second",
    ) -> list[dict[str, Any]]:
        """
        Get time series data for a specific metric.
        """
        agent_snapshots = [s for s in self.snapshots if s.agent_type == agent_type]

        return [
            {
                "timestamp": s.timestamp.isoformat(),
                "value": getattr(s, metric, 0),
            }
            for s in sorted(agent_snapshots, key=lambda x: x.timestamp)
        ]


class PerformanceTracker:
    """
    Track real-time performance metrics.
    """

    def __init__(self):
        self.request_times: dict[str, list[float]] = defaultdict(list)
        self.error_counts: dict[str, int] = defaultdict(int)
        self.success_counts: dict[str, int] = defaultdict(int)
        self.active_requests: dict[str, int] = defaultdict(int)
        self.start_times: dict[str, float] = {}

    def start_request(self, agent_type: str, request_id: str) -> None:
        """
        Start tracking a request.
        """
        self.start_times[request_id] = time.time()
        self.active_requests[agent_type] += 1

    def end_request(self, agent_type: str, request_id: str, success: bool = True) -> None:
        """
        End tracking a request.
        """
        if request_id in self.start_times:
            duration = time.time() - self.start_times.pop(request_id)
            self.request_times[agent_type].append(duration)

            if success:
                self.success_counts[agent_type] += 1
            else:
                self.error_counts[agent_type] += 1

            self.active_requests[agent_type] = max(0, self.active_requests[agent_type] - 1)

    def get_metrics(self, agent_type: str) -> dict[str, Any]:
        """
        Get current metrics for an agent type.
        """
        times = self.request_times.get(agent_type, [])
        total_requests = self.success_counts[agent_type] + self.error_counts[agent_type]

        return {
            "agent_type": agent_type,
            "total_requests": total_requests,
            "successful_requests": self.success_counts[agent_type],
            "failed_requests": self.error_counts[agent_type],
            "active_requests": self.active_requests[agent_type],
            "avg_response_time": sum(times) / len(times) if times else 0.0,
            "min_response_time": min(times) if times else 0.0,
            "max_response_time": max(times) if times else 0.0,
            "error_rate": (
                self.error_counts[agent_type] / total_requests if total_requests > 0 else 0.0
            ),
        }

    def get_all_metrics(self) -> dict[str, dict[str, Any]]:
        """
        Get metrics for all tracked agent types.
        """
        return {
            agent_type: self.get_metrics(agent_type)
            for agent_type in set(
                list(self.request_times.keys())
                + list(self.error_counts.keys())
                + list(self.success_counts.keys()),
            )
        }

    def reset_metrics(self, agent_type: str | None = None) -> None:
        """
        Reset metrics for specific agent type or all.
        """
        if agent_type:
            self.request_times[agent_type].clear()
            self.error_counts[agent_type] = 0
            self.success_counts[agent_type] = 0
            self.active_requests[agent_type] = 0
        else:
            self.request_times.clear()
            self.error_counts.clear()
            self.success_counts.clear()
            self.active_requests.clear()
            self.start_times.clear()


def create_metrics_dashboard(
    collector: "AgentMetricsCollector",
    aggregator: MetricsAggregator | None = None,
    tracker: PerformanceTracker | None = None,
) -> dict[str, Any]:
    """Create comprehensive metrics dashboard data.

    Args:
        collector: AgentMetricsCollector instance
        aggregator: Optional MetricsAggregator instance
        tracker: Optional PerformanceTracker instance

    Returns:
        Dict containing comprehensive dashboard data
    """
    dashboard = {
        "timestamp": datetime.utcnow().isoformat(),
        "overview": {
            "total_executions": len(collector.metrics),
            "active_executions": len(collector.active_executions),
            "agent_types": len(collector.metrics_by_agent),
        },
        "agent_summaries": {},
        "recent_executions": collector.get_recent_metrics(limit=10),
    }

    # Add agent summaries
    summaries = collector.get_summary()
    for agent_type, summary in summaries.items():
        dashboard["agent_summaries"][agent_type] = {
            "total_executions": summary.total_executions,
            "success_rate": f"{summary.success_rate * 100:.1f}%",
            "error_rate": f"{summary.error_rate * 100:.1f}%",
            "avg_duration": f"{summary.avg_duration_seconds:.2f}s",
            "min_duration": f"{summary.min_duration_seconds:.2f}s",
            "max_duration": f"{summary.max_duration_seconds:.2f}s",
        }

    # Add aggregated metrics if available
    if aggregator:
        dashboard["aggregated_metrics"] = aggregator.get_aggregated_metrics()

    # Add real-time performance metrics if available
    if tracker:
        dashboard["performance_metrics"] = tracker.get_all_metrics()

    return dashboard


class MetricsExporter:
    """
    Export metrics in various formats.
    """

    @staticmethod
    def to_prometheus(collector: "AgentMetricsCollector") -> str:
        """
        Export metrics in Prometheus format.
        """
        lines = []

        summaries = collector.get_summary()
        for agent_type, summary in summaries.items():
            # Total executions
            lines.append(
                f'mcp_agent_executions_total{{agent_type="{agent_type}"}} '
                f"{summary.total_executions}",
            )

            # Success rate
            lines.append(
                f'mcp_agent_success_rate{{agent_type="{agent_type}"}} ' f"{summary.success_rate}",
            )

            # Average duration
            lines.append(
                f'mcp_agent_duration_seconds{{agent_type="{agent_type}",stat="avg"}} '
                f"{summary.avg_duration_seconds}",
            )

            # Min duration
            lines.append(
                f'mcp_agent_duration_seconds{{agent_type="{agent_type}",stat="min"}} '
                f"{summary.min_duration_seconds}",
            )

            # Max duration
            lines.append(
                f'mcp_agent_duration_seconds{{agent_type="{agent_type}",stat="max"}} '
                f"{summary.max_duration_seconds}",
            )

        return "\n".join(lines)

    @staticmethod
    def to_json(collector: "AgentMetricsCollector") -> dict[str, Any]:
        """
        Export metrics in JSON format.
        """
        return collector.get_dashboard_data()

    @staticmethod
    def to_csv(collector: "AgentMetricsCollector") -> str:
        """
        Export metrics in CSV format.
        """
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(
            [
                "agent_type",
                "task_id",
                "started_at",
                "duration_seconds",
                "success",
                "output_length",
                "xml_tags_found",
                "error",
            ],
        )

        # Data
        for metric in collector.metrics:
            writer.writerow(
                [
                    metric.agent_type,
                    metric.task_id,
                    metric.started_at.isoformat(),
                    metric.duration_seconds,
                    metric.success,
                    metric.output_length,
                    metric.xml_tags_found,
                    metric.error or "",
                ],
            )

        return output.getvalue()
