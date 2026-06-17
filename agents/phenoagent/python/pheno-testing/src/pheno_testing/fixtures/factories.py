"""
Test Fixture Factories - Reduce duplication with factory pattern.

Instead of creating separate fixture classes for each repository type,
use a generic factory that can create any type of in-memory repository.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

T = TypeVar("T")


@dataclass
class RepositoryConfig:
    """
    Configuration for repository factory.
    """

    id_field: str = "id"
    find_methods: dict[str, str] = field(default_factory=dict)  # method_name -> field_name
    filter_methods: dict[str, Callable] = field(default_factory=dict)  # method_name -> filter_func


class InMemoryRepository(Generic[T]):
    """Generic in-memory repository for testing.

    Replaces multiple specific repository implementations with a single
    configurable class.

    Example:
        >>> # Instead of InMemoryUserRepository, InMemoryDeploymentRepository, etc.
        >>> user_repo = InMemoryRepository[User](id_field="id")
        >>> deployment_repo = InMemoryRepository[Deployment](id_field="id")
        >>>
        >>> # Use the same interface
        >>> await user_repo.save(user)
        >>> found = await user_repo.find_by_id(user_id)
    """

    def __init__(self, config: RepositoryConfig | None = None):
        self.config = config or RepositoryConfig()
        self._items: dict[str, T] = {}

    async def save(self, item: T) -> None:
        """
        Save an item.
        """
        item_id = str(getattr(item, self.config.id_field))
        self._items[item_id] = item

    async def find_by_id(self, item_id: Any) -> T | None:
        """
        Find item by ID.
        """
        return self._items.get(str(item_id))

    async def find_by(self, field: str, value: Any) -> T | None:
        """
        Find item by any field.
        """
        for item in self._items.values():
            if getattr(item, field, None) == value:
                return item
        return None

    async def find_all_by(self, field: str, value: Any) -> list[T]:
        """
        Find all items matching a field value.
        """
        return [item for item in self._items.values() if getattr(item, field, None) == value]

    async def delete(self, item_id: Any) -> None:
        """
        Delete an item.
        """
        self._items.pop(str(item_id), None)

    async def find_all(self, limit: int = 100, offset: int = 0, **filters) -> list[T]:
        """
        Find all items with pagination and filtering.
        """
        items = list(self._items.values())

        # Apply filters
        for field, value in filters.items():
            if value is not None:
                items = [item for item in items if getattr(item, field, None) == value]

        return items[offset : offset + limit]

    async def count(self, **filters) -> int:
        """
        Count items with optional filtering.
        """
        items = list(self._items.values())

        for field, value in filters.items():
            if value is not None:
                items = [item for item in items if getattr(item, field, None) == value]

        return len(items)

    def clear(self) -> None:
        """
        Clear all items (useful for test cleanup).
        """
        self._items.clear()


class InMemoryEventBus:
    """Generic in-memory event bus for testing.

    Replaces multiple event bus implementations.
    """

    def __init__(self):
        self._events: list[Any] = []
        self._handlers: dict[str, list[Callable]] = {}

    async def publish(self, event: Any) -> None:
        """
        Publish an event.
        """
        self._events.append(event)

        # Call registered handlers
        event_type = type(event).__name__
        for handler in self._handlers.get(event_type, []):
            await handler(event)

    def subscribe(self, event_type: str, handler: Callable) -> None:
        """
        Subscribe to an event type.
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def get_events(self, event_type: str | None = None) -> list[Any]:
        """
        Get published events, optionally filtered by type.
        """
        if event_type is None:
            return self._events.copy()

        return [event for event in self._events if type(event).__name__ == event_type]

    def clear(self) -> None:
        """
        Clear all events (useful for test cleanup).
        """
        self._events.clear()

    def count(self, event_type: str | None = None) -> int:
        """
        Count events, optionally filtered by type.
        """
        return len(self.get_events(event_type))


class MockService(Generic[T]):
    """Generic mock service for testing.

    Provides a simple way to mock any service with configurable responses.
    """

    def __init__(self):
        self._responses: dict[str, Any] = {}
        self._calls: list[tuple] = []

    def set_response(self, method: str, response: Any) -> None:
        """
        Set the response for a method call.
        """
        self._responses[method] = response

    def get_calls(self, method: str | None = None) -> list[tuple]:
        """
        Get recorded calls, optionally filtered by method.
        """
        if method is None:
            return self._calls.copy()

        return [call for call in self._calls if call[0] == method]

    def clear_calls(self) -> None:
        """
        Clear recorded calls.
        """
        self._calls.clear()

    async def __call__(self, method: str, *args, **kwargs) -> Any:
        """
        Record call and return configured response.
        """
        self._calls.append((method, args, kwargs))
        return self._responses.get(method)


# Pytest fixtures using factories


def pytest_fixtures():
    """Example pytest fixtures using the factory pattern.

    Add these to your conftest.py:
    """
    import pytest

    @pytest.fixture
    def repo_factory():
        """
        Factory for creating in-memory repositories.
        """

        def create(entity_type, **config_kwargs):
            config = RepositoryConfig(**config_kwargs)
            return InMemoryRepository[entity_type](config)

        return create

    @pytest.fixture
    def event_bus():
        """
        In-memory event bus for testing.
        """
        bus = InMemoryEventBus()
        yield bus
        bus.clear()

    @pytest.fixture
    def mock_service_factory():
        """
        Factory for creating mock services.
        """

        def create():
            return MockService()

        return create

    # Example usage in tests:
    # def test_user_repository(repo_factory):
    #     user_repo = repo_factory(User, id_field="id")
    #     await user_repo.save(user)
    #     found = await user_repo.find_by_id(user.id)
    #     assert found == user


__all__ = [
    "InMemoryEventBus",
    "InMemoryRepository",
    "MockService",
    "RepositoryConfig",
    "pytest_fixtures",
]
