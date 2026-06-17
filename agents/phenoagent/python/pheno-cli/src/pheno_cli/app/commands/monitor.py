"""Monitor command for Pheno Control Center.

Provides command-line interface to launch the enhanced TUI monitor for managing multiple
pheno-sdk projects.
"""

import asyncio
import logging

import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from ..tui.monitors import run_control_center, run_tui_monitor

app = typer.Typer(
    name="monitor", help="Launch the Pheno Control Center TUI monitor", no_args_is_help=True,
)

console = Console()


@app.command("start")
def start_monitor(
    config_file: str | None = typer.Option(
        None, "--config", "-c", help="Path to configuration file",
    ),
    no_textual: bool = typer.Option(
        False, "--no-textual", help="Disable textual TUI (use rich instead)",
    ),
    refresh_interval: float = typer.Option(
        2.0, "--refresh-interval", "-r", help="Refresh interval in seconds",
    ),
    simple: bool = typer.Option(
        False, "--simple", help="Use simple monitor (no enhanced features)",
    ),
):
    """
    Start the Pheno Control Center TUI monitor.
    """

    # Show startup banner
    banner_text = Text()
    banner_text.append("🧬 Pheno Control Center\n", style="bold cyan")
    banner_text.append("Multi-Project Monitor & Control\n", style="bold")
    banner_text.append("Press Ctrl+C to exit\n", style="dim")

    console.print(Panel(banner_text, box="double", border_style="cyan"))

    # Setup logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    try:
        if simple:
            # Run simple monitor
            console.print("[yellow]Starting simple monitor...[/yellow]")
            asyncio.run(run_tui_monitor(use_textual=not no_textual))
        else:
            # Run full control center
            console.print("[green]Starting Pheno Control Center...[/green]")
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


@app.command("status")
def show_status(
    project: str | None = typer.Option(
        None, "--project", "-p", help="Show status for specific project",
    ),
):
    """
    Show current status of projects.
    """

    from ..tui.enhanced_monitor import ProjectRegistry, UnifiedMonitorEngine

    # Initialize components
    project_registry = ProjectRegistry()
    monitor_engine = UnifiedMonitorEngine()

    # Load default projects
    default_projects = {
        "atoms": {"name": "atoms", "description": "Atoms MCP Server"},
        "zen": {"name": "zen", "description": "Zen MCP Server"},
        "byteport": {"name": "byteport", "description": "Byteport Service"},
    }

    for project_name, config in default_projects.items():
        project_registry.register_project(project_name, config)

    # Get status
    global_status = monitor_engine.get_global_status()

    # Show summary
    summary = global_status["summary"]
    console.print("\n[bold]Global Status:[/bold]")
    console.print(f"  Projects: {summary['healthy_projects']}/{summary['total_projects']} healthy")
    console.print(
        f"  Processes: {summary['running_processes']}/{summary['total_processes']} running",
    )

    # Show project details
    if project:
        if project in global_status["projects"]:
            project_status = global_status["projects"][project]
            console.print(f"\n[bold]{project.upper()}:[/bold]")
            console.print(f"  Status: {project_status['overall_state']}")
            console.print(
                f"  Processes: {project_status['processes']['running']}/{project_status['processes']['total']}",
            )
            console.print(
                f"  Resources: {project_status['resources']['available']}/{project_status['resources']['total']}",
            )
        else:
            console.print(f"[red]Project '{project}' not found[/red]")
    else:
        console.print("\n[bold]Projects:[/bold]")
        for project_name, project_status in global_status["projects"].items():
            status_color = {
                "healthy": "green",
                "degraded": "yellow",
                "down": "red",
                "no_processes": "dim",
            }.get(project_status["overall_state"], "white")

            console.print(
                f"  {project_name}: [{status_color}]{project_status['overall_state']}[/{status_color}]",
            )


@app.command("projects")
def list_projects():
    """
    List available projects.
    """

    from ..tui.enhanced_monitor import ProjectRegistry

    project_registry = ProjectRegistry()

    # Load default projects
    default_projects = {
        "atoms": {
            "name": "atoms",
            "description": "Atoms MCP Server",
            "default_port": 50002,
            "tunnel_domain": "atomcp.kooshapari.com",
        },
        "zen": {
            "name": "zen",
            "description": "Zen MCP Server",
            "default_port": 50001,
            "tunnel_domain": "zen.kooshapari.com",
        },
        "byteport": {
            "name": "byteport",
            "description": "Byteport Service",
            "default_port": 50003,
            "tunnel_domain": "byteport.kooshapari.com",
        },
    }

    for project_name, config in default_projects.items():
        project_registry.register_project(project_name, config)

    projects = project_registry.list_projects()

    if not projects:
        console.print("[dim]No projects available[/dim]")
        return

    console.print("\n[bold]Available Projects:[/bold]")

    for project_name in projects:
        project_config = project_registry.get_project(project_name)
        if project_config:
            config = project_config.get("config", {})
            description = config.get("description", "No description")
            default_port = config.get("default_port", "N/A")
            tunnel_domain = config.get("tunnel_domain", "N/A")

            console.print(f"\n  [bold cyan]{project_name}[/bold cyan]")
            console.print(f"    Description: {description}")
            console.print(f"    Default Port: {default_port}")
            console.print(f"    Tunnel Domain: {tunnel_domain}")


if __name__ == "__main__":
    app()
