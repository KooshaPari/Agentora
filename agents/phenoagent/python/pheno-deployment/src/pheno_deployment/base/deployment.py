"""Base Deployment Abstractions (Framework-Agnostic)

These classes define the interface for deployment operations.
Can be moved to pheno-sdk/deploy-kit/base/

No platform-specific code here - only abstract interfaces.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any


class DeploymentEnvironment(Enum):
    """
    Deployment environment types.
    """

    LOCAL = "local"
    PREVIEW = "preview"
    STAGING = "staging"
    PRODUCTION = "production"


class DeploymentStatus(Enum):
    """
    Deployment status.
    """

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class DeploymentConfig:
    """
    Configuration for a deployment.
    """

    environment: DeploymentEnvironment
    project_root: Path
    env_file: Path | None = None
    domain: str | None = None
    build_command: str | None = None
    install_command: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary.
        """
        return {
            "environment": self.environment.value,
            "project_root": str(self.project_root),
            "env_file": str(self.env_file) if self.env_file else None,
            "domain": self.domain,
            "build_command": self.build_command,
            "install_command": self.install_command,
        }


@dataclass
class DeploymentResult:
    """
    Result of a deployment operation.
    """

    status: DeploymentStatus
    environment: DeploymentEnvironment
    url: str | None = None
    deployment_id: str | None = None
    error_message: str | None = None
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary.
        """
        return {
            "status": self.status.value,
            "environment": self.environment.value,
            "url": self.url,
            "deployment_id": self.deployment_id,
            "error_message": self.error_message,
            "metadata": self.metadata or {},
        }

    @property
    def success(self) -> bool:
        """
        Check if deployment was successful.
        """
        return self.status == DeploymentStatus.SUCCESS


class DeploymentProvider(ABC):
    """Abstract base class for deployment providers.

    This defines the interface that all deployment providers must implement. Platform-
    specific implementations (Vercel, AWS, etc.) inherit from this.
    """

    def __init__(self, config: DeploymentConfig, logger=None):
        self.config = config
        self.logger = logger

    @abstractmethod
    def validate_config(self) -> bool:
        """Validate deployment configuration.

        Returns:
            True if configuration is valid, False otherwise
        """

    @abstractmethod
    def check_prerequisites(self) -> bool:
        """Check if all prerequisites are met (CLI installed, auth, etc.).

        Returns:
            True if prerequisites are met, False otherwise
        """

    @abstractmethod
    def deploy(self) -> DeploymentResult:
        """Execute the deployment.

        Returns:
            DeploymentResult with status and details
        """

    @abstractmethod
    def rollback(self, deployment_id: str) -> DeploymentResult:
        """Rollback to a previous deployment.

        Args:
            deployment_id: ID of deployment to rollback to

        Returns:
            DeploymentResult with rollback status
        """

    @abstractmethod
    def get_deployment_url(self) -> str | None:
        """Get the URL of the deployed application.

        Returns:
            URL string or None if not available
        """

    def log_info(self, message: str):
        """
        Log info message.
        """
        if self.logger:
            self.logger.info(message)

    def log_error(self, message: str):
        """
        Log error message.
        """
        if self.logger:
            self.logger.error(message)

    def log_warning(self, message: str):
        """
        Log warning message.
        """
        if self.logger and hasattr(self.logger, "warning"):
            self.logger.warning(message)


class HealthCheckProvider(ABC):
    """
    Abstract base class for health check providers.
    """

    @abstractmethod
    def check(self, url: str, timeout: int = 10) -> bool:
        """Check if URL is healthy.

        Args:
            url: URL to check
            timeout: Timeout in seconds

        Returns:
            True if healthy, False otherwise
        """

    @abstractmethod
    def check_with_retries(
        self, url: str, max_retries: int = 5, retry_delay: int = 2, timeout: int = 10,
    ) -> bool:
        """Check URL health with retries.

        Args:
            url: URL to check
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
            timeout: Timeout per attempt in seconds

        Returns:
            True if healthy, False otherwise
        """


class ServerProvider(ABC):
    """
    Abstract base class for server providers.
    """

    @abstractmethod
    def start(self, port: int, **kwargs) -> int:
        """Start the server.

        Args:
            port: Port to run on
            **kwargs: Additional provider-specific arguments

        Returns:
            Exit code (0 for success)
        """

    @abstractmethod
    def stop(self) -> int:
        """Stop the server.

        Returns:
            Exit code (0 for success)
        """

    @abstractmethod
    def get_status(self) -> dict[str, Any]:
        """Get server status.

        Returns:
            Dictionary with status information
        """


class TunnelProvider(ABC):
    """
    Abstract base class for tunnel providers (CloudFlare, ngrok, etc.).
    """

    @abstractmethod
    def start_tunnel(self, port: int, domain: str | None = None) -> str | None:
        """Start tunnel to local port.

        Args:
            port: Local port to tunnel to
            domain: Optional custom domain

        Returns:
            Public URL or None if failed
        """

    @abstractmethod
    def stop_tunnel(self, port: int) -> bool:
        """Stop tunnel for port.

        Args:
            port: Port to stop tunnel for

        Returns:
            True if stopped successfully
        """

    @abstractmethod
    def get_tunnel_url(self, port: int) -> str | None:
        """Get tunnel URL for port.

        Args:
            port: Port to get URL for

        Returns:
            URL or None if no tunnel
        """


class ConfigurationProvider(ABC):
    """
    Abstract base class for configuration providers.
    """

    @abstractmethod
    def load(self, source: Path) -> dict[str, Any]:
        """Load configuration from source.

        Args:
            source: Path to configuration file

        Returns:
            Configuration dictionary
        """

    @abstractmethod
    def save(self, config: dict[str, Any], _destination: Path) -> bool:
        """Save configuration to destination.

        Args:
            config: Configuration dictionary
            destination: Path to save to

        Returns:
            True if saved successfully
        """

    @abstractmethod
    def validate(self, config: dict[str, Any]) -> bool:
        """Validate configuration.

        Args:
            config: Configuration to validate

        Returns:
            True if valid
        """
