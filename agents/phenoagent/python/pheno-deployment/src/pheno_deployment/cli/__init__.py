"""
Pheno deployment CLI package.
"""

from __future__ import annotations

import click

from .commands.hooks import generate_hooks, install_hooks, uninstall_hooks, verify_hooks
from .commands.maintenance import (
    check_freshness_cmd,
    clean,
    info,
    startup_check_cmd,
    validate,
)
from .commands.setup import setup
from .shared import console


@click.group()
@click.version_option(version="0.1.0", prog_name="pheno-vendor")
def cli() -> None:
    """Pheno-SDK Deployment Toolkit - Vendoring and production preparation."""


cli.add_command(setup)
cli.add_command(validate)
cli.add_command(clean)
cli.add_command(info)
cli.add_command(generate_hooks)
cli.add_command(install_hooks)
cli.add_command(uninstall_hooks)
cli.add_command(verify_hooks)
cli.add_command(check_freshness_cmd)
cli.add_command(startup_check_cmd)


def main() -> None:
    """
    Entry point for pheno-vendor CLI.
    """
    cli()


__all__ = ["cli", "console", "main"]
