#!/usr/bin/env python3
"""Vendor Freshness Checker for pheno-sdk packages.

Centralized vendoring freshness checks - imported by projects to verify
that pheno_vendor/ directory is up-to-date with requirements.txt.

Usage:
    from pheno.deployment.checks import VendorChecker

    checker = VendorChecker()
    is_stale, reason = checker.is_vendoring_stale()
    if is_stale:
        checker.run_vendor_setup()
"""

import subprocess
import sys
from pathlib import Path


class VendorChecker:
    """
    Check and manage pheno-vendor package freshness.
    """

    def __init__(self, project_root: Path | None = None, quiet: bool = False):
        """Initialize vendor checker.

        Args:
            project_root: Project root directory (default: auto-detect)
            quiet: Suppress output messages
        """
        self.project_root = project_root or self._find_project_root()
        self.quiet = quiet
        self.vendor_dir = self.project_root / "pheno_vendor"
        self.requirements_file = self.project_root / "requirements.txt"
        self.requirements_prod = self.project_root / "requirements-prod.txt"

    def _find_project_root(self) -> Path:
        """
        Find project root by looking for requirements.txt.
        """
        # Start from cwd and walk up
        current = Path.cwd()
        for parent in [current, *list(current.parents)]:
            if (parent / "requirements.txt").exists():
                return parent
        return current

    def _log(self, message: str, level: str = "info") -> None:
        """Log message if not in quiet mode.

        Args:
            message: Message to log
            level: Log level (info, warning, error, success)
        """
        if self.quiet:
            return

        colors = {
            "info": "\033[0;34m",  # Blue
            "warning": "\033[1;33m",  # Yellow
            "error": "\033[0;31m",  # Red
            "success": "\033[0;32m",  # Green
        }
        reset = "\033[0m"

        color = colors.get(level, "")
        prefix = {
            "info": "ℹ",
            "warning": "⚠",
            "error": "✗",
            "success": "✓",
        }.get(level, "•")

        print(f"{color}{prefix}{reset} {message}", file=sys.stderr)

    def check_vendor_exists(self) -> bool:
        """
        Check if vendor directory exists.
        """
        return self.vendor_dir.exists() and self.vendor_dir.is_dir()

    def check_requirements_exist(self) -> bool:
        """
        Check if requirements files exist.
        """
        return self.requirements_file.exists()

    def get_vendor_mtime(self) -> float | None:
        """
        Get modification time of vendor directory.
        """
        if not self.check_vendor_exists():
            return None
        try:
            return self.vendor_dir.stat().st_mtime
        except OSError:
            return None

    def get_requirements_mtime(self) -> float | None:
        """
        Get modification time of requirements.txt.
        """
        if not self.check_requirements_exist():
            return None
        try:
            return self.requirements_file.stat().st_mtime
        except OSError:
            return None

    def is_vendoring_stale(self) -> tuple[bool, str]:
        """Check if vendoring is stale.

        Returns:
            Tuple of (is_stale, reason)
        """
        # Check if vendor directory exists
        if not self.check_vendor_exists():
            return True, "pheno_vendor directory does not exist"

        # Check if requirements.txt exists
        if not self.check_requirements_exist():
            return False, "requirements.txt not found (skipping check)"

        # Check if requirements-prod.txt exists
        if not self.requirements_prod.exists():
            return True, "requirements-prod.txt does not exist"

        # Compare modification times
        vendor_mtime = self.get_vendor_mtime()
        requirements_mtime = self.get_requirements_mtime()

        if vendor_mtime is None:
            return True, "Could not read vendor directory mtime"

        if requirements_mtime is None:
            return False, "Could not read requirements.txt mtime (skipping check)"

        if requirements_mtime > vendor_mtime:
            return True, "requirements.txt is newer than pheno_vendor"

        # Check if vendor directory is empty
        try:
            vendor_contents = list(self.vendor_dir.iterdir())
            if len(vendor_contents) == 0:
                return True, "pheno_vendor directory is empty"

            # Filter out __pycache__ and hidden files
            real_packages = [
                p
                for p in vendor_contents
                if p.is_dir() and not p.name.startswith(".") and p.name != "__pycache__"
            ]

            if len(real_packages) == 0:
                return True, "pheno_vendor has no actual packages"

        except OSError as e:
            return True, f"Could not read vendor directory: {e}"

        return False, "Vendoring is up-to-date"

    def run_vendor_setup(self, force: bool = False) -> bool:
        """Run pheno-vendor setup.

        Args:
            force: Force re-vendor even if up-to-date

        Returns:
            True if vendoring succeeded, False otherwise
        """
        self._log("Running pheno-vendor setup...", "info")

        # Check if pheno-vendor is installed
        try:
            result = subprocess.run(
                ["pheno-vendor", "--version"], capture_output=True, text=True, check=False,
            )
            if result.returncode != 0:
                self._log("pheno-vendor not found, installing deploy-kit...", "warning")
                install_result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "deploy-kit"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if install_result.returncode != 0:
                    self._log(f"Failed to install deploy-kit: {install_result.stderr}", "error")
                    return False
        except FileNotFoundError:
            self._log("pheno-vendor command not found", "error")
            return False

        # Run pheno-vendor setup
        cmd = ["pheno-vendor", "setup"]
        if force:
            cmd.append("--force")

        try:
            result = subprocess.run(
                cmd, cwd=self.project_root, capture_output=True, text=True, check=False,
            )

            if result.returncode == 0:
                self._log("pheno-vendor setup completed successfully", "success")
                return True
            self._log(f"pheno-vendor setup failed: {result.stderr}", "error")
            return False

        except Exception as e:
            self._log(f"Error running pheno-vendor: {e}", "error")
            return False

    def check_and_report(self, auto_vendor: bool = False, force: bool = False) -> int:
        """Check vendoring status and optionally auto-vendor.

        Args:
            auto_vendor: Automatically vendor if stale
            force: Force re-vendor even if up-to-date

        Returns:
            Exit code (0 = up-to-date, 1 = stale, 2 = error)
        """
        if force:
            self._log("Force re-vendoring requested", "info")
            if self.run_vendor_setup(force=True):
                return 0
            return 2

        # Check if vendoring is stale
        is_stale, reason = self.is_vendoring_stale()

        if is_stale:
            self._log(f"Vendoring is stale: {reason}", "warning")

            if auto_vendor:
                self._log("Auto-vendoring enabled, running setup...", "info")
                if self.run_vendor_setup():
                    self._log("Auto-vendoring completed", "success")
                    return 0
                self._log("Auto-vendoring failed", "error")
                return 2
            self._log("Run 'pheno-vendor setup' to update", "info")
            return 1
        self._log(f"Vendoring is up-to-date: {reason}", "success")
        return 0


def check_freshness(
    project_root: Path | None = None,
    auto_vendor: bool = False,
    force: bool = False,
    quiet: bool = False,
) -> int:
    """Check vendor freshness (CLI-friendly interface).

    Args:
        project_root: Project root directory (default: auto-detect)
        auto_vendor: Automatically vendor if stale
        force: Force re-vendor even if up-to-date
        quiet: Quiet mode - only return exit code

    Returns:
        Exit code (0 = up-to-date, 1 = stale, 2 = error)
    """
    checker = VendorChecker(project_root=project_root, quiet=quiet)
    return checker.check_and_report(auto_vendor=auto_vendor, force=force)
