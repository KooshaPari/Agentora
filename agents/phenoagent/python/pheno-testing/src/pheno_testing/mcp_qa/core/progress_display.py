"""Enhanced Progress Display with Rich Metrics.

Single comprehensive progress bar with detailed line-item metrics.
"""

from typing import List, Optional

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
    from rich.text import Text  # noqa: F401 - Used in type hints and rich components

    HAS_RICH = True
except ImportError:
    HAS_RICH = False


class ComprehensiveProgressDisplay:
    """Single progress bar with comprehensive metrics display.

    Shows:
    - Overall progress bar
    - Per-category progress breakdown
    - Current test info
    - Pass/fail counts
    - Performance metrics
    - Cache statistics
    - Worker info (if parallel)
    """

    def __init__(
        self, total_tests: int, categories: List[str], parallel: bool = False, workers: int = 1
    ):
        if not HAS_RICH:
            self.enabled = False
            return

        self.enabled = True
        self.console = Console()
        self.total_tests = total_tests
        self.categories = categories
        self.parallel = parallel
        self.workers = workers

        # Statistics
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.cached = 0
        self.current = 0

        # Category breakdown
        self.category_stats = {
            cat: {"total": 0, "completed": 0, "passed": 0, "failed": 0} for cat in categories
        }

        # Performance metrics
        self.durations: List[float] = []
        self.current_test = ""
        self.current_tool = ""
        self.current_category = ""

        # Setup Rich Progress
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=40),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("({task.completed}/{task.total})"),
            TimeElapsedColumn(),
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
        self.overall_task = self.progress.add_task("[cyan]Running tests", total=self.total_tests)

        # Create live display with progress + metrics
        self.live = Live(self._generate_display(), console=self.console, refresh_per_second=4)
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
        """
        if not self.enabled:
            return

        self.current += 1
        self.current_test = test_name
        self.current_tool = tool_name
        self.current_category = category

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
            if success and not cached and not skipped:
                self.category_stats[category]["passed"] += 1
            elif not success and not skipped:
                self.category_stats[category]["failed"] += 1

        # Track duration
        if not cached:
            self.durations.append(duration_ms)

        # Update progress bar
        self.progress.update(self.overall_task, advance=1)

        # Refresh live display
        if self.live:
            self.live.update(self._generate_display())

    def set_category_total(self, category: str, total: int):
        """
        Set total tests for a category.
        """
        if category in self.category_stats:
            self.category_stats[category]["total"] = total

    def _generate_display(self) -> Group:
        """
        Generate complete display with progress + metrics.
        """
        components = []

        # Main progress bar
        components.append(self.progress)

        # Current test info
        if self.current_test:
            current_info = Table.grid(padding=(0, 2))
            current_info.add_column(style="cyan", justify="right")
            current_info.add_column(style="white")
            current_info.add_row("Current:", f"[yellow]{self.current_test[:60]}[/yellow]")
            current_info.add_row("Tool:", f"[blue]{self.current_tool}[/blue]")
            current_info.add_row("Category:", f"[magenta]{self.current_category}[/magenta]")
            components.append(
                Panel(current_info, title="[bold]Current Test[/bold]", border_style="cyan")
            )

        # Statistics table
        stats_table = Table(show_header=False, box=None, padding=(0, 1))
        stats_table.add_column("Label", style="cyan")
        stats_table.add_column("Value", style="white")

        # Overall stats
        pass_rate = (
            (self.passed / (self.current - self.skipped - self.cached)) * 100
            if (self.current - self.skipped - self.cached) > 0
            else 0
        )

        stats_table.add_row("✅ Passed", f"[green]{self.passed}[/green]")
        stats_table.add_row("❌ Failed", f"[red]{self.failed}[/red]")
        stats_table.add_row("⏭️  Skipped", f"[yellow]{self.skipped}[/yellow]")
        stats_table.add_row("💾 Cached", f"[blue]{self.cached}[/blue]")
        stats_table.add_row(
            "📊 Pass Rate", f"[{'green' if pass_rate >= 90 else 'yellow'}]{pass_rate:.1f}%[/]"
        )

        # Performance metrics
        if self.durations:
            avg_duration = sum(self.durations) / len(self.durations)
            stats_table.add_row("⏱️  Avg Duration", f"{avg_duration:.2f}ms")
            stats_table.add_row(
                "⚡ Min/Max", f"{min(self.durations):.0f}ms / {max(self.durations):.0f}ms"
            )

        # Worker info (if parallel)
        if self.parallel:
            stats_table.add_row("👷 Workers", f"[cyan]{self.workers}[/cyan]")

        components.append(Panel(stats_table, title="[bold]Statistics[/bold]", border_style="blue"))

        # Category breakdown
        cat_table = Table(show_header=True, box=None)
        cat_table.add_column("Category", style="cyan")
        cat_table.add_column("Progress", style="white")
        cat_table.add_column("Passed", style="green")
        cat_table.add_column("Failed", style="red")

        for category, stats in self.category_stats.items():
            if stats["total"] > 0:
                progress_str = f"{stats['completed']}/{stats['total']}"
                cat_table.add_row(
                    category,
                    progress_str,
                    str(stats["passed"]),
                    str(stats["failed"]),
                )

        components.append(
            Panel(cat_table, title="[bold]By Category[/bold]", border_style="magenta")
        )

        return Group(*components)

    def write(self, message: str):
        """
        Write a message above the progress display.
        """
        if self.enabled and self.live:
            self.console.print(message)
