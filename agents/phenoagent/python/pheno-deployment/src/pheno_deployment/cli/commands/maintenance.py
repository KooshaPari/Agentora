"""
Maintenance commands for vendored packages.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.panel import Panel
from rich.table import Table

from pheno.deployment.checks import check_freshness
from pheno.deployment.startup import check_vendor_on_startup
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
    "--vendor-dir",
    type=str,
    default="pheno_vendor",
    help="Vendor directory name (default: pheno_vendor)",
)
@click.option(
    "--test-imports/--no-test-imports",
    default=False,
    help="Test package imports (default: disabled)",
)
def validate(project_root: Path | None, vendor_dir: str, test_imports: bool) -> None:
    """
    Validate vendored packages.
    """
    console.print("[bold]Validating vendored packages...[/bold]\n")

    try:
        vendor = PhenoVendor(project_root=project_root, vendor_dir=vendor_dir)
        results = vendor.validate_vendored()

        table = Table(title="Validation Results", show_header=True)
        table.add_column("Package", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details", style="dim")

        all_valid = True
        for pkg_name, (success, message) in sorted(results.items()):
            status = "✓" if success else "✗"
            style = "green" if success else "red"
            table.add_row(pkg_name, status, message, style=style)
            if not success:
                all_valid = False

        console.print(table)

        if test_imports:
            console.print("\n[bold]Testing imports...[/bold]\n")
            import_results = vendor.test_imports()

            import_table = Table(title="Import Test Results", show_header=True)
            import_table.add_column("Package", style="cyan")
            import_table.add_column("Status", style="green")
            import_table.add_column("Details", style="dim")

            for pkg_name, (success, message) in sorted(import_results.items()):
                status = "✓" if success else "✗"
                style = "green" if success else "red"
                import_table.add_row(pkg_name, status, message, style=style)
                if not success:
                    all_valid = False

            console.print(import_table)

        if all_valid:
            console.print("\n[bold green]✓ All validations passed![/bold green]")
        else:
            console.print("\n[bold red]✗ Some validations failed[/bold red]")
            sys.exit(1)

    except FileNotFoundError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        console.print("\nRun [cyan]pheno-vendor setup[/cyan] first to create vendor directory")
        sys.exit(1)
    except Exception as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        sys.exit(1)


@click.command()
@click.option(
    "--project-root",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root directory (default: current directory)",
)
@click.option(
    "--vendor-dir",
    type=str,
    default="pheno_vendor",
    help="Vendor directory name (default: pheno_vendor)",
)
@click.confirmation_option(prompt="Are you sure you want to remove all vendored packages?")
def clean(project_root: Path | None, vendor_dir: str) -> None:
    """
    Remove vendored packages directory.
    """
    try:
        vendor = PhenoVendor(project_root=project_root, vendor_dir=vendor_dir)
        if vendor.clean():
            console.print(f"[green]✓ Removed {vendor.vendor_dir}[/green]")
        else:
            console.print(f"[yellow]Vendor directory not found: {vendor.vendor_dir}[/yellow]")
    except Exception as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        sys.exit(1)


@click.command()
@click.option(
    "--project-root",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root directory (default: current directory)",
)
@click.option(
    "--vendor-dir",
    type=str,
    default="pheno_vendor",
    help="Vendor directory name (default: pheno_vendor)",
)
def info(project_root: Path | None, vendor_dir: str) -> None:
    """
    Show information about vendored packages.
    """
    try:
        vendor = PhenoVendor(project_root=project_root, vendor_dir=vendor_dir)

        console.print(
            Panel.fit(
                f"[bold]Project:[/bold] {vendor.project_root}\n"
                f"[bold]Pheno-SDK:[/bold] {vendor.pheno_sdk_root}\n"
                f"[bold]Vendor Dir:[/bold] {vendor.vendor_dir}",
                title="Configuration",
                border_style="blue",
            ),
        )

        console.print("\n[bold]Available Pheno-SDK Packages:[/bold]")
        table = Table(show_header=True)
        table.add_column("Package", style="cyan")
        table.add_column("Module", style="yellow")
        table.add_column("Available", style="green")
        table.add_column("Files", justify="right", style="dim")
        table.add_column("Size", justify="right", style="dim")

        for module_name, pkg_info in sorted(vendor.packages.items()):
            available = "✓" if pkg_info.is_available and pkg_info.has_setup else "✗"
            files = str(pkg_info.python_files_count) if pkg_info.python_files_count > 0 else "-"
            size = f"{pkg_info.size_bytes / 1024:.1f} KB" if pkg_info.size_bytes > 0 else "-"
            table.add_row(pkg_info.dir_name, module_name, available, files, size)

        console.print(table)

        used = vendor.detect_used_packages()
        if used:
            console.print(f"\n[bold]Detected Usage:[/bold] {len(used)} packages")
            console.print(", ".join(sorted(used)))

        if vendor.vendor_dir.exists():
            vendored = [
                d.name
                for d in vendor.vendor_dir.iterdir()
                if d.is_dir() and not d.name.startswith("_")
            ]
            console.print(f"\n[bold]Currently Vendored:[/bold] {len(vendored)} packages")
            console.print(", ".join(sorted(vendored)))
        else:
            console.print("\n[yellow]No vendored packages found[/yellow]")
            console.print("Run [cyan]pheno-vendor setup[/cyan] to vendor packages")

    except Exception as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        sys.exit(1)


@click.command(name="check-freshness")
@click.option(
    "--project-root",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root directory (default: current directory)",
)
@click.option("--auto", is_flag=True, help="Automatically vendor if stale")
@click.option("--force", is_flag=True, help="Force re-vendor even if up-to-date")
@click.option("--quiet", is_flag=True, help="Quiet mode (exit code only)")
def check_freshness_cmd(project_root: Path | None, auto: bool, force: bool, quiet: bool) -> None:
    """
    Check if vendored packages are up-to-date.
    """
    exit_code = check_freshness(
        project_root=project_root,
        auto_vendor=auto,
        force=force,
        quiet=quiet,
    )
    sys.exit(exit_code)


@click.command(name="startup-check")
@click.option(
    "--project-root",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root directory (default: current directory)",
)
@click.option("--quiet", is_flag=True, help="Quiet mode")
def startup_check_cmd(project_root: Path | None, quiet: bool) -> None:
    """
    Check vendored packages before production startup.
    """
    success = check_vendor_on_startup(project_root=project_root, quiet=quiet, exit_on_failure=False)
    sys.exit(0 if success else 1)


__all__ = [
    "check_freshness_cmd",
    "clean",
    "info",
    "startup_check_cmd",
    "validate",
]
