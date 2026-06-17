"""Process monitoring and logging capabilities.

Provides process monitoring, metrics collection, and logging utilities for process
lifecycle tracking.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any

import psutil

logger = logging.getLogger(__name__)


@dataclass
class ProcessMetrics:
    """
    Metrics for a monitored process.
    """

    pid: int
    """
    Process ID.
    """

    name: str
    """
    Process name.
    """

    start_time: float = field(default_factory=time.time)
    """
    Process start timestamp.
    """

    cpu_percent: float | None = None
    """
    Current CPU usage percentage.
    """

    memory_mb: float | None = None
    """
    Current memory usage in MB.
    """

    open_files: int | None = None
    """
    Number of open file descriptors.
    """

    num_threads: int | None = None
    """
    Number of threads.
    """

    last_update: float = field(default_factory=time.time)
    """
    Last metrics update timestamp.
    """

    @property
    def age_seconds(self) -> float:
        """
        Process age in seconds.
        """
        return time.time() - self.start_time

    @property
    def is_active(self) -> bool:
        """
        Whether process appears to be active.
        """
        try:
            proc = psutil.Process(self.pid)
            return proc.is_running()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False


class ProcessMonitor:
    """Monitor process resource usage and provide logging capabilities.

    Provides:
    - Real-time metrics collection
    - Resource usage logging
    - Performance alerts
    - Historical data tracking
    """

    def __init__(self, max_processes: int = 100):
        """
        Initialize process monitor.
        """
        self.max_processes = max_processes

        # Monitored processes
        self.monitored_processes: dict[int, ProcessMetrics] = {}

        # Historical data (limited)
        self.metrics_history: list[dict[str, Any]] = []
        self.max_history = 1000

        # Monitoring callbacks
        self.metrics_callbacks: list[callable] = []

        # Alert thresholds
        self.cpu_threshold = 80.0  # CPU usage alert threshold
        self.memory_threshold_mb = 1000.0  # Memory usage alert threshold

        logger.info("Process Monitor initialized")

    def start_monitoring(self, pid: int, name: str | None = None) -> ProcessMetrics | None:
        """Start monitoring a process.

        Args:
            pid: Process ID to monitor
            name: Process name (auto-detected if None)

        Returns:
            ProcessMetrics object if successful, None otherwise
        """
        try:
            proc = psutil.Process(pid)

            if not name:
                name = proc.name()

            if len(self.monitored_processes) >= self.max_processes:
                logger.warning(
                    f"Max processes ({self.max_processes}) reached, cannot monitor PID {pid}",
                )
                return None

            metrics = ProcessMetrics(pid=pid, name=name)
            self.monitored_processes[pid] = metrics

            # Initial metrics collection
            self._update_process_metrics(metrics)

            logger.info(f"Started monitoring process {pid} ({name})")
            return metrics

        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            logger.exception(f"Cannot start monitoring process {pid}: {e}")
            return None

    def stop_monitoring(self, pid: int) -> ProcessMetrics | None:
        """Stop monitoring a process and return final metrics.

        Args:
            pid: Process ID to stop monitoring

        Returns:
            Final ProcessMetrics object
        """
        metrics = self.monitored_processes.pop(pid, None)
        if metrics:
            # Final metrics update
            self._update_process_metrics(metrics)

            # Add to history
            self._add_to_history(metrics, "stopped")

            logger.info(f"Stopped monitoring process {pid} ({metrics.name})")
            return metrics

        return None

    def update_all_metrics(self) -> None:
        """
        Update metrics for all monitored processes.
        """
        for metrics in self.monitored_processes.values():
            if metrics.is_active:
                self._update_process_metrics(metrics)

    def get_process_metrics(self, pid: int) -> ProcessMetrics | None:
        """
        Get metrics for a specific process.
        """
        return self.monitored_processes.get(pid)

    def get_all_metrics(self) -> dict[int, ProcessMetrics]:
        """
        Get metrics for all monitored processes.
        """
        return self.monitored_processes.copy()

    def get_active_processes(self) -> list[int]:
        """
        Get list of currently active process IDs.
        """
        return [pid for pid, metrics in self.monitored_processes.items() if metrics.is_active]

    def get_process_history(
        self,
        pid: int | None = None,
        event_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get metrics history.

        Args:
            pid: Filter by process ID
            event_type: Filter by event type

        Returns:
            List of historical events
        """
        history = self.metrics_history.copy()

        if pid:
            history = [h for h in history if h.get("pid") == pid]

        if event_type:
            history = [h for h in history if h.get("event_type") == event_type]

        return history

    def add_metrics_callback(self, callback: callable) -> None:
        """Add callback for metrics events.

        Args:
            callback: Function called with (event_type, data)
        """
        self.metrics_callbacks.append(callback)

    def set_alert_thresholds(
        self, cpu_percent: float | None = None, memory_mb: float | None = None,
    ) -> None:
        """
        Set alert thresholds for resource usage.
        """
        if cpu_percent is not None:
            self.cpu_threshold = cpu_percent
        if memory_mb is not None:
            self.memory_threshold_mb = memory_mb

    def _update_process_metrics(self, metrics: ProcessMetrics) -> None:
        """
        Update metrics for a process.
        """
        try:
            proc = psutil.Process(metrics.pid)

            # Collect current metrics
            metrics.cpu_percent = proc.cpu_percent()
            memory_info = proc.memory_info()
            metrics.memory_mb = memory_info.rss / (1024 * 1024)  # Convert to MB

            try:
                metrics.num_threads = proc.num_threads()
            except (AttributeError, psutil.AccessDenied):
                metrics.num_threads = None

            try:
                metrics.open_files = len(proc.open_files())
            except (AttributeError, psutil.AccessDenied):
                metrics.open_files = None

            metrics.last_update = time.time()

            # Check for alerts
            self._check_alerts(metrics)

            # Notify callbacks
            for callback in self.metrics_callbacks:
                try:
                    callback(
                        "metrics_updated",
                        {
                            "pid": metrics.pid,
                            "name": metrics.name,
                            "metrics": metrics,
                        },
                    )
                except Exception as e:
                    logger.warning(f"Metrics callback error: {e}")

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            # Process no longer exists
            self._add_to_history(metrics, "terminated")
            logger.debug(f"Process {metrics.pid} no longer exists")

    def _check_alerts(self, metrics: ProcessMetrics) -> None:
        """
        Check if metrics exceed alert thresholds.
        """
        alerts = []

        if metrics.cpu_percent is not None and metrics.cpu_percent > self.cpu_threshold:
            alerts.append(f"CPU usage high: {metrics.cpu_percent:.1f}%")

        if metrics.memory_mb is not None and metrics.memory_mb > self.memory_threshold_mb:
            alerts.append(f"Memory usage high: {metrics.memory_mb:.1f}MB")

        if alerts:
            message = f"Process {metrics.pid} ({metrics.name}) - " + "; ".join(alerts)

            # Add to history as alert event
            self._add_to_history(metrics, "alert", message)

            # Notify callbacks
            for callback in self.metrics_callbacks:
                try:
                    callback(
                        "alert",
                        {
                            "pid": metrics.pid,
                            "name": metrics.name,
                            "message": message,
                            "metrics": metrics,
                        },
                    )
                except Exception as e:
                    logger.warning(f"Alert callback error: {e}")

            logger.warning(message)

    def _add_to_history(
        self, metrics: ProcessMetrics, event_type: str, message: str | None = None,
    ) -> None:
        """
        Add event to history.
        """
        event = {
            "timestamp": time.time(),
            "pid": metrics.pid,
            "name": metrics.name,
            "event_type": event_type,
            "cpu_percent": metrics.cpu_percent,
            "memory_mb": metrics.memory_mb,
            "open_files": metrics.open_files,
            "num_threads": metrics.num_threads,
            "message": message,
        }

        self.metrics_history.append(event)

        # Maintain history limit
        if len(self.metrics_history) > self.max_history:
            self.metrics_history = self.metrics_history[-self.max_history :]

    def export_metrics(self, format: str = "dict") -> Any:
        """Export monitoring data in various formats.

        Args:
            format: Export format ('dict', 'json', 'csv')

        Returns:
            Exported data
        """
        data = {
            "current_metrics": {
                str(pid): {
                    "name": metrics.name,
                    "cpu_percent": metrics.cpu_percent,
                    "memory_mb": metrics.memory_mb,
                    "open_files": metrics.open_files,
                    "num_threads": metrics.num_threads,
                    "age_seconds": metrics.age_seconds,
                    "is_active": metrics.is_active,
                }
                for pid, metrics in self.monitored_processes.items()
            },
            "history": self.metrics_history,
            "alert_thresholds": {
                "cpu_percent": self.cpu_threshold,
                "memory_mb": self.memory_threshold_mb,
            },
        }

        if format == "json":
            import json

            return json.dumps(data, indent=2, default=str)
        if format == "csv":
            import csv
            import io

            output = io.StringIO()
            writer = csv.writer(output)

            # Write history as CSV
            writer.writerow(
                [
                    "timestamp",
                    "pid",
                    "name",
                    "event_type",
                    "cpu_percent",
                    "memory_mb",
                    "open_files",
                    "num_threads",
                    "message",
                ],
            )

            for event in self.metrics_history:
                writer.writerow(
                    [
                        event.get("timestamp"),
                        event.get("pid"),
                        event.get("name"),
                        event.get("event_type"),
                        event.get("cpu_percent"),
                        event.get("memory_mb"),
                        event.get("open_files"),
                        event.get("num_threads"),
                        event.get("message"),
                    ],
                )

            return output.getvalue()

        return data

    def cleanup_stale_processes(self) -> None:
        """
        Remove processes that are no longer running.
        """
        stale_pids = [
            pid for pid, metrics in self.monitored_processes.items() if not metrics.is_active
        ]

        for pid in stale_pids:
            metrics = self.monitored_processes.pop(pid)
            self._add_to_history(metrics, "cleanup")
            logger.debug(f"Cleaned up stale process {pid}")


__all__ = [
    "ProcessMetrics",
    "ProcessMonitor",
]
