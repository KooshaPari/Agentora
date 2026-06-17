"""MCP Setup Utilities.

Helper functions to configure MCP with adapters and DI container.
"""

import logging

from pheno.adapters.container import Container, Lifecycle, get_container
from pheno.mcp.adapters import (
    InMemoryMcpProvider,
    InMemoryMonitoringProvider,
    InMemoryResourceProvider,
    InMemorySessionManager,
    InMemoryToolRegistry,
)
from pheno.mcp.adapters.resource_provider import (
    ConfigSchemeHandler,
    MemorySchemeHandler,
)
from pheno.mcp.manager import McpManager
from pheno.mcp.schemes import (
    EnvSchemeHandler,
    FileSchemeHandler,
    HttpSchemeHandler,
    LogsSchemeHandler,
    MetricsSchemeHandler,
)
from pheno.ports.mcp import (
    McpProvider,
    MonitoringProvider,
    ResourceProvider,
    SessionManager,
    ToolRegistry,
)

logger = logging.getLogger(__name__)


def setup_mcp(
    container: Container | None = None,
    with_monitoring: bool = True,
    with_default_schemes: bool = True,
    with_extended_schemes: bool = False,
) -> McpManager:
    """Setup MCP with default in-memory adapters.

    Registers all MCP providers in the DI container and returns
    a configured MCP manager.

    Args:
        container: Optional DI container (uses global if None)
        with_monitoring: Whether to register monitoring provider
        with_default_schemes: Whether to register default resource schemes (config://, memory://)
        with_extended_schemes: Whether to register extended schemes (env://, file://, http://, logs://, metrics://)

    Returns:
        Configured MCP manager

    Example:
        >>> manager = setup_mcp()
        >>> session = await manager.connect(server)
        >>> result = await manager.execute_tool("search", {"query": "hello"})
    """
    container = container or get_container()

    # Register MCP provider
    if not container.has_service(McpProvider):
        container.register(McpProvider, InMemoryMcpProvider, Lifecycle.SINGLETON)
        logger.info("Registered InMemoryMcpProvider")

    # Register resource provider
    if not container.has_service(ResourceProvider):
        container.register(ResourceProvider, InMemoryResourceProvider, Lifecycle.SINGLETON)
        logger.info("Registered InMemoryResourceProvider")

    # Register schemes (always do this, even if provider already registered)
    if with_default_schemes or with_extended_schemes:
        resource_provider = container.resolve(ResourceProvider)

        # Register default schemes
        if with_default_schemes:
            # Config scheme
            config_handler = ConfigSchemeHandler()
            resource_provider.register_scheme("config", config_handler)

            # Memory scheme
            memory_handler = MemorySchemeHandler()
            resource_provider.register_scheme("memory", memory_handler)

            logger.info("Registered default resource schemes: config://, memory://")

        # Register extended schemes
        if with_extended_schemes:
            # Environment variables
            env_handler = EnvSchemeHandler()
            resource_provider.register_scheme("env", env_handler)

            # File system
            file_handler = FileSchemeHandler()
            resource_provider.register_scheme("file", file_handler)

            # HTTP
            http_handler = HttpSchemeHandler()
            resource_provider.register_scheme("http", http_handler)
            resource_provider.register_scheme("https", http_handler)

            # Logs
            logs_handler = LogsSchemeHandler()
            resource_provider.register_scheme("logs", logs_handler)

            # Metrics
            metrics_handler = MetricsSchemeHandler()
            resource_provider.register_scheme("metrics", metrics_handler)

            logger.info(
                "Registered extended resource schemes: env://, file://, http://, logs://, metrics://",
            )

    # Register tool registry
    if not container.has_service(ToolRegistry):
        container.register(ToolRegistry, InMemoryToolRegistry, Lifecycle.SINGLETON)
        logger.info("Registered InMemoryToolRegistry")

    # Register session manager
    if not container.has_service(SessionManager):
        container.register(SessionManager, InMemorySessionManager, Lifecycle.SINGLETON)
        logger.info("Registered InMemorySessionManager")

    # Register monitoring provider (optional)
    if with_monitoring and not container.has_service(MonitoringProvider):
        container.register(MonitoringProvider, InMemoryMonitoringProvider, Lifecycle.SINGLETON)
        logger.info("Registered InMemoryMonitoringProvider")

    # Create and return manager
    manager = McpManager(container)
    logger.info("MCP setup complete")

    return manager


def setup_mcp_with_config(config: dict) -> McpManager:
    """Setup MCP with configuration data.

    Registers adapters and pre-loads configuration into config:// scheme.

    Args:
        config: Configuration dictionary

    Returns:
        Configured MCP manager

    Example:
        >>> config = {
        ...     "app": {"name": "myapp", "debug": True},
        ...     "database": {"host": "localhost", "port": 5432}
        ... }
        >>> manager = setup_mcp_with_config(config)
        >>> db_config = await manager.get_resource("config://database")
    """
    manager = setup_mcp(with_default_schemes=True)

    # Get resource provider and set config
    resource_provider = manager.container.resolve(ResourceProvider)
    config_handler = resource_provider.get_scheme_handler("config")

    if hasattr(config_handler, "set_config"):
        config_handler.set_config(config)
        logger.info("Loaded configuration into config:// scheme")

    return manager


def register_custom_scheme(scheme: str, handler: any, container: Container | None = None) -> None:
    """Register a custom resource scheme handler.

    Args:
        scheme: Scheme name (e.g., "db", "storage")
        handler: Scheme handler implementation
        container: Optional DI container (uses global if None)

    Example:
        >>> class DbSchemeHandler:
        ...     async def get_resource(self, uri: str):
        ...         # Fetch from database
        ...         pass
        >>>
        >>> register_custom_scheme("db", DbSchemeHandler())
    """
    container = container or get_container()

    if not container.has_service(ResourceProvider):
        raise RuntimeError("ResourceProvider not registered. Call setup_mcp() first.")

    resource_provider = container.resolve(ResourceProvider)
    resource_provider.register_scheme(scheme, handler)
    logger.info(f"Registered custom scheme: {scheme}://")


__all__ = [
    "register_custom_scheme",
    "setup_mcp",
    "setup_mcp_with_config",
]
