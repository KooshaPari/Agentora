"""Input validation and schema generation for MCP tools.

This module provides:
    - JSON schema generation from Python type hints
    - Input validation against schemas
    - Type coercion for string inputs
    - Pydantic model support
"""

from __future__ import annotations

import inspect
import json
import logging
from typing import Any, get_args, get_origin, get_type_hints

# Optional Pydantic support
try:
    from pydantic import BaseModel

    PYDANTIC_AVAILABLE = True
except ImportError:
    BaseModel = object  # type: ignore
    PYDANTIC_AVAILABLE = False

logger = logging.getLogger(__name__)


def _process_inputs(
    inputs: dict[str, Any],
    metadata: Any,
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

    if metadata.coerce_types:
        inputs = coerce_types(inputs, schema)

    if metadata.validate_inputs:
        is_valid, error = validate_tool_input(inputs, schema)
        if not is_valid:
            raise ValueError(f"Input validation failed: {error}")

    return inputs


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
        if f"{param_name}:" in line:
            return line.split(":", 1)[1].strip()

        if f":param {param_name}:" in line:
            return line.split(":", 2)[2].strip()

    return None


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
    if python_type == inspect.Parameter.empty:
        return "string", {}

    origin = get_origin(python_type)
    args = get_args(python_type)

    if origin is type(None) or python_type is type(None):
        return "null", {}

    if origin is not None:
        if origin is list:
            if args:
                item_type, item_props = python_type_to_schema_type(args[0])
                return "array", {"items": {"type": item_type, **item_props}}
            return "array", {"items": {"type": "string"}}

        if origin is dict:
            if len(args) >= 2:
                value_type, value_props = python_type_to_schema_type(args[1])
                return "object", {
                    "additionalProperties": {"type": value_type, **value_props},
                }
            return "object", {}

        if origin is tuple:
            if args:
                items = []
                for arg in args:
                    item_type, item_props = python_type_to_schema_type(arg)
                    items.append({"type": item_type, **item_props})
                return "array", {
                    "items": items,
                    "minItems": len(items),
                    "maxItems": len(items),
                }
            return "array", {}

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

    logger.warning(f"Unknown type {python_type}, defaulting to string")
    return "string", {}


def generate_schema_from_signature(func: callable) -> dict[str, Any]:
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
        if param_name in ("self", "cls"):
            continue

        param_type = type_hints.get(param_name, param.annotation)

        schema_type, schema_props = python_type_to_schema_type(param_type)

        prop_def: dict[str, Any] = {"type": schema_type}
        prop_def.update(schema_props)

        if func.__doc__:
            param_desc = _extract_param_description(func.__doc__, param_name)
            if param_desc:
                prop_def["description"] = param_desc
            else:
                prop_def["description"] = f"Parameter {param_name}"

        if param.default is not inspect.Parameter.empty:
            if param.default is not None:
                prop_def["default"] = param.default
        else:
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
        raise ImportError(
            "Pydantic is not installed. Install with: pip install pydantic",
        )

    if not (isinstance(model, type) and issubclass(model, BaseModel)):
        raise TypeError(f"Expected Pydantic model, got {type(model)}")

    return model.model_json_schema()


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

    for field in required:
        if field not in inputs:
            return False, f"Required field '{field}' is missing"

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
        return True

    return isinstance(value, expected_py_type)


def _coerce_value(value: Any, schema_type: str) -> Any:
    """Coerce a value to match schema type.

    Args:
        value: Value to coerce
        schema_type: Target JSON schema type

    Returns:
        Coerced value
    """
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
                return json.loads(value)
            return list(value)
        if schema_type == "object":
            if isinstance(value, str):
                return json.loads(value)
            return dict(value)
    except (ValueError, TypeError) as e:
        logger.warning(f"Failed to coerce {value} to {schema_type}: {e}")
        return value

    return value
