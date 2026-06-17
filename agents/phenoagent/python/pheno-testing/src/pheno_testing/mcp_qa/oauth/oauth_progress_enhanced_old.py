"""Enhanced OAuth Progress Flow with Better UX.

Fixes:
- Clean input prompts without progress bar interference
- Proper password masking
- Integrated step display in progress bar
- Better error handling and timeouts
"""

import getpass
import time
from contextlib import contextmanager

try:
    from rich.console import Console
    from rich.live import Live
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

    HAS_RICH = True
except ImportError:
    HAS_RICH = False


class EnhancedOAuthProgressFlow:
    """
    Enhanced OAuth progress with clean UX and integrated steps.
    """

    def __init__(self):
        self.console = Console() if HAS_RICH else None
        self.progress = None
        self.task = None
        self.current_step = 0
        self.total_steps = 8
        self.live = None

        self.steps = [
            "Initializing OAuth flow...",
            "Opening OAuth consent page...",
            "Waiting for email input...",
            "Entering email credentials...",
            "Entering password credentials...",
            "Submitting login form...",
            "Approving OAuth request...",
            "Completing OAuth callback...",
        ]

    def __enter__(self):
        if self.console:
            self.console.print("\n[bold blue]🔐 Starting OAuth Authentication Flow[/bold blue]")
        else:
            print("\n🔐 Starting OAuth Authentication Flow")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.live:
            self.live.stop()
        if exc_type and self.console:
            self.console.print(f"\n[red]❌ OAuth failed: {exc_val}[/red]")
        elif exc_type:
            print(f"\n❌ OAuth failed: {exc_val}")

    def step(self, description: str):
        """
        Update progress to next step.
        """
        if self.current_step < len(self.steps):
            step_desc = self.steps[self.current_step]
        else:
            step_desc = description

        if self.console:
            if not self.progress:
                self.progress = Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    TimeElapsedColumn(),
                    console=self.console,
                )
                self.live = Live(self.progress, console=self.console, refresh_per_second=4)
                self.live.start()
                self.task = self.progress.add_task(step_desc, total=self.total_steps)

            self.progress.update(self.task, description=step_desc, completed=self.current_step + 1)
        else:
            print(f"⏳ {step_desc}")

        self.current_step += 1

    def complete(self, message: str):
        """
        Complete the OAuth flow.
        """
        if self.progress and self.task:
            self.progress.update(self.task, description=f"✅ {message}", completed=self.total_steps)

        # Brief pause to show completion
        time.sleep(1)

        if self.live:
            self.live.stop()
            self.live = None

        if self.console:
            self.console.print(f"\n[green]✅ {message}[/green]")
        else:
            print(f"\n✅ {message}")

    def error(self, message: str):
        """
        Handle error in OAuth flow.
        """
        if self.progress and self.task:
            self.progress.update(self.task, description=f"❌ {message}")

        if self.live:
            self.live.stop()
            self.live = None

        if self.console:
            self.console.print(f"\n[red]❌ {message}[/red]")
        else:
            print(f"\n❌ {message}")

    def prompt_credential(self, key: str, hint: str) -> str:
        """
        Prompt for credential with clean UX.
        """
        # Temporarily stop progress display for clean input
        if self.live:
            self.live.stop()

        is_password = "password" in key.lower() or "secret" in key.lower() or "token" in key.lower()

        if self.console:
            self.console.print("\n[cyan]🔑 OAuth Credential Required[/cyan]")
            prompt = f"Enter {hint}: "
        else:
            print("\n🔑 OAuth Credential Required")
            prompt = f"Enter {hint}: "

        try:
            if is_password:
                value = getpass.getpass(prompt)
            else:
                value = input(prompt).strip()

            if not value:
                raise ValueError(f"Empty value provided for {key}")

            if self.console:
                self.console.print(f"[green]✅ {key} received[/green]")
            else:
                print(f"✅ {key} received")

            return value

        finally:
            # Restart progress display
            if self.live and not self.live.is_started:
                self.live.start()

    def update_env_notification(self, env_var: str):
        """
        Show clean notification about .env update.
        """
        if self.live:
            self.live.stop()

        if self.console:
            self.console.print(f"[green]💾 Updated .env with {env_var}[/green]")
        else:
            print(f"💾 Updated .env with {env_var}")

        if self.live and not self.live.is_started:
            self.live.start()


@contextmanager
def clean_oauth_flow():
    """
    Context manager for clean OAuth flow UX.
    """
    flow = EnhancedOAuthProgressFlow()
    try:
        yield flow
    finally:
        if flow.live:
            flow.live.stop()


# Integration function for existing code
def create_progress_flow():
    """Create progress flow - maintains backward compatibility."""
    return EnhancedOAuthProgressFlow()
