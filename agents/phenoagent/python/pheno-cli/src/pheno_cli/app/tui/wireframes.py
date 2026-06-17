"""
TUI Wireframes - Pre-built layouts and structured interfaces.

Provides ready-to-use wireframe templates that can be populated with
content and configured for different contexts and operations.
"""

from collections.abc import Callable
from enum import Enum
from pathlib import Path
from typing import Any

try:
    from rich.panel import Panel
    from rich.table import Table
    from textual.app import App, ComposeResult
    from textual.containers import Container, Grid, Horizontal, Vertical
    from textual.reactive import reactive
    from textual.screen import Screen
    from textual.widgets import (
        Button,
        DataTable,
        Footer,
        Header,
        Log,
        ProgressBar,
        Static,
        TabbedContent,
        TabPane,
        Tree,
    )

    HAS_TEXTUAL = True
except ImportError:
    HAS_TEXTUAL = False
    # Fallback stubs for when textual is not available
    App = Screen = Container = Static = object


class WireframeStyle(Enum):
    """
    Predefined wireframe styles.
    """

    MINIMAL = "minimal"
    DASHBOARD = "dashboard"
    WIZARD = "wizard"
    MONITOR = "monitor"
    FORM = "form"


class BaseWireframe(Screen if HAS_TEXTUAL else object):
    """
    Base wireframe with common layout patterns.
    """

    def __init__(
        self,
        title: str = "Pheno CLI",
        context: str = "pheno",
        style: WireframeStyle = WireframeStyle.MINIMAL,
        **kwargs,
    ):
        if HAS_TEXTUAL:
            super().__init__(**kwargs)
        self.title = title
        self.context = context
        self.style = style
        self._content_widgets = []
        self._actions = {}

    def add_content(self, widget: Any) -> None:
        """
        Add content widget to wireframe.
        """
        self._content_widgets.append(widget)

    def add_action(self, key: str, callback: Callable, description: str = "") -> None:
        """
        Add keyboard action to wireframe.
        """
        self._actions[key] = {"callback": callback, "description": description}

    def get_header_content(self) -> str:
        """
        Get header content with context info.
        """
        context_info = {
            "atoms": "⚛️  Atoms FastMCP Server",
            "zen": "🧘 Zen MCP Server",
            "byteport": "🚢 BytePort Platform",
            "pheno": "🧬 Pheno-SDK",
        }
        return f"{context_info.get(self.context, '🧬 Pheno-SDK')} - {self.title}"

    def get_footer_content(self) -> str:
        """
        Get footer with available actions.
        """
        if not self._actions:
            return "Press 'q' to quit"

        action_hints = []
        for key, info in self._actions.items():
            desc = info.get("description", key)
            action_hints.append(f"[bold]{key}[/bold]: {desc}")

        return " | ".join(action_hints) + " | [bold]q[/bold]: quit"


class SetupWireframe(BaseWireframe):
    """
    Wireframe for project setup and configuration.
    """

    def __init__(self, **kwargs):
        super().__init__(title="Project Setup", style=WireframeStyle.WIZARD, **kwargs)
        self.current_step = reactive(1)
        self.total_steps = reactive(5)
        self.setup_data = {}

    def compose(self) -> ComposeResult:
        if not HAS_TEXTUAL:
            return []

        yield Header(show_clock=True)

        with Vertical():
            # Progress indicator
            yield Static(self.get_progress_display(), id="progress")

            # Main content area
            with Container(id="main-content"):
                yield Static("Loading setup...", id="step-content")

            # Navigation buttons
            with Horizontal(id="nav-buttons"):
                yield Button("Previous", id="prev-btn", disabled=True)
                yield Button("Next", id="next-btn")
                yield Button("Skip", id="skip-btn", variant="outline")

        yield Footer(self.get_footer_content())

    def get_progress_display(self) -> Panel:
        """
        Get progress indicator panel.
        """
        progress = f"Step {self.current_step} of {self.total_steps}"
        steps = ["Project Info", "Templates", "Configuration", "Dependencies", "Complete"]

        table = Table.grid(expand=True)
        table.add_column(justify="left")
        table.add_column(justify="right")

        for i, step in enumerate(steps, 1):
            if i < self.current_step:
                icon = "✅"
                style = "green"
            elif i == self.current_step:
                icon = "▶️"
                style = "blue bold"
            else:
                icon = "⭕"
                style = "dim"

            table.add_row(f"[{style}]{icon} {step}[/]", "")

        return Panel(table, title=f"Setup Progress ({progress})", border_style="blue")


class DeploymentWireframe(BaseWireframe):
    """
    Wireframe for deployment operations with progress tracking.
    """

    def __init__(self, **kwargs):
        super().__init__(title="Deployment", style=WireframeStyle.MONITOR, **kwargs)
        self.deployment_status = reactive("preparing")
        self.current_stage = reactive("")
        self.progress_value = reactive(0)

    def compose(self) -> ComposeResult:
        if not HAS_TEXTUAL:
            return []

        yield Header(show_clock=True)

        with Vertical():
            # Status overview
            yield Static(self.get_status_panel(), id="status")

            # Progress tracking
            with Container(id="progress-container"):
                yield ProgressBar(show_eta=True, id="main-progress")
                yield Static("Preparing deployment...", id="stage-info")

            # Live logs
            with Container(id="logs-container"):
                yield Log(id="deployment-logs", auto_scroll=True)

            # Actions
            with Horizontal(id="actions"):
                yield Button("Pause", id="pause-btn")
                yield Button("Cancel", id="cancel-btn", variant="error")
                yield Button("View Details", id="details-btn", variant="outline")

        yield Footer(self.get_footer_content())

    def get_status_panel(self) -> Panel:
        """
        Get deployment status panel.
        """
        status_icons = {
            "preparing": "🔄",
            "building": "🔨",
            "testing": "🧪",
            "packaging": "📦",
            "uploading": "⬆️",
            "complete": "✅",
            "failed": "❌",
        }

        icon = status_icons.get(self.deployment_status, "🔄")
        content = f"[bold]{icon} Deployment Status: {self.deployment_status.title()}[/bold]"

        if self.current_stage:
            content += f"\n[dim]Current: {self.current_stage}[/dim]"

        return Panel(content, border_style="blue", title="Status")


class ProjectWireframe(BaseWireframe):
    """
    Wireframe for project management and overview.
    """

    def __init__(self, project_path: Path | None = None, **kwargs):
        super().__init__(title="Project Dashboard", style=WireframeStyle.DASHBOARD, **kwargs)
        self.project_path = project_path or Path.cwd()
        self.project_info = {}

    def compose(self) -> ComposeResult:
        if not HAS_TEXTUAL:
            return []

        yield Header(show_clock=True)

        with Vertical():
            # Project overview
            with Horizontal():
                yield Static(self.get_project_info(), id="project-info")
                yield Static(self.get_quick_stats(), id="quick-stats")

            # Tabbed content
            with TabbedContent():
                with TabPane("Files", id="files-tab"):
                    yield Tree("Project Files", id="file-tree")

                with TabPane("Scripts", id="scripts-tab"):
                    yield DataTable(id="scripts-table")

                with TabPane("Dependencies", id="deps-tab"):
                    yield DataTable(id="deps-table")

                with TabPane("Logs", id="logs-tab"):
                    yield Log(id="project-logs", auto_scroll=True)

            # Action bar
            with Horizontal(id="actions"):
                yield Button("Build", id="build-btn", variant="primary")
                yield Button("Test", id="test-btn")
                yield Button("Deploy", id="deploy-btn", variant="success")
                yield Button("Settings", id="settings-btn", variant="outline")

        yield Footer(self.get_footer_content())

    def get_project_info(self) -> Panel:
        """
        Get project information panel.
        """
        name = self.project_path.name
        content = f"""[bold]Project: {name}[/bold]
Path: [cyan]{self.project_path}[/cyan]
Context: [blue]{self.context}[/blue]
Status: [green]Active[/green]"""

        return Panel(content, title="Project Info", border_style="green")

    def get_quick_stats(self) -> Panel:
        """
        Get quick statistics panel.
        """
        # This would be populated with real project stats
        content = """Files: [cyan]42[/cyan]
Size: [cyan]2.1 MB[/cyan]
Tests: [green]15 passing[/green]
Coverage: [green]87%[/green]"""

        return Panel(content, title="Quick Stats", border_style="blue")


class ConfigurationWireframe(BaseWireframe):
    """
    Wireframe for configuration management.
    """

    def __init__(self, **kwargs):
        super().__init__(title="Configuration", style=WireframeStyle.FORM, **kwargs)
        self.config_sections = ["General", "Authentication", "Deployment", "Development"]
        self.current_section = reactive("General")

    def compose(self) -> ComposeResult:
        if not HAS_TEXTUAL:
            return []

        yield Header(show_clock=True)

        with Horizontal():
            # Sidebar with sections
            with Vertical(id="sidebar"):
                yield Static("[bold]Configuration Sections[/bold]", id="sidebar-title")
                for section in self.config_sections:
                    yield Button(
                        section,
                        id=f"section-{section.lower()}",
                        variant="primary" if section == self.current_section else "outline",
                    )

            # Main configuration area
            with Vertical(id="main-config"):
                yield Static(self.get_section_header(), id="section-header")

                # Configuration form
                with Container(id="config-form"):
                    yield Static("Loading configuration...", id="form-content")

                # Action buttons
                with Horizontal(id="config-actions"):
                    yield Button("Save", id="save-btn", variant="success")
                    yield Button("Reset", id="reset-btn", variant="warning")
                    yield Button("Import", id="import-btn", variant="outline")
                    yield Button("Export", id="export-btn", variant="outline")

        yield Footer(self.get_footer_content())

    def get_section_header(self) -> Panel:
        """
        Get current section header.
        """
        section_descriptions = {
            "General": "Basic project and workspace settings",
            "Authentication": "OAuth, tokens, and credentials",
            "Deployment": "Publishing and deployment configuration",
            "Development": "Build, test, and development tools",
        }

        desc = section_descriptions.get(self.current_section, "")
        content = f"[bold]{self.current_section} Settings[/bold]\n[dim]{desc}[/dim]"

        return Panel(content, border_style="blue", title="Current Section")


class MonitoringWireframe(BaseWireframe):
    """
    Wireframe for system monitoring and observability.
    """

    def __init__(self, **kwargs):
        super().__init__(title="System Monitor", style=WireframeStyle.MONITOR, **kwargs)
        self.refresh_interval = 5  # seconds
        self.monitoring_active = reactive(True)

    def compose(self) -> ComposeResult:
        if not HAS_TEXTUAL:
            return []

        yield Header(show_clock=True)

        with Vertical():
            # Control panel
            with Horizontal(id="controls"):
                yield Button(
                    "Pause" if self.monitoring_active else "Resume", id="toggle-monitoring",
                )
                yield Button("Refresh", id="manual-refresh")
                yield Static(f"Auto-refresh: {self.refresh_interval}s", id="refresh-info")

            # Monitoring grid
            with Grid(id="monitor-grid"):
                yield Static(self.get_system_status(), id="system-status")
                yield Static(self.get_service_status(), id="service-status")
                yield Static(self.get_resource_usage(), id="resource-usage")
                yield Static(self.get_network_status(), id="network-status")

            # Event log
            with Container(id="events"):
                yield Static("[bold]Recent Events[/bold]", id="events-header")
                yield Log(id="event-log", auto_scroll=True)

        yield Footer(self.get_footer_content())

    def get_system_status(self) -> Panel:
        """
        Get system status panel.
        """
        content = """[green]✅ System Online[/green]
Uptime: [cyan]2d 14h 32m[/cyan]
Load: [yellow]0.75[/yellow]
Memory: [green]67%[/green]"""

        return Panel(content, title="System", border_style="green")

    def get_service_status(self) -> Panel:
        """
        Get service status panel.
        """
        content = """[green]✅ Web Server[/green]
[green]✅ Database[/green]
[yellow]⚠️  Cache Server[/yellow]
[red]❌ Backup Service[/red]"""

        return Panel(content, title="Services", border_style="blue")

    def get_resource_usage(self) -> Panel:
        """
        Get resource usage panel.
        """
        content = """CPU: [green]▓▓▓▓▓░░░░░[/green] 52%
RAM: [yellow]▓▓▓▓▓▓▓░░░[/yellow] 67%
Disk: [green]▓▓░░░░░░░░[/green] 23%
Net: [blue]▓░░░░░░░░░[/blue] 12%"""

        return Panel(content, title="Resources", border_style="yellow")

    def get_network_status(self) -> Panel:
        """
        Get network status panel.
        """
        content = """Connections: [cyan]142[/cyan]
Bandwidth: [green]↑ 1.2MB/s ↓ 3.4MB/s[/green]
Latency: [green]23ms[/green]
Errors: [red]2[/red]"""

        return Panel(content, title="Network", border_style="blue")


# Factory functions for creating wireframes


def launch_wireframe(wireframe_type: str, **kwargs) -> BaseWireframe:
    """
    Factory function to create and launch wireframes.
    """
    wireframes = {
        "setup": SetupWireframe,
        "deployment": DeploymentWireframe,
        "project": ProjectWireframe,
        "configuration": ConfigurationWireframe,
        "monitoring": MonitoringWireframe,
    }

    if wireframe_type not in wireframes:
        raise ValueError(f"Unknown wireframe type: {wireframe_type}")

    return wireframes[wireframe_type](**kwargs)


class WireframeApp(App if HAS_TEXTUAL else object):
    """
    App wrapper for running wireframes.
    """

    def __init__(self, wireframe: BaseWireframe, **kwargs):
        if HAS_TEXTUAL:
            super().__init__(**kwargs)
        self.wireframe = wireframe

    def on_mount(self) -> None:
        """
        Install the wireframe as the main screen.
        """
        if HAS_TEXTUAL:
            self.install_screen(self.wireframe, name="main")
            self.push_screen("main")


def run_wireframe_app(wireframe: BaseWireframe) -> None:
    """
    Run a wireframe in a Textual app.
    """
    if not HAS_TEXTUAL:
        print("Textual is not available. Install it with: pip install textual")
        return

    app = WireframeApp(wireframe)
    app.run()


# Export commonly used wireframes
__all__ = [
    "BaseWireframe",
    "ConfigurationWireframe",
    "DeploymentWireframe",
    "MonitoringWireframe",
    "ProjectWireframe",
    "SetupWireframe",
    "WireframeStyle",
    "launch_wireframe",
    "run_wireframe_app",
]
