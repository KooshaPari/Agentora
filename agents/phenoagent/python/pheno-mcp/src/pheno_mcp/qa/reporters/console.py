"""
Console Reporter - Rich-formatted console output for test results.

Provides colored, formatted console output with:
- Summary statistics (pass/fail/skip rates)
- Grouped results by tool
- Cache hit indicators
- Performance metrics
- Rich formatting when available
"""

from typing import Any

try:
    from rich.console import Console
    from rich.table import Table

    HAS_RICH = True
except ImportError:
    HAS_RICH = False


class ConsoleReporter:
    """
    Console reporter with formatted output supporting both plain and rich modes.
    """

    def __init__(
        self,
        title: str = "MCP TEST REPORT",
        use_rich: bool = True,
        verbose: bool = False,
        show_running: bool = False,
    ):
        """Initialize console reporter.

        Args:
            title: Report title to display
            use_rich: Use rich formatting if available (default: True)
            verbose: Show detailed output during test execution (default: False)
            show_running: Show currently running tests (default: False)
        """
        self.title = title
        self.use_rich = use_rich and HAS_RICH
        self.verbose = verbose
        self.show_running = show_running
        self.console = Console() if self.use_rich else None

    def report(self, results: list[dict[str, Any]], metadata: dict[str, Any]) -> None:
        """Print formatted report to console.

        Args:
            results: List of test result dictionaries
            metadata: Test run metadata (endpoint, auth status, etc.)
        """
        if self.use_rich:
            self._report_rich(results, metadata)
        else:
            self._report_plain(results, metadata)

    def _report_rich(self, results: list[dict[str, Any]], metadata: dict[str, Any]) -> None:
        """
        Generate rich formatted report.
        """
        self._print_rich_header()
        self._print_rich_connection_info(metadata)
        self._print_rich_summary(results, metadata)
        self._print_rich_results_by_tool(results)
        self._print_rich_footer()

    def _print_rich_header(self) -> None:
        """
        Print the rich report header.
        """
        self.console.print()
        self.console.print(f"[bold cyan]{self.title}[/bold cyan]")
        self.console.print("[dim]" + "=" * 80 + "[/dim]")

    def _print_rich_connection_info(self, metadata: dict[str, Any]) -> None:
        """
        Print connection information.
        """
        if "endpoint" in metadata:
            self.console.print(f"\n[bold]Endpoint:[/bold] {metadata['endpoint']}")
        if "auth_status" in metadata:
            auth_icon = "🔓" if metadata["auth_status"] == "unauthenticated" else "🔐"
            self.console.print(f"[bold]Auth:[/bold] {auth_icon} {metadata['auth_status']}")

    def _print_rich_summary(self, results: list[dict[str, Any]], metadata: dict[str, Any]) -> None:
        """
        Print the rich summary section.
        """
        summary = self._calculate_summary(results)

        self.console.print("\n[bold cyan]Summary[/bold cyan]")
        summary_table = self._build_rich_summary_table(summary, metadata)
        self.console.print(summary_table)

    def _build_rich_summary_table(self, summary: dict[str, Any], metadata: dict[str, Any]) -> Table:
        """
        Build the rich summary table.
        """
        summary_table = Table(show_header=False, box=None, padding=(0, 2))
        summary_table.add_row("Total Tests:", str(summary["total"]))
        summary_table.add_row("[green]Passed:[/green]", f"[green]✓ {summary['passed']}[/green]")
        summary_table.add_row("[red]Failed:[/red]", f"[red]✗ {summary['failed']}[/red]")
        summary_table.add_row(
            "[yellow]Skipped:[/yellow]", f"[yellow]⊘ {summary['skipped']}[/yellow]",
        )

        if summary["cached"] > 0:
            summary_table.add_row("[blue]Cached:[/blue]", f"[blue]💾 {summary['cached']}[/blue]")

        summary_table.add_row(
            "[bold]Pass Rate:[/bold]", f"[bold]{summary['pass_rate']:.1f}%[/bold]",
        )

        if "duration_seconds" in metadata:
            summary_table.add_row("Total Time:", f"{metadata['duration_seconds']:.2f}s")

        if summary["avg_duration_ms"] > 0:
            summary_table.add_row("Avg Duration:", f"{summary['avg_duration_ms']:.2f}ms")

        return summary_table

    def _print_rich_results_by_tool(self, results: list[dict[str, Any]]) -> None:
        """
        Print results grouped by tool.
        """
        by_tool = self._group_by_tool(results)

        self.console.print("\n[bold cyan]Results by Tool[/bold cyan]")

        for tool, tool_results in sorted(by_tool.items()):
            self._print_rich_tool_section(tool, tool_results)

    def _print_rich_tool_section(self, tool: str, tool_results: list[dict[str, Any]]) -> None:
        """
        Print a single tool's results section.
        """
        tool_passed = sum(
            1 for r in tool_results if r.get("success", False) and not r.get("skipped", False)
        )
        tool_total = sum(1 for r in tool_results if not r.get("skipped", False))

        if tool_total > 0:
            tool_rate = (tool_passed / tool_total) * 100
            status_color = "green" if tool_rate == 100 else ("yellow" if tool_rate >= 50 else "red")
            self.console.print(
                f"\n[bold]{tool}[/bold] [{status_color}]({tool_passed}/{tool_total} - {tool_rate:.0f}%)[/{status_color}]",
            )
        else:
            self.console.print(f"\n[bold]{tool}[/bold] [dim](all skipped)[/dim]")

        for r in tool_results:
            self._print_rich_result(r)

    def _print_rich_footer(self) -> None:
        """
        Print the rich report footer.
        """
        self.console.print("\n[dim]" + "=" * 80 + "[/dim]")

    def _report_plain(self, results: list[dict[str, Any]], metadata: dict[str, Any]) -> None:
        """
        Generate plain text report.
        """
        print("\n" + "=" * 80)
        print(self.title)
        print("=" * 80)

        # Connection info
        if "endpoint" in metadata:
            print(f"\nEndpoint: {metadata['endpoint']}")
        if "auth_status" in metadata:
            print(f"Auth: {metadata['auth_status']}")

        # Summary stats
        summary = self._calculate_summary(results)

        print("\nSummary")
        print(f"  Total: {summary['total']}")
        print(f"  Passed: ✓ {summary['passed']}")
        print(f"  Failed: ✗ {summary['failed']}")
        print(f"  Skipped: ⊘ {summary['skipped']}")

        if summary["cached"] > 0:
            print(f"  Cached: 💾 {summary['cached']}")

        print(f"  Pass Rate: {summary['pass_rate']:.1f}%")

        if "duration_seconds" in metadata:
            print(f"  Total Time: {metadata['duration_seconds']:.2f}s")

        if summary["avg_duration_ms"] > 0:
            print(f"  Avg Duration: {summary['avg_duration_ms']:.2f}ms")

        # Results by tool
        by_tool = self._group_by_tool(results)

        print("\nResults by Tool:")
        for tool, tool_results in sorted(by_tool.items()):
            tool_passed = sum(
                1 for r in tool_results if r.get("success", False) and not r.get("skipped", False)
            )
            tool_total = sum(1 for r in tool_results if not r.get("skipped", False))

            if tool_total > 0:
                tool_rate = (tool_passed / tool_total) * 100
                print(f"\n  {tool} ({tool_passed}/{tool_total} - {tool_rate:.0f}%)")
            else:
                print(f"\n  {tool} (all skipped)")

            for r in tool_results:
                self._print_plain_result(r)

        print("\n" + "=" * 80)

    def _print_rich_result(self, result: dict[str, Any]) -> None:
        """
        Print a single test result with rich formatting.
        """
        name = result.get("test_name", "unknown")
        duration = result.get("duration_ms", 0)

        if result.get("cached"):
            icon = "[blue]💾[/blue]"
            status_text = "[blue]cached[/blue]"
        elif result.get("skipped"):
            icon = "[yellow]⊘[/yellow]"
            status_text = "[yellow]skipped[/yellow]"
        elif result.get("success"):
            icon = "[green]✓[/green]"
            status_text = "[green]pass[/green]"
        else:
            icon = "[red]✗[/red]"
            status_text = "[red]fail[/red]"

        self.console.print(f"  {icon} {name} ({duration:.2f}ms) - {status_text}")

        if result.get("error") and not result.get("success"):
            error_preview = str(result["error"])[:80]
            self.console.print(f"    [dim red]{error_preview}[/dim red]")

        # Show recent auth/MFA events for failed tests (redacted)
        if not result.get("success"):
            evs = result.get("events") or []
            if evs:
                preview = [ev.get("type", "") for ev in evs[-3:]]
                self.console.print(f"    [dim]events:[/dim] {', '.join(preview)}")

    def _print_plain_result(self, result: dict[str, Any]) -> None:
        """
        Print a single test result with plain formatting.
        """
        name = result.get("test_name", "unknown")
        duration = result.get("duration_ms", 0)

        if result.get("cached"):
            icon = "💾"
            status = "cached"
        elif result.get("skipped"):
            icon = "⊘"
            status = "skipped"
        elif result.get("success"):
            icon = "✓"
            status = "pass"
        else:
            icon = "✗"
            status = "fail"

        # Show recent auth/MFA events for failed tests (redacted)
        if not result.get("success"):
            evs = result.get("events") or []
            if evs:
                preview = ", ".join(ev.get("type", "") for ev in evs[-3:])
                print(f"      events: {preview}")

            icon = "✗"
            status = "fail"

        print(f"    {icon} {name} ({duration:.2f}ms) - {status}")

        if result.get("error") and not result.get("success"):
            error_preview = str(result["error"])[:80]
            print(f"      {error_preview}")

    def _calculate_summary(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Calculate summary statistics.
        """
        total = len(results)
        passed = sum(1 for r in results if r.get("success", False) and not r.get("skipped", False))
        failed = sum(
            1 for r in results if not r.get("success", False) and not r.get("skipped", False)
        )
        skipped = sum(1 for r in results if r.get("skipped", False))
        cached = sum(1 for r in results if r.get("cached", False))

        total_duration = sum(
            r.get("duration_ms", 0) for r in results if not r.get("skipped", False)
        )
        avg_duration = total_duration / (total - skipped) if (total - skipped) > 0 else 0

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "cached": cached,
            "pass_rate": (passed / (total - skipped) * 100) if (total - skipped) > 0 else 0,
            "avg_duration_ms": avg_duration,
        }

    def _group_by_tool(self, results: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        """
        Group results by tool name.
        """
        by_tool: dict[str, list] = {}
        for result in results:
            tool = result.get("tool_name", "unknown")
            by_tool.setdefault(tool, []).append(result)
        return by_tool
