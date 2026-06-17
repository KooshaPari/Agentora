"""
Test Runner - Redirect to Base Test Runner

DEPRECATED: This module is deprecated and will be removed in a future version.
Please import from mcp_qa.core.base.test_runner instead.

This testing runner has been replaced by BaseTestRunner in the core.base module.

Migration Guide:
    OLD: from pheno.testing.mcp_qa.testing.runner import TestRunner
    NEW: from pheno.testing.mcp_qa.core.base.test_runner import BaseTestRunner

    Or use the main package export:
    from mcp_qa import BaseTestRunner  # Recommended
    from mcp_qa import TestRunner      # Legacy alias (still works)
"""

import warnings

# Re-export from base module
from pheno.testing.mcp_qa.core.base.test_runner import BaseTestRunner

# Provide legacy alias
TestRunner = BaseTestRunner

# Issue deprecation warning
warnings.warn(
    "mcp_qa.testing.runner is deprecated. "
    "Please import BaseTestRunner from mcp_qa.core.base.test_runner instead. "
    "Example: from mcp_qa import BaseTestRunner",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["TestRunner", "BaseTestRunner"]
