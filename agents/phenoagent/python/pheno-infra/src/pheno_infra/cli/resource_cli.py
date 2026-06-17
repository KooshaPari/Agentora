"""
Resource Management CLI - Enhanced resource coordination commands

Provides a synchronous Click interface over the asynchronous resource coordinator.
"""

import asyncio
import json
import logging
import time
from typing import Any

import click
from tabulate import tabulate

from ..global_registry import ResourceMode
from ..resource_coordinator import (
    LifecycleRule,
    ResourceCoordinator,
    ResourcePolicy,
)
from ..resource_reference_cache import ResourceReuseStrategy
from .progress import progress_step

logger = logging.getLogger(__name__)


class ResourceCLI:
    """
    CLI for enhanced resource management.
    """

    def __init__(self, project_name: str):
        """Initialize resource CLI.

        Args:
            project_name: Name of the project
        """
        self.project_name = project_name
        self.coordinator = ResourceCoordinator(
            instance_id=f"{project_name}-cli-{int(time.time() * 1000)}",
            project_name=project_name,
        )

    async def initialize(self) -> None:
        """Initialize the coordinator."""
        await self.coordinator.initialize()

    async def shutdown(self) -> None:
        """Shutdown the coordinator."""
        await self.coordinator.shutdown()

    async def set_policy(
        self,
        resource_type: str,
        lifecycle_rule: str,
        reuse_strategy: str,
        dependencies: list[str] | None = None,
        compatibility_requirements: dict[str, Any] | None = None,
    ) -> bool:
        """
        Set policy for a resource type.

        Args:
            resource_type: Type of resource (e.g., 'postgres', 'redis')
            lifecycle_rule: Lifecycle rule (project_scoped, global_reuse, smart_decision, dependency_driven)
            reuse_strategy: Reuse strategy (always, conditional, never, smart)
            dependencies: List of dependencies
            compatibility_requirements: Compatibility requirements

        Returns:
            True if policy was set successfully
        """
        try:
            # Parse lifecycle rule
            lifecycle_rule_enum = LifecycleRule(lifecycle_rule)

            # Parse reuse strategy
            reuse_strategy_enum = ResourceReuseStrategy(reuse_strategy)

            # Create policy
            policy = ResourcePolicy(
                resource_type=resource_type,
                lifecycle_rule=lifecycle_rule_enum,
                reuse_strategy=reuse_strategy_enum,
                dependencies=dependencies or [],
                compatibility_requirements=compatibility_requirements or {},
            )

            with progress_step(f"Applying policy for '{resource_type}'") as step:
                self.coordinator.set_resource_policy(policy)
                step.succeed(f"Policy applied for '{resource_type}'")
            return True

        except ValueError as e:
            logger.exception(f"Invalid policy parameters: {e}")
            return False
        except Exception as e:
            logger.exception(f"Error setting policy: {e}")
            return False

    async def request_resource(
        self,
        resource_name: str,
        config: dict[str, Any],
        mode: str | None = None,
        dependencies: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Request a resource with enhanced coordination.

        Args:
            resource_name: Name of the resource
            config: Resource configuration
            mode: Resource mode (global, tenanted, local)
            dependencies: List of dependencies
            metadata: Additional metadata

        Returns:
            True if resource was requested successfully
        """
        try:
            # Parse mode
            resource_mode = None
            if mode:
                resource_mode = ResourceMode(mode)

            # Request resource
            resource_info = None
            with progress_step(f"Requesting resource '{resource_name}'") as step:
                success, resource_info = await self.coordinator.request_resource(
                    resource_name=resource_name,
                    config=config,
                    mode=resource_mode,
                    dependencies=dependencies,
                    metadata=metadata,
                )
                if success:
                    step.succeed(f"Resource '{resource_name}' ready")
                else:
                    step.fail(f"Failed to request resource '{resource_name}'")

            if success and resource_info:
                click.echo(f"✓ Resource '{resource_name}' requested successfully")
                if resource_info.get("is_reused"):
                    click.echo("  → Reused existing global resource")
                if resource_info.get("dependencies"):
                    click.echo(f"  → Dependencies: {', '.join(resource_info['dependencies'])}")
            else:
                click.echo(f"✗ Failed to request resource '{resource_name}'")

            return success

        except Exception as e:
            logger.exception(f"Error requesting resource: {e}")
            click.echo(f"✗ Error requesting resource: {e}")
            return False

    async def release_resource(
        self,
        resource_name: str,
        force: bool = False,
    ) -> bool:
        """
        Release a resource.

        Args:
            resource_name: Name of the resource to release
            force: Force cleanup even if other projects are using it

        Returns:
            True if resource was released successfully
        """
        try:
            with progress_step(f"Releasing resource '{resource_name}'") as step:
                success = await self.coordinator.release_resource(resource_name, force)
                if success:
                    step.succeed(f"Resource '{resource_name}' released")
                else:
                    step.fail(f"Failed to release resource '{resource_name}'")

            if success:
                click.echo(f"✓ Resource '{resource_name}' released successfully")
            else:
                click.echo(f"✗ Failed to release resource '{resource_name}'")

            return success

        except Exception as e:
            logger.exception(f"Error releasing resource: {e}")
            click.echo(f"✗ Error releasing resource: {e}")
            return False

    async def get_resource_status(self, resource_name: str) -> dict[str, Any] | None:
        """
        Get status of a resource.

        Args:
            resource_name: Name of the resource

        Returns:
            Resource status information
        """
        return await self.coordinator.get_resource_status(resource_name)

    async def list_resources(self) -> list[dict[str, Any]]:
        """
        List all project resources.

        Returns:
            List of resource information
        """
        return await self.coordinator.get_project_resources()

    async def validate_dependencies(self) -> tuple[bool, list[str]]:
        """
        Validate project dependencies.

        Returns:
            Tuple of (is_valid, missing_dependencies)
        """
        return await self.coordinator.validate_project_dependencies()

    async def get_coordination_status(self) -> dict[str, Any]:
        """
        Get overall coordination status.

        Returns:
            Coordination status information
        """
        return await self.coordinator.get_coordination_status()


def _run_cli(project_name: str, coro_fn):
    async def runner():
        cli = ResourceCLI(project_name=project_name)
        await cli.initialize()
        try:
            return await coro_fn(cli)
        finally:
            await cli.shutdown()

    return asyncio.run(runner())


# CLI Commands


@click.group()
@click.argument("project_name")
@click.pass_context
def resource_cli(ctx: click.Context, project_name: str):
    """Enhanced resource management CLI (Phase 3)."""
    ctx.ensure_object(dict)
    ctx.obj["project_name"] = project_name


@resource_cli.command()
@click.argument("resource_type")
@click.option(
    "--lifecycle-rule",
    type=click.Choice(["project_scoped", "global_reuse", "smart_decision", "dependency_driven"]),
    default="smart_decision",
    help="Lifecycle rule for the resource type",
)
@click.option(
    "--reuse-strategy",
    type=click.Choice(["always", "conditional", "never", "smart"]),
    default="smart",
    help="Strategy for reusing global resources",
)
@click.option("--dependencies", multiple=True, help="Dependencies for this resource type")
@click.option("--compatibility-requirements", help="JSON string with compatibility requirements")
@click.pass_context
def set_policy(
    ctx: click.Context,
    resource_type: str,
    lifecycle_rule: str,
    reuse_strategy: str,
    dependencies: list[str],
    compatibility_requirements: str | None,
):
    """Set policy for a resource type."""
    project_name = ctx.obj["project_name"]

    def command(cli: ResourceCLI):
        # Parse compatibility requirements
        compat_reqs = None
        if compatibility_requirements:
            compat_reqs = json.loads(compatibility_requirements)
        return cli.set_policy(
            resource_type=resource_type,
            lifecycle_rule=lifecycle_rule,
            reuse_strategy=reuse_strategy,
            dependencies=list(dependencies),
            compatibility_requirements=compat_reqs,
        )

    success = _run_cli(project_name, command)
    if success:
        click.echo(f"✓ Policy set for resource type '{resource_type}'")
    else:
        click.echo(f"✗ Failed to set policy for resource type '{resource_type}'")
        ctx.exit(1)


@resource_cli.command()
@click.argument("resource_name")
@click.argument("config_file", type=click.Path(exists=True))
@click.option("--mode", type=click.Choice(["global", "tenanted", "local"]), help="Resource mode")
@click.option("--dependencies", multiple=True, help="Dependencies for this resource")
@click.option("--metadata", help="JSON string with additional metadata")
@click.pass_context
def request(
    ctx: click.Context,
    resource_name: str,
    config_file: str,
    mode: str | None,
    dependencies: list[str],
    metadata: str | None,
):
    """Request a resource with enhanced coordination."""
    project_name = ctx.obj["project_name"]

    with open(config_file, encoding="utf-8") as f:
        config = json.load(f)

    metadata_dict = json.loads(metadata) if metadata else None

    def command(cli: ResourceCLI):
        return cli.request_resource(
            resource_name=resource_name,
            config=config,
            mode=mode,
            dependencies=list(dependencies),
            metadata=metadata_dict,
        )

    success = _run_cli(project_name, command)
    if not success:
        ctx.exit(1)


@resource_cli.command()
@click.argument("resource_name")
@click.option("--force", is_flag=True, help="Force cleanup even if other projects are using it")
@click.pass_context
def release(ctx: click.Context, resource_name: str, force: bool):
    """Release a resource."""
    project_name = ctx.obj["project_name"]

    def command(cli: ResourceCLI):
        return cli.release_resource(resource_name, force)

    success = _run_cli(project_name, command)
    if not success:
        ctx.exit(1)


@resource_cli.command()
@click.argument("resource_name")
@click.pass_context
def status(ctx: click.Context, resource_name: str):
    """Get status of a resource."""
    project_name = ctx.obj["project_name"]

    def command(cli: ResourceCLI):
        return cli.get_resource_status(resource_name)

    status_info = _run_cli(project_name, command)
    if status_info:
        click.echo(json.dumps(status_info, indent=2))
    else:
        click.echo(f"Resource '{resource_name}' not found")
        ctx.exit(1)


@resource_cli.command()
@click.pass_context
def list_resources(ctx: click.Context):
    """List all project resources."""
    project_name = ctx.obj["project_name"]

    resources = _run_cli(project_name, lambda cli: cli.list_resources())

    if not resources:
        click.echo("No resources found")
        return

    headers = ["Name", "Mode", "Health", "Dependencies", "Metadata"]
    rows = []
    for resource in resources:
        rows.append(
            [
                resource.get("name", "N/A"),
                resource.get("mode", "N/A"),
                resource.get("health", "N/A"),
                ", ".join(resource.get("dependencies", [])),
                json.dumps(resource.get("metadata", {}), separators=(",", ":")),
            ],
        )

    click.echo(tabulate(rows, headers=headers, tablefmt="grid"))


@resource_cli.command()
@click.pass_context
def validate(ctx: click.Context):
    """Validate project dependencies."""
    project_name = ctx.obj["project_name"]

    is_valid, missing = _run_cli(project_name, lambda cli: cli.validate_dependencies())

    if is_valid:
        click.echo("✓ All dependencies are satisfied")
    else:
        click.echo("✗ Missing dependencies:")
        for dep in missing:
            click.echo(f"  - {dep}")
        ctx.exit(1)


@resource_cli.command()
@click.pass_context
def coordination_status(ctx: click.Context):
    """Get overall coordination status."""
    project_name = ctx.obj["project_name"]
    status = _run_cli(project_name, lambda cli: cli.get_coordination_status())
    click.echo(json.dumps(status, indent=2))
