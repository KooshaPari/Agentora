#!/usr/bin/env python3
"""Git hook installation for pheno-vendor automation.

This module installs git hooks in target projects that call centralized
deploy-kit functions for vendoring automation.

Usage:
    from deploy_kit.install_hooks import install_pre_push_hook

    install_pre_push_hook("/path/to/project")

Or via CLI:
    pheno-vendor install-hooks
"""

import os
import stat
import subprocess
import sys
from pathlib import Path

# Pre-push hook template that calls deploy-kit
PRE_PUSH_HOOK_TEMPLATE = """#!/bin/bash
# Pre-push hook: Auto-vendor pheno-sdk if requirements.txt changed
# This hook is installed and managed by pheno-sdk/deploy-kit
# To update: run 'pheno-vendor install-hooks'

set -e

# Colors
GREEN='\\033[0;32m'
BLUE='\\033[0;34m'
YELLOW='\\033[1;33m'
RED='\\033[0;31m'
NC='\\033[0m'

echo -e "${BLUE}[pre-push]${NC} Running vendor automation check..."

# Call centralized deploy-kit hook logic
python3 -c "from deploy_kit.hooks import pre_push_check; exit(pre_push_check())"

exit_code=$?
if [ $exit_code -ne 0 ]; then
    echo -e "${RED}[pre-push]${NC} Vendor check failed!"
    exit $exit_code
fi

echo -e "${GREEN}[pre-push]${NC} All checks passed"
exit 0
"""


def find_git_hooks_dir(project_root: Path | None = None) -> Path | None:
    """Find the .git/hooks directory for a project.

    Args:
        project_root: Project root directory (default: current directory)

    Returns:
        Path to .git/hooks or None if not found
    """
    project_root = Path.cwd() if project_root is None else Path(project_root)

    # Check if .git directory exists
    git_dir = project_root / ".git"
    if not git_dir.exists():
        # Try to find git dir via git command
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=project_root,
                capture_output=True,
                text=True,
                check=True,
            )
            git_dir = project_root / result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    return hooks_dir


def install_pre_push_hook(
    project_root: Path | None = None,
    force: bool = False,
    backup: bool = True,
) -> bool:
    """Install pre-push hook in a project.

    Args:
        project_root: Project root directory (default: current directory)
        force: Overwrite existing hook (default: False)
        backup: Backup existing hook before overwriting (default: True)

    Returns:
        True if hook was installed successfully
    """
    hooks_dir = find_git_hooks_dir(project_root)
    if hooks_dir is None:
        print("Error: Not a git repository or .git/hooks not found", file=sys.stderr)
        return False

    hook_file = hooks_dir / "pre-push"

    # Check if hook already exists
    if hook_file.exists():
        if not force:
            print(f"Pre-push hook already exists at {hook_file}", file=sys.stderr)
            print("Use --force to overwrite", file=sys.stderr)
            return False

        # Backup existing hook
        if backup:
            backup_file = hook_file.with_suffix(".backup")
            counter = 1
            while backup_file.exists():
                backup_file = hook_file.with_suffix(f".backup.{counter}")
                counter += 1

            hook_file.rename(backup_file)
            print(f"Backed up existing hook to {backup_file}")

    # Write hook file
    hook_file.write_text(PRE_PUSH_HOOK_TEMPLATE)

    # Make executable
    current_permissions = hook_file.stat().st_mode
    hook_file.chmod(current_permissions | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    print(f"✓ Installed pre-push hook at {hook_file}")
    return True


def uninstall_pre_push_hook(
    project_root: Path | None = None,
    restore_backup: bool = True,
) -> bool:
    """Uninstall pre-push hook from a project.

    Args:
        project_root: Project root directory (default: current directory)
        restore_backup: Restore backup if available (default: True)

    Returns:
        True if hook was uninstalled successfully
    """
    hooks_dir = find_git_hooks_dir(project_root)
    if hooks_dir is None:
        print("Error: Not a git repository or .git/hooks not found", file=sys.stderr)
        return False

    hook_file = hooks_dir / "pre-push"

    if not hook_file.exists():
        print("Pre-push hook not found", file=sys.stderr)
        return False

    # Check if this is a deploy-kit hook
    content = hook_file.read_text()
    if "deploy-kit" not in content:
        print("Warning: Existing hook is not a deploy-kit hook", file=sys.stderr)
        print("Use --force to remove anyway", file=sys.stderr)
        return False

    # Remove hook
    hook_file.unlink()
    print(f"✓ Removed pre-push hook from {hook_file}")

    # Restore backup if available
    if restore_backup:
        backup_file = hook_file.with_suffix(".backup")
        if backup_file.exists():
            backup_file.rename(hook_file)
            print(f"✓ Restored backup hook from {backup_file}")

    return True


def verify_hook_installation(project_root: Path | None = None) -> bool:
    """Verify that the pre-push hook is installed and working.

    Args:
        project_root: Project root directory (default: current directory)

    Returns:
        True if hook is installed and valid
    """
    hooks_dir = find_git_hooks_dir(project_root)
    if hooks_dir is None:
        print("✗ Not a git repository", file=sys.stderr)
        return False

    hook_file = hooks_dir / "pre-push"

    if not hook_file.exists():
        print("✗ Pre-push hook not installed", file=sys.stderr)
        return False

    # Check if executable
    if not os.access(hook_file, os.X_OK):
        print("✗ Pre-push hook is not executable", file=sys.stderr)
        return False

    # Check if it's a deploy-kit hook
    content = hook_file.read_text()
    if "deploy-kit" not in content:
        print("⚠ Pre-push hook exists but is not a deploy-kit hook", file=sys.stderr)
        return False

    print("✓ Pre-push hook is installed and configured correctly")
    return True


def main() -> int:
    """
    Main entry point for CLI usage.
    """
    import argparse

    parser = argparse.ArgumentParser(description="Install git hooks for pheno-vendor automation")
    parser.add_argument(
        "action", choices=["install", "uninstall", "verify"], help="Action to perform",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=None,
        help="Project root directory (default: current directory)",
    )
    parser.add_argument("--force", action="store_true", help="Force overwrite existing hook")
    parser.add_argument("--no-backup", action="store_true", help="Don't backup existing hook")

    args = parser.parse_args()

    if args.action == "install":
        success = install_pre_push_hook(
            project_root=args.project_root, force=args.force, backup=not args.no_backup,
        )
    elif args.action == "uninstall":
        success = uninstall_pre_push_hook(
            project_root=args.project_root, restore_backup=not args.no_backup,
        )
    elif args.action == "verify":
        success = verify_hook_installation(project_root=args.project_root)
    else:
        parser.print_help()
        return 1

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
