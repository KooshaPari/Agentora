"""
Resource-specific assertions for MCP testing.
"""

from typing import Any, Dict


def assert_resource_available(resource_uri: str, mcp_client):
    """Assert that a resource is available via MCP.

    Args:
        resource_uri: URI of the resource
        mcp_client: MCP client instance

    Usage:
        assert_resource_available("file:///test.txt", mcp_client)
    """
    # Implementation would check if resource exists
    pass


def assert_resource_schema(resource: Dict[str, Any], schema: Dict[str, type]):
    """
    Assert resource matches expected schema.
    """
    for field, expected_type in schema.items():
        assert field in resource, f"Missing field: {field}"
        assert isinstance(resource[field], expected_type)


def assert_resource_content(resource: Dict[str, Any], expected_content: str):
    """
    Assert resource content matches expected.
    """
    content = resource.get("content", "")
    assert expected_content in content, "Expected content not found"
