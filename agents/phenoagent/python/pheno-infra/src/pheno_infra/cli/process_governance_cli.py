"""
Process Governance CLI - Commands for process and tunnel governance

Provides comprehensive CLI commands for:
- Process management with metadata
- Tunnel lifecycle management
- Cleanup policy configuration
- Status monitoring and reporting
"""

import json
import logging
from pathlib import Path

import click
from tabulate import tabulate

from ..cleanup_policies import (
    CleanupPolicyManager,
    CleanupRule,
    CleanupStrategy,
    ResourceType,
)
from ..fallback_site.status_pages import StatusPageManager
from ..process_governance import (
    ProcessGovernanceManager,
    ProcessMetadata,
)
from ..tunnel_governance import (
    TunnelGovernanceManager,
)
from .progress import progress_step

logger = logging.getLogger(__name__)


class ProcessGovernanceCLI:
    """
    CLI for process and tunnel governance management.
    """

    def __init__(self, config_dir: Path | None = None):
        """Initialize process governance CLI.

        Args:
            config_dir: Configuration directory
        """
        self.process_manager = ProcessGovernanceManager()
        self.tunnel_manager = TunnelGovernanceManager(config_dir=config_dir)
        self.cleanup_manager = CleanupPolicyManager(config_dir=config_dir)
        self.status_manager = StatusPageManager()

    def create_process_metadata(
        self,
        project: str,
        service: str,
        pid: int,
        command_line: list[str],
        environment: dict[str, str],
        scope: str = "local",
        resource_type: str = "process",
        tags: list[str] | None = None,
    ) -> ProcessMetadata:
        """
        Create process metadata.

        Args:
            project: Project name
            service: Service name
            pid: Process ID
            command_line: Command line arguments
            environment: Environment variables
            scope: Process scope
            resource_type: Resource type
            tags: Additional tags

        Returns:
            Process metadata
        """
        return ProcessMetadata(
            project=project,
            service=service,
            pid=pid,
            command_line=command_line,
            environment=environment,
            scope=scope,
            resource_type=resource_type,
            tags=set(tags or []),
        )


# CLI Commands


@click.group()
@click.option("--config-dir", type=click.Path(), help="Configuration directory")
@click.pass_context
def process_governance_cli(ctx: click.Context, config_dir: str | None):
    """Process and tunnel governance management CLI."""
    ctx.ensure_object(dict)
    ctx.obj["cli"] = ProcessGovernanceCLI(Path(config_dir) if config_dir else None)


@process_governance_cli.group()
def process():
    """Process management commands."""


@process.command()
@click.argument("project_name")
@click.argument("service_name")
@click.argument("pid", type=int)
@click.option("--command-line", help="Command line arguments (JSON)")
@click.option("--environment", help="Environment variables (JSON)")
@click.option("--scope", default="local", help="Process scope")
@click.option("--resource-type", default="process", help="Resource type")
@click.option("--tags", help="Additional tags (comma-separated)")
@click.pass_context
def register(
    ctx: click.Context,
    project_name: str,
    service_name: str,
    pid: int,
    command_line: str | None,
    environment: str | None,
    scope: str,
    resource_type: str,
    tags: str | None,
):
    """Register a process with metadata."""
    cli = ctx.obj["cli"]

    # Parse command line
    cmd_line = []
    if command_line:
        try:
            cmd_line = json.loads(command_line)
        except json.JSONDecodeError:
            click.echo("✗ Invalid JSON for command line")
            ctx.exit(1)

    # Parse environment
    env = {}
    if environment:
        try:
            env = json.loads(environment)
        except json.JSONDecodeError:
            click.echo("✗ Invalid JSON for environment")
            ctx.exit(1)

    # Parse tags
    tag_list = []
    if tags:
        tag_list = [tag.strip() for tag in tags.split(",")]

    # Create metadata
    metadata = cli.create_process_metadata(
        project=project_name,
        service=service_name,
        pid=pid,
        command_line=cmd_line,
        environment=env,
        scope=scope,
        resource_type=resource_type,
        tags=tag_list,
    )

    # Register process
    with progress_step(f"Registering process {pid} for {project_name}:{service_name}") as step:
        cli.process_manager.register_process(pid, metadata)
        step.succeed(f"Process {pid} registered")

    click.echo(f"✓ Registered process {pid} for {project_name}:{service_name}")


@process.command()
@click.argument("pid", type=int)
@click.pass_context
def unregister(ctx: click.Context, pid: int):
    """Unregister a process."""
    cli = ctx.obj["cli"]

    with progress_step(f"Unregistering process {pid}") as step:
        cli.process_manager.unregister_process(pid)
        step.succeed(f"Process {pid} unregistered")
    click.echo(f"✓ Unregistered process {pid}")


@process.command()
@click.argument("project_name")
@click.option("--force", is_flag=True, help="Force cleanup even if conservative policy")
@click.pass_context
def cleanup_project(ctx: click.Context, project_name: str, force: bool):
    """Clean up all processes for a project."""
    cli = ctx.obj["cli"]

    stats = {}
    with progress_step(f"Cleaning processes for project '{project_name}'") as step:
        stats = cli.process_manager.cleanup_project_processes(project_name, force=force)
        if stats.get("errors"):
            step.fail(f"Cleanup finished with {stats['errors']} errors")
        else:
            step.succeed("Process cleanup complete")

    click.echo(f"✓ Cleaned up processes for project '{project_name}'")
    click.echo(f"  Inspected: {stats['inspected']}")
    click.echo(f"  Terminated: {stats['terminated']}")
    click.echo(f"  Force killed: {stats['force_killed']}")
    click.echo(f"  Skipped: {stats['skipped']}")
    click.echo(f"  Errors: {stats['errors']}")


@process.command()
@click.argument("service_name")
@click.option("--force", is_flag=True, help="Force cleanup even if conservative policy")
@click.pass_context
def cleanup_service(ctx: click.Context, service_name: str, force: bool):
    """Clean up all processes for a service."""
    cli = ctx.obj["cli"]

    stats = {}
    with progress_step(f"Cleaning processes for service '{service_name}'") as step:
        stats = cli.process_manager.cleanup_service_processes(service_name, force=force)
        if stats.get("errors"):
            step.fail(f"Cleanup finished with {stats['errors']} errors")
        else:
            step.succeed("Process cleanup complete")

    click.echo(f"✓ Cleaned up processes for service '{service_name}'")
    click.echo(f"  Inspected: {stats['inspected']}")
    click.echo(f"  Terminated: {stats['terminated']}")
    click.echo(f"  Force killed: {stats['force_killed']}")
    click.echo(f"  Skipped: {stats['skipped']}")
    click.echo(f"  Errors: {stats['errors']}")


@process.command()
@click.option("--max-age", type=float, help="Maximum age for processes in seconds")
@click.pass_context
def cleanup_stale(ctx: click.Context, max_age: float | None):
    """Clean up stale processes."""
    cli = ctx.obj["cli"]

    stats = {}
    with progress_step("Cleaning stale processes") as step:
        stats = cli.process_manager.cleanup_stale_processes(max_age)
        if stats.get("errors"):
            step.fail(f"Cleanup finished with {stats['errors']} errors")
        else:
            step.succeed("Stale process cleanup complete")

    click.echo("✓ Cleaned up stale processes")
    click.echo(f"  Inspected: {stats['inspected']}")
    click.echo(f"  Terminated: {stats['terminated']}")
    click.echo(f"  Force killed: {stats['force_killed']}")
    click.echo(f"  Skipped: {stats['skipped']}")
    click.echo(f"  Errors: {stats['errors']}")


@process.command()
@click.argument("project_name")
@click.pass_context
def list_project(ctx: click.Context, project_name: str):
    """List all processes for a project."""
    cli = ctx.obj["cli"]

    processes = cli.process_manager.get_project_processes(project_name)

    if not processes:
        click.echo(f"No processes found for project '{project_name}'")
        return

    # Create table
    headers = ["PID", "Service", "Status", "Scope", "Resource Type", "Uptime"]
    rows = []

    for process in processes:
        rows.append(
            [
                process.pid or "N/A",
                process.service or "N/A",
                "Running" if process.pid else "Unknown",
                process.scope or "N/A",
                process.resource_type or "N/A",
                f"{process.uptime:.1f}s" if process.uptime else "N/A",
            ],
        )

    click.echo(tabulate(rows, headers=headers, tablefmt="grid"))


@process.command()
@click.argument("service_name")
@click.pass_context
def list_service(ctx: click.Context, service_name: str):
    """List all processes for a service."""
    cli = ctx.obj["cli"]

    processes = cli.process_manager.get_service_processes(service_name)

    if not processes:
        click.echo(f"No processes found for service '{service_name}'")
        return

    # Create table
    headers = ["PID", "Project", "Status", "Scope", "Resource Type", "Uptime"]
    rows = []

    for process in processes:
        rows.append(
            [
                process.pid or "N/A",
                process.project or "N/A",
                "Running" if process.pid else "Unknown",
                process.scope or "N/A",
                process.resource_type or "N/A",
                f"{process.uptime:.1f}s" if process.uptime else "N/A",
            ],
        )

    click.echo(tabulate(rows, headers=headers, tablefmt="grid"))


@process_governance_cli.group()
def tunnel():
    """Tunnel management commands."""


@tunnel.command()
@click.argument("project_name")
@click.argument("service_name")
@click.argument("port", type=int)
@click.option("--provider", default="cloudflare", help="Tunnel provider")
@click.option("--hostname", help="Tunnel hostname")
@click.option("--reuse", is_flag=True, help="Reuse existing tunnel")
@click.pass_context
def create(
    ctx: click.Context,
    project_name: str,
    service_name: str,
    port: int,
    provider: str,
    hostname: str | None,
    reuse: bool,
):
    """Create a tunnel for a service."""
    cli = ctx.obj["cli"]

    with progress_step(f"Creating tunnel for {project_name}:{service_name}") as step:
        tunnel_info = cli.tunnel_manager.create_tunnel(
            project=project_name,
            service=service_name,
            port=port,
            provider=provider,
            hostname=hostname,
            reuse_existing=reuse,
        )
        step.succeed(f"Tunnel {tunnel_info.tunnel_id} ready")

    click.echo(f"✓ Created tunnel {tunnel_info.tunnel_id}")
    click.echo(f"  Project: {tunnel_info.project}")
    click.echo(f"  Service: {tunnel_info.service}")
    click.echo(f"  Hostname: {tunnel_info.hostname}")
    click.echo(f"  Port: {tunnel_info.port}")
    click.echo(f"  Provider: {tunnel_info.provider}")
    click.echo(f"  Status: {tunnel_info.status}")


@tunnel.command()
@click.argument("tunnel_id")
@click.pass_context
def stop(ctx: click.Context, tunnel_id: str):
    """Stop a tunnel."""
    cli = ctx.obj["cli"]

    success = False
    with progress_step(f"Stopping tunnel {tunnel_id}") as step:
        success = cli.tunnel_manager.stop_tunnel(tunnel_id)
        if success:
            step.succeed(f"Tunnel {tunnel_id} stopped")
        else:
            step.fail(f"Failed to stop tunnel {tunnel_id}")

    if success:
        click.echo(f"✓ Stopped tunnel {tunnel_id}")
    else:
        click.echo(f"✗ Failed to stop tunnel {tunnel_id}")
        ctx.exit(1)


@tunnel.command()
@click.argument("tunnel_id")
@click.pass_context
def cleanup(ctx: click.Context, tunnel_id: str):
    """Clean up a tunnel completely."""
    cli = ctx.obj["cli"]

    success = False
    with progress_step(f"Cleaning up tunnel {tunnel_id}") as step:
        success = cli.tunnel_manager.cleanup_tunnel(tunnel_id)
        if success:
            step.succeed(f"Tunnel {tunnel_id} removed")
        else:
            step.fail(f"Failed to clean up tunnel {tunnel_id}")

    if success:
        click.echo(f"✓ Cleaned up tunnel {tunnel_id}")
    else:
        click.echo(f"✗ Failed to clean up tunnel {tunnel_id}")
        ctx.exit(1)


@tunnel.command()
@click.argument("project_name")
@click.pass_context
def cleanup_project(ctx: click.Context, project_name: str):
    """Clean up all tunnels for a project."""
    cli = ctx.obj["cli"]

    with progress_step(f"Cleaning tunnels for project '{project_name}'") as step:
        cleaned_up = cli.tunnel_manager.cleanup_project_tunnels(project_name)
        step.succeed(f"{cleaned_up} tunnel(s) cleaned")

    click.echo(f"✓ Cleaned up {cleaned_up} tunnels for project '{project_name}'")


@tunnel.command()
@click.argument("project_name")
@click.pass_context
def list_project(ctx: click.Context, project_name: str):
    """List all tunnels for a project."""
    cli = ctx.obj["cli"]

    tunnels = cli.tunnel_manager.get_project_tunnels(project_name)

    if not tunnels:
        click.echo(f"No tunnels found for project '{project_name}'")
        return

    # Create table
    headers = ["Tunnel ID", "Service", "Hostname", "Port", "Provider", "Status"]
    rows = []

    for tunnel in tunnels:
        rows.append(
            [
                tunnel.tunnel_id,
                tunnel.service_name,
                tunnel.hostname,
                tunnel.port,
                tunnel.provider,
                tunnel.status,
            ],
        )

    click.echo(tabulate(rows, headers=headers, tablefmt="grid"))


@tunnel.command()
@click.argument("project_name")
@click.argument("service_name")
@click.argument("provider")
@click.argument("credentials_file", type=click.Path(exists=True))
@click.pass_context
def set_credentials(
    ctx: click.Context,
    project_name: str,
    service_name: str,
    provider: str,
    credentials_file: str,
):
    """Set credentials for a project/service."""
    cli = ctx.obj["cli"]

    # Load credentials from file
    with open(credentials_file) as f:
        credentials = json.load(f)

    with progress_step(f"Setting credentials for {project_name}:{service_name}") as step:
        credential_id = cli.tunnel_manager.set_credentials(
            project=project_name,
            service=service_name,
            provider=provider,
            credentials=credentials,
        )
        step.succeed(f"Credentials stored for {credential_id}")

    click.echo(f"✓ Set credentials for {credential_id}")


@process_governance_cli.group()
def cleanup():
    """Cleanup policy management commands."""


@cleanup.command()
@click.argument("project_name")
@click.option(
    "--strategy",
    type=click.Choice(["conservative", "moderate", "aggressive"]),
    default="moderate",
    help="Cleanup strategy",
)
@click.pass_context
def init_project(ctx: click.Context, project_name: str, strategy: str):
    """Initialize cleanup policy for a project."""
    cli = ctx.obj["cli"]

    from ..cleanup_policies import CleanupStrategy

    strategy_enum = CleanupStrategy(strategy)

    with progress_step(f"Initializing cleanup policy for '{project_name}'") as step:
        policy = cli.cleanup_manager.create_default_policy(project_name, strategy_enum)
        step.succeed("Cleanup policy created")

    click.echo(f"✓ Initialized cleanup policy for project '{project_name}'")
    click.echo(f"  Strategy: {policy.global_strategy.value}")
    click.echo(f"  Rules: {len(policy.rules)}")


@cleanup.command()
@click.argument("project_name")
@click.argument("resource_type")
@click.option(
    "--strategy",
    type=click.Choice(["conservative", "moderate", "aggressive"]),
    help="Cleanup strategy",
)
@click.option("--patterns", help="Patterns to match (comma-separated)")
@click.option("--exclude-patterns", help="Patterns to exclude (comma-separated)")
@click.option("--max-age", type=float, help="Maximum age in seconds")
@click.option("--force", is_flag=True, help="Force cleanup")
@click.option("--enabled/--disabled", default=True, help="Enable/disable rule")
@click.pass_context
def set_rule(
    ctx: click.Context,
    project_name: str,
    resource_type: str,
    strategy: str | None,
    patterns: str | None,
    exclude_patterns: str | None,
    max_age: float | None,
    force: bool,
    enabled: bool,
):
    """Set cleanup rule for a project and resource type."""
    cli = ctx.obj["cli"]

    # Parse resource type
    try:
        resource_type_enum = ResourceType(resource_type)
    except ValueError:
        click.echo(f"✗ Invalid resource type: {resource_type}")
        ctx.exit(1)

    # Parse strategy
    strategy_enum = None
    if strategy:
        try:
            strategy_enum = CleanupStrategy(strategy)
        except ValueError:
            click.echo(f"✗ Invalid strategy: {strategy}")
            ctx.exit(1)

    # Parse patterns
    pattern_list = []
    if patterns:
        pattern_list = [p.strip() for p in patterns.split(",")]

    exclude_list = []
    if exclude_patterns:
        exclude_list = [p.strip() for p in exclude_patterns.split(",")]

    # Create rule
    rule = CleanupRule(
        resource_type=resource_type_enum,
        strategy=strategy_enum or CleanupStrategy.MODERATE,
        patterns=pattern_list,
        exclude_patterns=exclude_list,
        max_age=max_age,
        force_cleanup=force,
        enabled=enabled,
    )

    # Update rule
    with progress_step(f"Updating {resource_type} cleanup rule for '{project_name}'") as step:
        cli.cleanup_manager.update_project_rule(project_name, resource_type_enum, rule)
        step.succeed("Cleanup rule updated")

    click.echo(f"✓ Updated {resource_type} cleanup rule for project '{project_name}'")


@cleanup.command()
@click.argument("project_name")
@click.pass_context
def show_policy(ctx: click.Context, project_name: str):
    """Show cleanup policy for a project."""
    cli = ctx.obj["cli"]

    policy = cli.cleanup_manager.get_project_policy(project_name)
    if not policy:
        click.echo(f"✗ No cleanup policy found for project '{project_name}'")
        ctx.exit(1)

    click.echo(f"Project: {policy.project_name}")
    click.echo(f"Strategy: {policy.global_strategy.value}")
    click.echo(f"Enabled: {policy.enabled}")
    click.echo(f"Created: {policy.created_at}")
    click.echo(f"Updated: {policy.updated_at}")
    click.echo()

    # Show rules
    if policy.rules:
        headers = [
            "Resource Type",
            "Strategy",
            "Patterns",
            "Exclude",
            "Max Age",
            "Force",
            "Enabled",
        ]
        rows = []

        for resource_type, rule in policy.rules.items():
            rows.append(
                [
                    resource_type.value,
                    rule.strategy.value,
                    ", ".join(rule.patterns) if rule.patterns else "None",
                    ", ".join(rule.exclude_patterns) if rule.exclude_patterns else "None",
                    f"{rule.max_age}s" if rule.max_age else "None",
                    "Yes" if rule.force_cleanup else "No",
                    "Yes" if rule.enabled else "No",
                ],
            )

        click.echo(tabulate(rows, headers=headers, tablefmt="grid"))
    else:
        click.echo("No rules configured")


@process_governance_cli.group()
def status():
    """Status monitoring commands."""


@status.command()
@click.argument("project_name")
@click.option("--format", type=click.Choice(["html", "json"]), default="html", help="Output format")
@click.pass_context
def show_project(ctx: click.Context, project_name: str, format: str):
    """Show status for a project."""
    cli = ctx.obj["cli"]

    if format == "html":
        page_content = cli.status_manager.generate_status_page(project_name, "status")
        click.echo(page_content)
    elif format == "json":
        summary = cli.status_manager.generate_project_summary(project_name)
        click.echo(json.dumps(summary, indent=2))
    else:
        click.echo(f"✗ Unsupported format: {format}")
        ctx.exit(1)


@status.command()
@click.pass_context
def list_projects(ctx: click.Context):
    """List all projects with status."""
    cli = ctx.obj["cli"]

    projects = cli.status_manager.get_all_projects()

    if not projects:
        click.echo("No projects found")
        return

    # Create table
    headers = ["Project Name", "Overall Status", "Services", "Tunnels", "Last Updated"]
    rows = []

    for project_name in projects:
        project_status = cli.status_manager.get_project_status(project_name)
        if project_status:
            rows.append(
                [
                    project_name,
                    project_status.overall_status,
                    len(project_status.services),
                    len(project_status.tunnels),
                    project_status.last_updated,
                ],
            )

    click.echo(tabulate(rows, headers=headers, tablefmt="grid"))


@process_governance_cli.command()
@click.pass_context
def stats(ctx: click.Context):
    """Show governance statistics."""
    cli = ctx.obj["cli"]

    # Process stats
    process_stats = cli.process_manager.get_cleanup_stats()

    # Tunnel stats
    tunnel_stats = cli.tunnel_manager.get_tunnel_stats()

    # Cleanup stats
    projects = cli.cleanup_manager.list_projects()

    click.echo("Process Governance Statistics")
    click.echo("=" * 40)
    click.echo(f"Processes inspected: {process_stats['inspected']}")
    click.echo(f"Processes terminated: {process_stats['terminated']}")
    click.echo(f"Processes force killed: {process_stats['force_killed']}")
    click.echo(f"Processes skipped: {process_stats['skipped']}")
    click.echo(f"Process errors: {process_stats['errors']}")
    click.echo()

    click.echo("Tunnel Governance Statistics")
    click.echo("=" * 40)
    click.echo(f"Total tunnels: {tunnel_stats['total_tunnels']}")
    click.echo(f"Active tunnels: {tunnel_stats['active_tunnels']}")
    click.echo(f"Tunnels created: {tunnel_stats['created']}")
    click.echo(f"Tunnels reused: {tunnel_stats['reused']}")
    click.echo(f"Tunnels cleaned up: {tunnel_stats['cleaned_up']}")
    click.echo(f"Projects: {tunnel_stats['projects']}")
    click.echo(f"Services: {tunnel_stats['services']}")
    click.echo(f"Credentials: {tunnel_stats['credentials']}")
    click.echo()

    click.echo("Cleanup Policy Statistics")
    click.echo("=" * 40)
    click.echo(f"Projects with policies: {len(projects)}")
    click.echo(f"Projects: {', '.join(projects) if projects else 'None'}")
