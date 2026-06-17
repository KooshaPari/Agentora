"""
MCP Test Reporters - Unified reporting library for MCP test results.

This package provides comprehensive test result reporting with multiple output formats:

- ConsoleReporter: Rich-formatted console output with colors and tables
- JSONReporter: Machine-readable JSON export for CI/CD integration
- MarkdownReporter: Human-readable documentation format
- FunctionalityMatrixReporter: Comprehensive feature coverage mapping
- DetailedErrorReporter: Pytest-like detailed error output for debugging

Usage:
    from pheno.testing.mcp_qa.reporters import ConsoleReporter, JSONReporter

    # Console output
    console = ConsoleReporter(title="My Test Run")
    console.report(results, metadata)

    # JSON export
    json_reporter = JSONReporter("reports/results.json")
    json_reporter.report(results, metadata)

    # Multiple reporters
    reporters = [
        ConsoleReporter(),
        JSONReporter("results.json"),
        MarkdownReporter("report.md")
    ]
    for reporter in reporters:
        reporter.report(results, metadata)

Expected Result Format:
    Each result dictionary should contain:
    - test_name: str - Name of the test
    - tool_name: str - Name of the tool being tested
    - success: bool - Whether test passed
    - duration_ms: float - Test duration in milliseconds
    - skipped: bool (optional) - Whether test was skipped
    - cached: bool (optional) - Whether result was cached
    - error: str (optional) - Error message if failed
    - request_params: dict (optional) - Request parameters sent
    - response: any (optional) - Response received
    - traceback: str (optional) - Stack trace if failed
    - locals: dict (optional) - Local variables at failure

Expected Metadata Format:
    - endpoint: str (optional) - MCP server endpoint
    - auth_status: str (optional) - Authentication status
    - duration_seconds: float (optional) - Total run duration
    - [any other custom metadata]
"""

from typing import Any, Dict, List

from .console import ConsoleReporter
from .error_detail import DetailedErrorReporter
from .json_reporter import JSONReporter
from .markdown import MarkdownReporter
from .matrix import FunctionalityMatrixReporter


class TestReporter:
    """Base class for test reporters.

    All reporters should inherit from this class and implement the report() method.
    """

    def report(self, results: List[Dict[str, Any]], metadata: Dict[str, Any]) -> None:
        """Generate report from test results.

        Args:
            results: List of test result dictionaries
            metadata: Test run metadata

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement report()")


class MultiReporter(TestReporter):
    """Composite reporter that runs multiple reporters.

    Useful for generating multiple report formats in a single call.

    Example:
        multi = MultiReporter([
            ConsoleReporter(),
            JSONReporter("results.json"),
            MarkdownReporter("report.md")
        ])
        multi.report(results, metadata)
    """

    def __init__(self, reporters: List[TestReporter]):
        """Initialize multi-reporter.

        Args:
            reporters: List of reporter instances to run
        """
        self.reporters = reporters

    def report(self, results: List[Dict[str, Any]], metadata: Dict[str, Any]) -> None:
        """Run all reporters.

        Args:
            results: List of test result dictionaries
            metadata: Test run metadata
        """
        for reporter in self.reporters:
            try:
                reporter.report(results, metadata)
            except Exception as e:
                print(f"Warning: Reporter {reporter.__class__.__name__} failed: {e}")

    def add_reporter(self, reporter: TestReporter) -> None:
        """Add a reporter to the list.

        Args:
            reporter: Reporter instance to add
        """
        self.reporters.append(reporter)


# Export all reporter classes
__all__ = [
    "TestReporter",
    "ConsoleReporter",
    "JSONReporter",
    "MarkdownReporter",
    "FunctionalityMatrixReporter",
    "DetailedErrorReporter",
    "MultiReporter",
]


# Convenience function for creating standard reporter set
def create_standard_reporters(
    output_dir: str = "reports", console_title: str = "MCP TEST REPORT", verbose_errors: bool = True
) -> List[TestReporter]:
    """Create a standard set of reporters for comprehensive test reporting.

    Args:
        output_dir: Directory to write report files
        console_title: Title for console output
        verbose_errors: Show detailed error information

    Returns:
        List of configured reporter instances

    Example:
        reporters = create_standard_reporters("test-reports")
        for reporter in reporters:
            reporter.report(results, metadata)
    """
    from pathlib import Path

    output_path = Path(output_dir)

    return [
        ConsoleReporter(title=console_title),
        JSONReporter(str(output_path / "results.json")),
        MarkdownReporter(str(output_path / "report.md")),
        FunctionalityMatrixReporter(str(output_path / "matrix.md")),
        DetailedErrorReporter(verbose=verbose_errors),
    ]
