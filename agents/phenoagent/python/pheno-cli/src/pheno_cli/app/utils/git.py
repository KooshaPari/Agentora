"""
Git utilities for Pheno-CLI.
"""

import subprocess
from pathlib import Path

from rich.console import Console

console = Console()


def init_git_repo(project_dir: Path, initial_commit: bool = True) -> bool:
    """
    Initialize a git repository in the project directory.
    """

    try:
        # Initialize git repo
        subprocess.run(["git", "init"], cwd=project_dir, check=True, capture_output=True)
        console.print("  ✅ Git repository initialized")

        # Create .gitignore if it doesn't exist
        gitignore_path = project_dir / ".gitignore"
        if not gitignore_path.exists():
            gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
dist/
*.egg-info/

# Virtual environments
.env
.venv
venv/
env/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Testing
.coverage
.pytest_cache/
htmlcov/

# Logs
*.log
"""
            gitignore_path.write_text(gitignore_content)
            console.print("  ✅ .gitignore created")

        if initial_commit:
            # Add all files
            subprocess.run(["git", "add", "."], cwd=project_dir, check=True, capture_output=True)

            # Initial commit
            subprocess.run(
                ["git", "commit", "-m", "Initial commit"],
                cwd=project_dir,
                check=True,
                capture_output=True,
            )

            console.print("  ✅ Initial commit created")

        return True

    except subprocess.CalledProcessError as e:
        console.print(f"  ❌ Git initialization failed: {e}")
        return False
    except FileNotFoundError:
        console.print("  ❌ Git not found. Please install Git.")
        return False


def is_git_repo(path: Path) -> bool:
    """
    Check if path is a git repository.
    """
    try:
        subprocess.run(["git", "rev-parse", "--git-dir"], cwd=path, check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def get_git_root(path: Path) -> Path | None:
    """
    Get the root of the git repository.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=path,
            check=True,
            capture_output=True,
            text=True,
        )
        return Path(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
