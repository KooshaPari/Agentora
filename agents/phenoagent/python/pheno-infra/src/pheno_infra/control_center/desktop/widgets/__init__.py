"""
Widget modules for PyQt desktop application.
"""

# Re-export widgets
from .monitoring_widget import MonitoringWidget
from .project_launcher import ProjectLauncherWidget
from .status_widget import StatusWidget
from .terminal_widget import TerminalWidget

__all__ = [
    "MonitoringWidget",
    "ProjectLauncherWidget",
    "StatusWidget",
    "TerminalWidget",
]
