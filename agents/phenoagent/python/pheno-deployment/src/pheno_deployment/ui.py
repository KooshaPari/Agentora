"""Rich UI utilities for pheno-vendor CLI.

Provides consistent progress reporting, spinners, and summary panels similar to MCP test
output style.
"""

import time
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from typing import Any

try:
    from rich.console import Console
    from rich.live import Live
    from rich.panel import Panel
    from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
    from rich.table import Table

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None  # type: ignore
    Progress = None  # type: ignore
    Panel = None  # type: ignore
    Table = None  # type: ignore
    Live = None  # type: ignore


class StepStatus(Enum):
    """
    Status for progress steps.
    """

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ProgressStep:
    """
    A step in the vendoring process.
    """

    name: str
    status: StepStatus = StepStatus.PENDING
    elapsed: float = 0.0
    message: str = ""

    def format_time(self) -> str:
        """
        Format elapsed time.
        """
        if self.elapsed < 1.0 or self.elapsed < 60:
            return f"{self.elapsed:.1f}s"
        mins = int(self.elapsed / 60)
        secs = self.elapsed % 60
        return f"{mins}m {secs:.1f}s"


class FallbackConsole:
    """
    Fallback console when Rich is not available.
    """

    def print(self, *args, **kwargs):
        """
        Print to stdout.
        """
        # Strip markup
        text = str(args[0]) if args else ""
        # Remove Rich markup
        import re

        text = re.sub(r"\[.*?\]", "", text)
        print(text)

    def rule(self, title: str = "", **kwargs):
        """
        Print a rule.
        """
        print(f"\n{'-' * 40}")
        if title:
            print(title)
        print("-" * 40)


class PhenoUI:
    """UI manager for pheno-vendor CLI.

    Provides rich progress bars, spinners, and summary panels. Falls back to simple
    output if Rich is not available.
    """

    def __init__(self, use_rich: bool = True):
        """
        Initialize UI manager.
        """
        self.use_rich = use_rich and RICH_AVAILABLE

        if self.use_rich:
            self.console = Console()
        else:
            self.console = FallbackConsole()

        self.steps: list[ProgressStep] = []
        self.start_time: float = 0.0

    @contextmanager
    def spinner(self, description: str) -> Generator[dict, None, None]:
        """Context manager for a spinner with timing.

        Usage:
            with ui.spinner("Loading packages") as step:
                # Do work
                step['count'] = 15
            # Automatically shows: ✓ Loading packages [dim](0.5s)[/dim]

        Args:
            description: Description of the step

        Yields:
            Dict that can be updated with additional info
        """
        step_data = {}
        start = time.time()

        if self.use_rich:
            with Progress(
                SpinnerColumn(spinner_name="dots"),
                TextColumn("[progress.description]{task.description}"),
                console=self.console,
                transient=True,
            ) as progress:
                task = progress.add_task(f"⊝ {description}", total=None)

                try:
                    yield step_data
                    elapsed = time.time() - start

                    # Format final message
                    final_msg = f"✓ {description}"
                    if "count" in step_data:
                        final_msg += f" ({step_data['count']})"
                    if "details" in step_data:
                        final_msg += f" - {step_data['details']}"
                    final_msg += f" [dim]({elapsed:.1f}s)[/dim]"

                    progress.update(task, description=final_msg)
                    progress.stop()
                    self.console.print(final_msg)

                except Exception:
                    elapsed = time.time() - start
                    error_msg = f"✗ {description} [red]failed[/red] [dim]({elapsed:.1f}s)[/dim]"
                    progress.update(task, description=error_msg)
                    progress.stop()
                    self.console.print(error_msg)
                    raise
        else:
            # Fallback: simple print
            print(f"⊝ {description}...")
            try:
                yield step_data
                elapsed = time.time() - start
                print(f"✓ {description} ({elapsed:.1f}s)")
            except Exception:
                elapsed = time.time() - start
                print(f"✗ {description} failed ({elapsed:.1f}s)")
                raise

    def step_progress(
        self, description: str, total: int, unit: str = "items",
    ) -> "StepProgressContext":
        """Create a step with a progress bar.

        Usage:
            with ui.step_progress("Vendoring packages", total=15, unit="packages") as step:
                for i in range(15):
                    step.update(i + 1, f"package_{i}")

        Args:
            description: Description of the step
            total: Total number of items
            unit: Unit name for items

        Returns:
            StepProgressContext manager
        """
        return StepProgressContext(self, description, total, unit)

    def success(self, message: str, elapsed: float | None = None):
        """
        Print a success message.
        """
        if elapsed is not None:
            msg = f"✓ {message} [dim]({elapsed:.1f}s)[/dim]"
        else:
            msg = f"✓ {message}"

        if self.use_rich:
            self.console.print(f"[green]{msg}[/green]")
        else:
            print(msg)

    def error(self, message: str, elapsed: float | None = None):
        """
        Print an error message.
        """
        if elapsed is not None:
            msg = f"✗ {message} [dim]({elapsed:.1f}s)[/dim]"
        else:
            msg = f"✗ {message}"

        if self.use_rich:
            self.console.print(f"[red]{msg}[/red]")
        else:
            print(msg)

    def warning(self, message: str):
        """
        Print a warning message.
        """
        if self.use_rich:
            self.console.print(f"[yellow]⚠ {message}[/yellow]")
        else:
            print(f"⚠ {message}")

    def info(self, message: str):
        """
        Print an info message.
        """
        if self.use_rich:
            self.console.print(f"[cyan]ℹ {message}[/cyan]")
        else:
            print(f"ℹ {message}")

    def panel(self, content: str, title: str, style: str = "blue"):
        """
        Print a panel with content.
        """
        if self.use_rich:
            self.console.print(Panel(content, title=title, border_style=style))
        else:
            print(f"\n{'='*60}")
            print(f" {title}")
            print("=" * 60)
            print(content)
            print("=" * 60)

    def summary_panel(
        self,
        title: str,
        stats: dict[str, Any],
        status: str = "success",
        total_time: float | None = None,
    ):
        """Print a summary panel at the end of operations.

        Args:
            title: Panel title
            stats: Dictionary of statistics to display
            status: Overall status (success/failed)
            total_time: Total elapsed time
        """
        if self.use_rich:
            self._print_rich_summary_panel(title, stats, status, total_time)
        else:
            self._print_fallback_summary_panel(title, stats, status, total_time)

    def _print_rich_summary_panel(
        self, title: str, stats: dict[str, Any], status: str, total_time: float | None,
    ) -> None:
        """
        Print summary panel using Rich formatting.
        """
        lines = self._build_summary_lines(stats, status, total_time)
        self._print_rich_panel(title, lines)

    def _print_fallback_summary_panel(
        self, title: str, stats: dict[str, Any], status: str, total_time: float | None,
    ) -> None:
        """
        Print summary panel using fallback formatting.
        """
        print(f"\n{'='*60}")
        print(f" {title}")
        print("=" * 60)

        for key, value in stats.items():
            print(f"{key}: {value}")

        if total_time is not None:
            print(f"Time: {total_time:.1f}s")

        status_symbol = "✓" if status == "success" else "✗"
        status_text = "Ready for deployment" if status == "success" else "Failed"
        print(f"Status: {status_symbol} {status_text}")
        print("=" * 60)

    def _build_summary_lines(
        self, stats: dict[str, Any], status: str, total_time: float | None,
    ) -> list[str]:
        """
        Build list of lines for summary panel.
        """
        lines = []

        for key, value in stats.items():
            lines.append(f"{key}: {value}")

        if total_time is not None:
            lines.append(f"Time: {total_time:.1f}s")

        # Status line
        status_symbol = "✓" if status == "success" else "✗"
        status_text = "Ready for deployment" if status == "success" else "Failed"
        lines.append(f"Status: {status_symbol} {status_text}")

        return lines

    def _print_rich_panel(self, title: str, lines: list[str]) -> None:
        """
        Print Rich-formatted panel with box drawing.
        """
        self.console.print(f"\n╔{'═' * 58}╗")
        self.console.print(f"║ {title:<56} ║")
        self.console.print(f"╠{'═' * 58}╣")
        for line in lines:
            self.console.print(f"║ {line:<56} ║")
        self.console.print(f"╚{'═' * 58}╝\n")

    def table(self, title: str, columns: list[str], rows: list[list[str]]):
        """
        Print a table.
        """
        if self.use_rich:
            table = Table(title=title, show_header=True)
            for col in columns:
                table.add_column(col)
            for row in rows:
                table.add_row(*row)
            self.console.print(table)
        else:
            # Simple fallback
            print(f"\n{title}")
            print("-" * 60)
            print(" | ".join(columns))
            print("-" * 60)
            for row in rows:
                print(" | ".join(str(cell) for cell in row))
            print("-" * 60)


class StepProgressContext:
    """
    Context manager for step progress tracking.
    """

    def __init__(self, ui: PhenoUI, description: str, total: int, unit: str):
        self.ui = ui
        self.description = description
        self.total = total
        self.unit = unit
        self.progress = None
        self.task = None
        self.start_time = 0.0

    def __enter__(self):
        """
        Enter context.
        """
        self.start_time = time.time()

        if self.ui.use_rich:
            self.progress = Progress(
                SpinnerColumn(spinner_name="dots"),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                console=self.ui.console,
            )
            self.progress.__enter__()
            self.task = self.progress.add_task(f"⊝ {self.description}", total=self.total)
        else:
            print(f"⊝ {self.description} (0/{self.total})...")

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit context.
        """
        elapsed = time.time() - self.start_time

        if self.ui.use_rich and self.progress:
            if exc_type is None:
                # Success
                self.progress.update(
                    self.task, description=f"✓ {self.description} ({self.total}/{self.total})",
                )
            else:
                # Failed
                self.progress.update(
                    self.task, description=f"✗ {self.description} [red]failed[/red]",
                )
            self.progress.__exit__(exc_type, exc_val, exc_tb)

            # Print final message
            if exc_type is None:
                self.ui.success(f"{self.description} ({self.total}/{self.total})", elapsed=elapsed)
            else:
                self.ui.error(f"{self.description} failed", elapsed=elapsed)
        elif exc_type is None:
            print(f"✓ {self.description} ({self.total}/{self.total}) ({elapsed:.1f}s)")
        else:
            print(f"✗ {self.description} failed ({elapsed:.1f}s)")

    def update(self, completed: int, current_item: str = ""):
        """
        Update progress.
        """
        if self.ui.use_rich and self.progress:
            desc = f"⊝ {self.description} ({completed}/{self.total})"
            if current_item:
                desc += f" - {current_item}"
            self.progress.update(self.task, completed=completed, description=desc)
        elif completed % max(1, self.total // 10) == 0:  # Update every 10%
            print(f"  Progress: {completed}/{self.total}...")


def create_ui(use_rich: bool = True) -> PhenoUI:
    """Create a UI instance.

    Args:
        use_rich: Whether to use Rich library (auto-detected if True)

    Returns:
        PhenoUI instance
    """
    return PhenoUI(use_rich=use_rich)
