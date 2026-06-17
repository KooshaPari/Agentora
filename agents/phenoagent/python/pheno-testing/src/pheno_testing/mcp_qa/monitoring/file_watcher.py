"""File Watcher for Auto-Reload.

Monitors file system for changes and triggers test re-runs.
"""

import asyncio
import time
from pathlib import Path
from typing import TYPE_CHECKING, Callable, List, Optional, Set

if TYPE_CHECKING:
    from pheno.testing.mcp_qa.testing.live_runner import LiveTestRunner

try:
    from watchdog.events import FileSystemEvent, FileSystemEventHandler
    from watchdog.observers import Observer

    HAS_WATCHDOG = True
except ImportError:
    HAS_WATCHDOG = False
    FileSystemEventHandler = object
    Observer = None


class TestFileWatcher(FileSystemEventHandler if HAS_WATCHDOG else object):
    """
    Watches for file changes and triggers test re-runs.
    """

    def __init__(
        self,
        watch_paths: List[str],
        on_change: Callable[[str], None],
        debounce_seconds: float = 0.5,
        watch_patterns: Optional[List[str]] = None,
    ):
        """Initialize file watcher.

        Args:
            watch_paths: Directories to watch
            on_change: Callback(changed_file_path) when file changes
            debounce_seconds: Wait time after last change before triggering
            watch_patterns: File patterns to watch (e.g., ["*.py", "*.yaml"])
        """
        if not HAS_WATCHDOG:
            raise ImportError("watchdog library required. Install with: pip install watchdog")

        super().__init__()
        self.watch_paths = [Path(p) for p in watch_paths]
        self.on_change = on_change
        self.debounce_seconds = debounce_seconds
        self.watch_patterns = watch_patterns or ["*.py"]

        self._pending_changes: Set[str] = set()
        self._last_change_time: Optional[float] = None
        self._debounce_task: Optional[asyncio.Task] = None
        self._observer: Optional[Observer] = None

    def on_modified(self, event: "FileSystemEvent") -> None:
        """
        Called when a file is modified.
        """
        if event.is_directory:
            return

        file_path = event.src_path

        # Check if file matches patterns
        if not self._matches_pattern(file_path):
            return

        # Add to pending changes
        self._pending_changes.add(file_path)
        self._last_change_time = time.time()

        # Schedule debounced callback
        if self._debounce_task:
            self._debounce_task.cancel()

        self._debounce_task = asyncio.create_task(self._debounce_and_trigger())

    def _matches_pattern(self, file_path: str) -> bool:
        """
        Check if file matches watch patterns.
        """
        path = Path(file_path)
        return any(path.match(pattern) for pattern in self.watch_patterns)

    async def _debounce_and_trigger(self) -> None:
        """
        Wait for debounce period then trigger callback.
        """
        await asyncio.sleep(self.debounce_seconds)

        # Check if enough time has passed since last change
        if time.time() - self._last_change_time >= self.debounce_seconds:
            # Trigger callback for all pending changes
            for file_path in self._pending_changes:
                self.on_change(file_path)
            self._pending_changes.clear()

    def start(self) -> None:
        """
        Start watching files.
        """
        if not HAS_WATCHDOG:
            return

        self._observer = Observer()

        for watch_path in self.watch_paths:
            if watch_path.exists():
                self._observer.schedule(self, str(watch_path), recursive=True)

        self._observer.start()

    def stop(self) -> None:
        """
        Stop watching files.
        """
        if self._observer:
            self._observer.stop()
            self._observer.join()

    def get_affected_tools(self, file_path: str) -> List[str]:
        """Determine which tools are affected by file change.

        Args:
            file_path: Path to changed file

        Returns:
            List of tool names affected
        """
        path = Path(file_path)

        # If it's a tool file, return that tool
        if "tools/" in str(path):
            tool_name = path.stem
            # Remove _tool suffix if present
            if tool_name.endswith("_tool"):
                tool_name = tool_name[:-5]
            return [f"{tool_name}_tool"]

        # If it's a test file, return the tool being tested
        if "test_" in path.name:
            # Extract tool from test filename
            # e.g., test_entity_comprehensive.py → entity_tool
            name = path.stem.replace("test_", "").replace("_comprehensive", "")
            return [f"{name}_tool"]

        # Unknown - trigger all tests
        return []


class SmartReloadManager:
    """
    Manages smart reloading of only affected tests.
    """

    def __init__(self, test_runner: "LiveTestRunner"):
        self.test_runner = test_runner
        self.file_watcher: Optional["TestFileWatcher"] = None

    def enable_auto_reload(self, watch_paths: List[str]) -> None:
        """Enable auto-reload when files change.

        Args:
            watch_paths: Directories to watch for changes
        """
        self.file_watcher = TestFileWatcher(
            watch_paths=watch_paths, on_change=self._on_file_change, debounce_seconds=0.5
        )
        self.file_watcher.start()

    def disable_auto_reload(self) -> None:
        """
        Disable auto-reload.
        """
        if self.file_watcher:
            self.file_watcher.stop()
            self.file_watcher = None

    def _on_file_change(self, file_path: str) -> None:
        """
        Handle file change event.
        """
        print(f"\n🔄 File changed: {file_path}")

        # Determine affected tools
        affected_tools = self.file_watcher.get_affected_tools(file_path)

        if affected_tools:
            print(f"   Re-running tests for: {', '.join(affected_tools)}")
            # Clear cache for affected tools
            if self.test_runner.cache_instance:
                for tool in affected_tools:
                    self.test_runner.cache_instance.clear_tool(tool)

            # Trigger selective re-run
            # (Would be implemented by TUI to re-run specific tests)
        else:
            print("   Re-running all tests...")
