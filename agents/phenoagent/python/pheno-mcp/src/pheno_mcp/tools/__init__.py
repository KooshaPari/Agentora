"""MCP Tools - Generic tool decorators and utilities.

This module provides framework-agnostic decorators for tool registration
across multiple MCP frameworks (FastMCP, LangChain, Anthropic, Custom).

Quick Start:
    >>> from pheno.mcp.tools import mcp_tool
    >>>
    >>> @mcp_tool(category="analysis", tags=["code"])
    ... async def analyze_code(file_path: str, depth: int = 1) -> dict:
    ...     '''Analyze code structure.'''
    ...     return {"analyzed": file_path, "depth": depth}

Features:
    - Auto-schema generation from type hints
    - Input validation with type coercion
    - Multi-framework support (FastMCP, LangChain, Anthropic)
    - Async/sync function support
    - Deprecation handling
    - Zero external dependencies (except optional Pydantic)

See Also:
    docs/mcp/tool_decorators.md - Comprehensive documentation
"""

from pheno.mcp.tools.decorators_core import (  # Main decorator; Metadata classes
    ToolFramework,
    ToolMetadata,
    mcp_tool,
)
from pheno.mcp.tools.decorators_handlers import (  # Registry conversion; Framework adapters; Utility decorators
    convert_to_registry_format,
    deprecated,
    register_mcp_tools,
    requires_version,
    to_anthropic_tool,
    to_fastmcp_tool,
    to_langchain_tool,
)
from pheno.mcp.tools.decorators_validation import (  # Schema generation; Validation
    coerce_types,
    generate_schema_from_pydantic,
    generate_schema_from_signature,
    python_type_to_schema_type,
    validate_tool_input,
)

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

__version__ = "1.0.0"
