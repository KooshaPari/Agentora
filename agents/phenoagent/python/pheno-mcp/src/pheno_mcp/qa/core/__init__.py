"""Core building blocks for the MCP QA toolkit.

Only a subset of the original ``mcp_qa`` code base is required by current
consumers.  The consolidated implementation focuses on the registry and base
test runner abstractions so the rest of the system can continue to evolve in
the pheno namespace.
"""

from __future__ import annotations

from .base.client_adapter import BaseClientAdapter, MCPClientAdapter
from .base.test_runner import BaseTestRunner
from .test_registry import TestRegistry, get_test_registry, mcp_test, require_auth

# Backwards compatible aliases
TestRunner = BaseTestRunner

__all__ = [
    "BaseClientAdapter",
    "BaseTestRunner",
    "MCPClientAdapter",
    "TestRegistry",
    "TestRunner",
    "get_test_registry",
    "mcp_test",
    "require_auth",
]
