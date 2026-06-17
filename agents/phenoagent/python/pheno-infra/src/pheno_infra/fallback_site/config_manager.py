"""
Fallback Configuration Manager - API/CLI for configuring fallback states and maintenance pages

Provides comprehensive configuration management for:
- Fallback page customization
- Maintenance mode configuration
- Project-specific fallback states
- Template management and customization
- CLI commands for configuration
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class FallbackPageConfig:
    """
    Configuration for a fallback page.
    """

    page_type: str
    """
    Type of page (loading, error, maintenance, custom).
    """

    service_name: str
    """
    Name of the service.
    """

    title: str
    """
    Page title.
    """

    message: str
    """
    Main message to display.
    """

    refresh_interval: int = 5
    """
    Auto-refresh interval in seconds.
    """

    custom_css: str | None = None
    """
    Custom CSS for the page.
    """

    custom_js: str | None = None
    """
    Custom JavaScript for the page.
    """

    template_vars: dict[str, Any] = field(default_factory=dict)
    """
    Additional template variables.
    """

    is_active: bool = True
    """
    Whether this page configuration is active.
    """


@dataclass
class MaintenanceConfig:
    """
    Configuration for maintenance mode.
    """

    enabled: bool = False
    """
    Whether maintenance mode is enabled.
    """

    message: str = "Service is under maintenance"
    """
    Maintenance message.
    """

    estimated_duration: str = "30 minutes"
    """
    Estimated duration of maintenance.
    """

    contact_info: str | None = None
    """
    Contact information for maintenance.
    """

    custom_page: str | None = None
    """
    Custom maintenance page HTML.
    """

    allowed_ips: list[str] = field(default_factory=list)
    """
    IP addresses allowed during maintenance.
    """

    bypass_token: str | None = None
    """
    Token to bypass maintenance mode.
    """


@dataclass
class ProjectFallbackConfig:
    """
    Fallback configuration for a project.
    """

    project_name: str
    """
    Name of the project.
    """

    fallback_pages: dict[str, FallbackPageConfig] = field(default_factory=dict)
    """
    Fallback page configurations by type.
    """

    maintenance_config: MaintenanceConfig = field(default_factory=MaintenanceConfig)
    """
    Maintenance mode configuration.
    """

    default_page_type: str = "loading"
    """
    Default page type to show.
    """

    custom_templates_dir: Path | None = None
    """
    Directory containing custom templates.
    """

    global_settings: dict[str, Any] = field(default_factory=dict)
    """
    Global settings for the project.
    """


class FallbackConfigManager:
    """
    Manages fallback configuration and templates.

    Features:
    - Fallback page customization
    - Maintenance mode configuration
    - Project-specific fallback states
    - Template management and customization
    - Configuration import/export
    """

    def __init__(self, config_dir: Path | None = None):
        """Initialize fallback configuration manager.

        Args:
            config_dir: Directory to store configuration files
        """
        self.config_dir = config_dir or Path.home() / ".kinfra" / "fallback"
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self._project_configs: dict[str, ProjectFallbackConfig] = {}
        self._global_templates_dir = Path(__file__).parent / "templates"

        logger.info(f"FallbackConfigManager initialized (config_dir: {self.config_dir})")

    def create_project_config(
        self,
        project_name: str,
        default_page_type: str = "loading",
    ) -> ProjectFallbackConfig:
        """
        Create a default fallback configuration for a project.

        Args:
            project_name: Name of the project
            default_page_type: Default page type

        Returns:
            Project fallback configuration
        """
        # Create default fallback pages
        fallback_pages = {
            "loading": FallbackPageConfig(
                page_type="loading",
                service_name=project_name,
                title=f"{project_name} - Starting Up",
                message=f"{project_name} is currently starting up...",
                refresh_interval=5,
            ),
            "error": FallbackPageConfig(
                page_type="error",
                service_name=project_name,
                title=f"{project_name} - Service Unavailable",
                message=f"{project_name} is temporarily unavailable. Please try again later.",
                refresh_interval=10,
            ),
            "maintenance": FallbackPageConfig(
                page_type="maintenance",
                service_name=project_name,
                title=f"{project_name} - Under Maintenance",
                message=f"{project_name} is currently under maintenance.",
                refresh_interval=30,
            ),
        }

        config = ProjectFallbackConfig(
            project_name=project_name,
            fallback_pages=fallback_pages,
            maintenance_config=MaintenanceConfig(),
            default_page_type=default_page_type,
        )

        self._project_configs[project_name] = config
        logger.info(f"Created fallback config for project '{project_name}'")

        return config

    def get_project_config(
        self,
        project_name: str,
    ) -> ProjectFallbackConfig | None:
        """
        Get fallback configuration for a project.

        Args:
            project_name: Name of the project

        Returns:
            Project fallback configuration or None
        """
        return self._project_configs.get(project_name)

    def get_or_create_project_config(
        self,
        project_name: str,
    ) -> ProjectFallbackConfig:
        """
        Get or create fallback configuration for a project.

        Args:
            project_name: Name of the project

        Returns:
            Project fallback configuration
        """
        config = self.get_project_config(project_name)
        if not config:
            config = self.create_project_config(project_name)

        return config

    def update_fallback_page(
        self,
        project_name: str,
        page_type: str,
        config: FallbackPageConfig,
    ) -> None:
        """
        Update a fallback page configuration.

        Args:
            project_name: Name of the project
            page_type: Type of page to update
            config: Fallback page configuration
        """
        project_config = self.get_or_create_project_config(project_name)
        project_config.fallback_pages[page_type] = config

        logger.info(f"Updated fallback page '{page_type}' for project '{project_name}'")

    def get_fallback_page(
        self,
        project_name: str,
        page_type: str,
    ) -> FallbackPageConfig | None:
        """
        Get a fallback page configuration.

        Args:
            project_name: Name of the project
            page_type: Type of page

        Returns:
            Fallback page configuration or None
        """
        project_config = self.get_project_config(project_name)
        if not project_config:
            return None

        return project_config.fallback_pages.get(page_type)

    def update_maintenance_config(
        self,
        project_name: str,
        maintenance_config: MaintenanceConfig,
    ) -> None:
        """
        Update maintenance configuration for a project.

        Args:
            project_name: Name of the project
            maintenance_config: Maintenance configuration
        """
        project_config = self.get_or_create_project_config(project_name)
        project_config.maintenance_config = maintenance_config

        logger.info(f"Updated maintenance config for project '{project_name}'")

    def enable_maintenance(
        self,
        project_name: str,
        message: str | None = None,
        estimated_duration: str | None = None,
        contact_info: str | None = None,
    ) -> None:
        """
        Enable maintenance mode for a project.

        Args:
            project_name: Name of the project
            message: Maintenance message
            estimated_duration: Estimated duration
            contact_info: Contact information
        """
        project_config = self.get_or_create_project_config(project_name)

        project_config.maintenance_config.enabled = True
        if message:
            project_config.maintenance_config.message = message
        if estimated_duration:
            project_config.maintenance_config.estimated_duration = estimated_duration
        if contact_info:
            project_config.maintenance_config.contact_info = contact_info

        logger.info(f"Enabled maintenance mode for project '{project_name}'")

    def disable_maintenance(
        self,
        project_name: str,
    ) -> None:
        """
        Disable maintenance mode for a project.

        Args:
            project_name: Name of the project
        """
        project_config = self.get_project_config(project_name)
        if not project_config:
            return

        project_config.maintenance_config.enabled = False
        logger.info(f"Disabled maintenance mode for project '{project_name}'")

    def set_custom_template(
        self,
        project_name: str,
        page_type: str,
        template_content: str,
    ) -> None:
        """
        Set a custom template for a fallback page.

        Args:
            project_name: Name of the project
            page_type: Type of page
            template_content: Custom template content
        """
        project_config = self.get_or_create_project_config(project_name)

        # Create custom templates directory
        custom_dir = self.config_dir / project_name / "templates"
        custom_dir.mkdir(parents=True, exist_ok=True)

        # Write template file
        template_file = custom_dir / f"{page_type}.html"
        template_file.write_text(template_content)

        project_config.custom_templates_dir = custom_dir
        logger.info(f"Set custom template for '{page_type}' in project '{project_name}'")

    def get_custom_template(
        self,
        project_name: str,
        page_type: str,
    ) -> str | None:
        """
        Get custom template content for a fallback page.

        Args:
            project_name: Name of the project
            page_type: Type of page

        Returns:
            Custom template content or None
        """
        project_config = self.get_project_config(project_name)
        if not project_config or not project_config.custom_templates_dir:
            return None

        template_file = project_config.custom_templates_dir / f"{page_type}.html"
        if template_file.exists():
            return template_file.read_text()

        return None

    def list_project_pages(
        self,
        project_name: str,
    ) -> list[str]:
        """
        List all fallback page types for a project.

        Args:
            project_name: Name of the project

        Returns:
            List of page types
        """
        project_config = self.get_project_config(project_name)
        if not project_config:
            return []

        return list(project_config.fallback_pages.keys())

    def export_project_config(
        self,
        project_name: str,
        format: str = "json",
    ) -> str:
        """
        Export fallback configuration for a project.

        Args:
            project_name: Name of the project
            format: Export format (json, yaml)

        Returns:
            Exported configuration
        """
        project_config = self.get_project_config(project_name)
        if not project_config:
            return ""

        # Convert to serializable format
        config_data = {
            "project_name": project_config.project_name,
            "default_page_type": project_config.default_page_type,
            "fallback_pages": {
                page_type: {
                    "page_type": page.page_type,
                    "service_name": page.service_name,
                    "title": page.title,
                    "message": page.message,
                    "refresh_interval": page.refresh_interval,
                    "custom_css": page.custom_css,
                    "custom_js": page.custom_js,
                    "template_vars": page.template_vars,
                    "is_active": page.is_active,
                }
                for page_type, page in project_config.fallback_pages.items()
            },
            "maintenance_config": {
                "enabled": project_config.maintenance_config.enabled,
                "message": project_config.maintenance_config.message,
                "estimated_duration": project_config.maintenance_config.estimated_duration,
                "contact_info": project_config.maintenance_config.contact_info,
                "custom_page": project_config.maintenance_config.custom_page,
                "allowed_ips": project_config.maintenance_config.allowed_ips,
                "bypass_token": project_config.maintenance_config.bypass_token,
            },
            "global_settings": project_config.global_settings,
        }

        if format == "json":
            return json.dumps(config_data, indent=2)
        if format == "yaml":
            import yaml

            return yaml.dump(config_data, default_flow_style=False)
        raise ValueError(f"Unsupported format: {format}")

    def import_project_config(
        self,
        project_name: str,
        config_data: str,
        format: str = "json",
    ) -> None:
        """
        Import fallback configuration for a project.

        Args:
            project_name: Name of the project
            config_data: Configuration data
            format: Import format (json, yaml)
        """
        if format == "json":
            data = json.loads(config_data)
        elif format == "yaml":
            import yaml

            data = yaml.safe_load(config_data)
        else:
            raise ValueError(f"Unsupported format: {format}")

        # Create project config
        project_config = ProjectFallbackConfig(
            project_name=data["project_name"],
            default_page_type=data.get("default_page_type", "loading"),
            global_settings=data.get("global_settings", {}),
        )

        # Import fallback pages
        for page_type, page_data in data.get("fallback_pages", {}).items():
            page_config = FallbackPageConfig(
                page_type=page_data["page_type"],
                service_name=page_data["service_name"],
                title=page_data["title"],
                message=page_data["message"],
                refresh_interval=page_data.get("refresh_interval", 5),
                custom_css=page_data.get("custom_css"),
                custom_js=page_data.get("custom_js"),
                template_vars=page_data.get("template_vars", {}),
                is_active=page_data.get("is_active", True),
            )
            project_config.fallback_pages[page_type] = page_config

        # Import maintenance config
        maintenance_data = data.get("maintenance_config", {})
        project_config.maintenance_config = MaintenanceConfig(
            enabled=maintenance_data.get("enabled", False),
            message=maintenance_data.get("message", "Service is under maintenance"),
            estimated_duration=maintenance_data.get("estimated_duration", "30 minutes"),
            contact_info=maintenance_data.get("contact_info"),
            custom_page=maintenance_data.get("custom_page"),
            allowed_ips=maintenance_data.get("allowed_ips", []),
            bypass_token=maintenance_data.get("bypass_token"),
        )

        self._project_configs[project_name] = project_config
        logger.info(f"Imported fallback config for project '{project_name}'")

    def save_project_config(
        self,
        project_name: str,
    ) -> None:
        """
        Save project configuration to disk.

        Args:
            project_name: Name of the project
        """
        project_config = self.get_project_config(project_name)
        if not project_config:
            return

        config_file = self.config_dir / f"{project_name}.json"
        config_data = self.export_project_config(project_name, "json")
        config_file.write_text(config_data)

        logger.info(f"Saved fallback config for project '{project_name}' to {config_file}")

    def load_project_config(
        self,
        project_name: str,
    ) -> bool:
        """
        Load project configuration from disk.

        Args:
            project_name: Name of the project

        Returns:
            True if config was loaded successfully
        """
        config_file = self.config_dir / f"{project_name}.json"
        if not config_file.exists():
            return False

        try:
            config_data = config_file.read_text()
            self.import_project_config(project_name, config_data, "json")
            logger.info(f"Loaded fallback config for project '{project_name}' from {config_file}")
            return True
        except Exception as e:
            logger.exception(f"Failed to load fallback config for project '{project_name}': {e}")
            return False

    def list_projects(self) -> list[str]:
        """
        List all configured projects.

        Returns:
            List of project names
        """
        return list(self._project_configs.keys())

    def get_global_templates_dir(self) -> Path:
        """
        Get the global templates directory.

        Returns:
            Path to global templates directory
        """
        return self._global_templates_dir
