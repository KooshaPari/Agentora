"""PyQt Desktop Application for Pheno Control Center.

Provides a visual desktop interface with:
- Project launcher tiles with start/stop actions
- Resizable panes for monitoring and logs
- Embedded terminal widget for command execution
- Config-driven project registry integration
- System tray integration
"""

# Check for PyQt6 first
try:
    _HAS_PYQT_MODULE = True
except ImportError:
    _HAS_PYQT_MODULE = False

if _HAS_PYQT_MODULE:
    try:
        from .dialogs import (
            AboutDialog,
            ProjectConfigDialog,
            SettingsDialog,
        )
        from .main_window import PhenoControlCenterGUI
        from .widgets import (
            MonitoringWidget,
            ProjectLauncherWidget,
            StatusWidget,
            TerminalWidget,
        )

        HAS_PYQT = True
    except (ImportError, NameError):
        # Handle import errors even when PyQt6 is present
        PhenoControlCenterGUI = None
        ProjectLauncherWidget = None
        MonitoringWidget = None
        TerminalWidget = None
        StatusWidget = None
        ProjectConfigDialog = None
        SettingsDialog = None
        AboutDialog = None
        HAS_PYQT = False
else:
    # PyQt6 not available
    PhenoControlCenterGUI = None
    ProjectLauncherWidget = None
    MonitoringWidget = None
    TerminalWidget = None
    StatusWidget = None
    ProjectConfigDialog = None
    SettingsDialog = None
    AboutDialog = None
    HAS_PYQT = False

__all__ = [
    "HAS_PYQT",
    "AboutDialog",
    "MonitoringWidget",
    "PhenoControlCenterGUI",
    "ProjectConfigDialog",
    "ProjectLauncherWidget",
    "SettingsDialog",
    "StatusWidget",
    "TerminalWidget",
]
