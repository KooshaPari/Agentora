"""Command, Argument, and Option dataclasses for CLI components.

Provides type-safe definitions with validation rules and help text generation.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, List, Optional, Union


class ArgumentType(Enum):
    """
    Supported argument types across all backends.
    """

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    PATH = "path"
    FILE = "file"
    CHOICE = "choice"
    LIST = "list"


@dataclass
class Argument:
    """Represents a positional CLI argument.

    Attributes:
        name: Argument name (used in function signature)
        type: Data type of the argument
        help: Help text describing the argument
        required: Whether the argument is required
        default: Default value if not provided
        choices: Valid choices for the argument (for CHOICE type)
        nargs: Number of values (for LIST type: '+', '*', or integer)
        metavar: Display name in help text
    """

    name: str
    type: ArgumentType = ArgumentType.STRING
    help: str = ""
    required: bool = True
    default: Any = None
    choices: Optional[List[Any]] = None
    nargs: Optional[Union[int, str]] = None
    metavar: Optional[str] = None

    def __post_init__(self) -> None:
        """
        Validate argument configuration.
        """
        if self.type == ArgumentType.CHOICE and not self.choices:
            raise ValueError(f"Argument '{self.name}' with CHOICE type must have choices")

        if self.type == ArgumentType.LIST and not self.nargs:
            self.nargs = "*"

        if not self.required and self.default is None:
            raise ValueError(f"Optional argument '{self.name}' must have a default value")

    @property
    def python_type(self) -> type:
        """
        Get the Python type for this argument.
        """
        type_map = {
            ArgumentType.STRING: str,
            ArgumentType.INTEGER: int,
            ArgumentType.FLOAT: float,
            ArgumentType.BOOLEAN: bool,
            ArgumentType.PATH: str,
            ArgumentType.FILE: str,
            ArgumentType.CHOICE: str,
            ArgumentType.LIST: list,
        }
        return type_map[self.type]


@dataclass
class Option:
    """Represents a CLI option/flag.

    Attributes:
        name: Long option name (e.g., 'verbose')
        short: Short option flag (e.g., 'v')
        type: Data type of the option
        help: Help text describing the option
        required: Whether the option is required
        default: Default value if not provided
        is_flag: Whether this is a boolean flag
        flag_value: Value when flag is present (for is_flag=True)
        choices: Valid choices for the option
        multiple: Whether option can be specified multiple times
        envvar: Environment variable to read value from
        prompt: Prompt text for interactive input
        hide_input: Hide input when prompting (for passwords)
        confirmation_prompt: Ask for confirmation (for sensitive operations)
        metavar: Display name in help text
    """

    name: str
    short: Optional[str] = None
    type: ArgumentType = ArgumentType.STRING
    help: str = ""
    required: bool = False
    default: Any = None
    is_flag: bool = False
    flag_value: Any = True
    choices: Optional[List[Any]] = None
    multiple: bool = False
    envvar: Optional[str] = None
    prompt: Optional[str] = None
    hide_input: bool = False
    confirmation_prompt: bool = False
    metavar: Optional[str] = None

    def __post_init__(self) -> None:
        """
        Validate option configuration.
        """
        if self.is_flag:
            self.type = ArgumentType.BOOLEAN
            if self.default is None:
                self.default = False

        if self.type == ArgumentType.CHOICE and not self.choices:
            raise ValueError(f"Option '{self.name}' with CHOICE type must have choices")

        if self.short and len(self.short) > 1:
            raise ValueError(f"Short option must be a single character: '{self.short}'")

    @property
    def python_type(self) -> type:
        """
        Get the Python type for this option.
        """
        if self.multiple:
            return list

        type_map = {
            ArgumentType.STRING: str,
            ArgumentType.INTEGER: int,
            ArgumentType.FLOAT: float,
            ArgumentType.BOOLEAN: bool,
            ArgumentType.PATH: str,
            ArgumentType.FILE: str,
            ArgumentType.CHOICE: str,
            ArgumentType.LIST: list,
        }
        return type_map[self.type]

    @property
    def option_strings(self) -> List[str]:
        """
        Generate option strings for CLI (e.g., ['-v', '--verbose']).
        """
        strings = []
        if self.short:
            strings.append(f"-{self.short}")
        strings.append(f"--{self.name.replace('_', '-')}")
        return strings


@dataclass
class Command:
    """Represents a CLI command or subcommand.

    Attributes:
        name: Command name
        callback: Function to execute when command is invoked
        help: Help text describing the command
        arguments: List of positional arguments
        options: List of options/flags
        subcommands: Nested subcommands
        hidden: Whether to hide command from help
        deprecated: Whether command is deprecated
        epilog: Additional help text shown after options
        short_help: Short help text for command listings
    """

    name: str
    callback: Optional[Callable[..., Any]] = None
    help: str = ""
    arguments: List[Argument] = field(default_factory=list)
    options: List[Option] = field(default_factory=list)
    subcommands: List["Command"] = field(default_factory=list)
    hidden: bool = False
    deprecated: bool = False
    epilog: Optional[str] = None
    short_help: Optional[str] = None

    def add_argument(self, argument: Argument) -> "Command":
        """
        Add an argument to this command.
        """
        self.arguments.append(argument)
        return self

    def add_option(self, option: Option) -> "Command":
        """
        Add an option to this command.
        """
        self.options.append(option)
        return self

    def add_subcommand(self, command: "Command") -> "Command":
        """
        Add a subcommand to this command.
        """
        self.subcommands.append(command)
        return self

    def validate(self) -> None:
        """
        Validate command configuration.
        """
        # Check for duplicate argument names
        arg_names = [arg.name for arg in self.arguments]
        if len(arg_names) != len(set(arg_names)):
            raise ValueError(f"Duplicate argument names in command '{self.name}'")

        # Check for duplicate option names
        opt_names = [opt.name for opt in self.options]
        if len(opt_names) != len(set(opt_names)):
            raise ValueError(f"Duplicate option names in command '{self.name}'")

        # Check for required arguments after optional ones
        seen_optional = False
        for arg in self.arguments:
            if not arg.required:
                seen_optional = True
            elif seen_optional:
                raise ValueError(
                    f"Required argument '{arg.name}' cannot come after optional arguments"
                )

        # Validate all arguments and options
        for arg in self.arguments:
            arg.__post_init__()

        for opt in self.options:
            opt.__post_init__()

        # Validate subcommands recursively
        for subcmd in self.subcommands:
            subcmd.validate()


# Aliases for backward compatibility
ArgumentDefinition = Argument
CommandDefinition = Command
