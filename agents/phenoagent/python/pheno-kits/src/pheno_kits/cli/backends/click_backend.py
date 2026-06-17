"""Click backend generator.

Generates CLI code using the Click framework.
"""

from typing import List, Optional

from .registry import BaseBackend
from ...cli_builder.core.command import Argument, ArgumentType, Command, Option


class ClickBackend(BaseBackend):
    """
    Backend for generating Click-based CLIs.
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
        Generate Click CLI code.
        """
        code = self._generate_header(cli_name, version, standalone)
        code += self._generate_imports()
        code += "\n\n"

        # Include original callback functions
        code += self._generate_callback_functions(commands)
        code += "\n\n"

        if self._is_single_command(commands):
            # Single command CLI
            cmd = commands[0]
            code += self._generate_single_command(
                cmd, cli_name, version, help, global_options, epilog
            )
        else:
            # Multi-command CLI with groups
            code += self._generate_multi_command(
                cli_name, version, help, commands, global_options, epilog
            )

        # Generate entry point
        if standalone:
            code += "\n\nif __name__ == '__main__':\n"
            if self._is_single_command(commands):
                code += f"    {commands[0].name.replace('-', '_')}()\n"
            else:
                code += "    cli()\n"

        return code

    def _generate_imports(self) -> str:
        """
        Generate import statements.
        """
        return "import click"

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

    def _generate_single_command(
        self,
        cmd: Command,
        cli_name: str,
        version: str,
        help: str,
        global_options: List[Option],
        epilog: Optional[str],
    ) -> str:
        """
        Generate code for single-command CLI.
        """
        code = "@click.command(\n"
        code += f'    name="{cli_name}",\n'
        code += f'    help="{help or cmd.help}",\n'

        if epilog:
            code += f'    epilog="{epilog}",\n'

        code += ")\n"

        # Add version option
        code += f'@click.version_option(version="{version}", prog_name="{cli_name}")\n'

        # Add global options
        for opt in global_options:
            code += self._generate_option_decorator(opt)

        # Add command options
        for opt in cmd.options:
            code += self._generate_option_decorator(opt)

        # Add command arguments
        for arg in reversed(cmd.arguments):  # Click wants them in reverse order
            code += self._generate_argument_decorator(arg)

        # Function definition
        params = []
        for arg in cmd.arguments:
            params.append(arg.name)
        for opt in cmd.options:
            params.append(opt.name)
        for opt in global_options:
            params.append(opt.name)

        code += f"def {cmd.name.replace('-', '_')}({', '.join(params)}):\n"

        if cmd.callback:
            code += f"    '''Generated wrapper for {cmd.callback.__name__}'''\n"
            code += f"    return {cmd.callback.__name__}({', '.join(params)})\n"
        else:
            code += f'    """Execute {cmd.name} command."""\n'
            code += f'    click.echo("Executing {cmd.name}")\n'

        return code

    def _generate_multi_command(
        self,
        cli_name: str,
        version: str,
        help: str,
        commands: List[Command],
        global_options: List[Option],
        epilog: Optional[str],
    ) -> str:
        """
        Generate code for multi-command CLI with groups.
        """
        code = "@click.group(\n"
        code += f'    name="{cli_name}",\n'
        code += f'    help="{help}",\n'

        if epilog:
            code += f'    epilog="{epilog}",\n'

        code += ")\n"

        # Add version option
        code += f'@click.version_option(version="{version}", prog_name="{cli_name}")\n'

        # Add global options
        for opt in global_options:
            code += self._generate_option_decorator(opt)

        # Main CLI group function
        global_params = [opt.name for opt in global_options]
        code += f"def cli({', '.join(global_params)}):\n"
        code += '    """Main CLI entry point."""\n'
        code += "    pass\n\n\n"

        # Generate commands
        for cmd in commands:
            code += self._generate_command(cmd, is_subcommand=False)
            code += "\n\n"

        return code

    def _generate_command(
        self, cmd: Command, is_subcommand: bool = True, parent: str = "cli"
    ) -> str:
        """
        Generate a command or subcommand.
        """
        # Determine decorator
        if cmd.subcommands:
            decorator = f"@{parent}.group"
        else:
            decorator = f"@{parent}.command"

        code = f"{decorator}(\n"
        code += f'    name="{cmd.name}",\n'

        if cmd.help:
            code += f'    help="{cmd.help}",\n'

        if cmd.short_help:
            code += f'    short_help="{cmd.short_help}",\n'

        if cmd.epilog:
            code += f'    epilog="{cmd.epilog}",\n'

        if cmd.hidden:
            code += "    hidden=True,\n"

        if cmd.deprecated:
            code += "    deprecated=True,\n"

        code += ")\n"

        # Add options
        for opt in cmd.options:
            code += self._generate_option_decorator(opt)

        # Add arguments
        for arg in reversed(cmd.arguments):  # Click wants them in reverse order
            code += self._generate_argument_decorator(arg)

        # Function definition
        params = []
        for arg in cmd.arguments:
            params.append(arg.name)
        for opt in cmd.options:
            params.append(opt.name)

        func_name = cmd.name.replace("-", "_")
        code += f"def {func_name}({', '.join(params)}):\n"

        if cmd.callback:
            code += f"    '''Generated wrapper for {cmd.callback.__name__}'''\n"
            code += f"    return {cmd.callback.__name__}({', '.join(params)})\n"
        else:
            code += f'    """Execute {cmd.name} command."""\n'
            code += f'    click.echo("Executing {cmd.name}")\n'

        # Generate subcommands recursively
        if cmd.subcommands:
            code += "\n\n"
            for subcmd in cmd.subcommands:
                code += self._generate_command(subcmd, is_subcommand=True, parent=func_name)
                code += "\n\n"

        return code

    def _generate_argument_decorator(self, arg: Argument) -> str:
        """
        Generate @click.argument decorator.
        """
        code = "@click.argument(\n"
        code += f'    "{arg.name}",\n'

        if arg.type != ArgumentType.STRING:
            type_map = {
                ArgumentType.INTEGER: "click.INT",
                ArgumentType.FLOAT: "click.FLOAT",
                ArgumentType.BOOLEAN: "click.BOOL",
                ArgumentType.PATH: "click.Path()",
                ArgumentType.FILE: "click.File()",
            }
            if arg.type in type_map:
                code += f"    type={type_map[arg.type]},\n"

        if not arg.required and arg.default is not None:
            code += f"    default={repr(arg.default)},\n"

        if arg.nargs and arg.nargs != 1:
            code += f"    nargs={arg.nargs},\n"

        if arg.metavar:
            code += f'    metavar="{arg.metavar}",\n'

        code += ")\n"
        return code

    def _generate_option_decorator(self, opt: Option) -> str:
        """
        Generate @click.option decorator.
        """
        # Build option strings
        opt_strings = opt.option_strings
        opt_str = ", ".join(f'"{s}"' for s in opt_strings)

        code = "@click.option(\n"
        code += f"    {opt_str},\n"

        if opt.help:
            code += f'    help="{opt.help}",\n'

        if opt.is_flag:
            code += "    is_flag=True,\n"
            if opt.default is not None:
                code += f"    default={opt.default},\n"
        else:
            if opt.type != ArgumentType.STRING:
                type_map = {
                    ArgumentType.INTEGER: "click.INT",
                    ArgumentType.FLOAT: "click.FLOAT",
                    ArgumentType.BOOLEAN: "click.BOOL",
                    ArgumentType.PATH: "click.Path()",
                    ArgumentType.FILE: "click.File()",
                }
                if opt.type in type_map:
                    code += f"    type={type_map[opt.type]},\n"

            if opt.choices:
                choices_str = ", ".join(f'"{c}"' for c in opt.choices)
                code += f"    type=click.Choice([{choices_str}]),\n"

            if opt.multiple:
                code += "    multiple=True,\n"

            if opt.default is not None:
                code += f"    default={repr(opt.default)},\n"

            if opt.required:
                code += "    required=True,\n"

            if opt.prompt:
                code += f'    prompt="{opt.prompt}",\n'

            if opt.hide_input:
                code += "    hide_input=True,\n"

            if opt.confirmation_prompt:
                code += "    confirmation_prompt=True,\n"

            if opt.envvar:
                code += f'    envvar="{opt.envvar}",\n'

        if opt.metavar:
            code += f'    metavar="{opt.metavar}",\n'

        code += ")\n"
        return code
