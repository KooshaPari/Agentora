"""Pytest plugin namespace for the integrated MCP QA toolkit.

Historically the standalone ``mcp_qa`` package exposed plugins via the
``mcp_qa.pytest_plugins`` entry point.  We provide an equivalent module so
existing configurations keep working while the suite runs entirely from the
``pheno`` namespace.
"""

from __future__ import annotations

from .auth import pytest_configure  # re-export hook for compatibility

__all__ = ["pytest_configure"]
