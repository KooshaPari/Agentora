#!/usr/bin/env python3
"""
Pheno-SDK CLI - Main Entry Point

A comprehensive framework-style CLI for the pheno-sdk ecosystem.
Provides scaffolding, project management, and development workflow automation.
"""

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.traceback import install as install_rich_traceback

from .commands import (
    build_group,
    config_group,
    create_group,
    deploy_group,
    dev_group,
    manage_group,
    setup_group,
    ui_group,
)
from .commands.context import context_group
from .core import PhenoContext, get_version
from .utils.exceptions import PhenoError, handle_exception
from .utils.logging import setup_logging

# Install rich traceback handler for better error display
install_rich_traceback(show_locals=True)

console = Console()


@click.group(
    name="pheno",  # This will be dynamically updated based on context
    help="Comprehensive CLI framework for the pheno-sdk ecosystem",
    context_settings={"help_option_names": ["-h", "--help"]},
    invoke_without_command=True,
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option(
    "--debug", "-d", is_flag=True, help="Enable debug mode with detailed error information",
)
@click.option("--log-file", type=click.Path(path_type=Path), help="Log output to file")
@click.option(
    "--config-path", type=click.Path(exists=True, path_type=Path), help="Path to configuration file",
)
@click.option("--workspace", type=click.Path(path_type=Path), help="Override workspace directory")
@click.version_option(version=get_version(), prog_name="pheno")
@click.pass_context
def cli(
    ctx: click.Context,
    verbose: bool,
    debug: bool,
    log_file: Path | None,
    config_path: Path | None,
    workspace: Path | None,
):
    """Pheno-SDK CLI - Framework for the pheno-sdk ecosystem."""

    # Setup logging
    setup_logging(verbose=verbose, debug=debug, log_file=log_file)

    # Create and setup context with entry point detection
    pheno_context = PhenoContext(
        verbose=verbose,
        debug=debug,
        config_path=config_path,
        workspace=workspace,
        argv0=ctx.find_root().info_name,  # Get the actual command name used
    )
    ctx.obj = pheno_context

    # Update CLI name based on context
    ctx.info_name = pheno_context.current_context

    # If no subcommand, show help or dashboard with context info
    if ctx.invoked_subcommand is None:
        if pheno_context.config.ui.show_dashboard_by_default:
            # Launch TUI dashboard
            from .commands.ui import dashboard

            dashboard()
        else:
            # Show context information
            context_info = pheno_context.get_context_info()
            console.print(
                f"\n[bold green]{context_info.get('display_name', 'Pheno CLI')}[/bold green]",
            )
            console.print(
                f"[dim]{context_info.get('description', 'CLI framework for the pheno-sdk ecosystem')}[/dim]",
            )
            console.print(f"\n[bold]Context:[/bold] {pheno_context.current_context}")
            console.print(f"[bold]Workspace:[/bold] {pheno_context.workspace}")

            # Show help
            click.echo("\n" + ctx.get_help())


# Register command groups
cli.add_command(create_group)
cli.add_command(setup_group)
cli.add_command(dev_group)
cli.add_command(build_group)
cli.add_command(deploy_group)
cli.add_command(manage_group)
cli.add_command(config_group)
cli.add_command(context_group)
cli.add_command(ui_group)


def main():
    """
    Main entry point for the CLI.
    """
    try:
        cli()
    except PhenoError as e:
        handle_exception(e, debug=False)
        sys.exit(e.exit_code)
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Operation cancelled by user[/yellow]")
        sys.exit(130)  # Standard exit code for Ctrl+C
    except Exception as e:
        handle_exception(e, debug=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
