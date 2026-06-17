"""
Pheno Control Center - Main TUI Application.

Unified desktop application and TUI monitor for managing multiple
pheno-sdk projects with interactive command execution and real-time monitoring.
"""

import asyncio
import logging

from .cli_bridge import CLIBridge, CommandExecutor, CommandRouter
from .monitor import ProjectRegistry, ResourceInfo, TUIMonitor

try:
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

try:
    from textual.app import App, ComposeResult
    from textual.containers import Horizontal, Vertical
    from textual.widgets import (
        DataTable,
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


class PhenoControlCenter:
    """Main control center application.

    Provides:
    - Multi-project monitoring
    - Interactive command execution
    - Real-time log streaming
    - Project management
    """

    def __init__(
        self,
        config_file: str | None = None,
        use_textual: bool = True,
        refresh_interval: float = 2.0,
    ):
        """
        Initialize the control center.
        """
        self.config_file = config_file
        self.use_textual = use_textual and HAS_TEXTUAL
        self.refresh_interval = refresh_interval

        # Initialize components
        self.project_registry = ProjectRegistry()
        self.monitor_engine = UnifiedMonitorEngine()
        self.cli_bridge = CLIBridge()
        self.command_router = CommandRouter(self.cli_bridge)
        self.command_executor = CommandExecutor(self.cli_bridge)

        # Load configuration
        self._load_configuration()

        # Initialize TUI monitor
        self.tui_monitor = TUIMonitor(
            project_registry=self.project_registry,
            monitor_engine=self.monitor_engine,
            use_textual=self.use_textual,
            refresh_interval=refresh_interval,
        )

        # Setup CLI bridge callbacks
        self.cli_bridge.add_output_callback(self._handle_command_output)

        logger.info("Pheno Control Center initialized")

    def _load_configuration(self) -> None:
        """
        Load configuration from file or defaults.
        """
        # Default project configurations
        default_projects = {
            "atoms": {
                "name": "atoms",
                "description": "Atoms MCP Server",
                "working_directory": None,  # Will be detected
                "default_port": 50002,
                "tunnel_domain": "atomcp.kooshapari.com",
                "processes": ["atoms-mcp"],
                "resources": ["fallback", "proxy"],
            },
            "zen": {
                "name": "zen",
                "description": "Zen MCP Server",
                "working_directory": None,  # Will be detected
                "default_port": 50001,
                "tunnel_domain": "zen.kooshapari.com",
                "processes": ["zen-mcp"],
                "resources": ["fallback", "proxy"],
            },
            "byteport": {
                "name": "byteport",
                "description": "Byteport Service",
                "working_directory": None,  # Will be detected
                "default_port": 50003,
                "tunnel_domain": "byteport.kooshapari.com",
                "processes": ["byteport-service"],
                "resources": ["fallback", "proxy"],
            },
        }

        # Register default projects
        for project_name, config in default_projects.items():
            self.project_registry.register_project(project_name, config)

            # Add default resources
            for resource_name in config.get("resources", []):
                resource_info = ResourceInfo(
                    name=resource_name,
                    project=project_name,
                    endpoint=f"localhost:{config.get('default_port', 9000)}",
                    state="unknown",
                    required=True,
                )
                self.monitor_engine.add_resource(project_name, resource_info)

        logger.info(f"Loaded configuration for {len(default_projects)} projects")

    def _handle_command_output(self, command_id: str, stream_type: str, line: str) -> None:
        """
        Handle streaming output from CLI commands.
        """
        # Parse command result to get project context
        result = self.cli_bridge.get_command_result(command_id)
        project = result.project_name if result else "global"

        # Add to monitor engine as log entry
        self.tui_monitor.add_log_entry(
            project=project, process="cli", level=stream_type, message=line,
        )

    async def run(self) -> None:
        """
        Run the control center.
        """
        logger.info("Starting Pheno Control Center")

        try:
            await self.tui_monitor.run()
        except KeyboardInterrupt:
            logger.info("Control center interrupted by user")
        except Exception as e:
            logger.exception(f"Control center error: {e}")
            raise
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        """
        Shutdown the control center.
        """
        logger.info("Shutting down Pheno Control Center")

        # Stop TUI monitor
        if hasattr(self.tui_monitor, "stop"):
            self.tui_monitor.stop()

        # Cancel any running commands
        running_commands = self.cli_bridge.get_running_commands()
        for command_id in running_commands:
            self.cli_bridge.cancel_command(command_id)

        logger.info("Control center shutdown complete")


if HAS_TEXTUAL:

    class PhenoControlCenterApp(App):
        """
        Textual-based main application for Pheno Control Center.
        """

        BINDINGS = [
            ("q", "quit", "Quit"),
            ("ctrl+c", "quit", "Quit"),
            ("enter", "execute_command", "Execute Command"),
            ("tab", "cycle_focus", "Cycle Focus"),
            ("f1", "show_help", "Help"),
            ("f2", "show_status", "Status"),
            ("f3", "show_logs", "Logs"),
        ]

        def __init__(self, control_center: PhenoControlCenter):
            super().__init__()
            self.control_center = control_center
            self.command_history: list[str] = []
            self.current_project = "global"

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

                with TabPane("Commands", id="commands-tab"), Vertical():
                    yield Input(
                        placeholder="Enter command (e.g., 'atoms start', 'zen logs')",
                        id="command-input",
                    )
                    yield Log(id="command-output", classes="command-log")
                    yield Static("Command History:", id="history-label")
                    yield Log(id="command-history", classes="history-log")

                with TabPane("Projects", id="projects-tab"), Vertical():
                    yield DataTable(id="projects-table")
                    yield Static("Project Details:", id="project-details")

        def on_mount(self) -> None:
            """
            Initialize the application.
            """
            self.title = "Pheno Control Center"
            self.sub_title = "Multi-Project Monitor & Control"

            # Start monitoring updates
            self.set_timer(self.control_center.refresh_interval, self.update_status)

            # Setup tables
            self._setup_tables()

            # Focus on command input
            command_input = self.query_one("#command-input", Input)
            command_input.focus()

        def _setup_tables(self) -> None:
            """
            Setup data tables.
            """
            # Processes table
            processes_table = self.query_one("#processes-table", DataTable)
            processes_table.add_columns("Project", "Process", "State", "PID", "Port", "Tunnel")

            # Projects table
            projects_table = self.query_one("#projects-table", DataTable)
            projects_table.add_columns("Project", "Status", "Processes", "Resources", "Port")

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
            self.command_history.append(command_text)
            history_log = self.query_one("#command-history", Log)
            history_log.write(f"> {command_text}")

            # Execute command
            command_id = self.command_executor.execute(command_text)

            if command_id:
                command_output = self.query_one("#command-output", Log)
                command_output.write(f"[dim]Executing: {command_text}[/dim]")

                # Update current project context
                if command_text.startswith(("atoms", "zen", "byteport")):
                    self.current_project = command_text.split()[0]
            else:
                command_output = self.query_one("#command-output", Log)
                command_output.write(f"[red]Failed to execute: {command_text}[/red]")

        def action_show_help(self) -> None:
            """
            Show help information.
            """
            help_text = """
Pheno Control Center - Keyboard Shortcuts:

F1 - Help (this screen)
F2 - Status overview
F3 - Logs view
Tab - Cycle focus
Enter - Execute command
Ctrl+C, Q - Quit

Project Commands:
  atoms <command>     - Execute atoms project command
  zen <command>       - Execute zen project command
  byteport <command>  - Execute byteport project command

General Commands:
  help, status, quit  - Built-in commands
            """

            command_output = self.query_one("#command-output", Log)
            for line in help_text.strip().split("\n"):
                command_output.write(line)

        def action_show_status(self) -> None:
            """
            Show detailed status.
            """
            global_status = self.control_center.monitor_engine.get_global_status()

            command_output = self.query_one("#command-output", Log)
            command_output.write("=== Global Status ===")
            command_output.write(
                f"Projects: {global_status['summary']['healthy_projects']}/{global_status['summary']['total_projects']} healthy",
            )
            command_output.write(
                f"Processes: {global_status['summary']['running_processes']}/{global_status['summary']['total_processes']} running",
            )

            for project_name, project_status in global_status["projects"].items():
                command_output.write(f"\n{project_name.upper()}: {project_status['overall_state']}")
                for process_name, state in project_status["processes"]["details"].items():
                    command_output.write(f"  {process_name}: {state}")

        def action_show_logs(self) -> None:
            """
            Switch to logs view.
            """
            self.query_one("#main-tabs").active = "monitor-tab"
            logs_panel = self.query_one("#logs-panel", Log)
            logs_panel.scroll_end()

        def update_status(self) -> None:
            """
            Update the status display.
            """
            # Update status display
            status_display = self.query_one("#status-display", Static)
            global_status = self.control_center.monitor_engine.get_global_status()

            status_text = (
                f"Projects: {global_status['summary']['healthy_projects']}/{global_status['summary']['total_projects']} healthy | "
                f"Processes: {global_status['summary']['running_processes']}/{global_status['summary']['total_processes']} running | "
                f"Current: {self.current_project}"
            )
            status_display.update(status_text)

            # Update processes table
            self._update_processes_table()

            # Update projects table
            self._update_projects_table()

            # Update logs
            self._update_logs()

        def _update_processes_table(self) -> None:
            """
            Update the processes table.
            """
            processes_table = self.query_one("#processes-table", DataTable)
            processes_table.clear()

            global_status = self.control_center.monitor_engine.get_global_status()

            for project_name, project_status in global_status["projects"].items():
                for process_name, state in project_status["processes"]["details"].items():
                    process_info = self.control_center.monitor_engine.get_process(
                        project_name, process_name,
                    )
                    pid = str(process_info.pid) if process_info and process_info.pid else "-"
                    port = str(process_info.port) if process_info and process_info.port else "-"
                    tunnel = "✓" if process_info and process_info.tunnel_url else "-"

                    # Color state
                    state_colors = {
                        "running": "green",
                        "stopped": "red",
                        "starting": "yellow",
                        "stopping": "yellow",
                        "error": "red",
                    }
                    color = state_colors.get(state, "white")
                    state_display = f"[{color}]{state}[/{color}]"

                    processes_table.add_row(
                        project_name, process_name, state_display, pid, port, tunnel,
                    )

        def _update_projects_table(self) -> None:
            """
            Update the projects table.
            """
            projects_table = self.query_one("#projects-table", DataTable)
            projects_table.clear()

            global_status = self.control_center.monitor_engine.get_global_status()

            for project_name, project_status in global_status["projects"].items():
                # Color status
                status_colors = {
                    "healthy": "green",
                    "degraded": "yellow",
                    "down": "red",
                    "no_processes": "dim",
                }
                color = status_colors.get(project_status["overall_state"], "white")
                status_display = f"[{color}]{project_status['overall_state']}[/{color}]"

                processes_count = f"{project_status['processes']['running']}/{project_status['processes']['total']}"
                resources_count = f"{project_status['resources']['available']}/{project_status['resources']['total']}"

                # Get default port from project config
                project_config = self.control_center.project_registry.get_project(project_name)
                default_port = project_config.get("default_port", "-") if project_config else "-"

                projects_table.add_row(
                    project_name,
                    status_display,
                    processes_count,
                    resources_count,
                    str(default_port),
                )

        def _update_logs(self) -> None:
            """
            Update the logs panel.
            """
            logs_panel = self.query_one("#logs-panel", Log)
            recent_logs = self.control_center.monitor_engine.get_logs(limit=10)

            for log_entry in recent_logs:
                timestamp = log_entry.timestamp.strftime("%H:%M:%S")
                project_process = f"{log_entry.project}.{log_entry.process}"

                # Only add new logs (simple check - in real implementation would track last seen)
                log_line = f"{timestamp} {project_process}: {log_entry.message}"
                logs_panel.write(log_line)

        def action_quit(self) -> None:
            """
            Quit the application.
            """
            self.control_center.shutdown()
            self.exit()


async def run_control_center(
    config_file: str | None = None, use_textual: bool = True, refresh_interval: float = 2.0,
) -> None:
    """Run the Pheno Control Center.

    Args:
        config_file: Path to configuration file
        use_textual: Whether to use textual TUI (if available)
        refresh_interval: Refresh interval in seconds
    """
    # Setup logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Create control center
    control_center = PhenoControlCenter(
        config_file=config_file, use_textual=use_textual, refresh_interval=refresh_interval,
    )

    # Run the application
    if use_textual and HAS_TEXTUAL:
        app = PhenoControlCenterApp(control_center)
        await app.run_async()
    else:
        await control_center.run()


def main():
    """
    Main entry point for the control center.
    """
    import argparse

    parser = argparse.ArgumentParser(description="Pheno Control Center")
    parser.add_argument("--config", help="Configuration file path", default=None)
    parser.add_argument(
        "--no-textual", action="store_true", help="Disable textual TUI (use rich instead)",
    )
    parser.add_argument(
        "--refresh-interval", type=float, default=2.0, help="Refresh interval in seconds",
    )

    args = parser.parse_args()

    # Run the control center
    asyncio.run(
        run_control_center(
            config_file=args.config,
            use_textual=not args.no_textual,
            refresh_interval=args.refresh_interval,
        ),
    )


if __name__ == "__main__":
    main()
