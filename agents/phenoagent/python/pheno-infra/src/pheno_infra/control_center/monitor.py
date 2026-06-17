"""Enhanced Multi-Project Monitor for Pheno Control Center.

Extends the existing KInfra monitor to group processes and resources by project
namespace and handle multiple concurrent projects in a unified display.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta

from ..monitoring import ServiceMonitor
from .config import ProjectRegistry
from .engine import LogEntry, MonitorEngine, ResourceState, ServiceState

try:
    from rich import box
    from rich.console import Console, Group
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table

    HAS_RICH = True
except ImportError:
    HAS_RICH = False

logger = logging.getLogger(__name__)


class MultiProjectMonitor:
    """Monitor that provides unified display of multiple pheno-sdk projects.

    Features:
    - Project-grouped process and resource display
    - Streaming logs with project categorization
    - Global status overview
    - Integration with existing KInfra monitors
    """

    def __init__(
        self,
        project_registry: ProjectRegistry,
        monitor_engine: MonitorEngine,
        refresh_interval: float = 2.0,
        enable_rich: bool = True,
    ):
        """
        Initialize enhanced multi-project monitor.
        """
        self.project_registry = project_registry
        self.monitor_engine = monitor_engine
        self.refresh_interval = refresh_interval
        self.enable_rich = enable_rich and HAS_RICH

        # Console for output
        self.console = Console() if self.enable_rich else None

        # Individual project monitors
        self.project_monitors: dict[str, ServiceMonitor] = {}

        # Start time for uptime calculation
        self.start_time = time.time()

        # Shutdown flag
        self._shutdown = False

        # Subscribe to monitor engine events
        self.monitor_engine.subscribe_to_events(self._handle_monitor_event)

        logger.info("Enhanced multi-project monitor initialized")

    def _handle_monitor_event(self, event_type: str, event_data: dict) -> None:
        """
        Handle events from the monitor engine.
        """
        if event_type == "log_entry":
            # Log events are handled automatically by the engine
            pass
        elif event_type in ["process_added", "process_removed", "process_state_changed"]:
            # Process state changes could trigger UI updates
            pass
        elif event_type in ["resource_added", "resource_state_changed"]:
            # Resource state changes
            pass

    def attach_project_monitor(self, project_name: str, monitor: ServiceMonitor) -> None:
        """
        Attach an existing project monitor.
        """
        self.project_monitors[project_name] = monitor
        logger.debug(f"Attached project monitor for: {project_name}")

    def detach_project_monitor(self, project_name: str) -> None:
        """
        Detach a project monitor.
        """
        if project_name in self.project_monitors:
            del self.project_monitors[project_name]
            logger.debug(f"Detached project monitor for: {project_name}")

    async def run(self) -> None:
        """
        Run the enhanced monitor (blocking until shutdown).
        """
        if not self.enable_rich:
            await self._run_simple()
            return

        logger.info("Starting enhanced multi-project monitor")

        try:
            with Live(
                self._make_monitor_panel(),
                console=self.console,
                refresh_per_second=1.0 / self.refresh_interval,
                screen=False,  # Allow logs to scroll above
            ) as live:
                while not self._shutdown:
                    await asyncio.sleep(self.refresh_interval)

                    # Update the display
                    live.update(self._make_monitor_panel())

        except KeyboardInterrupt:
            self.console.print("\n[yellow]👋 Shutting down monitor...[/yellow]")
            self._shutdown = True
        except Exception as e:
            logger.exception(f"Monitor error: {e}")
            raise

    async def _run_simple(self) -> None:
        """
        Fallback simple monitoring without Rich.
        """
        logger.info("Running simple multi-project monitor")

        while not self._shutdown:
            print("\n" + "=" * 80)
            print("PHENO CONTROL CENTER - Multi-Project Status")
            print("=" * 80)

            global_status = self.monitor_engine.get_global_status()

            print(
                f"Projects: {global_status['summary']['healthy_projects']}/{global_status['summary']['total_projects']} healthy",
            )
            print(
                f"Processes: {global_status['summary']['running_processes']}/{global_status['summary']['total_processes']} running",
            )

            for project_name, project_status in global_status["projects"].items():
                print(f"\n[{project_name.upper()}]")
                print(f"  State: {project_status['overall_state']}")
                print(
                    f"  Processes: {project_status['processes']['running']}/{project_status['processes']['total']}",
                )
                print(
                    f"  Resources: {project_status['resources']['available']}/{project_status['resources']['total']}",
                )

                for process_name, state in project_status["processes"]["details"].items():
                    print(f"    {process_name}: {state}")

            print("=" * 80)

            await asyncio.sleep(5.0)

    def _make_monitor_panel(self) -> Panel:
        """
        Create the Rich monitor panel.
        """
        uptime = timedelta(seconds=int(time.time() - self.start_time))
        header = f"[bold cyan]Pheno Control Center[/bold cyan] | Uptime: {uptime}"

        # Get global status
        global_status = self.monitor_engine.get_global_status()

        # Create summary table
        summary_table = Table(show_header=False, box=None, expand=True)
        summary_table.add_column("Metric", style="bold")
        summary_table.add_column("Value")

        summary = global_status["summary"]
        summary_table.add_row(
            "Projects",
            f"[green]{summary['healthy_projects']}[/green]/{summary['total_projects']} healthy",
        )
        summary_table.add_row(
            "Processes",
            f"[green]{summary['running_processes']}[/green]/{summary['total_processes']} running",
        )

        # Create per-project panels
        project_panels = []

        for project_name in self.project_registry.list_projects():
            project_panel = self._make_project_panel(project_name)
            if project_panel:
                project_panels.append(project_panel)

        # If no projects, show placeholder
        if not project_panels:
            project_panels = [
                Panel("[dim]No projects registered[/dim]", title="Projects", box=box.ROUNDED),
            ]

        # Combine into main panel
        content = Group(
            Panel(summary_table, title="[bold]Summary[/bold]", box=box.ROUNDED), *project_panels,
        )

        return Panel(content, title=header, box=box.DOUBLE, border_style="cyan")

    def _make_project_panel(self, project_name: str) -> Panel | None:
        """
        Create a panel for a specific project.
        """
        project_status = self.monitor_engine.get_project_status(project_name)

        if project_status["processes"]["total"] == 0 and project_status["resources"]["total"] == 0:
            # Skip empty projects
            return None

        # Project header with status
        state_colors = {
            "healthy": "green",
            "degraded": "yellow",
            "down": "red",
            "no_processes": "dim",
        }
        state_color = state_colors.get(project_status["overall_state"], "white")

        project_title = f"[bold]{project_name.upper()}[/bold] [{state_color}]({project_status['overall_state']})[/{state_color}]"

        # Process table
        process_table = Table(show_header=True, box=None, expand=True, padding=(0, 1))
        process_table.add_column("Process", style="bold")
        process_table.add_column("State")
        process_table.add_column("PID")
        process_table.add_column("Port")
        process_table.add_column("Tunnel")

        processes = self.monitor_engine.get_project_processes(project_name)
        for process_name, process_info in processes.items():
            # State formatting
            state_styles = {
                ServiceState.RUNNING: "[green]● Running[/green]",
                ServiceState.STARTING: "[yellow]◐ Starting[/yellow]",
                ServiceState.STOPPING: "[yellow]◐ Stopping[/yellow]",
                ServiceState.STOPPED: "[red]✗ Stopped[/red]",
                ServiceState.ERROR: "[red]✗ Error[/red]",
                ServiceState.UNKNOWN: "[dim]○ Unknown[/dim]",
            }
            state_display = state_styles.get(process_info.state, str(process_info.state.value))

            pid_display = str(process_info.pid) if process_info.pid else "-"
            port_display = str(process_info.port) if process_info.port else "-"

            # Tunnel status
            tunnel_display = "-"
            if process_info.tunnel_url:
                tunnel_display = "[green]✓[/green]"

            process_table.add_row(
                process_name, state_display, pid_display, port_display, tunnel_display,
            )

        # Resource table
        resource_table = Table(show_header=True, box=None, expand=True, padding=(0, 1))
        resource_table.add_column("Resource", style="bold")
        resource_table.add_column("State")
        resource_table.add_column("Endpoint")

        resources = self.monitor_engine.get_project_resources(project_name)
        for resource_name, resource_info in resources.items():
            # State formatting
            state_styles = {
                ResourceState.AVAILABLE: "[green]● Available[/green]",
                ResourceState.UNAVAILABLE: "[red]✗ Unavailable[/red]",
                ResourceState.DEGRADED: "[yellow]◐ Degraded[/yellow]",
                ResourceState.UNKNOWN: "[dim]○ Unknown[/dim]",
            }
            state_display = state_styles.get(resource_info.state, str(resource_info.state.value))

            if not resource_info.required and resource_info.state == ResourceState.UNAVAILABLE:
                state_display = "[yellow]○ Optional[/yellow]"

            endpoint = resource_info.endpoint or "-"

            resource_table.add_row(resource_name, state_display, endpoint)

        # Endpoints section
        endpoints_text = ""
        tunnels = self.monitor_engine.get_project_processes(project_name)
        for process_name, process_info in tunnels.items():
            if process_info.port:
                local_url = f"http://localhost:{process_info.port}"
                local_status = "✓" if process_info.state == ServiceState.RUNNING else "✗"
                local_color = "green" if local_status == "✓" else "red"
                endpoints_text += (
                    f"\n  Local:  [{local_color}]{local_status}[/{local_color}] {local_url}"
                )

            if process_info.tunnel_url:
                tunnel_status = "✓" if process_info.state == ServiceState.RUNNING else "✗"
                tunnel_color = "green" if tunnel_status == "✓" else "yellow"
                endpoints_text += f"\n  Public: [{tunnel_color}]{tunnel_status}[/{tunnel_color}] {process_info.tunnel_url}"

        if not endpoints_text:
            endpoints_text = "[dim]No endpoints available[/dim]"

        # Combine tables
        tables = []
        if processes:
            tables.append(Panel(process_table, title="[bold]Processes[/bold]", box=box.ROUNDED))
        if resources:
            tables.append(Panel(resource_table, title="[bold]Resources[/bold]", box=box.ROUNDED))
        if endpoints_text.strip():
            tables.append(
                Panel(endpoints_text.strip(), title="[bold]Endpoints[/bold]", box=box.ROUNDED),
            )

        if not tables:
            return None

        content = Group(*tables)
        return Panel(content, title=project_title, box=box.ROUNDED)

    def add_log_entry(
        self, project: str, process: str, level: str, message: str, metadata: dict | None = None,
    ) -> None:
        """
        Add a log entry to the monitor.
        """
        entry = LogEntry(
            timestamp=datetime.now(),
            project=project,
            process=process,
            level=level,
            message=message,
            metadata=metadata or {},
        )

        self.monitor_engine.log_entry(entry)

        # Also emit to console if Rich is available
        if self.console:
            timestamp = entry.timestamp.strftime("%H:%M:%S")

            # Color based on level
            level_colors = {
                "stdout": "cyan",
                "stderr": "red",
                "info": "blue",
                "warn": "yellow",
                "error": "red",
            }
            color = level_colors.get(level.lower(), "white")

            self.console.print(
                f"[dim]{timestamp}[/dim] [{color}][{project}.{process}][/{color}] {message}",
            )

    def stop(self) -> None:
        """
        Stop the monitor.
        """
        self._shutdown = True
        logger.info("Enhanced multi-project monitor stopped")


# Alias for backward compatibility
EnhancedMultiProjectMonitor = MultiProjectMonitor
