"""Generic MCP tool decorators with auto-schema generation.

This module provides framework-agnostic decorators that simplify tool registration
across multiple MCP frameworks (FastMCP 2.0+, LangChain, Anthropic SDK, Custom).

Key Features:
    - Auto-schema generation from type hints
    - Multi-framework support (FastMCP, LangChain, Anthropic)
    - Input validation with type coercion
    - Async/sync function support
    - Error handling wrappers
    - Deprecation decorators
    - Zero-dependency generic implementation

Examples:
    Basic usage with auto-schema:
        >>> @mcp_tool(name="analyze_code", category="code_analysis")
        ... async def analyze(file_path: str, depth: int = 1) -> dict:
        ...     '''Analyze code structure.'''
        ...     return {"status": "analyzed", "depth": depth}

    With explicit schema:
        >>> @mcp_tool(
        ...     name="process_data",
        ...     schema={"type": "object", "properties": {...}}
        ... )
        ... def process(data: dict) -> dict:
        ...     return data

    Framework-specific registration:
        >>> @mcp_tool(framework="fastmcp", tags=["ml", "analysis"])
        ... async def ml_analyze(data: list[float]) -> dict:
        ...     return {"result": sum(data)}

    With validation:
        >>> @mcp_tool(validate_inputs=True, coerce_types=True)
        ... def strict_tool(count: int, name: str) -> dict:
        ...     return {"count": count, "name": name}
"""

from __future__ import annotations

import functools
import inspect
import logging
import warnings
from dataclasses import dataclass, field
from enum import StrEnum
from typing import (
    TYPE_CHECKING,
    Any,
    ParamSpec,
    TypeVar,
)

if TYPE_CHECKING:
    from collections.abc import Callable

# Type variables for generic decorator support
P = ParamSpec("P")
R = TypeVar("R")

# Configure logger
logger = logging.getLogger(__name__)


class ToolFramework(StrEnum):
    """Supported MCP tool frameworks."""

    FASTMCP = "fastmcp"
    LANGCHAIN = "langchain"
    ANTHROPIC = "anthropic"
    CUSTOM = "custom"
    AUTO = "auto"


@dataclass
class ToolMetadata:
    """Metadata container for MCP tools.

    Stores all information needed to register and execute tools across
    different MCP frameworks.

    Attributes:
        name: Tool identifier
        description: Human-readable tool description
        schema: JSON schema for tool parameters
        annotations: Additional metadata (category, tags, etc.)
        framework: Target MCP framework
        validate_inputs: Whether to validate inputs against schema
        coerce_types: Whether to coerce input types to match schema
        deprecated: Deprecation message if tool is deprecated
        version: Tool version string
    """

    name: str
    description: str
    schema: dict[str, Any]
    annotations: dict[str, Any] = field(default_factory=dict)
    framework: ToolFramework = ToolFramework.AUTO
    validate_inputs: bool = True
    coerce_types: bool = False
    deprecated: str | None = None
    version: str | None = None


def _extract_description(func: Callable) -> str:
    """Extract description from function docstring.

    Args:
        func: Function to extract description from

    Returns:
        First line of docstring or empty string
    """
    if not func.__doc__:
        return ""
    return func.__doc__.strip().split("\n")[0]


def _create_async_wrapper(
    func: Callable[P, R],
    metadata: ToolMetadata,
) -> Callable[P, R]:
    """Create async wrapper with validation and error handling.

    Args:
        func: Original async function
        metadata: Tool metadata

    Returns:
        Wrapped async function
    """
    from pheno.mcp.tools.decorators_validation import _process_inputs

    @functools.wraps(func)
    async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        if metadata.deprecated:
            warnings.warn(
                f"Tool '{metadata.name}' is deprecated: {metadata.deprecated}",
                DeprecationWarning,
                stacklevel=2,
            )

        try:
            if metadata.validate_inputs or metadata.coerce_types:
                kwargs = _process_inputs(kwargs, metadata)

            return await func(*args, **kwargs)

        except Exception as e:
            logger.error(f"Tool '{metadata.name}' failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "error_type": type(e).__name__,
                "tool": metadata.name,
            }

    return async_wrapper  # type: ignore


def _create_sync_wrapper(
    func: Callable[P, R],
    metadata: ToolMetadata,
) -> Callable[P, R]:
    """Create sync wrapper with validation and error handling.

    Args:
        func: Original sync function
        metadata: Tool metadata

    Returns:
        Wrapped sync function
    """
    from pheno.mcp.tools.decorators_validation import _process_inputs

    @functools.wraps(func)
    def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        if metadata.deprecated:
            warnings.warn(
                f"Tool '{metadata.name}' is deprecated: {metadata.deprecated}",
                DeprecationWarning,
                stacklevel=2,
            )

        try:
            if metadata.validate_inputs or metadata.coerce_types:
                kwargs = _process_inputs(kwargs, metadata)

            return func(*args, **kwargs)

        except Exception as e:
            logger.error(f"Tool '{metadata.name}' failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "error_type": type(e).__name__,
                "tool": metadata.name,
            }

    return sync_wrapper  # type: ignore


def mcp_tool(
    name: str | None = None,
    description: str | None = None,
    category: str | None = None,
    tags: list[str] | None = None,
    framework: ToolFramework | str = ToolFramework.AUTO,
    schema: dict[str, Any] | None = None,
    validate_inputs: bool = True,
    coerce_types: bool = False,
    deprecated: str | None = None,
    version: str | None = None,
    **extra_annotations: Any,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator for registering functions as MCP tools with auto-schema generation.

    This decorator provides a unified interface for tool registration across multiple
    MCP frameworks. It automatically generates JSON schemas from type hints and handles
    both sync and async functions.

    Args:
        name: Tool name (defaults to function name with underscores)
        description: Tool description (extracted from docstring if not provided)
        category: Tool category for grouping (e.g., "code_analysis", "data")
        tags: Additional tags for tool discovery
        framework: Target framework (fastmcp, langchain, anthropic, custom, auto)
        schema: Explicit JSON schema (overrides auto-generation)
        validate_inputs: Enable input validation against schema
        coerce_types: Enable type coercion for inputs
        deprecated: Deprecation message (None if not deprecated)
        version: Tool version string
        **extra_annotations: Additional custom metadata

    Returns:
        Decorated function with __mcp_metadata__ attribute

    Examples:
        >>> @mcp_tool(name="analyze_code", category="code_analysis")
        ... async def analyze(file_path: str, depth: int = 1) -> dict:
        ...     '''Analyze code structure.'''
        ...     return {"analyzed": file_path, "depth": depth}

        >>> @mcp_tool(framework="langchain", tags=["ml"])
        ... def train_model(data: list[float], epochs: int = 10) -> dict:
        ...     return {"trained": True, "epochs": epochs}

        >>> @mcp_tool(deprecated="Use analyze_v2 instead", version="1.0")
        ... def old_analyze(path: str) -> dict:
        ...     return {}
    """
    from pheno.mcp.tools.decorators_validation import generate_schema_from_signature

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        tool_name = name or func.__name__
        tool_desc = description or _extract_description(func)

        tool_framework = (
            framework
            if isinstance(framework, ToolFramework)
            else ToolFramework(framework)
        )

        tool_schema = schema if schema else generate_schema_from_signature(func)

        annotations = {
            "category": category or "general",
            "tags": tags or [],
            **extra_annotations,
        }

        metadata = ToolMetadata(
            name=tool_name,
            description=tool_desc,
            schema=tool_schema,
            annotations=annotations,
            framework=tool_framework,
            validate_inputs=validate_inputs,
            coerce_types=coerce_types,
            deprecated=deprecated,
            version=version,
        )

        func.__mcp_metadata__ = metadata  # type: ignore

        if inspect.iscoroutinefunction(func):
            wrapper = _create_async_wrapper(func, metadata)
        else:
            wrapper = _create_sync_wrapper(func, metadata)

        wrapper.__mcp_metadata__ = metadata  # type: ignore
        wrapper.__wrapped__ = func  # type: ignore

        return wrapper  # type: ignore

    return decorator
