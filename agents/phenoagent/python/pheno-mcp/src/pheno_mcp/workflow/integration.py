"""Workflow Integration Utilities for MCP.

Helper functions for integrating workflow monitoring with MCP servers.
"""

import asyncio
import logging
import os
from typing import Any

from pheno.mcp.workflow.monitoring import (
    WorkflowMonitoringIntegration,
    initialize_workflow_monitoring,
)

logger = logging.getLogger(__name__)


def integrate_with_server(app, **kwargs):
    """One-line integration with existing MCP server.

    Args:
        app: FastAPI application instance
        **kwargs: Additional configuration for monitoring

    Returns:
        WorkflowMonitoringIntegration: Initialized integration instance
    """
    try:
        # Initialize monitoring with configuration
        integration = initialize_workflow_monitoring(**kwargs)

        # Integrate with FastAPI
        integration.integrate_with_fastapi(app)

        # Start monitoring in background
        loop = asyncio.get_event_loop()
        loop.create_task(integration.start_monitoring())

        logger.info("Successfully integrated workflow monitoring with server")
        return integration

    except Exception as e:
        logger.exception(f"Failed to integrate workflow monitoring with server: {e}")
        raise


def get_monitoring_config() -> dict[str, Any]:
    """Get monitoring configuration from environment variables.

    Returns:
        dict: Configuration dictionary
    """
    return {
        "enable_background_monitoring": os.getenv("WORKFLOW_MONITORING_ENABLED", "true").lower()
        == "true",
        "monitoring_interval_seconds": int(os.getenv("WORKFLOW_MONITORING_INTERVAL", "30")),
        "log_level": getattr(
            logging, os.getenv("WORKFLOW_MONITORING_LOG_LEVEL", "INFO").upper(), logging.INFO,
        ),
    }


def configure_monitoring_from_env() -> dict[str, Any]:
    """Configure monitoring from environment variables.

    Returns:
        dict: Full configuration dictionary with all settings
    """
    config = get_monitoring_config()

    # Add additional configuration
    config.update(
        {
            "dashboard_enabled": os.getenv("WORKFLOW_DASHBOARD_ENABLED", "true").lower() == "true",
            "api_enabled": os.getenv("WORKFLOW_API_ENABLED", "true").lower() == "true",
            "alerts_enabled": os.getenv("WORKFLOW_ALERTS_ENABLED", "true").lower() == "true",
        },
    )

    return config


async def setup_mcp_workflow_monitoring(
    app,
    workflow_engine: Any | None = None,
    distributed_executor: Any | None = None,
    config: dict[str, Any] | None = None,
) -> WorkflowMonitoringIntegration:
    """Complete setup for MCP workflow monitoring.

    Args:
        app: FastAPI application instance
        workflow_engine: Optional workflow engine instance
        distributed_executor: Optional distributed executor instance
        config: Optional configuration dictionary (uses env vars if None)

    Returns:
        WorkflowMonitoringIntegration: Configured and started integration
    """
    # Use environment config if none provided
    if config is None:
        config = configure_monitoring_from_env()

    # Initialize integration
    integration = initialize_workflow_monitoring(
        workflow_engine=workflow_engine, distributed_executor=distributed_executor, **config,
    )

    # Integrate with FastAPI
    if config.get("api_enabled", True):
        integration.integrate_with_fastapi(app)

    # Start monitoring
    if config.get("enable_background_monitoring", True):
        await integration.start_monitoring()

    logger.info("MCP workflow monitoring fully configured and started")
    return integration


async def shutdown_workflow_monitoring(integration: WorkflowMonitoringIntegration | None = None):
    """Gracefully shutdown workflow monitoring.

    Args:
        integration: Optional specific integration instance (uses global if None)
    """
    if integration is None:
        from pheno.mcp.workflow.monitoring import get_workflow_monitoring

        integration = get_workflow_monitoring()

    if integration:
        await integration.stop_monitoring()
        logger.info("Workflow monitoring shutdown complete")
    else:
        logger.warning("No workflow monitoring instance to shutdown")
