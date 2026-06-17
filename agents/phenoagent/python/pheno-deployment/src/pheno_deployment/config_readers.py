"""Configuration readers and validation.

Provides environment management and configuration validation for different deployment
platforms.
"""

import json
import os
from pathlib import Path
from typing import Any

import yaml


class ConfigValidationError(Exception):
    """
    Configuration validation error.
    """



class EnvironmentConfig:
    """Manage environment-specific configuration.

    Handles loading and validating configuration files for different deployment
    environments.
    """

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self._configs: dict[str, dict[str, Any]] = {}
        self._load_configs()

    def _load_configs(self) -> None:
        """
        Load all available configuration files.
        """
        config_files = [
            "package.json",
            "requirements.txt",
            "pyproject.toml",
            "Dockerfile",
            "docker-compose.yml",
            ".env.example",
            "vercel.json",
            "netlify.toml",
            "google-cloud.json",
            "aws-config.json",
        ]

        for config_file in config_files:
            config_path = self.project_root / config_file
            if config_path.exists():
                try:
                    self._configs[config_file] = self._load_config_file(config_path)
                except Exception as e:
                    # Log warning but continue loading other configs
                    print(f"Warning: Failed to load {config_file}: {e}")

    def _load_config_file(self, config_path: Path) -> dict[str, Any]:
        """
        Load a single configuration file.
        """
        suffix = config_path.suffix.lower()

        if suffix == ".json":
            with open(config_path, encoding="utf-8") as f:
                return json.load(f)
        elif suffix in [".yml", ".yaml"]:
            with open(config_path, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        elif suffix == ".toml":
            try:
                import tomllib

                with open(config_path, "rb") as f:
                    return tomllib.load(f)
            except ImportError:
                import toml

                with open(config_path, encoding="utf-8") as f:
                    return toml.load(f)
        else:
            # For text files like requirements.txt, .env.example
            with open(config_path, encoding="utf-8") as f:
                return {"content": f.read()}

    def get_config(self, filename: str) -> dict[str, Any] | None:
        """
        Get configuration by filename.
        """
        return self._configs.get(filename)

    def has_config(self, filename: str) -> bool:
        """
        Check if configuration file exists.
        """
        return filename in self._configs

    def list_configs(self) -> list[str]:
        """
        List all loaded configuration files.
        """
        return list(self._configs.keys())

    def validate_config(self, filename: str, required_keys: list[str]) -> bool:
        """
        Validate configuration has required keys.
        """
        config = self.get_config(filename)
        if not config:
            raise ConfigValidationError(f"Configuration file {filename} not found")

        missing_keys = [key for key in required_keys if key not in config]
        if missing_keys:
            raise ConfigValidationError(f"Missing required keys in {filename}: {missing_keys}")
        return True

    def get_value(self, config_file: str, key_path: str, default: Any = None) -> Any:
        """
        Get a value from config using dot notation (e.g., 'build.command').
        """
        config = self.get_config(config_file)
        if not config:
            return default

        keys = key_path.split(".")
        current = config

        try:
            for key in keys:
                current = current[key]
            return current
        except (KeyError, TypeError):
            return default


class EnvVarManager:
    """Manage environment variables for deployment.

    Handles loading, validating, and managing environment variables across different
    deployment platforms.
    """

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self._env_vars: dict[str, str] = {}
        self._load_env_vars()

    def _load_env_vars(self) -> None:
        """
        Load environment variables from various sources.
        """
        # Load from .env file if it exists
        env_file = self.project_root / ".env"
        if env_file.exists():
            with open(env_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        self._env_vars[key.strip()] = value.strip()

        # Override with actual environment variables
        self._env_vars.update(os.environ)

    def get(self, key: str, default: str | None = None) -> str | None:
        """
        Get environment variable.
        """
        return self._env_vars.get(key, default)

    def set(self, key: str, value: str) -> None:
        """
        Set environment variable.
        """
        self._env_vars[key] = value

    def get_required(self, key: str) -> str:
        """
        Get required environment variable, raise if missing.
        """
        value = self.get(key)
        if value is None:
            raise ConfigValidationError(f"Required environment variable {key} is missing")
        return value

    def list_required_vars(self, platform: str) -> list[str]:
        """
        Get list of required variables for a platform.
        """
        required_vars = {
            "vercel": ["VERCEL_TOKEN", "VERCEL_ORG_ID", "VERCEL_PROJECT_ID"],
            "netlify": ["NETLIFY_AUTH_TOKEN", "NETLIFY_SITE_ID"],
            "heroku": ["HEROKU_API_KEY", "HEROKU_APP_NAME"],
            "aws": ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION"],
            "gcp": ["GOOGLE_APPLICATION_CREDENTIALS", "GCP_PROJECT_ID"],
            "azure": ["AZURE_SUBSCRIPTION_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET"],
        }
        return required_vars.get(platform, [])

    def validate_platform_vars(self, platform: str) -> bool:
        """
        Validate required environment variables for a platform.
        """
        required_vars = self.list_required_vars(platform)
        missing_vars = [var for var in required_vars if not self.get(var)]

        if missing_vars:
            raise ConfigValidationError(
                f"Missing required environment variables for {platform}: {missing_vars}",
            )
        return True

    def export_vars(self, vars_to_export: list[str]) -> dict[str, str]:
        """
        Export specified environment variables.
        """
        return {var: self.get(var, "") for var in vars_to_export}
