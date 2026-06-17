"""
TUI interface commands.
"""

import asyncio

import typer
from rich.console import Console

from ..core import PhenoContext
from ..tui.monitors import run_control_center

console = Console()


def dashboard(ctx: PhenoContext):
    """
    Launch main dashboard.
    """
    console.print("[bold green]🎯 Launching Pheno-SDK Dashboard...[/bold green]")
    console.print("[yellow]TUI dashboard coming soon![/yellow]")
    console.print("\n[dim]For now, use the CLI commands:[/dim]")
    console.print("  • [cyan]pheno create project <name>[/cyan] - Create new project")
    console.print("  • [cyan]pheno setup cicd[/cyan] - Setup CI/CD")
    console.print("  • [cyan]pheno dev test[/cyan] - Run tests")
    console.print("  • [cyan]pheno manage list[/cyan] - List projects")


def create_ui(ctx: PhenoContext):
    """
    Interactive project creation.
    """
    console.print("[bold green]🚀 Interactive Project Creator...[/bold green]")
    console.print("[yellow]Interactive TUI coming soon![/yellow]")
    console.print("\n[dim]Use: [cyan]pheno create project --interactive[/cyan][/dim]")


def monitor(
    config_file: str | None = typer.Option(
        None, "--config", "-c", help="Path to configuration file",
    ),
    no_textual: bool = typer.Option(
        False, "--no-textual", help="Disable textual TUI (use rich instead)",
    ),
    refresh_interval: float = typer.Option(
        2.0, "--refresh-interval", "-r", help="Refresh interval in seconds",
    ),
):
    """
    Launch the Pheno Control Center TUI monitor.
    """

    # Show startup banner
    banner_text = """
🧬 Pheno Control Center
Multi-Project Monitor & Control
Press Ctrl+C to exit
    """

    console.print(f"[bold cyan]{banner_text}[/bold cyan]")

    try:
        # Run the control center
        asyncio.run(
            run_control_center(
                config_file=config_file,
                use_textual=not no_textual,
                refresh_interval=refresh_interval,
            ),
        )
    except KeyboardInterrupt:
        console.print("\n[yellow]👋 Shutting down...[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        raise typer.Exit(1)
