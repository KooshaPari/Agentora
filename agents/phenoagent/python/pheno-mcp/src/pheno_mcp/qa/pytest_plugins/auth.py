"""Minimal pytest plugin wiring for MCP QA tests.

The original project used this hook to perform lightweight configuration.  We retain a
no-op implementation so pytest can import the entry point without modifying the broader
test stack.
"""

from __future__ import annotations


def pytest_configure(config):  # pragma: no cover - integration glue
    return None


__all__ = ["pytest_configure"]
