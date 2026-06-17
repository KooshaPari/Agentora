"""
Fallback Configuration CLI - Commands for configuring fallback states and maintenance pages

Provides comprehensive CLI commands for:
- Fallback page management
- Maintenance mode configuration
- Project-specific fallback states
- Template customization
- Configuration import/export
"""

import json
import logging
from pathlib import Path
from typing import Any

import click
from tabulate import tabulate

from ..fallback_site.config_manager import (
    FallbackConfigManager,
    FallbackPageConfig,
    MaintenanceConfig,
)
from .progress import progress_step

logger = logging.getLogger(__name__)


class FallbackCLI:
    """
    CLI for fallback configuration management.
    """

    def __init__(self, config_dir: Path | None = None):
        """Initialize fallback CLI.

        Args:
            config_dir: Directory to store configuration files
        """
        self.config_manager = FallbackConfigManager(config_dir)

    def create_page_config(
        self,
        page_type: str,
        service_name: str,
        title: str,
        message: str,
        refresh_interval: int = 5,
        custom_css: str | None = None,
        custom_js: str | None = None,
        template_vars: dict[str, Any] | None = None,
    ) -> FallbackPageConfig:
        """
        Create a fallback page configuration.

        Args:
            page_type: Type of page (loading, error, maintenance, custom)
            service_name: Name of the service
            title: Page title
            message: Main message
            refresh_interval: Auto-refresh interval in seconds
            custom_css: Custom CSS
            custom_js: Custom JavaScript
            template_vars: Additional template variables

        Returns:
            Fallback page configuration
        """
        return FallbackPageConfig(
            page_type=page_type,
            service_name=service_name,
            title=title,
            message=message,
            refresh_interval=refresh_interval,
            custom_css=custom_css,
            custom_js=custom_js,
            template_vars=template_vars or {},
        )

    def create_maintenance_config(
        self,
        enabled: bool = False,
        message: str = "Service is under maintenance",
        estimated_duration: str = "30 minutes",
        contact_info: str | None = None,
        custom_page: str | None = None,
        allowed_ips: list[str] | None = None,
        bypass_token: str | None = None,
    ) -> MaintenanceConfig:
        """
        Create a maintenance configuration.

        Args:
            enabled: Whether maintenance mode is enabled
            message: Maintenance message
            estimated_duration: Estimated duration
            contact_info: Contact information
            custom_page: Custom maintenance page HTML
            allowed_ips: IP addresses allowed during maintenance
            bypass_token: Token to bypass maintenance mode

        Returns:
            Maintenance configuration
        """
        return MaintenanceConfig(
            enabled=enabled,
            message=message,
            estimated_duration=estimated_duration,
            contact_info=contact_info,
            custom_page=custom_page,
            allowed_ips=allowed_ips or [],
            bypass_token=bypass_token,
        )


# CLI Commands


@click.group()
@click.option("--config-dir", type=click.Path(), help="Configuration directory")
@click.pass_context
def fallback_cli(ctx: click.Context, config_dir: str | None):
    """Fallback configuration management CLI."""
    ctx.ensure_object(dict)
    ctx.obj["cli"] = FallbackCLI(Path(config_dir) if config_dir else None)


@fallback_cli.command()
@click.argument("project_name")
@click.option("--default-page-type", default="loading", help="Default page type")
@click.pass_context
def init_project(ctx: click.Context, project_name: str, default_page_type: str):
    """Initialize fallback configuration for a project."""
    cli = ctx.obj["cli"]

    with progress_step(f"Initializing fallback config for '{project_name}'") as step:
        config = cli.config_manager.create_project_config(project_name, default_page_type)
        cli.config_manager.save_project_config(project_name)
        step.succeed(f"Configuration ready for '{project_name}'")

    click.echo(f"✓ Initialized fallback configuration for project '{project_name}'")
    click.echo(f"  Default page type: {config.default_page_type}")
    click.echo(f"  Available pages: {', '.join(config.fallback_pages.keys())}")


@fallback_cli.command()
@click.argument("project_name")
@click.argument("page_type")
@click.option("--service-name", help="Service name")
@click.option("--title", help="Page title")
@click.option("--message", help="Main message")
@click.option("--refresh-interval", type=int, default=5, help="Refresh interval in seconds")
@click.option("--custom-css", help="Custom CSS")
@click.option("--custom-js", help="Custom JavaScript")
@click.option("--template-vars", help="Template variables as JSON")
@click.pass_context
def set_page(
    ctx: click.Context,
    project_name: str,
    page_type: str,
    service_name: str | None,
    title: str | None,
    message: str | None,
    refresh_interval: int,
    custom_css: str | None,
    custom_js: str | None,
    template_vars: str | None,
):
    """Set fallback page configuration."""
    cli = ctx.obj["cli"]

    # Get existing config or create new one
    existing_config = cli.config_manager.get_fallback_page(project_name, page_type)

    # Parse template variables
    template_vars_dict = {}
    if template_vars:
        try:
            template_vars_dict = json.loads(template_vars)
        except json.JSONDecodeError:
            click.echo("✗ Invalid JSON for template variables")
            ctx.exit(1)

    # Create page config
    page_config = cli.create_page_config(
        page_type=page_type,
        service_name=(
            service_name or existing_config.service_name if existing_config else project_name
        ),
        title=(
            title or existing_config.title
            if existing_config
            else f"{project_name} - {page_type.title()}"
        ),
        message=(
            message or existing_config.message
            if existing_config
            else f"{project_name} is {page_type}..."
        ),
        refresh_interval=refresh_interval,
        custom_css=custom_css,
        custom_js=custom_js,
        template_vars=template_vars_dict,
    )

    with progress_step(f"Updating fallback page '{page_type}' for '{project_name}'") as step:
        cli.config_manager.update_fallback_page(project_name, page_type, page_config)
        cli.config_manager.save_project_config(project_name)
        step.succeed(f"Page '{page_type}' saved")

    click.echo(f"✓ Updated fallback page '{page_type}' for project '{project_name}'")


@fallback_cli.command()
@click.argument("project_name")
@click.option("--message", help="Maintenance message")
@click.option("--duration", help="Estimated duration")
@click.option("--contact", help="Contact information")
@click.option("--custom-page", help="Custom maintenance page HTML")
@click.option("--allowed-ips", help="Comma-separated list of allowed IPs")
@click.option("--bypass-token", help="Token to bypass maintenance mode")
@click.pass_context
def enable_maintenance(
    ctx: click.Context,
    project_name: str,
    message: str | None,
    duration: str | None,
    contact: str | None,
    custom_page: str | None,
    allowed_ips: str | None,
    bypass_token: str | None,
):
    """Enable maintenance mode for a project."""
    cli = ctx.obj["cli"]

    # Parse allowed IPs
    allowed_ips_list = []
    if allowed_ips:
        allowed_ips_list = [ip.strip() for ip in allowed_ips.split(",")]

    # Create maintenance config
    maintenance_config = cli.create_maintenance_config(
        enabled=True,
        message=message or f"{project_name} is under maintenance",
        estimated_duration=duration or "30 minutes",
        contact_info=contact,
        custom_page=custom_page,
        allowed_ips=allowed_ips_list,
        bypass_token=bypass_token,
    )

    with progress_step(f"Enabling maintenance for '{project_name}'") as step:
        cli.config_manager.update_maintenance_config(project_name, maintenance_config)
        cli.config_manager.save_project_config(project_name)
        step.succeed(f"Maintenance enabled for '{project_name}'")

    click.echo(f"✓ Enabled maintenance mode for project '{project_name}'")


@fallback_cli.command()
@click.argument("project_name")
@click.pass_context
def disable_maintenance(ctx: click.Context, project_name: str):
    """Disable maintenance mode for a project."""
    cli = ctx.obj["cli"]

    with progress_step(f"Disabling maintenance for '{project_name}'") as step:
        cli.config_manager.disable_maintenance(project_name)
        cli.config_manager.save_project_config(project_name)
        step.succeed(f"Maintenance disabled for '{project_name}'")

    click.echo(f"✓ Disabled maintenance mode for project '{project_name}'")


@fallback_cli.command()
@click.argument("project_name")
@click.argument("page_type")
@click.argument("template_file", type=click.Path(exists=True))
@click.pass_context
def set_template(
    ctx: click.Context,
    project_name: str,
    page_type: str,
    template_file: str,
):
    """Set custom template for a fallback page."""
    cli = ctx.obj["cli"]

    template_path = Path(template_file)
    template_content = template_path.read_text()

    with progress_step(f"Updating template for '{page_type}' in '{project_name}'") as step:
        cli.config_manager.set_custom_template(project_name, page_type, template_content)
        cli.config_manager.save_project_config(project_name)
        step.succeed(f"Template set for '{page_type}'")

    click.echo(f"✓ Set custom template for '{page_type}' in project '{project_name}'")


@fallback_cli.command()
@click.argument("project_name")
@click.option("--format", type=click.Choice(["json", "yaml"]), default="json", help="Output format")
@click.pass_context
def show_config(ctx: click.Context, project_name: str, format: str):
    """Show fallback configuration for a project."""
    cli = ctx.obj["cli"]

    config = cli.config_manager.get_project_config(project_name)
    if not config:
        click.echo(f"✗ No configuration found for project '{project_name}'")
        ctx.exit(1)

    if format == "json":
        config_data = cli.config_manager.export_project_config(project_name, "json")
        click.echo(config_data)
    elif format == "yaml":
        config_data = cli.config_manager.export_project_config(project_name, "yaml")
        click.echo(config_data)


@fallback_cli.command()
@click.argument("project_name")
@click.argument("config_file", type=click.Path(exists=True))
@click.option("--format", type=click.Choice(["json", "yaml"]), default="json", help="Input format")
@click.pass_context
def import_config(
    ctx: click.Context,
    project_name: str,
    config_file: str,
    format: str,
):
    """Import fallback configuration from file."""
    cli = ctx.obj["cli"]

    config_path = Path(config_file)
    config_data = config_path.read_text()

    with progress_step(f"Importing fallback config for '{project_name}'") as step:
        cli.config_manager.import_project_config(project_name, config_data, format)
        cli.config_manager.save_project_config(project_name)
        step.succeed(f"Configuration imported for '{project_name}'")

    click.echo(f"✓ Imported fallback configuration for project '{project_name}'")


@fallback_cli.command()
@click.argument("project_name")
@click.argument("output_file", type=click.Path())
@click.option("--format", type=click.Choice(["json", "yaml"]), default="json", help="Output format")
@click.pass_context
def export_config(
    ctx: click.Context,
    project_name: str,
    output_file: str,
    format: str,
):
    """Export fallback configuration to file."""
    cli = ctx.obj["cli"]

    config = cli.config_manager.get_project_config(project_name)
    if not config:
        click.echo(f"✗ No configuration found for project '{project_name}'")
        ctx.exit(1)

    config_data = cli.config_manager.export_project_config(project_name, format)

    with progress_step(f"Exporting fallback config for '{project_name}'") as step:
        output_path = Path(output_file)
        output_path.write_text(config_data)
        step.succeed(f"Configuration written to {output_file}")

    click.echo(f"✓ Exported fallback configuration for project '{project_name}' to {output_file}")


@fallback_cli.command()
@click.pass_context
def list_projects(ctx: click.Context):
    """List all configured projects."""
    cli = ctx.obj["cli"]

    projects = cli.config_manager.list_projects()

    if not projects:
        click.echo("No projects configured")
        return

    # Create table
    headers = ["Project Name", "Default Page Type", "Pages", "Maintenance"]
    rows = []

    for project_name in projects:
        config = cli.config_manager.get_project_config(project_name)
        if config:
            pages = ", ".join(config.fallback_pages.keys())
            maintenance = "Enabled" if config.maintenance_config.enabled else "Disabled"
            rows.append([project_name, config.default_page_type, pages, maintenance])

    click.echo(tabulate(rows, headers=headers, tablefmt="grid"))


@fallback_cli.command()
@click.argument("project_name")
@click.pass_context
def list_pages(ctx: click.Context, project_name: str):
    """List all fallback pages for a project."""
    cli = ctx.obj["cli"]

    pages = cli.config_manager.list_project_pages(project_name)

    if not pages:
        click.echo(f"No pages configured for project '{project_name}'")
        return

    # Create table
    headers = ["Page Type", "Service Name", "Title", "Refresh Interval", "Active"]
    rows = []

    for page_type in pages:
        page_config = cli.config_manager.get_fallback_page(project_name, page_type)
        if page_config:
            rows.append(
                [
                    page_type,
                    page_config.service_name,
                    page_config.title,
                    f"{page_config.refresh_interval}s",
                    "Yes" if page_config.is_active else "No",
                ],
            )

    click.echo(tabulate(rows, headers=headers, tablefmt="grid"))


@fallback_cli.command()
@click.argument("project_name")
@click.argument("page_type")
@click.pass_context
def show_page(ctx: click.Context, project_name: str, page_type: str):
    """Show detailed information about a fallback page."""
    cli = ctx.obj["cli"]

    page_config = cli.config_manager.get_fallback_page(project_name, page_type)
    if not page_config:
        click.echo(f"✗ Page '{page_type}' not found for project '{project_name}'")
        ctx.exit(1)

    click.echo(f"Page Type: {page_config.page_type}")
    click.echo(f"Service Name: {page_config.service_name}")
    click.echo(f"Title: {page_config.title}")
    click.echo(f"Message: {page_config.message}")
    click.echo(f"Refresh Interval: {page_config.refresh_interval}s")
    click.echo(f"Active: {page_config.is_active}")

    if page_config.custom_css:
        click.echo(f"Custom CSS: {len(page_config.custom_css)} characters")

    if page_config.custom_js:
        click.echo(f"Custom JS: {len(page_config.custom_js)} characters")

    if page_config.template_vars:
        click.echo(f"Template Variables: {len(page_config.template_vars)} variables")


@fallback_cli.command()
@click.argument("project_name")
@click.pass_context
def show_maintenance(ctx: click.Context, project_name: str):
    """Show maintenance configuration for a project."""
    cli = ctx.obj["cli"]

    config = cli.config_manager.get_project_config(project_name)
    if not config:
        click.echo(f"✗ No configuration found for project '{project_name}'")
        ctx.exit(1)

    maintenance = config.maintenance_config

    click.echo(f"Enabled: {maintenance.enabled}")
    click.echo(f"Message: {maintenance.message}")
    click.echo(f"Estimated Duration: {maintenance.estimated_duration}")

    if maintenance.contact_info:
        click.echo(f"Contact Info: {maintenance.contact_info}")

    if maintenance.allowed_ips:
        click.echo(f"Allowed IPs: {', '.join(maintenance.allowed_ips)}")

    if maintenance.bypass_token:
        click.echo(f"Bypass Token: {maintenance.bypass_token}")

    if maintenance.custom_page:
        click.echo(f"Custom Page: {len(maintenance.custom_page)} characters")


# Wrapper functions for async commands
def run_async_command(coro):
    """Run an async command."""
    import asyncio

    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)
