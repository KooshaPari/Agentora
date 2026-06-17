"""
Setup vendoring command.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import click
from rich.table import Table

from pheno.deployment.ui import create_ui
from pheno.deployment.vendor import PhenoVendor

from ..shared import console


@click.command()
@click.option(
    "--project-root",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root directory (default: current directory)",
)
@click.option(
    "--pheno-sdk-root",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Pheno-SDK root directory (default: auto-detect)",
)
@click.option(
    "--vendor-dir",
    type=str,
    default="pheno_vendor",
    help="Vendor directory name (default: pheno_vendor)",
)
@click.option(
    "--auto-detect/--no-auto-detect",
    default=True,
    help="Auto-detect used packages (default: enabled)",
)
@click.option(
    "--validate/--no-validate",
    default=True,
    help="Validate after vendoring (default: enabled)",
)
@click.option(
    "--clean/--no-clean",
    default=True,
    help="Clean vendor dir before vendoring (default: enabled)",
)
def setup(
    project_root: Path | None,
    pheno_sdk_root: Path | None,
    vendor_dir: str,
    auto_detect: bool,
    validate: bool,
    clean: bool,
) -> None:
    """
    Vendor pheno-sdk packages for production deployment.
    """
    ui = create_ui()
    overall_start = time.time()

    ui.panel(
        "[bold blue]Pheno-SDK Vendoring System[/bold blue]\nPreparing production deployment...",
        title="Setup",
        style="blue",
    )

    try:
        with ui.spinner("Detecting pheno-sdk packages") as step:
            vendor = PhenoVendor(
                project_root=project_root,
                pheno_sdk_root=pheno_sdk_root,
                vendor_dir=vendor_dir,
            )
            if auto_detect:
                used_packages = vendor.detect_used_packages()
                step["count"] = len(used_packages)
            else:
                available = sum(
                    1 for info in vendor.packages.values() if info.is_available and info.has_setup
                )
                step["count"] = available

        if auto_detect:
            used_packages = vendor.detect_used_packages()
            if not used_packages:
                ui.warning("No pheno-sdk packages detected in project")
                return

            table = Table(title="Packages to Vendor", show_header=True)
            table.add_column("Package", style="cyan")
            table.add_column("Status", style="green")

            for pkg_name in sorted(used_packages):
                if pkg_name in vendor.packages:
                    pkg_info = vendor.packages[pkg_name]
                    status = "✓ Available" if pkg_info.is_available else "✗ Not found"
                    table.add_row(pkg_name, status)

            console.print()
            console.print(table)
            console.print()

        if clean and vendor.vendor_dir.exists():
            with ui.spinner("Cleaning vendor directory") as step:
                vendor.clean()
                step["details"] = str(vendor.vendor_dir)

        packages_to_vendor = (
            vendor.detect_used_packages()
            if auto_detect
            else {
                name
                for name, info in vendor.packages.items()
                if info.is_available and info.has_setup
            }
        )
        total_packages = len(packages_to_vendor)

        with ui.step_progress(
            "Vendoring packages", total=total_packages, unit="packages",
        ) as progress:

            def progress_callback(pkg_name: str, current: int, total: int):
                progress.update(current, pkg_name)

            _results, _timings = vendor.vendor_packages(
                auto_detect=auto_detect,
                clean=False,
                progress_callback=progress_callback,
            )

        if validate:
            ui.panel("Running post-vendor validation...", title="Validation", style="green")
            validation_results = vendor.validate_vendored()
            failures = [name for name, (success, _) in validation_results.items() if not success]
            if failures:
                ui.warning(f"Validation failed for: {', '.join(failures)}")

        duration = time.time() - overall_start
        ui.panel(
            f"[bold green]Vendoring completed in {duration:.1f}s[/bold green]",
            title="Done",
            style="green",
        )

    except Exception as exc:
        ui.error(f"Vendoring failed: {exc}")
        sys.exit(1)


__all__ = ["setup"]
