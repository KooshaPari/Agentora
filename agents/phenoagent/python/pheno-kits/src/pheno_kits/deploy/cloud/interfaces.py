"""
Core interfaces for cloud provider abstraction.
"""

from abc import ABC, abstractmethod
from typing import Protocol

from .types import (
    AlertConfig,
    Backup,
    BackupConfig,
    Capability,
    Cost,
    CostEstimate,
    Credentials,
    Deployment,
    DeploymentConfig,
    DeploymentStatus,
    HealthCheckStatus,
    LogOptions,
    LogStream,
    Metric,
    MetricOptions,
    Migration,
    PoolConfig,
    ProjectConfig,
    ProjectDeployment,
    ProjectStatus,
    ProviderMetadata,
    Resource,
    ResourceConfig,
    ResourceFilter,
    ResourceType,
    ScaleConfig,
    TimeRange,
)


class CloudProvider(ABC):
    """Core interface for all cloud providers.

    Providers should return NotSupportedError for operations they don't support. Use
    get_capabilities() to check what a provider supports before calling operations.
    """

    @abstractmethod
    def get_metadata(self) -> ProviderMetadata:
        """
        Return provider metadata and capabilities.
        """
        ...

    @abstractmethod
    def supports_resource(self, resource_type: ResourceType) -> bool:
        """
        Check if provider supports a resource type.
        """
        ...

    @abstractmethod
    def get_capabilities(self) -> list[Capability]:
        """
        Return list of optional capabilities this provider supports.
        """
        ...

    @abstractmethod
    async def initialize(self, credentials: Credentials) -> None:
        """
        Initialize provider with credentials and validate connectivity.
        """
        ...

    @abstractmethod
    async def validate_credentials(self) -> bool:
        """
        Validate that credentials are valid.
        """
        ...

    @abstractmethod
    async def create_resource(self, config: ResourceConfig) -> Resource:
        """
        Create a new cloud resource.
        """
        ...

    @abstractmethod
    async def get_resource(self, resource_id: str) -> Resource:
        """
        Get information about a specific resource.
        """
        ...

    @abstractmethod
    async def update_resource(self, resource_id: str, config: ResourceConfig) -> Resource:
        """
        Update an existing resource.
        """
        ...

    @abstractmethod
    async def delete_resource(self, resource_id: str) -> None:
        """
        Delete a resource.
        """
        ...

    @abstractmethod
    async def list_resources(self, filter: ResourceFilter | None = None) -> list[Resource]:
        """
        List resources matching filter criteria.
        """
        ...

    @abstractmethod
    async def deploy(self, deployment: DeploymentConfig) -> Deployment:
        """
        Deploy code or configuration to a resource.
        """
        ...

    @abstractmethod
    async def get_deployment_status(self, deployment_id: str) -> DeploymentStatus:
        """
        Get current status of a deployment.
        """
        ...

    @abstractmethod
    async def rollback_deployment(self, deployment_id: str) -> None:
        """
        Rollback a deployment to previous version.
        """
        ...

    @abstractmethod
    async def get_logs(self, resource: Resource, opts: LogOptions) -> LogStream:
        """
        Retrieve logs from a resource.
        """
        ...

    @abstractmethod
    async def get_metrics(self, resource: Resource, opts: MetricOptions) -> list[Metric]:
        """
        Retrieve performance metrics from a resource.
        """
        ...

    @abstractmethod
    async def estimate_cost(self, config: ResourceConfig) -> CostEstimate:
        """
        Estimate cost of a resource configuration.
        """
        ...

    @abstractmethod
    async def get_actual_cost(self, resource: Resource, time_range: TimeRange) -> Cost:
        """
        Get actual incurred cost for a resource.
        """
        ...


class Scalable(Protocol):
    """
    Optional interface for resources that support scaling.
    """

    async def set_scale(self, resource_id: str, config: ScaleConfig) -> None:
        """
        Manually set scale configuration.
        """
        ...

    async def get_scale_config(self, resource_id: str) -> ScaleConfig:
        """
        Get current scale configuration.
        """
        ...

    async def auto_scale(self, resource_id: str, enabled: bool) -> None:
        """
        Enable or disable auto-scaling.
        """
        ...


class Loggable(Protocol):
    """
    Optional interface for resources that support logging.
    """

    async def stream_logs(self, resource_id: str, opts: LogOptions) -> LogStream:
        """
        Provide real-time stream of logs.
        """
        ...

    async def set_log_level(self, resource_id: str, level: str) -> None:
        """
        Change logging level.
        """
        ...

    async def get_log_retention(self, resource_id: str) -> int:
        """
        Get log retention settings in days.
        """
        ...


class Executable(Protocol):
    """
    Optional interface for resources that support command execution.
    """

    async def exec(self, resource_id: str, command: str) -> str:
        """
        Execute a command and return output.
        """
        ...

    async def run_command(self, resource_id: str, command: str) -> LogStream:
        """
        Run a command and stream output.
        """
        ...

    async def get_shell(self, resource_id: str, instance_id: str) -> None:
        """
        Open an interactive shell (if supported).
        """
        ...


class Backupable(Protocol):
    """
    Optional interface for resources that support backups.
    """

    async def create_backup(self, resource_id: str, config: BackupConfig) -> Backup:
        """
        Create a new backup.
        """
        ...

    async def restore_backup(self, resource_id: str, backup_id: str) -> None:
        """
        Restore from a backup.
        """
        ...

    async def list_backups(self, resource_id: str) -> list[Backup]:
        """
        List available backups.
        """
        ...

    async def delete_backup(self, backup_id: str) -> None:
        """
        Delete a backup.
        """
        ...

    async def get_backup_config(self, resource_id: str) -> BackupConfig:
        """
        Get backup configuration.
        """
        ...

    async def set_backup_config(self, resource_id: str, config: BackupConfig) -> None:
        """
        Update backup configuration.
        """
        ...


class Monitorable(Protocol):
    """
    Optional interface for resources that support monitoring.
    """

    async def set_alert(self, resource_id: str, alert: AlertConfig) -> None:
        """
        Configure an alert for a metric.
        """
        ...

    async def list_alerts(self, resource_id: str) -> list[AlertConfig]:
        """
        List configured alerts.
        """
        ...

    async def delete_alert(self, alert_id: str) -> None:
        """
        Remove an alert.
        """
        ...

    async def get_health_check(self, resource_id: str) -> HealthCheckStatus:
        """
        Get health check status.
        """
        ...


class DatabaseProvider(CloudProvider):
    """
    Extended interface for database-specific operations.
    """

    @abstractmethod
    async def get_connection_string(self, resource_id: str) -> str:
        """
        Get connection string for database.
        """
        ...

    @abstractmethod
    async def execute_migration(self, resource_id: str, migration: Migration) -> None:
        """
        Run a database migration.
        """
        ...

    @abstractmethod
    async def list_migrations(self, resource_id: str) -> list[Migration]:
        """
        List applied migrations.
        """
        ...

    @abstractmethod
    async def create_database(self, resource_id: str, db_name: str) -> None:
        """
        Create a database within the resource.
        """
        ...

    @abstractmethod
    async def list_databases(self, resource_id: str) -> list[str]:
        """
        List databases within the resource.
        """
        ...

    @abstractmethod
    async def set_connection_pooling(self, resource_id: str, config: PoolConfig) -> None:
        """
        Configure connection pooling.
        """
        ...


class ProviderRegistry(ABC):
    """
    Registry for managing cloud providers.
    """

    @abstractmethod
    def register(self, metadata: ProviderMetadata, factory: callable) -> None:
        """
        Register a provider.
        """
        ...

    @abstractmethod
    def unregister(self, provider_name: str) -> None:
        """
        Unregister a provider.
        """
        ...

    @abstractmethod
    def get(self, provider_name: str, credentials: Credentials) -> CloudProvider:
        """
        Get a provider instance.
        """
        ...

    @abstractmethod
    def list(self) -> list[ProviderMetadata]:
        """
        List all registered providers.
        """
        ...

    @abstractmethod
    def supports(self, provider_name: str, resource_type: ResourceType) -> bool:
        """
        Check if provider supports a resource type.
        """
        ...

    @abstractmethod
    def get_metadata(self, provider_name: str) -> ProviderMetadata:
        """
        Get provider metadata.
        """
        ...


class DeploymentOrchestrator(ABC):
    """
    Manages multi-provider deployments.
    """

    @abstractmethod
    async def deploy_project(self, config: ProjectConfig) -> ProjectDeployment:
        """
        Deploy an entire project across multiple providers.
        """
        ...

    @abstractmethod
    async def update_project(self, project_id: str, config: ProjectConfig) -> ProjectDeployment:
        """
        Update a deployed project.
        """
        ...

    @abstractmethod
    async def get_project_status(self, project_id: str) -> ProjectStatus:
        """
        Get status of a project deployment.
        """
        ...

    @abstractmethod
    async def delete_project(self, project_id: str) -> None:
        """
        Remove all resources for a project.
        """
        ...

    @abstractmethod
    async def rollback_project(self, project_id: str) -> None:
        """
        Rollback all resources to previous versions.
        """
        ...
