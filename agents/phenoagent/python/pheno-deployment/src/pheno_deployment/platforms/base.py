"""
Base platform adapter.
"""

from abc import ABC, abstractmethod
from typing import Any


class PlatformAdapter(ABC):
    @abstractmethod
    async def deploy(self, config: dict[str, Any]) -> dict[str, Any]:
        """
        Deploy to platform.
        """
