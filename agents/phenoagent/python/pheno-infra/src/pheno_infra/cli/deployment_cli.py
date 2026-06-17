"""
Deployment CLI - Command-line interface for resource management.

Provides commands for managing global and tenanted resources:
- pheno deploy: Deploy a new resource
- pheno start: Start a resource
- pheno stop: Stop a resource
- pheno status: Check resource status
- pheno discover: Discover available resources
- pheno cleanup: Clean up resources
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any

import click

from ..deployment_manager import DeploymentManager
from ..global_registry import ResourceMode
from .progress import progress_step

logger = logging.getLogger(__name__)


class DeploymentCLI:
    """
    CLI for deployment management.
    """

    def __init__(self, instance_id: str, project_name: str | None = None):
        """Initialize CLI.

        Args:
            instance_id: Unique instance identifier
            project_name: Project name for tenanted deployments
        """
        self.instance_id = instance_id
        self.project_name = project_name
        self.manager: DeploymentManager | None = None

    async def initialize(self) -> None:
        """
        Initialize the deployment manager.
        """
        if not self.manager:
            self.manager = DeploymentManager(
                instance_id=self.instance_id,
                project_name=self.project_name,
            )
            await self.manager.initialize()

    async def deploy(
        self,
        name: str,
        config_path: str,
        mode: str = "global",
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Deploy a resource.

        Args:
            name: Resource name
            config_path: Path to resource configuration file
            mode: Deployment mode (global, tenanted, local)
            metadata: Additional metadata

        Returns:
            True if deployment successful
        """
        await self.initialize()

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
            resource_mode = ResourceMode[mode.upper()] if mode else ResourceMode.GLOBAL
            success = False

            with progress_step(f"Deploying resource '{name}'") as step:
                success = await self.manager.deploy_resource(
                    name,
                    config,
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

    async def start(self, name: str) -> bool:
        """Start a resource.

        Args:
            name: Resource name

        Returns:
            True if started successfully
        """
        await self.initialize()

        try:
            success = False
            with progress_step(f"Starting resource '{name}'") as step:
                success = await self.manager.start_resource(name)
                if success:
                    step.succeed(f"Resource '{name}' started")
                else:
                    step.fail(f"Failed to start resource '{name}'")

            if success:
                click.secho(f"✓ Resource started: {name}", fg="green")
            else:
                click.secho(f"✗ Failed to start: {name}", fg="red")

            return success

        except Exception as e:
            logger.exception(f"Error starting resource: {e}")
            click.secho(f"✗ Error: {e}", fg="red")
            return False

    async def stop(
        self,
        name: str,
        cleanup_global: bool = False,
    ) -> bool:
        """Stop a resource.

        Args:
            name: Resource name
            cleanup_global: Force cleanup of global resource

        Returns:
            True if stopped successfully
        """
        await self.initialize()

        try:
            success = False
            with progress_step(f"Stopping resource '{name}'") as step:
                success = await self.manager.stop_resource(name, cleanup_global=cleanup_global)
                if success:
                    step.succeed(f"Resource '{name}' stopped")
                else:
                    step.fail(f"Failed to stop resource '{name}'")

            if success:
                click.secho(f"✓ Resource stopped: {name}", fg="green")
            else:
                click.secho(f"✗ Failed to stop: {name}", fg="red")

            return success

        except Exception as e:
            logger.exception(f"Error stopping resource: {e}")
            click.secho(f"✗ Error: {e}", fg="red")
            return False

    async def status(
        self,
        name: str | None = None,
        json_output: bool = False,
    ) -> bool:
        """Show resource status.

        Args:
            name: Specific resource name (optional)
            json_output: Output as JSON

        Returns:
            True if status retrieved successfully
        """
        await self.initialize()

        try:
            if name:
                # Show status for specific resource
                status = await self.manager.get_resource_status(name)
                if not status:
                    click.secho(f"Resource not found: {name}", fg="red")
                    return False

                if json_output:
                    click.echo(json.dumps(status, indent=2))
                else:
                    click.secho(f"\n📊 Status: {name}", fg="cyan", bold=True)
                    for key, value in status.items():
                        click.echo(f"  {key}: {value}")

            else:
                # Show status for all resources
                all_status = await self.manager.get_all_status()

                if json_output:
                    click.echo(json.dumps(all_status, indent=2))
                else:
                    click.secho("\n📊 Resource Status", fg="cyan", bold=True)

                    if not all_status:
                        click.echo("  (No resources deployed)")
                    else:
                        for resource_name, status in all_status.items():
                            mode = status.get("mode", "unknown")
                            running = status.get("local", {}).get("running", False)
                            status_str = "✓ Running" if running else "✗ Stopped"
                            click.secho(
                                f"  {resource_name} [{mode}] {status_str}",
                                fg="green" if running else "red",
                            )

            return True

        except Exception as e:
            logger.exception(f"Error getting status: {e}")
            click.secho(f"✗ Error: {e}", fg="red")
            return False

    async def discover(
        self,
        name: str | None = None,
        mode: str | None = None,
        json_output: bool = False,
    ) -> bool:
        """Discover available resources.

        Args:
            name: Specific resource name
            mode: Filter by mode (global, tenanted, local)
            json_output: Output as JSON

        Returns:
            True if discovery successful
        """
        await self.initialize()

        try:
            if name:
                # Discover specific resource
                resource = await self.manager.discover_resource(name)
                if not resource:
                    click.secho(f"Resource not found: {name}", fg="red")
                    return False

                if json_output:
                    click.echo(json.dumps(resource, indent=2))
                else:
                    click.secho(f"\n🔍 Discovered: {name}", fg="cyan", bold=True)
                    for key, value in resource.items():
                        click.echo(f"  {key}: {value}")

            else:
                # List all resources
                filter_mode = ResourceMode[mode.upper()] if mode else None
                resources = await self.manager.list_resources(mode=filter_mode)

                if json_output:
                    click.echo(json.dumps({"resources": resources}, indent=2))
                else:
                    click.secho("\n🔍 Available Resources", fg="cyan", bold=True)

                    if not resources:
                        click.echo("  (No resources found)")
                    else:
                        for resource_name in resources:
                            click.echo(f"  • {resource_name}")

            return True

        except Exception as e:
            logger.exception(f"Error discovering resources: {e}")
            click.secho(f"✗ Error: {e}", fg="red")
            return False

    async def cleanup(
        self,
        mode: str | None = None,
        all_resources: bool = False,
    ) -> bool:
        """Clean up resources.

        Args:
            mode: Filter by mode
            all_resources: Clean up all resources

        Returns:
            True if cleanup successful
        """
        await self.initialize()

        try:
            filter_mode = ResourceMode[mode.upper()] if mode else None
            resources = await self.manager.list_resources(mode=filter_mode)

            if all_resources or not resources:
                with progress_step("Stopping all resources") as step:
                    await self.manager.stop_all()
                    step.succeed("All resources stopped")
                click.secho("✓ Cleanup complete", fg="green")
                return True

            failures: list[str] = []
            for resource_name in resources:
                with progress_step(f"Stopping resource '{resource_name}'") as step:
                    success = await self.manager.stop_resource(resource_name, cleanup_global=True)
                    if success:
                        step.succeed(f"Stopped resource '{resource_name}'")
                    else:
                        failures.append(resource_name)
                        step.fail(f"Failed to stop resource '{resource_name}'")

            if failures:
                click.secho("✗ Cleanup completed with failures", fg="red")
                for name in failures:
                    click.echo(f"  • {name}")
                return False

            click.secho("✓ Cleanup complete", fg="green")
            return True

        except Exception as e:
            logger.exception(f"Error during cleanup: {e}")
            click.secho(f"✗ Error: {e}", fg="red")
            return False


# ============================================================================
# Click CLI Commands
# ============================================================================


@click.group()
@click.option("--instance-id", default="default", help="Instance ID")
@click.option("--project", default=None, help="Project name")
@click.pass_context
def deployment_cli(ctx: click.Context, instance_id: str, project: str | None):
    """
    Pheno Deployment Management CLI.
    """
    ctx.ensure_object(dict)
    ctx.obj["cli"] = DeploymentCLI(instance_id=instance_id, project_name=project)


@deployment_cli.command()
@click.argument("name")
@click.option("--config", "-c", required=True, help="Configuration file path")
@click.option("--mode", default="global", help="Deployment mode (global, tenanted, local)")
@click.option("--metadata", "-m", multiple=True, help="Metadata key=value pairs")
@click.pass_context
def deploy(
    ctx: click.Context,
    name: str,
    config: str,
    mode: str,
    metadata: tuple,
):
    """
    Deploy a new resource.
    """
    cli = ctx.obj["cli"]
    metadata_dict = {}
    for item in metadata:
        if "=" in item:
            key, value = item.split("=", 1)
            metadata_dict[key] = value

    success = asyncio.run(cli.deploy(name, config, mode, metadata_dict))
    sys.exit(0 if success else 1)


@deployment_cli.command()
@click.argument("name")
@click.pass_context
def start(ctx: click.Context, name: str):
    """
    Start a resource.
    """
    cli = ctx.obj["cli"]
    success = asyncio.run(cli.start(name))
    sys.exit(0 if success else 1)


@deployment_cli.command()
@click.argument("name")
@click.option("--cleanup-global", is_flag=True, help="Force cleanup of global resource")
@click.pass_context
def stop(ctx: click.Context, name: str, cleanup_global: bool):
    """
    Stop a resource.
    """
    cli = ctx.obj["cli"]
    success = asyncio.run(cli.stop(name, cleanup_global=cleanup_global))
    sys.exit(0 if success else 1)


@deployment_cli.command()
@click.argument("name", required=False)
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
@click.pass_context
def status(ctx: click.Context, name: str | None, json_output: bool):
    """
    Show resource status.
    """
    cli = ctx.obj["cli"]
    success = asyncio.run(cli.status(name, json_output=json_output))
    sys.exit(0 if success else 1)


@deployment_cli.command()
@click.argument("name", required=False)
@click.option("--mode", help="Filter by mode (global, tenanted, local)")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
@click.pass_context
def discover(
    ctx: click.Context,
    name: str | None,
    mode: str | None,
    json_output: bool,
):
    """
    Discover available resources.
    """
    cli = ctx.obj["cli"]
    success = asyncio.run(cli.discover(name, mode, json_output=json_output))
    sys.exit(0 if success else 1)


@deployment_cli.command()
@click.option("--mode", help="Filter by mode")
@click.option("--all", "all_resources", is_flag=True, help="Clean up all resources")
@click.pass_context
def cleanup(
    ctx: click.Context,
    mode: str | None,
    all_resources: bool,
):
    """
    Clean up resources.
    """
    cli = ctx.obj["cli"]
    success = asyncio.run(cli.cleanup(mode, all_resources=all_resources))
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    deployment_cli()
