"""Monitoring Widget Module.

Provides real-time monitoring display for project status, process monitoring, and health
indicators.
"""

import logging
from typing import Any

try:
    from PyQt6.QtCore import Qt, pyqtSignal
    from PyQt6.QtGui import QBrush, QColor
    from PyQt6.QtWidgets import (
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QProgressBar,
        QTableWidget,
        QTableWidgetItem,
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

    class MonitoringWidget(QWidget):
        """
        Widget for monitoring project and process status.
        """

        project_double_clicked = pyqtSignal(str)
        process_double_clicked = pyqtSignal(str, str)

        def __init__(self, control_center):
            super().__init__()
            self.control_center = control_center
            self._init_ui()

        def _init_ui(self):
            """
            Initialize the user interface.
            """
            layout = QVBoxLayout(self)
            layout.setContentsMargins(10, 10, 10, 10)

            # Header
            header_layout = QHBoxLayout()
            title_label = QLabel("Monitoring")
            title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
            header_layout.addWidget(title_label)
            header_layout.addStretch()

            # Refresh button
            refresh_button = QLabel("🔄")
            refresh_button.setToolTip("Auto-refreshing every 2 seconds")
            refresh_button.setStyleSheet("font-size: 16px;")
            header_layout.addWidget(refresh_button)

            layout.addLayout(header_layout)

            # Projects table
            self.projects_table = QTableWidget()
            self.projects_table.setColumnCount(4)
            self.projects_table.setHorizontalHeaderLabels(
                ["Project", "Status", "Processes", "Health"],
            )
            self.projects_table.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.Stretch,
            )
            self.projects_table.setAlternatingRowColors(True)
            self.projects_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            self.projects_table.doubleClicked.connect(self.on_project_double_click)
            layout.addWidget(self.projects_table)

            # Processes tree
            layout.addSpacing(10)
            processes_label = QLabel("Processes")
            processes_label.setStyleSheet("font-weight: bold;")
            layout.addWidget(processes_label)

            self.processes_tree = QTreeWidget()
            self.processes_tree.setColumnCount(4)
            self.processes_tree.setHeaderLabels(["Name", "Status", "CPU", "Memory"])
            self.processes_tree.setAlternatingRowColors(True)
            self.processes_tree.doubleClicked.connect(self.on_process_double_click)
            layout.addWidget(self.processes_tree)

            # Status summary
            layout.addSpacing(10)
            summary_label = QLabel("System Summary")
            summary_label.setStyleSheet("font-weight: bold;")
            layout.addWidget(summary_label)

            summary_layout = QHBoxLayout()

            self.health_indicator = QLabel("🟢")
            self.health_indicator.setStyleSheet("font-size: 24px;")
            summary_layout.addWidget(self.health_indicator)

            self.summary_label = QLabel("No data")
            summary_layout.addWidget(self.summary_label)
            summary_layout.addStretch()

            layout.addLayout(summary_layout)

        def update_status(self, global_status: dict[str, Any]):
            """
            Update monitoring display from status data.
            """
            if not hasattr(self, "projects_table") or not hasattr(self, "processes_tree"):
                return

            summary = global_status.get("summary", {})
            projects_status = global_status.get("projects", {})
            processes_status = global_status.get("processes", {})

            # Update projects table
            self._update_projects_table(projects_status)

            # Update processes tree
            self._update_processes_tree(processes_status)

            # Update summary
            self._update_summary(summary)

        def _update_projects_table(self, projects_status: dict[str, Any]):
            """
            Update projects table with status data.
            """
            self.projects_table.setRowCount(len(projects_status))

            for row, (project_id, status) in enumerate(projects_status.items()):
                # Project name
                name_item = QTableWidgetItem(status.get("name", project_id))
                name_item.setData(Qt.ItemDataRole.UserRole, project_id)
                self.projects_table.setItem(row, 0, name_item)

                # Status
                status_text = status.get("status", "unknown")
                status_item = QTableWidgetItem(status_text)
                status_item.setBackground(self._get_status_color(status_text))
                self.projects_table.setItem(row, 1, status_item)

                # Processes count
                processes_count = len(status.get("processes", []))
                processes_item = QTableWidgetItem(str(processes_count))
                self.projects_table.setItem(row, 2, processes_item)

                # Health
                health_status = status.get("health", "unknown")
                health_item = QTableWidgetItem(health_status)
                health_item.setBackground(self._get_health_color(health_status))
                self.projects_table.setItem(row, 3, health_item)

        def _update_processes_tree(self, processes_status: dict[str, Any]):
            """
            Update processes tree with status data.
            """
            self.processes_tree.clear()

            # Group processes by project
            projects = {}
            for process_id, process_status in processes_status.items():
                project_id = process_status.get("project_id", "unknown")
                if project_id not in projects:
                    projects[project_id] = []
                projects[project_id].append((process_id, process_status))

            # Add projects and processes to tree
            for project_id, project_processes in projects.items():
                project_item = QTreeWidgetItem([project_id, "", "", ""])
                self.processes_tree.addTopLevelItem(project_item)

                for process_id, process_status in project_processes:
                    process_item = QTreeWidgetItem(
                        [
                            process_id,
                            process_status.get("status", "unknown"),
                            f"{process_status.get('cpu_percent', 0):.1f}%",
                            f"{process_status.get('memory_mb', 0):.1f}MB",
                        ],
                    )

                    # Color code based on status
                    status = process_status.get("status", "unknown")
                    process_item.setBackground(1, QBrush(self._get_status_color(status)))

                    project_item.addChild(process_item)

                project_item.setExpanded(True)

            # Resize columns
            for i in range(self.processes_tree.columnCount()):
                self.processes_tree.resizeColumnToContents(i)

        def _update_summary(self, summary: dict[str, Any]):
            """
            Update system summary display.
            """
            if not hasattr(self, "health_indicator") or not hasattr(self, "summary_label"):
                return

            total_projects = summary.get("total_projects", 0)
            healthy_projects = summary.get("healthy_projects", 0)
            total_processes = summary.get("total_processes", 0)
            running_processes = summary.get("running_processes", 0)

            # Set health indicator
            if total_projects == 0:
                self.health_indicator.setText("⚪")
                summary_text = "No projects configured"
            elif healthy_projects == total_projects:
                self.health_indicator.setText("🟢")
                summary_text = "All systems operational"
            elif healthy_projects > total_projects / 2:
                self.health_indicator.setText("🟡")
                summary_text = "Partial systems operational"
            else:
                self.health_indicator.setText("🔴")
                summary_text = "Multiple systems down"

            # Update summary text
            summary_text += f" | Projects: {healthy_projects}/{total_projects} healthy"
            summary_text += f" | Processes: {running_processes}/{total_processes} running"
            self.summary_label.setText(summary_text)

        def _get_status_color(self, status: str) -> QColor:
            """
            Get color for status indicator.
            """
            if status == "running":
                return QColor(144, 238, 144)  # Light green
            if status == "stopped":
                return QColor(211, 211, 211)  # Light gray
            if status == "error":
                return QColor(255, 182, 193)  # Light red
            if status == "starting":
                return QColor(255, 255, 153)  # Light yellow
            return QColor(255, 255, 255)  # White

        def _get_health_color(self, health: str) -> QColor:
            """
            Get color for health indicator.
            """
            if health == "healthy":
                return QColor(144, 238, 144)  # Light green
            if health == "warning":
                return QColor(255, 255, 153)  # Light yellow
            if health == "critical":
                return QColor(255, 182, 193)  # Light red
            return QColor(211, 211, 211)  # Light gray

        def on_project_double_click(self, index):
            """
            Handle project double click.
            """
            if index.isValid():
                item = self.projects_table.item(index.row(), 0)
                if item:
                    project_id = item.data(Qt.ItemDataRole.UserRole)
                    self.project_double_clicked.emit(project_id)

        def on_process_double_click(self, item, column):
            """
            Handle process double click.
            """
            if item.parent():  # Process item (child of project)
                project_id = item.parent().text(0)
                process_id = item.text(0)
                self.process_double_clicked.emit(project_id, process_id)

else:
    # Fallback when PyQt is not available
    class MonitoringWidget:
        def __init__(self, *args, **kwargs):
            raise RuntimeError(
                "PyQt6 is not available. Please install PyQt6 to use the desktop GUI.",
            )
