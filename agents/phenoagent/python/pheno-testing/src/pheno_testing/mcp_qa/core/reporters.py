"""
Test Reporters - Redirect to Modular Reporters Package

DEPRECATED: This module is deprecated and will be removed in a future version.
Please import directly from mcp_qa.reporters instead.

This file now re-exports all reporters from the modular reporters package
to maintain backward compatibility with existing code.

Migration Guide:
    OLD: from pheno.testing.mcp_qa.core.reporters import ConsoleReporter
    NEW: from pheno.testing.mcp_qa.reporters import ConsoleReporter

The new reporters package provides the same functionality with:
- Modular architecture (easier to maintain)
- Better code organization
- Individual reporter files
"""

import warnings

# Re-export all reporters from the modular package
from pheno.testing.mcp_qa.reporters import (
    ConsoleReporter,
    DetailedErrorReporter,
    FunctionalityMatrixReporter,
    JSONReporter,
    MarkdownReporter,
    MultiReporter,
    TestReporter,
    create_standard_reporters,
)

# Issue deprecation warning
warnings.warn(
    "mcp_qa.core.reporters is deprecated. "
    "Please import from mcp_qa.reporters instead. "
    "Example: from pheno.testing.mcp_qa.reporters import ConsoleReporter",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "TestReporter",
    "ConsoleReporter",
    "JSONReporter",
    "MarkdownReporter",
    "FunctionalityMatrixReporter",
    "DetailedErrorReporter",
    "MultiReporter",
    "create_standard_reporters",
]
