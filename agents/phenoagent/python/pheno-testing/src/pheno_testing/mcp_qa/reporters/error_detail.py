"""
Detailed Error Reporter - Pytest-like comprehensive error output.

Provides detailed error information including:
- Full stack traces with file paths and line numbers
- Local variables at failure point
- Request parameters sent to MCP tool
- Full response received (not truncated)
- Assertion failures with actual vs expected
- Suggestions for fixes (if common error pattern)
- Rich formatting when available
"""

import json
from typing import Any, Dict, List, Optional

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.syntax import Syntax
    from rich.table import Table
    from rich.text import Text

    HAS_RICH = True
except ImportError:
    HAS_RICH = False


class DetailedErrorReporter:
    """
    Detailed Error Reporter - Pytest-like detailed error output.

    Provides comprehensive error information for debugging failed tests.
    """

    # Known error patterns and suggested fixes
    KNOWN_ISSUES = {
        "DB_CONSTRAINT_VIOLATION": {
            "title": "Database Constraint Violation",
            "description": "The data violates a database integrity constraint (CHECK, UNIQUE, FOREIGN KEY, or NOT NULL).",
            "fix": "Review the field values and ensure they meet the database schema requirements.",
            "doc_link": None,
            "is_db_constraint": True,
        },
        "valid_slug": {
            "title": "Invalid Slug Format",
            "description": "The slug field contains invalid characters or format.",
            "fix": "Ensure slug only contains lowercase letters, numbers, and hyphens. No underscores or special characters.",
            "doc_link": None,
            "is_db_constraint": True,
        },
        "NOT NULL constraint failed: updated_by": {
            "title": "RLS Policy Constraint",
            "description": "The updated_by field constraint is failing due to RLS policy issues.",
            "fix": "Ensure RLS policies are properly configured for the updated_by field.",
            "doc_link": "docs/known_issues.md#updated_by_constraint",
        },
        "Embedding calculation error": {
            "title": "Vector Embedding Issue",
            "description": "RAG semantic search embedding calculation is failing.",
            "fix": "Check that the embedding service is available and properly configured.",
            "doc_link": "docs/known_issues.md#embedding_errors",
        },
        "Connection refused": {
            "title": "MCP Server Connection",
            "description": "Unable to connect to the MCP server.",
            "fix": "Verify the MCP server is running and accessible at the configured endpoint.",
            "doc_link": None,
        },
        "Permission denied": {
            "title": "Authentication Error",
            "description": "The request lacks proper authentication credentials.",
            "fix": "Ensure OAuth tokens are valid and properly configured.",
            "doc_link": None,
        },
        "Timeout": {
            "title": "Request Timeout",
            "description": "The MCP tool request timed out.",
            "fix": "Check server responsiveness or increase timeout settings.",
            "doc_link": None,
        },
        "Invalid JSON": {
            "title": "JSON Parse Error",
            "description": "Unable to parse the response as JSON.",
            "fix": "Verify the MCP tool is returning properly formatted JSON.",
            "doc_link": None,
        },
        "404": {
            "title": "Resource Not Found",
            "description": "The requested resource was not found.",
            "fix": "Verify the resource ID or path is correct.",
            "doc_link": None,
        },
        "500": {
            "title": "Server Error",
            "description": "The server encountered an internal error.",
            "fix": "Check server logs for more details.",
            "doc_link": None,
        },
    }

    def __init__(self, verbose: bool = True, use_rich: bool = True):
        """Initialize detailed error reporter.

        Args:
            verbose: Show detailed information (locals, traceback)
            use_rich: Use rich formatting if available
        """
        self.verbose = verbose
        self.use_rich = use_rich and HAS_RICH
        self.console = Console() if self.use_rich else None

    def report(self, results: List[Dict[str, Any]], metadata: Dict[str, Any]) -> None:
        """Generate detailed error reports for all failed tests.

        Args:
            results: List of test result dictionaries
            metadata: Test run metadata
        """
        failed_tests = [
            r for r in results if not r.get("success", False) and not r.get("skipped", False)
        ]

        if not failed_tests:
            return

        if self.use_rich:
            self._report_rich(failed_tests, metadata)
        else:
            self._report_plain(failed_tests, metadata)

    def _report_rich(self, failed_tests: List[Dict[str, Any]], metadata: Dict[str, Any]) -> None:
        """
        Generate rich formatted error report.
        """
        self.console.print("\n")
        self.console.print("[bold red]DETAILED ERROR REPORT[/bold red]")
        self.console.print("[dim]" + "=" * 80 + "[/dim]\n")

        for idx, result in enumerate(failed_tests, 1):
            self._print_rich_error(result, idx, len(failed_tests))

    def _report_plain(self, failed_tests: List[Dict[str, Any]], metadata: Dict[str, Any]) -> None:
        """
        Generate plain text error report.
        """
        print("\n" + "=" * 80)
        print("DETAILED ERROR REPORT")
        print("=" * 80 + "\n")

        for idx, result in enumerate(failed_tests, 1):
            self._print_plain_error(result, idx, len(failed_tests))

    def _print_rich_error(self, result: Dict[str, Any], idx: int, total: int) -> None:
        """
        Print a single error with Rich formatting.
        """
        test_name = result.get("test_name", "unknown")
        tool_name = result.get("tool_name", "unknown")
        error = result.get("error", "Unknown error")
        duration_ms = result.get("duration_ms", 0)

        # Detect if this is a DB constraint violation
        is_db_constraint = (
            "DB_CONSTRAINT_VIOLATION" in str(error)
            or "check constraint" in str(error).lower()
            or "23514" in str(error)
            or "23505" in str(error)
            or "23503" in str(error)
            or "23502" in str(error)
        )

        # Use different colors for DB constraints vs other errors
        if is_db_constraint:
            icon = "🔶"  # Orange diamond for DB constraints
            title_color = "bold yellow"
            border_color = "yellow"
            text_style = "yellow"
            error_type = "DB CONSTRAINT"
        else:
            icon = "❌"  # Red X for other errors
            title_color = "bold red"
            border_color = "red"
            text_style = "red"
            error_type = "FAILED"

        # Main error header
        title = f"[{idx}/{total}] {test_name} {error_type}"
        self.console.print(f"\n[{title_color}]{icon} {title}[/{title_color}]")
        self.console.print("[dim]" + "━" * 80 + "[/dim]")

        # Test information
        info_table = Table(show_header=False, box=None, padding=(0, 2))
        info_table.add_row("[cyan]Test:[/cyan]", test_name)
        info_table.add_row("[cyan]Tool:[/cyan]", tool_name)
        info_table.add_row("[cyan]Duration:[/cyan]", f"{duration_ms:.2f}ms")
        if is_db_constraint:
            info_table.add_row(
                "[cyan]Type:[/cyan]", "[yellow]Database Constraint Violation[/yellow]"
            )

        if result.get("retry_count"):
            info_table.add_row("[cyan]Retries:[/cyan]", str(result["retry_count"]))

        self.console.print(info_table)

        # Error message
        self.console.print("\n[bold yellow]Error:[/bold yellow]")
        error_text = Text(str(error), style=text_style)
        self.console.print(Panel(error_text, border_style=border_color, padding=(1, 2)))

        # Request parameters (if available)
        request_params = result.get("request_params")
        if request_params:
            self.console.print(f"\n[bold]{'─' * 27} Request {'─' * 27}[/bold]")
            syntax = Syntax(
                json.dumps(request_params, indent=2), "json", theme="monokai", line_numbers=False
            )
            self.console.print(syntax)

        # Response (if available)
        response = result.get("response")
        if response:
            self.console.print(f"\n[bold]{'─' * 26} Response {'─' * 26}[/bold]")
            response_str = (
                json.dumps(response, indent=2) if isinstance(response, dict) else str(response)
            )
            syntax = Syntax(
                response_str,
                "json" if isinstance(response, dict) else "text",
                theme="monokai",
                line_numbers=False,
            )
            self.console.print(syntax)

        # Local variables (if available)
        locals_data = result.get("locals")
        if locals_data and self.verbose:
            self.console.print(f"\n[bold]{'─' * 27} Locals {'─' * 27}[/bold]")
            locals_table = Table(show_header=True, box=None)
            locals_table.add_column("Variable", style="cyan")
            locals_table.add_column("Value", style="white")

            for key, value in locals_data.items():
                value_str = str(value)[:100]
                if len(str(value)) > 100:
                    value_str += "..."
                locals_table.add_row(key, value_str)

            self.console.print(locals_table)

        # Traceback (if available)
        tb = result.get("traceback")
        if tb and self.verbose:
            self.console.print(f"\n[bold]{'─' * 25} Traceback {'─' * 26}[/bold]")
            syntax = Syntax(tb, "python", theme="monokai", line_numbers=False)
            self.console.print(syntax)

        # Suggestions
        suggestion = self._get_suggestion(str(error))
        if suggestion:
            self.console.print(f"\n[bold]{'─' * 24} Suggestion {'─' * 25}[/bold]")

            msg = f"💡 [bold yellow]{suggestion['title']}[/bold yellow]\n"
            msg += f"   {suggestion['description']}\n\n"
            msg += f"   [bold]Fix:[/bold] {suggestion['fix']}"

            if suggestion.get("doc_link"):
                msg += f"\n   [bold]See:[/bold] [link]{suggestion['doc_link']}[/link]"

            self.console.print(Panel(msg, border_style="yellow", padding=(1, 2)))

        self.console.print("[dim]" + "━" * 80 + "[/dim]\n")

    def _print_plain_error(self, result: Dict[str, Any], idx: int, total: int) -> None:
        """
        Print a single error with plain text formatting.
        """
        test_name = result.get("test_name", "unknown")
        tool_name = result.get("tool_name", "unknown")
        error = result.get("error", "Unknown error")
        duration_ms = result.get("duration_ms", 0)

        # Main error header
        print(f"\n✗ [{idx}/{total}] {test_name} FAILED")
        print("━" * 80)

        # Test information
        print(f"Test:     {test_name}")
        print(f"Tool:     {tool_name}")
        print(f"Duration: {duration_ms:.2f}ms")

        if result.get("retry_count"):
            print(f"Retries:  {result['retry_count']}")

        # Error message
        print("\nError:")
        print(f"  {error}")

        # Request parameters (if available)
        request_params = result.get("request_params")
        if request_params:
            print(f"\n{'─' * 27} Request {'─' * 27}")
            print(json.dumps(request_params, indent=2))

        # Response (if available)
        response = result.get("response")
        if response:
            print(f"\n{'─' * 26} Response {'─' * 26}")
            response_str = (
                json.dumps(response, indent=2) if isinstance(response, dict) else str(response)
            )
            print(response_str)

        # Local variables (if available)
        locals_data = result.get("locals")
        if locals_data and self.verbose:
            print(f"\n{'─' * 27} Locals {'─' * 27}")
            for key, value in locals_data.items():
                value_str = str(value)[:100]
                if len(str(value)) > 100:
                    value_str += "..."
                print(f"  {key} = {value_str}")

        # Traceback (if available)
        tb = result.get("traceback")
        if tb and self.verbose:
            print(f"\n{'─' * 25} Traceback {'─' * 26}")
            print(tb)

        # Suggestions
        suggestion = self._get_suggestion(str(error))
        if suggestion:
            print(f"\n{'─' * 24} Suggestion {'─' * 25}")
            print(f"💡 {suggestion['title']}")
            print(f"   {suggestion['description']}")
            print(f"   Fix: {suggestion['fix']}")

            if suggestion.get("doc_link"):
                print(f"   See: {suggestion['doc_link']}")

        print("━" * 80 + "\n")

    def _get_suggestion(self, error: str) -> Optional[Dict[str, str]]:
        """Get suggestion for a known error pattern.

        Args:
            error: Error message to match

        Returns:
            Dictionary with suggestion details or None
        """
        error_lower = error.lower()
        for pattern, suggestion in self.KNOWN_ISSUES.items():
            if pattern.lower() in error_lower:
                return suggestion
        return None

    def add_known_issue(
        self, pattern: str, title: str, description: str, fix: str, doc_link: Optional[str] = None
    ) -> None:
        """Add a new known issue pattern and suggestion.

        Args:
            pattern: Error message pattern to match
            title: Short title for the issue
            description: Detailed description
            fix: Suggested fix
            doc_link: Optional documentation link
        """
        self.KNOWN_ISSUES[pattern] = {
            "title": title,
            "description": description,
            "fix": fix,
            "doc_link": doc_link,
        }
