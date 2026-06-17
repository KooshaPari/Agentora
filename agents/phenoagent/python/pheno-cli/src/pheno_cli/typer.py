"""Typer integration for pheno.cli.

Provides helpers for building Typer-based CLIs with standard options and context.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

try:
    import typer

    _HAS_TYPER = True
except ImportError:
    _HAS_TYPER = False
    typer = None  # type: ignore


def make_app(name: str, help: str | None = None) -> Any:
    """Create a Typer app with standard global options.

    Automatically adds common CLI options:
    - --verbose/-v: Verbose output
    - --debug: Debug mode
    - --workspace/-w: Workspace path
    - --config/-c: Config file path

    These options are available in ctx.obj for all subcommands.

    Args:
        name: Application name
        help: Help text for the application

    Returns:
        Configured Typer application

    Example:
        from pheno.cli.typer import make_app

        app = make_app("myapp", "My CLI application")

        @app.command()
        def hello(ctx: typer.Context):
            if ctx.obj["verbose"]:
                print("Verbose mode enabled")
            print("Hello!")

        if __name__ == "__main__":
            app()
    """
    if not _HAS_TYPER:
        raise ImportError("Typer is required for make_app. Install with: pip install typer")

    app = typer.Typer(help=help or name)

    @app.callback()
    def _root(
        ctx: typer.Context,
        verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
        debug: bool = typer.Option(False, "--debug", help="Debug mode"),
        workspace: Path | None = typer.Option(None, "--workspace", "-w", help="Workspace path"),
        config_path: Path | None = typer.Option(None, "--config", "-c", help="Config file path"),
    ) -> None:
        """
        Root callback to set up context.
        """
        ctx.ensure_object(dict)
        ctx.obj.update(
            {
                "app_name": name,
                "verbose": verbose,
                "debug": debug,
                "workspace": workspace,
                "config_path": config_path,
            },
        )

    return app


def create_command_group(name: str, help: str | None = None) -> Any:
    """Create a Typer command group.

    Args:
        name: Group name
        help: Help text for the group

    Returns:
        Typer instance for the command group

    Example:
        from pheno.cli.typer import make_app, create_command_group

        app = make_app("myapp")
        db_group = create_command_group("db", "Database commands")

        @db_group.command()
        def migrate():
            print("Running migrations...")

        app.add_typer(db_group, name="db")
    """
    if not _HAS_TYPER:
        raise ImportError(
            "Typer is required for create_command_group. Install with: pip install typer",
        )

    return typer.Typer(name=name, help=help or name)


__all__ = ["create_command_group", "make_app"]
