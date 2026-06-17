"""
Vector module for database vector/embeddings support.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class VectorAdapter(ABC):
    """
    Base class for vector/embeddings adapters.
    """

    @abstractmethod
    def create_embedding(self, text: str) -> list[float]:
        """
        Create embedding for text.
        """

    @abstractmethod
    def search_similar(self, query_embedding: list[float], limit: int = 10) -> list[dict[str, Any]]:
        """
        Search for similar vectors.
        """

    @abstractmethod
    def store_vector(
        self, id: str, embedding: list[float], metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Store a vector with metadata.
        """


__all__ = ["VectorAdapter"]
