"""
Rich-based monitor rendering helpers.
"""

from __future__ import annotations

import asyncio
import time
from datetime import timedelta
from typing import TYPE_CHECKING

from .environment import (
    HAS_RICH,
    Align,
    Console,
    Group,
    Layout,
    Live,
    Panel,
    Table,
    box,
)

if TYPE_CHECKING:
    from .engine import MonitorEngine


def _require_rich() -> None:
    if not HAS_RICH:  # pragma: no cover - defensive
        raise RuntimeError("Rich is not available")


def _make_monitor_panel(engine: MonitorEngine) -> Panel:
    uptime = timedelta(seconds=int(time.time() - engine.start_time))
    header = f"[bold cyan]Pheno Control Center[/bold cyan] | Uptime: {uptime}"

    global_status = engine.get_global_status()

    summary_table = Table(show_header=False, box=None, expand=True)
    summary_table.add_row(
        "Projects",
        f"{global_status['summary']['healthy_projects']}/{global_status['summary']['total_projects']} healthy",
    )
    summary_table.add_row(
        "Processes",
        f"{global_status['summary']['running_processes']}/{global_status['summary']['total_processes']} running",
    )

    project_panels = []
    for project_name in engine.project_registry.list_projects():
        panel = _make_project_panel(engine, project_name)
        if panel is not None:
            project_panels.append(panel)

    if not project_panels:
        project_panels = [Panel("[dim]No active projects[/dim]", title="Projects", box=box.ROUNDED)]

    content = Group(
        Panel(summary_table, title="[bold]Summary[/bold]", box=box.ROUNDED),
        *project_panels,
    )
    return Panel(content, title=header, box=box.DOUBLE, border_style="cyan")


def _make_project_panel(engine: MonitorEngine, project_name: str) -> Panel | None:
    project_status = engine.get_project_status(project_name)

    if project_status["processes"]["total"] == 0 and project_status["resources"]["total"] == 0:
        return None

    state_colors = {
        "healthy": "green",
        "degraded": "yellow",
        "down": "red",
        "no_processes": "dim",
    }
    state_color = state_colors.get(project_status["overall_state"], "white")
    project_title = (
        f"[bold]{project_name.upper()}[/bold] "
        f"[{state_color}]({project_status['overall_state']})[/{state_color}]"
    )

    process_table = Table(show_header=True, box=None, expand=True, padding=(0, 1))
    process_table.add_column("Process", style="bold")
    process_table.add_column("State")
    process_table.add_column("PID")
    process_table.add_column("Port")
    process_table.add_column("Tunnel")

    processes = engine.get_project_processes(project_name)
    for process_name, process_info in processes.items():
        state_styles = {
            "running": "[green]● Running[/green]",
            "starting": "[yellow]◐ Starting[/yellow]",
            "stopping": "[yellow]◐ Stopping[/yellow]",
            "stopped": "[red]✗ Stopped[/red]",
            "error": "[red]✗ Error[/red]",
            "unknown": "[dim]○ Unknown[/dim]",
        }
        state_display = state_styles.get(process_info.state, process_info.state)

        pid_display = str(process_info.pid) if process_info.pid else "-"
        port_display = str(process_info.port) if process_info.port else "-"

        tunnel_display = "-"
        if process_info.tunnel_url:
            tunnel_display = "[green]✓[/green]"

        process_table.add_row(
            process_name,
            state_display,
            pid_display,
            port_display,
            tunnel_display,
        )

    resource_table = Table(show_header=True, box=None, expand=True, padding=(0, 1))
    resource_table.add_column("Resource", style="bold")
    resource_table.add_column("State")
    resource_table.add_column("Endpoint")

    resources = engine.get_project_resources(project_name)
    for resource_name, resource_info in resources.items():
        state_styles = {
            "available": "[green]● Available[/green]",
            "unavailable": "[red]✗ Unavailable[/red]",
            "degraded": "[yellow]◐ Degraded[/yellow]",
            "unknown": "[dim]○ Unknown[/dim]",
        }
        state_display = state_styles.get(resource_info.state, resource_info.state)

        if not resource_info.required and resource_info.state == "unavailable":
            state_display = "[yellow]○ Optional[/yellow]"

        endpoint = resource_info.endpoint or "-"

        resource_table.add_row(resource_name, state_display, endpoint)

    tunnels = engine.get_project_processes(project_name)
    endpoints_text = ""
    for process_name, process_info in tunnels.items():
        if process_info.port:
            local_url = f"http://localhost:{process_info.port}"
            local_status = "✓" if process_info.state == "running" else "✗"
            local_color = "green" if local_status == "✓" else "red"
            endpoints_text += (
                f"\n  Local:  [{local_color}]{local_status}[/{local_color}] {local_url}"
            )

        if process_info.tunnel_url:
            tunnel_status = "✓" if process_info.state == "running" else "✗"
            tunnel_color = "green" if tunnel_status == "✓" else "yellow"
            endpoints_text += (
                f"\n  Public: [{tunnel_color}]{tunnel_status}[/{tunnel_color}] "
                f"{process_info.tunnel_url}"
            )

    tables = []
    if processes:
        tables.append(Panel(process_table, title="[bold]Processes[/bold]", box=box.ROUNDED))
    if resources:
        tables.append(Panel(resource_table, title="[bold]Resources[/bold]", box=box.ROUNDED))
    if endpoints_text.strip():
        tables.append(
            Panel(
                endpoints_text.strip(),
                title="[bold]Endpoints[/bold]",
                box=box.ROUNDED,
            ),
        )

    if not tables:
        return None

    content = Group(*tables)
    return Panel(content, title=project_title, box=box.ROUNDED)


def _make_logs_panel(engine: MonitorEngine) -> Panel:
    logs = engine.get_logs(limit=20)

    log_text = ""
    for log_entry in logs[-10:]:
        timestamp = log_entry.timestamp.strftime("%H:%M:%S")
        project_process = f"{log_entry.project}.{log_entry.process}"

        level_colors = {
            "stdout": "cyan",
            "stderr": "red",
            "info": "blue",
            "warn": "yellow",
            "error": "red",
        }
        color = level_colors.get(log_entry.level, "white")

        log_text += (
            f"[dim]{timestamp}[/dim] [{color}]{project_process}[/{color}] {log_entry.message}\n"
        )

    if not log_text:
        log_text = "[dim]No recent logs[/dim]"

    return Panel(log_text.strip(), title="[bold]Recent Logs[/bold]", box=box.ROUNDED)


async def run_rich_monitor(
    engine: MonitorEngine, console: Console, refresh_interval: float,
) -> None:
    """
    Run the Rich-based monitor until shutdown.
    """
    _require_rich()

    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main"),
        Layout(name="input", size=3),
    )
    layout["main"].split_row(
        Layout(name="status", ratio=2),
        Layout(name="logs", ratio=1),
    )

    current_input = ""

    with Live(layout, console=console, screen=True):
        while True:
            layout["header"].update(
                Panel(
                    Align.center("[bold cyan]Pheno Control Center - TUI Monitor[/bold cyan]"),
                    box=box.ROUNDED,
                ),
            )
            layout["status"].update(_make_monitor_panel(engine))
            layout["logs"].update(_make_logs_panel(engine))
            layout["input"].update(
                Panel(f"Command: {current_input}_", title="Input", box=box.ROUNDED),
            )

            await asyncio.sleep(refresh_interval)


__all__ = ["run_rich_monitor"]
