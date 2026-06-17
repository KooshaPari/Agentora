"""
Phase 6: Configuration & Developer Experience - Enhanced Configuration Schemas

This module provides comprehensive configuration schemas that integrate all Phase 5
features (Process Governance, Tunnel Governance, Cleanup Policies, Status Pages)
with the existing KInfra configuration system.

Features:
- Pydantic v2 BaseModel schemas for all Phase 5 components
- Hierarchical configuration loading (env > files > defaults)
- Type safety and validation
- Integration with existing config-kit
- Default values optimized for production use
"""

from __future__ import annotations

import logging
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)


class CleanupStrategy(StrEnum):
    """Cleanup strategy options."""

    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


class ResourceType(StrEnum):
    """Resource types for cleanup policies."""

    PROCESS = "process"
    TUNNEL = "tunnel"
    PORT = "port"
    FILE = "file"
    NETWORK = "network"
    CACHE = "cache"
    LOG = "log"


class TunnelLifecyclePolicy(StrEnum):
    """Tunnel lifecycle policy options."""

    REUSE = "reuse"
    RECREATE = "recreate"
    SMART = "smart"


class TunnelCredentialScope(StrEnum):
    """Tunnel credential scope options."""

    GLOBAL = "global"
    PROJECT = "project"
    SERVICE = "service"


class ProcessGovernanceConfig(BaseModel):
    """Configuration for process governance manager."""

    # Process tracking
    enable_metadata_tracking: bool = Field(
        default=True, description="Enable metadata-based process tracking",
    )
    max_process_age: float = Field(
        default=3600.0, description="Maximum age for processes before cleanup (seconds)",
    )
    cleanup_interval: float = Field(
        default=300.0, description="Interval for automatic cleanup (seconds)",
    )

    # Process identification
    process_name_patterns: list[str] = Field(
        default_factory=lambda: [
            "python",
            "node",
            "java",
            "go",
            "rust",
            "docker",
            "kubectl",
            "terraform",
            "ansible",
        ],
        description="Patterns to identify managed processes",
    )
    exclude_patterns: list[str] = Field(
        default_factory=lambda: ["systemd", "kernel", "init", "kthreadd"],
        description="Patterns to exclude from process management",
    )

    # Cleanup behavior
    force_cleanup: bool = Field(
        default=False, description="Force cleanup of processes that don't respond to SIGTERM",
    )
    cleanup_timeout: float = Field(
        default=30.0, description="Timeout for process cleanup (seconds)",
    )

    # Metadata requirements
    require_project_metadata: bool = Field(
        default=True, description="Require project metadata for process registration",
    )
    require_service_metadata: bool = Field(
        default=True, description="Require service metadata for process registration",
    )


class TunnelGovernanceConfig(BaseModel):
    """Configuration for tunnel governance manager."""

    # Tunnel lifecycle
    default_lifecycle_policy: TunnelLifecyclePolicy = Field(
        default=TunnelLifecyclePolicy.SMART, description="Default tunnel lifecycle policy",
    )
    tunnel_reuse_threshold: float = Field(
        default=1800.0, description="Threshold for tunnel reuse (seconds)",
    )
    max_tunnel_age: float = Field(
        default=7200.0, description="Maximum age for tunnels before cleanup (seconds)",
    )

    # Credential management
    credential_scope: TunnelCredentialScope = Field(
        default=TunnelCredentialScope.PROJECT, description="Default credential scope",
    )
    credential_cache_ttl: float = Field(
        default=3600.0, description="Credential cache TTL (seconds)",
    )

    # Tunnel providers
    default_provider: str = Field(default="cloudflare", description="Default tunnel provider")
    supported_providers: list[str] = Field(
        default_factory=lambda: ["cloudflare", "ngrok", "localtunnel"],
        description="Supported tunnel providers",
    )

    # Health monitoring
    health_check_interval: float = Field(
        default=60.0, description="Tunnel health check interval (seconds)",
    )
    health_check_timeout: float = Field(
        default=10.0, description="Tunnel health check timeout (seconds)",
    )

    # Cleanup behavior
    auto_cleanup_stale: bool = Field(
        default=True, description="Automatically cleanup stale tunnels",
    )
    cleanup_interval: float = Field(
        default=300.0, description="Interval for automatic tunnel cleanup (seconds)",
    )


class CleanupRuleConfig(BaseModel):
    """Configuration for a specific cleanup rule."""

    resource_type: ResourceType = Field(description="Type of resource to clean up")
    strategy: CleanupStrategy = Field(description="Cleanup strategy to use")
    patterns: list[str] = Field(default_factory=list, description="Patterns to match resources")
    exclude_patterns: list[str] = Field(
        default_factory=list, description="Patterns to exclude from cleanup",
    )
    max_age: float | None = Field(
        default=None, description="Maximum age for resources (seconds)",
    )
    force_cleanup: bool = Field(default=False, description="Force cleanup of resources")
    enabled: bool = Field(default=True, description="Whether this rule is enabled")


class ProjectCleanupPolicyConfig(BaseModel):
    """Configuration for project-specific cleanup policy."""

    project_name: str = Field(description="Name of the project")
    default_strategy: CleanupStrategy = Field(
        default=CleanupStrategy.MODERATE, description="Default cleanup strategy for this project",
    )
    rules: dict[ResourceType, CleanupRuleConfig] = Field(
        default_factory=dict, description="Resource-specific cleanup rules",
    )
    enabled: bool = Field(default=True, description="Whether cleanup is enabled for this project")

    @validator("rules", pre=True)
    def validate_rules(self, v):
        """Validate that rules have correct resource types."""
        if isinstance(v, dict):
            for resource_type, rule in v.items():
                if isinstance(rule, dict):
                    rule["resource_type"] = resource_type
        return v


class GlobalCleanupPolicyConfig(BaseModel):
    """Configuration for global cleanup policy."""

    default_strategy: CleanupStrategy = Field(
        default=CleanupStrategy.CONSERVATIVE, description="Default cleanup strategy",
    )
    max_concurrent_cleanups: int = Field(
        default=5, description="Maximum concurrent cleanup operations",
    )
    cleanup_timeout: float = Field(
        default=300.0, description="Timeout for cleanup operations (seconds)",
    )
    enabled: bool = Field(default=True, description="Whether global cleanup is enabled")


class StatusPageConfig(BaseModel):
    """Configuration for status page generation."""

    # Page generation
    auto_refresh_interval: int = Field(
        default=5, description="Auto-refresh interval for status pages (seconds)",
    )
    include_service_details: bool = Field(
        default=True, description="Include detailed service information",
    )
    include_tunnel_details: bool = Field(
        default=True, description="Include detailed tunnel information",
    )
    include_health_metrics: bool = Field(
        default=True, description="Include health metrics and statistics",
    )

    # Styling and customization
    theme: str = Field(default="default", description="Status page theme")
    custom_css: str | None = Field(default=None, description="Custom CSS for status pages")
    custom_js: str | None = Field(default=None, description="Custom JavaScript for status pages")

    # Maintenance mode
    maintenance_mode_enabled: bool = Field(default=False, description="Enable maintenance mode")
    maintenance_message: str = Field(
        default="Service is under maintenance", description="Maintenance mode message",
    )
    maintenance_contact: str | None = Field(
        default=None, description="Contact information for maintenance",
    )


class ProjectRoutingConfig(BaseModel):
    """Configuration for project routing."""

    project_name: str = Field(description="Name of the project")
    domain: str = Field(description="Primary domain for the project")
    base_path: str = Field(default="/", description="Base path for the project")

    # Routing behavior
    enable_health_checks: bool = Field(default=True, description="Enable health checks for routes")
    health_check_interval: float = Field(default=5.0, description="Health check interval (seconds)")
    health_check_timeout: float = Field(default=2.0, description="Health check timeout (seconds)")

    # Fallback configuration
    fallback_enabled: bool = Field(default=True, description="Enable fallback pages")
    maintenance_enabled: bool = Field(default=False, description="Enable maintenance mode")


class KInfraConfig(BaseModel):
    """Main KInfra configuration schema integrating all Phase 5 features."""

    # Application settings
    app_name: str = Field(default="kinfra", description="Application name")
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(default="INFO", description="Logging level")
    environment: str = Field(default="development", description="Environment name")

    # Phase 5 component configurations
    process_governance: ProcessGovernanceConfig = Field(
        default_factory=ProcessGovernanceConfig, description="Process governance configuration",
    )
    tunnel_governance: TunnelGovernanceConfig = Field(
        default_factory=TunnelGovernanceConfig, description="Tunnel governance configuration",
    )
    global_cleanup_policy: GlobalCleanupPolicyConfig = Field(
        default_factory=GlobalCleanupPolicyConfig, description="Global cleanup policy configuration",
    )
    status_pages: StatusPageConfig = Field(
        default_factory=StatusPageConfig, description="Status page configuration",
    )

    # Project-specific configurations
    projects: dict[str, ProjectCleanupPolicyConfig] = Field(
        default_factory=dict, description="Project-specific cleanup policies",
    )
    project_routing: dict[str, ProjectRoutingConfig] = Field(
        default_factory=dict, description="Project-specific routing configurations",
    )

    # Infrastructure settings
    data_dir: Path = Field(default=Path.home() / ".kinfra", description="Data directory for KInfra")
    config_dir: Path = Field(
        default=Path.home() / ".kinfra" / "config", description="Configuration directory",
    )
    cache_dir: Path = Field(
        default=Path.home() / ".kinfra" / "cache", description="Cache directory",
    )

    # Advanced settings
    enable_nats: bool = Field(default=True, description="Enable NATS for distributed coordination")
    nats_url: str = Field(default="nats://localhost:4222", description="NATS server URL")
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")
    metrics_port: int = Field(default=9090, description="Metrics server port")

    @validator("data_dir", "config_dir", "cache_dir", pre=True)
    def resolve_paths(self, v):
        """Resolve paths to absolute paths."""
        if isinstance(v, str):
            return Path(v).expanduser().resolve()
        return v

    @validator("projects", pre=True)
    def validate_projects(self, v):
        """Validate project configurations."""
        if isinstance(v, dict):
            for project_name, config in v.items():
                if isinstance(config, dict):
                    config["project_name"] = project_name
        return v

    @validator("project_routing", pre=True)
    def validate_project_routing(self, v):
        """Validate project routing configurations."""
        if isinstance(v, dict):
            for project_name, config in v.items():
                if isinstance(config, dict):
                    config["project_name"] = project_name
        return v


class KInfraConfigManager:
    """Enhanced configuration manager for KInfra with Phase 5 integration."""

    def __init__(self, config_file: Path | None = None):
        self.config_file = config_file or Path.home() / ".kinfra" / "config" / "kinfra.yaml"
        self._config: KInfraConfig | None = None

    def load(
        self,
        env_prefix: str = "KINFRA_",
        config_file: Path | None = None,
        defaults: dict[str, Any] | None = None,
    ) -> KInfraConfig:
        """Load configuration with hierarchical merging."""
        config_file = config_file or self.config_file

        # Start with defaults
        data = defaults or {}

        # Merge file config
        if config_file and config_file.exists():
            try:
                file_config = KInfraConfig.from_file(config_file)
                data.update(file_config.model_dump())
            except Exception as e:
                logger.warning(f"Failed to load config file {config_file}: {e}")

        # Merge environment variables
        if env_prefix:
            env_data = KInfraConfig.from_env(prefix=env_prefix, _return_dict=True)
            data.update(env_data)

        self._config = KInfraConfig(**data)
        return self._config

    def get_config(self) -> KInfraConfig:
        """Get the current configuration."""
        if self._config is None:
            self.load()
        return self._config

    def save_config(self, config: KInfraConfig, config_file: Path | None = None) -> None:
        """Save configuration to file."""
        config_file = config_file or self.config_file
        config_file.parent.mkdir(parents=True, exist_ok=True)

        with open(config_file, "w") as f:
            import yaml

            yaml.dump(config.model_dump(), f, default_flow_style=False)

    def get_project_config(self, project_name: str) -> ProjectCleanupPolicyConfig | None:
        """Get project-specific cleanup policy."""
        config = self.get_config()
        return config.projects.get(project_name)

    def set_project_config(
        self, project_name: str, project_config: ProjectCleanupPolicyConfig,
    ) -> None:
        """Set project-specific cleanup policy."""
        config = self.get_config()
        config.projects[project_name] = project_config
        self.save_config(config)

    def get_project_routing(self, project_name: str) -> ProjectRoutingConfig | None:
        """Get project-specific routing configuration."""
        config = self.get_config()
        return config.project_routing.get(project_name)

    def set_project_routing(self, project_name: str, routing_config: ProjectRoutingConfig) -> None:
        """Set project-specific routing configuration."""
        config = self.get_config()
        config.project_routing[project_name] = routing_config
        self.save_config(config)


# Default configuration instances
DEFAULT_KINFRA_CONFIG = KInfraConfig()
DEFAULT_PROCESS_GOVERNANCE_CONFIG = ProcessGovernanceConfig()
DEFAULT_TUNNEL_GOVERNANCE_CONFIG = TunnelGovernanceConfig()
DEFAULT_CLEANUP_POLICY_CONFIG = GlobalCleanupPolicyConfig()
DEFAULT_STATUS_PAGE_CONFIG = StatusPageConfig()


def create_default_project_config(project_name: str) -> ProjectCleanupPolicyConfig:
    """Create a default project configuration."""
    return ProjectCleanupPolicyConfig(
        project_name=project_name,
        default_strategy=CleanupStrategy.MODERATE,
        rules={
            ResourceType.PROCESS: CleanupRuleConfig(
                resource_type=ResourceType.PROCESS,
                strategy=CleanupStrategy.MODERATE,
                patterns=[f"{project_name}-*", f"*{project_name}*"],
                max_age=3600.0,
                force_cleanup=False,
                enabled=True,
            ),
            ResourceType.TUNNEL: CleanupRuleConfig(
                resource_type=ResourceType.TUNNEL,
                strategy=CleanupStrategy.CONSERVATIVE,
                patterns=[f"{project_name}-*"],
                max_age=7200.0,
                force_cleanup=False,
                enabled=True,
            ),
            ResourceType.PORT: CleanupRuleConfig(
                resource_type=ResourceType.PORT,
                strategy=CleanupStrategy.AGGRESSIVE,
                patterns=[f"{project_name}-*"],
                max_age=1800.0,
                force_cleanup=True,
                enabled=True,
            ),
        },
    )


def create_default_routing_config(project_name: str, domain: str) -> ProjectRoutingConfig:
    """Create a default project routing configuration."""
    return ProjectRoutingConfig(
        project_name=project_name,
        domain=domain,
        base_path="/",
        enable_health_checks=True,
        health_check_interval=5.0,
        health_check_timeout=2.0,
        fallback_enabled=True,
        maintenance_enabled=False,
    )


__all__ = [
    "DEFAULT_CLEANUP_POLICY_CONFIG",
    "DEFAULT_KINFRA_CONFIG",
    "DEFAULT_PROCESS_GOVERNANCE_CONFIG",
    "DEFAULT_STATUS_PAGE_CONFIG",
    "DEFAULT_TUNNEL_GOVERNANCE_CONFIG",
    "CleanupRuleConfig",
    "CleanupStrategy",
    "GlobalCleanupPolicyConfig",
    "KInfraConfig",
    "KInfraConfigManager",
    "ProcessGovernanceConfig",
    "ProjectCleanupPolicyConfig",
    "ProjectRoutingConfig",
    "ResourceType",
    "StatusPageConfig",
    "TunnelCredentialScope",
    "TunnelGovernanceConfig",
    "TunnelLifecyclePolicy",
    "create_default_project_config",
    "create_default_routing_config",
]
