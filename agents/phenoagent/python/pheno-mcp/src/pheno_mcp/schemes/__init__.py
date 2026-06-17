"""MCP Resource Scheme Handlers.

Collection of resource scheme handlers for different data sources.
These handlers implement the ResourceSchemeHandler protocol.

Available schemes:
- config:// - Configuration access (already in adapters)
- memory:// - In-memory key-value store (already in adapters)
- env:// - Environment variables
- file:// - File system access
- http:// - HTTP resources
- logs:// - Log access
- metrics:// - Metrics access
"""

from .env_scheme import EnvSchemeHandler
from .file_scheme import FileSchemeHandler
from .http_scheme import HttpSchemeHandler
from .logs_scheme import LogsSchemeHandler
from .metrics_scheme import MetricsSchemeHandler

__all__ = [
    "EnvSchemeHandler",
    "FileSchemeHandler",
    "HttpSchemeHandler",
    "LogsSchemeHandler",
    "MetricsSchemeHandler",
]
