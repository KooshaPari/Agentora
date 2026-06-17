"""Main CLIBuilder class for building CLI applications.

Provides a unified interface for creating CLIs that can target multiple backends.
"""

from typing import Any, Dict, List, Optional

from ...cli_builder.core.command import Argument, ArgumentType, Command, Option


class CLIBuilder:
    """Main builder class for creating CLI applications.

    Supports generating code for argparse, Click, and Typer backends.

    Example:
        >>> builder = CLIBuilder("myapp", version="1.0.0")
        >>> builder.add_command(
        ...     Command(name="hello", callback=hello_func, help="Say hello")
        ... )
        >>> code = builder.generate(backend="click")
    """

    def __init__(
        self,
        name: str,
        version: str = "0.1.0",
        help: str = "",
        epilog: Optional[str] = None,
    ):
        """Initialize CLI builder.

        Args:
            name: Application name
            version: Application version
            help: Application help text
            epilog: Additional help text shown after commands
        """
        self.name = name
        self.version = version
        self.help = help
        self.epilog = epilog
        self.commands: List[Command] = []
        self._global_options: List[Option] = []

    def add_command(
        self,
        command: Command,
    ) -> "CLIBuilder":
        """Add a command to the CLI.

        Args:
            command: Command to add

        Returns:
            Self for method chaining
        """
        command.validate()
        self.commands.append(command)
        return self

    def add_argument(
        self,
        name: str,
        type: ArgumentType = ArgumentType.STRING,
        help: str = "",
        **kwargs: Any,
    ) -> "CLIBuilder":
        """Add a positional argument to the CLI (for single-command apps).

        Args:
            name: Argument name
            type: Argument type
            help: Help text
            **kwargs: Additional argument parameters

        Returns:
            Self for method chaining
        """
        if not self.commands:
            # Create default command for single-command CLI
            self.commands.append(Command(name=self.name, help=self.help or f"{self.name} CLI"))

        argument = Argument(name=name, type=type, help=help, **kwargs)
        self.commands[0].add_argument(argument)
        return self

    def add_option(
        self,
        name: str,
        short: Optional[str] = None,
        type: ArgumentType = ArgumentType.STRING,
        help: str = "",
        **kwargs: Any,
    ) -> "CLIBuilder":
        """Add an option/flag to the CLI.

        Args:
            name: Option name
            short: Short flag (single character)
            type: Option type
            help: Help text
            **kwargs: Additional option parameters

        Returns:
            Self for method chaining
        """
        option = Option(name=name, short=short, type=type, help=help, **kwargs)

        if not self.commands:
            # Create default command for single-command CLI
            self.commands.append(Command(name=self.name, help=self.help or f"{self.name} CLI"))

        self.commands[0].add_option(option)
        return self

    def add_global_option(
        self,
        name: str,
        short: Optional[str] = None,
        type: ArgumentType = ArgumentType.STRING,
        help: str = "",
        **kwargs: Any,
    ) -> "CLIBuilder":
        """Add a global option available to all commands.

        Args:
            name: Option name
            short: Short flag (single character)
            type: Option type
            help: Help text
            **kwargs: Additional option parameters

        Returns:
            Self for method chaining
        """
        option = Option(name=name, short=short, type=type, help=help, **kwargs)
        self._global_options.append(option)
        return self

    def generate(
        self,
        backend: str = "click",
        output_file: Optional[str] = None,
        standalone: bool = True,
    ) -> str:
        """Generate CLI code for the specified backend.

        Args:
            backend: Target backend ('argparse', 'click', or 'typer')
            output_file: Optional file path to write generated code
            standalone: Whether to generate a standalone executable script

        Returns:
            Generated Python code as a string

        Raises:
            ValueError: If backend is not supported
        """
        from cli_builder.backends.registry import BackendRegistry

        registry = BackendRegistry()
        backend_instance = registry.get_backend(backend)

        if not backend_instance:
            raise ValueError(
                f"Backend '{backend}' not supported. "
                f"Available: {', '.join(registry.list_backends())}"
            )

        # Pass global options to backend
        code = backend_instance.generate(
            cli_name=self.name,
            version=self.version,
            help=self.help,
            commands=self.commands,
            global_options=self._global_options,
            epilog=self.epilog,
            standalone=standalone,
        )

        if output_file:
            with open(output_file, "w") as f:
                f.write(code)

        return code

    def validate(self) -> None:
        """
        Validate the entire CLI configuration.
        """
        if not self.commands:
            raise ValueError("CLI must have at least one command")

        # Check for duplicate command names
        cmd_names = [cmd.name for cmd in self.commands]
        if len(cmd_names) != len(set(cmd_names)):
            raise ValueError("Duplicate command names detected")

        # Validate all commands
        for cmd in self.commands:
            cmd.validate()

        # Validate global options
        for opt in self._global_options:
            opt.__post_init__()

    def get_structure(self) -> Dict[str, Any]:
        """Get a structured representation of the CLI.

        Returns:
            Dictionary containing CLI structure
        """

        def command_to_dict(cmd: Command) -> Dict[str, Any]:
            return {
                "name": cmd.name,
                "help": cmd.help,
                "arguments": [
                    {"name": arg.name, "type": arg.type.value, "required": arg.required}
                    for arg in cmd.arguments
                ],
                "options": [
                    {
                        "name": opt.name,
                        "short": opt.short,
                        "type": opt.type.value,
                        "required": opt.required,
                    }
                    for opt in cmd.options
                ],
                "subcommands": [command_to_dict(sub) for sub in cmd.subcommands],
            }

        return {
            "name": self.name,
            "version": self.version,
            "help": self.help,
            "commands": [command_to_dict(cmd) for cmd in self.commands],
            "global_options": [
                {
                    "name": opt.name,
                    "short": opt.short,
                    "type": opt.type.value,
                }
                for opt in self._global_options
            ],
        }
