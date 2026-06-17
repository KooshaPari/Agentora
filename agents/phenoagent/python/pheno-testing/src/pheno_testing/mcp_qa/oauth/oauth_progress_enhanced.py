"""
Enhanced OAuth Progress Display - Redirect to Unified Progress

DEPRECATED: This module is deprecated and will be removed in a future version.
Please import from mcp_qa.oauth.progress instead.

The "enhanced" features have been merged into the unified progress module.

Migration Guide:
    OLD: from pheno.testing.mcp_qa.oauth.oauth_progress_enhanced import EnhancedOAuthProgressFlow
    NEW: from pheno.testing.mcp_qa.oauth.progress import OAuthProgressFlow

    The unified OAuthProgressFlow includes all enhanced features.
"""

import warnings

# Re-export from unified progress module
# Note: EnhancedOAuthProgressFlow is now just OAuthProgressFlow
from .progress import InlineProgress
from .progress import OAuthProgressFlow as EnhancedOAuthProgressFlow
from .progress import inline_progress

# Issue deprecation warning
warnings.warn(
    "mcp_qa.oauth.oauth_progress_enhanced is deprecated. "
    "Please import from mcp_qa.oauth.progress instead. "
    "The unified OAuthProgressFlow includes all enhanced features.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["EnhancedOAuthProgressFlow", "InlineProgress", "inline_progress"]
