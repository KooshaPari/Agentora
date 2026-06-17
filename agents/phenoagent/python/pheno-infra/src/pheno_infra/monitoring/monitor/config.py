"""
Configuration objects for the service monitor.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MonitorConfig:
    """
    Configuration for service monitoring.
    """

    project_name: str
    """
    Name of the project being monitored.
    """

    services: list[str] = field(default_factory=list)
    """
    Names of services to observe.
    """

    domain: str | None = None
    """
    Public domain for the services.
    """

    resources: list[dict[str, Any]] = field(default_factory=list)
    """
    External resources to monitor (postgres, redis, etc.).
    """

    refresh_interval: float = 2.0
    """
    TUI refresh cadence in seconds.
    """

    colorize_logs: bool = True
    """
    Colorize log output based on detected level keywords.
    """

    show_timestamps: bool = True
    """
    Display timestamps on log lines.
    """

    enable_rich: bool = True
    """
    Enable Rich-powered interactive TUI (set False for log-only mode).
    """


__all__ = ["MonitorConfig"]
