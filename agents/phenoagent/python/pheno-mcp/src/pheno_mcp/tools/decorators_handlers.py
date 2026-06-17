"""Framework adapters and registry conversion for MCP tools.

This module provides:
    - Registry format conversion
    - FastMCP, LangChain, Anthropic adapters
    - Utility decorators (deprecated, requires_version)
"""

from __future__ import annotations

import functools
import inspect
import warnings
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from pheno.mcp.tools.decorators_core import ToolMetadata

# Configure logger
logger = logging.getLogger(__name__)


def convert_to_registry_format(func: Callable) -> dict[str, Any]:
    """Convert MCP decorated function to registry format.

    Extracts metadata from decorated function and formats it for use with
    existing tool registries.

    Args:
        func: Decorated function with __mcp_metadata__

    Returns:
        Registry entry dictionary

    Raises:
        ValueError: If function is not decorated with @mcp_tool

    Examples:
        >>> @mcp_tool(name="example")
        ... async def example_tool(arg: str) -> dict:
        ...     return {"result": arg}
        >>> entry = convert_to_registry_format(example_tool)
        >>> entry["description"]
        ''
    """
    if not hasattr(func, "__mcp_metadata__"):
        raise ValueError("Function must be decorated with @mcp_tool")

    metadata: ToolMetadata = func.__mcp_metadata__  # type: ignore

    return {
        "function": func,
        "description": metadata.description,
        "input_schema": metadata.schema,
        "annotations": metadata.annotations,
        "framework": metadata.framework.value,
        "version": metadata.version,
        "deprecated": metadata.deprecated,
    }


def register_mcp_tools(*decorated_funcs: Callable) -> dict[str, dict[str, Any]]:
    """Register multiple MCP decorated functions into registry format.

    Args:
        *decorated_funcs: Functions decorated with @mcp_tool

    Returns:
        Dictionary in tools registry format

    Examples:
        >>> @mcp_tool(name="tool1")
        ... async def tool1(x: str): pass
        >>> @mcp_tool(name="tool2")
        ... async def tool2(y: int): pass
        >>> registry = register_mcp_tools(tool1, tool2)
        >>> len(registry)
        2
    """
    registry = {}

    for func in decorated_funcs:
        if not hasattr(func, "__mcp_metadata__"):
            logger.warning(f"Function {func.__name__} is not decorated, skipping")
            continue

        metadata: ToolMetadata = func.__mcp_metadata__  # type: ignore
        registry[metadata.name] = convert_to_registry_format(func)

    logger.info(f"Registered {len(registry)} MCP tools")
    return registry


def to_fastmcp_tool(func: Callable) -> dict[str, Any]:
    """Convert decorated function to FastMCP tool format.

    Args:
        func: Decorated function

    Returns:
        FastMCP tool dictionary

    Raises:
        ValueError: If function is not decorated
    """
    if not hasattr(func, "__mcp_metadata__"):
        raise ValueError("Function must be decorated with @mcp_tool")

    metadata: ToolMetadata = func.__mcp_metadata__  # type: ignore

    return {
        "name": metadata.name,
        "description": metadata.description,
        "input_schema": metadata.schema,
        "function": func,
    }


def to_langchain_tool(func: Callable) -> dict[str, Any]:
    """Convert decorated function to LangChain tool format.

    Args:
        func: Decorated function

    Returns:
        LangChain tool dictionary

    Raises:
        ValueError: If function is not decorated
    """
    if not hasattr(func, "__mcp_metadata__"):
        raise ValueError("Function must be decorated with @mcp_tool")

    metadata: ToolMetadata = func.__mcp_metadata__  # type: ignore

    return {
        "name": metadata.name,
        "description": metadata.description,
        "args_schema": metadata.schema,
        "func": func,
        "coroutine": inspect.iscoroutinefunction(func),
    }


def to_anthropic_tool(func: Callable) -> dict[str, Any]:
    """Convert decorated function to Anthropic tool format.

    Args:
        func: Decorated function

    Returns:
        Anthropic tool dictionary

    Raises:
        ValueError: If function is not decorated
    """
    if not hasattr(func, "__mcp_metadata__"):
        raise ValueError("Function must be decorated with @mcp_tool")

    metadata: ToolMetadata = func.__mcp_metadata__  # type: ignore

    return {
        "name": metadata.name,
        "description": metadata.description,
        "input_schema": metadata.schema,
    }


def deprecated(message: str, version: str | None = None) -> Callable:
    """Mark a tool as deprecated.

    Args:
        message: Deprecation message
        version: Version when tool will be removed

    Returns:
        Decorator function

    Examples:
        >>> @deprecated("Use new_tool instead", version="2.0")
        ... @mcp_tool()
        ... def old_tool(): pass
    """
    from pheno.mcp.tools.decorators_core import ToolMetadata

    def decorator(func: Callable) -> Callable:
        if hasattr(func, "__mcp_metadata__"):
            metadata: ToolMetadata = func.__mcp_metadata__  # type: ignore
            metadata.deprecated = message
            if version:
                metadata.version = version

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            warnings.warn(
                f"{func.__name__} is deprecated: {message}",
                DeprecationWarning,
                stacklevel=2,
            )
            return func(*args, **kwargs)

        return wrapper

    return decorator


def requires_version(min_version: str) -> Callable:
    """Decorator to specify minimum framework version requirement.

    Args:
        min_version: Minimum version string (e.g., "2.0", "1.5.0")

    Returns:
        Decorator function

    Examples:
        >>> @requires_version("2.0")
        ... @mcp_tool()
        ... def new_feature_tool(): pass
    """
    from pheno.mcp.tools.decorators_core import ToolMetadata

    def decorator(func: Callable) -> Callable:
        if hasattr(func, "__mcp_metadata__"):
            metadata: ToolMetadata = func.__mcp_metadata__  # type: ignore
            if not metadata.annotations:
                metadata.annotations = {}
            metadata.annotations["min_version"] = min_version

        return func

    return decorator
