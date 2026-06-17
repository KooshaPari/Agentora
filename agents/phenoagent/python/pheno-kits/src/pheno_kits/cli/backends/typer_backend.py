"""Typer backend generator.

Generates CLI code using the Typer framework with type hints.
"""

from typing import List, Optional

from .registry import BaseBackend
from ...cli_builder.core.command import Argument, ArgumentType, Command, Option


class TyperBackend(BaseBackend):
    """
    Backend for generating Typer-based CLIs.
    """

    def generate(
        self,
        cli_name: str,
        version: str,
        help: str,
        commands: List[Command],
        global_options: List[Option],
        epilog: Optional[str] = None,
        standalone: bool = True,
    ) -> str:
        """
        Generate Typer CLI code.
        """
        code = self._generate_header(cli_name, version, standalone)
        code += self._generate_imports()
        code += "\n\n"

        # Include original callback functions
        code += self._generate_callback_functions(commands)
        code += "\n\n"

        # Create Typer app
        code += self._generate_app_initialization(cli_name, help, epilog)
        code += "\n\n"

        if self._is_single_command(commands):
            # Single command CLI
            cmd = commands[0]
            code += self._generate_single_command(cmd, global_options)
        else:
            # Multi-command CLI
            code += self._generate_multi_command(commands, global_options)

        # Version callback
        code += "\n\n"
        code += self._generate_version_callback(cli_name, version)

        # Generate entry point
        if standalone:
            code += "\n\nif __name__ == '__main__':\n"
            code += "    app()\n"

        return code

    def _generate_imports(self) -> str:
        """
        Generate import statements.
        """
        return "import typer\nfrom typing import Optional, List, Annotated"

    def _generate_callback_functions(self, commands: List[Command]) -> str:
        """
        Include original callback function implementations.
        """
        code = "# Command implementation functions\n"
        seen_functions = set()

        def add_callback(cmd: Command) -> None:
            if cmd.callback and cmd.callback.__name__ not in seen_functions:
                seen_functions.add(cmd.callback.__name__)
                # Use the base class helper to get clean source
                source = self._get_function_source(cmd.callback)
                code_lines.append(source)
                code_lines.append("\n")

            # Process subcommands
            for subcmd in cmd.subcommands:
                add_callback(subcmd)

        code_lines = [code]
        for cmd in commands:
            add_callback(cmd)

        return "".join(code_lines)

    def _generate_app_initialization(self, cli_name: str, help: str, epilog: Optional[str]) -> str:
        """
        Generate Typer app initialization.
        """
        code = "app = typer.Typer(\n"
        code += f'    name="{cli_name}",\n'
        code += f'    help="{help}",\n'

        if epilog:
            code += f'    epilog="{epilog}",\n'

        code += "    add_completion=True,\n"
        code += ")\n"
        return code

    def _generate_single_command(
        self,
        cmd: Command,
        global_options: List[Option],
    ) -> str:
        """
        Generate code for single-command CLI.
        """
        code = "@app.command()\n"

        # Function definition with type hints
        code += self._generate_function_signature(cmd, global_options)
        code += ":\n"

        # Function body
        if cmd.help:
            code += f'    """{cmd.help}"""\n'

        if cmd.callback:
            params = []
            for arg in cmd.arguments:
                params.append(arg.name)
            for opt in cmd.options:
                params.append(opt.name)
            for opt in global_options:
                params.append(opt.name)

            code += f"    return {cmd.callback.__name__}({', '.join(params)})\n"
        else:
            code += f'    typer.echo("Executing {cmd.name}")\n'

        return code

    def _generate_multi_command(
        self,
        commands: List[Command],
        global_options: List[Option],
    ) -> str:
        """
        Generate code for multi-command CLI.
        """
        code = ""

        # Generate callback for global options if any
        if global_options:
            code += "@app.callback()\n"
            code += "def main(\n"

            for opt in global_options:
                code += self._generate_parameter(opt, is_option=True)
                code += ",\n"

            code += "):\n"
            code += '    """Main CLI with global options."""\n'
            code += "    pass\n\n\n"

        # Generate commands
        for cmd in commands:
            code += self._generate_command(cmd)
            code += "\n\n"

        return code

    def _generate_command(self, cmd: Command, parent: str = "app") -> str:
        """
        Generate a command or subcommand.
        """
        # If command has subcommands, create a sub-app
        if cmd.subcommands:
            code = f'{cmd.name.replace("-", "_")}_app = typer.Typer(\n'
            code += f'    name="{cmd.name}",\n'
            code += f'    help="{cmd.help}",\n'
            code += ")\n"
            code += f'{parent}.add_typer({cmd.name.replace("-", "_")}_app)\n\n'

            # Generate subcommands
            for subcmd in cmd.subcommands:
                code += self._generate_command(subcmd, f'{cmd.name.replace("-", "_")}_app')
                code += "\n\n"

            return code

        # Regular command
        code = f'@{parent}.command(name="{cmd.name}"'

        if cmd.hidden:
            code += ", hidden=True"

        if cmd.deprecated:
            code += ", deprecated=True"

        code += ")\n"

        # Function definition with type hints
        code += self._generate_function_signature(cmd)
        code += ":\n"

        # Function docstring
        if cmd.help:
            code += f'    """{cmd.help}\n'
            if cmd.epilog:
                code += f"\n    {cmd.epilog}\n"
            code += '    """\n'

        # Function body
        if cmd.callback:
            params = []
            for arg in cmd.arguments:
                params.append(arg.name)
            for opt in cmd.options:
                params.append(opt.name)

            code += f"    return {cmd.callback.__name__}({', '.join(params)})\n"
        else:
            code += f'    typer.echo("Executing {cmd.name}")\n'

        return code

    def _generate_function_signature(
        self,
        cmd: Command,
        global_options: Optional[List[Option]] = None,
    ) -> str:
        """
        Generate function signature with type hints.
        """
        func_name = cmd.name.replace("-", "_")
        code = f"def {func_name}(\n"

        # Add arguments
        for arg in cmd.arguments:
            code += "    "
            code += self._generate_parameter(arg, is_option=False)
            code += ",\n"

        # Add options
        for opt in cmd.options:
            code += "    "
            code += self._generate_parameter(opt, is_option=True)
            code += ",\n"

        # Add global options if provided
        if global_options:
            for opt in global_options:
                code += "    "
                code += self._generate_parameter(opt, is_option=True)
                code += ",\n"

        code += ")"
        return code

    def _generate_parameter(self, param: Argument | Option, is_option: bool) -> str:
        """
        Generate a single parameter with Typer annotations.
        """
        param_name = param.name

        # Determine Python type
        python_type = self._get_python_type(param)

        # Make optional if has default
        if not param.required or (hasattr(param, "default") and param.default is not None):
            python_type = f"Optional[{python_type}]"

        code = f"{param_name}: Annotated[{python_type}, "

        if is_option:
            # This is an option
            opt = param  # type: ignore
            if opt.is_flag:
                # Boolean flag
                code += f'typer.Option(False, "--{opt.name.replace("_", "-")}"'
                if opt.short:
                    code += f', "-{opt.short}"'
                if opt.help:
                    code += f', help="{opt.help}"'
                code += ")"
            else:
                # Regular option
                code += "typer.Option("
                if opt.default is not None:
                    code += repr(opt.default)
                else:
                    code += "..."

                code += f', "--{opt.name.replace("_", "-")}"'
                if opt.short:
                    code += f', "-{opt.short}"'
                if opt.help:
                    code += f', help="{opt.help}"'

                if opt.prompt:
                    code += f', prompt="{opt.prompt}"'

                if opt.hide_input:
                    code += ", hide_input=True"

                if opt.confirmation_prompt:
                    code += ", confirmation_prompt=True"

                if opt.envvar:
                    code += f', envvar="{opt.envvar}"'

                code += ")"
        else:
            # This is an argument
            arg = param  # type: ignore
            code += "typer.Argument("

            if not arg.required and arg.default is not None:
                code += repr(arg.default)
            else:
                code += "..."

            if arg.help:
                code += f', help="{arg.help}"'

            if arg.metavar:
                code += f', metavar="{arg.metavar}"'

            code += ")"

        code += "]"

        # Add default value
        if not param.required and param.default is not None:
            code += f" = {repr(param.default)}"

        return code

    def _get_python_type(self, param: Argument | Option) -> str:
        """
        Get Python type string for parameter.
        """
        if isinstance(param, Option) and param.multiple:
            return "List[str]"

        type_map = {
            ArgumentType.STRING: "str",
            ArgumentType.INTEGER: "int",
            ArgumentType.FLOAT: "float",
            ArgumentType.BOOLEAN: "bool",
            ArgumentType.PATH: "str",
            ArgumentType.FILE: "str",
            ArgumentType.CHOICE: "str",
            ArgumentType.LIST: "List[str]",
        }

        return type_map.get(param.type, "str")

    def _generate_version_callback(self, cli_name: str, version: str) -> str:
        """
        Generate version callback function.
        """
        code = "def version_callback(value: bool):\n"
        code += '    """Show version and exit."""\n'
        code += "    if value:\n"
        code += f'        typer.echo(f"{cli_name} version {version}")\n'
        code += "        raise typer.Exit()\n\n"

        code += "@app.callback(invoke_without_command=True)\n"
        code += "def main(\n"
        code += "    version: Annotated[Optional[bool], typer.Option(\n"
        code += '        None, "--version", "-v",\n'
        code += "        callback=version_callback,\n"
        code += "        is_eager=True,\n"
        code += '        help="Show version"\n'
        code += "    )] = None,\n"
        code += "):\n"
        code += '    """Main entry point."""\n'
        code += "    pass\n"

        return code
