"""
MCP-QA: Shared Testing Library for MCP Servers

A unified testing infrastructure that provides:
- OAuth credential management with .env persistence
- Playwright automation with inline progress
- Interactive TUI dashboards
- Comprehensive test reporting
- Health checks and validation

This is a framework-level library that can be used across multiple MCP projects.
Projects should extend BaseTestRunner and BaseClientAdapter with their specific implementations.
"""

__version__ = "0.2.0"

# Adapter imports - FastHTTPClient for ecosystem-wide reuse
from pheno.testing.mcp_qa.adapters import FastHTTPClient
from pheno.testing.mcp_qa.core.base.client_adapter import BaseClientAdapter, SimpleClientAdapter

# Core imports - New base classes (framework-level)
from pheno.testing.mcp_qa.core.base.test_runner import BaseTestRunner

# OAuth imports
from pheno.testing.mcp_qa.oauth.credential_broker import (
    CapturedCredentials,
    UnifiedCredentialBroker,
)

# Reporter imports - Use modular reporters package
from pheno.testing.mcp_qa.reporters import ConsoleReporter, JSONReporter

__all__ = [
    # Base classes for projects to extend
    "BaseTestRunner",
    "BaseClientAdapter",
    "SimpleClientAdapter",
    # OAuth
    "UnifiedCredentialBroker",
    "CapturedCredentials",
    # Reporters
    "ConsoleReporter",
    "JSONReporter",
    # Adapters
    "FastHTTPClient",
]
