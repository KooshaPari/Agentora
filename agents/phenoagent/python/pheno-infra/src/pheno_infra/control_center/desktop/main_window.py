"""Main PyQt window for Pheno Control Center desktop application.

Provides the primary desktop interface with resizable panes, project management, and
integrated monitoring capabilities.
"""

import asyncio
import logging
from pathlib import Path

try:
    from PyQt6.QtCore import QSettings, Qt, QThread, pyqtSignal
    from PyQt6.QtWidgets import (
        QAction,
        QLabel,
        QMainWindow,
        QMenu,
        QMessageBox,
        QProgressBar,
        QSplitter,
        QSystemTrayIcon,
        QTabWidget,
        QToolBar,
        QVBoxLayout,
        QWidget,
    )

    HAS_PYQT = True
except ImportError:
    HAS_PYQT = False

if HAS_PYQT:
    from .dialogs import (
        AboutDialog,
        ProjectConfigDialog,
        SettingsDialog,
    )
    from .widgets.monitoring_widget import MonitoringWidget
    from .widgets.project_launcher import ProjectLauncherWidget
    from .widgets.status_widget import StatusWidget
    from .widgets.terminal_widget import TerminalWidget


logger = logging.getLogger(__name__)


if HAS_PYQT:

    class AsyncWorker(QThread):
        """
        Worker thread for async monitoring operations.
        """

        finished = pyqtSignal()
        error = pyqtSignal(str)
        status_update = pyqtSignal(dict)

        def __init__(self, control_center):
            super().__init__()
            self.control_center = control_center
            self.running = False

        def run(self):
            """
            Run async monitoring loop.
            """
            self.running = True
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self._async_monitor())
            except Exception as e:
                self.error.emit(str(e))
            finally:
                self.finished.emit()

        async def _async_monitor(self):
            """
            Async monitoring loop.
            """
            await self.control_center.setup()

            while self.running:
                try:
                    # Get status updates
                    global_status = self.control_center.monitor_engine.get_global_status()
                    self.status_update.emit(global_status)

                    await asyncio.sleep(2.0)  # Update every 2 seconds
                except Exception as e:
                    logger.exception(f"Monitor loop error: {e}")
                    await asyncio.sleep(5.0)

        def stop(self):
            """
            Stop the monitoring loop.
            """
            self.running = False


if HAS_PYQT:

    class PhenoControlCenterGUI(QMainWindow):
        """Main PyQt desktop application for Pheno Control Center.

        Features:
        - Project launcher with start/stop buttons
        - Resizable monitoring panes
        - Embedded terminal widget
        - System tray integration
        - Real-time status updates
        """

        def __init__(self, config_dir: Path | None = None):
            super().__init__()
            self.config_dir = config_dir

            # Initialize control center components
            self._init_control_center()

            # Setup UI
            self._init_ui()
            self._create_menus()
            self._create_toolbar()
            self._create_status_bar()
            self._setup_system_tray()

            # Setup async worker
            self.async_worker = AsyncWorker(self.control_center)
            self.async_worker.status_update.connect(self.update_status)
            self.async_worker.error.connect(self.handle_error)
            self.async_worker.finished.connect(self.on_worker_finished)

            # Settings
            self.settings = QSettings("PhenoSDK", "ControlCenter")
            self._restore_settings()

            logger.info("Pheno Control Center GUI initialized")

        def _init_control_center(self):
            """
            Initialize control center components.
            """
            # Import here to avoid circular imports
            from ..main import PhenoControlCenter

            self.control_center = PhenoControlCenter(self.config_dir)

        def _init_ui(self):
            """
            Initialize the user interface.
            """
            self.setWindowTitle("Pheno Control Center")
            self.setMinimumSize(1200, 800)
            self.resize(1400, 900)

            # Central widget with main splitter
            central_widget = QWidget()
            self.setCentralWidget(central_widget)

            layout = QVBoxLayout(central_widget)
            layout.setContentsMargins(5, 5, 5, 5)

            # Main horizontal splitter
            main_splitter = QSplitter(Qt.Orientation.Horizontal)
            layout.addWidget(main_splitter)

            # Left pane - Project launcher
            self.project_launcher = ProjectLauncherWidget(self.control_center)
            main_splitter.addWidget(self.project_launcher)

            # Right pane - Tabbed interface
            right_widget = QWidget()
            right_layout = QVBoxLayout(right_widget)
            right_layout.setContentsMargins(0, 0, 0, 0)

            # Tab widget for monitoring and terminal
            self.tab_widget = QTabWidget()

            # Monitoring tab
            self.monitoring_widget = MonitoringWidget(self.control_center)
            self.tab_widget.addTab(self.monitoring_widget, "Monitoring")

            # Terminal tab
            self.terminal_widget = TerminalWidget(self.control_center)
            self.tab_widget.addTab(self.terminal_widget, "Terminal")

            # Status tab
            self.status_widget = StatusWidget(self.control_center)
            self.tab_widget.addTab(self.status_widget, "Status")

            right_layout.addWidget(self.tab_widget)
            main_splitter.addWidget(right_widget)

            # Set splitter proportions
            main_splitter.setSizes([400, 1000])
            main_splitter.setStretchFactor(0, 0)
            main_splitter.setStretchFactor(1, 1)

        def _create_menus(self):
            """
            Create application menus.
            """
            menubar = self.menuBar()

            # File menu
            file_menu = menubar.addMenu("&File")

            new_project_action = QAction("&New Project...", self)
            new_project_action.setShortcut("Ctrl+N")
            new_project_action.triggered.connect(self.new_project)
            file_menu.addAction(new_project_action)

            file_menu.addSeparator()

            settings_action = QAction("&Settings...", self)
            settings_action.setShortcut("Ctrl+,")
            settings_action.triggered.connect(self.open_settings)
            file_menu.addAction(settings_action)

            file_menu.addSeparator()

            exit_action = QAction("E&xit", self)
            exit_action.setShortcut("Ctrl+Q")
            exit_action.triggered.connect(self.close)
            file_menu.addAction(exit_action)

            # Project menu
            project_menu = menubar.addMenu("&Project")

            start_all_action = QAction("&Start All Projects", self)
            start_all_action.triggered.connect(self.start_all_projects)
            project_menu.addAction(start_all_action)

            stop_all_action = QAction("S&top All Projects", self)
            stop_all_action.triggered.connect(self.stop_all_projects)
            project_menu.addAction(stop_all_action)

            project_menu.addSeparator()

            refresh_action = QAction("&Refresh Status", self)
            refresh_action.setShortcut("F5")
            refresh_action.triggered.connect(self.refresh_status)
            project_menu.addAction(refresh_action)

            # View menu
            view_menu = menubar.addMenu("&View")

            show_launcher_action = QAction("Show Project &Launcher", self)
            show_launcher_action.setCheckable(True)
            show_launcher_action.setChecked(True)
            show_launcher_action.triggered.connect(self.toggle_project_launcher)
            view_menu.addAction(show_launcher_action)

            view_menu.addSeparator()

            monitoring_action = QAction("&Monitoring", self)
            monitoring_action.triggered.connect(lambda: self.tab_widget.setCurrentIndex(0))
            view_menu.addAction(monitoring_action)

            terminal_action = QAction("&Terminal", self)
            terminal_action.triggered.connect(lambda: self.tab_widget.setCurrentIndex(1))
            view_menu.addAction(terminal_action)

            status_action = QAction("&Status", self)
            status_action.triggered.connect(lambda: self.tab_widget.setCurrentIndex(2))
            view_menu.addAction(status_action)

            # Help menu
            help_menu = menubar.addMenu("&Help")

            about_action = QAction("&About...", self)
            about_action.triggered.connect(self.show_about)
            help_menu.addAction(about_action)

        def _create_toolbar(self):
            """
            Create application toolbar.
            """
            toolbar = QToolBar("Main Toolbar", self)
            toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            self.addToolBar(toolbar)

            # Start all action
            start_action = QAction("Start All", self)
            start_action.setToolTip("Start all projects")
            start_action.triggered.connect(self.start_all_projects)
            toolbar.addAction(start_action)

            # Stop all action
            stop_action = QAction("Stop All", self)
            stop_action.setToolTip("Stop all projects")
            stop_action.triggered.connect(self.stop_all_projects)
            toolbar.addAction(stop_action)

            toolbar.addSeparator()

            # Refresh action
            refresh_action = QAction("Refresh", self)
            refresh_action.setToolTip("Refresh status")
            refresh_action.triggered.connect(self.refresh_status)
            toolbar.addAction(refresh_action)

            toolbar.addSeparator()

            # Settings action
            settings_action = QAction("Settings", self)
            settings_action.setToolTip("Open settings")
            settings_action.triggered.connect(self.open_settings)
            toolbar.addAction(settings_action)

        def _create_status_bar(self):
            """
            Create status bar.
            """
            status_bar = self.statusBar()

            # Status label
            self.status_label = QLabel("Ready")
            status_bar.addWidget(self.status_label)

            # Progress bar
            self.progress_bar = QProgressBar()
            self.progress_bar.setVisible(False)
            status_bar.addPermanentWidget(self.progress_bar)

            # Projects count
            self.projects_count_label = QLabel("Projects: 0")
            status_bar.addPermanentWidget(self.projects_count_label)

        def _setup_system_tray(self):
            """
            Setup system tray icon and menu.
            """
            if not QSystemTrayIcon.isSystemTrayAvailable():
                logger.warning("System tray not available")
                return

            # Create tray icon
            self.tray_icon = QSystemTrayIcon(self)

            # Create tray menu
            tray_menu = QMenu()

            show_action = QAction("Show", self)
            show_action.triggered.connect(self.show)
            tray_menu.addAction(show_action)

            hide_action = QAction("Hide", self)
            hide_action.triggered.connect(self.hide)
            tray_menu.addAction(hide_action)

            tray_menu.addSeparator()

            quit_action = QAction("Quit", self)
            quit_action.triggered.connect(self.close)
            tray_menu.addAction(quit_action)

            self.tray_icon.setContextMenu(tray_menu)
            self.tray_icon.activated.connect(self.tray_icon_activated)

            # Show tray icon
            self.tray_icon.show()

        def _restore_settings(self):
            """
            Restore application settings.
            """
            # Window geometry
            geometry = self.settings.value("geometry")
            if geometry:
                self.restoreGeometry(geometry)

            # Window state
            state = self.settings.value("windowState")
            if state:
                self.restoreState(state)

        def _save_settings(self):
            """
            Save application settings.
            """
            self.settings.setValue("geometry", self.saveGeometry())
            self.settings.setValue("windowState", self.saveState())

        def showEvent(self, event):
            """
            Handle show event.
            """
            super().showEvent(event)

            # Start async worker when window is shown
            if not self.async_worker.isRunning():
                self.async_worker.start()

        def closeEvent(self, event):
            """
            Handle close event.
            """
            # Save settings
            self._save_settings()

            # Stop async worker
            if self.async_worker.isRunning():
                self.async_worker.stop()
                self.async_worker.wait(5000)  # Wait up to 5 seconds

            # Hide to tray if available
            if hasattr(self, "tray_icon") and self.tray_icon.isVisible():
                self.hide()
                event.ignore()
            else:
                # Shutdown control center
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self.control_center.shutdown())
                except Exception as e:
                    logger.exception(f"Shutdown error: {e}")

                event.accept()

        def tray_icon_activated(self, reason):
            """
            Handle tray icon activation.
            """
            if reason == QSystemTrayIcon.ActivationReason.Trigger:
                if self.isVisible():
                    self.hide()
                else:
                    self.show()
                    self.raise_()
                    self.activateWindow()

        def update_status(self, global_status):
            """
            Update status from monitoring data.
            """
            summary = global_status["summary"]

            # Update status label
            healthy_projects = summary["healthy_projects"]
            total_projects = summary["total_projects"]
            running_processes = summary["running_processes"]
            total_processes = summary["total_processes"]

            status_text = f"Projects: {healthy_projects}/{total_projects} healthy | Processes: {running_processes}/{total_processes} running"
            self.status_label.setText(status_text)

            # Update projects count
            self.projects_count_label.setText(f"Projects: {total_projects}")

            # Update widgets
            self.project_launcher.update_status(global_status)
            self.monitoring_widget.update_status(global_status)
            self.status_widget.update_status(global_status)

        def handle_error(self, error_msg):
            """
            Handle errors from async worker.
            """
            logger.error(f"Async worker error: {error_msg}")
            QMessageBox.critical(self, "Error", f"Control center error: {error_msg}")

        def on_worker_finished(self):
            """
            Handle async worker finished.
            """
            logger.info("Async worker finished")

        # Menu actions
        def new_project(self):
            """
            Create new project.
            """
            dialog = ProjectConfigDialog(self)
            if dialog.exec() == dialog.DialogCode.Accepted:
                project_config = dialog.get_project_config()
                self.control_center.project_registry.register_project(project_config)
                self.refresh_status()

        def open_settings(self):
            """
            Open settings dialog.
            """
            dialog = SettingsDialog(self.control_center.project_registry, self)
            dialog.exec()

        def show_about(self):
            """
            Show about dialog.
            """
            dialog = AboutDialog(self)
            dialog.exec()

        def start_all_projects(self):
            """
            Start all projects.
            """
            self.status_label.setText("Starting all projects...")
            self.progress_bar.setVisible(True)
            # This would trigger actual project starts
            # Implementation would depend on integration with CLI bridge

        def stop_all_projects(self):
            """
            Stop all projects.
            """
            self.status_label.setText("Stopping all projects...")
            self.progress_bar.setVisible(True)
            # This would trigger actual project stops

        def refresh_status(self):
            """
            Refresh status display.
            """
            self.status_label.setText("Refreshing status...")
            # Force immediate status update
            if hasattr(self, "async_worker") and self.async_worker.isRunning():
                # Trigger immediate update in worker thread
                pass

        def toggle_project_launcher(self, visible):
            """
            Toggle project launcher visibility.
            """
            self.project_launcher.setVisible(visible)

else:
    # Fallback when PyQt is not available
    class PhenoControlCenterGUI:
        def __init__(self, *args, **kwargs):
            raise RuntimeError(
                "PyQt6 is not available. Please install PyQt6 to use the desktop GUI.",
            )
