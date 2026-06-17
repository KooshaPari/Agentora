"""
Shared pytest fixtures for core pheno tests.
"""

from __future__ import annotations

import pytest

from pheno.adapters.container import Container
from pheno.adapters.container_config import configure_in_memory_container
from pheno.adapters.events.memory_publisher import InMemoryEventPublisher
from pheno.adapters.persistence.memory import (
    InMemoryConfigurationRepository,
    InMemoryDeploymentRepository,
    InMemoryServiceRepository,
    InMemoryUserRepository,
)


@pytest.fixture
def container() -> Container:
    return configure_in_memory_container()


@pytest.fixture
def clean_container() -> Container:
    return Container()


@pytest.fixture
def user_repository() -> InMemoryUserRepository:
    return InMemoryUserRepository()


@pytest.fixture
def deployment_repository() -> InMemoryDeploymentRepository:
    return InMemoryDeploymentRepository()


@pytest.fixture
def service_repository() -> InMemoryServiceRepository:
    return InMemoryServiceRepository()


@pytest.fixture
def configuration_repository() -> InMemoryConfigurationRepository:
    return InMemoryConfigurationRepository()


@pytest.fixture
def event_publisher() -> InMemoryEventPublisher:
    return InMemoryEventPublisher()


@pytest.fixture
def create_user_use_case(user_repository, event_publisher):
    from pheno.application.use_cases.user import CreateUserUseCase

    return CreateUserUseCase(user_repository, event_publisher)


@pytest.fixture
def update_user_use_case(user_repository, event_publisher):
    from pheno.application.use_cases.user import UpdateUserUseCase

    return UpdateUserUseCase(user_repository, event_publisher)


@pytest.fixture
def get_user_use_case(user_repository):
    from pheno.application.use_cases.user import GetUserUseCase

    return GetUserUseCase(user_repository)


@pytest.fixture
def list_users_use_case(user_repository):
    from pheno.application.use_cases.user import ListUsersUseCase

    return ListUsersUseCase(user_repository)


@pytest.fixture
def deactivate_user_use_case(user_repository, event_publisher):
    from pheno.application.use_cases.user import DeactivateUserUseCase

    return DeactivateUserUseCase(user_repository, event_publisher)


@pytest.fixture
def cli_adapter(
    user_repository,
    deployment_repository,
    service_repository,
    configuration_repository,
    event_publisher,
):
    from pheno.adapters.cli.adapter import CLIAdapter

    return CLIAdapter(
        user_repository=user_repository,
        deployment_repository=deployment_repository,
        service_repository=service_repository,
        configuration_repository=configuration_repository,
        event_publisher=event_publisher,
    )


@pytest.fixture
def user_commands(cli_adapter):
    from pheno.adapters.cli.commands import UserCommands

    return UserCommands(cli_adapter)


@pytest.fixture
def deployment_commands(cli_adapter):
    from pheno.adapters.cli.commands import DeploymentCommands

    return DeploymentCommands(cli_adapter)


@pytest.fixture
def service_commands(cli_adapter):
    from pheno.adapters.cli.commands import ServiceCommands

    return ServiceCommands(cli_adapter)


@pytest.fixture
def configuration_commands(cli_adapter):
    from pheno.adapters.cli.commands import ConfigurationCommands

    return ConfigurationCommands(cli_adapter)


@pytest.fixture
def sample_user_data():
    return {"email": "test@example.com", "name": "Test User"}


@pytest.fixture
def sample_deployment_data():
    return {"environment": "production", "strategy": "blue_green"}


@pytest.fixture
def sample_service_data():
    return {"name": "test-service", "port": 8000, "protocol": "http"}


@pytest.fixture
def sample_configuration_data():
    return {
        "key": "app.test.setting",
        "value": "test_value",
        "description": "Test configuration",
    }


@pytest.fixture
async def created_user(create_user_use_case, sample_user_data):
    from pheno.application.dtos.user import CreateUserDTO

    dto = CreateUserDTO(**sample_user_data)
    return await create_user_use_case.execute(dto)


@pytest.fixture
async def created_deployment(
    deployment_repository,
    event_publisher,
    sample_deployment_data,
):
    from pheno.application.dtos.deployment import CreateDeploymentDTO
    from pheno.application.use_cases.deployment import CreateDeploymentUseCase

    use_case = CreateDeploymentUseCase(deployment_repository, event_publisher)
    dto = CreateDeploymentDTO(**sample_deployment_data)
    return await use_case.execute(dto)


@pytest.fixture
async def created_service(
    service_repository,
    event_publisher,
    sample_service_data,
):
    from pheno.application.dtos.service import CreateServiceDTO
    from pheno.application.use_cases.service import CreateServiceUseCase

    use_case = CreateServiceUseCase(service_repository, event_publisher)
    dto = CreateServiceDTO(**sample_service_data)
    return await use_case.execute(dto)


def pytest_configure(config):
    config.addinivalue_line("markers", "unit: Unit tests (fast, isolated, no I/O)")
    config.addinivalue_line("markers", "integration: Integration tests (slower, may use I/O)")
    config.addinivalue_line("markers", "e2e: End-to-end tests (slowest, full system)")


def pytest_collection_modifyitems(config, items):
    for item in items:
        path = str(item.fspath)
        if "unit" in path:
            item.add_marker(pytest.mark.unit)
            item.add_marker(pytest.mark.fast)
        elif "integration" in path:
            item.add_marker(pytest.mark.integration)
        elif "e2e" in path:
            item.add_marker(pytest.mark.e2e)
            item.add_marker(pytest.mark.slow)

        if "domain" in path:
            item.add_marker(pytest.mark.domain)
        elif "application" in path:
            item.add_marker(pytest.mark.application)
        elif "adapters" in path:
            item.add_marker(pytest.mark.adapters)


__all__ = [
    "clean_container",
    "cli_adapter",
    "configuration_commands",
    "configuration_repository",
    "container",
    "create_user_use_case",
    "created_deployment",
    "created_service",
    "created_user",
    "deactivate_user_use_case",
    "deployment_commands",
    "deployment_repository",
    "event_publisher",
    "get_user_use_case",
    "list_users_use_case",
    "pytest_collection_modifyitems",
    "pytest_configure",
    "sample_configuration_data",
    "sample_deployment_data",
    "sample_service_data",
    "sample_user_data",
    "service_commands",
    "service_repository",
    "update_user_use_case",
    "user_commands",
    "user_repository",
]
