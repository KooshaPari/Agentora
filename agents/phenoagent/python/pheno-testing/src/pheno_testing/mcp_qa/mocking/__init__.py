"""
MCP-QA Mocking - Mock MCP Servers and Tools

Provides:
- MockMCPServer for unit testing
- MockTool, MockResource, MockPrompt builders
- Response builders for common scenarios
"""

from pheno.testing.mcp_qa.mocking.builders import (
    build_error_response,
    build_list_response,
    build_success_response,
)
from pheno.testing.mcp_qa.mocking.prompts import MockPrompt
from pheno.testing.mcp_qa.mocking.resources import MockResource
from pheno.testing.mcp_qa.mocking.server import MockMCPServer
from pheno.testing.mcp_qa.mocking.tools import MockTool

__all__ = [
    "MockMCPServer",
    "MockTool",
    "MockResource",
    "MockPrompt",
    "build_success_response",
    "build_error_response",
    "build_list_response",
]
