"""OAuth Flow with Progress Bar.

Shows OAuth authentication as a multi-step progress flow.
"""

import asyncio
from typing import Optional

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn

    HAS_RICH = True
except ImportError:
    HAS_RICH = False


class OAuthProgressFlow:
    """
    Display OAuth flow as progress bar with steps.
    """

    def __init__(self):
        self.console = Console() if HAS_RICH else None
        self.progress: Optional[Progress] = None
        self.task_id = None

    def __enter__(self):
        """
        Start progress display.
        """
        if not HAS_RICH:
            return self

        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=30),
            TaskProgressColumn(),
            console=self.console,
        )

        self.progress.start()
        self.task_id = self.progress.add_task("[cyan]🔐 OAuth Authentication", total=6)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Stop progress display.
        """
        if self.progress:
            self.progress.stop()

    def step(self, description: str, advance: int = 1):
        """
        Advance progress with step description.
        """
        if self.progress and self.task_id is not None:
            self.progress.update(self.task_id, description=f"[cyan]{description}", advance=advance)
        else:
            print(f"  {description}")

    def complete(self, message: str = "Authentication complete"):
        """
        Mark OAuth flow as complete.
        """
        if self.progress and self.task_id is not None:
            self.progress.update(self.task_id, description=f"[green]✅ {message}", completed=6)
        else:
            print(f"✅ {message}")

    def error(self, message: str):
        """
        Show error in OAuth flow.
        """
        if self.progress and self.task_id is not None:
            self.progress.update(self.task_id, description=f"[red]❌ {message}")
        else:
            print(f"❌ {message}")


async def oauth_with_progress(oauth_handler, oauth_url: str) -> bool:
    """Run OAuth flow with progress bar display.

    Args:
        oauth_handler: OAuth automation handler function
        oauth_url: OAuth authorization URL

    Returns:
        True if successful
    """
    with OAuthProgressFlow() as progress:
        try:
            # Step 1: Capture URL
            progress.step("1/6: Captured OAuth URL")
            await asyncio.sleep(0.1)

            # Step 2: Opening browser/automation
            progress.step("2/6: Starting Playwright automation")
            await asyncio.sleep(0.5)

            # Step 3: Navigating to OAuth page
            progress.step("3/6: Navigating to OAuth page")
            await asyncio.sleep(0.5)

            # Step 4: Filling credentials
            progress.step("4/6: Entering credentials")

            # Run actual OAuth automation
            success = await oauth_handler(oauth_url)

            if not success:
                progress.error("OAuth authentication failed")
                return False

            # Step 5: Authorizing
            progress.step("5/6: Authorizing access")
            await asyncio.sleep(0.5)

            # Step 6: Complete
            progress.step("6/6: Receiving token")
            await asyncio.sleep(0.5)

            progress.complete("✅ OAuth authentication successful")
            return True

        except Exception as e:
            progress.error(f"OAuth failed: {str(e)[:50]}")
            return False


# Export
__all__ = ["OAuthProgressFlow", "oauth_with_progress"]
