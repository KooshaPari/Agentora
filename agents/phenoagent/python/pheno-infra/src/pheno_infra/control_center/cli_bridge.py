"""CLI Bridge and Command Router for Pheno Control Center.

Provides command execution, streaming output capture, and environment
context switching for pheno-cli commands across different projects.

This module re-exports CLI functionality from specialized modules:
- Command execution and process management: CommandResult, CLIBridge
- Command routing and context switching: CommandRouter
- Telemetry and monitoring: CLITelemetry, CommandMetrics
"""

from pheno.infra.control_center.cli_telemetry import CLITelemetry, CommandMetrics

# Re-export from specialized modules for backward compatibility
from pheno.infra.control_center.command_executor import CLIBridge, CommandResult
from pheno.infra.control_center.command_router import CommandRouter

__all__ = [
    "CLIBridge",
    "CLITelemetry",
    "CommandMetrics",
    "CommandResult",
    "CommandRouter",
]
