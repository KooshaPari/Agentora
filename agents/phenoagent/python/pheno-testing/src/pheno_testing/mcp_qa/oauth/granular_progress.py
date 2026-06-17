"""Granular OAuth Progress Display with Step-by-Step Tracking.

This module provides a composable progress system that shows each step
of the OAuth authentication flow in detail:

1. Credential manager operations (pulling credentials → pulled)
2. Each page navigation (login page, consent page, etc.)
3. Each interaction (entering email, entering password, clicking buttons)
4. Token exchange
5. Session save

Features:
- Each step is a separate progress item with timing
- Composable: custom flows can add their own steps
- Rich terminal support with fallback
- Clean, readable output

Example Output:
    ✓ Pulling credentials from cache
    ✓ Navigating to login page
    ✓ Entering email
    ✓ Navigating to password page
    ✓ Entering password
    ✓ Clicking sign in
    ✓ Handling consent page
    ✓ Exchanging authorization code for token
    ✓ Saving session
    ✅ Authentication complete (3.2s)
"""

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, List, Optional

try:
    from rich.console import Console
    from rich.live import Live
    from rich.table import Table
    from rich.text import Text

    HAS_RICH = True
except ImportError:
    HAS_RICH = False


class StepStatus(Enum):
    """
    Status of a progress step.
    """

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ProgressStep:
    """
    A single step in the OAuth flow.
    """

    # Step identification
    id: str
    description: str

    # Step state
    status: StepStatus = StepStatus.PENDING
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    error: Optional[str] = None

    # Display customization
    emoji_pending: str = "⏳"
    emoji_in_progress: str = "🔄"
    emoji_completed: str = "✓"
    emoji_failed: str = "✗"
    emoji_skipped: str = "⊝"

    # Metadata
    metadata: dict = field(default_factory=dict)

    @property
    def duration(self) -> Optional[float]:
        """
        Get step duration in seconds.
        """
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None

    @property
    def emoji(self) -> str:
        """
        Get emoji for current status.
        """
        return {
            StepStatus.PENDING: self.emoji_pending,
            StepStatus.IN_PROGRESS: self.emoji_in_progress,
            StepStatus.COMPLETED: self.emoji_completed,
            StepStatus.FAILED: self.emoji_failed,
            StepStatus.SKIPPED: self.emoji_skipped,
        }[self.status]

    def start(self):
        """
        Mark step as started.
        """
        self.status = StepStatus.IN_PROGRESS
        self.start_time = time.time()

    def complete(self, error: Optional[str] = None):
        """
        Mark step as completed or failed.
        """
        self.end_time = time.time()
        if error:
            self.status = StepStatus.FAILED
            self.error = error
        else:
            self.status = StepStatus.COMPLETED

    def skip(self, reason: Optional[str] = None):
        """
        Mark step as skipped.
        """
        self.status = StepStatus.SKIPPED
        if reason:
            self.metadata["skip_reason"] = reason

    def format_line(self, show_timing: bool = True) -> str:
        """
        Format step as a single line.
        """
        parts = [self.emoji, self.description]

        if self.status == StepStatus.IN_PROGRESS:
            parts.append("...")
        elif show_timing and self.duration is not None:
            parts.append(f"({self.duration:.1f}s)")

        if self.error:
            parts.append(f"- {self.error}")

        return " ".join(parts)


class GranularOAuthProgress:
    """Granular progress display for OAuth flows.

    Features:
    - Step-by-step progress tracking
    - Live updates with Rich (or fallback)
    - Composable: add custom steps dynamically
    - Clean output without spam

    Usage:
        progress = GranularOAuthProgress()
        progress.start()

        # Add standard OAuth steps
        progress.add_step("pull_credentials", "Pulling credentials from cache")
        progress.add_step("navigate_login", "Navigating to login page")
        progress.add_step("enter_email", "Entering email")

        # Execute steps
        progress.start_step("pull_credentials")
        # ... do work ...
        progress.complete_step("pull_credentials")

        progress.complete("Authentication complete")
    """

    def __init__(self, show_timing: bool = True):
        """Initialize granular progress.

        Args:
            show_timing: Show step durations
        """
        self.show_timing = show_timing
        self.steps: List[ProgressStep] = []
        self.console = Console() if HAS_RICH else None
        self.live: Optional[Live] = None
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self._step_lookup: dict[str, ProgressStep] = {}
        self._completed = False

    def add_step(self, step_id: str, description: str, **kwargs) -> ProgressStep:
        """Add a step to the progress tracker.

        Args:
            step_id: Unique step identifier
            description: Human-readable description
            **kwargs: Additional ProgressStep arguments

        Returns:
            The created ProgressStep
        """
        step = ProgressStep(id=step_id, description=description, **kwargs)
        self.steps.append(step)
        self._step_lookup[step_id] = step
        self._refresh()
        return step

    def get_step(self, step_id: str) -> Optional[ProgressStep]:
        """
        Get step by ID.
        """
        return self._step_lookup.get(step_id)

    def start_step(self, step_id: str):
        """
        Start a step.
        """
        step = self._step_lookup.get(step_id)
        if step:
            step.start()
            self._refresh()

    def complete_step(self, step_id: str, error: Optional[str] = None):
        """
        Complete a step.
        """
        step = self._step_lookup.get(step_id)
        if step:
            step.complete(error)
            self._refresh()

    def skip_step(self, step_id: str, reason: Optional[str] = None):
        """
        Skip a step.
        """
        step = self._step_lookup.get(step_id)
        if step:
            step.skip(reason)
            self._refresh()

    def update_step_description(self, step_id: str, description: str):
        """
        Update step description (e.g., to add details).
        """
        step = self._step_lookup.get(step_id)
        if step:
            step.description = description
            self._refresh()

    @contextmanager
    def step(self, step_id: str, description: str, **kwargs):
        """Context manager for auto-completing steps.

        Usage:
            with progress.step("my_step", "Doing something"):
                # ... do work ...
                pass
        """
        step = self.add_step(step_id, description, **kwargs)
        step.start()
        self._refresh()

        try:
            yield step
            step.complete()
        except Exception as e:
            step.complete(error=str(e))
            raise
        finally:
            self._refresh()

    def start(self):
        """
        Start progress display.
        """
        self.start_time = time.time()

        if HAS_RICH and self.console:
            self.live = Live(
                self._render(), console=self.console, refresh_per_second=4, transient=False
            )
            self.live.start()
        else:
            # Fallback: just print initial message
            print("Starting OAuth authentication...")

    def complete(self, message: str = "Authentication complete"):
        """
        Complete progress with final message.
        """
        self.end_time = time.time()
        self._completed = True

        if self.live:
            self.live.stop()
            self.live = None

        # Print final summary
        total_time = self.end_time - self.start_time if self.start_time else 0

        if self.console:
            self.console.print(f"\n[green]✅ {message}[/green] [dim]({total_time:.1f}s)[/dim]")
        else:
            print(f"\n✅ {message} ({total_time:.1f}s)")

    def error(self, message: str):
        """
        Show error and stop.
        """
        self.end_time = time.time()
        self._completed = True

        if self.live:
            self.live.stop()
            self.live = None

        if self.console:
            self.console.print(f"\n[red]❌ {message}[/red]")
        else:
            print(f"\n❌ {message}")

    def _refresh(self):
        """
        Refresh the live display.
        """
        if self.live and self.live.is_started and not self._completed:
            self.live.update(self._render())
        elif not HAS_RICH and not self._completed:
            # Fallback: print each completed step once
            for step in self.steps:
                if step.status == StepStatus.COMPLETED and not step.metadata.get("printed"):
                    print(step.format_line(self.show_timing))
                    step.metadata["printed"] = True

    def _render(self) -> Any:
        """
        Render progress display.
        """
        if HAS_RICH and self.console:
            return self._render_rich()
        else:
            return self._render_plain()

    def _render_rich(self) -> Table:
        """
        Render using Rich table.
        """
        table = Table.grid(padding=(0, 1))
        table.add_column(style="cyan", width=3)
        table.add_column()

        for step in self.steps:
            emoji = step.emoji
            description = step.description

            # Color based on status
            if step.status == StepStatus.COMPLETED:
                style = "green"
            elif step.status == StepStatus.FAILED:
                style = "red"
            elif step.status == StepStatus.IN_PROGRESS:
                style = "yellow"
            elif step.status == StepStatus.SKIPPED:
                style = "dim"
            else:
                style = "dim"

            # Build description with timing
            desc_parts = [description]
            if step.status == StepStatus.IN_PROGRESS:
                desc_parts.append("...")
            elif self.show_timing and step.duration is not None:
                desc_parts.append(f"[dim]({step.duration:.1f}s)[/dim]")

            if step.error:
                desc_parts.append(f"[red]- {step.error}[/red]")

            table.add_row(Text(emoji), Text(" ".join(desc_parts), style=style))

        return table

    def _render_plain(self) -> str:
        """
        Render plain text (fallback).
        """
        lines = []
        for step in self.steps:
            lines.append(step.format_line(self.show_timing))
        return "\n".join(lines)


# Predefined step templates for common OAuth flows
class OAuthSteps:
    """
    Predefined OAuth step definitions.
    """

    # Credential management
    PULL_CREDENTIALS = ("pull_credentials", "Pulling credentials from cache")
    LOAD_ENV_CREDENTIALS = ("load_env_credentials", "Loading credentials from environment")
    PROMPT_CREDENTIALS = ("prompt_credentials", "Prompting for credentials")
    SAVE_CREDENTIALS = ("save_credentials", "Saving credentials to cache")

    # OAuth initialization
    INIT_OAUTH = ("init_oauth", "Initializing OAuth flow")
    FETCH_OAUTH_URL = ("fetch_oauth_url", "Fetching OAuth authorization URL")

    # Page navigation
    NAVIGATE_LOGIN = ("navigate_login", "Navigating to login page")
    NAVIGATE_PASSWORD = ("navigate_password", "Navigating to password page")
    NAVIGATE_CONSENT = ("navigate_consent", "Navigating to consent page")

    # Form interactions
    ENTER_EMAIL = ("enter_email", "Entering email")
    ENTER_PASSWORD = ("enter_password", "Entering password")
    CLICK_CONTINUE = ("click_continue", "Clicking continue button")
    CLICK_SIGNIN = ("click_signin", "Clicking sign in button")
    CLICK_ALLOW = ("click_allow", "Clicking allow/authorize button")

    # MFA
    ENTER_MFA_CODE = ("enter_mfa", "Entering MFA code")
    WAIT_FOR_MFA = ("wait_mfa", "Waiting for MFA approval")

    # Token exchange
    EXCHANGE_TOKEN = ("exchange_token", "Exchanging authorization code for token")
    VALIDATE_TOKEN = ("validate_token", "Validating access token")

    # Session
    SAVE_SESSION = ("save_session", "Saving session")
    VERIFY_SESSION = ("verify_session", "Verifying session")

    # Completion
    FINALIZE = ("finalize", "Finalizing authentication")


def create_standard_oauth_progress() -> GranularOAuthProgress:
    """Create a progress tracker with standard OAuth steps pre-added.

    Returns:
        GranularOAuthProgress with common steps
    """
    progress = GranularOAuthProgress()

    # Add standard steps
    progress.add_step(*OAuthSteps.PULL_CREDENTIALS)
    progress.add_step(*OAuthSteps.INIT_OAUTH)
    progress.add_step(*OAuthSteps.FETCH_OAUTH_URL)
    progress.add_step(*OAuthSteps.NAVIGATE_LOGIN)
    progress.add_step(*OAuthSteps.ENTER_EMAIL)
    progress.add_step(*OAuthSteps.ENTER_PASSWORD)
    progress.add_step(*OAuthSteps.CLICK_SIGNIN)
    progress.add_step(*OAuthSteps.NAVIGATE_CONSENT)
    progress.add_step(*OAuthSteps.CLICK_ALLOW)
    progress.add_step(*OAuthSteps.EXCHANGE_TOKEN)
    progress.add_step(*OAuthSteps.SAVE_SESSION)

    return progress
