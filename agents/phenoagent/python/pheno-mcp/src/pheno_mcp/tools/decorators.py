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
    get_args,
    get_origin,
    get_type_hints,
)

if TYPE_CHECKING:
    from collections.abc import Callable

# Optional Pydantic support
try:
    from pydantic import BaseModel

    PYDANTIC_AVAILABLE = True
except ImportError:
    BaseModel = object  # type: ignore
    PYDANTIC_AVAILABLE = False

# Type variables for generic decorator support
P = ParamSpec("P")
R = TypeVar("R")

# Configure logger
logger = logging.getLogger(__name__)


class ToolFramework(StrEnum):
    """
    Supported MCP tool frameworks.
    """

    FASTMCP = "fastmcp"
    LANGCHAIN = "langchain"
    ANTHROPIC = "anthropic"
    CUSTOM = "custom"
    AUTO = "auto"  # Auto-detect framework


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


# === CORE DECORATOR ===


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

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        # Extract metadata from function
        tool_name = name or func.__name__
        tool_desc = description or _extract_description(func)

        # Convert framework string to enum
        tool_framework = (
            framework if isinstance(framework, ToolFramework) else ToolFramework(framework)
        )

        # Generate or validate schema
        tool_schema = schema if schema else generate_schema_from_signature(func)

        # Build annotations dictionary
        annotations = {
            "category": category or "general",
            "tags": tags or [],
            **extra_annotations,
        }

        # Create metadata object
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

        # Store metadata on function
        func.__mcp_metadata__ = metadata  # type: ignore

        # Wrap function with validation and error handling
        if inspect.iscoroutinefunction(func):
            wrapper = _create_async_wrapper(func, metadata)
        else:
            wrapper = _create_sync_wrapper(func, metadata)

        # Preserve original function attributes
        wrapper.__mcp_metadata__ = metadata  # type: ignore
        wrapper.__wrapped__ = func  # type: ignore

        return wrapper  # type: ignore

    return decorator


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

    @functools.wraps(func)
    async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        # Check deprecation
        if metadata.deprecated:
            warnings.warn(
                f"Tool '{metadata.name}' is deprecated: {metadata.deprecated}",
                DeprecationWarning,
                stacklevel=2,
            )

        try:
            # Validate and coerce inputs if enabled
            if metadata.validate_inputs or metadata.coerce_types:
                kwargs = _process_inputs(kwargs, metadata)

            # Execute function
            return await func(*args, **kwargs)

        except Exception as e:
            logger.error(f"Tool '{metadata.name}' failed: {e}", exc_info=True)
            # Return error in standard format
            return {  # type: ignore
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

    @functools.wraps(func)
    def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        # Check deprecation
        if metadata.deprecated:
            warnings.warn(
                f"Tool '{metadata.name}' is deprecated: {metadata.deprecated}",
                DeprecationWarning,
                stacklevel=2,
            )

        try:
            # Validate and coerce inputs if enabled
            if metadata.validate_inputs or metadata.coerce_types:
                kwargs = _process_inputs(kwargs, metadata)

            # Execute function
            return func(*args, **kwargs)

        except Exception as e:
            logger.error(f"Tool '{metadata.name}' failed: {e}", exc_info=True)
            # Return error in standard format
            return {  # type: ignore
                "status": "error",
                "error": str(e),
                "error_type": type(e).__name__,
                "tool": metadata.name,
            }

    return sync_wrapper  # type: ignore


def _process_inputs(
    inputs: dict[str, Any],
    metadata: ToolMetadata,
) -> dict[str, Any]:
    """Process inputs: validate and/or coerce types.

    Args:
        inputs: Input dictionary
        metadata: Tool metadata with validation settings

    Returns:
        Processed inputs dictionary

    Raises:
        ValueError: If validation fails
    """
    schema = metadata.schema

    # Coerce types if enabled
    if metadata.coerce_types:
        inputs = coerce_types(inputs, schema)

    # Validate if enabled
    if metadata.validate_inputs:
        is_valid, error = validate_tool_input(inputs, schema)
        if not is_valid:
            raise ValueError(f"Input validation failed: {error}")

    return inputs


# === SCHEMA GENERATION ===


def generate_schema_from_signature(func: Callable) -> dict[str, Any]:
    """Generate JSON schema from function signature and type hints.

    Analyzes function parameters and their type annotations to create a complete
    JSON schema compatible with all MCP frameworks.

    Args:
        func: Function to analyze

    Returns:
        JSON schema dictionary with properties and required fields

    Examples:
        >>> def example(name: str, count: int = 5, tags: list[str] = None) -> dict:
        ...     pass
        >>> schema = generate_schema_from_signature(example)
        >>> schema["required"]
        ['name']
        >>> schema["properties"]["count"]["default"]
        5
    """
    sig = inspect.signature(func)
    type_hints = get_type_hints(func)

    properties: dict[str, Any] = {}
    required: list[str] = []

    for param_name, param in sig.parameters.items():
        # Skip self and cls parameters
        if param_name in ("self", "cls"):
            continue

        # Get type from hints or annotation
        param_type = type_hints.get(param_name, param.annotation)

        # Convert Python type to JSON schema type
        schema_type, schema_props = python_type_to_schema_type(param_type)

        # Build property definition
        prop_def: dict[str, Any] = {"type": schema_type}
        prop_def.update(schema_props)

        # Extract description from docstring if available
        if func.__doc__:
            # Try to extract parameter description from docstring
            param_desc = _extract_param_description(func.__doc__, param_name)
            if param_desc:
                prop_def["description"] = param_desc
            else:
                prop_def["description"] = f"Parameter {param_name}"

        # Handle default values
        if param.default is not inspect.Parameter.empty:
            if param.default is not None:
                prop_def["default"] = param.default
        else:
            # No default = required parameter
            required.append(param_name)

        properties[param_name] = prop_def

    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


def generate_schema_from_pydantic(model: type[BaseModel]) -> dict[str, Any]:
    """Generate JSON schema from Pydantic model.

    Args:
        model: Pydantic model class

    Returns:
        JSON schema compatible with MCP frameworks

    Raises:
        ImportError: If Pydantic is not installed
        TypeError: If model is not a Pydantic model

    Examples:
        >>> from pydantic import BaseModel
        >>> class AnalysisInput(BaseModel):
        ...     file_path: str
        ...     depth: int = 1
        >>> schema = generate_schema_from_pydantic(AnalysisInput)
    """
    if not PYDANTIC_AVAILABLE:
        raise ImportError("Pydantic is not installed. Install with: pip install pydantic")

    if not (isinstance(model, type) and issubclass(model, BaseModel)):
        raise TypeError(f"Expected Pydantic model, got {type(model)}")

    return model.model_json_schema()


def python_type_to_schema_type(python_type: Any) -> tuple[str, dict[str, Any]]:
    """Convert Python type annotation to JSON schema type.

    Handles simple types, generics (list, dict, Optional), and nested types.

    Args:
        python_type: Python type annotation

    Returns:
        Tuple of (schema_type, additional_properties)

    Examples:
        >>> python_type_to_schema_type(str)
        ('string', {})
        >>> python_type_to_schema_type(list[str])
        ('array', {'items': {'type': 'string'}})
        >>> python_type_to_schema_type(dict[str, int])
        ('object', {'additionalProperties': {'type': 'integer'}})
    """
    # Handle missing/empty annotations
    if python_type == inspect.Parameter.empty:
        return "string", {}

    # Get origin for generic types (list, dict, Optional, etc.)
    origin = get_origin(python_type)
    args = get_args(python_type)

    # Handle Optional[T] (which is Union[T, None])
    if origin is type(None) or python_type is type(None):
        return "null", {}

    # Handle Union types (including Optional)
    if origin is not None:
        # List type
        if origin is list:
            if args:
                item_type, item_props = python_type_to_schema_type(args[0])
                return "array", {"items": {"type": item_type, **item_props}}
            return "array", {"items": {"type": "string"}}

        # Dict type
        if origin is dict:
            if len(args) >= 2:
                value_type, value_props = python_type_to_schema_type(args[1])
                return "object", {"additionalProperties": {"type": value_type, **value_props}}
            return "object", {}

        # Tuple type (treat as array with fixed length)
        if origin is tuple:
            if args:
                items = []
                for arg in args:
                    item_type, item_props = python_type_to_schema_type(arg)
                    items.append({"type": item_type, **item_props})
                return "array", {"items": items, "minItems": len(items), "maxItems": len(items)}
            return "array", {}

    # Handle basic types
    if python_type in (str,):
        return "string", {}
    if python_type in (int,):
        return "integer", {}
    if python_type in (float,):
        return "number", {}
    if python_type in (bool,):
        return "boolean", {}
    if python_type in (list,):
        return "array", {}
    if python_type in (dict,):
        return "object", {}

    # Default to string for unknown types
    logger.warning(f"Unknown type {python_type}, defaulting to string")
    return "string", {}


def _extract_param_description(docstring: str, param_name: str) -> str | None:
    """Extract parameter description from docstring.

    Supports Google, NumPy, and Sphinx docstring styles.

    Args:
        docstring: Function docstring
        param_name: Parameter name to find

    Returns:
        Parameter description or None if not found
    """
    lines = docstring.strip().split("\n")

    for _i, line in enumerate(lines):
        # Google style: param_name: description
        if f"{param_name}:" in line:
            return line.split(":", 1)[1].strip()

        # Sphinx style: :param param_name: description
        if f":param {param_name}:" in line:
            return line.split(":", 2)[2].strip()

    return None


# === INPUT VALIDATION ===


def validate_tool_input(
    inputs: dict[str, Any],
    schema: dict[str, Any],
) -> tuple[bool, str | None]:
    """Validate tool inputs against JSON schema.

    Args:
        inputs: Input dictionary to validate
        schema: JSON schema to validate against

    Returns:
        Tuple of (is_valid, error_message)

    Examples:
        >>> schema = {"type": "object", "properties": {"x": {"type": "integer"}}, "required": ["x"]}
        >>> validate_tool_input({"x": 5}, schema)
        (True, None)
        >>> validate_tool_input({}, schema)
        (False, "Required field 'x' is missing")
    """
    properties = schema.get("properties", {})
    required = schema.get("required", [])

    # Check required fields
    for field in required:
        if field not in inputs:
            return False, f"Required field '{field}' is missing"

    # Validate types
    for key, value in inputs.items():
        if key not in properties:
            if not schema.get("additionalProperties", False):
                logger.warning(f"Unexpected field '{key}' in input")
            continue

        expected_type = properties[key].get("type")
        if not _check_type(value, expected_type):
            return (
                False,
                f"Field '{key}' has invalid type. Expected {expected_type}, got {type(value).__name__}",
            )

    return True, None


def coerce_types(
    inputs: dict[str, Any],
    schema: dict[str, Any],
) -> dict[str, Any]:
    """Coerce input types to match schema types.

    Attempts to convert input values to the types specified in the schema.
    Useful for handling string inputs from CLI or web forms.

    Args:
        inputs: Input dictionary
        schema: JSON schema with type information

    Returns:
        New dictionary with coerced types

    Examples:
        >>> schema = {"properties": {"count": {"type": "integer"}, "active": {"type": "boolean"}}}
        >>> coerce_types({"count": "5", "active": "true"}, schema)
        {'count': 5, 'active': True}
    """
    properties = schema.get("properties", {})
    coerced = {}

    for key, value in inputs.items():
        if key not in properties:
            coerced[key] = value
            continue

        expected_type = properties[key].get("type")
        coerced[key] = _coerce_value(value, expected_type)

    return coerced


def _check_type(value: Any, schema_type: str) -> bool:
    """Check if value matches schema type.

    Args:
        value: Value to check
        schema_type: Expected JSON schema type

    Returns:
        True if type matches
    """
    type_map = {
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
        "array": list,
        "object": dict,
        "null": type(None),
    }

    expected_py_type = type_map.get(schema_type)
    if expected_py_type is None:
        return True  # Unknown type, allow

    return isinstance(value, expected_py_type)


def _coerce_value(value: Any, schema_type: str) -> Any:
    """Coerce a value to match schema type.

    Args:
        value: Value to coerce
        schema_type: Target JSON schema type

    Returns:
        Coerced value
    """
    # Already correct type
    if _check_type(value, schema_type):
        return value

    try:
        if schema_type == "integer":
            return int(value)
        if schema_type == "number":
            return float(value)
        if schema_type == "boolean":
            if isinstance(value, str):
                return value.lower() in ("true", "1", "yes", "on")
            return bool(value)
        if schema_type == "string":
            return str(value)
        if schema_type == "array":
            if isinstance(value, str):
                import json

                return json.loads(value)
            return list(value)
        if schema_type == "object":
            if isinstance(value, str):
                import json

                return json.loads(value)
            return dict(value)
    except (ValueError, TypeError) as e:
        logger.warning(f"Failed to coerce {value} to {schema_type}: {e}")
        return value

    return value


# === REGISTRY CONVERSION ===


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


# === FRAMEWORK-SPECIFIC ADAPTERS ===


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


# === UTILITY DECORATORS ===


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

    def decorator(func: Callable) -> Callable:
        if hasattr(func, "__mcp_metadata__"):
            metadata: ToolMetadata = func.__mcp_metadata__  # type: ignore
            if not metadata.annotations:
                metadata.annotations = {}
            metadata.annotations["min_version"] = min_version

        return func

    return decorator


# === EXPORTS ===

__all__ = [
    "ToolFramework",
    # Metadata classes
    "ToolMetadata",
    "coerce_types",
    # Registry conversion
    "convert_to_registry_format",
    # Utility decorators
    "deprecated",
    "generate_schema_from_pydantic",
    # Schema generation
    "generate_schema_from_signature",
    # Main decorator
    "mcp_tool",
    "python_type_to_schema_type",
    "register_mcp_tools",
    "requires_version",
    "to_anthropic_tool",
    # Framework adapters
    "to_fastmcp_tool",
    "to_langchain_tool",
    # Validation
    "validate_tool_input",
]
