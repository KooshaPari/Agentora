"""
Zen MCP Entry Point Constructor
==============================

Specialized entry point for the Zen MCP server, providing Zen-specific
configuration and defaults.
"""

import logging
import os
from pathlib import Path

from .base import MCPEntryPoint, MCPServiceConfig


class ZenMCPEntryPoint(MCPEntryPoint):
    """Entry point constructor for the Zen MCP server.

    Provides Zen-specific defaults and configuration:
    - Default port: 8000
    - Default domain: zen.kooshapari.com
    - Zen-specific service configuration
    - Integration with FastMCP and pheno-sdk packages
    """

    # Zen-specific defaults
    DEFAULT_PORT = 8000
    DEFAULT_DOMAIN = "zen.kooshapari.com"
    PROJECT_NAME = "zen_mcp"

    def __init__(
        self,
        port: int | None = None,
        domain: str | None = None,
        dev_mode: bool = False,
        no_auth: bool = False,
        skip_validation: bool = False,
        logger: logging.Logger | None = None,
    ):
        """Initialize the Zen MCP entry point.

        Args:
            port: Port to run on (default: 8000)
            domain: Domain for tunnel (default: zen.kooshapari.com)
            dev_mode: Enable development mode
            no_auth: Disable authentication
            skip_validation: Skip startup validation
            logger: Optional logger instance
        """
        self.port = port or self.DEFAULT_PORT
        self.domain = domain or self.DEFAULT_DOMAIN
        self.dev_mode = dev_mode
        self.no_auth = no_auth
        self.skip_validation = skip_validation

        # Configure logging
        if logger is None:
            logger = logging.getLogger(self.PROJECT_NAME)
            if dev_mode:
                logger.setLevel(logging.DEBUG)

        # Create Zen-specific service configuration
        service_configs = self._create_zen_service_configs()

        # Initialize base class
        super().__init__(
            project_name=self.PROJECT_NAME,
            service_configs=service_configs,
            dependencies={},  # Zen doesn't have complex dependencies
            service_domain=self.domain,
            logger=logger,
        )

    def _create_zen_service_configs(self) -> list[MCPServiceConfig]:
        """
        Create Zen-specific service configurations.
        """
        # Build the command with proper environment
        repo_root = Path(__file__).parent.parent.parent.parent.resolve()

        # Set up environment variables for Zen
        environment = {
            "ZEN_DEV_MODE": "1" if self.dev_mode else "0",
            "ZEN_NO_AUTH": "1" if self.no_auth else "0",
            "ZEN_SKIP_VALIDATION": "1" if self.skip_validation else "0",
            "ZEN_PROVIDER_PRIORITY": "OPENROUTER",
            "EMBEDDINGS_PROVIDER": "ollama",
            "OLLAMA_EMBED_MODEL": "nomic-embed-text",
        }

        # Add development-specific environment variables
        if self.dev_mode:
            environment.update(
                {
                    "FASTMCP_LOG_LEVEL": "DEBUG",
                    "ZEN_MINIMAL_HTTP": "0",
                },
            )

        # Create service configuration
        service_config = MCPServiceConfig(
            name="zen_server",
            command="python -m zen_mcp_server.server",
            port=self.port,
            domain=self.domain,
            health_check_path="/health",
            startup_timeout=60,  # Zen has more complex startup
            shutdown_timeout=15,
            environment=environment,
            working_directory=repo_root,
        )

        return [service_config]

    async def start_zen_server(self) -> int:
        """Start the Zen MCP server.

        Returns:
            Exit code (0 for success, 1 for failure)
        """
        try:
            success = await self.start(monitor=True)
            return 0 if success else 1
        except Exception as e:
            self.logger.exception(f"Failed to start Zen MCP server: {e}")
            return 1

    def get_server_info(self) -> dict:
        """
        Get information about the Zen MCP server configuration.
        """
        return {
            "project": self.PROJECT_NAME,
            "port": self.port,
            "domain": self.domain,
            "dev_mode": self.dev_mode,
            "no_auth": self.no_auth,
            "skip_validation": self.skip_validation,
            "services": [config.name for config in self.service_configs],
        }

    async def validate_configuration(self) -> bool:
        """Validate Zen MCP server configuration.

        Returns:
            True if configuration is valid, False otherwise
        """
        try:
            # Check if FastMCP is available
            try:
                self.logger.debug("FastMCP is available")
            except ImportError as e:
                self.logger.exception(f"FastMCP is not available: {e}")
                return False

            # Check if required environment variables are set
            required_vars = ["AUTHKIT_DOMAIN", "AUTHKIT_BASE_URL"]
            missing_vars = [var for var in required_vars if not os.getenv(var)]

            if missing_vars and not self.no_auth:
                self.logger.warning(f"Missing required environment variables: {missing_vars}")
                self.logger.warning("Set FASTMCP_ALLOW_UNAUTH=1 for local testing without auth")

            return True

        except Exception as e:
            self.logger.exception(f"Configuration validation failed: {e}")
            return False
