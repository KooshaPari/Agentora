"""Pheno Observability.

Bootstrap utilities for OpenTelemetry, structlog, and metrics.

Phase 1 consolidation:
- Re-export observability-kit helpers to provide a stable `pheno.observability` path
- Future: migrate selected helpers into `pheno` natively

Phase 5 consolidation:
- Unified monitoring layer with metrics, events, dashboards, and health checks
- Consolidates functionality from infra/monitoring, MCP QA, and observability stacks
"""

from __future__ import annotations

from .otel import configure_otel, get_meter_provider, get_tracer_provider

try:  # pragma: no cover - optional dependency path
    from .logging import configure_structlog, get_logger
except ModuleNotFoundError:  # pragma: no cover - fallback in lightweight environments
    import logging

    def configure_structlog() -> None:
        logging.getLogger(__name__).info(
            "Structlog integration not available; using stdlib logging",
        )

    def get_logger(name: str):
        return logging.getLogger(name)


from .bootstrap import add_prometheus_endpoint, init_otel

try:  # pragma: no cover - optional monitoring stack
    from .monitoring import (
        CommandExecutor,
        CommandRunner,
        DashboardManager,
        DashboardProvider,
        EventCollector,
        EventEmitter,
        HealthChecker,
        HealthStatus,
        MetricsCollector,
        MetricsRegistry,
        MonitoringConfig,
        MonitoringManager,
    )
except ModuleNotFoundError:  # pragma: no cover - minimal environments
    MonitoringManager = MonitoringConfig = MetricsCollector = MetricsRegistry = None  # type: ignore
    EventEmitter = EventCollector = DashboardManager = DashboardProvider = None  # type: ignore
    CommandRunner = CommandExecutor = HealthChecker = HealthStatus = None  # type: ignore

__all__ = [
    "CommandExecutor",
    "CommandRunner",
    "DashboardManager",
    "DashboardProvider",
    "EventCollector",
    "EventEmitter",
    "HealthChecker",
    "HealthStatus",
    "MetricsCollector",
    "MetricsRegistry",
    "MonitoringConfig",
    # Monitoring
    "MonitoringManager",
    "add_prometheus_endpoint",
    # Core observability
    "configure_otel",
    "configure_structlog",
    "get_logger",
    "get_meter_provider",
    "get_tracer_provider",
    "init_otel",
]
