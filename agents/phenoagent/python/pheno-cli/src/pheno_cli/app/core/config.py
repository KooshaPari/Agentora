"""
Configuration management for Pheno-CLI.
"""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, validator

# Use centralized config from pheno.config.core
from pheno.config.core import Config

from ..utils.paths import get_user_config_dir


class UIConfig(BaseModel):
    """
    UI-related configuration.
    """

    theme: str = "dark"
    enable_animations: bool = True
    show_dashboard_by_default: bool = False
    use_rich_formatting: bool = True


class TemplateConfig(BaseModel):
    """
    Template-related configuration.
    """

    default: str = "api-gateway"
    custom_path: Path | None = None
    sources: dict[str, str] = Field(default_factory=dict)


class IntegrationConfig(BaseModel):
    """
    External integration configuration.
    """

    github_token_env: str = "GITHUB_TOKEN"
    pypi_token_env: str = "PYPI_TOKEN"
    codecov_token_env: str = "CODECOV_TOKEN"


class DevConfig(BaseModel):
    """
    Development-related configuration.
    """

    default_python_version: str = "3.10"
    auto_setup_git: bool = True
    auto_install_hooks: bool = True
    prefer_venv: bool = True


class BuildConfig(BaseModel):
    """
    Build-related configuration.
    """

    default_targets: list[str] = Field(default_factory=lambda: ["wheel"])
    include_docs: bool = True
    parallel_builds: bool = True


class WorkspaceConfig(BaseModel):
    """
    Workspace-related configuration.
    """

    path: Path | None = None
    auto_discover: bool = True
    project_patterns: list[str] = Field(default_factory=lambda: ["*-kit", "*-service", "*-app"])


class ContextConfig(BaseModel):
    """
    Configuration for a specific context (atoms, zen, byteport, etc.).
    """

    name: str
    description: str
    default_template: str = "api-gateway"
    workspace_path: Path | None = None
    project_patterns: list[str] = Field(default_factory=list)
    commands: dict[str, Any] = Field(default_factory=dict)
    integrations: dict[str, Any] = Field(default_factory=dict)
    deployment_targets: list[str] = Field(default_factory=list)
    auth: dict[str, Any] = Field(default_factory=dict)
    database: dict[str, Any] = Field(default_factory=dict)

    @validator("workspace_path", pre=True)
    def expand_workspace_path(self, v):
        """
        Expand user paths in workspace configuration.
        """
        if v and isinstance(v, (str, Path)):
            return Path(v).expanduser()
        return v


class ContextSystemConfig(BaseModel):
    """
    Configuration for the context system.
    """

    default_context: str = "pheno"
    auto_detect_context: bool = True
    current_context: str | None = None
    contexts: dict[str, ContextConfig] = Field(default_factory=dict)

    def get_context(self, name: str) -> ContextConfig | None:
        """
        Get a specific context configuration.
        """
        return self.contexts.get(name)

    def add_context(self, name: str, config: ContextConfig) -> None:
        """
        Add or update a context configuration.
        """
        self.contexts[name] = config

    def list_contexts(self) -> list[str]:
        """
        List all available context names.
        """
        return list(self.contexts.keys())


class PhenoConfig(BaseModel):
    """
    Main configuration model for Pheno-CLI.
    """

    # General settings
    default_author: str = "Koosha Pari <kooshapari@gmail.com>"
    default_license: str = "MIT"
    workspace_path: Path | None = None

    # Sub-configurations
    ui: UIConfig = Field(default_factory=UIConfig)
    templates: TemplateConfig = Field(default_factory=TemplateConfig)
    integrations: IntegrationConfig = Field(default_factory=IntegrationConfig)
    dev: DevConfig = Field(default_factory=DevConfig)
    build: BuildConfig = Field(default_factory=BuildConfig)
    workspace: WorkspaceConfig = Field(default_factory=WorkspaceConfig)

    # Context system
    context_system: ContextSystemConfig = Field(default_factory=ContextSystemConfig)

    # Custom settings
    custom: dict[str, Any] = Field(default_factory=dict)

    @validator("workspace_path", "templates", pre=True)
    def expand_paths(self, v):
        """
        Expand user paths in configuration.
        """
        if isinstance(v, (str, Path)):
            return Path(v).expanduser()
        if isinstance(v, dict) and "custom_path" in v and v["custom_path"]:
            v["custom_path"] = Path(v["custom_path"]).expanduser()
        return v

    class Config:
        """
        Pydantic configuration.
        """

        validate_assignment = True
        use_enum_values = True


def create_default_contexts() -> dict[str, ContextConfig]:
    """
    Create default context configurations.
    """
    return {
        "pheno": ContextConfig(
            name="Pheno-SDK",
            description="General pheno-sdk ecosystem",
            default_template="api-gateway",
            workspace_path=Path("~/pheno-workspace"),
            project_patterns=["*-kit", "*-service", "*-app"],
            deployment_targets=["docker", "pypi"],
        ),
        "atoms": ContextConfig(
            name="Atoms FastMCP Server",
            description="AI-powered FastAPI MCP server",
            default_template="atoms-server",
            workspace_path=Path("~/atoms-workspace"),
            project_patterns=["atoms-*", "*-atoms", "*-fastmcp"],
            deployment_targets=["vercel", "docker"],
            auth={"default_provider": "authkit"},
            database={"default_provider": "supabase"},
            integrations={
                "authkit": {"enabled": True},
                "supabase": {"enabled": True},
                "vercel": {"enabled": True},
            },
        ),
        "zen": ContextConfig(
            name="Zen MCP Server",
            description="Multi-provider AI MCP server",
            default_template="zen-server",
            workspace_path=Path("~/zen-workspace"),
            project_patterns=["zen-*", "*-zen", "*-mcp-server"],
            deployment_targets=["docker", "k8s", "local"],
            integrations={
                "openai": {"enabled": True},
                "google": {"enabled": True},
                "temporal": {"enabled": True},
                "nats": {"enabled": True},
            },
        ),
        "byteport": ContextConfig(
            name="Byteport",
            description="Development platform and toolkit",
            default_template="byteport-service",
            workspace_path=Path("~/byteport-workspace"),
            project_patterns=["byteport-*", "*-byteport"],
            deployment_targets=["k8s", "aws", "gcp", "docker"],
        ),
    }


def load_config(config_path: Path | None = None) -> PhenoConfig:
    """
    Load configuration from file or create default.
    """

    if config_path is None:
        config_path = get_user_config_dir() / "config.toml"

    if config_path.exists():
        try:
            # Use centralized Config.from_file() which handles TOML
            temp_config = Config.from_file(config_path)
            config_data = temp_config.model_dump()
            config = PhenoConfig(**config_data)
        except Exception:
            # If config is malformed, create backup and use defaults
            backup_path = config_path.with_suffix(".toml.backup")
            config_path.rename(backup_path)
            print(f"Warning: Malformed config backed up to {backup_path}. Using defaults.")
            config = PhenoConfig()
    else:
        # Create default config
        config = PhenoConfig()

    # Ensure default contexts are available
    default_contexts = create_default_contexts()
    for name, context_config in default_contexts.items():
        if name not in config.context_system.contexts:
            config.context_system.add_context(name, context_config)

    # Save config if it was created or updated
    if not config_path.exists() or len(config.context_system.contexts) != len(default_contexts):
        save_config(config, config_path)

    return config


def save_config(config: PhenoConfig, config_path: Path | None = None) -> None:
    """
    Save configuration to file.
    """
    import tomli_w  # For writing TOML

    if config_path is None:
        config_path = get_user_config_dir() / "config.toml"

    # Ensure directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert to dict and save
    config_dict = config.dict()
    with open(config_path, "wb") as f:
        tomli_w.dump(config_dict, f)


def get_project_config(project_path: Path) -> dict[str, Any] | None:
    """
    Load project-specific configuration if it exists.
    """

    project_config_path = project_path / ".pheno.toml"
    if project_config_path.exists():
        try:
            # Use centralized Config.from_file()
            temp_config = Config.from_file(project_config_path)
            return temp_config.model_dump()
        except Exception:
            return None
    return None


def save_project_config(config: dict[str, Any], project_path: Path) -> None:
    """
    Save project-specific configuration.
    """
    import tomli_w

    project_config_path = project_path / ".pheno.toml"
    with open(project_config_path, "wb") as f:
        tomli_w.dump(config, f)
