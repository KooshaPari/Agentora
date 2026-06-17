"""Enhanced TUI Monitor for Pheno Control Center.

Non-interactive TUI view with scrollable log panels, command entry, and config-based
layout using rich/textual for enhanced user experience.
"""

import asyncio
import logging

from .cli_bridge import CLIBridge, CommandRouter
from .config import ProjectRegistry
from .engine import MonitorEngine as UnifiedMonitorEngine
from .enhanced_monitor import MultiProjectMonitor

try:
    from rich import box
    from rich.align import Align
    from rich.console import Console
    from rich.layout import Layout
    from rich.live import Live
    from rich.panel import Panel

    HAS_RICH = True
except ImportError:
    HAS_RICH = False

try:
    # Try to import textual for enhanced TUI
    from textual.app import App, ComposeResult
    from textual.containers import Horizontal, Vertical
    from textual.widgets import (
        DataTable,
        Footer,
        Header,
        Input,
        Log,
        Static,
        TabbedContent,
        TabPane,
    )

    HAS_TEXTUAL = True
except ImportError:
    HAS_TEXTUAL = False

logger = logging.getLogger(__name__)


class TUIMonitor:
    """TUI monitor with command input and scrollable logs.

    Provides:
    - Multi-project monitoring display
    - Interactive command input
    - Scrollable log panels
    - Real-time status updates
    """

    def __init__(
        self,
        project_registry: ProjectRegistry,
        monitor_engine: UnifiedMonitorEngine,
        cli_bridge: CLIBridge,
        command_router: CommandRouter,
        use_textual: bool = True,
    ):
        """
        Initialize enhanced TUI monitor.
        """
        self.project_registry = project_registry
        self.monitor_engine = monitor_engine
        self.cli_bridge = cli_bridge
        self.command_router = command_router

        # Determine which TUI to use
        self.use_textual = use_textual and HAS_TEXTUAL
        self.use_rich = not self.use_textual and HAS_RICH

        if not self.use_textual and not self.use_rich:
            raise RuntimeError("Neither textual nor rich is available for TUI")

        # Rich-based components
        if self.use_rich:
            self.console = Console()
            self.enhanced_monitor = MultiProjectMonitor(
                project_registry=project_registry, monitor_engine=monitor_engine, enable_rich=True,
            )

        # Command history for input
        self.command_history: list[str] = []
        self.history_index = -1

        # Setup CLI bridge callbacks
        self.cli_bridge.add_output_callback(self._handle_command_output)

        logger.info(
            f"Enhanced TUI monitor initialized (using {'textual' if self.use_textual else 'rich'})",
        )

    def _handle_command_output(self, command_id: str, stream_type: str, line: str) -> None:
        """
        Handle streaming output from CLI commands.
        """
        # Parse command result to get project context
        result = self.cli_bridge.get_command_result(command_id)
        project = result.project_name if result else "global"

        # Add to monitor engine
        self.enhanced_monitor.add_log_entry(
            project=project, process="cli", level=stream_type, message=line,
        )

    async def run(self) -> None:
        """
        Run the enhanced TUI monitor.
        """
        if self.use_textual:
            await self._run_textual()
        else:
            await self._run_rich()

    async def _run_textual(self) -> None:
        """
        Run using Textual TUI framework.
        """
        app = PhenoControlCenterApp(
            project_registry=self.project_registry,
            monitor_engine=self.monitor_engine,
            cli_bridge=self.cli_bridge,
            command_router=self.command_router,
        )
        await app.run_async()

    async def _run_rich(self) -> None:
        """
        Run using Rich with custom layout.
        """
        logger.info("Starting Rich-based TUI monitor")

        # Create layout
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

        # Command input state
        current_input = ""

        with Live(layout, console=self.console, screen=True):
            while True:
                # Update header
                layout["header"].update(
                    Panel(
                        Align.center("[bold cyan]Pheno Control Center - TUI Monitor[/bold cyan]"),
                        box=box.ROUNDED,
                    ),
                )

                # Update status panel
                layout["status"].update(self.enhanced_monitor._make_monitor_panel())

                # Update logs panel
                layout["logs"].update(self._make_logs_panel())

                # Update input panel
                layout["input"].update(
                    Panel(f"Command: {current_input}_", title="Input", box=box.ROUNDED),
                )

                # Note: In a real implementation, we'd need proper keyboard handling
                # This is a simplified version showing the structure
                await asyncio.sleep(1.0)

    def _make_logs_panel(self) -> Panel:
        """
        Create logs panel with recent entries.
        """
        logs = self.monitor_engine.get_logs(limit=20)

        log_text = ""
        for log_entry in logs[-10:]:  # Show last 10 entries
            timestamp = log_entry.timestamp.strftime("%H:%M:%S")
            project_process = f"{log_entry.project}.{log_entry.process}"

            # Color based on level
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


if HAS_TEXTUAL:

    class PhenoControlCenterApp(App):
        """
        Textual-based TUI application for Pheno Control Center.
        """

        BINDINGS = [
            ("q", "quit", "Quit"),
            ("ctrl+c", "quit", "Quit"),
            ("enter", "execute_command", "Execute Command"),
            ("tab", "cycle_focus", "Cycle Focus"),
        ]

        def __init__(
            self,
            project_registry: ProjectRegistry,
            monitor_engine: UnifiedMonitorEngine,
            cli_bridge: CLIBridge,
            command_router: CommandRouter,
        ):
            super().__init__()
            self.project_registry = project_registry
            self.monitor_engine = monitor_engine
            self.cli_bridge = cli_bridge
            self.command_router = command_router

            # Setup CLI output callback
            self.cli_bridge.add_output_callback(self._handle_command_output)

        def compose(self) -> ComposeResult:
            """
            Create the application layout.
            """
            yield Header()

            with TabbedContent(id="main-tabs"):
                with TabPane("Monitor", id="monitor-tab"), Vertical():
                    yield Static(id="status-display")
                    with Horizontal():
                        yield Log(id="logs-panel", classes="log-panel")
                        yield DataTable(id="processes-table")

                with TabPane("Commands", id="commands-tab"):
                    with Vertical():
                        yield Input(
                            placeholder="Enter command (e.g., 'atoms start')", id="command-input",
                        )
                        yield Log(id="command-output", classes="command-log")
                        yield Static("Command History:", id="history-label")
                        yield Log(id="command-history", classes="history-log")

            yield Footer()

        def on_mount(self) -> None:
            """
            Initialize the application.
            """
            self.title = "Pheno Control Center"
            self.sub_title = "Multi-Project Monitor & Control"

            # Start monitoring updates
            self.set_timer(2.0, self.update_status)

            # Setup processes table
            processes_table = self.query_one("#processes-table", DataTable)
            processes_table.add_columns("Project", "Process", "State", "PID", "Port")

        def action_execute_command(self) -> None:
            """
            Execute command from input.
            """
            command_input = self.query_one("#command-input", Input)
            command_text = command_input.value.strip()

            if not command_text:
                return

            # Clear input
            command_input.value = ""

            # Add to history
            history_log = self.query_one("#command-history", Log)
            history_log.write(f"> {command_text}")

            # Execute command
            command_id = self.command_router.route_command(command_text)

            if command_id:
                command_output = self.query_one("#command-output", Log)
                command_output.write(f"[dim]Executing: {command_text}[/dim]")
            else:
                command_output = self.query_one("#command-output", Log)
                command_output.write(f"[red]Failed to execute: {command_text}[/red]")

        def _handle_command_output(self, command_id: str, stream_type: str, line: str) -> None:
            """
            Handle streaming command output.
            """
            command_output = self.query_one("#command-output", Log)

            # Color based on stream type
            if stream_type == "stderr":
                command_output.write(f"[red]{line}[/red]")
            else:
                command_output.write(line)

        def update_status(self) -> None:
            """
            Update the status display.
            """
            # Update status display
            status_display = self.query_one("#status-display", Static)
            global_status = self.monitor_engine.get_global_status()

            status_text = (
                f"Projects: {global_status['summary']['healthy_projects']}/{global_status['summary']['total_projects']} healthy | "
                f"Processes: {global_status['summary']['running_processes']}/{global_status['summary']['total_processes']} running"
            )
            status_display.update(status_text)

            # Update processes table
            processes_table = self.query_one("#processes-table", DataTable)
            processes_table.clear()

            for project_name, project_status in global_status["projects"].items():
                for process_name, state in project_status["processes"]["details"].items():
                    process_info = self.monitor_engine.get_process(project_name, process_name)
                    pid = str(process_info.pid) if process_info and process_info.pid else "-"
                    port = str(process_info.port) if process_info and process_info.port else "-"

                    processes_table.add_row(project_name, process_name, state, pid, port)

            # Update logs
            logs_panel = self.query_one("#logs-panel", Log)
            recent_logs = self.monitor_engine.get_logs(limit=5)

            for log_entry in recent_logs:
                timestamp = log_entry.timestamp.strftime("%H:%M:%S")
                project_process = f"{log_entry.project}.{log_entry.process}"

                # Only add new logs (simple check)
                log_line = f"{timestamp} {project_process}: {log_entry.message}"
                logs_panel.write(log_line)

        def action_quit(self) -> None:
            """
            Quit the application.
            """
            self.exit()


# Fallback simple TUI for when neither Rich nor Textual is available
class SimpleTUIMonitor:
    """
    Simple fallback TUI monitor using basic console output.
    """

    def __init__(
        self,
        project_registry: ProjectRegistry,
        monitor_engine: UnifiedMonitorEngine,
        cli_bridge: CLIBridge,
        command_router: CommandRouter,
    ):
        self.project_registry = project_registry
        self.monitor_engine = monitor_engine
        self.cli_bridge = cli_bridge
        self.command_router = command_router

    async def run(self) -> None:
        """
        Run simple console-based monitor.
        """
        print("=== Pheno Control Center - Simple Monitor ===")
        print("Enhanced TUI not available (missing rich/textual)")
        print("Commands: 'status', 'quit', or any project command")
        print("=" * 50)

        while True:
            try:
                command = input("> ").strip()

                if command.lower() in ["quit", "exit", "q"]:
                    break
                if command.lower() == "status":
                    self._print_status()
                elif command:
                    command_id = self.command_router.route_command(command)
                    if command_id:
                        print(f"Executed: {command} (ID: {command_id})")
                    else:
                        print(f"Failed to execute: {command}")

            except (EOFError, KeyboardInterrupt):
                break

        print("\nShutting down...")

    def _print_status(self) -> None:
        """
        Print current status.
        """
        global_status = self.monitor_engine.get_global_status()

        print("\nGlobal Status:")
        print(
            f"  Projects: {global_status['summary']['healthy_projects']}/{global_status['summary']['total_projects']} healthy",
        )
        print(
            f"  Processes: {global_status['summary']['running_processes']}/{global_status['summary']['total_processes']} running",
        )

        for project_name, project_status in global_status["projects"].items():
            print(f"\n{project_name.upper()}:")
            print(f"  Overall: {project_status['overall_state']}")
            print(
                f"  Processes: {project_status['processes']['running']}/{project_status['processes']['total']}",
            )

            for process_name, state in project_status["processes"]["details"].items():
                print(f"    {process_name}: {state}")
        print()


async def run_enhanced_tui_monitor(
    project_registry: ProjectRegistry,
    monitor_engine: UnifiedMonitorEngine,
    cli_bridge: CLIBridge,
    command_router: CommandRouter,
    prefer_textual: bool = True,
) -> None:
    """Run the enhanced TUI monitor with the best available interface.

    Args:
        project_registry: Project registry instance
        monitor_engine: Monitor engine instance
        cli_bridge: CLI bridge instance
        command_router: Command router instance
        prefer_textual: Whether to prefer textual over rich
    """
    if prefer_textual and HAS_TEXTUAL:
        monitor = TUIMonitor(
            project_registry, monitor_engine, cli_bridge, command_router, use_textual=True,
        )
    elif HAS_RICH:
        monitor = TUIMonitor(
            project_registry, monitor_engine, cli_bridge, command_router, use_textual=False,
        )
    else:
        monitor = SimpleTUIMonitor(project_registry, monitor_engine, cli_bridge, command_router)

    await monitor.run()
