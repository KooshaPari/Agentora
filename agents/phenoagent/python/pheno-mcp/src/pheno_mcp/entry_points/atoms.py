"""
Atoms MCP Entry Point Constructor
=================================

Specialized entry point for the Atoms MCP server, providing Atoms-specific
configuration and defaults.
"""

import logging
from pathlib import Path

from .base import MCPEntryPoint, MCPServiceConfig


class AtomsMCPEntryPoint(MCPEntryPoint):
    """Entry point constructor for the Atoms MCP server.

    Provides Atoms-specific defaults and configuration:
    - Default port: 50002
    - Default domain: atomcp.kooshapari.com
    - Atoms-specific service configuration
    - Integration with pheno-sdk packages
    """

    # Atoms-specific defaults
    DEFAULT_PORT = 50002
    DEFAULT_DOMAIN = "atomcp.kooshapari.com"
    PROJECT_NAME = "atoms_mcp"

    def __init__(
        self,
        port: int | None = None,
        domain: str | None = None,
        verbose: bool = False,
        no_tunnel: bool = False,
        logger: logging.Logger | None = None,
    ):
        """Initialize the Atoms MCP entry point.

        Args:
            port: Port to run on (default: 50002)
            domain: Domain for tunnel (default: atomcp.kooshapari.com)
            verbose: Enable verbose logging
            no_tunnel: Disable CloudFlare tunnel
            logger: Optional logger instance
        """
        self.port = port or self.DEFAULT_PORT
        self.domain = domain if not no_tunnel else None
        self.verbose = verbose
        self.no_tunnel = no_tunnel

        # Configure logging
        if logger is None:
            logger = logging.getLogger(self.PROJECT_NAME)
            if verbose:
                logger.setLevel(logging.DEBUG)

        # Create Atoms-specific service configuration
        service_configs = self._create_atoms_service_configs()

        # Initialize base class
        super().__init__(
            project_name=self.PROJECT_NAME,
            service_configs=service_configs,
            dependencies={},  # Atoms doesn't have complex dependencies
            service_domain=self.domain,
            logger=logger,
        )

    def _create_atoms_service_configs(self) -> list[MCPServiceConfig]:
        """
        Create Atoms-specific service configurations.
        """
        # Build the command with proper PYTHONPATH
        sdk_root = Path(__file__).parent.parent.parent.parent.resolve()
        repo_root = sdk_root.parent.parent

        # Set up PYTHONPATH for pheno-sdk packages
        sdk_paths = [
            str(sdk_root / "KInfra" / "libraries" / "python"),
            str(sdk_root / "mcp-QA"),
        ]

        # Create environment variables
        environment = {
            "PYTHONPATH": ":".join(sdk_paths),
            "ATOMS_VERBOSE": "1" if self.verbose else "0",
            "ATOMS_NO_TUNNEL": "1" if self.no_tunnel else "0",
        }

        # Create service configuration - use atoms-mcp-enhanced.py directly
        atoms_script = repo_root / "atoms_mcp-old" / "atoms-mcp-enhanced.py"
        service_config = MCPServiceConfig(
            name="atoms_server",
            command=["python", str(atoms_script), "start"],
            port=self.port,
            domain=self.domain,
            health_check_path="/health",
            startup_timeout=30,
            shutdown_timeout=10,
            environment=environment,
            working_directory=repo_root,
        )

        return [service_config]

    async def start_atoms_server(self) -> int:
        """Start the Atoms MCP server.

        Returns:
            Exit code (0 for success, 1 for failure)
        """
        try:
            success = await self.start(monitor=True)
            return 0 if success else 1
        except Exception as e:
            self.logger.exception(f"Failed to start Atoms MCP server: {e}")
            return 1

    def get_server_info(self) -> dict:
        """
        Get information about the Atoms MCP server configuration.
        """
        return {
            "project": self.PROJECT_NAME,
            "port": self.port,
            "domain": self.domain,
            "tunnel_enabled": not self.no_tunnel,
            "verbose": self.verbose,
            "services": [config.name for config in self.service_configs],
        }
