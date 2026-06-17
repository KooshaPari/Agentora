"""
CLI Application Runner

Provides a CLI runner that integrates with Click/Typer to create
command-line applications with command registration and execution.
"""

from __future__ import annotations

import asyncio
import sys
from typing import Any

try:
    import typer
    from typer import Context, Typer
    TYPER_AVAILABLE = True
except ImportError:
    typer = None
    Context = None
    Typer = None
    TYPER_AVAILABLE = False

try:
    import click
    CLICK_AVAILABLE = True
except ImportError:
    click = None
    CLICK_AVAILABLE = False

from rich.console import Console

from .command import Command, CommandConfig, CommandError


class CLIRunner:
    """
    CLI application runner supporting multiple CLI frameworks.

    Supports:
    - Typer (recommended for modern CLIs)
    - Click (for compatibility)

    Example:
        from pheno.cli import CLIRunner, Command, CommandConfig

        class HelloCommand(Command):
            async def execute(self, args: Dict[str, Any]) -> Any:
                return f"Hello {args['name']}!"

            def format_output(self, result: Any) -> str:
                return result

        runner = CLIRunner("myapp", "My CLI Application")
        runner.register_command("hello", HelloCommand, {
            "name": {"type": str, "required": True}
        })
        runner.run()
    """

    def __init__(
        self,
        app_name: str,
        description: str = "",
        version: str = "1.0.0",
        framework: str = "typer",
    ) -> None:
        """
        Initialize CLI runner.

        Args:
            app_name: Application name
            description: Application description
            version: Application version
            framework: CLI framework to use ("typer" or "click")

        Raises:
            ImportError: If specified framework is not available
        """
        self.app_name = app_name
        self.description = description
        self.version = version
        self.framework = framework
        self.console = Console()

        # Command registry: name -> (command_class, arg_specs)
        self.commands: dict[str, tuple[type[Command], dict[str, Any]]] = {}

        # CLI app instance
        self.app: Any | None = None

        # Validate framework availability
        if framework == "typer" and not TYPER_AVAILABLE:
            raise ImportError("Typer is not installed. Install with: pip install typer")
        if framework == "click" and not CLICK_AVAILABLE:
            raise ImportError("Click is not installed. Install with: pip install click")

    def register_command(
        self,
        name: str,
        command_class: type[Command],
        arg_specs: dict[str, Any] | None = None,
        help_text: str | None = None,
    ) -> None:
        """
        Register a command with the CLI runner.

        Args:
            name: Command name
            command_class: Command class (subclass of Command)
            arg_specs: Argument specifications
            help_text: Help text for the command

        Example:
            runner.register_command("create", CreateCommand, {
                "entity_type": {"type": str, "required": True},
                "data": {"type": str, "required": True}
            })
        """
        self.commands[name] = (command_class, arg_specs or {}, help_text or "")

    def _create_typer_app(self) -> Typer:
        """
        Create Typer CLI application.

        Returns:
            Typer app instance
        """
        if not TYPER_AVAILABLE:
            raise ImportError("Typer is not available")

        app = typer.Typer(
            name=self.app_name,
            help=self.description,
            add_completion=True,
            rich_markup_mode="rich",
        )

        # Add version callback
        @app.callback(invoke_without_command=True)
        def main_callback(
            ctx: Context,
            version: bool = typer.Option(False, "--version", "-v", help="Show version"),
            verbose: bool = typer.Option(False, "--verbose", help="Verbose output"),
        ) -> None:
            """Main callback to handle global options."""
            if version:
                self.console.print(f"[bold cyan]{self.app_name}[/bold cyan] version [bold]{self.version}[/bold]")
                raise typer.Exit

            # Store global options in context
            ctx.ensure_object(dict)
            ctx.obj["verbose"] = verbose

        # Register commands
        for cmd_name, (cmd_class, arg_specs, help_text) in self.commands.items():
            self._add_typer_command(app, cmd_name, cmd_class, arg_specs, help_text)

        return app

    def _add_typer_command(
        self,
        app: Typer,
        name: str,
        command_class: type[Command],
        arg_specs: dict[str, Any],
        help_text: str,
    ) -> None:
        """
        Add a command to Typer app.

        Args:
            app: Typer app instance
            name: Command name
            command_class: Command class
            arg_specs: Argument specifications
            help_text: Help text
        """
        # Create command function dynamically
        def cmd_func(**kwargs: Any) -> None:
            """Command function wrapper."""
            # Extract global options
            ctx = kwargs.pop("ctx", None)
            verbose = False
            if ctx and hasattr(ctx, "obj") and ctx.obj:
                verbose = ctx.obj.get("verbose", False)

            json_output = kwargs.pop("json", False)

            # Create config
            config = CommandConfig(verbose=verbose, json_output=json_output)

            # Instantiate command
            try:
                command = command_class(config)
            except Exception as e:
                self.console.print(f"[bold red]Error initializing command:[/bold red] {e!s}")
                raise typer.Exit(1)

            # Execute command
            try:
                output = asyncio.run(command.run(kwargs))
                self.console.print(output)
            except CommandError as e:
                self.console.print(f"[bold red]Error:[/bold red] {e.message}")
                raise typer.Exit(e.code)
            except Exception as e:
                self.console.print(f"[bold red]Unexpected error:[/bold red] {e!s}")
                if verbose:
                    import traceback
                    traceback.print_exc()
                raise typer.Exit(1)

        # Build function signature from arg_specs
        # Note: This is a simplified version - full implementation would use
        # inspect.Parameter to build proper signatures
        cmd_func.__name__ = name
        cmd_func.__doc__ = help_text

        # Register with typer
        app.command(name=name, help=help_text)(cmd_func)

    def _create_click_app(self) -> click.Group:
        """
        Create Click CLI application.

        Returns:
            Click group instance
        """
        if not CLICK_AVAILABLE:
            raise ImportError("Click is not available")

        @click.group(help=self.description)
        @click.option("--version", is_flag=True, help="Show version")
        @click.option("--verbose", is_flag=True, help="Verbose output")
        @click.pass_context
        def cli(ctx: click.Context, version: bool, verbose: bool) -> None:
            """Main CLI group."""
            if version:
                self.console.print(f"{self.app_name} version {self.version}")
                sys.exit(0)

            ctx.ensure_object(dict)
            ctx.obj["verbose"] = verbose

        # Register commands
        for cmd_name, (cmd_class, arg_specs, help_text) in self.commands.items():
            self._add_click_command(cli, cmd_name, cmd_class, arg_specs, help_text)

        return cli

    def _add_click_command(
        self,
        group: click.Group,
        name: str,
        command_class: type[Command],
        arg_specs: dict[str, Any],
        help_text: str,
    ) -> None:
        """
        Add a command to Click group.

        Args:
            group: Click group
            name: Command name
            command_class: Command class
            arg_specs: Argument specifications
            help_text: Help text
        """
        @click.command(name=name, help=help_text)
        @click.pass_context
        def cmd_func(ctx: click.Context, **kwargs: Any) -> None:
            """Command function wrapper."""
            verbose = ctx.obj.get("verbose", False)
            json_output = kwargs.pop("json", False)

            config = CommandConfig(verbose=verbose, json_output=json_output)

            try:
                command = command_class(config)
                output = asyncio.run(command.run(kwargs))
                self.console.print(output)
            except CommandError as e:
                self.console.print(f"[bold red]Error:[/bold red] {e.message}")
                sys.exit(e.code)
            except Exception as e:
                self.console.print(f"[bold red]Unexpected error:[/bold red] {e!s}")
                if verbose:
                    import traceback
                    traceback.print_exc()
                sys.exit(1)

        group.add_command(cmd_func)

    def create_app(self) -> Any:
        """
        Create CLI application based on configured framework.

        Returns:
            CLI app instance (Typer or Click)
        """
        if self.framework == "typer":
            return self._create_typer_app()
        if self.framework == "click":
            return self._create_click_app()
        raise ValueError(f"Unknown framework: {self.framework}")

    def run(self, args: list[str] | None = None) -> None:
        """
        Run the CLI application.

        Args:
            args: Command-line arguments (defaults to sys.argv[1:])
        """
        if self.app is None:
            self.app = self.create_app()

        try:
            if self.framework == "typer":
                self.app(args or sys.argv[1:])
            elif self.framework == "click":
                self.app(args or sys.argv[1:], standalone_mode=False)
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Operation cancelled by user[/yellow]")
            sys.exit(0)
        except SystemExit:
            # Re-raise SystemExit
            raise
        except Exception as e:
            self.console.print(f"[bold red]Fatal error:[/bold red] {e!s}")
            sys.exit(1)


__all__ = ["CLIRunner"]
