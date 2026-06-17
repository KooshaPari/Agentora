"""
CLI-Builder-Kit: Framework-agnostic CLI construction toolkit.

This kit provides a unified interface for building command-line applications
with support for multiple backend frameworks:
- argparse (Python standard library)
- click (Flask-style decorators)
- typer (modern type hints)

Features:
- Backend-agnostic CLI definition
- Automatic help generation
- Type validation and conversion
- Command composition and grouping
- Argument parsing across frameworks
- Backend switching without code changes
- Decorator-based command registration
- Rich CLI output formatting
"""

# Backends
from .backends.argparse_backend import ArgparseBackend
from .backends.click_backend import ClickBackend
from .backends.registry import BackendRegistry, get_backend, register_backend
from .backends.typer_backend import TyperBackend

# Core CLI components
from .cli import CLI, Command

# Core builders and decorators
from .core.builder import CLIBuilder
from .core.command import ArgumentDefinition, CommandDefinition
from .core.decorators import argument, command, group, option

__version__ = "0.1.0"
__kit_name__ = "cli"

__all__ = [
    # Core
    "CLI",
    "Command",
    # Backends
    "ArgparseBackend",
    "ClickBackend",
    "TyperBackend",
    "BackendRegistry",
    "register_backend",
    "get_backend",
    # Builders
    "CLIBuilder",
    "CommandDefinition",
    "ArgumentDefinition",
    # Decorators
    "command",
    "argument",
    "option",
    "group",
]
