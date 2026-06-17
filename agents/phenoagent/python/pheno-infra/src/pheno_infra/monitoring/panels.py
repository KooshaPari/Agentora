"""
Reusable Rich panel components for service monitoring.
"""

from typing import Any

try:
    from rich import box
    from rich.panel import Panel
    from rich.table import Table

    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    Table = None
    Panel = None
    box = None


class ProcessPanel:
    """
    Panel showing process status.
    """

    @staticmethod
    def create(services: list[dict[str, Any]]) -> Panel | None:
        """Create a process status panel.

        Args:
            services: List of service dicts with keys: name, status, pid, port

        Returns:
            Rich Panel or None if Rich not available
        """
        if not HAS_RICH:
            return None

        table = Table(show_header=True, box=None, expand=True, padding=(0, 1))
        table.add_column("Process", style="bold")
        table.add_column("Status", style="bold")
        table.add_column("PID")
        table.add_column("Port")

        for service in services:
            name = service.get("name", "Unknown")
            status = service.get("status", "unknown")
            pid = str(service.get("pid", "-"))
            port = str(service.get("port", "-"))

            # Format status with color
            if status == "running":
                status_display = "[green]● Running[/green]"
            elif status == "stopped":
                status_display = "[red]✗ Stopped[/red]"
            else:
                status_display = "[dim]○ Unknown[/dim]"

            table.add_row(name, status_display, pid, port)

        return Panel(table, title="[bold]Processes[/bold]", box=box.ROUNDED)


class ResourcePanel:
    """
    Panel showing external resource availability.
    """

    @staticmethod
    def create(resources: list[dict[str, Any]]) -> Panel | None:
        """Create a resource availability panel.

        Args:
            resources: List of resource dicts with keys: name, available, endpoint, optional

        Returns:
            Rich Panel or None if Rich not available
        """
        if not HAS_RICH:
            return None

        table = Table(show_header=True, box=None, expand=True, padding=(0, 1))
        table.add_column("Resource", style="bold")
        table.add_column("Status", style="bold")
        table.add_column("Endpoint")

        for resource in resources:
            name = resource.get("name", "Unknown")
            available = resource.get("available", False)
            endpoint = resource.get("endpoint", "-")
            optional = resource.get("optional", True)

            # Format status with color
            if available:
                status = "[green]● Available[/green]"
            elif optional:
                status = "[yellow]○ Optional[/yellow]"
            else:
                status = "[red]✗ Unavailable[/red]"

            table.add_row(name, status, endpoint)

        return Panel(table, title="[bold]Resources[/bold]", box=box.ROUNDED)


class EndpointPanel:
    """
    Panel showing service endpoints.
    """

    @staticmethod
    def create(endpoints: list[dict[str, Any]]) -> Panel | None:
        """Create an endpoints panel.

        Args:
            endpoints: List of endpoint dicts with keys: label, url, healthy

        Returns:
            Rich Panel or None if Rich not available
        """
        if not HAS_RICH:
            return None

        content = ""
        for endpoint in endpoints:
            label = endpoint.get("label", "Endpoint")
            url = endpoint.get("url", "-")
            healthy = endpoint.get("healthy", False)

            health_indicator = "✓" if healthy else "✗"
            color = "green" if healthy else "red"

            content += f"\n  {label}: [{color}]{health_indicator}[/{color}] {url}"

        if not content:
            content = "[dim]No endpoints available[/dim]"

        return Panel(content.strip(), title="[bold]Endpoints[/bold]", box=box.ROUNDED)
