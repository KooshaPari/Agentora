"""Domain repository ports."""

from abc import ABC, abstractmethod
from typing import List, Optional
from .entities import Entity


class EntityRepository(ABC):
    """Repository port for entity persistence."""
    
    @abstractmethod
    def create(self, entity: Entity) -> None:
        """Create a new entity."""
        pass
    
    @abstractmethod
    def get_by_id(self, entity_id: str) -> Optional[Entity]:
        """Get entity by ID."""
        pass
    
    @abstractmethod
    def update(self, entity: Entity) -> None:
        """Update an existing entity."""
        pass
    
    @abstractmethod
    def delete(self, entity_id: str) -> None:
        """Delete an entity by ID."""
        pass
    
    @abstractmethod
    def list_all(self) -> List[Entity]:
        """List all entities."""
        pass
