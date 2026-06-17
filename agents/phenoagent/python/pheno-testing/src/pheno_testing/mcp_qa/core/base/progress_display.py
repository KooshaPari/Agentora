"""Enhanced Progress Display with Real-Time Statistics.

Provides a rich, detailed progress display for test execution with:
- Live pass/fail/cache/skip counters
- Current test name and tool being executed
- Worker information (for parallel execution)
- Performance metrics (tests/sec, avg duration, cache hit rate)
- Spinner animation for active progress
- Category breakdown

Reuses components from:
- tui-kit/widgets/unified_progress.py
- mcp_qa/oauth/granular_progress.py
"""

import threading
import time
from collections import deque
from typing import Dict, List, Optional

try:
    from rich.console import Console, Group
    from rich.live import Live
    from rich.panel import Panel
    from rich.progress import (
        BarColumn,
        Progress,
        SpinnerColumn,
        TaskID,
        TextColumn,
        TimeElapsedColumn,
        TimeRemainingColumn,
    )
    from rich.table import Table
    from rich.text import Text

    HAS_RICH = True
except ImportError:
    HAS_RICH = False


class ComprehensiveProgressDisplay:
    """Enhanced progress display with real-time statistics.

    Shows:
    - Overall progress bar with spinner
    - Live statistics (pass/fail/cache/skip counts)
    - Current test information (name, tool, worker, duration)
    - Performance metrics (tests/sec, avg duration, cache hit rate)
    - Per-category progress breakdown (optional)

    Example output:
    ```
    📋 ENTITY_READ Tests
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    ⠹ Running tests... ━━━━━━━━━━━━━━━━━━━━━━ 22% (29/131) 0:00:12 < 0:00:25

    📊 Live Stats:
       ✅ Passed: 25  ❌ Failed: 3  💾 Cached: 1  ⏭️  Skipped: 0

    🔄 Current: test_read_organization_by_id
       Tool: entity_tool | Worker: 3/10 | Duration: 0.8s

    📈 Performance:
       Speed: 2.4 tests/sec | Avg: 0.4s/test | Cache hit: 3%
    ```
    """

    def __init__(
        self,
        total_tests: int,
        categories: Optional[List[str]] = None,
        parallel: bool = False,
        workers: int = 1,
        show_categories: bool = False,
    ):
        """Initialize enhanced progress display.

        Args:
            total_tests: Total number of tests to run
            categories: List of test categories (for category breakdown)
            parallel: Whether parallel execution is enabled
            workers: Number of parallel workers
            show_categories: Show category breakdown panel
        """
        if not HAS_RICH:
            self.enabled = False
            return

        self.enabled = True
        self.console = Console()
        self.total_tests = total_tests
        self.categories = categories or []
        self.parallel = parallel
        self.workers = workers
        self.show_categories = show_categories

        # Thread-safe lock for updates
        self._lock = threading.RLock()

        # Statistics
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.cached = 0
        self.current = 0

        # Current test tracking
        self.current_test = ""
        self.current_tool = ""
        self.current_category = ""
        self.current_worker = None
        self.current_test_start = None

        # Category breakdown
        self.category_stats: Dict[str, Dict[str, int]] = {}
        for cat in self.categories:
            self.category_stats[cat] = {
                "total": 0,
                "completed": 0,
                "passed": 0,
                "failed": 0,
                "cached": 0,
                "skipped": 0,
            }

        # Performance metrics
        self.durations: deque = deque(maxlen=100)  # Keep last 100 durations
        self.start_time = time.time()

        # Setup Rich Progress
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[cyan]{task.description}"),
            BarColumn(bar_width=40),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("({task.completed}/{task.total})"),
            TimeElapsedColumn(),
            TextColumn("<"),
            TimeRemainingColumn(),
            console=self.console,
        )

        self.overall_task: Optional[TaskID] = None
        self.live: Optional[Live] = None

    def __enter__(self):
        """
        Start progress display.
        """
        if not self.enabled:
            return self

        # Create main task
        self.overall_task = self.progress.add_task("[cyan]Running tests...", total=self.total_tests)

        # Create live display with progress + metrics
        self.live = Live(
            self._generate_display(),
            console=self.console,
            refresh_per_second=4,
        )
        self.live.start()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Stop progress display.
        """
        if not self.enabled:
            return

        if self.live:
            self.live.stop()

    def update(
        self,
        test_name: str,
        tool_name: str,
        category: str,
        success: bool,
        duration_ms: float,
        cached: bool = False,
        skipped: bool = False,
        worker_id: Optional[int] = None,
    ):
        """Update progress with test result.

        Args:
            test_name: Test name
            tool_name: Tool being tested
            category: Test category
            success: Whether test passed
            duration_ms: Test duration in milliseconds
            cached: Whether result was cached
            skipped: Whether test was skipped
            worker_id: Worker ID (if parallel execution)
        """
        if not self.enabled:
            return

        with self._lock:
            self.current += 1

            # Update counts
            if cached:
                self.cached += 1
            elif skipped:
                self.skipped += 1
            elif success:
                self.passed += 1
            else:
                self.failed += 1

            # Update category stats
            if category in self.category_stats:
                self.category_stats[category]["completed"] += 1
                if cached:
                    self.category_stats[category]["cached"] += 1
                elif skipped:
                    self.category_stats[category]["skipped"] += 1
                elif success:
                    self.category_stats[category]["passed"] += 1
                else:
                    self.category_stats[category]["failed"] += 1

            # Track duration (exclude cached)
            if not cached:
                self.durations.append(duration_ms)

            # Update progress bar
            if self.overall_task is not None:
                self.progress.update(self.overall_task, advance=1)

            # Refresh live display
            if self.live:
                self.live.update(self._generate_display())

    def set_current_test(
        self,
        test_name: str,
        tool_name: str,
        category: str,
        worker_id: Optional[int] = None,
    ):
        """Set the currently executing test.

        Args:
            test_name: Test name
            tool_name: Tool being tested
            category: Test category
            worker_id: Worker ID (if parallel execution)
        """
        if not self.enabled:
            return

        with self._lock:
            self.current_test = test_name
            self.current_tool = tool_name
            self.current_category = category
            self.current_worker = worker_id
            self.current_test_start = time.time()

            # Refresh live display
            if self.live:
                self.live.update(self._generate_display())

    def set_category_total(self, category: str, total: int):
        """
        Set total tests for a category.
        """
        if not self.enabled:
            return

        with self._lock:
            if category in self.category_stats:
                self.category_stats[category]["total"] = total

    def _generate_display(self) -> Group:
        """
        Generate complete display with progress + metrics.
        """
        components = []

        # Main progress bar
        components.append(self.progress)

        # Live statistics
        components.append(self._create_stats_panel())

        # Current test info
        if self.current_test:
            components.append(self._create_current_test_panel())

        # Performance metrics
        components.append(self._create_performance_panel())

        # Category breakdown (if enabled)
        if self.show_categories and self.category_stats:
            components.append(self._create_category_panel())

        return Group(*components)

    def _create_stats_panel(self) -> Panel:
        """
        Create live statistics panel.
        """
        with self._lock:
            # Calculate real-time stats
            self.current - self.cached

            # Build stats string
            stats_text = Text()
            stats_text.append("   ")
            stats_text.append("✅ Passed: ", style="bold")
            stats_text.append(f"{self.passed}", style="green")
            stats_text.append("  ")
            stats_text.append("❌ Failed: ", style="bold")
            stats_text.append(f"{self.failed}", style="red")
            stats_text.append("  ")
            stats_text.append("💾 Cached: ", style="bold")
            stats_text.append(f"{self.cached}", style="blue")
            stats_text.append("  ")
            stats_text.append("⏭️  Skipped: ", style="bold")
            stats_text.append(f"{self.skipped}", style="yellow")

        return Panel(stats_text, title="[bold]📊 Live Stats[/bold]", border_style="blue")

    def _create_current_test_panel(self) -> Panel:
        """
        Create current test information panel.
        """
        with self._lock:
            current_duration = (
                time.time() - self.current_test_start if self.current_test_start else 0
            )

            # Build current test info
            info_text = Text()
            info_text.append("   Tool: ", style="cyan")
            info_text.append(self.current_tool, style="white")

            if self.parallel and self.current_worker is not None:
                info_text.append(" | ", style="dim")
                info_text.append("Worker: ", style="cyan")
                info_text.append(f"{self.current_worker}/{self.workers}", style="white")

            info_text.append(" | ", style="dim")
            info_text.append("Duration: ", style="cyan")
            info_text.append(f"{current_duration:.1f}s", style="white")

        return Panel(
            Text(f"🔄 Current: {self.current_test}\n") + info_text,
            title="",
            border_style="magenta",
        )

    def _create_performance_panel(self) -> Panel:
        """
        Create performance metrics panel.
        """
        with self._lock:
            # Calculate performance metrics
            elapsed = time.time() - self.start_time
            tests_per_sec = self.current / elapsed if elapsed > 0 else 0
            avg_duration = sum(self.durations) / len(self.durations) if self.durations else 0
            cache_hit_rate = (self.cached / self.current) * 100 if self.current > 0 else 0

            # Build performance info
            perf_text = Text()
            perf_text.append("   Speed: ", style="cyan")
            perf_text.append(f"{tests_per_sec:.1f} tests/sec", style="white")
            perf_text.append(" | ", style="dim")
            perf_text.append("Avg: ", style="cyan")
            perf_text.append(f"{avg_duration / 1000:.2f}s/test", style="white")
            perf_text.append(" | ", style="dim")
            perf_text.append("Cache hit: ", style="cyan")
            perf_text.append(f"{cache_hit_rate:.1f}%", style="white")

        return Panel(perf_text, title="[bold]📈 Performance[/bold]", border_style="green")

    def _create_category_panel(self) -> Panel:
        """
        Create category breakdown panel.
        """
        table = Table(show_header=True, box=None)
        table.add_column("Category", style="cyan")
        table.add_column("Progress", justify="center")
        table.add_column("Passed", style="green", justify="right")
        table.add_column("Failed", style="red", justify="right")
        table.add_column("Cached", style="blue", justify="right")

        with self._lock:
            for category, stats in sorted(self.category_stats.items()):
                if stats["total"] > 0:
                    progress_str = f"{stats['completed']}/{stats['total']}"
                    table.add_row(
                        category,
                        progress_str,
                        str(stats["passed"]),
                        str(stats["failed"]),
                        str(stats["cached"]),
                    )

        return Panel(table, title="[bold]By Category[/bold]", border_style="yellow")

    def write(self, message: str):
        """
        Write a message above the progress display.
        """
        if self.enabled and self.console:
            self.console.print(message)


__all__ = ["ComprehensiveProgressDisplay"]
