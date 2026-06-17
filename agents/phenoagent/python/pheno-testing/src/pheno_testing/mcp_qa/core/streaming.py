"""
Streaming Result Display - Real-time Test Feedback

Provides instant gratification with:
- Results shown immediately as they complete (no waiting)
- Real-time terminal updates with smart batching
- Non-blocking async display
- Priority queue for result ordering (fastest tests first)
- Buffer management to prevent terminal flooding
- Separate display thread for instant feedback
"""

import threading
import time
from collections import deque
from datetime import datetime
from queue import Empty, PriorityQueue, Queue
from typing import Any, Dict, List, Optional

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
    )
    from rich.table import Table
    from rich.text import Text

    HAS_RICH = True
except ImportError:
    HAS_RICH = False


class TestResult:
    """
    Container for test result with priority.
    """

    def __init__(
        self,
        test_name: str,
        tool_name: str,
        category: str,
        success: bool,
        duration_ms: float,
        cached: bool = False,
        skipped: bool = False,
        error: Optional[str] = None,
        completed_at: Optional[datetime] = None,
    ):
        self.test_name = test_name
        self.tool_name = tool_name
        self.category = category
        self.success = success
        self.duration_ms = duration_ms
        self.cached = cached
        self.skipped = skipped
        self.error = error
        self.completed_at = completed_at or datetime.now()

    def __lt__(self, other):
        """
        Compare by completion time for priority queue.
        """
        return self.completed_at < other.completed_at

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary.
        """
        return {
            "test_name": self.test_name,
            "tool_name": self.tool_name,
            "category": self.category,
            "success": self.success,
            "duration_ms": self.duration_ms,
            "cached": self.cached,
            "skipped": self.skipped,
            "error": self.error,
            "completed_at": self.completed_at,
        }


class ParallelStreamCollector:
    """Collect results from multiple workers in real-time.

    Features:
    - Order results by completion time (not start time)
    - Show fastest tests first
    - Priority queue for result ordering
    - Thread-safe collection
    """

    def __init__(self, max_buffer_size: int = 100):
        self.results_queue = PriorityQueue(maxsize=max_buffer_size)
        self.completed_results: List[TestResult] = []
        self.lock = threading.Lock()
        self._completion_times: Dict[str, float] = {}

    def add_result(self, result: TestResult) -> None:
        """
        Add a completed test result.
        """
        with self.lock:
            # Store completion time
            self._completion_times[result.test_name] = result.completed_at.timestamp()

            # Add to priority queue (fastest first)
            try:
                self.results_queue.put_nowait((result.duration_ms, result))
            except Exception:
                # Queue full, add to completed list directly
                self.completed_results.append(result)

    def get_next_result(self, timeout: float = 0.1) -> Optional[TestResult]:
        """
        Get next result by completion order (non-blocking).
        """
        try:
            _, result = self.results_queue.get(timeout=timeout)
            with self.lock:
                self.completed_results.append(result)
            return result
        except Empty:
            return None

    def get_all_pending(self) -> List[TestResult]:
        """
        Get all pending results (drain queue).
        """
        results = []
        while True:
            result = self.get_next_result(timeout=0)
            if result is None:
                break
            results.append(result)
        return results

    def get_completed_count(self) -> int:
        """
        Get count of completed tests.
        """
        with self.lock:
            return len(self.completed_results)


class SmartBatchingBuffer:
    """Batch console updates to reduce flicker.

    Features:
    - Update every 50ms max
    - Accumulate multiple results in batch
    - Flush on category change or suite completion
    - Prevent terminal flooding
    """

    def __init__(self, batch_interval_ms: int = 50, max_batch_size: int = 10):
        self.batch_interval = batch_interval_ms / 1000.0  # Convert to seconds
        self.max_batch_size = max_batch_size
        self.pending_results: deque = deque(maxlen=max_batch_size)
        self.last_flush_time = time.time()
        self.current_category: Optional[str] = None
        self.lock = threading.Lock()

    def add_result(self, result: TestResult) -> bool:
        """Add result to buffer.

        Returns:
            True if buffer should be flushed, False otherwise
        """
        with self.lock:
            # Check if category changed
            category_changed = (
                self.current_category is not None and result.category != self.current_category
            )
            self.current_category = result.category

            self.pending_results.append(result)

            # Check if we should flush
            now = time.time()
            time_elapsed = now - self.last_flush_time

            should_flush = (
                len(self.pending_results) >= self.max_batch_size
                or time_elapsed >= self.batch_interval
                or category_changed
            )

            return should_flush

    def flush(self) -> List[TestResult]:
        """
        Flush pending results and return them.
        """
        with self.lock:
            results = list(self.pending_results)
            self.pending_results.clear()
            self.last_flush_time = time.time()
            return results

    def has_pending(self) -> bool:
        """
        Check if buffer has pending results.
        """
        with self.lock:
            return len(self.pending_results) > 0


class InstantFeedbackMode:
    """Show test result within 100ms of completion.

    Features:
    - Separate thread for display
    - Async queue for results
    - No blocking on reporter generation
    - Instant visual feedback
    """

    def __init__(self, target_latency_ms: int = 100):
        self.target_latency = target_latency_ms / 1000.0  # Convert to seconds
        self.result_queue: Queue = Queue()
        self.display_thread: Optional[threading.Thread] = None
        self.running = False
        self.console = Console() if HAS_RICH else None
        self.callbacks: List[callable] = []

    def start(self) -> None:
        """
        Start instant feedback display thread.
        """
        self.running = True
        self.display_thread = threading.Thread(target=self._display_loop, daemon=True)
        self.display_thread.start()

    def stop(self) -> None:
        """
        Stop display thread.
        """
        self.running = False
        if self.display_thread:
            self.display_thread.join(timeout=1.0)

    def add_callback(self, callback: callable) -> None:
        """
        Add a callback to be called on each result.
        """
        self.callbacks.append(callback)

    def push_result(self, result: TestResult) -> None:
        """
        Push result for instant display.
        """
        self.result_queue.put(result)

    def _display_loop(self) -> None:
        """
        Main display loop running in separate thread.
        """
        while self.running:
            try:
                # Non-blocking get with timeout
                result = self.result_queue.get(timeout=0.05)

                # Display immediately
                self._display_result(result)

                # Call callbacks
                for callback in self.callbacks:
                    try:
                        callback(result)
                    except Exception:
                        pass  # Ignore callback errors

            except Empty:
                continue

    def _display_result(self, result: TestResult) -> None:
        """
        Display a single result immediately.
        """
        if not self.console or not HAS_RICH:
            # Fallback to simple print
            icon = (
                "💾"
                if result.cached
                else ("⏭️ " if result.skipped else ("✅" if result.success else "❌"))
            )
            print(f"{icon} {result.test_name} ({result.duration_ms:.2f}ms)")
            return

        # Rich display
        icon = (
            "💾"
            if result.cached
            else ("⏭️ " if result.skipped else ("✅" if result.success else "❌"))
        )
        color = (
            "blue"
            if result.cached
            else ("yellow" if result.skipped else ("green" if result.success else "red"))
        )

        text = Text()
        text.append(f"{icon} ", style=color)
        text.append(f"{result.test_name}", style="white")
        text.append(f" ({result.duration_ms:.2f}ms)", style="dim")

        if result.error:
            text.append(f"\n   Error: {result.error[:60]}...", style="red dim")

        self.console.print(text)


class StreamingResultDisplay:
    """Real-time streaming result display.

    Features:
    - Show results immediately as they complete
    - Real-time terminal updates
    - Non-blocking async display
    - Smart batching to prevent flooding
    - Instant feedback mode (<100ms latency)
    """

    def __init__(
        self,
        total_tests: int,
        categories: List[str],
        parallel: bool = False,
        workers: int = 1,
        instant_feedback: bool = True,
        batch_interval_ms: int = 50,
    ):
        self.total_tests = total_tests
        self.categories = categories
        self.parallel = parallel
        self.workers = workers
        self.enabled = HAS_RICH

        # Components
        self.collector = ParallelStreamCollector()
        self.buffer = SmartBatchingBuffer(batch_interval_ms=batch_interval_ms)
        self.instant_mode = InstantFeedbackMode() if instant_feedback else None

        # Statistics
        self.stats = {
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "cached": 0,
            "current": 0,
        }

        # Category tracking
        self.category_stats = {
            cat: {"total": 0, "completed": 0, "passed": 0, "failed": 0} for cat in categories
        }

        # Rich components
        if HAS_RICH:
            self.console = Console()
            self.progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(bar_width=40),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TextColumn("({task.completed}/{task.total})"),
                TimeElapsedColumn(),
                console=self.console,
            )
            self.overall_task: Optional[TaskID] = None
            self.live: Optional[Live] = None
        else:
            self.console = None
            self.progress = None

    def __enter__(self):
        """
        Start streaming display.
        """
        if not self.enabled:
            return self

        # Start instant feedback mode
        if self.instant_mode:
            self.instant_mode.start()
            # Register callback to update progress
            self.instant_mode.add_callback(self._on_result_callback)

        # Create progress task
        self.overall_task = self.progress.add_task("[cyan]Running tests", total=self.total_tests)

        # Start live display
        self.live = Live(self._generate_display(), console=self.console, refresh_per_second=20)
        self.live.start()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Stop streaming display.
        """
        if not self.enabled:
            return

        # Flush any remaining results
        self._flush_buffer()

        # Stop instant feedback
        if self.instant_mode:
            self.instant_mode.stop()

        # Stop live display
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
        error: Optional[str] = None,
    ) -> None:
        """Update display with new test result (instant).

        This method returns immediately (<100ms) while display updates happen
        asynchronously.
        """
        # Create result
        result = TestResult(
            test_name=test_name,
            tool_name=tool_name,
            category=category,
            success=success,
            duration_ms=duration_ms,
            cached=cached,
            skipped=skipped,
            error=error,
        )

        # Add to collector
        self.collector.add_result(result)

        # Push to instant feedback (if enabled)
        if self.instant_mode:
            self.instant_mode.push_result(result)

        # Add to buffer
        should_flush = self.buffer.add_result(result)

        # Flush if needed
        if should_flush:
            self._flush_buffer()

    def _on_result_callback(self, result: TestResult) -> None:
        """
        Callback when result is displayed in instant mode.
        """
        # Update statistics
        self.stats["current"] += 1

        if result.cached:
            self.stats["cached"] += 1
        elif result.skipped:
            self.stats["skipped"] += 1
        elif result.success:
            self.stats["passed"] += 1
        else:
            self.stats["failed"] += 1

        # Update category stats
        if result.category in self.category_stats:
            self.category_stats[result.category]["completed"] += 1
            if result.success and not result.cached and not result.skipped:
                self.category_stats[result.category]["passed"] += 1
            elif not result.success and not result.skipped:
                self.category_stats[result.category]["failed"] += 1

        # Update progress bar
        if self.overall_task:
            self.progress.update(self.overall_task, advance=1)

        # Refresh display
        if self.live:
            self.live.update(self._generate_display())

    def _flush_buffer(self) -> None:
        """
        Flush buffered results and update display.
        """
        results = self.buffer.flush()
        if not results:
            return

        # Process batched results
        for result in results:
            # These were already displayed via instant mode
            # Just ensure stats are updated
            pass

        # Refresh display
        if self.live:
            self.live.update(self._generate_display())

    def set_category_total(self, category: str, total: int) -> None:
        """
        Set total tests for a category.
        """
        if category in self.category_stats:
            self.category_stats[category]["total"] = total

    def _generate_display(self) -> Group:
        """
        Generate complete display.
        """
        if not HAS_RICH:
            return Group()

        components = []

        # Progress bar
        components.append(self.progress)

        # Statistics panel
        stats_table = Table(show_header=False, box=None, padding=(0, 1))
        stats_table.add_column("Label", style="cyan")
        stats_table.add_column("Value", style="white")

        stats_table.add_row("✅ Passed", f"[green]{self.stats['passed']}[/green]")
        stats_table.add_row("❌ Failed", f"[red]{self.stats['failed']}[/red]")
        stats_table.add_row("⏭️  Skipped", f"[yellow]{self.stats['skipped']}[/yellow]")
        stats_table.add_row("💾 Cached", f"[blue]{self.stats['cached']}[/blue]")

        # Pass rate
        completed = self.stats["current"] - self.stats["skipped"] - self.stats["cached"]
        if completed > 0:
            pass_rate = (self.stats["passed"] / completed) * 100
            stats_table.add_row(
                "📊 Pass Rate", f"[{'green' if pass_rate >= 90 else 'yellow'}]{pass_rate:.1f}%[/]"
            )

        components.append(Panel(stats_table, title="[bold]Statistics[/bold]", border_style="blue"))

        # Category breakdown (if multiple categories)
        if len([s for s in self.category_stats.values() if s["total"] > 0]) > 1:
            cat_table = Table(show_header=True, box=None)
            cat_table.add_column("Category", style="cyan")
            cat_table.add_column("Progress", style="white")
            cat_table.add_column("✅", style="green")
            cat_table.add_column("❌", style="red")

            for category, stats in self.category_stats.items():
                if stats["total"] > 0:
                    cat_table.add_row(
                        category,
                        f"{stats['completed']}/{stats['total']}",
                        str(stats["passed"]),
                        str(stats["failed"]),
                    )

            components.append(
                Panel(cat_table, title="[bold]By Category[/bold]", border_style="magenta")
            )

        return Group(*components)

    def write(self, message: str) -> None:
        """
        Write a message to console.
        """
        if self.console:
            self.console.print(message)
        else:
            print(message)

    def get_results(self) -> List[Dict[str, Any]]:
        """
        Get all collected results.
        """
        return [r.to_dict() for r in self.collector.completed_results]
