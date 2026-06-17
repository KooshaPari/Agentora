"""
Setup and configuration commands.
"""

import subprocess
import sys
from pathlib import Path

from rich.console import Console
from rich.prompt import Confirm

from ..core import PhenoContext
from ..utils.exceptions import PhenoError
from ..utils.project import ProjectSetup

console = Console()


def cicd(ctx: PhenoContext, project_path: Path | None, force: bool, interactive: bool):
    """
    Apply standardized CI/CD setup to a project.
    """

    # Determine project path
    if not project_path:
        project_path = ctx.get_current_project_path()
        if not project_path:
            project_path = Path.cwd()

    console.print(f"[bold green]🔧 Setting up CI/CD for project in: {project_path}[/bold green]")

    # Check if it's a valid project
    if not (project_path / "pyproject.toml").exists():
        if interactive:
            if not Confirm.ask(f"No pyproject.toml found in {project_path}. Continue anyway?"):
                console.print("[yellow]Operation cancelled[/yellow]")
                return
        else:
            raise PhenoError(
                f"No pyproject.toml found in {project_path}",
                hint="Make sure you're in a Python project directory or create one first",
            )

    # Get project information
    try:
        from pheno.config.core import Config

        temp_config = Config.from_file(project_path / "pyproject.toml")
        pyproject = temp_config.model_dump()

        project_name = pyproject.get("project", {}).get("name", project_path.name)
        project_description = pyproject.get("project", {}).get("description", "")
        project_version = pyproject.get("project", {}).get("version", "0.1.0")

    except Exception:
        project_name = project_path.name
        project_description = ""
        project_version = "0.1.0"

    # Setup standardized CI/CD
    try:
        # Use our existing setup_project.py functionality
        setup = ProjectSetup(ctx.templates_dir)

        success = setup.setup_full_project(
            project_name=project_name,
            project_dir=project_path,
            project_version=project_version,
            project_description=project_description,
            keywords="",  # Will be preserved from existing pyproject.toml
        )

        if success:
            console.print(
                f"\n[bold green]✅ CI/CD setup completed for {project_name}![/bold green]",
            )
        else:
            console.print("\n[yellow]⚠️  CI/CD setup completed with warnings[/yellow]")

    except Exception as e:
        raise PhenoError(f"Failed to setup CI/CD: {e}")


def dev(ctx: PhenoContext, project_path: Path | None, install_deps: bool, setup_hooks: bool):
    """
    Setup development environment for a project.
    """

    # Determine project path
    if not project_path:
        project_path = ctx.get_current_project_path()
        if not project_path:
            project_path = Path.cwd()

    console.print(
        f"[bold green]🛠️  Setting up development environment in: {project_path}[/bold green]",
    )

    # Check if pyproject.toml exists
    pyproject_path = project_path / "pyproject.toml"
    if not pyproject_path.exists():
        raise PhenoError(
            f"No pyproject.toml found in {project_path}",
            hint="Run 'pheno setup cicd' first to create standardized project structure",
        )

    try:
        # Install development dependencies
        if install_deps:
            console.print("\n[bold]📦 Installing development dependencies...[/bold]")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-e", ".[dev,test]"],
                check=False, cwd=project_path,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                console.print(f"[yellow]Warning: pip install failed: {result.stderr}[/yellow]")
            else:
                console.print("[green]✅ Development dependencies installed[/green]")

        # Setup pre-commit hooks
        if setup_hooks and ctx.config.dev.auto_install_hooks:
            console.print("\n[bold]🪝 Setting up pre-commit hooks...[/bold]")

            # First install pre-commit if needed
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "pre-commit"],
                check=False, cwd=project_path,
                capture_output=True,
            )

            # Install hooks
            result = subprocess.run(
                ["pre-commit", "install"], check=False, cwd=project_path, capture_output=True, text=True,
            )

            if result.returncode != 0:
                console.print(f"[yellow]Warning: pre-commit setup failed: {result.stderr}[/yellow]")
            else:
                console.print("[green]✅ Pre-commit hooks installed[/green]")

        # Create .pheno.toml project config
        project_config = {
            "project": {
                "type": "pheno-sdk",
                "setup_version": "1.0.0",
            },
            "dev": {
                "setup_completed": True,
            },
        }

        from ..core.config import save_project_config

        save_project_config(project_config, project_path)

        console.print("\n[bold green]✅ Development environment ready![/bold green]")
        console.print("\n[bold]Next steps:[/bold]")
        console.print("  • Start coding!")
        console.print("  • Run tests: [cyan]pheno dev test[/cyan]")
        console.print("  • Check code quality: [cyan]pheno dev check[/cyan]")

    except Exception as e:
        raise PhenoError(f"Failed to setup development environment: {e}")


def migrate(ctx: PhenoContext, project_path: Path | None, backup: bool):
    """
    Migrate existing project to pheno-sdk standards.
    """

    # Determine project path
    if not project_path:
        project_path = Path.cwd()

    console.print(
        f"[bold green]🔄 Migrating project to pheno-sdk standards: {project_path}[/bold green]",
    )

    try:
        # Apply CI/CD setup (which handles backups)
        setup = ProjectSetup(ctx.templates_dir)

        # Get existing project info
        pyproject_path = project_path / "pyproject.toml"
        if pyproject_path.exists():
            import toml

            with open(pyproject_path) as f:
                pyproject = toml.load(f)

            project_name = pyproject.get("project", {}).get("name", project_path.name)
            project_description = pyproject.get("project", {}).get("description", "")
            project_version = pyproject.get("project", {}).get("version", "0.1.0")
        else:
            project_name = project_path.name
            project_description = f"Migrated pheno-sdk project: {project_path.name}"
            project_version = "0.1.0"

        # Run setup
        success = setup.setup_full_project(
            project_name=project_name,
            project_dir=project_path,
            project_version=project_version,
            project_description=project_description,
            keywords="",
        )

        if success:
            console.print("\n[bold green]✅ Project migrated successfully![/bold green]")
            console.print("\n[bold]Next steps:[/bold]")
            console.print("  1. Review generated configuration files")
            console.print("  2. Run: [cyan]pheno setup dev[/cyan]")
            console.print("  3. Test the migration: [cyan]pheno dev check[/cyan]")

    except Exception as e:
        raise PhenoError(f"Failed to migrate project: {e}")


def hooks(ctx: PhenoContext, project_path: Path | None):
    """
    Setup pre-commit hooks for a project.
    """

    # Determine project path
    if not project_path:
        project_path = ctx.get_current_project_path()
        if not project_path:
            project_path = Path.cwd()

    console.print(f"[bold green]🪝 Setting up pre-commit hooks in: {project_path}[/bold green]")

    # Check for pre-commit config
    precommit_config = project_path / ".pre-commit-config.yaml"
    if not precommit_config.exists():
        console.print(
            "[yellow]No .pre-commit-config.yaml found. Run 'pheno setup cicd' first.[/yellow]",
        )
        return

    try:
        # Install pre-commit
        console.print("Installing pre-commit...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "pre-commit"], check=True, capture_output=True,
        )

        # Install hooks
        console.print("Installing hooks...")
        subprocess.run(["pre-commit", "install"], cwd=project_path, check=True, capture_output=True)

        console.print("[bold green]✅ Pre-commit hooks installed successfully![/bold green]")

    except subprocess.CalledProcessError as e:
        raise PhenoError(f"Failed to setup pre-commit hooks: {e}")


def testing(ctx: PhenoContext, project_path: Path | None):
    """
    Setup testing infrastructure for a project.
    """

    # Determine project path
    if not project_path:
        project_path = ctx.get_current_project_path()
        if not project_path:
            project_path = Path.cwd()

    console.print(
        f"[bold green]🧪 Setting up testing infrastructure in: {project_path}[/bold green]",
    )

    # Create tests directory structure if it doesn't exist
    tests_dir = project_path / "tests"
    tests_dir.mkdir(exist_ok=True)

    # Create basic test files if they don't exist
    test_files = [
        ("__init__.py", ""),
        ("conftest.py", """\"\"\"Shared test configuration.\"\"\"\n\nimport pytest\n"""),
        (
            "test_basic.py",
            """\"\"\"Basic tests.\"\"\"\n\ndef test_import():\n    \"\"\"Test that the package can be imported.\"\"\"\n    # Add your import tests here\n    pass\n""",
        ),
    ]

    for filename, content in test_files:
        test_file = tests_dir / filename
        if not test_file.exists():
            test_file.write_text(content)
            console.print(f"Created: {test_file}")

    console.print("\n[bold green]✅ Testing infrastructure ready![/bold green]")
    console.print("\n[bold]Run tests with:[/bold] [cyan]pheno dev test[/cyan]")
