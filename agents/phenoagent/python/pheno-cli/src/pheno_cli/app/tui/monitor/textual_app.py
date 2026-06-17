"""
Textual application for the monitor UI.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .environment import (
    HAS_TEXTUAL,
    App,
    ComposeResult,
    DataTable,
    Footer,
    Header,
    Horizontal,
    Input,
    Log,
    Static,
    TabbedContent,
    TabPane,
    Vertical,
)

if TYPE_CHECKING:
    from pheno.domain.models.project import ProjectRegistry

    from .engine import MonitorEngine

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

        def __init__(self, project_registry: ProjectRegistry, monitor_engine: MonitorEngine):
            super().__init__()
            self.project_registry = project_registry
            self.monitor_engine = monitor_engine
            self.command_history: list[str] = []

        def compose(self) -> ComposeResult:
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
            self.title = "Pheno Control Center"
            self.sub_title = "Multi-Project Monitor & Control"

            self.set_timer(2.0, self.update_status)

            processes_table = self.query_one("#processes-table", DataTable)
            processes_table.add_columns("Project", "Process", "State", "PID", "Port")

        def action_execute_command(self) -> None:
            command_input = self.query_one("#command-input", Input)
            command_text = command_input.value.strip()
            if not command_text:
                return

            command_input.value = ""
            self.command_history.append(command_text)
            history_log = self.query_one("#command-history", Log)
            history_log.write(f"> {command_text}")

        def update_status(self) -> None:
            status_display = self.query_one("#status-display", Static)
            global_status = self.monitor_engine.get_global_status()
            status_text = (
                f"Projects: {global_status['summary']['healthy_projects']}/{global_status['summary']['total_projects']} healthy | "
                f"Processes: {global_status['summary']['running_processes']}/{global_status['summary']['total_processes']} running"
            )
            status_display.update(status_text)

            processes_table = self.query_one("#processes-table", DataTable)
            processes_table.clear()
            for project_name, project_status in global_status["projects"].items():
                for process_name, state in project_status["processes"]["details"].items():
                    process_info = self.monitor_engine.get_process(project_name, process_name)
                    pid = str(process_info.pid) if process_info and process_info.pid else "-"
                    port = str(process_info.port) if process_info and process_info.port else "-"
                    processes_table.add_row(project_name, process_name, state, pid, port)

            logs_panel = self.query_one("#logs-panel", Log)
            recent_logs = self.monitor_engine.get_logs(limit=5)
            for log_entry in recent_logs:
                timestamp = log_entry.timestamp.strftime("%H:%M:%S")
                project_process = f"{log_entry.project}.{log_entry.process}"
                log_line = f"{timestamp} {project_process}: {log_entry.message}"
                logs_panel.write(log_line)

        def action_quit(self) -> None:
            self.exit()

else:  # pragma: no cover - textual not installed

    PhenoControlCenterApp = None  # type: ignore


__all__ = ["PhenoControlCenterApp"]
