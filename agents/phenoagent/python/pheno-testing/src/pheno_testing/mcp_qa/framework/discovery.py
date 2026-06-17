"""Test Discovery and Organization.

Provides utilities for:
- Discovering tests in a project
- Organizing tests by category, priority, tool
- Filtering tests based on criteria
- Generating test execution plans
"""

import importlib.util
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from pheno.testing.mcp_qa.framework.decorators import get_test_registry


def discover_tests(
    test_dir: str | Path,
    pattern: str = "test_*.py",
    recursive: bool = True,
) -> Dict[str, Dict[str, Any]]:
    """Discover all MCP tests in a directory.

    Args:
        test_dir: Directory to search for tests
        pattern: File name pattern to match
        recursive: Search subdirectories recursively

    Returns:
        Dict mapping test names to test metadata

    Usage:
        tests = discover_tests("tests/")
        print(f"Found {len(tests)} tests")

        for test_name, metadata in tests.items():
            print(f"  {test_name}: {metadata['tool_name']}")
    """
    test_dir = Path(test_dir)
    discovered_tests = {}

    # Find all test files
    if recursive:
        test_files = test_dir.rglob(pattern)
    else:
        test_files = test_dir.glob(pattern)

    for test_file in test_files:
        # Import test module to trigger decorator registration
        try:
            spec = importlib.util.spec_from_file_location(test_file.stem, test_file)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
        except Exception as e:
            print(f"Warning: Failed to import {test_file}: {e}")
            continue

    # Get all registered tests
    registry = get_test_registry()
    discovered_tests.update(registry.get_tests())

    return discovered_tests


def organize_tests(
    tests: Dict[str, Dict[str, Any]],
    group_by: str = "tool_name",
) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """Organize tests by a specific criterion.

    Args:
        tests: Dict of tests from discover_tests()
        group_by: Field to group by (tool_name, category, priority, etc.)

    Returns:
        Dict mapping group keys to test dicts

    Usage:
        tests = discover_tests("tests/")
        by_tool = organize_tests(tests, group_by="tool_name")

        for tool_name, tool_tests in by_tool.items():
            print(f"{tool_name}: {len(tool_tests)} tests")
    """
    organized = {}

    for test_name, test_data in tests.items():
        group_key = test_data.get(group_by, "unknown")

        if group_key not in organized:
            organized[group_key] = {}

        organized[group_key][test_name] = test_data

    return organized


def filter_tests(
    tests: Dict[str, Dict[str, Any]],
    category: Optional[str] = None,
    tool_name: Optional[str] = None,
    tags: Optional[List[str]] = None,
    priority_min: Optional[int] = None,
    priority_max: Optional[int] = None,
    requires_auth: Optional[bool] = None,
    custom_filter: Optional[Callable[[Dict[str, Any]], bool]] = None,
) -> Dict[str, Dict[str, Any]]:
    """Filter tests based on multiple criteria.

    Args:
        tests: Dict of tests to filter
        category: Filter by category
        tool_name: Filter by tool name
        tags: Filter by tags (match any)
        priority_min: Minimum priority
        priority_max: Maximum priority
        requires_auth: Filter by auth requirement
        custom_filter: Custom filter function

    Returns:
        Dict of filtered tests

    Usage:
        tests = discover_tests("tests/")

        # Get all high-priority chat tests
        chat_tests = filter_tests(
            tests,
            tool_name="chat",
            priority_min=8
        )

        # Get fast tests that don't require auth
        fast_tests = filter_tests(
            tests,
            tags=["fast"],
            requires_auth=False
        )

        # Custom filter
        long_tests = filter_tests(
            tests,
            custom_filter=lambda t: t["timeout_seconds"] > 60
        )
    """
    filtered = tests.copy()

    # Filter by category
    if category is not None:
        filtered = {k: v for k, v in filtered.items() if v.get("category") == category}

    # Filter by tool name
    if tool_name is not None:
        filtered = {k: v for k, v in filtered.items() if v.get("tool_name") == tool_name}

    # Filter by tags
    if tags is not None:
        filtered = {
            k: v for k, v in filtered.items() if any(tag in v.get("tags", []) for tag in tags)
        }

    # Filter by priority range
    if priority_min is not None:
        filtered = {k: v for k, v in filtered.items() if v.get("priority", 0) >= priority_min}

    if priority_max is not None:
        filtered = {k: v for k, v in filtered.items() if v.get("priority", 0) <= priority_max}

    # Filter by auth requirement
    if requires_auth is not None:
        filtered = {
            k: v for k, v in filtered.items() if v.get("requires_auth", False) == requires_auth
        }

    # Apply custom filter
    if custom_filter is not None:
        filtered = {k: v for k, v in filtered.items() if custom_filter(v)}

    return filtered


def generate_execution_plan(
    tests: Dict[str, Dict[str, Any]],
    strategy: str = "priority",
) -> List[str]:
    """Generate test execution plan.

    Args:
        tests: Dict of tests to plan
        strategy: Execution strategy
            - "priority": Run high-priority tests first
            - "fast_first": Run fast tests first
            - "alphabetical": Alphabetical order
            - "tool_grouped": Group by tool

    Returns:
        List of test names in execution order

    Usage:
        tests = discover_tests("tests/")
        plan = generate_execution_plan(tests, strategy="priority")

        print("Execution plan:")
        for i, test_name in enumerate(plan, 1):
            print(f"{i}. {test_name}")
    """
    if strategy == "priority":
        # Sort by priority (descending)
        sorted_tests = sorted(tests.items(), key=lambda x: x[1].get("priority", 0), reverse=True)
        return [name for name, _ in sorted_tests]

    elif strategy == "fast_first":
        # Sort by timeout (ascending)
        sorted_tests = sorted(tests.items(), key=lambda x: x[1].get("timeout_seconds", 30))
        return [name for name, _ in sorted_tests]

    elif strategy == "alphabetical":
        # Sort alphabetically
        return sorted(tests.keys())

    elif strategy == "tool_grouped":
        # Group by tool, then sort by priority within each group
        by_tool = organize_tests(tests, group_by="tool_name")
        plan = []

        for tool_name in sorted(by_tool.keys()):
            tool_tests = by_tool[tool_name]
            sorted_tool_tests = sorted(
                tool_tests.items(), key=lambda x: x[1].get("priority", 0), reverse=True
            )
            plan.extend([name for name, _ in sorted_tool_tests])

        return plan

    else:
        # Default: original order
        return list(tests.keys())


def get_test_stats(tests: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Get statistics about discovered tests.

    Args:
        tests: Dict of tests

    Returns:
        Dict with test statistics

    Usage:
        tests = discover_tests("tests/")
        stats = get_test_stats(tests)

        print(f"Total tests: {stats['total']}")
        print(f"By category: {stats['by_category']}")
        print(f"By tool: {stats['by_tool']}")
    """
    by_category = {}
    by_tool = {}
    by_priority = {}
    requires_auth_count = 0
    total_timeout = 0

    for test_data in tests.values():
        # Count by category
        category = test_data.get("category", "unknown")
        by_category[category] = by_category.get(category, 0) + 1

        # Count by tool
        tool = test_data.get("tool_name", "unknown")
        by_tool[tool] = by_tool.get(tool, 0) + 1

        # Count by priority
        priority = test_data.get("priority", 0)
        by_priority[priority] = by_priority.get(priority, 0) + 1

        # Count auth requirements
        if test_data.get("requires_auth", False):
            requires_auth_count += 1

        # Sum timeouts
        total_timeout += test_data.get("timeout_seconds", 30)

    return {
        "total": len(tests),
        "by_category": by_category,
        "by_tool": by_tool,
        "by_priority": by_priority,
        "requires_auth": requires_auth_count,
        "estimated_duration_seconds": total_timeout,
    }
