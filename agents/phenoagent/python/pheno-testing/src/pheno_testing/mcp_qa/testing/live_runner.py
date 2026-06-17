"""
Live Test Runner - Redirect to Core Live Runner

DEPRECATED: This module is deprecated and will be removed in a future version.
Please import from mcp_qa.core.live_runner instead.

Migration Guide:
    OLD: from pheno.testing.mcp_qa.testing.live_runner import LiveTestRunner
    NEW: from pheno.testing.mcp_qa.core.live_runner import LiveTestRunner

    Or use the core package export:
    from pheno.testing.mcp_qa.core import LiveTestRunner
"""

import warnings

# Re-export from core module
from pheno.testing.mcp_qa.core.live_runner import LiveTestRunner

# Issue deprecation warning
warnings.warn(
    "mcp_qa.testing.live_runner is deprecated. "
    "Please import from mcp_qa.core.live_runner instead. "
    "Example: from pheno.testing.mcp_qa.core import LiveTestRunner",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["LiveTestRunner"]
