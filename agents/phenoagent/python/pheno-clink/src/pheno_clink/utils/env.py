"""
Simplified environment access for clink.
"""

from __future__ import annotations

import os


def get_env(key: str, default: str | None = None) -> str | None:
    """
    Get environment variable with optional default.
    """
    return os.environ.get(key, default)
