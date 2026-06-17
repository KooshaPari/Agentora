"""
OAuth Progress Display - Redirect to Unified Progress

DEPRECATED: This module is deprecated and will be removed in a future version.
Please import from mcp_qa.oauth.progress instead.

This file now re-exports all functionality from the unified progress module
to maintain backward compatibility with existing code.

Migration Guide:
    OLD: from pheno.testing.mcp_qa.oauth.oauth_progress import OAuthProgressFlow
    NEW: from pheno.testing.mcp_qa.oauth.progress import OAuthProgressFlow

    Or even better:
    from pheno.testing.mcp_qa.oauth import OAuthProgressFlow, InlineProgress, inline_progress
"""

import warnings

# Re-export from unified progress module
from .progress import InlineProgress, OAuthProgressFlow, inline_progress

# Issue deprecation warning
warnings.warn(
    "mcp_qa.oauth.oauth_progress is deprecated. "
    "Please import from mcp_qa.oauth.progress instead. "
    "Example: from pheno.testing.mcp_qa.oauth.progress import OAuthProgressFlow",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["InlineProgress", "OAuthProgressFlow", "inline_progress"]
