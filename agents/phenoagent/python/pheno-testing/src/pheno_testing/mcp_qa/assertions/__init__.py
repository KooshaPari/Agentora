"""
MCP-QA Assertions - MCP-Specific Assertion Helpers

Provides assertion utilities for MCP testing:
- Tool response assertions
- Resource availability assertions
- Prompt validation assertions
- Schema validation
- Performance assertions
"""

from pheno.testing.mcp_qa.assertions.performance import (
    assert_memory_usage,
    assert_response_time,
    assert_throughput,
)
from pheno.testing.mcp_qa.assertions.prompts import (
    assert_prompt_arguments,
    assert_prompt_schema,
    assert_prompt_valid,
)
from pheno.testing.mcp_qa.assertions.resources import (
    assert_resource_available,
    assert_resource_content,
    assert_resource_schema,
)
from pheno.testing.mcp_qa.assertions.tools import (
    assert_tool_error,
    assert_tool_response,
    assert_tool_schema,
    assert_tool_success,
)

__all__ = [
    # Tool assertions
    "assert_tool_response",
    "assert_tool_success",
    "assert_tool_error",
    "assert_tool_schema",
    # Resource assertions
    "assert_resource_available",
    "assert_resource_schema",
    "assert_resource_content",
    # Prompt assertions
    "assert_prompt_valid",
    "assert_prompt_schema",
    "assert_prompt_arguments",
    # Performance assertions
    "assert_response_time",
    "assert_memory_usage",
    "assert_throughput",
]
