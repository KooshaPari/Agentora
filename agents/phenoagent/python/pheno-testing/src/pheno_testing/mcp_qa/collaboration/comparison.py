"""
Test result comparison across endpoints.
"""

from typing import Any, Dict, List

from .models import TestResult


class ResultComparator:
    """
    Compare test results across endpoints.
    """

    def compare_results(self, results: Dict[str, TestResult]) -> Dict[str, Any]:
        """
        Compare results from different endpoints.
        """
        if not results:
            return {"status": "no_results"}

        all_success = all(r.success for r in results.values())

        durations = [r.duration for r in results.values()]
        avg_duration = sum(durations) / len(durations)
        min_duration = min(durations)
        max_duration = max(durations)

        discrepancies = []
        success_values = [r.success for r in results.values()]
        if not all(s == success_values[0] for s in success_values):
            discrepancies.append(
                {
                    "type": "success_mismatch",
                    "details": {endpoint: r.success for endpoint, r in results.items()},
                }
            )

        return {
            "status": "all_passed" if all_success else "some_failed",
            "total_endpoints": len(results),
            "successful_endpoints": sum(1 for r in results.values() if r.success),
            "statistics": {
                "avg_duration": avg_duration,
                "min_duration": min_duration,
                "max_duration": max_duration,
                "duration_variance": max_duration - min_duration,
            },
            "discrepancies": discrepancies,
            "results": {endpoint: result.to_dict() for endpoint, result in results.items()},
        }

    def find_performance_outliers(
        self, results: Dict[str, TestResult], threshold: float = 2.0
    ) -> List[str]:
        """
        Find endpoints with significantly different performance.
        """
        durations = [r.duration for r in results.values()]
        if not durations:
            return []

        avg_duration = sum(durations) / len(durations)
        outliers = []

        for endpoint, result in results.items():
            if result.duration > avg_duration * threshold:
                outliers.append(endpoint)

        return outliers

    def generate_comparison_report(self, results: Dict[str, TestResult]) -> str:
        """
        Generate a human-readable comparison report.
        """
        comparison = self.compare_results(results)

        report = "Test Comparison Report\n"
        report += f"{'=' * 50}\n\n"
        report += f"Status: {comparison['status']}\n"
        report += f"Endpoints: {comparison['successful_endpoints']}/{comparison['total_endpoints']} passed\n\n"

        stats = comparison["statistics"]
        report += "Performance Statistics:\n"
        report += f"  Average Duration: {stats['avg_duration']:.3f}s\n"
        report += f"  Fastest: {stats['min_duration']:.3f}s\n"
        report += f"  Slowest: {stats['max_duration']:.3f}s\n"
        report += f"  Variance: {stats['duration_variance']:.3f}s\n\n"

        if comparison["discrepancies"]:
            report += "Discrepancies Found:\n"
            for disc in comparison["discrepancies"]:
                report += f"  - {disc['type']}: {disc['details']}\n"

        return report
