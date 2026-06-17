"""Status Page package.

Exposes StatusPageGenerator and ServiceStatus.
"""

from __future__ import annotations

from .generator import StatusPageGenerator
from .types import ServiceStatus

__all__ = ["ServiceStatus", "StatusPageGenerator"]
