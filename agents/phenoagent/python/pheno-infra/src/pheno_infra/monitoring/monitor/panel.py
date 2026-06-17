"""
Rich TUI panel builder for the service monitor.
"""

from __future__ import annotations

import time
from datetime import timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import MonitorConfig
    from .process import ProcessInspector

try:  # pragma: no cover - optional dependency
    from rich import box
    from rich.console import Group
    from rich.panel import Panel
    from rich.table import Table
except ImportError:  # pragma: no cover - emitted when Rich is missing
    box = Group = Panel = Table = None  # type: ignore


def build_status_panel(
    config: MonitorConfig,
    inspector: ProcessInspector,
    processes: dict[str, object],
    ports: dict[str, int],
    tunnel_urls: dict[str, str],
    start_time: float,
) -> Panel:
    """
    Construct the Rich panel describing current service/resource status.
    """
    if Panel is None or Table is None or Group is None or box is None:
        raise RuntimeError("Rich is not available for panel rendering")

    uptime = timedelta(seconds=int(time.time() - start_time))
    header = f"[bold cyan]{config.project_name} Monitor[/bold cyan] | Uptime: {uptime}"

    process_table = Table(show_header=True, box=None, expand=True, padding=(0, 1))
    process_table.add_column("Process", style="bold")
    process_table.add_column("Status", style="bold")
    process_table.add_column("PID")
    process_table.add_column("Port")

    for service_name in config.services:
        process = processes.get(service_name)
        running = inspector.is_running(service_name, process)
        pid_value = inspector.get_pid(service_name, process)
        status = "[green]● Running[/green]" if running else "[red]✗ Stopped[/red]"
        pid = str(pid_value) if pid_value is not None else "-"
        port_value = ports.get(service_name)
        port = str(port_value) if port_value is not None else "-"
        process_table.add_row(service_name, status, pid, port)

    if any(tunnel_urls.values()):
        unique_ports = sorted(
            {ports.get(service_name) for service_name in tunnel_urls if ports.get(service_name)},
        )
        unique_ports = [port for port in unique_ports if port is not None]

        pid_values = []
        for port in unique_ports:
            if port is None:
                continue
            pid = inspector.cloudflared_pid_for_port(port)
            if pid:
                pid_values.append(pid)

        if pid_values:
            tunnel_status = "[green]● Running[/green]"
        elif unique_ports:
            tunnel_status = "[yellow]○ Starting[/yellow]"
        else:
            tunnel_status = "[dim]○ Not started[/dim]"

        pid_text = ", ".join(str(pid) for pid in sorted(set(pid_values))) if pid_values else "-"
        port_text = ", ".join(str(port) for port in unique_ports) if unique_ports else "-"
        process_table.add_row("cloudflare-tunnel", tunnel_status, pid_text, port_text)

    resource_table = Table(show_header=True, box=None, expand=True, padding=(0, 1))
    resource_table.add_column("Resource", style="bold")
    resource_table.add_column("Status", style="bold")
    resource_table.add_column("Endpoint")

    for resource in config.resources:
        name = resource.get("name", "Unknown")
        port = resource.get("port")
        host = resource.get("host", "localhost")
        optional = resource.get("optional", True)

        if port:
            available = inspector.check_port(port, host)
            if available:
                status = "[green]● Available[/green]"
            else:
                status = "[yellow]○ Optional[/yellow]" if optional else "[red]✗ Unavailable[/red]"
            endpoint = f"{host}:{port}"
        else:
            status = "[dim]○ N/A[/dim]"
            endpoint = "-"

        resource_table.add_row(name, status, endpoint)

    endpoints_lines: list[str] = []
    for service_name in config.services:
        port = ports.get(service_name)
        tunnel_url = tunnel_urls.get(service_name)

        if port:
            local_url = f"http://localhost:{port}"
            local_health = inspector.check_port(port)
            color = "green" if local_health else "red"
            status_symbol = "✓" if local_health else "✗"
            endpoints_lines.append(f"  Local:  [{color}]{status_symbol}[/{color}] {local_url}")

        if tunnel_url:
            tunnel_ok = bool(port and inspector.check_port(port))
            color = "green" if tunnel_ok else "yellow"
            status_symbol = "✓" if tunnel_ok else "✗"
            endpoints_lines.append(f"  Public: [{color}]{status_symbol}[/{color}] {tunnel_url}")

    endpoints_text = (
        "\n".join(endpoints_lines) if endpoints_lines else "[dim]No endpoints available[/dim]"
    )

    content = Group(
        Panel(process_table, title="[bold]Processes[/bold]", box=box.ROUNDED),
        Panel(resource_table, title="[bold]Resources[/bold]", box=box.ROUNDED),
        Panel(endpoints_text, title="[bold]Endpoints[/bold]", box=box.ROUNDED),
    )

    return Panel(content, title=header, box=box.DOUBLE, border_style="cyan")


__all__ = ["build_status_panel"]
