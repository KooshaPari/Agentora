"""
Tenancy module for database multi-tenancy support.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class TenancyAdapter(ABC):
    """
    Base class for tenancy adapters.
    """

    @abstractmethod
    def get_tenant_id(self, context: dict[str, Any]) -> str | None:
        """
        Get tenant ID from context.
        """

    @abstractmethod
    def set_tenant_context(self, tenant_id: str) -> None:
        """
        Set tenant context for database operations.
        """


__all__ = ["TenancyAdapter"]
