"""
Test Runner - Redirect to Base Test Runner

DEPRECATED: This module is deprecated and will be removed in a future version.
Please import from mcp_qa.core.base.test_runner instead.

The TestRunner class has been refactored into BaseTestRunner with better
extensibility for project-specific implementations.

Migration Guide:
    OLD: from pheno.testing.mcp_qa.core.test_runner import TestRunner
    NEW: from pheno.testing.mcp_qa.core.base.test_runner import BaseTestRunner

    Or use the main package export:
    from mcp_qa import BaseTestRunner  # Recommended
    from mcp_qa import TestRunner      # Legacy alias (still works)

For new code, extend BaseTestRunner:
    class MyTestRunner(BaseTestRunner):
        def _get_metadata(self):
            return {"project": "my-project"}

        def _get_category_order(self):
            return ["core", "integration"]
"""

import warnings

# Re-export from base module
from .base.test_runner import BaseTestRunner

# Provide legacy alias
TestRunner = BaseTestRunner

# Issue deprecation warning
warnings.warn(
    "mcp_qa.core.test_runner is deprecated. "
    "Please import BaseTestRunner from mcp_qa.core.base.test_runner instead. "
    "Example: from mcp_qa import BaseTestRunner",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["TestRunner", "BaseTestRunner"]
