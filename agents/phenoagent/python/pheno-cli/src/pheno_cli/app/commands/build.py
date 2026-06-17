"""
Build and packaging commands.
"""

from rich.console import Console

from ..core import PhenoContext

console = Console()


def package(ctx: PhenoContext):
    """
    Build package for distribution.
    """
    console.print("[bold green]🏗️  Building package...[/bold green]")
    console.print("[yellow]Build commands coming soon![/yellow]")
