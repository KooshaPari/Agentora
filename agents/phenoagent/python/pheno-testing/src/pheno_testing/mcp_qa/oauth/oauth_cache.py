"""
OAuth Token Caching - Redirect to Unified Cache

DEPRECATED: This module is deprecated and will be removed in a future version.
Please import from mcp_qa.oauth.cache instead.

This file now re-exports all functionality from the unified cache module
to maintain backward compatibility with existing code.

Migration Guide:
    OLD: from pheno.testing.mcp_qa.oauth.oauth_cache import CachedOAuthClient
    NEW: from pheno.testing.mcp_qa.oauth.cache import CachedOAuthClient

    Or even better:
    from pheno.testing.mcp_qa.oauth import CachedOAuthClient, create_cached_client
"""

import warnings

# Re-export from unified cache module
from .cache import CachedOAuthClient, create_cached_client

# Issue deprecation warning
warnings.warn(
    "mcp_qa.oauth.oauth_cache is deprecated. "
    "Please import from mcp_qa.oauth.cache instead. "
    "Example: from pheno.testing.mcp_qa.oauth.cache import CachedOAuthClient",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["CachedOAuthClient", "create_cached_client"]
