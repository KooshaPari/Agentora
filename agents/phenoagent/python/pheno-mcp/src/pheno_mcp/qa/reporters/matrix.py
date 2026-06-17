"""
Functionality Matrix Reporter - Comprehensive Feature Coverage.

Maps test results to:
- Tool capabilities and operations
- User stories and use cases
- Data items validated
- Assertions checked
- Known issues and workarounds

Provides comprehensive documentation of what each test validates.
"""

from pathlib import Path
from typing import Any


class FunctionalityMatrixReporter:
    """
    Functionality Matrix Reporter - Comprehensive Feature Coverage

    Maps test results to tool capabilities, user stories, data coverage,
    and test results with performance metrics.
    """

    # Default tool capabilities - can be overridden per instance
    DEFAULT_TOOL_CAPABILITIES = {
        "workspace_tool": {
            "description": "Workspace context management for organizing work",
            "operations": {
                "list_workspaces": {
                    "feature": "List all accessible workspaces",
                    "user_story": "As a user, I want to see all my workspaces",
                    "data_items": ["organizations", "projects", "documents"],
                    "assertions": ["Returns organization list", "Includes context"],
                },
                "get_context": {
                    "feature": "Get current workspace context",
                    "user_story": "As a user, I want to know my current context",
                    "data_items": ["active_organization", "active_project"],
                    "assertions": ["Returns current context"],
                },
                "set_context": {
                    "feature": "Set workspace context",
                    "user_story": "As a user, I want to switch workspaces",
                    "data_items": ["organization_id", "project_id"],
                    "assertions": ["Sets active context"],
                },
            },
        },
        "entity_tool": {
            "description": "CRUD operations for all entities",
            "operations": {
                "list": {
                    "feature": "List entities",
                    "user_story": "As a user, I want to browse entities",
                    "data_items": ["id", "name", "metadata"],
                    "assertions": ["Returns entity list", "Respects permissions"],
                },
                "create": {
                    "feature": "Create entity",
                    "user_story": "As a user, I want to create new entities",
                    "data_items": ["name", "attributes", "metadata"],
                    "assertions": ["Creates entity", "Validates data"],
                },
                "read": {
                    "feature": "Read entity by ID",
                    "user_story": "As a user, I want to view entity details",
                    "data_items": ["entity data", "metadata", "relationships"],
                    "assertions": ["Returns entity", "Includes relations"],
                },
                "update": {
                    "feature": "Update entity",
                    "user_story": "As a user, I want to modify entities",
                    "data_items": ["entity_id", "update_data"],
                    "assertions": ["Updates entity", "Validates data"],
                },
                "delete": {
                    "feature": "Delete entity",
                    "user_story": "As a user, I want to remove entities",
                    "data_items": ["entity_id"],
                    "assertions": ["Deletes entity", "Handles cascade"],
                },
            },
        },
        "query_tool": {
            "description": "Search and analytics across all entities",
            "operations": {
                "search": {
                    "feature": "Search entities",
                    "user_story": "As a user, I want to find entities",
                    "data_items": ["search_term", "results", "count"],
                    "assertions": ["Returns ranked results"],
                },
                "aggregate": {
                    "feature": "Aggregate statistics",
                    "user_story": "As a user, I want summary stats",
                    "data_items": ["aggregates", "counts", "summaries"],
                    "assertions": ["Returns aggregated data"],
                },
                "fuzzy_match": {
                    "feature": "Fuzzy search",
                    "user_story": "As a user, I want flexible search",
                    "data_items": ["search_term", "matches", "scores"],
                    "assertions": ["Returns ranked matches"],
                },
            },
        },
        "relationship_tool": {
            "description": "Manage relationships between entities",
            "operations": {
                "list": {
                    "feature": "List entity relationships",
                    "user_story": "As a user, I want to see connections",
                    "data_items": ["relationship_type", "source", "target"],
                    "assertions": ["Returns relationship list"],
                },
                "link": {
                    "feature": "Link entities",
                    "user_story": "As a user, I want to connect entities",
                    "data_items": ["source", "target", "type", "metadata"],
                    "assertions": ["Creates relationship"],
                },
                "unlink": {
                    "feature": "Unlink entities",
                    "user_story": "As a user, I want to remove connections",
                    "data_items": ["relationship_id"],
                    "assertions": ["Removes relationship"],
                },
            },
        },
        "workflow_tool": {
            "description": "Automated workflows and bulk operations",
            "operations": {
                "setup": {
                    "feature": "Automated setup",
                    "user_story": "As a user, I want quick setup",
                    "data_items": ["configuration", "template"],
                    "assertions": ["Completes setup", "Validates config"],
                },
                "import": {
                    "feature": "Import data",
                    "user_story": "As a user, I want to bulk import",
                    "data_items": ["source", "data", "mapping"],
                    "assertions": ["Imports data", "Validates format"],
                },
                "bulk_update": {
                    "feature": "Bulk update",
                    "user_story": "As a user, I want to update multiple items",
                    "data_items": ["entity_ids", "update_data"],
                    "assertions": ["Updates multiple entities"],
                },
            },
        },
    }

    def __init__(
        self,
        output_path: str,
        title: str = "MCP FUNCTIONALITY MATRIX",
        tool_capabilities: dict[str, Any] | None = None,
    ):
        """Initialize Functionality Matrix reporter.

        Args:
            output_path: Path to write matrix report file
            title: Report title (default: "MCP FUNCTIONALITY MATRIX")
            tool_capabilities: Custom tool capabilities mapping (uses defaults if None)
        """
        self.output_path = Path(output_path)
        self.title = title
        self.tool_capabilities = tool_capabilities or self.DEFAULT_TOOL_CAPABILITIES

    def report(self, results: list[dict[str, Any]], metadata: dict[str, Any]) -> None:
        """Generate comprehensive functionality matrix.

        Args:
            results: List of test result dictionaries
            metadata: Test run metadata

        The matrix report includes:
        - Tool descriptions and capabilities
        - Operation-level coverage
        - User stories and use cases
        - Test results mapped to operations
        - Known issues and workarounds
        """
        lines = [
            f"# {self.title}",
            "",
            "## Overview",
            "",
            "Complete validation of all MCP tools covering:",
            "- **Functionality**: What the tool does",
            "- **User Stories**: Why users need it",
            "- **Data Coverage**: All data items validated",
            "- **Test Results**: Pass/fail status with performance",
            "",
            "---",
            "",
        ]

        # Create results lookup for efficient matching
        results_by_test = {r["test_name"]: r for r in results}

        # Generate matrix for each tool
        for tool_name, tool_info in self.tool_capabilities.items():
            lines.append(f"## {tool_name}")
            lines.append(f"**{tool_info['description']}**")
            lines.append("")

            # Operations table
            lines.append("| Operation | Status | Time (ms) | User Story | Data Items |")
            lines.append("|-----------|--------|-----------|------------|------------|")

            for op_name, op_info in tool_info["operations"].items():
                # Find matching test result
                test_result = self._find_test_result(results_by_test, tool_name, op_name)

                # Determine status
                if test_result:
                    if op_info.get("known_issue"):
                        status = "⚠️ Known Issue"
                    elif test_result.get("cached"):
                        status = "💾 Cached"
                    elif test_result.get("skipped"):
                        status = "⏭️ Skipped"
                    elif test_result["success"]:
                        status = "✅ Pass"
                    else:
                        status = "❌ Fail"
                    duration = f"{test_result['duration_ms']:.0f}"
                else:
                    status = "⏭️ Not Tested"
                    duration = "-"

                # Format user story (remove common prefix for brevity)
                user_story = op_info.get("user_story", "")
                user_story = user_story.replace("As a user, I want to ", "")

                # Format data items
                data_items = ", ".join(op_info.get("data_items", [])[:3])
                if len(op_info.get("data_items", [])) > 3:
                    data_items += "..."

                lines.append(
                    f"| {op_name} | {status} | {duration} | "
                    f"{user_story[:40]}{'...' if len(user_story) > 40 else ''} | "
                    f"{data_items[:30]}{'...' if len(data_items) > 30 else ''} |",
                )

            # Add detailed operation info
            lines.append("")
            lines.append(f"### {tool_name} Operations Detail")
            lines.append("")

            for op_name, op_info in tool_info["operations"].items():
                lines.append(f"#### {op_name}")
                lines.append(f"- **Feature**: {op_info.get('feature', 'N/A')}")
                lines.append(f"- **User Story**: {op_info.get('user_story', 'N/A')}")
                lines.append(f"- **Assertions**: {', '.join(op_info.get('assertions', []))}")

                if op_info.get("known_issue"):
                    lines.append(f"- **⚠️ Known Issue**: {op_info['known_issue']}")

                lines.append("")

            lines.append("---")
            lines.append("")

        # Summary statistics
        lines.append("## Test Coverage Summary")
        lines.append("")

        total_ops = sum(len(tool["operations"]) for tool in self.tool_capabilities.values())
        tested_ops = 0
        passed_ops = 0

        for tool_info in self.tool_capabilities.values():
            for op_name in tool_info["operations"]:
                test_result = self._find_test_result(
                    results_by_test, "", op_name,
                )  # Search across all tools
                if test_result:
                    tested_ops += 1
                    if test_result.get("success") and not test_result.get("skipped"):
                        passed_ops += 1

        lines.append(f"- **Total Operations**: {total_ops}")
        lines.append(f"- **Tested**: {tested_ops} ({tested_ops/total_ops*100:.1f}%)")
        lines.append(
            f"- **Passed**: {passed_ops} ({passed_ops/tested_ops*100:.1f}% of tested)"
            if tested_ops > 0
            else "- **Passed**: 0",
        )
        lines.append("")

        # Write to file
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_path.write_text("\n".join(lines))
        print(f"Functionality Matrix: {self.output_path}")

    def _find_test_result(
        self, results_by_test: dict[str, dict[str, Any]], tool_name: str, op_name: str,
    ) -> dict[str, Any] | None:
        """Find test result matching tool and operation.

        Args:
            results_by_test: Dictionary of test results keyed by test name
            tool_name: Tool name to match (empty string to search all)
            op_name: Operation name to match

        Returns:
            Matching test result or None
        """
        for test_name, result in results_by_test.items():
            test_name_lower = test_name.lower()
            op_name_lower = op_name.lower()

            # Check if operation name is in test name
            if op_name_lower in test_name_lower:
                # If tool name specified, verify it matches
                if tool_name and tool_name.lower() not in test_name_lower:
                    continue
                return result

        return None
