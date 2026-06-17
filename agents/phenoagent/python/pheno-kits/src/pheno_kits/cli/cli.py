"""
CLI builder framework.
"""

import sys
from dataclasses import dataclass
from typing import Any, Callable, Dict, List


@dataclass
class Command:
    """
    CLI command definition.
    """

    name: str
    handler: Callable
    description: str = ""
    args: List[str] = None

    def __post_init__(self):
        if self.args is None:
            self.args = []


class CLI:
    """
    CLI application builder.
    """

    def __init__(self, name: str = "app", description: str = ""):
        self.name = name
        self.description = description
        self.commands: Dict[str, Command] = {}
        self.global_options: Dict[str, Any] = {}

    def command(self, name: str, description: str = "", args: List[str] = None):
        """
        Register a command decorator.
        """

        def decorator(func: Callable):
            self.commands[name] = Command(
                name=name, handler=func, description=description, args=args or []
            )
            return func

        return decorator

    def option(self, name: str, default: Any = None, help: str = ""):
        """
        Add global option.
        """
        self.global_options[name] = {"default": default, "help": help}
        return self

    async def run(self, argv: List[str] = None):
        """
        Run CLI with arguments.
        """
        argv = argv or sys.argv[1:]

        if not argv or argv[0] in ["--help", "-h"]:
            self.print_help()
            return

        cmd_name = argv[0]
        cmd_args = argv[1:]

        if cmd_name not in self.commands:
            print(f"Error: Unknown command '{cmd_name}'")
            self.print_help()
            return

        command = self.commands[cmd_name]

        # Parse arguments
        parsed_args = {}
        for i, arg_name in enumerate(command.args):
            if arg_name.startswith("*"):
                name = arg_name.lstrip("*")
                parsed_args[name] = cmd_args[i:]
                break
            if i < len(cmd_args):
                parsed_args[arg_name] = cmd_args[i]

        # Execute command
        try:
            result = await command.handler(**parsed_args)
            return result
        except Exception as e:
            print(f"Error executing {cmd_name}: {e}")
            raise

    def print_help(self):
        """
        Print help message.
        """
        print(f"\n{self.name}")
        if self.description:
            print(f"{self.description}\n")

        print("Commands:")
        for cmd in self.commands.values():
            args_str = " ".join(f"<{arg}>" for arg in cmd.args)
            print(f"  {cmd.name} {args_str}")
            if cmd.description:
                print(f"    {cmd.description}")
        print()
