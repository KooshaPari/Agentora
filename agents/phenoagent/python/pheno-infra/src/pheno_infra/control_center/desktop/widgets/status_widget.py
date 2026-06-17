"""Status Widget Module.

Provides detailed system status and health monitoring display.
"""

import logging
from datetime import datetime
from typing import Any

try:
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal
    from PyQt6.QtGui import QBrush, QColor
    from PyQt6.QtWidgets import (
        QGridLayout,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QProgressBar,
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

    class StatusWidget(QWidget):
        """
        Widget for displaying detailed system status.
        """

        refresh_requested = pyqtSignal()

        def __init__(self, control_center):
            super().__init__()
            self.control_center = control_center
            self._last_update = datetime.now()
            self._init_ui()
            self._start_refresh_timer()

        def _init_ui(self):
            """
            Initialize the user interface.
            """
            layout = QVBoxLayout(self)
            layout.setContentsMargins(10, 10, 10, 10)

            # Header
            header_layout = QHBoxLayout()
            title_label = QLabel("System Status")
            title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
            header_layout.addWidget(title_label)
            header_layout.addStretch()

            # Last update label
            self.last_update_label = QLabel("Last update: Never")
            self.last_update_label.setStyleSheet("color: gray; font-size: 10px;")
            header_layout.addWidget(self.last_update_label)

            # Manual refresh button
            refresh_button = QLabel("🔄")
            refresh_button.setToolTip("Click to refresh manually")
            refresh_button.setStyleSheet("font-size: 16px; cursor: pointer;")
            refresh_button.mousePressEvent = self._manual_refresh
            header_layout.addWidget(refresh_button)

            layout.addLayout(header_layout)

            # Tab widget for different status views
            self.tab_widget = QTabWidget()

            # Overview tab
            overview_widget = self._create_overview_tab()
            self.tab_widget.addTab(overview_widget, "Overview")

            # Details tab
            details_widget = self._create_details_tab()
            self.tab_widget.addTab(details_widget, "Details")

            # Logs tab
            logs_widget = self._create_logs_tab()
            self.tab_widget.addTab(logs_widget, "Logs")

            layout.addWidget(self.tab_widget)

        def _create_overview_tab(self) -> QWidget:
            """
            Create overview tab with system summary.
            """
            widget = QWidget()
            layout = QGridLayout(widget)
            layout.setSpacing(15)

            # System health
            health_group = QGroupBox("System Health")
            health_layout = QVBoxLayout(health_group)

            self.health_indicator = QLabel("⚪")
            self.health_indicator.setStyleSheet("font-size: 48px; text-align: center;")
            health_layout.addWidget(self.health_indicator)

            self.health_label = QLabel("Unknown")
            self.health_label.setStyleSheet("font-weight: bold; text-align: center;")
            health_layout.addWidget(self.health_label)

            self.health_details = QLabel("No status data available")
            self.health_details.setStyleSheet("color: gray; text-align: center;")
            health_layout.addWidget(self.health_details)

            layout.addWidget(health_group, 0, 0)

            # Project statistics
            projects_group = QGroupBox("Projects")
            projects_layout = QVBoxLayout(projects_group)

            self.total_projects_label = QLabel("Total: 0")
            projects_layout.addWidget(self.total_projects_label)

            self.healthy_projects_label = QLabel("Healthy: 0")
            self.healthy_projects_label.setStyleSheet("color: green;")
            projects_layout.addWidget(self.healthy_projects_label)

            self.warning_projects_label = QLabel("Warning: 0")
            self.warning_projects_label.setStyleSheet("color: orange;")
            projects_layout.addWidget(self.warning_projects_label)

            self.critical_projects_label = QLabel("Critical: 0")
            self.critical_projects_label.setStyleSheet("color: red;")
            projects_layout.addWidget(self.critical_projects_label)

            layout.addWidget(projects_group, 0, 1)

            # Process statistics
            processes_group = QGroupBox("Processes")
            processes_layout = QVBoxLayout(processes_group)

            self.total_processes_label = QLabel("Total: 0")
            processes_layout.addWidget(self.total_processes_label)

            self.running_processes_label = QLabel("Running: 0")
            self.running_processes_label.setStyleSheet("color: green;")
            processes_layout.addWidget(self.running_processes_label)

            self.stopped_processes_label = QLabel("Stopped: 0")
            self.stopped_processes_label.setStyleSheet("color: gray;")
            processes_layout.addWidget(self.stopped_processes_label)

            self.error_processes_label = QLabel("Errors: 0")
            self.error_processes_label.setStyleSheet("color: red;")
            processes_layout.addWidget(self.error_processes_label)

            layout.addWidget(processes_group, 1, 0)

            # Resource usage
            resources_group = QGroupBox("Resources")
            resources_layout = QVBoxLayout(resources_group)

            # CPU usage
            cpu_layout = QHBoxLayout()
            cpu_label = QLabel("CPU:")
            cpu_layout.addWidget(cpu_label)

            self.cpu_progress = QProgressBar()
            self.cpu_progress.setRange(0, 100)
            self.cpu_progress.setValue(0)
            cpu_layout.addWidget(self.cpu_progress)

            self.cpu_label = QLabel("0%")
            cpu_layout.addWidget(self.cpu_label)
            cpu_layout.addStretch()
            resources_layout.addLayout(cpu_layout)

            # Memory usage
            memory_layout = QHBoxLayout()
            memory_label = QLabel("Memory:")
            memory_layout.addWidget(memory_label)

            self.memory_progress = QProgressBar()
            self.memory_progress.setRange(0, 100)
            self.memory_progress.setValue(0)
            memory_layout.addWidget(self.memory_progress)

            self.memory_label = QLabel("0 MB")
            memory_layout.addWidget(self.memory_label)
            memory_layout.addStretch()
            resources_layout.addLayout(memory_layout)

            layout.addWidget(resources_group, 1, 1)

            return widget

        def _create_details_tab(self) -> QWidget:
            """
            Create details tab with detailed information.
            """
            widget = QWidget()
            layout = QVBoxLayout(widget)

            # Projects tree
            self.projects_tree = QTreeWidget()
            self.projects_tree.setColumnCount(5)
            self.projects_tree.setHeaderLabels(["Project", "Status", "Processes", "CPU", "Memory"])
            self.projects_tree.setAlternatingRowColors(True)
            layout.addWidget(self.projects_tree)

            return widget

        def _create_logs_tab(self) -> QWidget:
            """
            Create logs tab with recent activity.
            """
            widget = QWidget()
            layout = QVBoxLayout(widget)

            # Logs tree
            self.logs_tree = QTreeWidget()
            self.logs_tree.setColumnCount(4)
            self.logs_tree.setHeaderLabels(["Time", "Level", "Project", "Message"])
            self.logs_tree.setAlternatingRowColors(True)
            layout.addWidget(self.logs_tree)

            return widget

        def _start_refresh_timer(self):
            """
            Start timer for automatic refresh.
            """
            self.refresh_timer = QTimer()
            self.refresh_timer.timeout.connect(self.refresh_status)
            self.refresh_timer.start(5000)  # Refresh every 5 seconds

        def _manual_refresh(self, event):
            """
            Handle manual refresh.
            """
            self.refresh_requested.emit()
            self.refresh_status()

        def update_status(self, global_status: dict[str, Any]):
            """
            Update status display from monitoring data.
            """
            self._last_update = datetime.now()

            # Update last update time
            if hasattr(self, "last_update_label"):
                self.last_update_label.setText(
                    f"Last update: {self._last_update.strftime('%H:%M:%S')}",
                )

            summary = global_status.get("summary", {})
            projects_status = global_status.get("projects", {})

            # Update overview tab
            self._update_overview(summary)

            # Update details tab
            self._update_details(projects_status)

            # Update logs tab
            self._update_logs(global_status.get("logs", []))

        def _update_overview(self, summary: dict[str, Any]):
            """
            Update overview tab.
            """
            if not all(
                hasattr(self, attr)
                for attr in [
                    "health_indicator",
                    "health_label",
                    "health_details",
                    "total_projects_label",
                    "healthy_projects_label",
                    "warning_projects_label",
                    "critical_projects_label",
                    "total_processes_label",
                    "running_processes_label",
                    "stopped_processes_label",
                    "error_processes_label",
                    "cpu_progress",
                    "cpu_label",
                    "memory_progress",
                    "memory_label",
                ]
            ):
                return

            total_projects = summary.get("total_projects", 0)
            healthy_projects = summary.get("healthy_projects", 0)
            warning_projects = summary.get("warning_projects", 0)
            critical_projects = summary.get("critical_projects", 0)

            total_processes = summary.get("total_processes", 0)
            running_processes = summary.get("running_processes", 0)
            stopped_processes = summary.get("stopped_processes", 0)
            error_processes = summary.get("error_processes", 0)

            cpu_percent = summary.get("cpu_percent", 0)
            memory_mb = summary.get("memory_mb", 0)
            memory_percent = summary.get("memory_percent", 0)

            # System health
            if total_projects == 0:
                self.health_indicator.setText("⚪")
                self.health_label.setText("No Projects")
                self.health_details.setText("No projects configured")
            elif critical_projects > 0:
                self.health_indicator.setText("🔴")
                self.health_label.setText("Critical")
                self.health_details.setText(f"{critical_projects} critical projects")
            elif warning_projects > 0:
                self.health_indicator.setText("🟡")
                self.health_label.setText("Warning")
                self.health_details.setText(f"{warning_projects} warning projects")
            else:
                self.health_indicator.setText("🟢")
                self.health_label.setText("Healthy")
                self.health_details.setText("All systems operational")

            # Project statistics
            self.total_projects_label.setText(f"Total: {total_projects}")
            self.healthy_projects_label.setText(f"Healthy: {healthy_projects}")
            self.warning_projects_label.setText(f"Warning: {warning_projects}")
            self.critical_projects_label.setText(f"Critical: {critical_projects}")

            # Process statistics
            self.total_processes_label.setText(f"Total: {total_processes}")
            self.running_processes_label.setText(f"Running: {running_processes}")
            self.stopped_processes_label.setText(f"Stopped: {stopped_processes}")
            self.error_processes_label.setText(f"Errors: {error_processes}")

            # Resource usage
            self.cpu_progress.setValue(int(cpu_percent))
            self.cpu_label.setText(f"{cpu_percent:.1f}%")

            self.memory_progress.setValue(int(memory_percent))
            self.memory_label.setText(f"{memory_mb:.1f} MB")

        def _update_details(self, projects_status: dict[str, Any]):
            """
            Update details tab with project information.
            """
            if not hasattr(self, "projects_tree"):
                return

            self.projects_tree.clear()

            for project_id, status in projects_status.items():
                project_item = QTreeWidgetItem(
                    [
                        project_id,
                        status.get("status", "unknown"),
                        str(len(status.get("processes", []))),
                        f"{status.get('cpu_percent', 0):.1f}%",
                        f"{status.get('memory_mb', 0):.1f} MB",
                    ],
                )

                # Color code based on status
                project_status = status.get("status", "unknown")
                if project_status == "running":
                    project_item.setBackground(1, QBrush(QColor(144, 238, 144)))  # Light green
                elif project_status == "stopped":
                    project_item.setBackground(1, QBrush(QColor(211, 211, 211)))  # Light gray
                elif project_status == "error":
                    project_item.setBackground(1, QBrush(QColor(255, 182, 193)))  # Light red
                elif project_status == "starting":
                    project_item.setBackground(1, QBrush(QColor(255, 255, 153)))  # Light yellow

                # Add process children
                for process_id, process_status in status.get("processes", {}).items():
                    process_item = QTreeWidgetItem(
                        [
                            f"  └─ {process_id}",
                            process_status.get("status", "unknown"),
                            "",
                            f"{process_status.get('cpu_percent', 0):.1f}%",
                            f"{process_status.get('memory_mb', 0):.1f} MB",
                        ],
                    )
                    project_item.addChild(process_item)

                self.projects_tree.addTopLevelItem(project_item)

            # Resize columns
            for i in range(self.projects_tree.columnCount()):
                self.projects_tree.resizeColumnToContents(i)

        def _update_logs(self, logs: list):
            """
            Update logs tab with recent activity.
            """
            if not hasattr(self, "logs_tree"):
                return

            self.logs_tree.clear()

            # Add recent logs (last 50)
            for log_entry in logs[-50:]:
                time_str = log_entry.get("timestamp", "Unknown")
                level = log_entry.get("level", "INFO")
                project = log_entry.get("project", "System")
                message = log_entry.get("message", "No message")

                log_item = QTreeWidgetItem([time_str, level, project, message])

                # Color code based on log level
                if level == "ERROR":
                    log_item.setBackground(1, QBrush(QColor(255, 182, 193)))  # Light red
                elif level == "WARNING":
                    log_item.setBackground(1, QBrush(QColor(255, 255, 153)))  # Light yellow

                self.logs_tree.addTopLevelItem(log_item)

            # Resize columns
            for i in range(self.logs_tree.columnCount()):
                self.logs_tree.resizeColumnToContents(i)

        def refresh_status(self):
            """
            Manually refresh status.
            """
            # Force immediate status update
            if hasattr(self.control_center, "monitor_engine"):
                global_status = self.control_center.monitor_engine.get_global_status()
                self.update_status(global_status)

else:
    # Fallback when PyQt is not available
    class StatusWidget:
        def __init__(self, *args, **kwargs):
            raise RuntimeError(
                "PyQt6 is not available. Please install PyQt6 to use the desktop GUI.",
            )
