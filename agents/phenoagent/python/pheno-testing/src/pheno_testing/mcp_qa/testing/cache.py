"""
Test Cache - Backward compatibility wrapper

This module maintains backward compatibility by re-exporting BaseTestCache
as TestCache for existing code that imports from this location.

For new projects, consider importing BaseTestCache from test_cache.py directly
and creating your own concrete implementation.
"""

from pheno.testing.mcp_qa.testing.test_cache import BaseTestCache

# For backward compatibility
TestCache = BaseTestCache

__all__ = ["BaseTestCache", "TestCache"]
