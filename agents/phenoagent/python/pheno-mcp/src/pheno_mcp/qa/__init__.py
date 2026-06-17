"""
pheno.mcp.qa - MCP Quality Assurance toolkit

A unified testing infrastructure for MCP servers that provides:
- OAuth credential management with .env persistence
- Playwright automation with inline progress
- Interactive TUI dashboards
- Comprehensive test reporting
- Health checks and validation

Migrated from mcp-QA into pheno namespace.

Usage:
    from pheno.mcp.qa import BaseTestRunner, UnifiedCredentialBroker

    # Create test runner
    runner = BaseTestRunner()

    # Manage credentials
    broker = UnifiedCredentialBroker()
"""

from __future__ import annotations

__version__ = "0.1.0"

# Adapter imports - FastHTTPClient for ecosystem-wide reuse
from .adapters import FastHTTPClient

# Config exports
from .config.endpoints import EndpointConfig, EndpointRegistry, Environment, MCPProject

# Backward compatibility aliases (deprecated - use base classes in new code)
# Import from core which now re-exports from base
from .core import MCPClientAdapter, TestRunner
from .core.base.client_adapter import BaseClientAdapter

# Core imports - New base classes
from .core.base.test_runner import BaseTestRunner

# OAuth imports
from .oauth.credential_broker import CapturedCredentials, UnifiedCredentialBroker

# Reporter imports - Use modular reporters package
from .reporters import ConsoleReporter, JSONReporter

__all__ = [
    "BaseClientAdapter",
    # New base classes (recommended)
    "BaseTestRunner",
    "CapturedCredentials",
    # Reporters
    "ConsoleReporter",
    "EndpointConfig",
    # Endpoint registry helpers
    "EndpointRegistry",
    "Environment",
    # Adapters
    "FastHTTPClient",
    "JSONReporter",
    "MCPClientAdapter",
    "MCPProject",
    # Legacy aliases (deprecated but still supported)
    "TestRunner",
    # OAuth
    "UnifiedCredentialBroker",
]
