"""Decorator-based API for defining CLI commands.

Provides @cli_command and @cli_group decorators with automatic argument extraction from
function signatures using type hints.
"""

import inspect
from enum import Enum
from functools import wraps

# cli_builder is not available - using placeholder types
from typing import Any, Callable, Dict, List, Optional, get_args, get_origin, get_type_hints


class ArgumentType(Enum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    LIST = "list"


class Argument:
    def __init__(self, name: str, type: ArgumentType, help: str = "", required: bool = True):
        self.name = name
        self.type = type
        self.help = help
        self.required = required


class Option:
    def __init__(
        self,
        name: str,
        type: ArgumentType,
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
    def __init__(
        self,
        name: str,
        callback: Callable = None,
        help: str = "",
        arguments: List[Argument] = None,
        options: List[Option] = None,
        hidden: bool = False,
        deprecated: bool = False,
        **kwargs,
    ):
        self.name = name
        self.callback = callback
        self.help = help
        self.arguments = arguments or []
        self.options = options or []
        self.hidden = hidden
        self.deprecated = deprecated
        self.subcommands = []

    def add_subcommand(self, command: "Command"):
        self.subcommands.append(command)


def _python_type_to_argument_type(python_type: type) -> ArgumentType:
    """
    Convert Python type to ArgumentType.
    """
    # Handle Optional types
    origin = get_origin(python_type)
    if origin is type(None) or origin is Optional:
        args = get_args(python_type)
        if args:
            python_type = args[0]

    # Handle List types
    if origin is list or python_type is list:
        return ArgumentType.LIST

    # Map basic types
    type_map = {
        str: ArgumentType.STRING,
        int: ArgumentType.INTEGER,
        float: ArgumentType.FLOAT,
        bool: ArgumentType.BOOLEAN,
        list: ArgumentType.LIST,
    }

    return type_map.get(python_type, ArgumentType.STRING)


def _extract_params_from_signature(
    func: Callable[..., Any],
) -> tuple[List[Argument], List[Option]]:
    """Extract CLI arguments and options from function signature.

    Parameters with defaults become options, parameters without defaults
    become required arguments. Uses type hints to determine types.

    Args:
        func: Function to analyze

    Returns:
        Tuple of (arguments, options)
    """
    sig = inspect.signature(func)
    type_hints = get_type_hints(func)

    arguments: List[Argument] = []
    options: List[Option] = []

    for param_name, param in sig.parameters.items():
        # Get type from type hints
        param_type = type_hints.get(param_name, str)
        arg_type = _python_type_to_argument_type(param_type)

        # Get help from docstring if available
        help_text = ""
        if func.__doc__:
            # Simple extraction - look for "param_name: description" in docstring
            for line in func.__doc__.split("\n"):
                if param_name in line and ":" in line:
                    help_text = line.split(":", 1)[1].strip()
                    break

        if param.default is inspect.Parameter.empty:
            # No default = required argument
            arguments.append(
                Argument(
                    name=param_name,
                    type=arg_type,
                    help=help_text,
                    required=True,
                )
            )
        else:
            # Has default = optional flag/option
            is_flag = param_type is bool or arg_type == ArgumentType.BOOLEAN

            options.append(
                Option(
                    name=param_name,
                    type=arg_type,
                    help=help_text,
                    default=param.default,
                    is_flag=is_flag,
                )
            )

    return arguments, options


class CommandRegistry:
    """Registry for tracking commands defined with decorators.

    This allows building a CLI from decorated functions.
    """

    def __init__(self) -> None:
        self.commands: List[Command] = []
        self.groups: Dict[str, Command] = {}

    def register_command(self, command: Command) -> None:
        """
        Register a command.
        """
        self.commands.append(command)

    def register_group(self, name: str, command: Command) -> None:
        """
        Register a command group.
        """
        self.groups[name] = command
        self.commands.append(command)

    def get_group(self, name: str) -> Optional[Command]:
        """
        Get a command group by name.
        """
        return self.groups.get(name)


# Global registry for decorator-based commands
_default_registry = CommandRegistry()


def cli_command(
    name: Optional[str] = None,
    help: Optional[str] = None,
    group: Optional[str] = None,
    hidden: bool = False,
    deprecated: bool = False,
    **kwargs: Any,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to mark a function as a CLI command.

    Automatically extracts arguments and options from the function signature
    using type hints.

    Args:
        name: Command name (defaults to function name)
        help: Help text (defaults to function docstring)
        group: Parent command group name
        hidden: Hide command from help
        deprecated: Mark command as deprecated
        **kwargs: Additional command parameters

    Example:
        >>> @cli_command(name="greet", help="Greet a user")
        ... def greet_user(name: str, loud: bool = False):
        ...     message = f"Hello, {name}!"
        ...     if loud:
        ...         message = message.upper()
        ...     print(message)
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        # Get command name and help
        cmd_name = name or func.__name__.replace("_", "-")
        cmd_help = help or (func.__doc__ or "").split("\n")[0].strip()

        # Extract arguments and options from signature
        arguments, options = _extract_params_from_signature(func)

        # Create command
        command = Command(
            name=cmd_name,
            callback=func,
            help=cmd_help,
            arguments=arguments,
            options=options,
            hidden=hidden,
            deprecated=deprecated,
            **kwargs,
        )

        # Register with group or global registry
        if group:
            parent = _default_registry.get_group(group)
            if parent:
                parent.add_subcommand(command)
            else:
                # Create group if it doesn't exist
                group_cmd = Command(name=group, help=f"{group} commands")
                group_cmd.add_subcommand(command)
                _default_registry.register_group(group, group_cmd)
        else:
            _default_registry.register_command(command)

        # Mark function as CLI command
        func._cli_command = command  # type: ignore

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        return wrapper

    return decorator


def cli_group(
    name: Optional[str] = None,
    help: Optional[str] = None,
    **kwargs: Any,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to mark a function as a command group.

    A command group can contain subcommands.

    Args:
        name: Group name (defaults to function name)
        help: Help text (defaults to function docstring)
        **kwargs: Additional command parameters

    Example:
        >>> @cli_group(name="database", help="Database commands")
        ... def db():
        ...     pass
        ...
        >>> @cli_command(group="database", name="migrate")
        ... def db_migrate():
        ...     print("Running migrations...")
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        # Get group name and help
        grp_name = name or func.__name__.replace("_", "-")
        grp_help = help or (func.__doc__ or "").split("\n")[0].strip()

        # Create group command
        group_cmd = Command(
            name=grp_name,
            callback=func,
            help=grp_help,
            **kwargs,
        )

        # Register group
        _default_registry.register_group(grp_name, group_cmd)

        # Mark function as CLI group
        func._cli_group = group_cmd  # type: ignore

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        return wrapper

    return decorator


def get_registry() -> CommandRegistry:
    """
    Get the default command registry.
    """
    return _default_registry


def reset_registry() -> None:
    """
    Reset the default command registry (useful for testing).
    """
    global _default_registry
    _default_registry = CommandRegistry()


# Backward compatibility function
def argument(
    name: str, type: ArgumentType = ArgumentType.STRING, help: str = "", required: bool = True
) -> Argument:
    """
    Create an argument (backward compatibility function).
    """
    return Argument(name=name, type=type, help=help, required=required)


def command(
    name: str, description: str = "", arguments: list = None, options: list = None
) -> Command:
    """
    Create a command (backward compatibility function).
    """
    return Command(
        name=name, description=description, arguments=arguments or [], options=options or []
    )


def group(name: str, description: str = "", commands: list = None) -> Command:
    """
    Create a command group (backward compatibility function).
    """
    return Command(name=name, description=description, arguments=commands or [])


def option(
    name: str, type: ArgumentType = ArgumentType.STRING, help: str = "", required: bool = False
) -> Option:
    """
    Create an option (backward compatibility function).
    """
    return Option(name=name, type=type, help=help, required=required)
