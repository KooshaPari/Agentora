"""
JSON Reporter - Machine-readable test result export.

Exports test results as structured JSON including:
- Test results with all metadata
- Summary statistics
- Test run metadata
- Proper sanitization of non-serializable objects
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


class JSONReporter:
    """
    JSON reporter for machine-readable output.
    """

    def __init__(self, output_path: str):
        """Initialize JSON reporter.

        Args:
            output_path: Path to write JSON report file
        """
        self.output_path = Path(output_path)

    def report(self, results: List[Dict[str, Any]], metadata: Dict[str, Any]) -> None:
        """Export report as JSON.

        Args:
            results: List of test result dictionaries
            metadata: Test run metadata

        The JSON structure includes:
        - generated_at: ISO timestamp of report generation
        - metadata: Test run metadata (endpoint, auth, etc.)
        - summary: Calculated summary statistics
        - results: Sanitized test results
        """
        # Sanitize results to remove non-JSON-serializable objects
        sanitized_results = []
        for result in results:
            sanitized = {}
            for key, value in result.items():
                # Skip functions, methods, and other non-serializable types
                if callable(value):
                    continue
                try:
                    json.dumps(value)  # Test if serializable
                    sanitized[key] = value
                except (TypeError, ValueError):
                    # Convert to string as fallback
                    sanitized[key] = str(value)

            sanitized_results.append(sanitized)

        # Build complete report
        report = {
            "generated_at": datetime.now().isoformat(),
            "metadata": self._sanitize_metadata(metadata),
            "summary": self._calculate_summary(results),
            "results": sanitized_results,
        }

        # Write to file
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_path.write_text(json.dumps(report, indent=2))
        print(f"JSON Report: {self.output_path}")

    def _sanitize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize metadata for JSON serialization.
        """
        sanitized = {}
        for key, value in metadata.items():
            if callable(value):
                continue
            try:
                json.dumps(value)
                sanitized[key] = value
            except (TypeError, ValueError):
                sanitized[key] = str(value)
        return sanitized

    def _calculate_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate summary statistics.

        Returns:
            Dictionary with:
            - total: Total number of tests
            - passed: Number of passed tests
            - failed: Number of failed tests
            - skipped: Number of skipped tests
            - cached: Number of cached results
            - pass_rate: Percentage of tests that passed
            - avg_duration_ms: Average test duration in milliseconds
            - total_duration_ms: Total test duration in milliseconds
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
            "total_duration_ms": total_duration,
        }
