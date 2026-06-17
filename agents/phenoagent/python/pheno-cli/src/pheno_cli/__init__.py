"""
pheno.cli - Command-line interface utilities

Provides helpers for building CLI applications with Typer and other frameworks,
plus the complete Pheno CLI application.

Generic CLI Framework:
    from pheno.cli import CLIRunner, Command, CommandConfig

    class HelloCommand(Command):
        async def execute(self, args):
            return f"Hello {args['name']}!"

        def format_output(self, result):
            return result

    runner = CLIRunner("myapp", "My CLI Application")
    runner.register_command("hello", HelloCommand)
    runner.run()

Output Formatting:
    from pheno.cli import OutputFormatter, TableBuilder

    formatter = OutputFormatter()
    formatter.print_json({"status": "success"})

    table = (TableBuilder("Users")
        .add_column("ID", style="cyan")
        .add_column("Name")
        .add_row("1", "John")
        .build())
    formatter.console.print(table)

Typer Integration:
    from pheno.cli.typer import make_app, create_command_group

    app = make_app("myapp", "My CLI application")

    @app.command()
    def hello(ctx):
        if ctx.obj["verbose"]:
            print("Verbose mode enabled")
        print("Hello!")

    if __name__ == "__main__":
        app()

Pheno CLI Application:
    from pheno.cli.app import get_version

    # The full Pheno CLI is available at pheno.cli.app
    # Run with: python -m pheno.cli.app
"""

# Generic CLI framework exports
from .cli_runner import CLIRunner
from .command import Command, CommandConfig, CommandError, SyncCommand
from .output import (
    OutputFormatter,
    TableBuilder,
    format_dict_as_table,
    format_list_as_table,
)

# Typer integration is available via pheno.cli.typer
# from pheno.cli.typer import make_app, create_command_group

# Pheno CLI app is available via pheno.cli.app
# from pheno.cli.app import get_version

__all__ = [
    "CLIRunner",
    # Command framework
    "Command",
    "CommandConfig",
    "CommandError",
    # Output formatting
    "OutputFormatter",
    "SyncCommand",
    "TableBuilder",
    "format_dict_as_table",
    "format_list_as_table",
]
