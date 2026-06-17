"""Rich TUI Framework for MCP QA SDK.

Provides consistent, informative terminal UI components similar to the test runner:
- Progress bars with statistics
- Status panels
- Category breakdowns
- Live updating displays
- Styled output

Usage:
    from pheno.testing.mcp_qa.ui.rich_tui import TestProgress, StatusPanel, create_progress_bar
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

try:
    from rich.box import ROUNDED
    from rich.console import Console, Group
    from rich.layout import Layout
    from rich.live import Live
    from rich.panel import Panel
    from rich.progress import (
        BarColumn,
        MofNCompleteColumn,
        Progress,
        SpinnerColumn,
        TaskProgressColumn,
        TextColumn,
        TimeElapsedColumn,
        TimeRemainingColumn,
    )
    from rich.table import Table
    from rich.text import Text

    HAS_RICH = True
except ImportError:
    HAS_RICH = False


class TestStatus(Enum):
    """
    Test execution status.
    """

    PASSED = "✅"
    FAILED = "❌"
    SKIPPED = "⏭️"
    CACHED = "💾"
    RUNNING = "⠋"


@dataclass
class TestResult:
    """
    Individual test result.
    """

    name: str
    category: str
    tool: Optional[str] = None
    status: TestStatus = TestStatus.RUNNING
    duration_ms: float = 0
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class CategoryStats:
    """
    Statistics for a test category.
    """

    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    cached: int = 0

    @property
    def completed(self) -> int:
        return self.passed + self.failed + self.skipped + self.cached

    @property
    def progress_percent(self) -> float:
        return (self.completed / self.total * 100) if self.total > 0 else 0


class TestProgressTracker:
    """Tracks test execution progress with rich, informative display.

    Features:
    - Live progress bar with spinner
    - Current test information
    - Real-time statistics
    - Category breakdown
    - Duration tracking
    """

    def __init__(
        self,
        total_tests: int,
        categories: Optional[List[str]] = None,
        console: Optional[Console] = None,
    ):
        """Initialize progress tracker.

        Args:
            total_tests: Total number of tests to run
            categories: List of test categories
            console: Rich console instance
        """
        if not HAS_RICH:
            raise RuntimeError("Rich library required for TUI. Install with: pip install rich")

        self.console = console or Console()
        self.total_tests = total_tests
        self.results: List[TestResult] = []
        self.current_test: Optional[TestResult] = None
        self.start_time = datetime.now()

        # Category tracking
        self.categories: Dict[str, CategoryStats] = {}
        if categories:
            for cat in categories:
                self.categories[cat] = CategoryStats()

        # Progress components
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=self.console,
            transient=False,
        )

        self.task_id = self.progress.add_task("Running tests", total=total_tests)

        self.live: Optional[Live] = None

    def start(self):
        """
        Start the live display.
        """
        self.live = Live(self._create_layout(), console=self.console, refresh_per_second=4)
        self.live.start()

    def stop(self):
        """
        Stop the live display.
        """
        if self.live:
            self.live.stop()

    def update_test(
        self,
        name: str,
        category: str,
        tool: Optional[str] = None,
        status: TestStatus = TestStatus.RUNNING,
    ):
        """Update current test being executed.

        Args:
            name: Test name
            category: Test category
            tool: Tool being tested
            status: Current status
        """
        self.current_test = TestResult(name=name, category=category, tool=tool, status=status)

        if self.live:
            self.live.update(self._create_layout())

    def complete_test(self, status: TestStatus, duration_ms: float, error: Optional[str] = None):
        """Mark current test as complete.

        Args:
            status: Final test status
            duration_ms: Test duration in milliseconds
            error: Error message if failed
        """
        if self.current_test:
            self.current_test.status = status
            self.current_test.duration_ms = duration_ms
            self.current_test.error = error
            self.results.append(self.current_test)

            # Update category stats
            cat = self.current_test.category
            if cat not in self.categories:
                self.categories[cat] = CategoryStats()

            stats = self.categories[cat]
            stats.total += 1

            if status == TestStatus.PASSED:
                stats.passed += 1
            elif status == TestStatus.FAILED:
                stats.failed += 1
            elif status == TestStatus.SKIPPED:
                stats.skipped += 1
            elif status == TestStatus.CACHED:
                stats.cached += 1

            # Update progress bar
            self.progress.update(self.task_id, advance=1)

            if self.live:
                self.live.update(self._create_layout())

    def _create_layout(self) -> Group:
        """
        Create the layout with all panels.
        """
        components = []

        # Progress bar
        components.append(self.progress)

        # Current test panel
        if self.current_test:
            components.append(self._create_current_test_panel())

        # Statistics panel
        components.append(self._create_statistics_panel())

        # Category breakdown
        if self.categories:
            components.append(self._create_category_panel())

        return Group(*components)

    def _create_current_test_panel(self) -> Panel:
        """
        Create current test information panel.
        """
        if not self.current_test:
            return Panel("")

        table = Table.grid(padding=(0, 2))
        table.add_column(style="cyan", justify="right")
        table.add_column()

        table.add_row("Current:", self.current_test.name)
        if self.current_test.tool:
            table.add_row("Tool:", self.current_test.tool)
        table.add_row("Category:", self.current_test.category)

        return Panel(table, title="Current Test", border_style="blue", box=ROUNDED)

    def _create_statistics_panel(self) -> Panel:
        """
        Create statistics panel.
        """
        stats = self._calculate_stats()

        table = Table.grid(padding=(0, 2))
        table.add_column(style="bold")
        table.add_column(justify="right")

        # Status counts
        table.add_row(f"{TestStatus.PASSED.value} Passed", f"[green]{stats['passed']}[/green]")
        table.add_row(f"{TestStatus.FAILED.value} Failed", f"[red]{stats['failed']}[/red]")
        table.add_row(f"{TestStatus.SKIPPED.value} Skipped", f"[yellow]{stats['skipped']}[/yellow]")
        table.add_row(f"{TestStatus.CACHED.value} Cached", f"[blue]{stats['cached']}[/blue]")

        # Pass rate
        table.add_row("📊 Pass Rate", f"[bold]{stats['pass_rate']:.1f}%[/bold]")

        # Timing
        table.add_row("⏱️  Avg Duration", f"{stats['avg_duration_ms']:.2f}ms")
        table.add_row(
            "⚡ Min/Max", f"{stats['min_duration_ms']:.0f}ms / {stats['max_duration_ms']:.0f}ms"
        )

        return Panel(table, title="Statistics", border_style="green", box=ROUNDED)

    def _create_category_panel(self) -> Panel:
        """
        Create category breakdown panel.
        """
        table = Table(show_header=True, box=None)
        table.add_column("Category", style="cyan")
        table.add_column("Progress", justify="center")
        table.add_column("Passed", justify="right", style="green")
        table.add_column("Failed", justify="right", style="red")

        for category, stats in sorted(self.categories.items()):
            progress = f"{stats.completed}/{stats.total}"
            table.add_row(category, progress, str(stats.passed), str(stats.failed))

        return Panel(table, title="By Category", border_style="magenta", box=ROUNDED)

    def _calculate_stats(self) -> Dict[str, Any]:
        """
        Calculate overall statistics.
        """
        completed = [r for r in self.results if r.status != TestStatus.RUNNING]

        if not completed:
            return {
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "cached": 0,
                "pass_rate": 0.0,
                "avg_duration_ms": 0.0,
                "min_duration_ms": 0.0,
                "max_duration_ms": 0.0,
            }

        passed = sum(1 for r in completed if r.status == TestStatus.PASSED)
        failed = sum(1 for r in completed if r.status == TestStatus.FAILED)
        skipped = sum(1 for r in completed if r.status == TestStatus.SKIPPED)
        cached = sum(1 for r in completed if r.status == TestStatus.CACHED)

        durations = [r.duration_ms for r in completed if r.duration_ms > 0]

        return {
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "cached": cached,
            "pass_rate": (passed / len(completed) * 100) if completed else 0.0,
            "avg_duration_ms": sum(durations) / len(durations) if durations else 0.0,
            "min_duration_ms": min(durations) if durations else 0.0,
            "max_duration_ms": max(durations) if durations else 0.0,
        }


class StatusPanel:
    """Simple status panel for operations.

    Shows current operation with spinner and status messages.
    """

    def __init__(self, title: str = "Status", console: Optional[Console] = None):
        """Initialize status panel.

        Args:
            title: Panel title
            console: Rich console instance
        """
        if not HAS_RICH:
            raise RuntimeError("Rich library required for TUI")

        self.console = console or Console()
        self.title = title
        self.messages: List[Tuple[str, str]] = []  # (emoji, message)
        self.live: Optional[Live] = None

    def start(self):
        """
        Start live display.
        """
        self.live = Live(self._create_panel(), console=self.console, refresh_per_second=4)
        self.live.start()

    def stop(self):
        """
        Stop live display.
        """
        if self.live:
            self.live.stop()

    def update(self, message: str, emoji: str = "⠋"):
        """Update status message.

        Args:
            message: Status message
            emoji: Emoji/icon for message
        """
        self.messages.append((emoji, message))
        if len(self.messages) > 10:  # Keep last 10 messages
            self.messages.pop(0)

        if self.live:
            self.live.update(self._create_panel())

    def _create_panel(self) -> Panel:
        """
        Create the status panel.
        """
        text = Text()
        for emoji, message in self.messages:
            text.append(f"{emoji} {message}\n")

        return Panel(text, title=self.title, border_style="blue", box=ROUNDED)


def create_progress_bar(
    description: str, total: Optional[int] = None, console: Optional[Console] = None
) -> Progress:
    """Create a styled progress bar.

    Args:
        description: Progress description
        total: Total items (None for indeterminate)
        console: Rich console instance

    Returns:
        Rich Progress instance
    """
    if not HAS_RICH:
        raise RuntimeError("Rich library required")

    console = console or Console()

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    )

    progress.add_task(description, total=total)
    return progress


def create_summary_table(
    title: str,
    data: List[Dict[str, Any]],
    columns: List[Tuple[str, str]],  # (key, header)
    console: Optional[Console] = None,
) -> Table:
    """Create a styled summary table.

    Args:
        title: Table title
        data: List of data dictionaries
        columns: List of (key, header) tuples
        console: Rich console instance

    Returns:
        Rich Table instance
    """
    if not HAS_RICH:
        raise RuntimeError("Rich library required")

    table = Table(title=title, show_header=True, box=ROUNDED, border_style="cyan")

    for key, header in columns:
        table.add_column(header, style="cyan")

    for row in data:
        table.add_row(*[str(row.get(key, "")) for key, _ in columns])

    return table


# Convenience functions for common patterns


def print_success(message: str, console: Optional[Console] = None):
    """
    Print success message.
    """
    console = console or Console()
    console.print(f"✅ {message}", style="bold green")


def print_error(message: str, console: Optional[Console] = None):
    """
    Print error message.
    """
    console = console or Console()
    console.print(f"❌ {message}", style="bold red")


def print_warning(message: str, console: Optional[Console] = None):
    """
    Print warning message.
    """
    console = console or Console()
    console.print(f"⚠️  {message}", style="bold yellow")


def print_info(message: str, console: Optional[Console] = None):
    """
    Print info message.
    """
    console = console or Console()
    console.print(f"ℹ️  {message}", style="bold blue")


def print_section(title: str, console: Optional[Console] = None):
    """
    Print section header.
    """
    console = console or Console()
    console.print()
    console.rule(f"[bold cyan]{title}[/bold cyan]")
    console.print()
