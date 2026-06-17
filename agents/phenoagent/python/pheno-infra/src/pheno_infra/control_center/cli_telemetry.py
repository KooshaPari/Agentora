"""Telemetry and monitoring for CLI command execution.

Provides metrics collection, performance tracking, and monitoring capabilities for the
CLI bridge system.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CommandMetrics:
    """
    Metrics for a single command execution.
    """

    command_id: str
    """
    Unique command identifier.
    """

    command: list[str]
    """
    The command that was executed.
    """

    project_name: str | None = None
    """
    Associated project name.
    """

    start_time: float = field(default_factory=time.time)
    """
    Command start timestamp.
    """

    end_time: float | None = None
    """
    Command end timestamp.
    """

    exit_code: int | None = None
    """
    Process exit code.
    """

    stdout_lines_count: int = 0
    """
    Number of stdout lines captured.
    """

    stderr_lines_count: int = 0
    """
    Number of stderr lines captured.
    """

    memory_usage_mb: float | None = None
    """
    Peak memory usage in MB.
    """

    cpu_time_seconds: float | None = None
    """
    Total CPU time used.
    """

    @property
    def duration(self) -> float | None:
        """
        Command duration in seconds.
        """
        if self.end_time:
            return self.end_time - self.start_time
        return None

    @property
    def success(self) -> bool:
        """
        Whether command completed successfully.
        """
        return self.exit_code == 0

    @property
    def performance_score(self) -> float | None:
        """
        Calculated performance score (lower is better).
        """
        if not self.duration:
            return None

        score = self.duration

        # Penalize stderr output
        if self.stderr_lines_count > 0:
            score *= 1 + self.stderr_lines_count * 0.1

        # Penalize high memory usage
        if self.memory_usage_mb and self.memory_usage_mb > 100:
            score *= 1 + (self.memory_usage_mb - 100) * 0.01

        return score


class CLITelemetry:
    """Telemetry system for CLI command execution.

    Collects metrics, tracks performance trends, and provides monitoring capabilities
    for CLI operations.
    """

    def __init__(self, max_history: int = 1000):
        """
        Initialize CLI telemetry system.
        """
        self.max_history = max_history

        # Command metrics history
        self.command_metrics: dict[str, CommandMetrics] = {}

        # Performance aggregates
        self.performance_stats: dict[str, dict[str, Any]] = {}

        # Real-time callbacks
        self.metrics_callbacks: list[callable] = []

        logger.info("CLI Telemetry initialized")

    def start_command_tracking(
        self,
        command_id: str,
        command: list[str],
        project_name: str | None = None,
    ) -> None:
        """Start tracking a command execution.

        Args:
            command_id: Unique command identifier
            command: Command being executed
            project_name: Associated project name
        """
        metrics = CommandMetrics(
            command_id=command_id,
            command=command,
            project_name=project_name,
        )

        self.command_metrics[command_id] = metrics

        # Notify callbacks
        for callback in self.metrics_callbacks:
            try:
                callback(
                    "command_started",
                    {
                        "command_id": command_id,
                        "command": command,
                        "project_name": project_name,
                        "start_time": metrics.start_time,
                    },
                )
            except Exception as e:
                logger.warning(f"Telemetry callback error: {e}")

    def update_command_tracking(
        self,
        command_id: str,
        **updates,
    ) -> None:
        """Update tracking data for a command.

        Args:
            command_id: Command identifier
            **updates: Fields to update (end_time, exit_code, etc.)
        """
        metrics = self.command_metrics.get(command_id)
        if not metrics:
            logger.warning(f"Unknown command ID for telemetry: {command_id}")
            return

        # Update fields
        for key, value in updates.items():
            if hasattr(metrics, key):
                setattr(metrics, key, value)

        # Notify callbacks
        for callback in self.metrics_callbacks:
            try:
                callback(
                    "command_updated",
                    {
                        "command_id": command_id,
                        "updates": updates,
                    },
                )
            except Exception as e:
                logger.warning(f"Telemetry callback error: {e}")

    def finish_command_tracking(self, command_id: str) -> CommandMetrics | None:
        """Finish tracking a command and calculate final metrics.

        Args:
            command_id: Command identifier

        Returns:
            Final command metrics
        """
        metrics = self.command_metrics.get(command_id)
        if not metrics:
            logger.warning(f"Unknown command ID for telemetry: {command_id}")
            return None

        # Set end time if not already set
        if not metrics.end_time:
            metrics.end_time = time.time()

        # Update performance stats
        self._update_performance_stats(metrics)

        # Notify callbacks
        for callback in self.metrics_callbacks:
            try:
                callback(
                    "command_finished",
                    {
                        "command_id": command_id,
                        "metrics": metrics,
                    },
                )
            except Exception as e:
                logger.warning(f"Telemetry callback error: {e}")

        # Clean up old metrics if needed
        if len(self.command_metrics) > self.max_history:
            self._cleanup_old_metrics()

        return metrics

    def get_command_metrics(self, command_id: str) -> CommandMetrics | None:
        """
        Get metrics for a specific command.
        """
        return self.command_metrics.get(command_id)

    def get_performance_stats(
        self,
        project_name: str | None = None,
        command_filter: str | None = None,
    ) -> dict[str, Any]:
        """Get performance statistics.

        Args:
            project_name: Filter by project name
            command_filter: Filter by command pattern

        Returns:
            Performance statistics dictionary
        """
        # Filter metrics
        filtered_metrics = []
        for metrics in self.command_metrics.values():
            if project_name and metrics.project_name != project_name:
                continue
            if command_filter and command_filter not in " ".join(metrics.command):
                continue
            if metrics.duration is not None:  # Only include completed commands
                filtered_metrics.append(metrics)

        if not filtered_metrics:
            return {
                "count": 0,
                "avg_duration": 0,
                "success_rate": 0,
                "total_stderr_lines": 0,
            }

        # Calculate statistics
        durations = [m.duration for m in filtered_metrics if m.duration is not None]
        success_count = sum(1 for m in filtered_metrics if m.success)
        total_stderr = sum(m.stderr_lines_count for m in filtered_metrics)

        return {
            "count": len(filtered_metrics),
            "avg_duration": sum(durations) / len(durations) if durations else 0,
            "min_duration": min(durations) if durations else 0,
            "max_duration": max(durations) if durations else 0,
            "success_rate": success_count / len(filtered_metrics),
            "total_stderr_lines": total_stderr,
            "avg_stderr_lines": total_stderr / len(filtered_metrics),
        }

    def get_active_commands(self) -> list[str]:
        """
        Get list of currently active command IDs.
        """
        return [
            cmd_id for cmd_id, metrics in self.command_metrics.items() if metrics.end_time is None
        ]

    def add_metrics_callback(self, callback: callable) -> None:
        """Add callback for metrics events.

        Args:
            callback: Function called with (event_type, data)
                     where event_type is 'command_started', 'command_updated', or 'command_finished'
        """
        self.metrics_callbacks.append(callback)

    def _update_performance_stats(self, metrics: CommandMetrics) -> None:
        """
        Update aggregated performance statistics.
        """
        # Create aggregate key
        if metrics.project_name:
            key = f"{metrics.project_name}:{metrics.command[0]}"
        else:
            key = f"global:{metrics.command[0]}"

        if key not in self.performance_stats:
            self.performance_stats[key] = {
                "count": 0,
                "total_duration": 0,
                "success_count": 0,
                "total_stderr": 0,
                "last_execution": 0,
            }

        stats = self.performance_stats[key]
        stats["count"] += 1
        stats["last_execution"] = time.time()

        if metrics.duration is not None:
            stats["total_duration"] += metrics.duration

        if metrics.success:
            stats["success_count"] += 1

        stats["total_stderr"] += metrics.stderr_lines_count

    def _cleanup_old_metrics(self) -> None:
        """
        Remove old metrics to maintain history limit.
        """
        # Sort by start time and keep most recent
        sorted_metrics = sorted(
            self.command_metrics.items(),
            key=lambda x: x[1].start_time,
        )

        # Keep only the most recent
        keep_count = self.max_history - len(sorted_metrics) // 2
        self.command_metrics = dict(sorted_metrics[-keep_count:])

    def export_metrics(self, format: str = "dict") -> Any:
        """Export telemetry data in various formats.

        Args:
            format: Export format ('dict', 'json')

        Returns:
            Exported data
        """
        data = {
            "command_metrics": {
                cmd_id: {
                    "command": metrics.command,
                    "project_name": metrics.project_name,
                    "start_time": metrics.start_time,
                    "end_time": metrics.end_time,
                    "duration": metrics.duration,
                    "exit_code": metrics.exit_code,
                    "success": metrics.success,
                    "stdout_lines_count": metrics.stdout_lines_count,
                    "stderr_lines_count": metrics.stderr_lines_count,
                    "performance_score": metrics.performance_score,
                }
                for cmd_id, metrics in self.command_metrics.items()
            },
            "performance_stats": self.performance_stats,
        }

        if format == "json":
            import json

            return json.dumps(data, indent=2, default=str)

        return data


__all__ = [
    "CLITelemetry",
    "CommandMetrics",
]
