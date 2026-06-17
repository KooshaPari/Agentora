#!/usr/bin/env python3
"""
Startup vendor check - ensures pheno_vendor is fresh before starting server.

This module is called from production start scripts to ensure vendored packages
are up-to-date before the server starts. It only runs in production mode.

Usage:
    from pheno.deployment.startup import check_vendor_on_startup

    if os.getenv('PRODUCTION'):
        check_vendor_on_startup()
"""

import sys
from pathlib import Path

from pheno.config import get_env
from pheno.deployment.checks import VendorChecker


def should_skip_vendor_check() -> bool:
    """Determine if vendor check should be skipped.

    Returns:
        True if check should be skipped
    """
    # Check if explicitly disabled
    skip_env = (get_env("SKIP_VENDOR_CHECK", "") or "").lower()
    if skip_env in ("1", "true", "yes"):
        return True

    # Skip in development mode unless forced
    is_production = (get_env("PRODUCTION", "") or "").lower() in ("1", "true", "yes")
    if not is_production:
        # In dev mode, skip unless explicitly requested
        return True

    return False


def check_vendor_on_startup(
    project_root: Path | None = None,
    quiet: bool = False,
    exit_on_failure: bool = True,
) -> bool:
    """Check vendored packages before startup.

    Args:
        project_root: Project root directory (default: auto-detect)
        quiet: Suppress output messages
        exit_on_failure: Exit process if vendoring fails (default: True)

    Returns:
        True if vendoring is up-to-date or was fixed, False on failure
    """
    if should_skip_vendor_check():
        if not quiet:
            print("Skipping vendor check (disabled or in dev mode)")
        return True

    if not quiet:
        print("Checking vendored packages before startup...")

    checker = VendorChecker(project_root=project_root, quiet=quiet)

    # Check if vendoring is stale
    is_stale, reason = checker.is_vendoring_stale()

    if is_stale:
        if not quiet:
            print(f"Warning: {reason}")
            print("Running pheno-vendor setup...")

        # Auto-vendor
        if checker.run_vendor_setup():
            if not quiet:
                print("Vendoring completed successfully")
            return True
        error_msg = (
            "Error: Vendoring failed!\n"
            "The server may not work correctly without vendored packages."
        )
        if not quiet:
            print(error_msg, file=sys.stderr)

        if exit_on_failure:
            sys.exit(1)
        return False
    if not quiet:
        print(f"Vendoring is up-to-date: {reason}")
    return True


def main() -> int:
    """Main entry point for CLI usage.

    Returns:
        Exit code (0 = success, 1 = failure)
    """
    result = check_vendor_on_startup(quiet=False, exit_on_failure=False)
    return 0 if result else 1


if __name__ == "__main__":
    sys.exit(main())
