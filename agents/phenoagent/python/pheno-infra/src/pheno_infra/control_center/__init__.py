"""
Pheno Control Center - Centralized orchestration for pheno-sdk projects.

This module provides:
- Multi-project registry and configuration
- Unified monitoring and control interfaces
- CLI bridge for command routing
- Desktop GUI and enhanced TUI components
"""

from .cli_bridge import CLIBridge, CommandRouter
from .config import (
    ControlCenterConfig,
    ProjectConfig,
    ProjectRegistry,
    ValidationError,
)
from .engine import UnifiedMonitorEngine
from .multi_tenant import MultiTenantManager

# Desktop components (PyQt-based)
try:
    from .desktop import HAS_PYQT as HAS_DESKTOP
    from .desktop import (
        AboutDialog,
        MonitoringWidget,
        PhenoControlCenterGUI,
        ProjectConfigDialog,
        ProjectLauncherWidget,
        SettingsDialog,
        StatusWidget,
        TerminalWidget,
    )
except (ImportError, NameError):
    # Handle both missing PyQt and import errors
    PhenoControlCenterGUI = None
    ProjectLauncherWidget = None
    MonitoringWidget = None
    TerminalWidget = None
    StatusWidget = None
    ProjectConfigDialog = None
    SettingsDialog = None
    AboutDialog = None
    HAS_DESKTOP = False

__all__ = [
    "HAS_DESKTOP",
    "AboutDialog",
    "CLIBridge",
    "CommandRouter",
    "ControlCenterConfig",
    "MonitoringWidget",
    "MultiTenantManager",
    # Desktop components
    "PhenoControlCenterGUI",
    "ProjectConfig",
    "ProjectConfigDialog",
    "ProjectLauncherWidget",
    "ProjectRegistry",
    "SettingsDialog",
    "StatusWidget",
    "TerminalWidget",
    "UnifiedMonitorEngine",
    "ValidationError",
]
