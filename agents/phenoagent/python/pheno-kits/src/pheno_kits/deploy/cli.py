"""Pheno-SDK Deployment Toolkit CLI.

Command-line interface for pheno-sdk vendoring and deployment.
"""

import sys
from pathlib import Path

import click
from deploy_kit.checks import check_freshness
from deploy_kit.install_hooks import (
    install_pre_push_hook,
    uninstall_pre_push_hook,
    verify_hook_installation,
)
from deploy_kit.startup import check_vendor_on_startup
from deploy_kit.utils import BuildHookGenerator, PlatformDetector
from deploy_kit.vendor import PhenoVendor
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

console = Console()


@click.group()
@click.version_option(version="0.1.0", prog_name="pheno-vendor")
def cli():
    """Pheno-SDK Deployment Toolkit - Vendoring and production preparation."""


@cli.command()
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
):
    """Vendor pheno-sdk packages for production deployment.

    This command copies pheno-sdk packages into your project's vendor directory,
    generates production requirements, and creates necessary configuration files.

    Example:
        pheno-vendor setup
        pheno-vendor setup --project-root /path/to/project
        pheno-vendor setup --no-auto-detect  # Vendor all packages
    """
    console.print(
        Panel.fit(
            "[bold blue]Pheno-SDK Vendoring System[/bold blue]\n"
            "Preparing production deployment...",
            border_style="blue",
        ),
    )

    try:
        # Initialize vendor
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Initializing...", total=None)

            vendor = PhenoVendor(
                project_root=project_root,
                pheno_sdk_root=pheno_sdk_root,
                vendor_dir=vendor_dir,
            )

            progress.update(task, description="Scanning packages...")

        # Show detected packages
        if auto_detect:
            used_packages = vendor.detect_used_packages()
            console.print(f"\n[green]Detected {len(used_packages)} used packages[/green]")

            if used_packages:
                table = Table(title="Packages to Vendor", show_header=True)
                table.add_column("Package", style="cyan")
                table.add_column("Status", style="green")

                for pkg_name in sorted(used_packages):
                    if pkg_name in vendor.packages:
                        pkg_info = vendor.packages[pkg_name]
                        status = "✓ Available" if pkg_info.is_available else "✗ Not found"
                        table.add_row(pkg_name, status)

                console.print(table)
            else:
                console.print("[yellow]No pheno-sdk packages detected in project[/yellow]")
                return

        # Vendor packages
        console.print("\n[bold]Vendoring packages...[/bold]")

        success = vendor.vendor_all(auto_detect=auto_detect, validate=validate)

        if success:
            console.print("\n[bold green]✓ Vendoring complete![/bold green]")

            # Show next steps
            console.print("\n[bold]Next steps:[/bold]")
            console.print("  1. Review vendored packages:")
            console.print(f"     [cyan]ls -la {vendor.vendor_dir}[/cyan]")
            console.print("  2. Test with production requirements:")
            console.print("     [cyan]pip install -r requirements-prod.txt[/cyan]")
            console.print("  3. Run tests:")
            console.print("     [cyan]pytest tests/[/cyan]")
            console.print("  4. Deploy:")
            console.print("     [cyan]vercel deploy[/cyan]")

            console.print(f"\n[dim]Vendored packages: {vendor.vendor_dir}[/dim]")
            console.print(
                f"[dim]Production requirements: {vendor.project_root}/requirements-prod.txt[/dim]",
            )
            console.print(f"[dim]Manifest: {vendor.vendor_dir}/VENDOR_MANIFEST.txt[/dim]")
        else:
            console.print("\n[bold red]✗ Vendoring failed[/bold red]")
            sys.exit(1)

    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@cli.command()
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
def validate(
    project_root: Path | None,
    vendor_dir: str,
    test_imports: bool,
):
    """Validate vendored packages.

    Checks that all vendored packages are properly structured and importable.

    Example:
        pheno-vendor validate
        pheno-vendor validate --test-imports
    """
    console.print("[bold]Validating vendored packages...[/bold]\n")

    try:
        vendor = PhenoVendor(
            project_root=project_root,
            vendor_dir=vendor_dir,
        )

        # Validate structure
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

        # Test imports if requested
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

        # Summary
        if all_valid:
            console.print("\n[bold green]✓ All validations passed![/bold green]")
        else:
            console.print("\n[bold red]✗ Some validations failed[/bold red]")
            sys.exit(1)

    except FileNotFoundError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        console.print("\nRun [cyan]pheno-vendor setup[/cyan] first to create vendor directory")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@cli.command()
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
def clean(
    project_root: Path | None,
    vendor_dir: str,
):
    """Remove vendored packages directory.

    This will delete the entire vendor directory and its contents.

    Example:
        pheno-vendor clean
    """
    try:
        vendor = PhenoVendor(
            project_root=project_root,
            vendor_dir=vendor_dir,
        )

        if vendor.clean():
            console.print(f"[green]✓ Removed {vendor.vendor_dir}[/green]")
        else:
            console.print(f"[yellow]Vendor directory not found: {vendor.vendor_dir}[/yellow]")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@cli.command()
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
def info(
    project_root: Path | None,
    vendor_dir: str,
):
    """Show information about vendored packages.

    Display details about the vendored packages and deployment configuration.

    Example:
        pheno-vendor info
    """
    try:
        vendor = PhenoVendor(
            project_root=project_root,
            vendor_dir=vendor_dir,
        )

        console.print(
            Panel.fit(
                f"[bold]Project:[/bold] {vendor.project_root}\n"
                f"[bold]Pheno-SDK:[/bold] {vendor.pheno_sdk_root}\n"
                f"[bold]Vendor Dir:[/bold] {vendor.vendor_dir}",
                title="Configuration",
                border_style="blue",
            ),
        )

        # Available packages
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

            table.add_row(
                pkg_info.dir_name,
                module_name,
                available,
                files,
                size,
            )

        console.print(table)

        # Used packages
        used = vendor.detect_used_packages()
        if used:
            console.print(f"\n[bold]Detected Usage:[/bold] {len(used)} packages")
            console.print(", ".join(sorted(used)))

        # Vendored packages
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

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@cli.command()
@click.option(
    "--project-root",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root directory (default: current directory)",
)
@click.option(
    "--platform",
    type=click.Choice(["vercel", "docker", "lambda", "auto"], case_sensitive=False),
    default="auto",
    help="Target platform (default: auto-detect)",
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default=None,
    help="Output file for build hooks (default: stdout)",
)
def generate_hooks(
    project_root: Path | None,
    platform: str,
    output: Path | None,
):
    """Generate build hooks for deployment platforms.

    Creates platform-specific build configuration that uses vendored packages.

    Example:
        pheno-vendor generate-hooks --platform vercel
        pheno-vendor generate-hooks --platform docker --output build.sh
    """
    try:
        project_root = Path(project_root or Path.cwd())

        # Detect platform if auto
        if platform == "auto":
            detector = PlatformDetector(project_root)
            platform = detector.detect()
            console.print(f"[dim]Detected platform: {platform}[/dim]\n")

        # Generate hooks
        generator = BuildHookGenerator(project_root)
        hooks = generator.generate(platform)

        if output:
            output.write_text(hooks)
            console.print(f"[green]✓ Generated build hooks: {output}[/green]")
        else:
            console.print(
                Panel(hooks, title=f"{platform.title()} Build Hooks", border_style="blue"),
            )

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@cli.command(name="install-hooks")
@click.option(
    "--project-root",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root directory (default: current directory)",
)
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite existing hook",
)
@click.option(
    "--no-backup",
    is_flag=True,
    help="Don't backup existing hook",
)
def install_hooks(
    project_root: Path | None,
    force: bool,
    no_backup: bool,
):
    """Install git pre-push hook for automatic vendoring.

    The hook will automatically check and update vendored packages when
    requirements.txt changes before each push.

    Example:
        pheno-vendor install-hooks
        pheno-vendor install-hooks --force  # Overwrite existing hook
    """
    console.print("[bold]Installing git hooks...[/bold]\n")

    try:
        success = install_pre_push_hook(
            project_root=project_root,
            force=force,
            backup=not no_backup,
        )

        if success:
            console.print("\n[bold green]✓ Git hook installed successfully![/bold green]")
            console.print("\n[bold]What this hook does:[/bold]")
            console.print("  • Checks if requirements.txt changed")
            console.print("  • Validates vendored packages are up-to-date")
            console.print("  • Auto-vendors if needed")
            console.print("  • Stages vendored files for commit")
            console.print("\n[dim]Run 'pheno-vendor verify-hooks' to test installation[/dim]")
        else:
            console.print("\n[bold red]✗ Hook installation failed[/bold red]")
            sys.exit(1)

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@cli.command(name="uninstall-hooks")
@click.option(
    "--project-root",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root directory (default: current directory)",
)
@click.option(
    "--no-restore",
    is_flag=True,
    help="Don't restore backup hook",
)
def uninstall_hooks(
    project_root: Path | None,
    no_restore: bool,
):
    """Uninstall git pre-push hook.

    Removes the deploy-kit pre-push hook and optionally restores backup.

    Example:
        pheno-vendor uninstall-hooks
    """
    console.print("[bold]Uninstalling git hooks...[/bold]\n")

    try:
        success = uninstall_pre_push_hook(
            project_root=project_root,
            restore_backup=not no_restore,
        )

        if success:
            console.print("\n[bold green]✓ Git hook uninstalled successfully![/bold green]")
        else:
            console.print("\n[bold red]✗ Hook uninstallation failed[/bold red]")
            sys.exit(1)

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@cli.command(name="verify-hooks")
@click.option(
    "--project-root",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root directory (default: current directory)",
)
def verify_hooks(project_root: Path | None):
    """Verify git hook installation.

    Checks that the pre-push hook is installed and configured correctly.

    Example:
        pheno-vendor verify-hooks
    """
    console.print("[bold]Verifying git hook installation...[/bold]\n")

    try:
        success = verify_hook_installation(project_root=project_root)

        if not success:
            console.print(
                "\n[yellow]Tip: Run 'pheno-vendor install-hooks' to install the hook[/yellow]",
            )
            sys.exit(1)

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@cli.command(name="check-freshness")
@click.option(
    "--project-root",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root directory (default: current directory)",
)
@click.option(
    "--auto",
    is_flag=True,
    help="Automatically vendor if stale",
)
@click.option(
    "--force",
    is_flag=True,
    help="Force re-vendor even if up-to-date",
)
@click.option(
    "--quiet",
    is_flag=True,
    help="Quiet mode (exit code only)",
)
def check_freshness_cmd(
    project_root: Path | None,
    auto: bool,
    force: bool,
    quiet: bool,
):
    """Check if vendored packages are up-to-date.

    Compares pheno_vendor directory with requirements.txt to determine
    if vendoring needs to be updated.

    Example:
        pheno-vendor check-freshness          # Just check status
        pheno-vendor check-freshness --auto   # Auto-vendor if stale
        pheno-vendor check-freshness --quiet  # For scripts

    Exit codes:
        0 - Vendoring is up-to-date
        1 - Vendoring is stale or missing
        2 - Error occurred
    """
    exit_code = check_freshness(
        project_root=project_root,
        auto_vendor=auto,
        force=force,
        quiet=quiet,
    )
    sys.exit(exit_code)


@cli.command(name="startup-check")
@click.option(
    "--project-root",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root directory (default: current directory)",
)
@click.option(
    "--quiet",
    is_flag=True,
    help="Quiet mode",
)
def startup_check_cmd(
    project_root: Path | None,
    quiet: bool,
):
    """Check vendored packages before production startup.

    This command is intended to be called from production startup scripts
    to ensure vendored packages are up-to-date before the server starts.

    Respects SKIP_VENDOR_CHECK and PRODUCTION environment variables.

    Example:
        pheno-vendor startup-check
        PRODUCTION=1 pheno-vendor startup-check

    Exit codes:
        0 - Success (vendoring up-to-date or fixed)
        1 - Failure (vendoring failed)
    """
    success = check_vendor_on_startup(
        project_root=project_root,
        quiet=quiet,
        exit_on_failure=False,
    )
    sys.exit(0 if success else 1)


def main():
    """
    Entry point for pheno-vendor CLI.
    """
    cli()


if __name__ == "__main__":
    main()
