"""
Context management commands.
"""

from rich.console import Console
from rich.table import Table

from ..core import PhenoContext
from ..core.config import save_config
from ..utils.exceptions import PhenoError

console = Console()


def current(ctx: PhenoContext):
    """
    Show current context information.
    """

    context_info = ctx.get_context_info()

    console.print(f"\n[bold green]Current Context: {ctx.current_context}[/bold green]")
    console.print(f"[bold]Name:[/bold] {context_info.get('display_name', 'Unknown')}")
    console.print(f"[bold]Description:[/bold] {context_info.get('description', 'N/A')}")
    console.print(f"[bold]Workspace:[/bold] {context_info.get('workspace', 'N/A')}")
    console.print(f"[bold]Default Template:[/bold] {context_info.get('default_template', 'N/A')}")

    if context_info.get("deployment_targets"):
        console.print(
            f"[bold]Deployment Targets:[/bold] {', '.join(context_info['deployment_targets'])}",
        )


def list_contexts(ctx: PhenoContext):
    """
    List all available contexts.
    """

    contexts = ctx.get_available_contexts()

    table = Table(title="Available Contexts")
    table.add_column("Name", style="cyan")
    table.add_column("Description", style="green")
    table.add_column("Current", style="yellow")

    for name, description in contexts.items():
        is_current = "✓" if name == ctx.current_context else ""
        table.add_row(name, description, is_current)

    console.print(table)


def use_context(ctx: PhenoContext, context_name: str, workspace: str | None):
    """
    Switch to a different context.
    """

    available_contexts = ctx.get_available_contexts()

    if context_name not in available_contexts:
        console.print(f"[red]❌ Context '{context_name}' not found[/red]")
        console.print("\n[bold]Available contexts:[/bold]")
        for name in available_contexts:
            console.print(f"  • {name}")
        raise PhenoError(f"Context '{context_name}' not found")

    # Switch context
    success = ctx.switch_context(context_name)
    if not success:
        raise PhenoError(f"Failed to switch to context '{context_name}'")

    # Update workspace if specified
    if workspace:
        from pathlib import Path

        ctx.workspace = Path(workspace).expanduser()

    # Update configuration to remember context
    ctx.config.context_system.current_context = context_name
    save_config(ctx.config)

    console.print(f"[bold green]✅ Switched to context: {context_name}[/bold green]")

    context_info = ctx.get_context_info()
    console.print(f"[bold]Workspace:[/bold] {context_info.get('workspace', 'N/A')}")
    console.print(f"[bold]Default Template:[/bold] {context_info.get('default_template', 'N/A')}")


def detect_context(ctx: PhenoContext, project_path: str | None):
    """
    Detect the appropriate context for a project.
    """

    from pathlib import Path

    path = Path(project_path) if project_path else Path.cwd()

    console.print(f"[bold]🔍 Detecting context for: {path}[/bold]")

    # Try different detection methods
    detector = ctx.context_detector

    entry_point = detector.detect_from_entry_point()
    project = detector.detect_from_project(path)
    config = detector.detect_from_config(path)
    environment = detector.detect_from_environment()

    table = Table(title="Context Detection Results")
    table.add_column("Method", style="cyan")
    table.add_column("Result", style="green")
    table.add_column("Details", style="dim")

    table.add_row(
        "Entry Point",
        entry_point or "[dim]None[/dim]",
        "Based on command name (atoms, zen, byteport)",
    )

    table.add_row(
        "Project Files", project or "[dim]None[/dim]", "Based on project structure and files",
    )

    table.add_row(
        "Configuration", config or "[dim]None[/dim]", "From .pheno.toml or pyproject.toml",
    )

    table.add_row("Environment", environment or "[dim]None[/dim]", "From environment variables")

    console.print(table)

    # Final detection
    detected = detector.detect_context(path)
    console.print(f"\n[bold green]🎯 Final Detection: {detected}[/bold green]")


def context_info(ctx: PhenoContext, context_name: str | None):
    """
    Show detailed information about a context.
    """

    if not context_name:
        context_name = ctx.current_context

    context_config = ctx.config.context_system.get_context(context_name)
    if not context_config:
        raise PhenoError(f"Context '{context_name}' not found")

    console.print(f"\n[bold green]Context: {context_name}[/bold green]")
    console.print(f"[bold]Name:[/bold] {context_config.name}")
    console.print(f"[bold]Description:[/bold] {context_config.description}")
    console.print(f"[bold]Default Template:[/bold] {context_config.default_template}")

    if context_config.workspace_path:
        console.print(f"[bold]Workspace:[/bold] {context_config.workspace_path}")

    if context_config.project_patterns:
        console.print("[bold]Project Patterns:[/bold]")
        for pattern in context_config.project_patterns:
            console.print(f"  • {pattern}")

    if context_config.deployment_targets:
        console.print("[bold]Deployment Targets:[/bold]")
        for target in context_config.deployment_targets:
            console.print(f"  • {target}")

    if context_config.integrations:
        console.print("[bold]Integrations:[/bold]")
        for name, config in context_config.integrations.items():
            status = "✓ Enabled" if config.get("enabled", False) else "○ Available"
            console.print(f"  • {name}: {status}")
