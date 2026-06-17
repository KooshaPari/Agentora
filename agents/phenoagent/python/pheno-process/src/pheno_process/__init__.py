"""
pheno.process - Process lifecycle management

Provides process monitoring, health checks, and lifecycle management.

Migrated from process-monitor-sdk into pheno namespace.

Usage:
    from pheno.process import ProcessManager, HealthMonitor

    # Create process manager
    manager = ProcessManager()

    # Monitor process health
    monitor = HealthMonitor(process)
    health = await monitor.check()
"""

from __future__ import annotations

from .base.health_check import HealthCheck
from .base.monitor_base import BaseMonitor
from .base.process_base import BaseProcess
from .components.health_monitor import HealthMonitor
from .components.port_manager import PortManager
from .components.process_manager import ProcessManager
from .factories.monitor_factory import MonitorFactory
from .factories.process_factory import ProcessFactory

__version__ = "0.1.0"

__all__ = [
    "BaseMonitor",
    "BaseProcess",
    "HealthCheck",
    "HealthMonitor",
    "MonitorFactory",
    "PortManager",
    "ProcessFactory",
    "ProcessManager",
]
