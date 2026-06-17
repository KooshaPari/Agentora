"""
ServiceManager package: split from monolithic service_manager.py into Pythonic modules
(under 500 lines each) and composed via mixins.
"""

from __future__ import annotations

from .base import BaseServiceManager
from .fallback import FallbackMixin
from .health import HealthMixin
from .manager.core import ServiceManager
from .models import ResourceConfig, ResourceStatus, ServiceConfig, ServiceStatus
from .monitor import MonitorMixin
from .processes import ProcessMixin
from .resources import ResourcesMixin

__all__ = [
    "BaseServiceManager",
    "FallbackMixin",
    "HealthMixin",
    "MonitorMixin",
    "ProcessMixin",
    "ResourceConfig",
    "ResourceStatus",
    "ResourcesMixin",
    "ServiceConfig",
    "ServiceManager",
    "ServiceStatus",
]
