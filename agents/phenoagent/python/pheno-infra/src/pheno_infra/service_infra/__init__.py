"""
ServiceInfra package: refactored from kinfra with canonical naming.
Public API is ServiceInfraManager in service_infra.service_infra as before.
"""

from __future__ import annotations

from .base import BaseServiceInfra
from .cleanup import CleanupMixin
from .info import InfoMixin
from .ports import PortsMixin
from .tunnels import TunnelsMixin
from .wrappers import WrappersMixin


class ServiceInfraManager(
    BaseServiceInfra, PortsMixin, TunnelsMixin, InfoMixin, CleanupMixin, WrappersMixin,
):
    """
    Unified ServiceInfra interface (composed from mixins).
    """


__all__ = ["ServiceInfraManager"]
