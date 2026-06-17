"""
Alert configuration types.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AlertAction:
    """
    Action to perform when an alert triggers.
    """

    type: str
    target: str
    config: dict[str, str] = field(default_factory=dict)


@dataclass
class AlertConfig:
    """
    Configuration describing alert thresholds and actions.
    """

    id: str
    resource_id: str
    metric_name: str
    condition: str
    threshold: float
    duration: int
    severity: str
    actions: list[dict[str, Any]]
    enabled: bool
    metadata: dict[str, str] = field(default_factory=dict)


__all__ = ["AlertAction", "AlertConfig"]
