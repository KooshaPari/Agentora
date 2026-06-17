"""
Performance metrics tracking.
"""

from typing import Any, Dict, List


class PerformanceMetrics:
    """
    Track performance metrics during tests.
    """

    def __init__(self):
        self.metrics: List[Dict[str, Any]] = []

    def record(self, operation: str, duration: float, **kwargs):
        """
        Record a performance metric.
        """
        self.metrics.append({"operation": operation, "duration": duration, **kwargs})

    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics.
        """
        if not self.metrics:
            return {}

        durations = [m["duration"] for m in self.metrics]
        return {
            "total_operations": len(self.metrics),
            "avg_duration": sum(durations) / len(durations),
            "min_duration": min(durations),
            "max_duration": max(durations),
        }
