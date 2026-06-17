"""
Helper to launch the best available TUI monitor.
"""

from __future__ import annotations

from pheno.domain.models.project import ProjectRegistry

from .controller import TUIMonitor
from .engine import MonitorEngine
from .environment import HAS_RICH, HAS_TEXTUAL
from .simple import SimpleTUIMonitor


async def run_tui_monitor(
    project_registry: ProjectRegistry | None = None,
    monitor_engine: MonitorEngine | None = None,
    prefer_textual: bool = True,
) -> None:
    """
    Run the TUI monitor with the best available interface.
    """
    project_registry = project_registry or ProjectRegistry()
    monitor_engine = monitor_engine or MonitorEngine()

    if prefer_textual and HAS_TEXTUAL:
        monitor = TUIMonitor(project_registry, monitor_engine, use_textual=True)
        await monitor.run()
    elif HAS_RICH:
        monitor = TUIMonitor(project_registry, monitor_engine, use_textual=False)
        await monitor.run()
    else:
        monitor = SimpleTUIMonitor(project_registry, monitor_engine)
        await monitor.run()


__all__ = ["run_tui_monitor"]
