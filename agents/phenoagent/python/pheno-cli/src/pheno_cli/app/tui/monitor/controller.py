"""
Primary TUI monitor controller.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from pheno.domain.models.log import LogEntry
from pheno.domain.models.project import ProjectRegistry

from .engine import MonitorEngine
from .environment import HAS_RICH, HAS_TEXTUAL, Console
from .rich_ui import run_rich_monitor
from .textual_app import PhenoControlCenterApp

logger = logging.getLogger(__name__)


class TUIMonitor:
    """
    Unified interface that selects the best available TUI implementation.
    """

    def __init__(
        self,
        project_registry: ProjectRegistry | None = None,
        monitor_engine: MonitorEngine | None = None,
        use_textual: bool = True,
        refresh_interval: float = 2.0,
    ):
        self.project_registry = project_registry or ProjectRegistry()
        self.monitor_engine = monitor_engine or MonitorEngine()
        self.refresh_interval = refresh_interval

        self.use_textual = use_textual and HAS_TEXTUAL
        self.use_rich = not self.use_textual and HAS_RICH

        if not self.use_textual and not self.use_rich:
            raise RuntimeError("Neither Textual nor Rich is available for TUI monitoring")

        self.console = Console() if self.use_rich and Console else None
        self.command_history: list[str] = []
        self._shutdown = False

        logger.info("TUI monitor initialized (%s)", "textual" if self.use_textual else "rich")

    async def run(self) -> None:
        if self.use_textual:
            await self._run_textual()
        else:
            await self._run_rich()

    async def _run_textual(self) -> None:
        if not HAS_TEXTUAL or PhenoControlCenterApp is None:
            raise RuntimeError("Textual is not available")

        app = PhenoControlCenterApp(
            project_registry=self.project_registry,
            monitor_engine=self.monitor_engine,
        )
        await app.run_async()

    async def _run_rich(self) -> None:
        if not HAS_RICH or self.console is None:
            raise RuntimeError("Rich is not available")

        await run_rich_monitor(
            engine=self.monitor_engine,
            console=self.console,
            refresh_interval=self.refresh_interval,
        )

    def add_log_entry(
        self,
        project: str,
        process: str,
        level: str,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        entry = LogEntry(
            timestamp=datetime.now(),
            project=project,
            process=process,
            level=level,
            message=message,
            metadata=metadata or {},
        )
        self.monitor_engine.log_entry(entry)

    def stop(self) -> None:
        self._shutdown = True
        logger.info("TUI monitor stopped")


__all__ = ["TUIMonitor"]
