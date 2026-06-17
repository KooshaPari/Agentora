"""
Ecosystem management commands.
"""

from rich.console import Console
from rich.table import Table

from ..core import PhenoContext

console = Console()


def list_projects(ctx: PhenoContext):
    """
    List all projects in workspace.
    """

    console.print("[bold green]📋 Discovering pheno-sdk projects...[/bold green]")

    workspace = ctx.workspace
    projects = []

    # Discover projects in workspace
    if workspace.exists():
        for item in workspace.iterdir():
            if item.is_dir() and ctx.is_pheno_project(item):
                projects.append(item)

    if projects:
        table = Table(title="Pheno-SDK Projects")
        table.add_column("Name", style="cyan")
        table.add_column("Path", style="green")
        table.add_column("Type", style="yellow")

        for project in projects:
            table.add_row(project.name, str(project), "pheno-sdk")

        console.print(table)
    else:
        console.print("[yellow]No pheno-sdk projects found in workspace[/yellow]")
        console.print(f"Workspace: {workspace}")


def health_check(ctx: PhenoContext):
    """
    Run health check on ecosystem.
    """
    console.print("[bold green]🏥 Running ecosystem health check...[/bold green]")
    console.print("[yellow]Health check coming soon![/yellow]")
