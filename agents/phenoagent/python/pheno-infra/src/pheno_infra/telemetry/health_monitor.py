"""
Health Monitor: Monitors system health and provides alerts

This module provides comprehensive health monitoring for KInfra components,
including system health, component health, and automated alerting.
"""

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import aiohttp
import psutil


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Represents a health check."""
    name: str
    component: str
    status: HealthStatus
    message: str
    timestamp: str
    duration: float
    metadata: dict[str, Any]


@dataclass
class HealthAlert:
    """Represents a health alert."""
    alert_id: str
    component: str
    status: HealthStatus
    message: str
    timestamp: str
    resolved: bool
    metadata: dict[str, Any]


class HealthMonitor:
    """Monitors health of KInfra components."""

    def __init__(self, config_manager=None):
        """Initialize the health monitor."""
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)

        # Health check registry
        self.health_checks = {}
        self.alert_handlers = []

        # Alert state
        self.active_alerts = {}
        self.alert_history = []

        # Monitoring state
        self._running = False
        self._monitor_task = None

        # Health thresholds
        self.thresholds = {
            "cpu_percent": 80.0,
            "memory_percent": 85.0,
            "disk_percent": 90.0,
            "response_time": 5.0,
            "error_rate": 0.05,  # 5%
            "health_score": 80.0,
        }

    def start(self):
        """Start health monitoring."""
        if self._running:
            return

        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        self.logger.info("Health monitor started")

    def stop(self):
        """Stop health monitoring."""
        if not self._running:
            return

        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
        self.logger.info("Health monitor stopped")

    async def _monitor_loop(self):
        """Main monitoring loop."""
        while self._running:
            try:
                await self._run_health_checks()
                await asyncio.sleep(30)  # Check every 30 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.exception(f"Error in health monitor loop: {e}")

    async def _run_health_checks(self):
        """Run all registered health checks."""
        for check_name, check_func in self.health_checks.items():
            try:
                start_time = time.time()
                result = await check_func()
                duration = time.time() - start_time

                # Create health check record
                health_check = HealthCheck(
                    name=check_name,
                    component=result.get("component", "unknown"),
                    status=HealthStatus(result.get("status", "unknown")),
                    message=result.get("message", ""),
                    timestamp=datetime.now().isoformat(),
                    duration=duration,
                    metadata=result.get("metadata", {}),
                )

                # Process health check result
                await self._process_health_check(health_check)

            except Exception as e:
                self.logger.exception(f"Error running health check {check_name}: {e}")

    async def _process_health_check(self, health_check: HealthCheck):
        """Process a health check result."""
        # Check if this is a new alert or status change
        alert_key = f"{health_check.component}.{health_check.name}"

        if health_check.status in [HealthStatus.WARNING, HealthStatus.CRITICAL]:
            if alert_key not in self.active_alerts:
                # New alert
                await self._create_alert(health_check)
            else:
                # Update existing alert
                await self._update_alert(alert_key, health_check)
        elif alert_key in self.active_alerts:
            # Resolve alert
            await self._resolve_alert(alert_key, health_check)

    async def _create_alert(self, health_check: HealthCheck):
        """Create a new alert."""
        alert_id = f"{health_check.component}.{health_check.name}.{int(time.time())}"

        alert = HealthAlert(
            alert_id=alert_id,
            component=health_check.component,
            status=health_check.status,
            message=health_check.message,
            timestamp=health_check.timestamp,
            resolved=False,
            metadata=health_check.metadata,
        )

        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert)

        # Trigger alert handlers
        for handler in self.alert_handlers:
            try:
                await handler(alert)
            except Exception as e:
                self.logger.exception(f"Error in alert handler: {e}")

        self.logger.warning(f"Health alert created: {alert_id} - {health_check.message}")

    async def _update_alert(self, alert_key: str, health_check: HealthCheck):
        """Update an existing alert."""
        # Find the alert by component and name
        for alert in self.active_alerts.values():
            if f"{alert.component}.{health_check.name}" == alert_key:
                alert.message = health_check.message
                alert.timestamp = health_check.timestamp
                alert.metadata.update(health_check.metadata)
                break

    async def _resolve_alert(self, alert_key: str, health_check: HealthCheck):
        """Resolve an alert."""
        # Find and resolve the alert
        for alert_id, alert in self.active_alerts.items():
            if f"{alert.component}.{health_check.name}" == alert_key:
                alert.resolved = True
                alert.timestamp = health_check.timestamp
                del self.active_alerts[alert_id]
                self.logger.info(f"Health alert resolved: {alert_id}")
                break

    def register_health_check(self, name: str, check_func: Callable):
        """Register a health check function."""
        self.health_checks[name] = check_func
        self.logger.info(f"Health check registered: {name}")

    def add_alert_handler(self, handler: Callable[[HealthAlert], None]):
        """Add an alert handler."""
        self.alert_handlers.append(handler)

    def get_health_status(self) -> dict[str, Any]:
        """Get current health status."""
        return {
            "active_alerts": len(self.active_alerts),
            "total_alerts": len(self.alert_history),
            "health_checks": len(self.health_checks),
            "status": "healthy" if not self.active_alerts else "warning",
            "alerts": [
                {
                    "id": alert.alert_id,
                    "component": alert.component,
                    "status": alert.status.value,
                    "message": alert.message,
                    "timestamp": alert.timestamp,
                }
                for alert in self.active_alerts.values()
            ],
        }

    def get_alert_history(self, hours: int = 24) -> list[dict[str, Any]]:
        """Get alert history for the last N hours."""
        since = datetime.now() - timedelta(hours=hours)

        return [
            {
                "id": alert.alert_id,
                "component": alert.component,
                "status": alert.status.value,
                "message": alert.message,
                "timestamp": alert.timestamp,
                "resolved": alert.resolved,
            }
            for alert in self.alert_history
            if datetime.fromisoformat(alert.timestamp) >= since
        ]


class SystemHealthChecker:
    """System-level health checker."""

    def __init__(self, thresholds: dict[str, float] | None = None):
        """Initialize system health checker."""
        self.thresholds = thresholds or {
            "cpu_percent": 80.0,
            "memory_percent": 85.0,
            "disk_percent": 90.0,
        }
        self.logger = logging.getLogger(__name__)

    async def check_system_health(self) -> dict[str, Any]:
        """Check overall system health."""
        try:
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            # Check thresholds
            issues = []
            if cpu_percent > self.thresholds["cpu_percent"]:
                issues.append(f"High CPU usage: {cpu_percent:.1f}%")

            if memory.percent > self.thresholds["memory_percent"]:
                issues.append(f"High memory usage: {memory.percent:.1f}%")

            if disk.percent > self.thresholds["disk_percent"]:
                issues.append(f"High disk usage: {disk.percent:.1f}%")

            # Determine status
            if issues:
                status = "critical" if len(issues) > 2 else "warning"
            else:
                status = "healthy"

            # Calculate health score
            health_score = 100.0
            if cpu_percent > self.thresholds["cpu_percent"]:
                health_score -= 20
            if memory.percent > self.thresholds["memory_percent"]:
                health_score -= 20
            if disk.percent > self.thresholds["disk_percent"]:
                health_score -= 20

            health_score = max(0, health_score)

            return {
                "component": "system",
                "status": status,
                "message": "; ".join(issues) if issues else "System healthy",
                "metadata": {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "disk_percent": disk.percent,
                    "health_score": health_score,
                    "issues": issues,
                },
            }

        except Exception as e:
            self.logger.exception(f"Error checking system health: {e}")
            return {
                "component": "system",
                "status": "unknown",
                "message": f"Error checking system health: {e}",
                "metadata": {"error": str(e)},
            }


class ComponentHealthChecker:
    """Component-level health checker."""

    def __init__(self, component_name: str, check_url: str | None = None):
        """Initialize component health checker."""
        self.component_name = component_name
        self.check_url = check_url
        self.logger = logging.getLogger(__name__)

    async def check_component_health(self) -> dict[str, Any]:
        """Check component health."""
        try:
            if self.check_url:
                # HTTP health check
                async with aiohttp.ClientSession() as session:
                    async with session.get(self.check_url, timeout=5) as response:
                        if response.status == 200:
                            status = "healthy"
                            message = "Component responding normally"
                        else:
                            status = "warning"
                            message = f"Component returned status {response.status}"

                        return {
                            "component": self.component_name,
                            "status": status,
                            "message": message,
                            "metadata": {
                                "url": self.check_url,
                                "status_code": response.status,
                                "response_time": 0,  # Could measure this
                            },
                        }
            else:
                # Basic component check
                return {
                    "component": self.component_name,
                    "status": "healthy",
                    "message": "Component check passed",
                    "metadata": {},
                }

        except TimeoutError:
            return {
                "component": self.component_name,
                "status": "critical",
                "message": "Component health check timeout",
                "metadata": {"url": self.check_url, "error": "timeout"},
            }
        except Exception as e:
            return {
                "component": self.component_name,
                "status": "critical",
                "message": f"Component health check failed: {e}",
                "metadata": {"url": self.check_url, "error": str(e)},
            }


class DatabaseHealthChecker:
    """Database health checker."""

    def __init__(self, db_path: str):
        """Initialize database health checker."""
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)

    async def check_database_health(self) -> dict[str, Any]:
        """Check database health."""
        try:
            import sqlite3

            # Check if database exists and is accessible
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Check database integrity
            cursor.execute("PRAGMA integrity_check")
            integrity_result = cursor.fetchone()[0]

            # Check database size
            db_size = self.db_path.stat().st_size if self.db_path.exists() else 0

            # Check table counts
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()

            conn.close()

            if integrity_result == "ok":
                status = "healthy"
                message = "Database healthy"
            else:
                status = "critical"
                message = f"Database integrity check failed: {integrity_result}"

            return {
                "component": "database",
                "status": status,
                "message": message,
                "metadata": {
                    "db_path": str(self.db_path),
                    "db_size": db_size,
                    "table_count": len(tables),
                    "integrity_check": integrity_result,
                },
            }

        except Exception as e:
            return {
                "component": "database",
                "status": "critical",
                "message": f"Database health check failed: {e}",
                "metadata": {"db_path": str(self.db_path), "error": str(e)},
            }
