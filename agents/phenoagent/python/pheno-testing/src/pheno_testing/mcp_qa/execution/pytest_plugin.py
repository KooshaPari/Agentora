"""Generic MCP Pytest Plugin Base Class.

Provides reusable pytest integration for MCP testing frameworks:
- Rich progress display with live stats
- Multiple reporters (JSON, Markdown, Console, FunctionalityMatrix)
- Auth validation before tests
- Performance metrics tracking
- Category-based execution
- Cache management

This base class can be extended by specific MCP projects to add
custom tool name extraction and project-specific features.
"""

import asyncio
import os
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

try:
    from rich.console import Console
    from rich.live import Live
    from rich.panel import Panel
    from rich.progress import (
        BarColumn,
        Progress,
        SpinnerColumn,
        TaskID,
        TextColumn,
        TimeElapsedColumn,
        TimeRemainingColumn,
    )
    from rich.table import Table
    from rich.text import Text  # noqa: F401 - Used in rich text formatting

    HAS_RICH = True
except ImportError:
    HAS_RICH = False


class MCPProgressDisplay:
    """
    Rich progress display for pytest execution.
    """

    def __init__(self, total_tests: int, parallel: bool = False, workers: int = 1):
        if not HAS_RICH:
            self.enabled = False
            return

        self.enabled = True
        self.console = Console()
        self.total_tests = total_tests
        self.parallel = parallel
        self.workers = workers

        # Statistics
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.cached = 0
        self.current_test = ""
        self.current_tool = ""
        self.current_worker = 0
        self.start_time = time.time()
        self.durations = []

        # Rich progress
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("({task.completed}/{task.total})"),
            TimeElapsedColumn(),
            TextColumn("<"),
            TimeRemainingColumn(),
            console=self.console,
        )
        self.task_id: Optional[TaskID] = None
        self.live: Optional[Live] = None

    def start(self):
        """
        Start the progress display.
        """
        if not self.enabled:
            return

        self.task_id = self.progress.add_task("Running tests...", total=self.total_tests)
        self.start_time = time.time()

        # Create live display
        self.live = Live(self._get_display(), console=self.console, refresh_per_second=4)
        self.live.start()

    def update(self, test_name: str = "", tool_name: str = "", worker_id: int = 0):
        """
        Update progress with current test info.
        """
        if not self.enabled or self.task_id is None:
            return

        self.current_test = test_name
        self.current_tool = tool_name
        self.current_worker = worker_id

        self.progress.update(self.task_id, advance=1)

        if self.live:
            self.live.update(self._get_display())

    def record_result(
        self,
        passed: bool = False,
        failed: bool = False,
        skipped: bool = False,
        cached: bool = False,
        duration: float = 0.0,
    ):
        """
        Record test result.
        """
        if passed:
            self.passed += 1
        if failed:
            self.failed += 1
        if skipped:
            self.skipped += 1
        if cached:
            self.cached += 1
        if duration > 0:
            self.durations.append(duration)

        if self.live:
            self.live.update(self._get_display())

    def stop(self):
        """
        Stop the progress display.
        """
        if not self.enabled or not self.live:
            return

        self.live.stop()

    def _get_display(self):
        """
        Generate the display layout.
        """
        # Stats table
        stats_table = Table.grid(padding=(0, 2))
        stats_table.add_row(
            "[green]✓ Passed:[/green]",
            str(self.passed),
            "[red]✗ Failed:[/red]",
            str(self.failed),
            "[yellow]⊘ Skipped:[/yellow]",
            str(self.skipped),
            "[cyan]◉ Cached:[/cyan]",
            str(self.cached),
        )

        # Performance metrics
        elapsed = time.time() - self.start_time
        completed = self.passed + self.failed + self.skipped
        speed = completed / elapsed if elapsed > 0 else 0
        avg_duration = sum(self.durations) / len(self.durations) if self.durations else 0
        cache_rate = (self.cached / completed * 100) if completed > 0 else 0

        perf_table = Table.grid(padding=(0, 2))
        perf_table.add_row(
            "[cyan]Speed:[/cyan]",
            f"{speed:.1f} tests/sec",
            "[cyan]Avg:[/cyan]",
            f"{avg_duration:.2f}s/test",
            "[cyan]Cache:[/cyan]",
            f"{cache_rate:.1f}%",
        )

        # Current test info
        current_info = ""
        if self.current_test:
            current_info = (
                f"[bold cyan]Current:[/bold cyan] {self.current_test}\n"
                f"[dim]Tool: {self.current_tool}"
            )
            if self.parallel:
                current_info += f" | Worker: {self.current_worker}/{self.workers}"
            current_info += "[/dim]"

        # Combine into layout
        layout = [
            self.progress,
            "",
            Panel(stats_table, title="📊 Live Stats", border_style="blue"),
            Panel(perf_table, title="📈 Performance", border_style="cyan"),
        ]

        if current_info:
            layout.append(Panel(current_info, title="🔄 Progress", border_style="yellow"))

        return "\n".join(str(item) for item in layout)


class MCPReporterManager:
    """
    Manages multiple test reporters.
    """

    def __init__(
        self,
        output_dir: Path,
        enable_json: bool = True,
        enable_markdown: bool = True,
        enable_matrix: bool = True,
        reporter_import_path: str = "tests.framework.reporters",
    ):
        self.output_dir = output_dir
        self.enable_json = enable_json
        self.enable_markdown = enable_markdown
        self.enable_matrix = enable_matrix
        self.reporter_import_path = reporter_import_path

        # Import reporters
        try:
            import importlib

            reporters_module = importlib.import_module(reporter_import_path)

            self.reporters = []

            if enable_json:
                JSONReporter = getattr(reporters_module, "JSONReporter")
                self.reporters.append(JSONReporter(str(output_dir / "test_results.json")))
            if enable_markdown:
                MarkdownReporter = getattr(reporters_module, "MarkdownReporter")
                self.reporters.append(MarkdownReporter(str(output_dir / "test_results.md")))
            if enable_matrix:
                FunctionalityMatrixReporter = getattr(
                    reporters_module, "FunctionalityMatrixReporter"
                )
                self.reporters.append(
                    FunctionalityMatrixReporter(str(output_dir / "functionality_matrix.md"))
                )

            self.has_reporters = True
        except (ImportError, AttributeError):
            self.has_reporters = False
            self.reporters = []

    def generate_reports(self, results: List[Dict[str, Any]], metadata: Dict[str, Any]):
        """
        Generate all enabled reports.
        """
        if not self.has_reporters:
            return

        for reporter in self.reporters:
            try:
                reporter.report(results, metadata)
            except Exception as e:
                print(f"Warning: Reporter {reporter.__class__.__name__} failed: {e}")


class MCPPytestPlugin(ABC):
    """Base pytest plugin that integrates MCP testing features.

    Features:
    - Rich progress display during test execution
    - Performance tracking and statistics
    - Multiple output formats (JSON, Markdown, Matrix)
    - Auth validation before tests
    - Cache management

    Subclasses must implement:
    - _extract_tool_name(): Project-specific tool name extraction logic
    """

    def __init__(self):
        self.progress_display: Optional[MCPProgressDisplay] = None
        self.reporter_manager: Optional[MCPReporterManager] = None
        self.test_results: List[Dict[str, Any]] = []
        self.start_time: float = 0
        self.auth_validated: bool = False
        self.enable_progress: bool = False
        self.enable_reports: bool = False

    @pytest.hookimpl(tryfirst=True)
    def pytest_configure(self, config):
        """
        Configure the plugin based on CLI options.
        """
        # Check for custom options
        self.enable_progress = config.getoption("--enable-rich-progress", False)
        self.enable_reports = config.getoption("--enable-reports", False)

        # Store config for later use
        self.config = config

    @pytest.hookimpl(tryfirst=True)
    def pytest_sessionstart(self, session):
        """
        Initialize session-level features.
        """
        self.start_time = time.time()
        self.test_results = []

        # Validate auth if enabled
        if hasattr(session.config, "getoption") and session.config.getoption(
            "--validate-auth", False
        ):
            self._validate_auth(session)

        # Initialize progress display if enabled
        if self.enable_progress and HAS_RICH:
            total_tests = len(session.items)
            parallel = hasattr(session.config, "workerinput")  # pytest-xdist
            workers = getattr(session.config.option, "numprocesses", 1) if parallel else 1

            self.progress_display = MCPProgressDisplay(
                total_tests=total_tests, parallel=parallel, workers=workers
            )
            self.progress_display.start()

        # Initialize reporters if enabled
        if self.enable_reports:
            output_dir = self._get_reports_output_dir()
            output_dir.mkdir(parents=True, exist_ok=True)

            self.reporter_manager = MCPReporterManager(
                output_dir=output_dir,
                enable_json=True,
                enable_markdown=True,
                enable_matrix=True,
                reporter_import_path=self._get_reporter_import_path(),
            )

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_protocol(self, item, nextitem):
        """
        Hook into test execution to track progress.
        """
        # Update progress display before test runs
        if self.progress_display and self.progress_display.enabled:
            test_name = item.name
            tool_name = self._extract_tool_name(item)
            worker_id = getattr(item.config, "workerinput", {}).get("workerid", 0)

            self.progress_display.update(
                test_name=test_name, tool_name=tool_name, worker_id=worker_id
            )

        yield

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item, call):
        """
        Capture test results for reporting.
        """
        outcome = yield
        report = outcome.get_result()

        # Only process call phase (not setup/teardown)
        if report.when != "call":
            return

        # Extract test info
        test_name = item.name
        tool_name = self._extract_tool_name(item)
        passed = report.outcome == "passed"
        failed = report.outcome == "failed"
        skipped = report.outcome == "skipped"
        duration = report.duration

        # Check if cached (from test cache)
        cached = hasattr(item, "cached") and item.cached

        # Update progress display
        if self.progress_display and self.progress_display.enabled:
            self.progress_display.record_result(
                passed=passed, failed=failed, skipped=skipped, cached=cached, duration=duration
            )

        # Store result for reporting
        result = {
            "test_name": test_name,
            "tool_name": tool_name,
            "success": passed,
            "failed": failed,
            "skipped": skipped,
            "cached": cached,
            "duration_ms": duration * 1000,
            "error": str(report.longrepr) if failed else None,
        }

        self.test_results.append(result)

    @pytest.hookimpl(trylast=True)
    def pytest_sessionfinish(self, session, exitstatus):
        """
        Finalize session and generate reports.
        """
        # Stop progress display
        if self.progress_display and self.progress_display.enabled:
            self.progress_display.stop()

        # Generate reports
        if self.enable_reports and self.reporter_manager:
            duration = time.time() - self.start_time
            metadata = self._get_report_metadata(duration)

            self.reporter_manager.generate_reports(self.test_results, metadata)

    def _validate_auth(self, session):
        """
        Validate authentication before running tests.
        """
        try:
            # Import auth validator
            from pheno.testing.mcp_qa.testing.auth_validator import validate_auth

            mcp_endpoint = self._get_mcp_endpoint()
            _ = os.getenv("ATOMS_OAUTH_PROVIDER", "authkit")  # Keep for future use

            # Run async auth validation
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create new loop if one is already running
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            result = loop.run_until_complete(
                validate_auth(
                    client=None, credentials=None, mcp_endpoint=mcp_endpoint, verbose=True
                )
            )

            self.auth_validated = result.success

            if result.success:
                print("\n✓ Auth validation passed\n")
            else:
                print(f"\n✗ Auth validation failed: {result.message}\n")
                if not session.config.getoption("--continue-on-auth-fail", False):
                    pytest.exit("Authentication validation failed", returncode=1)

        except ImportError:
            print("\n⚠ Auth validator not available, skipping validation\n")
        except Exception as e:
            print(f"\n⚠ Auth validation error: {e}\n")

    # Abstract methods for subclasses to implement

    @abstractmethod
    def _extract_tool_name(self, item) -> str:
        """Extract tool name from test item.

        Subclasses must implement this method to provide project-specific
        tool name extraction logic based on test registries, naming conventions,
        or other project-specific patterns.

        Args:
            item: The pytest test item

        Returns:
            Tool name as string (e.g., "workspace_tool", "entity_tool")
        """
        pass

    # Optional methods for subclasses to override

    def _get_mcp_endpoint(self) -> str:
        """Get the MCP endpoint URL.

        Override this method to provide project-specific endpoint logic.
        Default implementation uses MCP_ENDPOINT environment variable.

        Returns:
            MCP endpoint URL as string
        """
        return os.getenv("MCP_ENDPOINT", "https://mcp.atoms.tech/api/mcp")

    def _get_reports_output_dir(self) -> Path:
        """Get the output directory for reports.

        Override this method to change the default reports location.
        Default implementation returns tests/reports.

        Returns:
            Path object for reports directory
        """
        return Path("tests") / "reports"

    def _get_reporter_import_path(self) -> str:
        """Get the import path for reporter classes.

        Override this method to specify a different reporter module.
        Default implementation returns "tests.framework.reporters".

        Returns:
            Import path as string
        """
        return "tests.framework.reporters"

    def _get_report_metadata(self, duration: float) -> Dict[str, Any]:
        """Get metadata for test reports.

        Override this method to add project-specific metadata.
        Default implementation includes basic execution metadata.

        Args:
            duration: Test execution duration in seconds

        Returns:
            Metadata dictionary
        """
        return {
            "endpoint": self._get_mcp_endpoint(),
            "auth_status": "validated" if self.auth_validated else "not_validated",
            "duration_seconds": duration,
            "timestamp": datetime.now().isoformat(),
            "pytest_version": pytest.__version__,
        }


def create_pytest_addoption(group_name: str = "mcp"):
    """Factory function to create pytest_addoption with custom group name.

    Args:
        group_name: Name for the CLI option group

    Returns:
        pytest_addoption function
    """

    def pytest_addoption(parser):
        """
        Add custom CLI options.
        """
        group = parser.getgroup(group_name, f"{group_name.upper()} MCP Test Framework")

        group.addoption(
            "--enable-rich-progress",
            action="store_true",
            default=False,
            help="Enable rich progress display with live stats",
        )

        group.addoption(
            "--enable-reports",
            action="store_true",
            default=False,
            help="Enable report generation (JSON, Markdown, Matrix)",
        )

        group.addoption(
            "--validate-auth",
            action="store_true",
            default=False,
            help="Validate authentication before running tests",
        )

        group.addoption(
            "--continue-on-auth-fail",
            action="store_true",
            default=False,
            help="Continue running tests even if auth validation fails",
        )

    return pytest_addoption


__all__ = [
    "MCPProgressDisplay",
    "MCPReporterManager",
    "MCPPytestPlugin",
    "create_pytest_addoption",
]
