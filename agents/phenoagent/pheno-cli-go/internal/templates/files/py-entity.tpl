"""{{.RepoName}} - Domain entities."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid


@dataclass
class Entity:
    """Core domain entity."""
    
    name: str
    description: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def update(self, name: Optional[str] = None, description: Optional[str] = None) -> None:
        """Update entity fields."""
        if name is not None:
            self.name = name
        if description is not None:
            self.description = description
        self.updated_at = datetime.utcnow()


class DomainError(Exception):
    """Base domain error."""
    pass


class EntityNotFoundError(DomainError):
    """Raised when entity is not found."""
    pass


class InvalidInputError(DomainError):
    """Raised when input is invalid."""
    pass
