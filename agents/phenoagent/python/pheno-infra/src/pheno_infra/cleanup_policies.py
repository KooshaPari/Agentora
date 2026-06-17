"""
Cleanup Policies - Configurable cleanup strategies

Provides configurable cleanup policies for:
- Process cleanup strategies (aggressive, conservative, moderate)
- Resource cleanup policies
- Project-specific cleanup rules
- Cleanup policy configuration files
- Integration with existing cleanup systems
"""

import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class CleanupStrategy(Enum):
    """
    Cleanup strategy for different resource types.
    """

    CONSERVATIVE = "conservative"
    """
    Only clean up resources that are clearly related to the project/service.
    """

    MODERATE = "moderate"
    """
    Clean up related resources and shared resources.
    """

    AGGRESSIVE = "aggressive"
    """
    Clean up all potentially related resources.
    """


class ResourceType(Enum):
    """
    Type of resource for cleanup policies.
    """

    PROCESS = "process"
    TUNNEL = "tunnel"
    PORT = "port"
    FILE = "file"
    NETWORK = "network"
    CACHE = "cache"
    LOG = "log"


@dataclass
class CleanupRule:
    """
    A cleanup rule for a specific resource type.
    """

    resource_type: ResourceType
    """
    Type of resource to clean up.
    """

    strategy: CleanupStrategy
    """
    Cleanup strategy to use.
    """

    patterns: list[str] = field(default_factory=list)
    """
    Patterns to match for cleanup.
    """

    exclude_patterns: list[str] = field(default_factory=list)
    """
    Patterns to exclude from cleanup.
    """

    max_age: float | None = None
    """
    Maximum age for resources before cleanup (in seconds).
    """

    force_cleanup: bool = False
    """
    Whether to force cleanup even if conservative strategy.
    """

    enabled: bool = True
    """
    Whether this rule is enabled.
    """


@dataclass
class ProjectCleanupPolicy:
    """
    Cleanup policy for a specific project.
    """

    project_name: str
    """
    Name of the project.
    """

    rules: dict[ResourceType, CleanupRule] = field(default_factory=dict)
    """
    Cleanup rules by resource type.
    """

    global_strategy: CleanupStrategy = CleanupStrategy.MODERATE
    """
    Global cleanup strategy for the project.
    """

    enabled: bool = True
    """
    Whether cleanup is enabled for this project.
    """

    created_at: float = field(default_factory=time.time)
    """
    Timestamp when policy was created.
    """

    updated_at: float = field(default_factory=time.time)
    """
    Timestamp when policy was last updated.
    """


@dataclass
class GlobalCleanupPolicy:
    """
    Global cleanup policy configuration.
    """

    default_strategy: CleanupStrategy = CleanupStrategy.MODERATE
    """
    Default cleanup strategy.
    """

    project_policies: dict[str, ProjectCleanupPolicy] = field(default_factory=dict)
    """
    Project-specific cleanup policies.
    """

    global_rules: dict[ResourceType, CleanupRule] = field(default_factory=dict)
    """
    Global cleanup rules by resource type.
    """

    cleanup_interval: float = 300.0
    """
    Cleanup interval in seconds.
    """

    max_cleanup_age: float = 3600.0
    """
    Maximum age for resources before cleanup in seconds.
    """

    enable_auto_cleanup: bool = True
    """
    Whether to enable automatic cleanup.
    """

    created_at: float = field(default_factory=time.time)
    """
    Timestamp when policy was created.
    """

    updated_at: float = field(default_factory=time.time)
    """
    Timestamp when policy was last updated.
    """


class CleanupPolicyManager:
    """
    Manages cleanup policies and strategies.

    Features:
    - Project-specific cleanup policies
    - Configurable cleanup strategies
    - Resource-specific cleanup rules
    - Policy configuration files
    - Integration with cleanup systems
    """

    def __init__(self, config_dir: Path | None = None):
        """Initialize cleanup policy manager.

        Args:
            config_dir: Configuration directory
        """
        self.config_dir = config_dir or Path.home() / ".kinfra" / "cleanup"
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self._global_policy = GlobalCleanupPolicy()
        self._load_policies()

        logger.info("CleanupPolicyManager initialized")

    def create_default_policy(
        self,
        project_name: str,
        strategy: CleanupStrategy = CleanupStrategy.MODERATE,
    ) -> ProjectCleanupPolicy:
        """
        Create a default cleanup policy for a project.

        Args:
            project_name: Name of the project
            strategy: Cleanup strategy to use

        Returns:
            Project cleanup policy
        """
        # Create default rules for each resource type
        rules = {}

        # Process cleanup rule
        rules[ResourceType.PROCESS] = CleanupRule(
            resource_type=ResourceType.PROCESS,
            strategy=strategy,
            patterns=[f"{project_name}-*", f"*{project_name}*"],
            exclude_patterns=["system", "kernel"],
            max_age=3600.0,  # 1 hour
            force_cleanup=False,
        )

        # Tunnel cleanup rule
        rules[ResourceType.TUNNEL] = CleanupRule(
            resource_type=ResourceType.TUNNEL,
            strategy=strategy,
            patterns=[f"{project_name}-*", f"*{project_name}*"],
            exclude_patterns=[],
            max_age=1800.0,  # 30 minutes
            force_cleanup=True,
        )

        # Port cleanup rule
        rules[ResourceType.PORT] = CleanupRule(
            resource_type=ResourceType.PORT,
            strategy=strategy,
            patterns=[f"{project_name}-*", f"*{project_name}*"],
            exclude_patterns=["system"],
            max_age=7200.0,  # 2 hours
            force_cleanup=False,
        )

        # File cleanup rule
        rules[ResourceType.FILE] = CleanupRule(
            resource_type=ResourceType.FILE,
            strategy=strategy,
            patterns=[f"*{project_name}*", f"kinfra_{project_name}_*"],
            exclude_patterns=["config", "data"],
            max_age=86400.0,  # 24 hours
            force_cleanup=False,
        )

        # Cache cleanup rule
        rules[ResourceType.CACHE] = CleanupRule(
            resource_type=ResourceType.CACHE,
            strategy=strategy,
            patterns=[f"*{project_name}*", f"cache_{project_name}_*"],
            exclude_patterns=[],
            max_age=3600.0,  # 1 hour
            force_cleanup=True,
        )

        # Log cleanup rule
        rules[ResourceType.LOG] = CleanupRule(
            resource_type=ResourceType.LOG,
            strategy=strategy,
            patterns=[f"*{project_name}*", f"log_{project_name}_*"],
            exclude_patterns=[],
            max_age=604800.0,  # 7 days
            force_cleanup=False,
        )

        policy = ProjectCleanupPolicy(
            project_name=project_name,
            rules=rules,
            global_strategy=strategy,
        )

        self._global_policy.project_policies[project_name] = policy
        self._save_policies()

        logger.info(f"Created default cleanup policy for project '{project_name}'")
        return policy

    def get_project_policy(
        self,
        project_name: str,
    ) -> ProjectCleanupPolicy | None:
        """
        Get cleanup policy for a project.

        Args:
            project_name: Name of the project

        Returns:
            Project cleanup policy or None
        """
        return self._global_policy.project_policies.get(project_name)

    def get_or_create_project_policy(
        self,
        project_name: str,
    ) -> ProjectCleanupPolicy:
        """
        Get or create cleanup policy for a project.

        Args:
            project_name: Name of the project

        Returns:
            Project cleanup policy
        """
        policy = self.get_project_policy(project_name)
        if not policy:
            policy = self.create_default_policy(project_name)

        return policy

    def update_project_policy(
        self,
        project_name: str,
        policy: ProjectCleanupPolicy,
    ) -> None:
        """
        Update cleanup policy for a project.

        Args:
            project_name: Name of the project
            policy: Updated policy
        """
        policy.updated_at = time.time()
        self._global_policy.project_policies[project_name] = policy
        self._save_policies()

        logger.info(f"Updated cleanup policy for project '{project_name}'")

    def update_project_rule(
        self,
        project_name: str,
        resource_type: ResourceType,
        rule: CleanupRule,
    ) -> None:
        """
        Update a specific cleanup rule for a project.

        Args:
            project_name: Name of the project
            resource_type: Type of resource
            rule: Updated rule
        """
        policy = self.get_or_create_project_policy(project_name)
        policy.rules[resource_type] = rule
        policy.updated_at = time.time()

        self._global_policy.project_policies[project_name] = policy
        self._save_policies()

        logger.info(f"Updated {resource_type.value} cleanup rule for project '{project_name}'")

    def get_cleanup_strategy(
        self,
        project_name: str,
        resource_type: ResourceType,
    ) -> CleanupStrategy:
        """
        Get cleanup strategy for a project and resource type.

        Args:
            project_name: Name of the project
            resource_type: Type of resource

        Returns:
            Cleanup strategy
        """
        policy = self.get_project_policy(project_name)
        if not policy:
            return self._global_policy.default_strategy

        rule = policy.rules.get(resource_type)
        if not rule:
            return policy.global_strategy

        return rule.strategy

    def get_cleanup_patterns(
        self,
        project_name: str,
        resource_type: ResourceType,
    ) -> list[str]:
        """
        Get cleanup patterns for a project and resource type.

        Args:
            project_name: Name of the project
            resource_type: Type of resource

        Returns:
            List of patterns
        """
        policy = self.get_project_policy(project_name)
        if not policy:
            return []

        rule = policy.rules.get(resource_type)
        if not rule:
            return []

        return rule.patterns

    def get_exclude_patterns(
        self,
        project_name: str,
        resource_type: ResourceType,
    ) -> list[str]:
        """
        Get exclude patterns for a project and resource type.

        Args:
            project_name: Name of the project
            resource_type: Type of resource

        Returns:
            List of exclude patterns
        """
        policy = self.get_project_policy(project_name)
        if not policy:
            return []

        rule = policy.rules.get(resource_type)
        if not rule:
            return []

        return rule.exclude_patterns

    def get_max_age(
        self,
        project_name: str,
        resource_type: ResourceType,
    ) -> float | None:
        """
        Get maximum age for a project and resource type.

        Args:
            project_name: Name of the project
            resource_type: Type of resource

        Returns:
            Maximum age in seconds or None
        """
        policy = self.get_project_policy(project_name)
        if not policy:
            return self._global_policy.max_cleanup_age

        rule = policy.rules.get(resource_type)
        if not rule:
            return self._global_policy.max_cleanup_age

        return rule.max_age

    def is_force_cleanup(
        self,
        project_name: str,
        resource_type: ResourceType,
    ) -> bool:
        """
        Check if force cleanup is enabled for a project and resource type.

        Args:
            project_name: Name of the project
            resource_type: Type of resource

        Returns:
            True if force cleanup is enabled
        """
        policy = self.get_project_policy(project_name)
        if not policy:
            return False

        rule = policy.rules.get(resource_type)
        if not rule:
            return False

        return rule.force_cleanup

    def is_cleanup_enabled(
        self,
        project_name: str,
        resource_type: ResourceType,
    ) -> bool:
        """
        Check if cleanup is enabled for a project and resource type.

        Args:
            project_name: Name of the project
            resource_type: Type of resource

        Returns:
            True if cleanup is enabled
        """
        policy = self.get_project_policy(project_name)
        if not policy:
            return self._global_policy.enable_auto_cleanup

        if not policy.enabled:
            return False

        rule = policy.rules.get(resource_type)
        if not rule:
            return True

        return rule.enabled

    def list_projects(self) -> list[str]:
        """
        List all projects with cleanup policies.

        Returns:
            List of project names
        """
        return list(self._global_policy.project_policies.keys())

    def export_policy(
        self,
        project_name: str,
        format: str = "json",
    ) -> str:
        """
        Export cleanup policy for a project.

        Args:
            project_name: Name of the project
            format: Export format (json, yaml)

        Returns:
            Exported policy
        """
        policy = self.get_project_policy(project_name)
        if not policy:
            return ""

        # Convert to serializable format
        policy_data = {
            "project_name": policy.project_name,
            "global_strategy": policy.global_strategy.value,
            "enabled": policy.enabled,
            "created_at": policy.created_at,
            "updated_at": policy.updated_at,
            "rules": {
                resource_type.value: {
                    "strategy": rule.strategy.value,
                    "patterns": rule.patterns,
                    "exclude_patterns": rule.exclude_patterns,
                    "max_age": rule.max_age,
                    "force_cleanup": rule.force_cleanup,
                    "enabled": rule.enabled,
                }
                for resource_type, rule in policy.rules.items()
            },
        }

        if format == "json":
            return json.dumps(policy_data, indent=2)
        if format == "yaml":
            import yaml

            return yaml.dump(policy_data, default_flow_style=False)
        raise ValueError(f"Unsupported format: {format}")

    def import_policy(
        self,
        project_name: str,
        policy_data: str,
        format: str = "json",
    ) -> None:
        """
        Import cleanup policy for a project.

        Args:
            project_name: Name of the project
            policy_data: Policy data
            format: Import format (json, yaml)
        """
        if format == "json":
            data = json.loads(policy_data)
        elif format == "yaml":
            import yaml

            data = yaml.safe_load(policy_data)
        else:
            raise ValueError(f"Unsupported format: {format}")

        # Create policy from imported data
        policy = ProjectCleanupPolicy(
            project_name=data["project_name"],
            global_strategy=CleanupStrategy(data["global_strategy"]),
            enabled=data.get("enabled", True),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
        )

        # Import rules
        for resource_type_str, rule_data in data.get("rules", {}).items():
            resource_type = ResourceType(resource_type_str)
            rule = CleanupRule(
                resource_type=resource_type,
                strategy=CleanupStrategy(rule_data["strategy"]),
                patterns=rule_data.get("patterns", []),
                exclude_patterns=rule_data.get("exclude_patterns", []),
                max_age=rule_data.get("max_age"),
                force_cleanup=rule_data.get("force_cleanup", False),
                enabled=rule_data.get("enabled", True),
            )
            policy.rules[resource_type] = rule

        self._global_policy.project_policies[project_name] = policy
        self._save_policies()

        logger.info(f"Imported cleanup policy for project '{project_name}'")

    def get_global_policy(self) -> GlobalCleanupPolicy:
        """
        Get the global cleanup policy.

        Returns:
            Global cleanup policy
        """
        return self._global_policy

    def update_global_policy(
        self,
        policy: GlobalCleanupPolicy,
    ) -> None:
        """
        Update the global cleanup policy.

        Args:
            policy: Updated global policy
        """
        policy.updated_at = time.time()
        self._global_policy = policy
        self._save_policies()

        logger.info("Updated global cleanup policy")

    # ========== Private helper methods ==========

    def _load_policies(self) -> None:
        """
        Load policies from disk.
        """
        policies_file = self.config_dir / "policies.json"
        if not policies_file.exists():
            return

        try:
            with open(policies_file) as f:
                data = json.load(f)

            # Load global policy
            global_data = data.get("global", {})
            self._global_policy = GlobalCleanupPolicy(
                default_strategy=CleanupStrategy(global_data.get("default_strategy", "moderate")),
                cleanup_interval=global_data.get("cleanup_interval", 300.0),
                max_cleanup_age=global_data.get("max_cleanup_age", 3600.0),
                enable_auto_cleanup=global_data.get("enable_auto_cleanup", True),
                created_at=global_data.get("created_at", time.time()),
                updated_at=global_data.get("updated_at", time.time()),
            )

            # Load global rules
            for resource_type_str, rule_data in global_data.get("global_rules", {}).items():
                resource_type = ResourceType(resource_type_str)
                rule = CleanupRule(
                    resource_type=resource_type,
                    strategy=CleanupStrategy(rule_data["strategy"]),
                    patterns=rule_data.get("patterns", []),
                    exclude_patterns=rule_data.get("exclude_patterns", []),
                    max_age=rule_data.get("max_age"),
                    force_cleanup=rule_data.get("force_cleanup", False),
                    enabled=rule_data.get("enabled", True),
                )
                self._global_policy.global_rules[resource_type] = rule

            # Load project policies
            for project_name, project_data in data.get("projects", {}).items():
                policy = ProjectCleanupPolicy(
                    project_name=project_name,
                    global_strategy=CleanupStrategy(project_data["global_strategy"]),
                    enabled=project_data.get("enabled", True),
                    created_at=project_data.get("created_at", time.time()),
                    updated_at=project_data.get("updated_at", time.time()),
                )

                # Load project rules
                for resource_type_str, rule_data in project_data.get("rules", {}).items():
                    resource_type = ResourceType(resource_type_str)
                    rule = CleanupRule(
                        resource_type=resource_type,
                        strategy=CleanupStrategy(rule_data["strategy"]),
                        patterns=rule_data.get("patterns", []),
                        exclude_patterns=rule_data.get("exclude_patterns", []),
                        max_age=rule_data.get("max_age"),
                        force_cleanup=rule_data.get("force_cleanup", False),
                        enabled=rule_data.get("enabled", True),
                    )
                    policy.rules[resource_type] = rule

                self._global_policy.project_policies[project_name] = policy

            logger.info(
                f"Loaded cleanup policies for {len(self._global_policy.project_policies)} projects",
            )

        except Exception as e:
            logger.exception(f"Failed to load cleanup policies: {e}")

    def _save_policies(self) -> None:
        """
        Save policies to disk.
        """
        policies_file = self.config_dir / "policies.json"

        try:
            data = {
                "global": {
                    "default_strategy": self._global_policy.default_strategy.value,
                    "cleanup_interval": self._global_policy.cleanup_interval,
                    "max_cleanup_age": self._global_policy.max_cleanup_age,
                    "enable_auto_cleanup": self._global_policy.enable_auto_cleanup,
                    "created_at": self._global_policy.created_at,
                    "updated_at": self._global_policy.updated_at,
                    "global_rules": {
                        resource_type.value: {
                            "strategy": rule.strategy.value,
                            "patterns": rule.patterns,
                            "exclude_patterns": rule.exclude_patterns,
                            "max_age": rule.max_age,
                            "force_cleanup": rule.force_cleanup,
                            "enabled": rule.enabled,
                        }
                        for resource_type, rule in self._global_policy.global_rules.items()
                    },
                },
                "projects": {
                    project_name: {
                        "global_strategy": policy.global_strategy.value,
                        "enabled": policy.enabled,
                        "created_at": policy.created_at,
                        "updated_at": policy.updated_at,
                        "rules": {
                            resource_type.value: {
                                "strategy": rule.strategy.value,
                                "patterns": rule.patterns,
                                "exclude_patterns": rule.exclude_patterns,
                                "max_age": rule.max_age,
                                "force_cleanup": rule.force_cleanup,
                                "enabled": rule.enabled,
                            }
                            for resource_type, rule in policy.rules.items()
                        },
                    }
                    for project_name, policy in self._global_policy.project_policies.items()
                },
            }

            with open(policies_file, "w") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.exception(f"Failed to save cleanup policies: {e}")
