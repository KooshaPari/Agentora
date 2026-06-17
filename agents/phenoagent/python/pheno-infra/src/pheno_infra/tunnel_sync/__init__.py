"""
Tunnel synchronization package: split from monolithic tunnel_sync.py.
Public API preserved: TunnelManager, TunnelInfo.
"""

from __future__ import annotations

from .base import TunnelBase
from .dns import DNSMixin
from .models import TunnelEvent, TunnelInfo
from .processes import ProcessMixin
from .public import PublicMixin
from .quick import QuickMixin
from .separate import SeparateMixin
from .unified import UnifiedMixin


class TunnelManager(
    TunnelBase, DNSMixin, UnifiedMixin, SeparateMixin, ProcessMixin, QuickMixin, PublicMixin,
):
    pass


__all__ = ["TunnelEvent", "TunnelInfo", "TunnelManager"]
