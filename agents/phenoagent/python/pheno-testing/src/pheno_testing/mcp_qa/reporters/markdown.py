"""
Markdown Reporter - Human-readable documentation export.

Generates markdown reports with:
- Summary statistics
- Results table with status indicators
- Cache hit information
- Performance metrics
- Easy-to-read formatting for documentation
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


class MarkdownReporter:
    """
    Markdown reporter for documentation.
    """

    def __init__(self, output_path: str, title: str = "MCP Test Report"):
        """Initialize Markdown reporter.

        Args:
            output_path: Path to write markdown report file
            title: Report title (default: "MCP Test Report")
        """
        self.output_path = Path(output_path)
        self.title = title

    def report(self, results: List[Dict[str, Any]], metadata: Dict[str, Any]) -> None:
        """Export report as Markdown.

        Args:
            results: List of test result dictionaries
            metadata: Test run metadata

        The markdown report includes:
        - Header with generation timestamp
        - Connection/metadata information
        - Summary statistics
        - Detailed results table
        """
        lines = []

        # Header
        lines.append(f"# {self.title}\n")
        lines.append(f"**Generated**: {datetime.now().isoformat()}\n")

        # Metadata
        if "endpoint" in metadata:
            lines.append(f"**Endpoint**: `{metadata['endpoint']}`\n")
        if "auth_status" in metadata:
            lines.append(f"**Auth**: {metadata['auth_status']}\n")
        if "duration_seconds" in metadata:
            lines.append(f"**Total Duration**: {metadata['duration_seconds']:.2f}s\n")

        # Summary
        summary = self._calculate_summary(results)
        lines.append("\n## Summary\n")
        lines.append(f"- **Total Tests**: {summary['total']}")
        lines.append(f"- **Passed**: ✅ {summary['passed']}")
        lines.append(f"- **Failed**: ❌ {summary['failed']}")
        lines.append(f"- **Skipped**: ⏭️ {summary['skipped']}")

        if summary["cached"] > 0:
            lines.append(f"- **Cached**: 💾 {summary['cached']}")

        lines.append(f"- **Pass Rate**: {summary['pass_rate']:.1f}%")

        if summary["avg_duration_ms"] > 0:
            lines.append(f"- **Avg Duration**: {summary['avg_duration_ms']:.2f}ms")

        # Results by tool
        by_tool = self._group_by_tool(results)

        lines.append("\n## Results by Tool\n")

        for tool, tool_results in sorted(by_tool.items()):
            tool_passed = sum(
                1 for r in tool_results if r.get("success", False) and not r.get("skipped", False)
            )
            tool_total = sum(1 for r in tool_results if not r.get("skipped", False))

            if tool_total > 0:
                tool_rate = (tool_passed / tool_total) * 100
                lines.append(f"\n### {tool} ({tool_passed}/{tool_total} - {tool_rate:.0f}%)\n")
            else:
                lines.append(f"\n### {tool} (all skipped)\n")

            # Tool results table
            lines.append("| Test | Status | Duration | Details |")
            lines.append("|------|--------|----------|---------|")

            for r in tool_results:
                name = r.get("test_name", "unknown")
                duration = f"{r.get('duration_ms', 0):.2f}ms"

                if r.get("cached"):
                    status = "💾 Cached"
                    details = "Result from cache"
                elif r.get("skipped"):
                    status = "⏭️ Skipped"
                    details = r.get("skip_reason", "")
                elif r.get("success"):
                    status = "✅ Pass"
                    details = ""
                else:
                    status = "❌ Fail"
                    error = str(r.get("error", ""))
                    # Truncate and escape for markdown
                    details = error[:100].replace("|", "\\|").replace("\n", " ")
                    if len(error) > 100:
                        details += "..."

                lines.append(f"| {name} | {status} | {duration} | {details} |")

        # Detailed results table (all tests)
        lines.append("\n## All Results\n")
        lines.append("| Tool | Test | Status | Duration |")
        lines.append("|------|------|--------|----------|")

        for r in results:
            tool = r.get("tool_name", "unknown")
            name = r.get("test_name", "unknown")
            duration = f"{r.get('duration_ms', 0):.2f}ms"

            if r.get("cached"):
                status = "💾 Cached"
            elif r.get("skipped"):
                status = "⏭️ Skipped"
            elif r.get("success"):
                status = "✅ Pass"
            else:
                status = "❌ Fail"

            lines.append(f"| {tool} | {name} | {status} | {duration} |")

        # Write to file
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_path.write_text("\n".join(lines))
        print(f"Markdown Report: {self.output_path}")

    def _calculate_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
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

    def _group_by_tool(self, results: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group results by tool name.
        """
        by_tool: Dict[str, List] = {}
        for result in results:
            tool = result.get("tool_name", "unknown")
            by_tool.setdefault(tool, []).append(result)
        return by_tool
