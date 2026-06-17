"""
Project CLI - Command-line interface for project-scoped infrastructure management.

Provides commands for managing project infrastructure:
- pheno project init: Initialize a new project
- pheno project start: Start project services
- pheno project stop: Stop project services
- pheno project status: Check project status
- pheno project cleanup: Clean up project resources

Enhanced CLI UX:
- Long running commands emit Rich spinners when the optional ``rich`` dependency is installed.
- In environments without Rich the CLI falls back to ``click.echo`` messages so output stays readable.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any

import click

from ..deployment_manager import ResourceMode
from ..project_context import project_infra_context
from .progress import progress_step

logger = logging.getLogger(__name__)


class ProjectCLI:
    """
    CLI for project infrastructure management.
    """

    def __init__(self, project_name: str):
        """Initialize CLI.

        Args:
            project_name: Name of the project
        """
        self.project_name = project_name

    def init(
        self,
        domain: str = "kooshapari.com",
        config_dir: str | None = None,
        proxy_port: int = 9100,
        fallback_port: int = 9000,
        enable_proxy: bool = True,
    ) -> bool:
        """Initialize a new project.

        Args:
            domain: Base domain for tunnels
            config_dir: Configuration directory
            proxy_port: Port for reverse proxy server
            fallback_port: Port for fallback server
            enable_proxy: Whether to start reverse proxy server

        Returns:
            True if initialization successful
        """
        try:
            with project_infra_context(
                project_name=self.project_name,
                domain=domain,
                config_dir=config_dir,
                proxy_port=proxy_port,
                fallback_port=fallback_port,
                enable_proxy=enable_proxy,
            ) as ctx:
                # Set environment variables
                ctx.set_environment_variables()

                # Create project configuration file
                config_file = (
                    Path(config_dir or "~/.kinfra").expanduser() / f"{self.project_name}.json"
                )
                config_file.parent.mkdir(parents=True, exist_ok=True)

                project_config = {
                    "project_name": self.project_name,
                    "domain": domain,
                    "proxy_port": proxy_port,
                    "fallback_port": fallback_port,
                    "enable_proxy": enable_proxy,
                    "services": {},
                    "resources": {},
                }

                with open(config_file, "w") as f:
                    json.dump(project_config, f, indent=2)

                click.secho(f"✓ Project '{self.project_name}' initialized", fg="green")
                click.echo(f"Configuration saved to: {config_file}")

                # Show environment variables
                env_vars = ctx.export_environment_variables()
                click.echo("\nEnvironment variables set:")
                for key, value in env_vars.items():
                    click.echo(f"  {key}={value}")

                return True

        except Exception as e:
            logger.exception(f"Error initializing project: {e}")
            click.secho(f"✗ Error: {e}", fg="red")
            return False

    def start_service(
        self,
        service_name: str,
        preferred_port: int | None = None,
        service_type: str = "service",
        scope: str = "tenant",
        resource_type: str = "port",
        domain: str | None = None,
    ) -> bool:
        """Start a service for the project.

        Args:
            service_name: Name of the service
            preferred_port: Preferred port number
            service_type: Type of service
            scope: Resource scope
            resource_type: Type of resource
            domain: Override default domain

        Returns:
            True if service started successfully
        """
        try:
            with project_infra_context(project_name=self.project_name) as ctx:
                with progress_step(f"Allocating ports for '{service_name}'") as step:
                    result = ctx.allocate_and_tunnel(
                        service_name=service_name,
                        preferred_port=preferred_port,
                        service_type=service_type,
                        scope=scope,
                        resource_type=resource_type,
                    )
                    if result and result.get("port"):
                        step.succeed(f"Allocated port {result['port']}")

                click.secho(f"✓ Service '{service_name}' started", fg="green")
                click.echo(f"  Port: {result['port']}")
                click.echo(f"  URL: {result['url']}")
                click.echo(f"  Hostname: {result['hostname']}")

                return True

        except Exception as e:
            logger.exception(f"Error starting service: {e}")
            click.secho(f"✗ Error: {e}", fg="red")
            return False

    def stop_service(self, service_name: str) -> bool:
        """Stop a service for the project.

        Args:
            service_name: Name of the service

        Returns:
            True if service stopped successfully
        """
        try:
            with project_infra_context(project_name=self.project_name) as ctx:
                project_service_name = f"{self.project_name}-{service_name}"
                success = ctx.service_infra.cleanup(project_service_name)

                if success:
                    click.secho(f"✓ Service '{service_name}' stopped", fg="green")
                else:
                    click.secho(f"✗ Failed to stop service '{service_name}'", fg="red")

                return success

        except Exception as e:
            logger.exception(f"Error stopping service: {e}")
            click.secho(f"✗ Error: {e}", fg="red")
            return False

    def status(
        self,
        service_name: str | None = None,
        json_output: bool = False,
    ) -> bool:
        """Show project status.

        Args:
            service_name: Specific service name (optional)
            json_output: Output as JSON

        Returns:
            True if status retrieved successfully
        """
        try:
            with project_infra_context(project_name=self.project_name) as ctx:
                if service_name:
                    # Show status for specific service
                    project_service_name = f"{self.project_name}-{service_name}"
                    service_info = ctx.registry.get_service(project_service_name)

                    if not service_info:
                        click.secho(f"Service not found: {service_name}", fg="red")
                        return False

                    status = {
                        "service_name": service_name,
                        "project": service_info.project,
                        "port": service_info.assigned_port,
                        "pid": service_info.pid,
                        "tunnel_id": service_info.tunnel_id,
                        "hostname": service_info.tunnel_hostname,
                        "url": (
                            f"https://{service_info.tunnel_hostname}"
                            if service_info.tunnel_hostname
                            else None
                        ),
                        "service_type": service_info.service_type,
                        "scope": service_info.scope,
                        "resource_type": service_info.resource_type,
                        "last_seen": service_info.last_seen,
                        "created_at": service_info.created_at,
                    }

                    if json_output:
                        click.echo(json.dumps(status, indent=2))
                    else:
                        click.secho(f"\n📊 Service Status: {service_name}", fg="cyan", bold=True)
                        for key, value in status.items():
                            click.echo(f"  {key}: {value}")

                else:
                    # Show status for all project services
                    services = ctx.get_project_services()

                    if json_output:
                        click.echo(
                            json.dumps(
                                {"project": self.project_name, "services": services}, indent=2,
                            ),
                        )
                    else:
                        click.secho(
                            f"\n📊 Project Status: {self.project_name}", fg="cyan", bold=True,
                        )

                        if not services:
                            click.echo("  (No services running)")
                        else:
                            for service_name, info in services.items():
                                # Remove project prefix for display
                                display_name = service_name.replace(f"{self.project_name}-", "")
                                running = info.get("pid") is not None
                                status_str = "✓ Running" if running else "✗ Stopped"
                                click.secho(
                                    f"  {display_name} [{info.get('service_type', 'service')}] {status_str}",
                                    fg="green" if running else "red",
                                )
                                if info.get("url"):
                                    click.echo(f"    URL: {info['url']}")

                return True

        except Exception as e:
            logger.exception(f"Error getting status: {e}")
            click.secho(f"✗ Error: {e}", fg="red")
            return False

    def enable_maintenance(
        self,
        message: str | None = None,
        estimated_duration: str | None = None,
        contact_info: str | None = None,
        page_type: str = "maintenance",
    ) -> bool:
        """Enable maintenance mode for the project."""

        try:
            with project_infra_context(project_name=self.project_name) as ctx:
                with progress_step(f"Enabling maintenance banner for '{self.project_name}'") as step:
                    ctx.enable_maintenance(
                        message=message,
                        estimated_duration=estimated_duration,
                        contact_info=contact_info,
                        page_type=page_type,
                    )
                    step.succeed(f"Maintenance banner enabled for '{self.project_name}'")

                click.secho(f"✓ Maintenance enabled for project '{self.project_name}'", fg="green")
                if message:
                    click.echo(f"  Message: {message}")
                if estimated_duration:
                    click.echo(f"  Estimated duration: {estimated_duration}")
                if contact_info:
                    click.echo(f"  Contact: {contact_info}")
                click.echo(f"  Active page type: {page_type}")
                return True

        except Exception as e:
            logger.exception(f"Error enabling maintenance: {e}")
            click.secho(f"✗ Error: {e}", fg="red")
            return False

    def disable_maintenance(self) -> bool:
        """Disable maintenance mode for the project."""

        try:
            with project_infra_context(project_name=self.project_name) as ctx:
                with progress_step(f"Disabling maintenance banner for '{self.project_name}'") as step:
                    ctx.disable_maintenance()
                    step.succeed(f"Maintenance banner disabled for '{self.project_name}'")
                click.secho(f"✓ Maintenance disabled for project '{self.project_name}'", fg="green")
                return True

        except Exception as e:
            logger.exception(f"Error disabling maintenance: {e}")
            click.secho(f"✗ Error: {e}", fg="red")
            return False

    def update_fallback_content(
        self,
        page_type: str,
        message: str | None = None,
        estimated_duration: str | None = None,
        contact_info: str | None = None,
    ) -> bool:
        """Update fallback content for a specific page type."""

        try:
            with project_infra_context(project_name=self.project_name) as ctx:
                with progress_step(f"Updating fallback content for page '{page_type}'") as step:
                    ctx.update_fallback_content(
                        page_type=page_type,
                        message=message,
                        estimated_duration=estimated_duration,
                        contact_info=contact_info,
                    )
                    step.succeed(f"Fallback content updated for page '{page_type}'")

                click.secho(
                    f"✓ Updated fallback content for '{page_type}' in project '{self.project_name}'",
                    fg="green",
                )
                if message:
                    click.echo(f"  Message: {message}")
                if estimated_duration:
                    click.echo(f"  Estimated duration: {estimated_duration}")
                if contact_info:
                    click.echo(f"  Contact: {contact_info}")
                return True

        except Exception as e:
            logger.exception(f"Error updating fallback content: {e}")
            click.secho(f"✗ Error: {e}", fg="red")
            return False

    async def deploy_resource(
        self,
        name: str,
        config_path: str,
        mode: str = "tenanted",
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Deploy a resource for the project.

        Args:
            name: Resource name
            config_path: Path to resource configuration file
            mode: Deployment mode (global, tenanted, local)
            metadata: Additional metadata

        Returns:
            True if deployment successful
        """
        try:
            # Load configuration
            config_file = Path(config_path)
            if not config_file.exists():
                logger.error(f"Configuration file not found: {config_path}")
                return False

            if config_file.suffix == ".json":
                with open(config_file) as f:
                    config = json.load(f)
            elif config_file.suffix in {".yaml", ".yml"}:
                try:
                    import yaml

                    with open(config_file) as f:
                        config = yaml.safe_load(f)
                except ImportError:
                    logger.exception("PyYAML not installed for .yaml support")
                    return False
            else:
                logger.error(f"Unsupported config format: {config_file.suffix}")
                return False

            # Deploy resource
            resource_mode = ResourceMode[mode.upper()] if mode else ResourceMode.TENANTED

            with project_infra_context(project_name=self.project_name) as ctx:
                with progress_step(f"Deploying resource '{name}'") as step:
                    success = await ctx.deploy_resource(
                        name=name,
                        config=config,
                        mode=resource_mode,
                        metadata=metadata,
                    )
                    if success:
                        step.succeed(f"Resource '{name}' deployed")
                    else:
                        step.fail(f"Failed to deploy resource '{name}'")

                if success:
                    click.secho(f"✓ Resource deployed: {name}", fg="green")
                else:
                    click.secho(f"✗ Failed to deploy: {name}", fg="red")

                return success

        except Exception as e:
            logger.exception(f"Error deploying resource: {e}")
            click.secho(f"✗ Error: {e}", fg="red")
            return False

    def cleanup(self) -> bool:
        """Clean up all project resources.

        Returns:
            True if cleanup successful
        """
        try:
            with project_infra_context(project_name=self.project_name) as ctx:
                with progress_step(f"Stopping project services for '{self.project_name}'") as step:
                    ctx.cleanup_project_services()
                    step.succeed(f"Project services stopped for '{self.project_name}'")

                with progress_step(f"Releasing project resources for '{self.project_name}'") as step:
                    asyncio.run(ctx.cleanup_project_resources())
                    step.succeed(f"Project resources released for '{self.project_name}'")

                click.secho(f"✓ Project cleanup completed: {self.project_name}", fg="green")
                return True

        except Exception as e:
            logger.exception(f"Error during cleanup: {e}")
            click.secho(f"✗ Error: {e}", fg="red")
            return False


# ============================================================================
# Click CLI Commands
# ============================================================================


@click.group()
@click.argument("project_name")
@click.pass_context
def project_cli(ctx: click.Context, project_name: str):
    """
    Pheno Project Infrastructure Management CLI.
    """
    ctx.ensure_object(dict)
    ctx.obj["cli"] = ProjectCLI(project_name=project_name)


@project_cli.command()
@click.option("--domain", default="kooshapari.com", help="Base domain for tunnels")
@click.option("--config-dir", help="Configuration directory")
@click.option("--proxy-port", default=9100, help="Port for reverse proxy server")
@click.option("--fallback-port", default=9000, help="Port for fallback server")
@click.option("--enable-proxy/--no-proxy", default=True, help="Enable reverse proxy server")
@click.pass_context
def init(
    ctx: click.Context,
    domain: str,
    config_dir: str | None,
    proxy_port: int,
    fallback_port: int,
    enable_proxy: bool,
):
    """
    Initialize a new project.
    """
    cli = ctx.obj["cli"]
    success = cli.init(
        domain=domain,
        config_dir=config_dir,
        proxy_port=proxy_port,
        fallback_port=fallback_port,
        enable_proxy=enable_proxy,
    )
    sys.exit(0 if success else 1)


@project_cli.command()
@click.argument("service_name")
@click.option("--port", "preferred_port", type=int, help="Preferred port number")
@click.option("--service-type", default="service", help="Type of service")
@click.option("--scope", default="tenant", help="Resource scope")
@click.option("--resource-type", default="port", help="Type of resource")
@click.option("--domain", help="Override default domain")
@click.pass_context
def start_service(
    ctx: click.Context,
    service_name: str,
    preferred_port: int | None,
    service_type: str,
    scope: str,
    resource_type: str,
    domain: str | None,
):
    """
    Start a service for the project.
    """
    cli = ctx.obj["cli"]
    success = cli.start_service(
        service_name=service_name,
        preferred_port=preferred_port,
        service_type=service_type,
        scope=scope,
        resource_type=resource_type,
        domain=domain,
    )
    sys.exit(0 if success else 1)


@project_cli.command()
@click.argument("service_name")
@click.pass_context
def stop_service(ctx: click.Context, service_name: str):
    """
    Stop a service for the project.
    """
    cli = ctx.obj["cli"]
    success = cli.stop_service(service_name)
    sys.exit(0 if success else 1)


@project_cli.command()
@click.argument("service_name", required=False)
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
@click.pass_context
def status(
    ctx: click.Context,
    service_name: str | None,
    json_output: bool,
):
    """
    Show project status.
    """
    cli = ctx.obj["cli"]
    success = cli.status(service_name, json_output=json_output)
    sys.exit(0 if success else 1)


@project_cli.command()
@click.argument("name")
@click.option("--config", "-c", required=True, help="Configuration file path")
@click.option("--mode", default="tenanted", help="Deployment mode (global, tenanted, local)")
@click.option("--metadata", "-m", multiple=True, help="Metadata key=value pairs")
@click.pass_context
def deploy_resource(
    ctx: click.Context,
    name: str,
    config: str,
    mode: str,
    metadata: tuple,
):
    """
    Deploy a resource for the project.
    """
    cli = ctx.obj["cli"]
    metadata_dict = {}
    for item in metadata:
        if "=" in item:
            key, value = item.split("=", 1)
            metadata_dict[key] = value

    success = asyncio.run(cli.deploy_resource(name, config, mode, metadata_dict))
    sys.exit(0 if success else 1)


@project_cli.command()
@click.pass_context
def cleanup(ctx: click.Context):
    """
    Clean up all project resources.
    """
    cli = ctx.obj["cli"]
    success = cli.cleanup()
    sys.exit(0 if success else 1)


@project_cli.command(name="enable-maintenance")
@click.option("--message", help="Maintenance message to display")
@click.option("--duration", help="Estimated maintenance duration")
@click.option("--contact", help="Contact information for maintenance inquiries")
@click.option(
    "--page-type",
    default="maintenance",
    show_default=True,
    help="Fallback page type to mark active",
)
@click.pass_context
def enable_maintenance_command(
    ctx: click.Context,
    message: str | None,
    duration: str | None,
    contact: str | None,
    page_type: str,
):
    """Enable maintenance mode for the project."""

    cli = ctx.obj["cli"]
    success = cli.enable_maintenance(
        message=message,
        estimated_duration=duration,
        contact_info=contact,
        page_type=page_type,
    )
    sys.exit(0 if success else 1)


@project_cli.command(name="disable-maintenance")
@click.pass_context
def disable_maintenance_command(ctx: click.Context):
    """Disable maintenance mode for the project."""

    cli = ctx.obj["cli"]
    success = cli.disable_maintenance()
    sys.exit(0 if success else 1)


@project_cli.command(name="update-fallback-content")
@click.option(
    "--page-type",
    default="maintenance",
    show_default=True,
    help="Fallback page type to update",
)
@click.option("--message", help="Content message for the fallback page")
@click.option("--duration", help="Estimated duration to include in the page")
@click.option("--contact", help="Contact information to include in the page")
@click.pass_context
def update_fallback_content_command(
    ctx: click.Context,
    page_type: str,
    message: str | None,
    duration: str | None,
    contact: str | None,
):
    """Update fallback page content for the project."""

    cli = ctx.obj["cli"]
    success = cli.update_fallback_content(
        page_type=page_type,
        message=message,
        estimated_duration=duration,
        contact_info=contact,
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    project_cli()
