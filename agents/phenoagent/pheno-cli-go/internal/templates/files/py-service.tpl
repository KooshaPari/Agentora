"""Application service for entity management."""

from typing import List
from {{.RepoName}}.domain.entities import Entity, EntityNotFoundError, InvalidInputError
from {{.RepoName}}.domain.ports import EntityRepository


class EntityService:
    """Service for entity use cases."""
    
    def __init__(self, repository: EntityRepository):
        self.repository = repository
    
    def create_entity(self, name: str, description: str = "") -> Entity:
        """Create a new entity."""
        if not name:
            raise InvalidInputError("Name is required")
        
        entity = Entity(name=name, description=description)
        self.repository.create(entity)
        return entity
    
    def get_entity(self, entity_id: str) -> Entity:
        """Get entity by ID."""
        entity = self.repository.get_by_id(entity_id)
        if entity is None:
            raise EntityNotFoundError(f"Entity {entity_id} not found")
        return entity
    
    def update_entity(self, entity_id: str, name: str, description: str = "") -> Entity:
        """Update an entity."""
        entity = self.get_entity(entity_id)
        entity.update(name=name, description=description)
        self.repository.update(entity)
        return entity
    
    def delete_entity(self, entity_id: str) -> None:
        """Delete an entity."""
        self.repository.delete(entity_id)
    
    def list_entities(self) -> List[Entity]:
        """List all entities."""
        return self.repository.list_all()
