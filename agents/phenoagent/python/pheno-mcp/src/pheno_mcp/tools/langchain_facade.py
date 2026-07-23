import inspect
from typing import Callable, Any, Optional
from pydantic import create_model, Field

try:
    from langchain_core.tools import StructuredTool
    LANGCHAIN_AVAILABLE = True
except ImportError:
    StructuredTool = Any
    LANGCHAIN_AVAILABLE = False

from .decorators import ToolMetadata

def mcp_to_langchain_tool(func: Callable) -> Optional[StructuredTool]:
    """Convert an MCP decorated tool into a LangChain StructuredTool."""
    if not LANGCHAIN_AVAILABLE:
        raise ImportError("langchain-core is not installed.")

    if not hasattr(func, "__mcp_metadata__"):
        raise ValueError("Function must be decorated with @mcp_tool")

    metadata: ToolMetadata = func.__mcp_metadata__

    schema = metadata.schema
    properties = schema.get("properties", {})
    required = schema.get("required", [])

    fields = {}
    for name, prop in properties.items():
        type_mapping = {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool,
            "array": list,
            "object": dict
        }
        py_type = type_mapping.get(prop.get("type"), Any)
        if name not in required:
            py_type = Optional[py_type]
            fields[name] = (py_type, Field(default=None, description=prop.get("description", "")))
        else:
            fields[name] = (py_type, Field(..., description=prop.get("description", "")))

    ArgsModel = create_model(f"{metadata.name}Args", **fields)

    is_coro = inspect.iscoroutinefunction(func)

    return StructuredTool.from_function(
        func=func if not is_coro else None,
        coroutine=func if is_coro else None,
        name=metadata.name,
        description=metadata.description,
        args_schema=ArgsModel,
    )
