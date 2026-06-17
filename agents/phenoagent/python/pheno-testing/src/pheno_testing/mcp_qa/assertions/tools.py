"""
Tool-specific assertions for MCP testing.
"""

from typing import Any, Dict, List, Optional


def assert_tool_response(
    response: Dict[str, Any],
    expected_keys: Optional[List[str]] = None,
    success: bool = True,
    error_contains: Optional[str] = None,
):
    """Assert tool response meets expectations.

    Args:
        response: Tool response dict
        expected_keys: Keys that must be present in response
        success: Expected success status
        error_contains: String that should be in error message (if any)

    Raises:
        AssertionError: If response doesn't meet expectations

    Usage:
        result = await mcp_client.call_tool("chat", {"prompt": "test"})
        assert_tool_response(
            result,
            expected_keys=["response", "model"],
            success=True
        )
    """
    assert isinstance(response, dict), f"Response must be dict, got {type(response)}"

    # Check success status
    assert response.get("success") == success, (
        f"Expected success={success}, got {response.get('success')}\n" f"Response: {response}"
    )

    # Check expected keys
    if expected_keys:
        missing_keys = [k for k in expected_keys if k not in response]
        assert not missing_keys, (
            f"Missing expected keys: {missing_keys}\n" f"Response keys: {list(response.keys())}"
        )

    # Check error message
    if error_contains:
        error = response.get("error", "")
        assert error_contains in str(error), (
            f"Expected error to contain '{error_contains}'\n" f"Got: {error}"
        )


def assert_tool_success(
    response: Dict[str, Any],
    expected_data: Optional[Dict[str, Any]] = None,
):
    """Assert tool call succeeded and optionally check data.

    Args:
        response: Tool response dict
        expected_data: Expected data in response (partial match)

    Raises:
        AssertionError: If tool call failed or data doesn't match

    Usage:
        result = await mcp_client.call_tool("entity", {
            "operation": "create",
            "data": {"name": "Test"}
        })
        assert_tool_success(result, expected_data={"name": "Test"})
    """
    assert response.get("success"), (
        f"Tool call failed\n" f"Error: {response.get('error')}\n" f"Response: {response}"
    )

    # Check expected data
    if expected_data:
        for key, expected_value in expected_data.items():
            actual_value = response.get(key)
            assert actual_value == expected_value, (
                f"Expected {key}={expected_value}, got {actual_value}\n" f"Response: {response}"
            )


def assert_tool_error(
    response: Dict[str, Any],
    error_message: Optional[str] = None,
    error_code: Optional[str] = None,
):
    """Assert tool call failed with expected error.

    Args:
        response: Tool response dict
        error_message: Expected substring in error message
        error_code: Expected error code

    Raises:
        AssertionError: If tool succeeded or error doesn't match

    Usage:
        result = await mcp_client.call_tool("entity", {
            "operation": "invalid"
        })
        assert_tool_error(result, error_message="Invalid operation")
    """
    assert not response.get("success"), (
        f"Expected tool to fail, but it succeeded\n" f"Response: {response}"
    )

    error = response.get("error", "")

    # Check error message
    if error_message:
        assert error_message in str(error), (
            f"Expected error to contain '{error_message}'\n" f"Got: {error}"
        )

    # Check error code
    if error_code:
        actual_code = response.get("error_code")
        assert actual_code == error_code, (
            f"Expected error_code={error_code}, got {actual_code}\n" f"Error: {error}"
        )


def assert_tool_schema(
    response: Dict[str, Any],
    schema: Dict[str, type],
    strict: bool = False,
):
    """Assert tool response matches expected schema.

    Args:
        response: Tool response dict
        schema: Dict mapping field names to expected types
        strict: If True, response must not have extra fields

    Raises:
        AssertionError: If response doesn't match schema

    Usage:
        result = await mcp_client.call_tool("listmodels", {})
        assert_tool_schema(result, {
            "success": bool,
            "models": list,
            "provider": str,
        })
    """
    # Check all schema fields
    for field, expected_type in schema.items():
        assert field in response, (
            f"Missing required field: {field}\n" f"Response keys: {list(response.keys())}"
        )

        actual_value = response[field]
        assert isinstance(actual_value, expected_type), (
            f"Field '{field}' has wrong type\n"
            f"Expected: {expected_type.__name__}\n"
            f"Got: {type(actual_value).__name__}\n"
            f"Value: {actual_value}"
        )

    # Check for extra fields in strict mode
    if strict:
        extra_fields = set(response.keys()) - set(schema.keys())
        assert not extra_fields, (
            f"Unexpected fields in response: {extra_fields}\n"
            f"Expected only: {list(schema.keys())}"
        )


def assert_list_response(
    response: Dict[str, Any],
    min_items: Optional[int] = None,
    max_items: Optional[int] = None,
    item_schema: Optional[Dict[str, type]] = None,
):
    """Assert list-based tool response.

    Args:
        response: Tool response dict
        min_items: Minimum number of items expected
        max_items: Maximum number of items expected
        item_schema: Schema for each item in the list

    Usage:
        result = await mcp_client.call_tool("entity", {
            "operation": "list"
        })
        assert_list_response(
            result,
            min_items=0,
            item_schema={"id": str, "name": str}
        )
    """
    assert_tool_success(response)

    # Find the list field (usually "items", "results", "data", etc.)
    list_fields = ["items", "results", "data", "entities", "list"]
    items = None

    for field in list_fields:
        if field in response:
            items = response[field]
            break

    assert items is not None, (
        f"No list field found in response\n"
        f"Looked for: {list_fields}\n"
        f"Response keys: {list(response.keys())}"
    )

    assert isinstance(items, list), f"Items field is not a list: {type(items)}"

    # Check item count
    if min_items is not None:
        assert len(items) >= min_items, f"Expected at least {min_items} items, got {len(items)}"

    if max_items is not None:
        assert len(items) <= max_items, f"Expected at most {max_items} items, got {len(items)}"

    # Check item schema
    if item_schema and items:
        for i, item in enumerate(items):
            try:
                assert_tool_schema(item, item_schema)
            except AssertionError as e:
                raise AssertionError(f"Item {i} failed schema validation:\n{e}")
