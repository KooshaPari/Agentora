"""
Shared utilities for resource scheme handlers.
"""

from __future__ import annotations

import logging

LOGGER = logging.getLogger("pheno.mcp.resources.schemes")

try:  # pragma: no cover - optional dependency
    import psutil  # type: ignore[import-not-found]

    PSUTIL_AVAILABLE = True
except ImportError:  # pragma: no cover - psutil optional
    psutil = None  # type: ignore[assignment]
    PSUTIL_AVAILABLE = False

__all__ = ["LOGGER", "PSUTIL_AVAILABLE", "psutil"]
