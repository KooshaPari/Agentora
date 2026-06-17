"""PyQt dialog classes for Pheno Control Center desktop application.

Provides dialog windows for project configuration, application settings, and about
information display.
"""

import logging
from pathlib import Path

try:
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QFont
    from PyQt6.QtWidgets import (
        QCheckBox,
        QDialog,
        QDialogButtonBox,
        QFileDialog,
        QFormLayout,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QListWidget,
        QListWidgetItem,
        QMessageBox,
        QPushButton,
        QSpinBox,
        QTabWidget,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )

    HAS_PYQT = True
except ImportError:
    HAS_PYQT = False

if HAS_PYQT:
    from ..config import ProjectConfig, ProjectRegistry

logger = logging.getLogger(__name__)


if HAS_PYQT:

    class ProjectConfigDialog(QDialog):
        """
        Dialog for creating/editing project configurations.
        """

        def __init__(self, parent=None, project_config=None):
            super().__init__(parent)
            self.project_config = project_config
            self.editing_mode = project_config is not None

            self.setWindowTitle(
                "Project Configuration" if not self.editing_mode else f"Edit {project_config.name}",
            )
            self.setModal(True)
            self.resize(500, 600)

            self._init_ui()

            if self.editing_mode:
                self._populate_fields()

        def _init_ui(self):
            """
            Initialize the user interface.
            """
            layout = QVBoxLayout(self)

            tab_widget = self._create_tab_widget()
            layout.addWidget(tab_widget)

            button_box = self._create_button_box()
            layout.addWidget(button_box)

        def _create_tab_widget(self) -> QTabWidget:
            """
            Create and configure the tab widget.
            """
            tab_widget = QTabWidget()

            # Add tabs
            tab_widget.addTab(self._create_basic_tab(), "Basic")
            tab_widget.addTab(self._create_advanced_tab(), "Advanced")
            tab_widget.addTab(self._create_environment_tab(), "Environment")

            return tab_widget

        def _create_button_box(self) -> QDialogButtonBox:
            """
            Create and configure the button box.
            """
            button_box = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            )
            button_box.accepted.connect(self.accept)
            button_box.rejected.connect(self.reject)
            return button_box

        def _create_basic_tab(self):
            """
            Create basic settings tab.
            """
            widget = QWidget()
            layout = QFormLayout(widget)

            self._add_basic_fields(layout)
            self._add_optional_fields(layout)
            self._add_checkbox_fields(layout)

            return widget

        def _add_basic_fields(self, layout: QFormLayout):
            """
            Add basic required fields to the layout.
            """
            # Project name
            self.name_edit = QLineEdit()
            layout.addRow("Project Name:", self.name_edit)

            # CLI entry command
            self.cli_entry_edit = QLineEdit()
            self.cli_entry_edit.setPlaceholderText("e.g., atoms start")
            layout.addRow("CLI Entry:", self.cli_entry_edit)

            # Base port
            self.base_port_spin = QSpinBox()
            self.base_port_spin.setRange(1024, 65535)
            self.base_port_spin.setValue(50000)
            layout.addRow("Base Port:", self.base_port_spin)

        def _add_optional_fields(self, layout: QFormLayout):
            """
            Add optional configuration fields to the layout.
            """
            # Health endpoint
            self.health_endpoint_edit = QLineEdit()
            self.health_endpoint_edit.setPlaceholderText("/health")
            layout.addRow("Health Endpoint:", self.health_endpoint_edit)

            # Tunnel domain
            self.tunnel_domain_edit = QLineEdit()
            self.tunnel_domain_edit.setText("kooshapari.com")
            layout.addRow("Tunnel Domain:", self.tunnel_domain_edit)

        def _add_checkbox_fields(self, layout: QFormLayout):
            """
            Add checkbox fields to the layout.
            """
            # Auto start
            self.auto_start_check = QCheckBox("Auto-start this project")
            layout.addRow("", self.auto_start_check)

        def _create_advanced_tab(self):
            """
            Create advanced settings tab.
            """
            widget = QWidget()
            layout = QFormLayout(widget)

            self._add_port_offset_fields(layout)
            self._add_working_directory_field(layout)
            self._add_dependencies_field(layout)

            return widget

        def _add_port_offset_fields(self, layout: QFormLayout):
            """
            Add port offset configuration fields to the layout.
            """
            # Fallback port offset
            self.fallback_port_offset_spin = QSpinBox()
            self.fallback_port_offset_spin.setRange(0, 1000)
            layout.addRow("Fallback Port Offset:", self.fallback_port_offset_spin)

            # Proxy port offset
            self.proxy_port_offset_spin = QSpinBox()
            self.proxy_port_offset_spin.setRange(0, 1000)
            layout.addRow("Proxy Port Offset:", self.proxy_port_offset_spin)

        def _add_working_directory_field(self, layout: QFormLayout):
            """
            Add working directory field with browse button.
            """
            working_dir_layout = QHBoxLayout()
            self.working_dir_edit = QLineEdit()
            browse_button = QPushButton("Browse...")
            browse_button.clicked.connect(self._browse_working_directory)
            working_dir_layout.addWidget(self.working_dir_edit)
            working_dir_layout.addWidget(browse_button)
            layout.addRow("Working Directory:", working_dir_layout)

        def _add_dependencies_field(self, layout: QFormLayout):
            """
            Add dependencies list with add/remove buttons.
            """
            self.dependencies_list = QListWidget()
            self.dependencies_list.setMaximumHeight(100)

            deps_layout = QVBoxLayout()
            deps_layout.addWidget(self.dependencies_list)

            deps_button_layout = QHBoxLayout()
            add_dep_button = QPushButton("Add Dependency")
            add_dep_button.clicked.connect(self._add_dependency)
            remove_dep_button = QPushButton("Remove")
            remove_dep_button.clicked.connect(self._remove_dependency)
            deps_button_layout.addWidget(add_dep_button)
            deps_button_layout.addWidget(remove_dep_button)
            deps_layout.addLayout(deps_button_layout)

            deps_widget = QWidget()
            deps_widget.setLayout(deps_layout)
            layout.addRow("Dependencies:", deps_widget)

        def _create_environment_tab(self):
            """
            Create environment variables tab.
            """
            widget = QWidget()
            layout = QVBoxLayout(widget)

            label = QLabel("Environment Variables:")
            layout.addWidget(label)

            # Environment variables text area
            self.env_vars_edit = QTextEdit()
            self.env_vars_edit.setPlaceholderText(
                "Enter environment variables in KEY=VALUE format, one per line:\n\n"
                "DEBUG=true\n"
                "API_PORT=3000\n"
                "DATABASE_URL=postgresql://...",
            )
            layout.addWidget(self.env_vars_edit)

            return widget

        def _browse_working_directory(self):
            """
            Browse for working directory.
            """
            directory = QFileDialog.getExistingDirectory(
                self, "Select Working Directory", str(Path.home()),
            )
            if directory:
                self.working_dir_edit.setText(directory)

        def _add_dependency(self):
            """
            Add a dependency to the list.
            """
            # In a real implementation, this would show a dialog to select from available projects
            dependency, ok = QLineEdit.getText(self, "Add Dependency", "Project name:")
            if ok and dependency.strip():
                item = QListWidgetItem(dependency.strip())
                self.dependencies_list.addItem(item)

        def _remove_dependency(self):
            """
            Remove selected dependency.
            """
            current_item = self.dependencies_list.currentItem()
            if current_item:
                self.dependencies_list.takeItem(self.dependencies_list.row(current_item))

        def _populate_fields(self):
            """
            Populate fields with existing project configuration.
            """
            config = self.project_config

            self.name_edit.setText(config.name)
            self.cli_entry_edit.setText(" ".join(config.cli_entry))
            self.base_port_spin.setValue(config.base_port)
            self.health_endpoint_edit.setText(config.health_endpoint or "")
            self.tunnel_domain_edit.setText(config.tunnel_domain or "")
            self.auto_start_check.setChecked(config.auto_start)

            self.fallback_port_offset_spin.setValue(config.fallback_port_offset)
            self.proxy_port_offset_spin.setValue(config.proxy_port_offset)
            self.working_dir_edit.setText(config.working_directory or "")

            # Dependencies
            for dep in config.dependencies:
                item = QListWidgetItem(dep)
                self.dependencies_list.addItem(item)

            # Environment variables
            env_text = "\n".join(f"{k}={v}" for k, v in config.env_vars.items())
            self.env_vars_edit.setPlainText(env_text)

        def get_project_config(self) -> ProjectConfig:
            """
            Get project configuration from dialog fields.
            """
            cli_entry = self._parse_cli_entry()
            env_vars = self._parse_environment_variables()
            dependencies = self._get_dependencies()

            return self._create_project_config(cli_entry, env_vars, dependencies)

        def _parse_cli_entry(self) -> list[str]:
            """
            Parse CLI entry from text field.
            """
            return self.cli_entry_edit.text().strip().split()

        def _parse_environment_variables(self) -> dict[str, str]:
            """
            Parse environment variables from text area.
            """
            env_vars = {}
            env_text = self.env_vars_edit.toPlainText().strip()

            if not env_text:
                return env_vars

            for line in env_text.split("\n"):
                line = line.strip()
                if "=" in line:
                    key, value = line.split("=", 1)
                    env_vars[key.strip()] = value.strip()

            return env_vars

        def _get_dependencies(self) -> list[str]:
            """
            Get dependencies from list widget.
            """
            dependencies = []
            for i in range(self.dependencies_list.count()):
                item = self.dependencies_list.item(i)
                dependencies.append(item.text())
            return dependencies

        def _create_project_config(
            self, cli_entry: list[str], env_vars: dict[str, str], dependencies: list[str],
        ) -> ProjectConfig:
            """
            Create ProjectConfig object from parsed values.
            """
            return ProjectConfig(
                name=self.name_edit.text().strip(),
                cli_entry=cli_entry,
                base_port=self.base_port_spin.value(),
                fallback_port_offset=self.fallback_port_offset_spin.value(),
                proxy_port_offset=self.proxy_port_offset_spin.value(),
                health_endpoint=self.health_endpoint_edit.text().strip() or None,
                tunnel_domain=self.tunnel_domain_edit.text().strip() or None,
                env_vars=env_vars,
                working_directory=self.working_dir_edit.text().strip() or None,
                auto_start=self.auto_start_check.isChecked(),
                dependencies=dependencies,
            )

        def accept(self):
            """
            Accept dialog with validation.
            """
            try:
                config = self.get_project_config()
                config.validate()
                super().accept()
            except Exception as e:
                QMessageBox.warning(self, "Validation Error", str(e))

    class SettingsDialog(QDialog):
        """
        Dialog for application settings.
        """

        def __init__(self, project_registry: ProjectRegistry, parent=None):
            super().__init__(parent)
            self.project_registry = project_registry

            self.setWindowTitle("Settings")
            self.setModal(True)
            self.resize(600, 500)

            self._init_ui()
            self._load_settings()

        def _init_ui(self):
            """
            Initialize the user interface.
            """
            layout = QVBoxLayout(self)

            # Create tab widget
            tab_widget = QTabWidget()

            # General settings tab
            general_tab = self._create_general_tab()
            tab_widget.addTab(general_tab, "General")

            # Projects tab
            projects_tab = self._create_projects_tab()
            tab_widget.addTab(projects_tab, "Projects")

            # Advanced tab
            advanced_tab = self._create_advanced_tab()
            tab_widget.addTab(advanced_tab, "Advanced")

            layout.addWidget(tab_widget)

            # Button box
            button_box = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Ok
                | QDialogButtonBox.StandardButton.Cancel
                | QDialogButtonBox.StandardButton.Apply,
            )
            button_box.accepted.connect(self.accept)
            button_box.rejected.connect(self.reject)
            button_box.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(
                self._apply_settings,
            )
            layout.addWidget(button_box)

        def _create_general_tab(self):
            """
            Create general settings tab.
            """
            widget = QWidget()
            layout = QFormLayout(widget)

            # Monitor refresh interval
            self.refresh_interval_spin = QSpinBox()
            self.refresh_interval_spin.setRange(1, 60)
            self.refresh_interval_spin.setValue(2)
            self.refresh_interval_spin.setSuffix(" seconds")
            layout.addRow("Monitor Refresh Interval:", self.refresh_interval_spin)

            # Log retention
            self.log_retention_spin = QSpinBox()
            self.log_retention_spin.setRange(1, 365)
            self.log_retention_spin.setValue(7)
            self.log_retention_spin.setSuffix(" days")
            layout.addRow("Log Retention:", self.log_retention_spin)

            # Enable desktop GUI
            self.enable_gui_check = QCheckBox("Enable desktop GUI")
            self.enable_gui_check.setChecked(True)
            layout.addRow("", self.enable_gui_check)

            # Enable TUI monitor
            self.enable_tui_check = QCheckBox("Enable TUI monitor")
            self.enable_tui_check.setChecked(True)
            layout.addRow("", self.enable_tui_check)

            return widget

        def _create_projects_tab(self):
            """
            Create projects management tab.
            """
            widget = QWidget()
            layout = QVBoxLayout(widget)

            # Projects list
            projects_group = QGroupBox("Registered Projects")
            projects_layout = QVBoxLayout(projects_group)

            self.projects_list = QListWidget()
            projects_layout.addWidget(self.projects_list)

            # Project buttons
            project_buttons_layout = QHBoxLayout()

            add_project_button = QPushButton("Add Project...")
            add_project_button.clicked.connect(self._add_project)
            project_buttons_layout.addWidget(add_project_button)

            edit_project_button = QPushButton("Edit...")
            edit_project_button.clicked.connect(self._edit_project)
            project_buttons_layout.addWidget(edit_project_button)

            remove_project_button = QPushButton("Remove")
            remove_project_button.clicked.connect(self._remove_project)
            project_buttons_layout.addWidget(remove_project_button)

            projects_layout.addLayout(project_buttons_layout)
            layout.addWidget(projects_group)

            return widget

        def _create_advanced_tab(self):
            """
            Create advanced settings tab.
            """
            widget = QWidget()
            layout = QFormLayout(widget)

            # Base fallback port
            self.base_fallback_port_spin = QSpinBox()
            self.base_fallback_port_spin.setRange(1024, 65535)
            self.base_fallback_port_spin.setValue(9000)
            layout.addRow("Base Fallback Port:", self.base_fallback_port_spin)

            # Base proxy port
            self.base_proxy_port_spin = QSpinBox()
            self.base_proxy_port_spin.setRange(1024, 65535)
            self.base_proxy_port_spin.setValue(9100)
            layout.addRow("Base Proxy Port:", self.base_proxy_port_spin)

            # Telemetry endpoint
            self.telemetry_endpoint_edit = QLineEdit()
            self.telemetry_endpoint_edit.setPlaceholderText("https://telemetry.example.com/api")
            layout.addRow("Telemetry Endpoint:", self.telemetry_endpoint_edit)

            return widget

        def _load_settings(self):
            """
            Load current settings.
            """
            config = self.project_registry.config

            # General settings
            self.refresh_interval_spin.setValue(int(config.monitor_refresh_interval))
            self.log_retention_spin.setValue(config.log_retention_days)
            self.enable_gui_check.setChecked(config.enable_desktop_gui)
            self.enable_tui_check.setChecked(config.enable_tui_monitor)

            # Advanced settings
            self.base_fallback_port_spin.setValue(config.base_fallback_port)
            self.base_proxy_port_spin.setValue(config.base_proxy_port)
            self.telemetry_endpoint_edit.setText(config.telemetry_endpoint or "")

            # Load projects
            self._refresh_projects_list()

        def _refresh_projects_list(self):
            """
            Refresh the projects list.
            """
            self.projects_list.clear()

            for project_name in self.project_registry.list_projects():
                project_config = self.project_registry.get_project(project_name)
                if project_config:
                    item_text = f"{project_name} - {' '.join(project_config.cli_entry)}"
                    item = QListWidgetItem(item_text)
                    item.setData(Qt.ItemDataRole.UserRole, project_name)
                    self.projects_list.addItem(item)

        def _add_project(self):
            """
            Add a new project.
            """
            dialog = ProjectConfigDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                project_config = dialog.get_project_config()
                self.project_registry.register_project(project_config)
                self._refresh_projects_list()

        def _edit_project(self):
            """
            Edit selected project.
            """
            current_item = self.projects_list.currentItem()
            if not current_item:
                QMessageBox.information(self, "No Selection", "Please select a project to edit.")
                return

            project_name = current_item.data(Qt.ItemDataRole.UserRole)
            project_config = self.project_registry.get_project(project_name)

            if project_config:
                dialog = ProjectConfigDialog(self, project_config)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    updated_config = dialog.get_project_config()

                    # If name changed, unregister old and register new
                    if updated_config.name != project_name:
                        self.project_registry.unregister_project(project_name)

                    self.project_registry.register_project(updated_config)
                    self._refresh_projects_list()

        def _remove_project(self):
            """
            Remove selected project.
            """
            current_item = self.projects_list.currentItem()
            if not current_item:
                QMessageBox.information(self, "No Selection", "Please select a project to remove.")
                return

            project_name = current_item.data(Qt.ItemDataRole.UserRole)

            reply = QMessageBox.question(
                self,
                "Confirm Removal",
                f"Are you sure you want to remove project '{project_name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.project_registry.unregister_project(project_name)
                self._refresh_projects_list()

        def _apply_settings(self):
            """
            Apply settings without closing dialog.
            """
            try:
                config = self.project_registry.config

                # Update config
                config.monitor_refresh_interval = float(self.refresh_interval_spin.value())
                config.log_retention_days = self.log_retention_spin.value()
                config.enable_desktop_gui = self.enable_gui_check.isChecked()
                config.enable_tui_monitor = self.enable_tui_check.isChecked()
                config.base_fallback_port = self.base_fallback_port_spin.value()
                config.base_proxy_port = self.base_proxy_port_spin.value()
                config.telemetry_endpoint = self.telemetry_endpoint_edit.text().strip() or None

                # Save config
                self.project_registry.save_config()

                QMessageBox.information(
                    self, "Settings Applied", "Settings have been applied successfully.",
                )

            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to apply settings: {e}")

        def accept(self):
            """
            Accept dialog and apply settings.
            """
            self._apply_settings()
            super().accept()

    class AboutDialog(QDialog):
        """
        About dialog for the application.
        """

        def __init__(self, parent=None):
            super().__init__(parent)

            self.setWindowTitle("About Pheno Control Center")
            self.setModal(True)
            self.setFixedSize(500, 400)

            self._init_ui()

        def _init_ui(self):
            """
            Initialize the user interface.
            """
            layout = QVBoxLayout(self)

            # Title
            title_label = QLabel("Pheno Control Center")
            title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            title_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
            layout.addWidget(title_label)

            # Version
            version_label = QLabel("Version 1.0.0")
            version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(version_label)

            # Description
            description = QLabel(
                "A centralized orchestration system for managing multiple pheno-sdk projects "
                "with unified monitoring, command routing, and multi-tenant infrastructure management.",
            )
            description.setWordWrap(True)
            description.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(description)

            # Features
            features_label = QLabel("Features:")
            features_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            layout.addWidget(features_label)

            features_text = QLabel(
                "• Multi-project orchestration with dependency management\n"
                "• Port conflict resolution through dynamic allocation\n"
                "• Centralized monitoring with project-grouped status display\n"
                "• Command routing with project context switching\n"
                "• Multi-tenant infrastructure for tunnels, fallback, and proxy services\n"
                "• Desktop GUI with embedded terminal and real-time monitoring\n"
                "• Interactive TUI with command execution and log streaming",
            )
            layout.addWidget(features_text)

            # Credits
            credits_label = QLabel("Built on:")
            credits_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            layout.addWidget(credits_label)

            credits_text = QLabel(
                "• KInfra - Cross-platform infrastructure library\n"
                "• PyQt6 - Cross-platform GUI framework\n"
                "• Rich - Rich text and beautiful formatting\n"
                "• Textual - Modern TUI framework\n"
                "• pheno-sdk - Unified SDK ecosystem",
            )
            layout.addWidget(credits_text)

            # Button box
            button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
            button_box.accepted.connect(self.accept)
            layout.addWidget(button_box)

else:
    # Fallback classes when PyQt is not available
    class ProjectConfigDialog:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("PyQt6 not available")

    class SettingsDialog:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("PyQt6 not available")

    class AboutDialog:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("PyQt6 not available")
