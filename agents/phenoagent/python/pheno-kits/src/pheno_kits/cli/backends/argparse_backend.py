"""Argparse backend generator.

Generates CLI code using Python's built-in argparse module.
"""

from typing import List, Optional

from .registry import BaseBackend
from ...cli_builder.core.command import Argument, ArgumentType, Command, Option


class ArgparseBackend(BaseBackend):
    """
    Backend for generating argparse-based CLIs.
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
        Generate argparse CLI code.
        """
        code = self._generate_header(cli_name, version, standalone)
        code += self._generate_imports()
        code += "\n\n"

        # Include original callback functions
        code += self._generate_callback_functions(commands)
        code += "\n\n"

        # Generate command handler functions
        for cmd in commands:
            code += self._generate_command_functions(cmd)
            code += "\n\n"

        # Generate main function
        code += self._generate_main(cli_name, version, help, commands, global_options, epilog)

        # Generate entry point
        if standalone:
            code += "\n\nif __name__ == '__main__':\n"
            code += "    main()\n"

        return code

    def _generate_imports(self) -> str:
        """
        Generate import statements.
        """
        return "import argparse\nimport sys"

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

    def _generate_command_functions(self, cmd: Command, indent: int = 0) -> str:
        """
        Generate handler functions for commands.
        """
        ind = "    " * indent
        code = f"{ind}def {cmd.name.replace('-', '_')}_handler(args):\n"

        if cmd.callback:
            # Call the original callback
            code += f"{ind}    # Call command implementation\n"
            args_list = []

            for arg in cmd.arguments:
                args_list.append(f"args.{arg.name}")

            for opt in cmd.options:
                args_list.append(f"args.{opt.name}")

            code += f"{ind}    return {cmd.callback.__name__}({', '.join(args_list)})\n"
        else:
            code += f'{ind}    print("Executing {cmd.name} command")\n'

        # Generate subcommand functions recursively
        for subcmd in cmd.subcommands:
            code += "\n\n"
            code += self._generate_command_functions(subcmd, indent)

        return code

    def _generate_main(
        self,
        cli_name: str,
        version: str,
        help: str,
        commands: List[Command],
        global_options: List[Option],
        epilog: Optional[str],
    ) -> str:
        """
        Generate main function with argument parser.
        """
        code = "def main():\n"
        code += "    parser = argparse.ArgumentParser(\n"
        code += f'        prog="{cli_name}",\n'
        code += f'        description="{help}",\n'

        if epilog:
            code += f'        epilog="{epilog}",\n'

        code += "    )\n\n"

        # Add version
        code += "    parser.add_argument(\n"
        code += '        "--version",\n'
        code += '        action="version",\n'
        code += f'        version=f"{{parser.prog}} {version}"\n'
        code += "    )\n\n"

        # Add global options
        for opt in global_options:
            code += self._generate_option(opt, indent=1)
            code += "\n"

        if self._is_single_command(commands):
            # Single command - add arguments/options directly to parser
            cmd = commands[0]
            for arg in cmd.arguments:
                code += self._generate_argument(arg, indent=1)
                code += "\n"

            for opt in cmd.options:
                code += self._generate_option(opt, indent=1)
                code += "\n"

            code += "    args = parser.parse_args()\n"
            code += f"    return {cmd.name.replace('-', '_')}_handler(args)\n"
        else:
            # Multiple commands - use subparsers
            code += "    subparsers = parser.add_subparsers(\n"
            code += '        dest="command",\n'
            code += '        help="Available commands",\n'
            code += "        required=True\n"
            code += "    )\n\n"

            for cmd in commands:
                code += self._generate_subparser(cmd, indent=1, parent_subparser="subparsers")
                code += "\n"

            code += "    args = parser.parse_args()\n"
            code += "    return args.func(args)\n"

        return code

    def _generate_subparser(
        self, cmd: Command, indent: int = 0, parent_subparser: str = "subparsers"
    ) -> str:
        """
        Generate subparser for a command.
        """
        ind = "    " * indent
        code = f"{ind}# {cmd.name} command\n"
        code += f'{ind}{cmd.name.replace("-", "_")}_parser = {parent_subparser}.add_parser(\n'
        code += f'{ind}    "{cmd.name}",\n'
        code += f'{ind}    help="{cmd.help}",\n'

        if cmd.epilog:
            code += f'{ind}    epilog="{cmd.epilog}",\n'

        code += f"{ind})\n"

        # Add arguments
        for arg in cmd.arguments:
            code += self._generate_argument(
                arg, indent=indent, parser=f"{cmd.name.replace('-', '_')}_parser"
            )
            code += "\n"

        # Add options
        for opt in cmd.options:
            code += self._generate_option(
                opt, indent=indent, parser=f"{cmd.name.replace('-', '_')}_parser"
            )
            code += "\n"

        # Set handler
        code += f'{ind}{cmd.name.replace("-", "_")}_parser.set_defaults(func={cmd.name.replace("-", "_")}_handler)\n'

        # Handle subcommands
        if cmd.subcommands:
            sub_ind = "    " * (indent + 1)
            subparser_var = f'{cmd.name.replace("-", "_")}_subparsers'
            code += f"\n{ind}# {cmd.name} subcommands\n"
            code += f'{ind}{subparser_var} = {cmd.name.replace("-", "_")}_parser.add_subparsers(\n'
            code += f'{sub_ind}dest="{cmd.name}_subcommand",\n'
            code += f'{sub_ind}help="{cmd.name} subcommands"\n'
            code += f"{ind})\n\n"

            for subcmd in cmd.subcommands:
                code += self._generate_subparser(
                    subcmd, indent=indent, parent_subparser=subparser_var
                )
                code += "\n"

        return code

    def _generate_argument(self, arg: Argument, indent: int = 0, parser: str = "parser") -> str:
        """
        Generate add_argument call for a positional argument.
        """
        ind = "    " * indent
        code = f"{ind}{parser}.add_argument(\n"
        code += f'{ind}    "{arg.name}",\n'

        if arg.help:
            code += f'{ind}    help="{arg.help}",\n'

        if arg.type != ArgumentType.STRING:
            type_map = {
                ArgumentType.INTEGER: "int",
                ArgumentType.FLOAT: "float",
                ArgumentType.BOOLEAN: "bool",
                ArgumentType.PATH: "str",
                ArgumentType.FILE: "str",
            }
            if arg.type in type_map:
                code += f"{ind}    type={type_map[arg.type]},\n"

        if arg.choices:
            code += f"{ind}    choices={arg.choices},\n"

        if arg.nargs:
            code += f'{ind}    nargs="{arg.nargs}",\n'

        if not arg.required:
            code += f"{ind}    default={repr(arg.default)},\n"

        if arg.metavar:
            code += f'{ind}    metavar="{arg.metavar}",\n'

        code += f"{ind})\n"
        return code

    def _generate_option(self, opt: Option, indent: int = 0, parser: str = "parser") -> str:
        """
        Generate add_argument call for an option.
        """
        ind = "    " * indent

        # Build option strings
        opt_strings = opt.option_strings
        opt_str = ", ".join(f'"{s}"' for s in opt_strings)

        code = f"{ind}{parser}.add_argument(\n"
        code += f"{ind}    {opt_str},\n"

        if opt.help:
            code += f'{ind}    help="{opt.help}",\n'

        if opt.is_flag:
            code += f'{ind}    action="store_true",\n'
            if opt.default:
                code += f"{ind}    default={opt.default},\n"
        else:
            if opt.type != ArgumentType.STRING:
                type_map = {
                    ArgumentType.INTEGER: "int",
                    ArgumentType.FLOAT: "float",
                    ArgumentType.BOOLEAN: "bool",
                    ArgumentType.PATH: "str",
                    ArgumentType.FILE: "str",
                }
                if opt.type in type_map:
                    code += f"{ind}    type={type_map[opt.type]},\n"

            if opt.choices:
                code += f"{ind}    choices={opt.choices},\n"

            if opt.multiple:
                code += f'{ind}    action="append",\n'

            if opt.default is not None:
                code += f"{ind}    default={repr(opt.default)},\n"

            if opt.required:
                code += f"{ind}    required=True,\n"

        if opt.metavar:
            code += f'{ind}    metavar="{opt.metavar}",\n'

        code += f"{ind})\n"
        return code
