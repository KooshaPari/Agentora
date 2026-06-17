"""
Generic CLI Command Base Class

Provides a base class for building CLI commands with configuration support,
execution lifecycle, and output formatting.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Any

from rich.console import Console


class CommandConfig:
    """Configuration for CLI commands."""

    def __init__(
        self,
        verbose: bool = False,
        json_output: bool = False,
        config_path: str | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize command configuration.

        Args:
            verbose: Enable verbose output
            json_output: Output as JSON format
            config_path: Path to configuration file
            **kwargs: Additional configuration options
        """
        self.verbose = verbose
        self.json_output = json_output
        self.config_path = config_path
        self.extra = kwargs


class Command(ABC):
    """
    Base class for CLI commands.

    Commands should:
    1. Accept configuration via __init__
    2. Implement execute() to perform the command action
    3. Implement format_output() to format results for display
    4. Optionally override validate() to validate arguments

    Example:
        class CreateEntityCommand(Command):
            def __init__(self, config: CommandConfig, database_adapter):
                super().__init__(config)
                self.database = database_adapter

            async def execute(self, args: Dict[str, Any]) -> Any:
                entity_type = args["entity_type"]
                data = args["data"]
                return await self.database.create_entity(entity_type, data)

            def format_output(self, result: Any) -> str:
                if self.config.json_output:
                    return json.dumps(result)
                return f"Created entity: {result.id}"
    """

    def __init__(self, config: CommandConfig) -> None:
        """
        Initialize command with configuration.

        Args:
            config: Command configuration
        """
        self.config = config
        self.console = Console()

    @abstractmethod
    async def execute(self, args: dict[str, Any]) -> Any:
        """
        Execute the command with given arguments.

        Args:
            args: Command arguments as dictionary

        Returns:
            Command result (any type)

        Raises:
            CommandError: If command execution fails
        """

    @abstractmethod
    def format_output(self, result: Any) -> str:
        """
        Format command result for output.

        Args:
            result: Command execution result

        Returns:
            Formatted output string
        """

    def validate(self, args: dict[str, Any]) -> None:
        """
        Validate command arguments before execution.

        Args:
            args: Command arguments to validate

        Raises:
            ValueError: If arguments are invalid
        """

    async def run(self, args: dict[str, Any]) -> str:
        """
        Complete command lifecycle: validate, execute, format.

        Args:
            args: Command arguments

        Returns:
            Formatted output string

        Raises:
            ValueError: If validation fails
            CommandError: If execution fails
        """
        # Validate arguments
        self.validate(args)

        # Execute command
        result = await self.execute(args)

        # Format output
        return self.format_output(result)

    def log_verbose(self, message: str) -> None:
        """
        Log verbose message if verbose mode is enabled.

        Args:
            message: Message to log
        """
        if self.config.verbose:
            self.console.print(f"[dim]{message}[/dim]")

    def log_error(self, message: str) -> None:
        """
        Log error message.

        Args:
            message: Error message to log
        """
        self.console.print(f"[bold red]Error:[/bold red] {message}")

    def log_success(self, message: str) -> None:
        """
        Log success message.

        Args:
            message: Success message to log
        """
        self.console.print(f"[bold green]{message}[/bold green]")

    def log_info(self, message: str) -> None:
        """
        Log informational message.

        Args:
            message: Info message to log
        """
        self.console.print(f"[cyan]{message}[/cyan]")


class SyncCommand(Command):
    """
    Synchronous command wrapper for commands that don't need async.

    Example:
        class ListFilesCommand(SyncCommand):
            def execute_sync(self, args: Dict[str, Any]) -> Any:
                return os.listdir(args["path"])

            def format_output(self, result: Any) -> str:
                return "\\n".join(result)
    """

    async def execute(self, args: dict[str, Any]) -> Any:
        """
        Execute synchronous command in async context.

        Args:
            args: Command arguments

        Returns:
            Command result
        """
        return await asyncio.to_thread(self.execute_sync, args)

    @abstractmethod
    def execute_sync(self, args: dict[str, Any]) -> Any:
        """
        Execute command synchronously.

        Args:
            args: Command arguments

        Returns:
            Command result
        """


class CommandError(Exception):
    """Exception raised when command execution fails."""

    def __init__(self, message: str, code: int = 1) -> None:
        """
        Initialize command error.

        Args:
            message: Error message
            code: Exit code (default: 1)
        """
        super().__init__(message)
        self.message = message
        self.code = code


__all__ = [
    "Command",
    "CommandConfig",
    "CommandError",
    "SyncCommand",
]
