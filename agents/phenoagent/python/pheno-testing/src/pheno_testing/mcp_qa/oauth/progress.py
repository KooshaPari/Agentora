"""Unified Progress Display for OAuth Flows.

Combines best features from both implementations:
- Inline progress (single overwritten line)
- Rich terminal support with fallback
- Clean UX without progress bar interference during prompts
"""

from typing import Optional

try:
    from rich.console import Console
    from rich.live import Live
    from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

    HAS_RICH = True
except ImportError:
    HAS_RICH = False


class InlineProgress:
    """Inline progress display that overwrites a single line.

    Features:
    - Single-line updates (no new lines spam)
    - Rich terminal support with graceful fallback
    - Temporary pause for clean user input
    """

    def __init__(self):
        """
        Initialize inline progress.
        """
        self.console = Console() if HAS_RICH else None
        self.current_step = ""
        self.live = None
        self.progress = None
        self.task = None

    def start(self, total_steps: int = 0):
        """Start progress display.

        Args:
            total_steps: Total number of steps (0 for indeterminate)
        """
        if HAS_RICH and self.console:
            self.progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                TimeElapsedColumn(),
                console=self.console,
            )
            self.live = Live(self.progress, console=self.console, refresh_per_second=4)
            self.live.start()
            self.task = self.progress.add_task("Starting...", total=total_steps or None)

    def update(self, message: str, advance: int = 0):
        """Update progress message (overwrites current line).

        Args:
            message: Status message
            advance: Steps to advance (for progress bar mode)
        """
        self.current_step = message

        if self.progress and self.task is not None:
            self.progress.update(self.task, description=message, advance=advance)
        elif self.console:
            # Fallback: simple console print
            self.console.print(f"\r{message}", end="")
        else:
            # Fallback: carriage return
            print(f"\r{message}", end="", flush=True)

    def complete(self, message: str = "Complete"):
        """Complete progress with final message.

        Args:
            message: Final success message
        """
        if self.live:
            self.live.stop()
            self.live = None

        if self.console:
            self.console.print(f"\r{message}")
        else:
            print(f"\r{message}")

    def error(self, message: str):
        """Show error message.

        Args:
            message: Error message
        """
        if self.live:
            self.live.stop()
            self.live = None

        if self.console:
            self.console.print(f"\r[red]{message}[/red]")
        else:
            print(f"\r{message}")

    def pause(self):
        """
        Pause progress display for clean user input.
        """
        if self.live and self.live.is_started:
            self.live.stop()

    def resume(self):
        """
        Resume progress display after user input.
        """
        if self.live and not self.live.is_started:
            self.live.start()

    def stop(self):
        """
        Stop progress display.
        """
        if self.live:
            self.live.stop()
            self.live = None


class OAuthProgressFlow:
    """OAuth-specific progress flow with predefined steps.

    Features:
    - Predefined OAuth flow steps
    - Context manager support
    - Inline progress updates
    """

    def __init__(self):
        """
        Initialize OAuth progress flow.
        """
        self.progress = InlineProgress()
        self.steps = [
            "Initializing OAuth flow...",
            "Opening OAuth consent page...",
            "Entering credentials...",
            "Submitting login form...",
            "Approving OAuth request...",
            "Completing OAuth callback...",
        ]
        self.current_step_idx = 0

    def __enter__(self):
        """
        Start progress display.
        """
        self.progress.start(total_steps=len(self.steps))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Stop progress display.
        """
        self.progress.stop()
        if exc_type:
            self.progress.error(f"OAuth failed: {exc_val}")

    def step(self, description: Optional[str] = None):
        """Advance to next step.

        Args:
            description: Optional custom description (uses predefined if None)
        """
        if description:
            msg = description
        elif self.current_step_idx < len(self.steps):
            msg = self.steps[self.current_step_idx]
        else:
            msg = "Processing..."

        self.progress.update(msg, advance=1)
        self.current_step_idx += 1

    def complete(self, message: str = "OAuth authentication successful"):
        """Complete OAuth flow.

        Args:
            message: Success message
        """
        self.progress.complete(f"✅ {message}")

    def error(self, message: str):
        """Show OAuth error.

        Args:
            message: Error message
        """
        self.progress.error(f"❌ {message}")


# Convenience function for simple progress
def inline_progress() -> InlineProgress:
    """Create inline progress instance.

    Usage:
        progress = inline_progress()
        progress.start()
        progress.update("Doing something...")
        progress.complete("Done!")
    """
    return InlineProgress()
