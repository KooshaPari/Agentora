"""Shared MCP resource templates for pheno-sdk.

This module provides base resource templates that can be used across different MCP
server implementations. It includes common schemes like zen://, system://, config://,
logs://, metrics://, tools://, prompts://, files://, and static://.
"""

import logging

logger = logging.getLogger(__name__)

from .schemes import (
    ConfigResourceScheme,
    FilesResourceScheme,
    LogsResourceScheme,
    MetricsResourceScheme,
    PromptsResourceScheme,
    StaticResourceScheme,
    SystemResourceScheme,
    ToolsResourceScheme,
    ZenResourceScheme,
)
from .template_engine import ResourceAnnotation, ResourceParameter, ResourceTemplate

# Initialize scheme handlers
_zen_handler = ZenResourceScheme()
_system_handler = SystemResourceScheme()
_config_handler = ConfigResourceScheme()
_logs_handler = LogsResourceScheme()
_metrics_handler = MetricsResourceScheme()
_tools_handler = ToolsResourceScheme()
_prompts_handler = PromptsResourceScheme()
_files_handler = FilesResourceScheme()
_static_handler = StaticResourceScheme()

# Core Zen Resources
ZEN_RESOURCE_TEMPLATES = [
    ResourceTemplate(
        name="zen-status",
        uri_pattern="zen://status/{component}",
        description="Dynamic system status by component",
        handler=_zen_handler.get_status,
        parameters=[
            ResourceParameter(
                name="component",
                type="string",
                required=False,
                default="all",
                description="Status component to retrieve",
                choices=["all", "tools", "auth", "resources", "middleware"],
            ),
        ],
        annotations=ResourceAnnotation(
            read_only_hint=True,
            idempotent_hint=True,
            cache_ttl_seconds=30,
            performance_hint="fast",
            description="Real-time server status information",
        ),
        scheme="zen",
    ),
]

# Combine all shared templates
ALL_SHARED_TEMPLATES = ZEN_RESOURCE_TEMPLATES


def get_shared_templates() -> list[ResourceTemplate]:
    """
    Get all shared resource templates.
    """
    return ALL_SHARED_TEMPLATES
