"""
Development workflow commands.
"""

import subprocess
from pathlib import Path

from rich.console import Console

from ..core import PhenoContext
from ..utils.exceptions import PhenoError

console = Console()


def test(
    ctx: PhenoContext, project_path: Path | None, coverage: bool, integration: bool, watch: bool,
):
    """
    Run tests.
    """

    if not project_path:
        project_path = ctx.get_current_project_path() or Path.cwd()

    console.print(f"[bold green]🧪 Running tests in: {project_path}[/bold green]")

    # Build pytest command
    cmd = ["python", "-m", "pytest"]

    if coverage:
        cmd.extend(["--cov", "--cov-report=term-missing"])

    if integration:
        cmd.extend(["-m", "integration"])

    if watch:
        cmd.append("--watch")

    try:
        result = subprocess.run(cmd, check=False, cwd=project_path)
        if result.returncode != 0:
            raise PhenoError("Tests failed", exit_code=result.returncode)
    except FileNotFoundError:
        raise PhenoError("pytest not found. Run 'pheno setup dev' first.")


def lint(ctx: PhenoContext, project_path: Path | None):
    """
    Run linting checks.
    """

    if not project_path:
        project_path = ctx.get_current_project_path() or Path.cwd()

    console.print(f"[bold green]🔍 Running linting checks in: {project_path}[/bold green]")

    try:
        subprocess.run(["ruff", "check", "."], cwd=project_path, check=True)
        console.print("[green]✅ Linting passed[/green]")
    except subprocess.CalledProcessError:
        raise PhenoError("Linting failed")
    except FileNotFoundError:
        raise PhenoError("ruff not found. Run 'pheno setup dev' first.")


def format_code(ctx: PhenoContext, project_path: Path | None):
    """
    Format code.
    """

    if not project_path:
        project_path = ctx.get_current_project_path() or Path.cwd()

    console.print(f"[bold green]✨ Formatting code in: {project_path}[/bold green]")

    try:
        subprocess.run(["black", "."], cwd=project_path, check=True)
        subprocess.run(["isort", "."], cwd=project_path, check=True)
        console.print("[green]✅ Code formatted[/green]")
    except subprocess.CalledProcessError:
        raise PhenoError("Formatting failed")
    except FileNotFoundError:
        raise PhenoError("black/isort not found. Run 'pheno setup dev' first.")


def check(ctx: PhenoContext, project_path: Path | None):
    """
    Run all quality checks.
    """

    if not project_path:
        project_path = ctx.get_current_project_path() or Path.cwd()

    console.print(f"[bold green]🔎 Running all quality checks in: {project_path}[/bold green]")

    # Run format, lint, type check, and tests
    try:
        ctx.invoke(format_code, project_path=project_path)
        ctx.invoke(lint, project_path=project_path)
        ctx.invoke(test, project_path=project_path)

        console.print("[bold green]✅ All checks passed![/bold green]")

    except Exception as e:
        raise PhenoError(f"Quality checks failed: {e}")
