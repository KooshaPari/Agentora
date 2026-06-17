"""
Version management utilities for publishing.
"""

import re
import subprocess
import sys
from pathlib import Path


class VersionManager:
    """
    Manages version bumping and git operations for publishing.
    """

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.pyproject_path = project_path / "pyproject.toml"

    def get_current_version(self) -> str:
        """
        Get the current version from pyproject.toml.
        """
        if not self.pyproject_path.exists():
            raise FileNotFoundError("pyproject.toml not found")

        content = self.pyproject_path.read_text()
        match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
        if not match:
            raise ValueError("Version not found in pyproject.toml")

        return match.group(1)

    def bump_version(self, current_version: str, bump_type: str = "patch") -> str:
        """
        Bump version based on type.

        Args:
            current_version: Current version string
            bump_type: Type of bump - "patch", "minor", "major", or custom version

        Returns:
            New version string
        """
        if bump_type == "custom":
            # For custom version, we'll handle it in the CLI
            return current_version

        # Parse version
        version_parts = current_version.split(".")
        if len(version_parts) < 2:
            raise ValueError(f"Invalid version format: {current_version}")

        try:
            major = int(version_parts[0])
            minor = int(version_parts[1])
            patch = int(version_parts[2]) if len(version_parts) > 2 else 0
        except ValueError:
            raise ValueError(f"Invalid version format: {current_version}")

        # Bump based on type
        if bump_type == "major":
            major += 1
            minor = 0
            patch = 0
        elif bump_type == "minor":
            minor += 1
            patch = 0
        elif bump_type == "patch":
            patch += 1
        else:
            raise ValueError(f"Invalid bump type: {bump_type}")

        return f"{major}.{minor}.{patch}"

    def update_pyproject_version(self, new_version: str) -> None:
        """
        Update version in pyproject.toml.
        """
        if not self.pyproject_path.exists():
            raise FileNotFoundError("pyproject.toml not found")

        content = self.pyproject_path.read_text()

        # Update version line
        pattern = r'(version\s*=\s*["\'])[^"\']+(["\'])'
        replacement = f"\\g<1>{new_version}\\g<2>"
        new_content = re.sub(pattern, replacement, content)

        if new_content == content:
            raise ValueError("Failed to update version in pyproject.toml")

        self.pyproject_path.write_text(new_content)

    def is_git_repo(self) -> bool:
        """
        Check if current directory is a git repository.
        """
        return (self.project_path / ".git").exists()

    def is_clean_working_tree(self) -> bool:
        """
        Check if git working tree is clean.
        """
        if not self.is_git_repo():
            return False

        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip() == ""
        except subprocess.CalledProcessError:
            return False

    def get_current_branch(self) -> str:
        """
        Get current git branch.
        """
        if not self.is_git_repo():
            raise RuntimeError("Not a git repository")

        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            raise RuntimeError("Failed to get current branch")

    def is_on_main_branch(self) -> bool:
        """
        Check if currently on main branch.
        """
        try:
            current_branch = self.get_current_branch()
            return current_branch in ["main", "master"]
        except RuntimeError:
            return False

    def commit_changes(self, version: str) -> None:
        """
        Commit version changes.
        """
        if not self.is_git_repo():
            raise RuntimeError("Not a git repository")

        try:
            # Add pyproject.toml
            subprocess.run(
                ["git", "add", "pyproject.toml"],
                cwd=self.project_path,
                check=True,
            )

            # Commit
            subprocess.run(
                ["git", "commit", "-m", f"Bump version to {version}"],
                cwd=self.project_path,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to commit changes: {e}")

    def create_tag(self, version: str) -> None:
        """
        Create git tag for version.
        """
        if not self.is_git_repo():
            raise RuntimeError("Not a git repository")

        try:
            subprocess.run(
                ["git", "tag", f"v{version}"],
                cwd=self.project_path,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to create tag: {e}")

    def push_changes(self, include_tags: bool = True) -> None:
        """
        Push changes to remote.
        """
        if not self.is_git_repo():
            raise RuntimeError("Not a git repository")

        try:
            # Push commits
            subprocess.run(
                ["git", "push"],
                cwd=self.project_path,
                check=True,
            )

            # Push tags if requested
            if include_tags:
                subprocess.run(
                    ["git", "push", "--tags"],
                    cwd=self.project_path,
                    check=True,
                )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to push changes: {e}")

    def build_package(self) -> None:
        """
        Build the package using python -m build.
        """
        try:
            subprocess.run(
                [sys.executable, "-m", "build"],
                cwd=self.project_path,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to build package: {e}")

    def publish_package(self, repository: str = "pypi") -> None:
        """
        Publish package to PyPI or test PyPI.
        """
        try:
            subprocess.run(
                [sys.executable, "-m", "twine", "upload", f"--repository={repository}", "dist/*"],
                cwd=self.project_path,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to publish package: {e}")

    def cleanup_build_artifacts(self) -> None:
        """
        Clean up build artifacts.
        """
        dist_dir = self.project_path / "dist"
        build_dir = self.project_path / "build"

        if dist_dir.exists():
            import shutil
            shutil.rmtree(dist_dir)

        if build_dir.exists():
            import shutil
            shutil.rmtree(build_dir)
