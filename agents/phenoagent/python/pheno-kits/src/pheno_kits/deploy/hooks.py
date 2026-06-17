#!/usr/bin/env python3
"""Git hook logic for pheno-vendor automation.

This module provides Python functions that can be called from git hooks
to automate vendoring when requirements.txt changes.

Usage in git hooks:
    python -c "from deploy_kit.hooks import pre_push_check; exit(pre_push_check())"
"""

import subprocess
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from .checks import VendorChecker


def get_project_root() -> Path:
    """
    Find the project root from git repository.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True,
        )
        return Path(result.stdout.strip())
    except subprocess.CalledProcessError:
        # Fallback to current directory
        return Path.cwd()


def get_changed_files() -> list[str]:
    """Get list of files changed since remote branch.

    Returns:
        List of changed file paths
    """
    try:
        # Try to get remote branch
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0:
            remote_branch = result.stdout.strip()
        else:
            # Fallback to origin/<current-branch>
            current_branch = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            remote_branch = f"origin/{current_branch}"

        # Get changed files
        result = subprocess.run(
            ["git", "diff", "--name-only", remote_branch],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0:
            return result.stdout.strip().split("\n") if result.stdout.strip() else []

        # Fallback to HEAD~1
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~1"], capture_output=True, text=True, check=False,
        )

        return result.stdout.strip().split("\n") if result.stdout.strip() else []

    except Exception:
        return []


def requirements_changed(changed_files: list[str] | None = None) -> bool:
    """Check if requirements.txt was changed.

    Args:
        changed_files: List of changed files (default: auto-detect)

    Returns:
        True if requirements.txt changed
    """
    if changed_files is None:
        changed_files = get_changed_files()

    return any("requirements.txt" in f for f in changed_files)


def stage_vendored_files(project_root: Path) -> bool:
    """Stage vendored files and requirements-prod.txt.

    Args:
        project_root: Project root directory

    Returns:
        True if staging succeeded
    """
    try:
        # Stage pheno_vendor directory
        vendor_dir = project_root / "pheno_vendor"
        if vendor_dir.exists():
            subprocess.run(["git", "add", str(vendor_dir)], cwd=project_root, check=False)

        # Stage requirements-prod.txt
        req_prod = project_root / "requirements-prod.txt"
        if req_prod.exists():
            subprocess.run(["git", "add", str(req_prod)], cwd=project_root, check=False)

        return True
    except Exception as e:
        print(f"Warning: Failed to stage vendored files: {e}", file=sys.stderr)
        return False


def pre_push_check(quiet: bool = False, auto_stage: bool = True) -> int:
    """Pre-push hook check for vendoring.

    This function checks if requirements.txt changed and ensures vendoring
    is up-to-date before allowing the push.

    Args:
        quiet: Suppress output messages
        auto_stage: Automatically stage vendored files if updated

    Returns:
        Exit code (0 = success, non-zero = failure)
    """
    project_root = get_project_root()

    if not quiet:
        print("[pre-push] Checking vendored packages...", file=sys.stderr)

    # Get changed files
    changed_files = get_changed_files()

    # Check if requirements.txt changed
    if requirements_changed(changed_files):
        if not quiet:
            print("[pre-push] requirements.txt changed, checking vendoring...", file=sys.stderr)

        # Run vendor check
        checker = VendorChecker(project_root=project_root, quiet=quiet)
        is_stale, reason = checker.is_vendoring_stale()

        if is_stale:
            if not quiet:
                print(f"[pre-push] Vendoring is stale: {reason}", file=sys.stderr)
                print("[pre-push] Running pheno-vendor setup...", file=sys.stderr)

            # Auto-vendor
            if checker.run_vendor_setup():
                if not quiet:
                    print("[pre-push] Auto-vendoring completed successfully", file=sys.stderr)

                # Stage the vendored files
                if auto_stage:
                    if stage_vendored_files(project_root):
                        if not quiet:
                            print(
                                "[pre-push] Staged vendored packages and requirements-prod.txt",
                                file=sys.stderr,
                            )
                    elif not quiet:
                        print(
                            "[pre-push] Warning: Could not stage vendored files",
                            file=sys.stderr,
                        )
            else:
                if not quiet:
                    print("[pre-push] Auto-vendoring failed!", file=sys.stderr)
                    print(
                        "[pre-push] Run 'pheno-vendor setup' manually and try again",
                        file=sys.stderr,
                    )
                return 1
        elif not quiet:
            print("[pre-push] Vendoring is up-to-date", file=sys.stderr)
    else:
        # Requirements didn't change, but check if vendoring exists
        vendor_dir = project_root / "pheno_vendor"
        if not vendor_dir.exists():
            if not quiet:
                print(
                    "[pre-push] pheno_vendor directory not found, may need initial setup",
                    file=sys.stderr,
                )
                print(
                    "[pre-push] Run 'pheno-vendor setup' to initialize vendoring", file=sys.stderr,
                )

    if not quiet:
        print("[pre-push] Vendoring check passed", file=sys.stderr)

    return 0


def main() -> int:
    """
    Main entry point for CLI usage.
    """
    return pre_push_check(quiet=False)


if __name__ == "__main__":
    sys.exit(main())


# Placeholder Hook classes for backward compatibility
class DeploymentHook(ABC):
    """
    Base class for deployment hooks.
    """

    @abstractmethod
    def execute(self, context: dict[str, Any]) -> bool:
        """
        Execute the hook.
        """


class PreDeployHook(DeploymentHook):
    """
    Hook that runs before deployment.
    """



class PostDeployHook(DeploymentHook):
    """
    Hook that runs after deployment.
    """



class HookRegistry:
    """
    Registry for deployment hooks.
    """

    def __init__(self):
        self._hooks: list[DeploymentHook] = []

    def register(self, hook: DeploymentHook) -> None:
        """
        Register a hook.
        """
        self._hooks.append(hook)

    def execute_all(self, context: dict[str, Any]) -> bool:
        """
        Execute all registered hooks.
        """
        return all(hook.execute(context) for hook in self._hooks)
