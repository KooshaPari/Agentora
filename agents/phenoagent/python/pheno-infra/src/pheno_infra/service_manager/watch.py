"""
File watching helpers (watchdog-based), with graceful degradation.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)

try:
    from watchdog.events import FileSystemEvent, FileSystemEventHandler
    from watchdog.observers import Observer

    WATCHDOG_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    WATCHDOG_AVAILABLE = False

    class FileSystemEvent:  # type: ignore[no-redef]
        pass

    class FileSystemEventHandler:  # type: ignore[no-redef]
        pass

    Observer = None  # type: ignore


class FileChangeHandler(FileSystemEventHandler):
    def __init__(
        self, callback: Callable[[FileSystemEvent], None], patterns: list[str] | None = None,
    ) -> None:
        super().__init__()
        self.callback = callback
        self.patterns = patterns or ["*.py"]

    def on_modified(self, event):
        if getattr(event, "is_directory", False):
            return
        file_path = Path(getattr(event, "src_path", ""))
        if not any(file_path.match(pattern) for pattern in self.patterns):
            return
        logger.debug("File changed: %s", file_path)
        self.callback(event)


def setup_file_watching(
    name: str,
    watch_paths: list[Path],
    patterns: list[str] | None,
    on_change: Callable[[FileSystemEvent], None],
):
    if not WATCHDOG_AVAILABLE:
        logger.warning("Watchdog not available, file watching disabled for %s", name)
        return None

    handler = FileChangeHandler(on_change, patterns or ["*.py"])
    observer = Observer()
    for watch_path in watch_paths:
        if watch_path.exists():
            observer.schedule(handler, str(watch_path), recursive=True)
            logger.info("Watching %s for %s", watch_path, name)
    observer.start()
    return observer
