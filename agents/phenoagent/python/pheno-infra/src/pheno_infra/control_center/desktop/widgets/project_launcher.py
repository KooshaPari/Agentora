"""Project Launcher Widget Module.

Provides project launching functionality with start/stop controls and project status
display.
"""

import logging
from typing import Any

try:
    from PyQt6.QtCore import Qt, pyqtSignal
    from PyQt6.QtWidgets import (
        QHBoxLayout,
        QLabel,
        QListWidget,
        QListWidgetItem,
        QProgressBar,
        QPushButton,
        QVBoxLayout,
        QWidget,
    )

    HAS_PYQT = True
except ImportError:
    HAS_PYQT = False

logger = logging.getLogger(__name__)


if HAS_PYQT:

    class ProjectLauncherWidget(QWidget):
        """
        Widget for launching and managing projects.
        """

        project_started = pyqtSignal(str)
        project_stopped = pyqtSignal(str)
        project_selected = pyqtSignal(str)

        def __init__(self, control_center):
            super().__init__()
            self.control_center = control_center
            self._selected_project: str | None = None
            self._init_ui()

        def _init_ui(self):
            """
            Initialize the user interface.
            """
            layout = QVBoxLayout(self)
            layout.setContentsMargins(10, 10, 10, 10)

            # Header
            header_layout = QHBoxLayout()
            title_label = QLabel("Projects")
            title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
            header_layout.addWidget(title_label)
            header_layout.addStretch()

            # Refresh button
            refresh_button = QPushButton("🔄")
            refresh_button.setToolTip("Refresh projects")
            refresh_button.clicked.connect(self.refresh_projects)
            refresh_button.setFixedSize(30, 30)
            header_layout.addWidget(refresh_button)

            layout.addLayout(header_layout)

            # Projects list
            self.projects_list = QListWidget()
            self.projects_list.setAlternatingRowColors(True)
            self.projects_list.itemClicked.connect(self.on_project_selected)
            layout.addWidget(self.projects_list)

            # Project actions
            actions_layout = QHBoxLayout()

            self.start_button = QPushButton("Start")
            self.start_button.setEnabled(False)
            self.start_button.clicked.connect(self.start_selected_project)
            actions_layout.addWidget(self.start_button)

            self.stop_button = QPushButton("Stop")
            self.stop_button.setEnabled(False)
            self.stop_button.clicked.connect(self.stop_selected_project)
            actions_layout.addWidget(self.stop_button)

            layout.addLayout(actions_layout)

            # Status area
            self.status_label = QLabel("Select a project")
            layout.addWidget(self.status_label)

            # Progress bar
            self.progress_bar = QProgressBar()
            self.progress_bar.setVisible(False)
            layout.addWidget(self.progress_bar)

            layout.addStretch()

        def refresh_projects(self):
            """
            Refresh the projects list.
            """
            self.projects_list.clear()

            # Get registered projects
            projects = self.control_center.project_registry.get_all_projects()

            for project_id, project_config in projects.items():
                item = QListWidgetItem(project_config.get("name", project_id))
                item.setData(Qt.ItemDataRole.UserRole, project_id)
                self.projects_list.addItem(item)

            self._update_project_actions()

        def on_project_selected(self, item):
            """
            Handle project selection.
            """
            project_id = item.data(Qt.ItemDataRole.UserRole)
            self._selected_project = project_id
            self.project_selected.emit(project_id)
            self._update_project_actions()

        def start_selected_project(self):
            """
            Start the selected project.
            """
            if self._selected_project:
                self.start_button.setEnabled(False)
                self.progress_bar.setVisible(True)
                self.progress_bar.setRange(0, 0)  # Indeterminate progress

                try:
                    # Start project via control center
                    project = self.control_center.project_registry.get_project(
                        self._selected_project,
                    )
                    if project:
                        # Implementation depends on CLI bridge integration
                        self.project_started.emit(self._selected_project)
                        self.status_label.setText(
                            f"Starting {project.get('name', self._selected_project)}",
                        )
                    else:
                        self.status_label.setText("Project not found")
                except Exception as e:
                    logger.exception(f"Failed to start project {self._selected_project}: {e}")
                    self.status_label.setText(f"Error: {e}")
                finally:
                    self.progress_bar.setVisible(False)
                    self._update_project_actions()

        def stop_selected_project(self):
            """
            Stop the selected project.
            """
            if self._selected_project:
                self.stop_button.setEnabled(False)
                self.progress_bar.setVisible(True)
                self.progress_bar.setRange(0, 0)  # Indeterminate progress

                try:
                    # Stop project via control center
                    project = self.control_center.project_registry.get_project(
                        self._selected_project,
                    )
                    if project:
                        # Implementation depends on CLI bridge integration
                        self.project_stopped.emit(self._selected_project)
                        self.status_label.setText(
                            f"Stopping {project.get('name', self._selected_project)}",
                        )
                    else:
                        self.status_label.setText("Project not found")
                except Exception as e:
                    logger.exception(f"Failed to stop project {self._selected_project}: {e}")
                    self.status_label.setText(f"Error: {e}")
                finally:
                    self.progress_bar.setVisible(False)
                    self._update_project_actions()

        def _update_project_actions(self):
            """
            Update action button states.
            """
            has_selection = self._selected_project is not None
            self.start_button.setEnabled(has_selection)
            self.stop_button.setEnabled(has_selection)

            if has_selection:
                self.status_label.setText(f"Selected: {self._selected_project}")
            else:
                self.status_label.setText("Select a project")

        def update_status(self, global_status: dict[str, Any]):
            """
            Update widget status from monitoring data.
            """
            if not hasattr(self, "projects_list") or not hasattr(self, "_selected_project"):
                return

            projects_status = global_status.get("projects", {})

            # Update project status indicators
            for i in range(self.projects_list.count()):
                item = self.projects_list.item(i)
                project_id = item.data(Qt.ItemDataRole.UserRole)

                if project_id in projects_status:
                    project_status = projects_status[project_id]
                    status_text = project_status.get("status", "unknown")

                    # Update item text with status indicator
                    base_text = item.text().split(" [")[0]  # Remove existing status
                    item.setText(f"{base_text} [{status_text}]")

                    # Color coding based on status
                    if status_text == "running":
                        item.setBackground(Qt.GlobalColor.green.lighter(90))
                    elif status_text == "stopped":
                        item.setBackground(Qt.GlobalColor.gray.lighter(90))
                    elif status_text == "error":
                        item.setBackground(Qt.GlobalColor.red.lighter(90))
                    elif status_text == "starting":
                        item.setBackground(Qt.GlobalColor.yellow.lighter(90))
                    else:
                        item.setBackground(Qt.GlobalColor.white)

else:
    # Fallback when PyQt is not available
    class ProjectLauncherWidget:
        def __init__(self, *args, **kwargs):
            raise RuntimeError(
                "PyQt6 is not available. Please install PyQt6 to use the desktop GUI.",
            )
