"""Test data factories using polyfactory.

Provides base factories and utilities for generating test data.
"""

from typing import Any, TypeVar

import pytest

try:
    from faker import Faker
    from polyfactory.factories import DataclassFactory
    from polyfactory.factories.pydantic_factory import ModelFactory

    POLYFACTORY_AVAILABLE = True
except ImportError:
    POLYFACTORY_AVAILABLE = False
    DataclassFactory = object
    ModelFactory = object

try:
    from pydantic import BaseModel

    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    BaseModel = object


T = TypeVar("T")


# ============================================================================
# Base Factory Classes
# ============================================================================

if POLYFACTORY_AVAILABLE:

    class BaseFactory(DataclassFactory):
        """Base factory for dataclasses.

        Example:
            from dataclasses import dataclass

            @dataclass
            class User:
                id: int
                name: str
                email: str

            class UserFactory(BaseFactory):
                __model__ = User

                @classmethod
                def name(cls) -> str:
                    return cls.__faker__.name()

                @classmethod
                def email(cls) -> str:
                    return cls.__faker__.email()

            # Create test data
            user = UserFactory.build()
            users = UserFactory.batch(10)
        """

        __faker__ = Faker()

    class AsyncFactory(ModelFactory):
        """Base factory for Pydantic models with async support.

        Example:
            from pydantic import BaseModel

            class User(BaseModel):
                id: int
                name: str
                email: str

            class UserFactory(AsyncFactory):
                __model__ = User

                @classmethod
                def email(cls) -> str:
                    return cls.__faker__.email()

            # Create test data
            user = UserFactory.build()
            users = UserFactory.batch(10)
        """

        __faker__ = Faker()

        @classmethod
        async def build_async(cls, **kwargs) -> Any:
            """Build a model instance asynchronously.

            Useful for models that require async initialization.
            """
            instance = cls.build(**kwargs)

            # If model has async init, call it
            if hasattr(instance, "__ainit__"):
                await instance.__ainit__()

            return instance

        @classmethod
        async def batch_async(cls, size: int, **kwargs) -> list:
            """
            Build multiple instances asynchronously.
            """
            instances = cls.batch(size, **kwargs)

            # If models have async init, call them
            if instances and hasattr(instances[0], "__ainit__"):
                for instance in instances:
                    await instance.__ainit__()

            return instances

else:
    # Fallback when polyfactory not available
    class BaseFactory:
        """
        Fallback factory when polyfactory not available.
        """

        @classmethod
        def build(cls, **kwargs):
            raise ImportError("polyfactory not installed")

        @classmethod
        def batch(cls, size: int, **kwargs):
            raise ImportError("polyfactory not installed")

    class AsyncFactory(BaseFactory):
        """
        Fallback async factory when polyfactory not available.
        """


# ============================================================================
# Factory Utilities
# ============================================================================


def create_factory(model: type[T], **field_overrides) -> type[BaseFactory]:
    """Create a factory for a model dynamically.

    Args:
        model: Model class to create factory for
        **field_overrides: Field value overrides

    Returns:
        Factory class

    Example:
        from dataclasses import dataclass

        @dataclass
        class User:
            id: int
            name: str

        UserFactory = create_factory(User, name=lambda: "Test User")
        user = UserFactory.build()
    """
    if not POLYFACTORY_AVAILABLE:
        raise ImportError("polyfactory not installed")

    # Determine base factory class
    if PYDANTIC_AVAILABLE and isinstance(model, type) and issubclass(model, BaseModel):
        base_class = AsyncFactory
    else:
        base_class = BaseFactory

    # Create factory class
    factory_attrs = {"__model__": model, **field_overrides}

    return type(f"{model.__name__}Factory", (base_class,), factory_attrs)



# ============================================================================
# Common Field Generators
# ============================================================================

if POLYFACTORY_AVAILABLE:
    faker = Faker()

    # Common field generators
    def random_email() -> str:
        """
        Generate random email.
        """
        return faker.email()

    def random_name() -> str:
        """
        Generate random name.
        """
        return faker.name()

    def random_username() -> str:
        """
        Generate random username.
        """
        return faker.user_name()

    def random_password() -> str:
        """
        Generate random password.
        """
        return faker.password(length=12)

    def random_url() -> str:
        """
        Generate random URL.
        """
        return faker.url()

    def random_uuid() -> str:
        """
        Generate random UUID.
        """
        return faker.uuid4()

    def random_phone() -> str:
        """
        Generate random phone number.
        """
        return faker.phone_number()

    def random_address() -> str:
        """
        Generate random address.
        """
        return faker.address()

    def random_company() -> str:
        """
        Generate random company name.
        """
        return faker.company()

    def random_text(max_chars: int = 200) -> str:
        """Generate random text.

        Args:
            max_chars: Maximum number of characters
        """
        return faker.text(max_nb_chars=max_chars)

    def random_sentence() -> str:
        """
        Generate random sentence.
        """
        return faker.sentence()

    def random_paragraph() -> str:
        """
        Generate random paragraph.
        """
        return faker.paragraph()

else:
    # Fallback generators
    def random_email() -> str:
        raise ImportError("faker not installed")

    def random_name() -> str:
        raise ImportError("faker not installed")

    # ... (other fallbacks)


# ============================================================================
# Pytest Fixtures
# ============================================================================


@pytest.fixture
def factory_faker():
    """Provide Faker instance for tests.

    Example:
        def test_with_faker(factory_faker):
            email = factory_faker.email()
            name = factory_faker.name()
    """
    if not POLYFACTORY_AVAILABLE:
        pytest.skip("faker not installed")

    return Faker()


__all__ = [
    "AsyncFactory",
    "BaseFactory",
    "create_factory",
    "factory_faker",
    "random_address",
    "random_company",
    "random_email",
    "random_name",
    "random_paragraph",
    "random_password",
    "random_phone",
    "random_sentence",
    "random_text",
    "random_url",
    "random_username",
    "random_uuid",
]
