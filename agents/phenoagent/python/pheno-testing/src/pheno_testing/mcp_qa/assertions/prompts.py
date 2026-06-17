"""
Prompt-specific assertions for MCP testing.
"""

from typing import Any, Dict, List, Optional


def assert_prompt_valid(prompt: Dict[str, Any]):
    """
    Assert prompt is valid.
    """
    assert "name" in prompt, "Prompt must have a name"
    assert "arguments" in prompt or "description" in prompt


def assert_prompt_schema(prompt: Dict[str, Any], schema: Dict[str, type]):
    """
    Assert prompt matches schema.
    """
    for field, expected_type in schema.items():
        assert field in prompt
        assert isinstance(prompt[field], expected_type)


def assert_prompt_arguments(
    prompt: Dict[str, Any], required_args: List[str], optional_args: Optional[List[str]] = None
):
    """
    Assert prompt has required/optional arguments.
    """
    args = prompt.get("arguments", [])
    arg_names = [arg.get("name") for arg in args]

    for req_arg in required_args:
        assert req_arg in arg_names, f"Missing required argument: {req_arg}"
