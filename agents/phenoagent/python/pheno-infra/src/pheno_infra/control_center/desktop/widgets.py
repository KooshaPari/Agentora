"""PyQt widgets for Pheno Control Center desktop application.

Provides specialized widgets for project management, monitoring display, terminal
integration, and status reporting.
"""

import logging

try:
    from PyQt6.QtCore import Qt, pyqtSignal
    from PyQt6.QtGui import QFont
    from PyQt6.QtWidgets import (
        QFrame,
        QGridLayout,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QPlainTextEdit,
        QPushButton,
        QScrollArea,
        QSplitter,
        QTableWidget,
        QTableWidgetItem,
        QTabWidget,
        QTreeWidget,
        QTreeWidgetItem,
        QVBoxLayout,
        QWidget,
    )

    HAS_PYQT = True
except ImportError:
    HAS_PYQT = False

logger = logging.getLogger(__name__)


if HAS_PYQT:

    class ProjectTileWidget(QFrame):
        """
        Individual project tile with start/stop controls.
        """

        start_requested = pyqtSignal(str)  # project_name
        stop_requested = pyqtSignal(str)  # project_name

        def __init__(self, project_name: str, project_config):
            super().__init__()
            self.project_name = project_name
            self.project_config = project_config
            self.current_status = "stopped"

            self.setFrameStyle(QFrame.Shape.Box)
            self.setLineWidth(1)
            self.setFixedSize(200, 120)

            layout = QVBoxLayout(self)

            # Project name
            name_label = QLabel(project_name.upper())
            name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            name_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            layout.addWidget(name_label)

            # Status indicator
            self.status_label = QLabel("●")
            self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.status_label.setFont(QFont("Arial", 16))
            layout.addWidget(self.status_label)

            # Status text
            self.status_text = QLabel("Stopped")
            self.status_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(self.status_text)

            # Control buttons
            button_layout = QHBoxLayout()

            self.start_button = QPushButton("Start")
            self.start_button.clicked.connect(self.start_project)
            button_layout.addWidget(self.start_button)

            self.stop_button = QPushButton("Stop")
            self.stop_button.clicked.connect(self.stop_project)
            self.stop_button.setEnabled(False)
            button_layout.addWidget(self.stop_button)

            layout.addLayout(button_layout)

            # Update initial status
            self.update_status("stopped")

        def update_status(self, status: str):
            """
            Update the project status display.
            """
            self.current_status = status

            status_colors = {
                "running": ("#00AA00", "Running"),
                "starting": ("#FFAA00", "Starting"),
                "stopping": ("#FFAA00", "Stopping"),
                "stopped": ("#AA0000", "Stopped"),
                "error": ("#FF0000", "Error"),
                "unknown": ("#888888", "Unknown"),
            }

            color, text = status_colors.get(status, ("#888888", "Unknown"))

            self.status_label.setStyleSheet(f"color: {color};")
            self.status_text.setText(text)

            # Update button states
            is_running = status == "running"
            self.start_button.setEnabled(not is_running)
            self.stop_button.setEnabled(is_running)

        def start_project(self):
            """
            Handle start button click.
            """
            self.start_requested.emit(self.project_name)
            self.update_status("starting")

        def stop_project(self):
            """
            Handle stop button click.
            """
            self.stop_requested.emit(self.project_name)
            self.update_status("stopping")

    class ProjectLauncherWidget(QWidget):
        """
        Widget containing project launcher tiles.
        """

        def __init__(self, control_center):
            super().__init__()
            self.control_center = control_center
            self.project_tiles: dict[str, ProjectTileWidget] = {}

            self.setMinimumWidth(250)
            self.setMaximumWidth(400)

            layout = QVBoxLayout(self)

            # Title
            title_label = QLabel("Projects")
            title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
            layout.addWidget(title_label)

            # Scroll area for project tiles
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

            # Container widget for tiles
            self.container_widget = QWidget()
            self.container_layout = QVBoxLayout(self.container_widget)
            self.container_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

            scroll_area.setWidget(self.container_widget)
            layout.addWidget(scroll_area)

            # Initialize project tiles
            self._create_project_tiles()

        def _create_project_tiles(self):
            """
            Create tiles for all registered projects.
            """
            for project_name in self.control_center.project_registry.list_projects():
                project_config = self.control_center.project_registry.get_project(project_name)
                if project_config:
                    self._add_project_tile(project_name, project_config)

        def _add_project_tile(self, project_name: str, project_config):
            """
            Add a project tile to the launcher.
            """
            tile = ProjectTileWidget(project_name, project_config)
            tile.start_requested.connect(self._start_project)
            tile.stop_requested.connect(self._stop_project)

            self.project_tiles[project_name] = tile
            self.container_layout.addWidget(tile)

        def _start_project(self, project_name: str):
            """
            Start a project via CLI bridge.
            """
            logger.info(f"Starting project: {project_name}")

            # Get project config
            project_config = self.control_center.project_registry.get_project(project_name)
            if project_config and project_config.cli_entry:
                # Execute start command
                command = [*project_config.cli_entry, "start"]
                command_id = self.control_center.command_router.route_command(" ".join(command))
                logger.info(f"Executed start command for {project_name}: {command_id}")

        def _stop_project(self, project_name: str):
            """
            Stop a project via CLI bridge.
            """
            logger.info(f"Stopping project: {project_name}")

            # Get project config
            project_config = self.control_center.project_registry.get_project(project_name)
            if project_config and project_config.cli_entry:
                # Execute stop command
                command = [*project_config.cli_entry, "stop"]
                command_id = self.control_center.command_router.route_command(" ".join(command))
                logger.info(f"Executed stop command for {project_name}: {command_id}")

        def update_status(self, global_status):
            """
            Update project tile statuses based on global status.
            """
            projects_status = global_status.get("projects", {})

            for project_name, tile in self.project_tiles.items():
                project_status = projects_status.get(project_name, {})
                overall_state = project_status.get("overall_state", "unknown")

                # Map overall state to tile status
                status_mapping = {
                    "healthy": "running",
                    "degraded": "running",
                    "down": "stopped",
                    "no_processes": "stopped",
                }
                tile_status = status_mapping.get(overall_state, "unknown")
                tile.update_status(tile_status)

    class MonitoringWidget(QWidget):
        """
        Widget for displaying monitoring information.
        """

        def __init__(self, control_center):
            super().__init__()
            self.control_center = control_center

            layout = QVBoxLayout(self)

            # Create splitter for monitoring panes
            splitter = QSplitter(Qt.Orientation.Vertical)

            # Status overview
            self.status_overview = self._create_status_overview()
            splitter.addWidget(self.status_overview)

            # Process table
            self.process_table = self._create_process_table()
            splitter.addWidget(self.process_table)

            # Resource table
            self.resource_table = self._create_resource_table()
            splitter.addWidget(self.resource_table)

            # Log display
            self.log_display = self._create_log_display()
            splitter.addWidget(self.log_display)

            # Set splitter proportions
            splitter.setSizes([100, 200, 150, 250])

            layout.addWidget(splitter)

        def _create_status_overview(self):
            """
            Create status overview widget.
            """
            group = QGroupBox("Overview")
            layout = QGridLayout(group)

            # Status labels
            self.projects_label = QLabel("Projects: 0/0 healthy")
            self.processes_label = QLabel("Processes: 0/0 running")
            self.tunnels_label = QLabel("Tunnels: 0 active")

            layout.addWidget(QLabel("Status:"), 0, 0)
            layout.addWidget(self.projects_label, 0, 1)
            layout.addWidget(self.processes_label, 1, 1)
            layout.addWidget(self.tunnels_label, 2, 1)

            return group

        def _create_process_table(self):
            """
            Create process status table.
            """
            group = QGroupBox("Processes")
            layout = QVBoxLayout(group)

            table = QTableWidget()
            table.setColumnCount(5)
            table.setHorizontalHeaderLabels(["Project", "Process", "Status", "PID", "Port"])
            table.horizontalHeader().setStretchLastSection(True)

            layout.addWidget(table)
            self.process_table_widget = table

            return group

        def _create_resource_table(self):
            """
            Create resource status table.
            """
            group = QGroupBox("Resources")
            layout = QVBoxLayout(group)

            table = QTableWidget()
            table.setColumnCount(4)
            table.setHorizontalHeaderLabels(["Project", "Resource", "Status", "Endpoint"])
            table.horizontalHeader().setStretchLastSection(True)

            layout.addWidget(table)
            self.resource_table_widget = table

            return group

        def _create_log_display(self):
            """
            Create log display area.
            """
            group = QGroupBox("Recent Logs")
            layout = QVBoxLayout(group)

            log_text = QPlainTextEdit()
            log_text.setReadOnly(True)
            log_text.setMaximumBlockCount(1000)  # Limit log entries

            layout.addWidget(log_text)
            self.log_text_widget = log_text

            return group

        def update_status(self, global_status):
            """
            Update monitoring display with new status data.
            """
            summary = global_status["summary"]

            # Update overview
            self.projects_label.setText(
                f"Projects: {summary['healthy_projects']}/{summary['total_projects']} healthy",
            )
            self.processes_label.setText(
                f"Processes: {summary['running_processes']}/{summary['total_processes']} running",
            )

            # Update process table
            self._update_process_table(global_status["projects"])

            # Update resource table
            self._update_resource_table(global_status["projects"])

            # Update logs
            self._update_logs()

        def _update_process_table(self, projects_status):
            """
            Update the process status table.
            """
            self.process_table_widget.setRowCount(0)
            row = 0

            for project_name, project_status in projects_status.items():
                for process_name, state in project_status["processes"]["details"].items():
                    self.process_table_widget.insertRow(row)

                    # Get process info
                    process_info = self.control_center.monitor_engine.get_process(
                        project_name, process_name,
                    )

                    self.process_table_widget.setItem(row, 0, QTableWidgetItem(project_name))
                    self.process_table_widget.setItem(row, 1, QTableWidgetItem(process_name))
                    self.process_table_widget.setItem(row, 2, QTableWidgetItem(state))
                    self.process_table_widget.setItem(
                        row,
                        3,
                        QTableWidgetItem(
                            str(process_info.pid) if process_info and process_info.pid else "-",
                        ),
                    )
                    self.process_table_widget.setItem(
                        row,
                        4,
                        QTableWidgetItem(
                            str(process_info.port) if process_info and process_info.port else "-",
                        ),
                    )

                    row += 1

        def _update_resource_table(self, projects_status):
            """
            Update the resource status table.
            """
            self.resource_table_widget.setRowCount(0)
            row = 0

            for project_name, project_status in projects_status.items():
                for resource_name, state in project_status["resources"]["details"].items():
                    self.resource_table_widget.insertRow(row)

                    # Get resource info
                    resource_info = self.control_center.monitor_engine.get_resource(
                        project_name, resource_name,
                    )

                    self.resource_table_widget.setItem(row, 0, QTableWidgetItem(project_name))
                    self.resource_table_widget.setItem(row, 1, QTableWidgetItem(resource_name))
                    self.resource_table_widget.setItem(row, 2, QTableWidgetItem(state))
                    self.resource_table_widget.setItem(
                        row,
                        3,
                        QTableWidgetItem(
                            resource_info.endpoint
                            if resource_info and resource_info.endpoint
                            else "-",
                        ),
                    )

                    row += 1

        def _update_logs(self):
            """
            Update log display with recent entries.
            """
            recent_logs = self.control_center.monitor_engine.get_logs(limit=20)

            # Only add new logs (simple approach)
            for log_entry in recent_logs[-5:]:  # Show last 5 entries
                timestamp = log_entry.timestamp.strftime("%H:%M:%S")
                project_process = f"{log_entry.project}.{log_entry.process}"
                log_line = f"{timestamp} [{project_process}] {log_entry.message}"

                # Append to log display
                self.log_text_widget.appendPlainText(log_line)

    class TerminalWidget(QWidget):
        """
        Embedded terminal widget for command execution.
        """

        def __init__(self, control_center):
            super().__init__()
            self.control_center = control_center

            layout = QVBoxLayout(self)

            # Command output area
            self.output_text = QPlainTextEdit()
            self.output_text.setReadOnly(True)
            self.output_text.setFont(QFont("Monaco", 10))
            layout.addWidget(self.output_text)

            # Command input area
            input_layout = QHBoxLayout()

            self.command_input = QLineEdit()
            self.command_input.setPlaceholderText("Enter command (e.g., 'atoms start')")
            self.command_input.returnPressed.connect(self.execute_command)
            input_layout.addWidget(self.command_input)

            execute_button = QPushButton("Execute")
            execute_button.clicked.connect(self.execute_command)
            input_layout.addWidget(execute_button)

            clear_button = QPushButton("Clear")
            clear_button.clicked.connect(self.output_text.clear)
            input_layout.addWidget(clear_button)

            layout.addLayout(input_layout)

            # Setup CLI bridge callbacks
            self.control_center.cli_bridge.add_output_callback(self._handle_command_output)

        def execute_command(self):
            """
            Execute the command in the input field.
            """
            command_text = self.command_input.text().strip()
            if not command_text:
                return

            # Clear input
            self.command_input.clear()

            # Show command in output
            self.output_text.appendPlainText(f"> {command_text}")

            # Execute command
            try:
                command_id = self.control_center.command_router.route_command(command_text)
                if command_id:
                    self.output_text.appendPlainText(f"[Executing command ID: {command_id}]")
                else:
                    self.output_text.appendPlainText("[Failed to execute command]")
            except Exception as e:
                self.output_text.appendPlainText(f"[Error: {e}]")

        def _handle_command_output(self, command_id: str, stream_type: str, line: str):
            """
            Handle streaming command output.
            """
            # Color-code based on stream type
            prefix = "[ERROR]" if stream_type == "stderr" else "[INFO]"

            self.output_text.appendPlainText(f"{prefix} {line}")

            # Auto-scroll to bottom
            scrollbar = self.output_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    class StatusWidget(QWidget):
        """
        Widget for displaying detailed status information.
        """

        def __init__(self, control_center):
            super().__init__()
            self.control_center = control_center

            layout = QVBoxLayout(self)

            # Tabbed status display
            tab_widget = QTabWidget()

            # Global status tab
            self.global_status_widget = self._create_global_status_widget()
            tab_widget.addTab(self.global_status_widget, "Global")

            # Multi-tenant status tab
            self.mt_status_widget = self._create_mt_status_widget()
            tab_widget.addTab(self.mt_status_widget, "Infrastructure")

            layout.addWidget(tab_widget)

        def _create_global_status_widget(self):
            """
            Create global status display widget.
            """
            widget = QWidget()
            layout = QVBoxLayout(widget)

            # Status tree
            self.status_tree = QTreeWidget()
            self.status_tree.setHeaderLabel("Status")
            layout.addWidget(self.status_tree)

            return widget

        def _create_mt_status_widget(self):
            """
            Create multi-tenant status display widget.
            """
            widget = QWidget()
            layout = QVBoxLayout(widget)

            # Infrastructure status
            self.infra_text = QPlainTextEdit()
            self.infra_text.setReadOnly(True)
            layout.addWidget(self.infra_text)

            return widget

        def update_status(self, global_status):
            """
            Update status display.
            """
            self._update_global_status(global_status)
            self._update_mt_status()

        def _update_global_status(self, global_status):
            """
            Update global status tree.
            """
            self.status_tree.clear()

            # Summary
            summary_item = QTreeWidgetItem(["Summary"])
            summary = global_status["summary"]

            projects_item = QTreeWidgetItem(
                [f"Projects: {summary['healthy_projects']}/{summary['total_projects']} healthy"],
            )
            summary_item.addChild(projects_item)

            processes_item = QTreeWidgetItem(
                [f"Processes: {summary['running_processes']}/{summary['total_processes']} running"],
            )
            summary_item.addChild(processes_item)

            self.status_tree.addTopLevelItem(summary_item)

            # Per-project status
            for project_name, project_status in global_status["projects"].items():
                project_item = QTreeWidgetItem(
                    [f"{project_name.upper()} ({project_status['overall_state']})"],
                )

                # Processes
                proc_item = QTreeWidgetItem(["Processes"])
                for proc_name, state in project_status["processes"]["details"].items():
                    QTreeWidgetItem(proc_item, [f"{proc_name}: {state}"])
                project_item.addChild(proc_item)

                # Resources
                res_item = QTreeWidgetItem(["Resources"])
                for res_name, state in project_status["resources"]["details"].items():
                    QTreeWidgetItem(res_item, [f"{res_name}: {state}"])
                project_item.addChild(res_item)

                self.status_tree.addTopLevelItem(project_item)

            # Expand all items
            self.status_tree.expandAll()

        def _update_mt_status(self):
            """
            Update multi-tenant status display.
            """
            try:
                mt_status = self.control_center.multi_tenant_manager.get_global_status()
                status_text = self._build_mt_status_text(mt_status)
                self.infra_text.setPlainText(status_text)
            except Exception as e:
                self.infra_text.setPlainText(f"Error loading multi-tenant status: {e}")

        def _build_mt_status_text(self, mt_status):
            """
            Build the multi-tenant status text content.
            """
            status_text = "Multi-Tenant Infrastructure Status\n"
            status_text += "=" * 40 + "\n\n"

            # Add infrastructure summary
            status_text += self._build_infrastructure_summary(mt_status["infrastructure"])

            # Add project breakdown
            status_text += self._build_project_breakdown(mt_status)

            return status_text

        def _build_infrastructure_summary(self, infra):
            """
            Build infrastructure summary section.
            """
            summary = f"Active Fallback Servers: {infra['active_fallback_servers']}\n"
            summary += f"Active Proxy Servers: {infra['active_proxy_servers']}\n"
            summary += f"Total Tunnels: {infra['total_tunnels']}\n\n"
            return summary

        def _build_project_breakdown(self, mt_status):
            """
            Build project breakdown section.
            """
            breakdown = "Project Breakdown:\n"
            breakdown += "-" * 20 + "\n"

            for project, fallback_info in mt_status["fallbacks"].items():
                breakdown += f"\n{project.upper()}:\n"
                breakdown += self._build_project_fallback_info(fallback_info)
                breakdown += self._build_project_proxy_info(mt_status["proxies"].get(project, {}))
                breakdown += self._build_project_tunnel_info(mt_status["tunnels"].get(project, {}))

            return breakdown

        def _build_project_fallback_info(self, fallback_info):
            """
            Build fallback server information for a project.
            """
            status = "Active" if fallback_info["active"] else "Inactive"
            return f"  Fallback Port: {fallback_info['port']} ({status})\n"

        def _build_project_proxy_info(self, proxy_info):
            """
            Build proxy server information for a project.
            """
            if not proxy_info:
                return ""

            status = "Active" if proxy_info["active"] else "Inactive"
            info = f"  Proxy Port: {proxy_info['port']} ({status})\n"
            info += f"  Upstreams: {proxy_info['upstreams']}\n"
            return info

        def _build_project_tunnel_info(self, tunnel_info):
            """
            Build tunnel information for a project.
            """
            if not tunnel_info:
                return ""

            info = f"  Tunnels: {len(tunnel_info)}\n"
            for service, tunnel in tunnel_info.items():
                info += f"    {service}: {tunnel['hostname']}\n"
            return info

else:
    # Fallback classes when PyQt is not available
    class ProjectLauncherWidget:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("PyQt6 not available")

    class MonitoringWidget:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("PyQt6 not available")

    class TerminalWidget:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("PyQt6 not available")

    class StatusWidget:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("PyQt6 not available")
