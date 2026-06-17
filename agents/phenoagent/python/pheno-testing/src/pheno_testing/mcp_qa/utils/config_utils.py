"""Unified Configuration Utilities for MCP Projects.

Provides configuration management patterns including dataclasses,
YAML loading, environment variables, and validation.

Usage:
    from pheno.testing.mcp_qa.utils.config_utils import load_config, get_env_config

    config = load_config("config.yaml")
    db_url = get_env_config("DATABASE_URL", required=True)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any, Dict, Generic, Mapping, Optional, Type, TypeVar, Union

from pheno.testing.mcp_qa.utils.logging_utils import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


# ============================================================================
# Environment Variable Utilities
# ============================================================================


def get_env(
    key: str,
    default: Optional[str] = None,
    required: bool = False,
    cast: Optional[Type] = None,
) -> Any:
    """Get environment variable with optional casting and validation.

    Args:
        key: Environment variable name
        default: Default value if not found
        required: Raise error if not found and no default
        cast: Type to cast the value to (int, float, bool, etc.)

    Returns:
        Environment variable value (cast if specified)

    Raises:
        ValueError: If required and not found

    Example:
        port = get_env("PORT", default="8000", cast=int)
        debug = get_env("DEBUG", default="false", cast=bool)
    """
    value = os.environ.get(key, default)

    if value is None and required:
        raise ValueError(f"Required environment variable {key} not set")

    if value is None:
        return None

    # Cast to type if specified
    if cast is not None:
        if cast == bool:
            # Special handling for booleans
            return value.lower() in ("true", "1", "yes", "on")
        try:
            return cast(value)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Failed to cast {key}={value} to {cast.__name__}: {e}")

    return value


def get_env_config(prefix: str = "") -> Dict[str, str]:
    """Get all environment variables with optional prefix filtering.

    Args:
        prefix: Only return variables starting with this prefix

    Returns:
        Dictionary of environment variables

    Example:
        # Get all MCP_ variables
        mcp_config = get_env_config("MCP_")
        # Returns: {"MCP_HOST": "...", "MCP_PORT": "..."}
    """
    if not prefix:
        return dict(os.environ)

    return {k: v for k, v in os.environ.items() if k.startswith(prefix)}


def load_env_file(path: Union[str, Path], override: bool = False):
    """Load environment variables from a .env file.

    Args:
        path: Path to .env file
        override: Override existing environment variables

    Example:
        load_env_file(".env.local")
    """
    path = Path(path)

    if not path.exists():
        logger.warning(f"Environment file not found: {path}")
        return

    with path.open("r") as f:
        for line in f:
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith("#"):
                continue

            # Parse KEY=VALUE
            if "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()

            # Remove quotes
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                value = value[1:-1]

            # Set if not exists or override is True
            if override or key not in os.environ:
                os.environ[key] = value


# ============================================================================
# YAML Configuration Loading
# ============================================================================


def load_yaml(path: Union[str, Path]) -> Dict[str, Any]:
    """Load YAML file and return as dictionary.

    Args:
        path: Path to YAML file

    Returns:
        Parsed YAML content

    Raises:
        FileNotFoundError: If file doesn't exist
        RuntimeError: If PyYAML not installed
        ValueError: If YAML is invalid
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError(
            "PyYAML is required to load YAML configurations. "
            "Install it with 'pip install pyyaml'"
        ) from exc

    with path.open("r", encoding="utf-8") as f:
        try:
            data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {path}: {e}")

    if not isinstance(data, Mapping):
        raise ValueError(f"Expected YAML mapping in {path}, got {type(data).__name__}")

    return dict(data)


def save_yaml(data: Dict[str, Any], path: Union[str, Path]):
    """Save dictionary as YAML file.

    Args:
        data: Data to save
        path: Output path
    """
    path = Path(path)

    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError(
            "PyYAML is required to save YAML configurations. "
            "Install it with 'pip install pyyaml'"
        ) from exc

    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)


# ============================================================================
# Configuration Dataclass Base
# ============================================================================


@dataclass
class ConfigBase:
    """Base class for configuration dataclasses with utilities.

    Provides:
    - from_dict() class method for creating from dictionary
    - to_dict() method for converting to dictionary
    - from_yaml() class method for loading from YAML
    - validate() hook for custom validation

    Example:
        @dataclass
        class ServerConfig(ConfigBase):
            host: str = "localhost"
            port: int = 8000
            debug: bool = False

            def validate(self):
                if self.port < 1 or self.port > 65535:
                    raise ValueError("Invalid port")

        config = ServerConfig.from_yaml("server.yaml")
        config.validate()
    """

    @classmethod
    def from_dict(cls: Type[T], data: Mapping[str, Any]) -> T:
        """Create configuration instance from dictionary.

        Args:
            data: Configuration data

        Returns:
            Configuration instance
        """
        # Filter to only known fields
        field_names = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in field_names}

        return cls(**filtered)

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary.

        Returns:
            Configuration as dict
        """
        result = {}
        for f in fields(self):
            value = getattr(self, f.name)

            # Recursively convert nested ConfigBase objects
            if isinstance(value, ConfigBase):
                result[f.name] = value.to_dict()
            elif isinstance(value, list):
                result[f.name] = [v.to_dict() if isinstance(v, ConfigBase) else v for v in value]
            elif isinstance(value, dict):
                result[f.name] = {
                    k: v.to_dict() if isinstance(v, ConfigBase) else v for k, v in value.items()
                }
            else:
                result[f.name] = value

        return result

    @classmethod
    def from_yaml(cls: Type[T], path: Union[str, Path]) -> T:
        """Load configuration from YAML file.

        Args:
            path: Path to YAML file

        Returns:
            Configuration instance
        """
        data = load_yaml(path)
        return cls.from_dict(data)

    def to_yaml(self, path: Union[str, Path]):
        """Save configuration to YAML file.

        Args:
            path: Output path
        """
        save_yaml(self.to_dict(), path)

    def validate(self):
        """Override this method to add custom validation.

        Raises:
            ValueError: If validation fails
        """
        pass


# ============================================================================
# Configuration Manager
# ============================================================================


class ConfigManager(Generic[T]):
    """Generic configuration manager with caching and reloading.

    Example:
        @dataclass
        class AppConfig(ConfigBase):
            database_url: str
            api_key: str

        manager = ConfigManager(AppConfig, "config.yaml")
        config = manager.get()

        # Reload from disk
        manager.reload()
    """

    def __init__(
        self,
        config_class: Type[T],
        path: Optional[Union[str, Path]] = None,
        data: Optional[Dict[str, Any]] = None,
    ):
        """Initialize configuration manager.

        Args:
            config_class: Configuration dataclass type
            path: Path to YAML file (optional if data provided)
            data: Configuration data (optional if path provided)
        """
        self.config_class = config_class
        self.path = Path(path) if path else None
        self._config: Optional[T] = None

        if data:
            self._config = config_class.from_dict(data)
        elif self.path:
            self.reload()

    def get(self) -> T:
        """
        Get configuration instance.
        """
        if self._config is None:
            raise RuntimeError("Configuration not loaded")
        return self._config

    def reload(self):
        """
        Reload configuration from file.
        """
        if not self.path:
            raise RuntimeError("No path specified for reloading")

        if not self.path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.path}")

        data = load_yaml(self.path)
        self._config = self.config_class.from_dict(data)

        # Validate if method exists
        if hasattr(self._config, "validate"):
            self._config.validate()

        logger.info(f"Loaded configuration from {self.path}")

    def save(self):
        """
        Save current configuration to file.
        """
        if not self.path:
            raise RuntimeError("No path specified for saving")

        if self._config is None:
            raise RuntimeError("No configuration to save")

        if hasattr(self._config, "to_yaml"):
            self._config.to_yaml(self.path)
        else:
            save_yaml(
                self._config.to_dict() if hasattr(self._config, "to_dict") else vars(self._config),
                self.path,
            )

        logger.info(f"Saved configuration to {self.path}")


# ============================================================================
# Common Configuration Patterns
# ============================================================================


@dataclass
class DatabaseConfig(ConfigBase):
    """
    Common database configuration.
    """

    url: str
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    echo: bool = False


@dataclass
class ServerConfig(ConfigBase):
    """
    Common server configuration.
    """

    host: str = "localhost"
    port: int = 8000
    workers: int = 1
    reload: bool = False
    log_level: str = "info"


@dataclass
class AuthConfig(ConfigBase):
    """
    Common authentication configuration.
    """

    enabled: bool = True
    provider: str = "authkit"
    client_id: str = ""
    client_secret: str = ""
    redirect_uri: str = ""


__all__ = [
    "get_env",
    "get_env_config",
    "load_env_file",
    "load_yaml",
    "save_yaml",
    "ConfigBase",
    "ConfigManager",
    "DatabaseConfig",
    "ServerConfig",
    "AuthConfig",
]
