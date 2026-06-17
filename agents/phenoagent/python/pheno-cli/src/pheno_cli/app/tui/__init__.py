"""
TUI Wireframes and Flows - Premade composable TUI components for pheno-cli.

CLI-specific TUI components built on top of pheno.tui (canonical facade).
For base TUI widgets, layouts, and themes, import from ``pheno.tui``.

Features:
- Pre-built wireframes for common CLI operations
- Interactive setup flows with validation
- Status dashboards with real-time monitoring
- Deployment pipelines with progress tracking
- Context-aware interfaces (atoms, zen, byteport)
- Composable components that can be easily configured

Note: This module contains CLI-specific flows and wireframes.
      For general TUI widgets, import from pheno.ui.tui:

      from pheno.tui import StatusWidget, ProgressWidget, LogViewer
      from pheno.tui.widgets import MetricsPanel
      from pheno.tui.layouts import SplitLayout
"""

from .components import *
from .deployment import *
from .flows import *
from .monitors import *
from .wireframes import *

__all__ = [
    "AuthenticationFlow",
    "BuildMonitor",
    "ConfigurationFlow",
    "ConfigurationWireframe",
    "CratesDeployment",
    "DeploymentFlow",
    # Monitoring Components
    "DeploymentMonitor",
    "DeploymentWireframe",
    "DockerDeployment",
    "MonitoringWireframe",
    "NPMDeployment",
    "OnboardingFlow",
    # Interactive Flows
    "ProjectSetupFlow",
    "ProjectWireframe",
    # Deployment Pipelines
    "PyPIDeployment",
    "ResourceMonitor",
    "ServiceMonitor",
    # Wireframes
    "SetupWireframe",
    "SystemServiceDeployment",
    "TestMonitor",
    "create_flow",
    # Utility Functions
    "launch_wireframe",
    "run_monitor",
    "show_deployment_ui",
]
