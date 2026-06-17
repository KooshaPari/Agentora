"""
Progress utilities for the infrastructure CLI.

Provides a context manager that prefers Rich spinners when the dependency is
available and falls back to plain Click output otherwise.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn

    _RICH_AVAILABLE = True
    _CONSOLE: Console | None = Console()
except ImportError:  # pragma: no cover - exercised via unit tests
    Progress = None  # type: ignore[assignment]
    SpinnerColumn = None  # type: ignore[assignment]
    TextColumn = None  # type: ignore[assignment]
    _RICH_AVAILABLE = False
    _CONSOLE = None


@dataclass
class ProgressReporter:
    """Helper passed into progress contexts for live updates."""

    _update_callback: Callable[[str], None]
    _finish_callback: Callable[[str | None, bool], None]
    _finished: bool = False

    def update(self, message: str) -> None:
        """Update the active progress message."""
        self._update_callback(message)

    def succeed(self, message: str | None = None) -> None:
        """Mark the progress step as successful."""
        if not self._finished:
            self._finish_callback(message, True)
            self._finished = True

    def fail(self, message: str | None = None) -> None:
        """Mark the progress step as failed."""
        if not self._finished:
            self._finish_callback(message, False)
            self._finished = True


def _ensure_suffix(message: str) -> str:
    """Ensure progress messages look like actionable steps."""
    return message if message.endswith("...") else f"{message}..."


@contextmanager
def progress_step(
    message: str,
    *,
    transient: bool = True,
) -> Iterator[ProgressReporter]:
    """
    Provide a Rich-based spinner for CLI work, with Click fallback.

    Args:
        message: The message to display while work is in progress.
        transient: Whether to clear Rich output after completion.

    Yields:
        ProgressReporter for updating or finalising messaging.
    """

    start_message = _ensure_suffix(message)

    if _RICH_AVAILABLE and Progress and SpinnerColumn and TextColumn and _CONSOLE:
        with Progress(
            SpinnerColumn(),
            TextColumn("{task.description}"),
            transient=transient,
            console=_CONSOLE,
        ) as rich_progress:
            task_id = rich_progress.add_task(start_message, total=None)

            def _update(new_message: str) -> None:
                rich_progress.update(task_id, description=_ensure_suffix(new_message))

            def _finish(final_message: str | None, success: bool) -> None:
                status = "done" if success else "failed"
                if final_message:
                    rich_progress.update(task_id, description=final_message)
                else:
                    rich_progress.update(task_id, description=f"{message} {status}")

            reporter = ProgressReporter(_update, _finish)

            try:
                yield reporter
            except Exception:
                reporter.fail()
                raise
            else:
                reporter.succeed()
    else:
        click.echo(start_message)

        def _update(new_message: str) -> None:
            click.echo(_ensure_suffix(new_message))

        def _finish(final_message: str | None, success: bool) -> None:
            if final_message:
                click.echo(final_message)
            else:
                status = "done" if success else "failed"
                click.echo(f"{message} {status}")

        reporter = ProgressReporter(_update, _finish)

        try:
            yield reporter
        except Exception:
            reporter.fail()
            raise
        else:
            reporter.succeed()


__all__ = ["_RICH_AVAILABLE", "ProgressReporter", "progress_step"]
