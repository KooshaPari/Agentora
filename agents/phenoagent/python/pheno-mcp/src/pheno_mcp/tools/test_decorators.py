"""Quick verification tests for tool decorators.

This is a simple smoke test file to verify the decorators work correctly. For
comprehensive testing, use the main test suite.
"""

import asyncio

from pheno.mcp.tools.decorators import (
    ToolFramework,
    coerce_types,
    generate_schema_from_signature,
    mcp_tool,
    register_mcp_tools,
    validate_tool_input,
)


# Test 1: Basic decorator
@mcp_tool(name="test_basic", category="test")
def basic_tool(x: str, y: int = 5) -> dict:
    """
    Test basic tool.
    """
    return {"x": x, "y": y}


# Test 2: Async tool
@mcp_tool(category="async_test")
async def async_tool(data: list[str]) -> dict:
    """
    Test async tool.
    """
    await asyncio.sleep(0.01)
    return {"count": len(data)}


# Test 3: Complex types
@mcp_tool(validate_inputs=True)
def complex_tool(items: list[dict[str, int]], config: dict[str, str] | None = None) -> dict:
    """
    Test complex types.
    """
    return {"items": len(items)}


# Test 4: Type coercion
@mcp_tool(validate_inputs=True, coerce_types=True)
def coercion_tool(count: int, active: bool = True) -> dict:
    """
    Test type coercion.
    """
    return {"count": count, "active": active}


def test_metadata():
    """
    Test metadata is attached.
    """
    assert hasattr(basic_tool, "__mcp_metadata__")
    metadata = basic_tool.__mcp_metadata__

    assert metadata.name == "test_basic"
    assert metadata.description == "Test basic tool."
    assert metadata.annotations["category"] == "test"
    assert metadata.framework == ToolFramework.AUTO

    print("✓ Metadata test passed")


def test_schema_generation():
    """
    Test schema generation.
    """
    schema = generate_schema_from_signature(basic_tool.__wrapped__)

    assert schema["type"] == "object"
    assert "x" in schema["properties"]
    assert "y" in schema["properties"]
    assert schema["properties"]["x"]["type"] == "string"
    assert schema["properties"]["y"]["type"] == "integer"
    assert schema["properties"]["y"]["default"] == 5
    assert schema["required"] == ["x"]

    print("✓ Schema generation test passed")


def test_validation():
    """
    Test input validation.
    """
    schema = {
        "type": "object",
        "properties": {"x": {"type": "integer"}, "y": {"type": "string"}},
        "required": ["x"],
    }

    # Valid input
    is_valid, error = validate_tool_input({"x": 5, "y": "test"}, schema)
    assert is_valid
    assert error is None

    # Missing required
    is_valid, error = validate_tool_input({"y": "test"}, schema)
    assert not is_valid
    assert "Required field 'x' is missing" in error

    # Wrong type
    is_valid, error = validate_tool_input({"x": "wrong", "y": "test"}, schema)
    assert not is_valid
    assert "invalid type" in error

    print("✓ Validation test passed")


def test_type_coercion():
    """
    Test type coercion.
    """
    schema = {
        "properties": {
            "count": {"type": "integer"},
            "active": {"type": "boolean"},
            "name": {"type": "string"},
        },
    }

    inputs = {"count": "42", "active": "true", "name": 123}
    coerced = coerce_types(inputs, schema)

    assert coerced["count"] == 42
    assert coerced["active"] is True
    assert coerced["name"] == "123"

    print("✓ Type coercion test passed")


def test_execution():
    """
    Test decorated function execution.
    """
    # Sync tool
    result = basic_tool(x="test", y=10)
    assert result["x"] == "test"
    assert result["y"] == 10

    print("✓ Sync execution test passed")


async def test_async_execution():
    """
    Test async decorated function execution.
    """
    result = await async_tool(data=["a", "b", "c"])
    assert result["count"] == 3

    print("✓ Async execution test passed")


def test_coercion_integration():
    """
    Test coercion in decorated function.
    """
    # Pass strings that will be coerced
    result = coercion_tool(count="42", active="false")
    assert result["count"] == 42
    assert result["active"] is False

    print("✓ Coercion integration test passed")


def test_registry():
    """
    Test registry conversion.
    """
    registry = register_mcp_tools(basic_tool, async_tool, complex_tool)

    assert len(registry) == 3
    assert "test_basic" in registry
    assert "async_tool" in registry
    assert "complex_tool" in registry

    entry = registry["test_basic"]
    assert "function" in entry
    assert "description" in entry
    assert "input_schema" in entry

    print("✓ Registry test passed")


def run_all_tests():
    """
    Run all tests.
    """
    print("\nRunning decorator tests...\n")

    test_metadata()
    test_schema_generation()
    test_validation()
    test_type_coercion()
    test_execution()
    test_coercion_integration()
    test_registry()

    # Run async test
    asyncio.run(test_async_execution())

    print("\n✓ All tests passed!\n")


if __name__ == "__main__":
    run_all_tests()
