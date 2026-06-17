"""
Git hook management commands.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from pheno.deployment.install_hooks import (
    install_pre_push_hook,
    uninstall_pre_push_hook,
    verify_hook_installation,
)

from ..shared import console


@click.command(name="generate-hooks")
@click.option(
    "--project-root",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root directory (default: current directory)",
)
@click.option(
    "--platform",
    type=click.Choice(["vercel", "docker", "lambda", "auto"], case_sensitive=False),
    default="auto",
    help="Target platform (default: auto-detect)",
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default=None,
    help="Output file for build hooks (default: stdout)",
)
def generate_hooks(project_root: Path | None, platform: str, output: Path | None) -> None:
    """
    Generate build hooks for deployment platforms.
    """
    from pheno.deployment.utils import BuildHookGenerator, PlatformDetector

    try:
        project_root = Path(project_root or Path.cwd())
        if platform == "auto":
            detector = PlatformDetector(project_root)
            platform = detector.detect()
            console.print(f"[dim]Detected platform: {platform}[/dim]\n")

        generator = BuildHookGenerator(project_root)
        hooks = generator.generate(platform)

        if output:
            output.write_text(hooks)
            console.print(f"[green]✓ Generated build hooks: {output}[/green]")
        else:
            console.print(hooks)

    except Exception as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        sys.exit(1)


@click.command(name="install-hooks")
@click.option(
    "--project-root",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root directory (default: current directory)",
)
@click.option("--force", is_flag=True, help="Overwrite existing hook")
@click.option("--no-backup", is_flag=True, help="Don't backup existing hook")
def install_hooks(project_root: Path | None, force: bool, no_backup: bool) -> None:
    """
    Install git pre-push hook for automatic vendoring.
    """
    console.print("[bold]Installing git hooks...[/bold]\n")
    try:
        success = install_pre_push_hook(
            project_root=project_root, force=force, backup=not no_backup,
        )
        if success:
            console.print("\n[bold green]✓ Git hook installed successfully![/bold green]")
            console.print("\n[dim]Run 'pheno-vendor verify-hooks' to test installation[/dim]")
        else:
            console.print("\n[bold red]✗ Hook installation failed[/bold red]")
            sys.exit(1)
    except Exception as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        sys.exit(1)


@click.command(name="uninstall-hooks")
@click.option(
    "--project-root",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root directory (default: current directory)",
)
@click.option("--no-restore", is_flag=True, help="Don't restore backup hook")
def uninstall_hooks(project_root: Path | None, no_restore: bool) -> None:
    """
    Uninstall git pre-push hook.
    """
    console.print("[bold]Uninstalling git hooks...[/bold]\n")
    try:
        success = uninstall_pre_push_hook(project_root=project_root, restore_backup=not no_restore)
        if success:
            console.print("\n[bold green]✓ Git hook uninstalled successfully![/bold green]")
        else:
            console.print("\n[bold red]✗ Hook uninstallation failed[/bold red]")
            sys.exit(1)
    except Exception as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        sys.exit(1)


@click.command(name="verify-hooks")
@click.option(
    "--project-root",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root directory (default: current directory)",
)
def verify_hooks(project_root: Path | None) -> None:
    """
    Verify git hook installation.
    """
    console.print("[bold]Verifying git hook installation...[/bold]\n")
    try:
        success = verify_hook_installation(project_root=project_root)
        if not success:
            console.print(
                "\n[yellow]Tip: Run 'pheno-vendor install-hooks' to install the hook[/yellow]",
            )
            sys.exit(1)
    except Exception as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        sys.exit(1)


__all__ = ["generate_hooks", "install_hooks", "uninstall_hooks", "verify_hooks"]
