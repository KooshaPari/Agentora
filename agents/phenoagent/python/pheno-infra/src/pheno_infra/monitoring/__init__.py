"""
KInfra Service Monitoring Components
=====================================

Rich-based live monitoring for services with:
- Scrolling log output above TUI panel
- Fixed status panel at bottom
- Process health tracking
- Resource availability checks
- Endpoint status display

Example:
    >>> from pheno.infra.monitoring import ServiceMonitor
    >>> monitor = ServiceMonitor(services=["zen", "api"], domain="myapp.com")
    >>> await monitor.start()
"""

from .monitor import MonitorConfig, ServiceMonitor
from .panels import EndpointPanel, ProcessPanel, ResourcePanel

__all__ = [
    "EndpointPanel",
    "MonitorConfig",
    "ProcessPanel",
    "ResourcePanel",
    "ServiceMonitor",
]
