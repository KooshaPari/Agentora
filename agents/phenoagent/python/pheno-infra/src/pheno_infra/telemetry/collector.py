"""
Telemetry Collector: Collects metrics and events from KInfra components

This module provides comprehensive telemetry collection for all KInfra operations,
including performance metrics, usage patterns, error rates, and system health.
"""

import asyncio
import json
import logging
import sqlite3
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import psutil

from pheno.infra.config_schemas import KInfraConfigManager


@dataclass
class TelemetryEvent:
    """Represents a telemetry event."""
    timestamp: str
    event_type: str
    component: str
    project: str | None
    service: str | None
    metrics: dict[str, Any]
    metadata: dict[str, Any]
    severity: str = "info"


@dataclass
class PerformanceMetric:
    """Represents a performance metric."""
    timestamp: str
    component: str
    operation: str
    duration: float
    success: bool
    error_message: str | None
    resource_usage: dict[str, float]
    metadata: dict[str, Any]


@dataclass
class UsageMetric:
    """Represents a usage metric."""
    timestamp: str
    component: str
    operation: str
    project: str
    service: str
    user_id: str | None
    session_id: str | None
    metadata: dict[str, Any]


@dataclass
class HealthMetric:
    """Represents a health metric."""
    timestamp: str
    component: str
    status: str
    health_score: float
    issues: list[str]
    recommendations: list[str]
    metadata: dict[str, Any]


class TelemetryCollector:
    """Collects telemetry data from KInfra components."""

    def __init__(self, config_manager: KInfraConfigManager | None = None):
        """Initialize the telemetry collector."""
        self.config_manager = config_manager or KInfraConfigManager()
        self.config = self.config_manager.load()

        # Set up logging
        self.logger = logging.getLogger(__name__)

        # Initialize storage
        self.db_path = Path("~/.kinfra/telemetry.db").expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

        # Initialize buffers
        self.event_buffer = deque(maxlen=1000)
        self.performance_buffer = deque(maxlen=1000)
        self.usage_buffer = deque(maxlen=1000)
        self.health_buffer = deque(maxlen=1000)

        # Initialize counters
        self.counters = defaultdict(int)
        self.timers = defaultdict(list)

        # Initialize background tasks
        self._running = False
        self._flush_task = None
        self._health_check_task = None

        # Initialize system monitoring
        self._system_monitor = SystemMonitor()

        # Initialize event handlers
        self._event_handlers = []

        # Start background tasks
        self.start()

    def _init_database(self):
        """Initialize the telemetry database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                component TEXT NOT NULL,
                project TEXT,
                service TEXT,
                metrics TEXT NOT NULL,
                metadata TEXT NOT NULL,
                severity TEXT NOT NULL
            )
        """)

        # Create performance metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                component TEXT NOT NULL,
                operation TEXT NOT NULL,
                duration REAL NOT NULL,
                success BOOLEAN NOT NULL,
                error_message TEXT,
                resource_usage TEXT NOT NULL,
                metadata TEXT NOT NULL
            )
        """)

        # Create usage metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usage_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                component TEXT NOT NULL,
                operation TEXT NOT NULL,
                project TEXT NOT NULL,
                service TEXT NOT NULL,
                user_id TEXT,
                session_id TEXT,
                metadata TEXT NOT NULL
            )
        """)

        # Create health metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS health_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                component TEXT NOT NULL,
                status TEXT NOT NULL,
                health_score REAL NOT NULL,
                issues TEXT NOT NULL,
                recommendations TEXT NOT NULL,
                metadata TEXT NOT NULL
            )
        """)

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_component ON events(component)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_project ON events(project)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_performance_timestamp ON performance_metrics(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_performance_component ON performance_metrics(component)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_usage_timestamp ON usage_metrics(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_usage_project ON usage_metrics(project)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_health_timestamp ON health_metrics(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_health_component ON health_metrics(component)")

        conn.commit()
        conn.close()

    def start(self):
        """Start the telemetry collector."""
        if self._running:
            return

        self._running = True

        # Start background tasks
        self._flush_task = asyncio.create_task(self._flush_loop())
        self._health_check_task = asyncio.create_task(self._health_check_loop())

        self.logger.info("Telemetry collector started")

    def stop(self):
        """Stop the telemetry collector."""
        if not self._running:
            return

        self._running = False

        # Cancel background tasks
        if self._flush_task:
            self._flush_task.cancel()
        if self._health_check_task:
            self._health_check_task.cancel()

        # Flush remaining data
        asyncio.create_task(self._flush_all())

        self.logger.info("Telemetry collector stopped")

    async def _flush_loop(self):
        """Background task to flush telemetry data."""
        while self._running:
            try:
                await asyncio.sleep(30)  # Flush every 30 seconds
                await self._flush_all()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.exception(f"Error in flush loop: {e}")

    async def _health_check_loop(self):
        """Background task to perform health checks."""
        while self._running:
            try:
                await asyncio.sleep(60)  # Health check every minute
                await self._perform_health_check()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.exception(f"Error in health check loop: {e}")

    async def _flush_all(self):
        """Flush all buffered telemetry data to database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Flush events
            if self.event_buffer:
                events = [asdict(event) for event in self.event_buffer]
                cursor.executemany("""
                    INSERT INTO events (timestamp, event_type, component, project, service, metrics, metadata, severity)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    (event["timestamp"], event["event_type"], event["component"],
                     event["project"], event["service"], json.dumps(event["metrics"]),
                     json.dumps(event["metadata"]), event["severity"])
                    for event in events
                ])
                self.event_buffer.clear()

            # Flush performance metrics
            if self.performance_buffer:
                metrics = [asdict(metric) for metric in self.performance_buffer]
                cursor.executemany("""
                    INSERT INTO performance_metrics (timestamp, component, operation, duration, success, error_message, resource_usage, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    (metric["timestamp"], metric["component"], metric["operation"],
                     metric["duration"], metric["success"], metric["error_message"],
                     json.dumps(metric["resource_usage"]), json.dumps(metric["metadata"]))
                    for metric in metrics
                ])
                self.performance_buffer.clear()

            # Flush usage metrics
            if self.usage_buffer:
                metrics = [asdict(metric) for metric in self.usage_buffer]
                cursor.executemany("""
                    INSERT INTO usage_metrics (timestamp, component, operation, project, service, user_id, session_id, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    (metric["timestamp"], metric["component"], metric["operation"],
                     metric["project"], metric["service"], metric["user_id"],
                     metric["session_id"], json.dumps(metric["metadata"]))
                    for metric in metrics
                ])
                self.usage_buffer.clear()

            # Flush health metrics
            if self.health_buffer:
                metrics = [asdict(metric) for metric in self.health_buffer]
                cursor.executemany("""
                    INSERT INTO health_metrics (timestamp, component, status, health_score, issues, recommendations, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, [
                    (metric["timestamp"], metric["component"], metric["status"],
                     metric["health_score"], json.dumps(metric["issues"]),
                     json.dumps(metric["recommendations"]), json.dumps(metric["metadata"]))
                    for metric in metrics
                ])
                self.health_buffer.clear()

            conn.commit()
            conn.close()

        except Exception as e:
            self.logger.exception(f"Error flushing telemetry data: {e}")

    async def _perform_health_check(self):
        """Perform system health check."""
        try:
            # Get system metrics
            system_metrics = self._system_monitor.get_system_metrics()

            # Check for issues
            issues = []
            recommendations = []

            # Check CPU usage
            if system_metrics["cpu_percent"] > 80:
                issues.append("High CPU usage")
                recommendations.append("Consider optimizing resource usage")

            # Check memory usage
            if system_metrics["memory_percent"] > 85:
                issues.append("High memory usage")
                recommendations.append("Consider increasing memory or optimizing memory usage")

            # Check disk usage
            if system_metrics["disk_percent"] > 90:
                issues.append("High disk usage")
                recommendations.append("Consider cleaning up disk space")

            # Check database size
            db_size = self.db_path.stat().st_size if self.db_path.exists() else 0
            if db_size > 100 * 1024 * 1024:  # 100MB
                issues.append("Large telemetry database")
                recommendations.append("Consider archiving old telemetry data")

            # Calculate health score
            health_score = 100.0
            if issues:
                health_score -= len(issues) * 10
            if system_metrics["cpu_percent"] > 80:
                health_score -= 20
            if system_metrics["memory_percent"] > 85:
                health_score -= 20
            if system_metrics["disk_percent"] > 90:
                health_score -= 20

            health_score = max(0, health_score)

            # Record health metric
            health_metric = HealthMetric(
                timestamp=datetime.now().isoformat(),
                component="system",
                status="healthy" if health_score > 80 else "warning" if health_score > 60 else "critical",
                health_score=health_score,
                issues=issues,
                recommendations=recommendations,
                metadata=system_metrics,
            )

            self.health_buffer.append(health_metric)

            # Trigger alerts if needed
            if health_score < 60:
                await self._trigger_alert("system_health_critical", {
                    "health_score": health_score,
                    "issues": issues,
                    "recommendations": recommendations,
                })

        except Exception as e:
            self.logger.exception(f"Error performing health check: {e}")

    async def _trigger_alert(self, alert_type: str, data: dict[str, Any]):
        """Trigger an alert."""
        for handler in self._event_handlers:
            try:
                await handler(alert_type, data)
            except Exception as e:
                self.logger.exception(f"Error in alert handler: {e}")

    def add_event_handler(self, handler: Callable[[str, dict[str, Any]], None]):
        """Add an event handler."""
        self._event_handlers.append(handler)

    def record_event(self, event_type: str, component: str, metrics: dict[str, Any],
                    project: str | None = None, service: str | None = None,
                    metadata: dict[str, Any] | None = None, severity: str = "info"):
        """Record a telemetry event."""
        event = TelemetryEvent(
            timestamp=datetime.now().isoformat(),
            event_type=event_type,
            component=component,
            project=project,
            service=service,
            metrics=metrics,
            metadata=metadata or {},
            severity=severity,
        )

        self.event_buffer.append(event)
        self.counters[f"{component}.{event_type}"] += 1

        # Trigger event handlers
        asyncio.create_task(self._trigger_alert("event_recorded", asdict(event)))

    def record_performance(self, component: str, operation: str, duration: float,
                          success: bool, error_message: str | None = None,
                          resource_usage: dict[str, float] | None = None,
                          metadata: dict[str, Any] | None = None):
        """Record a performance metric."""
        metric = PerformanceMetric(
            timestamp=datetime.now().isoformat(),
            component=component,
            operation=operation,
            duration=duration,
            success=success,
            error_message=error_message,
            resource_usage=resource_usage or {},
            metadata=metadata or {},
        )

        self.performance_buffer.append(metric)
        self.timers[f"{component}.{operation}"].append(duration)

        # Keep only last 100 timings
        if len(self.timers[f"{component}.{operation}"]) > 100:
            self.timers[f"{component}.{operation}"] = self.timers[f"{component}.{operation}"][-100:]

    def record_usage(self, component: str, operation: str, project: str, service: str,
                    user_id: str | None = None, session_id: str | None = None,
                    metadata: dict[str, Any] | None = None):
        """Record a usage metric."""
        metric = UsageMetric(
            timestamp=datetime.now().isoformat(),
            component=component,
            operation=operation,
            project=project,
            service=service,
            user_id=user_id,
            session_id=session_id,
            metadata=metadata or {},
        )

        self.usage_buffer.append(metric)

    def get_counters(self) -> dict[str, int]:
        """Get current counters."""
        return dict(self.counters)

    def get_timings(self) -> dict[str, list[float]]:
        """Get current timings."""
        return dict(self.timers)

    def get_health_status(self) -> dict[str, Any]:
        """Get current health status."""
        if not self.health_buffer:
            return {"status": "unknown", "health_score": 0, "issues": [], "recommendations": []}

        latest_health = self.health_buffer[-1]
        return {
            "status": latest_health.status,
            "health_score": latest_health.health_score,
            "issues": latest_health.issues,
            "recommendations": latest_health.recommendations,
            "timestamp": latest_health.timestamp,
        }

    async def get_metrics_summary(self, hours: int = 24) -> dict[str, Any]:
        """Get metrics summary for the last N hours."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            since = (datetime.now() - timedelta(hours=hours)).isoformat()

            # Get event counts
            cursor.execute("""
                SELECT event_type, component, COUNT(*) as count
                FROM events
                WHERE timestamp >= ?
                GROUP BY event_type, component
            """, (since,))
            event_counts = {f"{row[1]}.{row[0]}": row[2] for row in cursor.fetchall()}

            # Get performance metrics
            cursor.execute("""
                SELECT component, operation, AVG(duration) as avg_duration,
                       COUNT(*) as count, SUM(success) as success_count
                FROM performance_metrics
                WHERE timestamp >= ?
                GROUP BY component, operation
            """, (since,))
            performance_metrics = {}
            for row in cursor.fetchall():
                key = f"{row[0]}.{row[1]}"
                performance_metrics[key] = {
                    "avg_duration": row[2],
                    "count": row[3],
                    "success_rate": row[4] / row[3] if row[3] > 0 else 0,
                }

            # Get usage metrics
            cursor.execute("""
                SELECT project, service, COUNT(*) as count
                FROM usage_metrics
                WHERE timestamp >= ?
                GROUP BY project, service
            """, (since,))
            usage_metrics = {f"{row[0]}.{row[1]}": row[2] for row in cursor.fetchall()}

            # Get health metrics
            cursor.execute("""
                SELECT component, AVG(health_score) as avg_health_score,
                       COUNT(*) as count
                FROM health_metrics
                WHERE timestamp >= ?
                GROUP BY component
            """, (since,))
            health_metrics = {row[0]: {"avg_health_score": row[1], "count": row[2]} for row in cursor.fetchall()}

            conn.close()

            return {
                "period_hours": hours,
                "event_counts": event_counts,
                "performance_metrics": performance_metrics,
                "usage_metrics": usage_metrics,
                "health_metrics": health_metrics,
                "current_counters": self.get_counters(),
                "current_timings": self.get_timings(),
                "current_health": self.get_health_status(),
            }

        except Exception as e:
            self.logger.exception(f"Error getting metrics summary: {e}")
            return {"error": str(e)}


class SystemMonitor:
    """Monitors system resources and performance."""

    def __init__(self):
        """Initialize the system monitor."""
        self.logger = logging.getLogger(__name__)

    def get_system_metrics(self) -> dict[str, Any]:
        """Get current system metrics."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)

            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent

            # Disk usage
            disk = psutil.disk_usage("/")
            disk_percent = (disk.used / disk.total) * 100

            # Network I/O
            network = psutil.net_io_counters()

            # Process count
            process_count = len(psutil.pids())

            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "memory_available": memory.available,
                "memory_total": memory.total,
                "disk_percent": disk_percent,
                "disk_free": disk.free,
                "disk_total": disk.total,
                "network_bytes_sent": network.bytes_sent,
                "network_bytes_recv": network.bytes_recv,
                "process_count": process_count,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.exception(f"Error getting system metrics: {e}")
            return {
                "cpu_percent": 0,
                "memory_percent": 0,
                "memory_available": 0,
                "memory_total": 0,
                "disk_percent": 0,
                "disk_free": 0,
                "disk_total": 0,
                "network_bytes_sent": 0,
                "network_bytes_recv": 0,
                "process_count": 0,
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
            }
