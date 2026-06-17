"""
KInfra package: split from a single monolith into pythonic modules under 500 lines.
Public API remains KInfra in kinfra.kinfra as before.
"""

from __future__ import annotations

from .base import BaseKInfra
from .cleanup import CleanupMixin
from .info import InfoMixin
from .ports import PortsMixin
from .tunnels import TunnelsMixin
from .wrappers import WrappersMixin


class KInfra(BaseKInfra, PortsMixin, TunnelsMixin, InfoMixin, CleanupMixin, WrappersMixin):
    """
    Unified KInfra interface (composed from mixins).
    """


__all__ = ["KInfra"]
