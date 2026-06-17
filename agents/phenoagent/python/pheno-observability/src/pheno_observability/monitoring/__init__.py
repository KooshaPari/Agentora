"""Unified Monitoring Layer.

Centralized monitoring components for metrics, events, dashboards, and command runners.
Consolidates functionality from infra/monitoring, MCP QA, and observability stacks.
"""

from .adapters import (
    CLIMonitoringAdapter,
    DashboardAdapter,
    InfraMonitoringAdapter,
    MCPQAMonitoringAdapter,
)
from .command_runner import CommandExecutor, CommandRunner
from .core import MonitoringConfig, MonitoringManager
from .dashboards import DashboardManager, DashboardProvider
from .events import EventCollector, EventEmitter
from .health import HealthChecker, HealthStatus
from .metrics import MetricsCollector, MetricsRegistry

__all__ = [
    "CLIMonitoringAdapter",
    "CommandExecutor",
    "CommandRunner",
    "DashboardAdapter",
    "DashboardManager",
    "DashboardProvider",
    "EventCollector",
    "EventEmitter",
    "HealthChecker",
    "HealthStatus",
    # Adapters
    "InfraMonitoringAdapter",
    "MCPQAMonitoringAdapter",
    "MetricsCollector",
    "MetricsRegistry",
    "MonitoringConfig",
    "MonitoringManager",
]
