"""
Exception handling for Pheno-CLI.
"""

from rich.console import Console
from rich.panel import Panel

console = Console()


class PhenoError(Exception):
    """
    Base exception for Pheno-CLI errors.
    """

    def __init__(self, message: str, hint: str | None = None, exit_code: int = 1):
        """
        Initialize the error.
        """
        super().__init__(message)
        self.message = message
        self.hint = hint
        self.exit_code = exit_code


class TemplateError(PhenoError):
    """
    Template-related errors.
    """


class ProjectError(PhenoError):
    """
    Project-related errors.
    """


class ConfigError(PhenoError):
    """
    Configuration-related errors.
    """


def handle_exception(error: Exception, debug: bool = False) -> None:
    """
    Handle and display exceptions in a user-friendly way.
    """

    if isinstance(error, PhenoError):
        # Custom pheno errors with rich formatting
        message_parts = [f"[red]❌ Error:[/red] {error.message}"]

        if error.hint:
            message_parts.append(f"[yellow]💡 Tip:[/yellow] {error.hint}")

        panel = Panel(
            "\n".join(message_parts),
            title="[bold red]Pheno CLI Error[/bold red]",
            border_style="red",
        )
        console.print(panel)

    # Generic errors
    elif debug:
        # Show full traceback in debug mode
        console.print_exception()
    else:
        # Show simplified error message
        error_message = str(error) or error.__class__.__name__
        panel = Panel(
            f"[red]❌ Unexpected error:[/red] {error_message}",
            title="[bold red]Error[/bold red]",
            border_style="red",
        )
        console.print(panel)
        console.print("[dim]Use --debug for more details[/dim]")
