"""Core command definitions for CLI Builder."""

from enum import Enum
from typing import Any


class ArgumentType(Enum):
    """Types of command line arguments."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    LIST = "list"


class Argument:
    """Command line argument definition."""

    def __init__(
        self,
        name: str,
        type: ArgumentType = ArgumentType.STRING,
        help: str = "",
        required: bool = True,
        default: Any = None,
    ):
        self.name = name
        self.type = type
        self.help = help
        self.required = required
        self.default = default


class Option:
    """Command line option definition."""

    def __init__(
        self,
        name: str,
        type: ArgumentType = ArgumentType.STRING,
        help: str = "",
        default: Any = None,
        is_flag: bool = False,
    ):
        self.name = name
        self.type = type
        self.help = help
        self.default = default
        self.is_flag = is_flag


class Command:
    """Command definition for CLI applications."""

    def __init__(
        self,
        name: str,
        description: str = "",
        arguments: list[Argument] | None = None,
        options: list[Option] | None = None,
        subcommands: list["Command"] | None = None,
    ):
        self.name = name
        self.description = description
        self.arguments = arguments or []
        self.options = options or []
        self.subcommands = subcommands or []

    def add_argument(self, argument: Argument) -> None:
        """Add an argument to the command."""
        self.arguments.append(argument)

    def add_option(self, option: Option) -> None:
        """Add an option to the command."""
        self.options.append(option)

    def add_subcommand(self, command: "Command") -> None:
        """Add a subcommand to the command."""
        self.subcommands.append(command)


__all__ = [
    "Argument",
    "ArgumentType",
    "Command",
    "Option",
]
