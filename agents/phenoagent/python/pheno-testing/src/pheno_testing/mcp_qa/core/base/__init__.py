"""Base Patterns for MCP Test Infrastructure.

This module provides abstract base classes for building MCP test frameworks.
Projects extend these to implement project-specific functionality while
sharing common infrastructure.

Available Base Classes:
- BaseClientAdapter: Abstract adapter for MCP client interactions
- BaseTestRunner: Abstract runner for test execution orchestration

Example Project Structure:
    # In your project's tests/framework/adapters.py
    from pheno.testing.mcp_qa.core.base import BaseClientAdapter

    class MyProjectAdapter(BaseClientAdapter):
        def _process_result(self, result, tool_name, params):
            return result.content if hasattr(result, 'content') else result

        def _log_error(self, error, tool_name, params):
            logger.error(f"{tool_name} failed: {error}")

    # In your project's tests/framework/runner.py
    from pheno.testing.mcp_qa.core.base import BaseTestRunner

    class MyProjectRunner(BaseTestRunner):
        def _get_metadata(self):
            return {
                "endpoint": self.client_adapter.endpoint,
                "project": "my-project"
            }
"""

from .client_adapter import BaseClientAdapter, SimpleClientAdapter
from .test_runner import BaseTestRunner

__all__ = [
    "BaseClientAdapter",
    "SimpleClientAdapter",
    "BaseTestRunner",
]
