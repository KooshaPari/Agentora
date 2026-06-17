"""
CLI Adapters for different CLI frameworks Provides adapters for Rich, Click, and
Argparse CLI frameworks.
"""

import argparse
from abc import ABC, abstractmethod
from typing import Any

try:
    import click

    CLICK_AVAILABLE = True
except ImportError:
    CLICK_AVAILABLE = False

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from .registry import CLICommand, CommandRegistry, ProjectType


class CLIAdapter(ABC):
    """
    Abstract base class for CLI adapters.
    """

    def __init__(self, registry: CommandRegistry):
        self.registry = registry

    @abstractmethod
    def create_cli(self, project_type: ProjectType, commands: list[CLICommand]) -> Any:
        """
        Create CLI instance for the adapter.
        """

    @abstractmethod
    def add_command(self, cli: Any, command: CLICommand) -> None:
        """
        Add command to CLI instance.
        """

    @abstractmethod
    def run_cli(self, cli: Any, args: list[str]) -> int:
        """
        Run CLI with arguments.
        """


class RichCLIAdapter(CLIAdapter):
    """
    Rich CLI adapter for enhanced terminal output.
    """

    def __init__(self, registry: CommandRegistry):
        super().__init__(registry)
        if not RICH_AVAILABLE:
            raise ImportError("Rich library not available. Install with: pip install rich")
        self.console = Console()

    def create_cli(self, project_type: ProjectType, commands: list[CLICommand]) -> "RichCLI":
        """
        Create Rich CLI instance.
        """
        return RichCLI(project_type.value, commands, self.console)

    def add_command(self, cli: "RichCLI", command: CLICommand) -> None:
        """
        Add command to Rich CLI.
        """
        cli.add_command(command)

    def run_cli(self, cli: "RichCLI", args: list[str]) -> int:
        """
        Run Rich CLI with arguments.
        """
        return cli.run(args)


class ClickCLIAdapter(CLIAdapter):
    """
    Click CLI adapter.
    """

    def __init__(self, registry: CommandRegistry):
        super().__init__(registry)
        if not CLICK_AVAILABLE:
            raise ImportError("Click library not available. Install with: pip install click")

    def create_cli(self, project_type: ProjectType, commands: list[CLICommand]) -> click.Group:
        """
        Create Click CLI instance.
        """
        cli = click.Group(name=project_type.value, help=f"{project_type.value} CLI")

        for command in commands:
            self.add_command(cli, command)

        return cli

    def add_command(self, cli: click.Group, command: CLICommand) -> None:
        """
        Add command to Click CLI.
        """

        def command_wrapper(**kwargs):
            # Convert Click context to args-like object
            class Args:
                def __init__(self, **kwargs):
                    for key, value in kwargs.items():
                        setattr(self, key, value)

            args = Args(**kwargs)
            return command.handler(args)

        # Create Click command
        click_command = click.Command(
            name=command.name, help=command.description, callback=command_wrapper,
        )

        # Add options
        for option in command.options:
            click_command.params.append(
                click.Option(
                    [f"--{option['name']}"],
                    help=option.get("help", ""),
                    type=option.get("type", str),
                    default=option.get("default"),
                    is_flag=option.get("flag", False),
                ),
            )

        # Add arguments
        for arg in command.arguments:
            click_command.params.append(
                click.Argument([arg["name"]], help=arg.get("help", ""), type=arg.get("type", str)),
            )

        cli.add_command(click_command)

    def run_cli(self, cli: click.Group, args: list[str]) -> int:
        """
        Run Click CLI with arguments.
        """
        try:
            cli(args)
            return 0
        except SystemExit as e:
            return e.code
        except Exception as e:
            print(f"Error: {e}")
            return 1


class ArgparseCLIAdapter(CLIAdapter):
    """
    Argparse CLI adapter.
    """

    def create_cli(
        self, project_type: ProjectType, commands: list[CLICommand],
    ) -> argparse.ArgumentParser:
        """
        Create Argparse CLI instance.
        """
        parser = argparse.ArgumentParser(
            prog=project_type.value, description=f"{project_type.value} CLI",
        )

        subparsers = parser.add_subparsers(dest="command", help="Available commands")

        for command in commands:
            self.add_command(subparsers, command)

        return parser

    def add_command(self, subparsers: argparse._SubParsersAction, command: CLICommand) -> None:
        """
        Add command to Argparse CLI.
        """
        cmd_parser = subparsers.add_parser(command.name, help=command.description)

        # Add options
        for option in command.options:
            if option.get("flag", False):
                cmd_parser.add_argument(
                    f"--{option['name']}", action="store_true", help=option.get("help", ""),
                )
            else:
                cmd_parser.add_argument(
                    f"--{option['name']}",
                    type=option.get("type", str),
                    default=option.get("default"),
                    help=option.get("help", ""),
                )

        # Add arguments
        for arg in command.arguments:
            cmd_parser.add_argument(
                arg["name"], help=arg.get("help", ""), type=arg.get("type", str),
            )

    def run_cli(self, cli: argparse.ArgumentParser, args: list[str]) -> int:
        """
        Run Argparse CLI with arguments.
        """
        try:
            parsed_args = cli.parse_args(args)

            if not parsed_args.command:
                cli.print_help()
                return 0

            # Find and execute command
            command = self.registry.get_command(parsed_args.command)
            if command:
                return command.handler(parsed_args)
            print(f"Unknown command: {parsed_args.command}")
            return 1

        except SystemExit as e:
            return e.code
        except Exception as e:
            print(f"Error: {e}")
            return 1


class RichCLI:
    """
    Rich CLI implementation.
    """

    def __init__(self, name: str, commands: list[CLICommand], console: Console):
        self.name = name
        self.commands = {cmd.name: cmd for cmd in commands}
        self.console = console

    def add_command(self, command: CLICommand) -> None:
        """
        Add command to CLI.
        """
        self.commands[command.name] = command

    def run(self, args: list[str]) -> int:
        """
        Run CLI with arguments.
        """
        if not args:
            self.show_help()
            return 0

        command_name = args[0]
        command_args = args[1:]

        if command_name in ["help", "-h", "--help"]:
            self.show_help()
            return 0

        if command_name not in self.commands:
            self.console.print(f"[red]Unknown command: {command_name}[/red]")
            self.show_help()
            return 1

        command = self.commands[command_name]

        # Parse arguments (simplified)
        class Args:
            def __init__(self, args):
                self.args = args
                # Add common attributes
                self.detailed = "--detailed" in args
                self.json = "--json" in args
                self.verbose = "--verbose" in args or "-v" in args

        try:
            return command.handler(Args(command_args))
        except Exception as e:
            self.console.print(f"[red]Error executing {command_name}: {e}[/red]")
            return 1

    def show_help(self) -> None:
        """
        Show help information.
        """
        # Create help table
        table = Table(title=f"{self.name} CLI Commands")
        table.add_column("Command", style="cyan")
        table.add_column("Description", style="white")
        table.add_column("Category", style="green")

        # Group commands by category
        categories = {}
        for command in self.commands.values():
            if command.category.value not in categories:
                categories[command.category.value] = []
            categories[command.category.value].append(command)

        # Add commands to table
        for category, commands in categories.items():
            for command in commands:
                table.add_row(command.name, command.description, category)

        self.console.print(table)

        # Show usage
        self.console.print(f"\n[bold]Usage:[/bold] {self.name} <command> [options]")
        self.console.print("[bold]Examples:[/bold]")
        self.console.print(f"  {self.name} status")
        self.console.print(f"  {self.name} build --verbose")
        self.console.print(f"  {self.name} help")


def create_cli_adapter(framework: str, registry: CommandRegistry) -> CLIAdapter:
    """
    Create CLI adapter for specified framework.
    """
    if framework == "rich":
        return RichCLIAdapter(registry)
    if framework == "click":
        return ClickCLIAdapter(registry)
    if framework == "argparse":
        return ArgparseCLIAdapter(registry)
    raise ValueError(f"Unknown CLI framework: {framework}")


def get_available_frameworks() -> list[str]:
    """
    Get list of available CLI frameworks.
    """
    frameworks = ["argparse"]  # Always available

    if RICH_AVAILABLE:
        frameworks.append("rich")

    if CLICK_AVAILABLE:
        frameworks.append("click")

    return frameworks
