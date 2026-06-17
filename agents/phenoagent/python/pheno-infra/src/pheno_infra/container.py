"""
Backward-compatible shim for infrastructure container helpers.
"""

from __future__ import annotations

from pheno.infrastructure import (
    get_container,
)
from pheno.infrastructure import (
    register_default_adapters as register_default_infrastructure,
)
from pheno.infrastructure import run_health_checks as run_container_health_checks

__all__ = [
    "get_container",
    "register_default_infrastructure",
    "run_container_health_checks",
]
