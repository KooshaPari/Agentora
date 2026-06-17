"""MCP extensions for infrastructure management.

This module contains MCP-specific features that are actively maintained.
"""

import os
import socket


class MCPExtensions:
    """
    MCP-specific extensions for infrastructure management.
    """

    def __init__(self):
        self._environment_cache = None

    def get_mcp_endpoint(
        self, environment: str | None = None, config: dict | None = None,
    ) -> str:
        """Get MCP endpoint URL for environment.

        Args:
            environment: Environment name (prod/staging/dev/local)
                        If None, auto-detects environment
            config: Configuration dictionary

        Returns:
            str: MCP endpoint URL
        """
        if environment is None:
            environment = self.detect_environment()

        if config is None:
            config = self._get_default_mcp_config()

        endpoints = config.get("mcp", {}).get("endpoints", {})

        # Map environment names
        env_mapping = {
            "production": "production",
            "prod": "production",
            "staging": "staging",
            "stage": "staging",
            "development": "development",
            "dev": "development",
            "local": "local",
        }

        mapped_env = env_mapping.get(environment.lower(), environment.lower())
        return endpoints.get(mapped_env, endpoints.get("local", "http://localhost:8000"))


    def detect_environment(self) -> str:
        """Auto-detect deployment environment.

        Returns:
            str: Environment name (production/staging/development/local)
        """
        if self._environment_cache:
            return self._environment_cache

        # Check environment variables
        env_var = os.getenv("ENVIRONMENT", "").lower()
        if env_var in ["production", "prod"]:
            self._environment_cache = "production"
        elif env_var in ["staging", "stage"]:
            self._environment_cache = "staging"
        elif env_var in ["development", "dev"]:
            self._environment_cache = "development"
        # Check if running locally
        elif self._is_local_environment():
            self._environment_cache = "local"
        else:
            self._environment_cache = "development"

        return self._environment_cache

    def _is_local_environment(self) -> bool:
        """
        Check if running in local environment.
        """
        # Check for common local development indicators
        local_indicators = [
            os.getenv("LOCAL_DEVELOPMENT", "").lower() == "true",
            os.getenv("NODE_ENV", "").lower() == "development",
            os.path.exists("/.dockerenv"),  # Docker container
            os.path.exists("/proc/1/cgroup") and "docker" in open("/proc/1/cgroup").read(),
            socket.gethostname().startswith("localhost"),
            socket.gethostname().startswith("dev-"),
        ]

        return any(local_indicators)

    def get_mcp_config(
        self, environment: str | None = None, config: dict | None = None,
    ) -> dict:
        """Get complete MCP configuration for environment.

        Args:
            environment: Environment name (prod/staging/dev/local)
                        If None, auto-detects environment
            config: Configuration dictionary

        Returns:
            dict: Complete MCP configuration
        """
        if environment is None:
            environment = self.detect_environment()

        if config is None:
            config = self._get_default_mcp_config()

        mcp_config = config.get("mcp", {}).copy()
        mcp_config["environment"] = environment
        mcp_config["endpoint"] = self.get_mcp_endpoint(environment, config)

        return mcp_config

    def get_environment_display(self) -> str:
        """Get human-readable environment display.

        Returns:
            str: Formatted environment information
        """
        environment = self.detect_environment()
        endpoint = self.get_mcp_endpoint(environment)

        display = f"Environment: {environment.title()}\n"
        display += f"Endpoint: {endpoint}\n"

        if environment == "local":
            display += "Status: Local Development"
        elif environment == "development":
            display += "Status: Development Server"
        elif environment == "staging":
            display += "Status: Staging Server"
        elif environment == "production":
            display += "Status: Production Server"

        return display

    def _get_default_mcp_config(self) -> dict:
        """
        Get default MCP configuration.
        """
        return {
            "mcp": {
                "endpoints": {
                    "production": "https://api.production.com",
                    "staging": "https://api.staging.com",
                    "development": "https://api.dev.com",
                    "local": "http://localhost:8000",
                },
                "timeout": 30,
                "retry_attempts": 3,
            },
        }

    def get_status(self) -> dict:
        """
        Get MCP extensions status.
        """
        return {
            "environment": self.detect_environment(),
            "endpoint": self.get_mcp_endpoint(),
            "cached": self._environment_cache is not None,
        }
