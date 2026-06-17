"""
Unified CLI Entry Point Consolidates all CLI systems into a single, extensible
framework.
"""

import sys
from pathlib import Path

from .adapters import create_cli_adapter, get_available_frameworks
from .registry import CLIContext


def create_pheno_cli(project_path: Path | None = None, framework: str = "rich") -> int:
    """
    Create and run Pheno CLI.
    """
    if project_path is None:
        project_path = Path.cwd()

    # Create CLI context
    context = CLIContext(project_path)

    # Get available commands
    commands = context.get_available_commands()

    # Create CLI adapter
    try:
        adapter = create_cli_adapter(framework, context.registry)
    except ImportError as e:
        print(f"Error: {e}")
        print(f"Available frameworks: {', '.join(get_available_frameworks())}")
        return 1

    # Create CLI instance
    cli = adapter.create_cli(context.project_type, commands)

    # Run CLI
    return adapter.run_cli(cli, sys.argv[1:])


def create_project_cli(
    project_name: str, project_path: Path | None = None, framework: str = "rich",
) -> int:
    """
    Create and run project-specific CLI.
    """
    if project_path is None:
        project_path = Path.cwd()

    # Create CLI context
    context = CLIContext(project_path)

    # Get available commands for project
    commands = context.get_available_commands()

    # Create CLI adapter
    try:
        adapter = create_cli_adapter(framework, context.registry)
    except ImportError as e:
        print(f"Error: {e}")
        return 1

    # Create CLI instance
    cli = adapter.create_cli(context.project_type, commands)

    # Run CLI
    return adapter.run_cli(cli, sys.argv[1:])


def main():
    """
    Main entry point.
    """
    project_path = Path.cwd()

    # Detect project type
    CLIContext(project_path)

    # Choose framework based on availability
    frameworks = get_available_frameworks()
    if "rich" in frameworks:
        framework = "rich"
    elif "click" in frameworks:
        framework = "click"
    else:
        framework = "argparse"

    # Create and run CLI
    return create_pheno_cli(project_path, framework)


if __name__ == "__main__":
    sys.exit(main())
