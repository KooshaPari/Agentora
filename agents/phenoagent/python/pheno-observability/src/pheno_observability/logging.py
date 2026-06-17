"""
Compatibility layer exposing logging helpers for observability.
"""

from __future__ import annotations

from pheno.logging.core.logger import get_logger as core_get_logger
from pheno.logging.integrations.structlog_adapter import configure_structlog_for_pheno


def configure_structlog() -> None:
    """
    Configure structlog using the standard Pheno adapter.
    """

    configure_structlog_for_pheno()


def get_logger(name: str):
    """
    Retrieve a configured Pheno logger.
    """

    return core_get_logger(name)


__all__ = ["configure_structlog", "get_logger"]
