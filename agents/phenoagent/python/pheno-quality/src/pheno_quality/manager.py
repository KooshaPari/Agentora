"""
Quality analysis manager for coordinating all quality tools.
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from .config import create_custom_config, list_configs
from .core import QualityConfig, QualityReport
from .exporters import (
    CSVExporter,
    HTMLExporter,
    JSONExporter,
    MarkdownExporter,
    XMLExporter,
)
from .importers import QualityReportImporter
from .plugins import plugin_registry
from .registry import tool_registry


class QualityAnalysisManager:
    """
    Main manager for quality analysis operations.
    """

    def __init__(self, config: QualityConfig | None = None):
        self.config = config or QualityConfig()
        self.exporters = {
            ".json": JSONExporter(),
            ".html": HTMLExporter(),
            ".md": MarkdownExporter(),
            ".csv": CSVExporter(),
            ".xml": XMLExporter(),
        }
        self.importer = QualityReportImporter()
        self._register_default_tools()

    def _register_default_tools(self):
        """
        Register default quality analysis tools.
        """
        from .tools import (
            ArchitecturalValidatorPlugin,
            AtlasHealthPlugin,
            CodeSmellDetectorPlugin,
            IntegrationGatesPlugin,
            PatternDetectorPlugin,
            PerformanceDetectorPlugin,
            SecurityScannerPlugin,
        )

        # Register plugins
        plugin_registry.register_plugin(PatternDetectorPlugin())
        plugin_registry.register_plugin(ArchitecturalValidatorPlugin())
        plugin_registry.register_plugin(PerformanceDetectorPlugin())
        plugin_registry.register_plugin(SecurityScannerPlugin())
        plugin_registry.register_plugin(CodeSmellDetectorPlugin())
        plugin_registry.register_plugin(IntegrationGatesPlugin())
        plugin_registry.register_plugin(AtlasHealthPlugin())

        # Register tools in registry
        for plugin_name in plugin_registry.list_plugins():
            plugin = plugin_registry.get_plugin(plugin_name)
            if plugin:
                analyzer = plugin.create_analyzer()
                tool_registry.register_tool(
                    plugin_name,
                    analyzer.__class__,
                    plugin.get_default_config(),
                    {
                        "version": plugin.version,
                        "description": plugin.description,
                        "supported_extensions": plugin.supported_extensions,
                        "category": "quality_analysis",
                    },
                )

    def analyze_project(
        self,
        project_path: str | Path,
        enabled_tools: list[str] | None = None,
        output_path: str | Path | None = None,
    ) -> QualityReport:
        """
        Analyze a project with all enabled tools.
        """
        project_path = Path(project_path)
        enabled_tools = enabled_tools or self.config.enabled_tools

        if not enabled_tools:
            enabled_tools = tool_registry.list_tools()

        report = QualityReport(project_name=project_path.name, config=self.config)

        # Run analysis with each tool
        if self.config.parallel_analysis:
            self._analyze_parallel(project_path, enabled_tools, report)
        else:
            self._analyze_sequential(project_path, enabled_tools, report)

        # Finalize report
        report.finalize()

        # Export if output path specified
        if output_path:
            self.export_report(report, output_path)

        return report

    def _analyze_parallel(
        self, project_path: Path, enabled_tools: list[str], report: QualityReport,
    ):
        """
        Run analysis in parallel.
        """
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            future_to_tool = {
                executor.submit(self._run_tool, project_path, tool): tool for tool in enabled_tools
            }

            for future in as_completed(future_to_tool, timeout=self.config.timeout_seconds):
                tool = future_to_tool[future]
                try:
                    tool_report = future.result()
                    if tool_report:
                        report.add_tool_report(tool, tool_report)
                except Exception as e:
                    print(f"Error running tool {tool}: {e}")

    def _analyze_sequential(
        self, project_path: Path, enabled_tools: list[str], report: QualityReport,
    ):
        """
        Run analysis sequentially.
        """
        for tool in enabled_tools:
            try:
                tool_report = self._run_tool(project_path, tool)
                if tool_report:
                    report.add_tool_report(tool, tool_report)
            except Exception as e:
                print(f"Error running tool {tool}: {e}")

    def _run_tool(self, project_path: Path, tool_name: str) -> dict[str, Any] | None:
        """
        Run a single tool.
        """
        analyzer = tool_registry.create_tool(tool_name, self.config)
        if not analyzer:
            return None

        start_time = time.time()

        # Analyze the project
        if project_path.is_file():
            issues = analyzer.analyze_file(project_path)
        else:
            issues = analyzer.analyze_directory(project_path)

        duration = time.time() - start_time

        # Add issues to report
        for issue in issues:
            report.add_issue(issue)

        # Return tool report
        return {
            "tool": tool_name,
            "duration": duration,
            "issues_found": len(issues),
            "metrics": analyzer.get_metrics(),
            "status": "completed",
        }

    def export_report(self, report: QualityReport, output_path: str | Path) -> bool:
        """
        Export a quality report.
        """
        output_path = Path(output_path)

        # Determine format from extension
        format_ext = output_path.suffix.lower()
        if format_ext in self.exporters:
            exporter = self.exporters[format_ext]
            return exporter.export(report, output_path)
        # Default to JSON
        exporter = self.exporters[".json"]
        json_path = output_path.with_suffix(".json")
        return exporter.export(report, json_path)

    def import_report(self, file_path: str | Path) -> QualityReport | None:
        """
        Import a quality report.
        """
        return self.importer.import_report(file_path)

    def get_available_tools(self) -> list[dict[str, Any]]:
        """
        Get list of available tools.
        """
        tools = []
        for tool_name in tool_registry.list_tools():
            tool_info = tool_registry.get_tool_info(tool_name)
            if tool_info:
                tools.append(tool_info)
        return tools

    def get_available_configs(self) -> list[str]:
        """
        Get list of available configuration presets.
        """
        return list_configs()

    def create_config(self, preset: str = "default", **overrides) -> QualityConfig:
        """
        Create a configuration from preset with overrides.
        """
        return create_custom_config(preset, **overrides)

    def get_tool_config(self, tool_name: str) -> dict[str, Any]:
        """
        Get configuration for a specific tool.
        """
        return tool_registry.get_tool_config(tool_name)

    def update_tool_config(self, tool_name: str, config: dict[str, Any]) -> None:
        """
        Update configuration for a specific tool.
        """
        tool_registry.update_tool_config(tool_name, config)

    def get_supported_formats(self) -> list[str]:
        """
        Get list of supported export formats.
        """
        return list(self.exporters.keys())

    def generate_summary(self, report: QualityReport) -> dict[str, Any]:
        """
        Generate a summary of the quality report.
        """
        return {
            "project_name": report.project_name,
            "analysis_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_issues": report.metrics.total_issues,
            "quality_score": report.metrics.quality_score,
            "files_affected": report.metrics.files_affected,
            "analysis_duration": report.metrics.analysis_duration,
            "issues_by_severity": report.metrics.issues_by_severity,
            "issues_by_type": report.metrics.issues_by_type,
            "issues_by_tool": report.metrics.issues_by_tool,
            "issues_by_impact": report.metrics.issues_by_impact,
            "quality_status": self._determine_quality_status(report.metrics.quality_score),
            "recommendations": self._generate_recommendations(report),
        }

    def _determine_quality_status(self, quality_score: float) -> str:
        """
        Determine overall quality status.
        """
        if quality_score >= 90:
            return "EXCELLENT"
        if quality_score >= 80:
            return "GOOD"
        if quality_score >= 70:
            return "FAIR"
        if quality_score >= 60:
            return "POOR"
        return "CRITICAL"

    def _generate_recommendations(self, report: QualityReport) -> list[str]:
        """
        Generate recommendations based on the report.
        """
        recommendations = []

        if report.metrics.total_issues == 0:
            recommendations.append("✅ Excellent! No quality issues found.")
            return recommendations

        # Critical issues
        critical_issues = report.metrics.issues_by_severity.get("critical", 0)
        if critical_issues > 0:
            recommendations.append(
                f"🚨 Critical: Fix {critical_issues} critical issues immediately",
            )

        # High severity issues
        high_issues = report.metrics.issues_by_severity.get("high", 0)
        if high_issues > 0:
            recommendations.append(f"⚠️ High: Address {high_issues} high-severity issues")

        # Quality score recommendations
        if report.metrics.quality_score < 60:
            recommendations.append("🔧 Consider major refactoring to improve code quality")
        elif report.metrics.quality_score < 80:
            recommendations.append("📝 Focus on addressing medium and high severity issues")

        # Tool-specific recommendations
        for tool, count in report.metrics.issues_by_tool.items():
            if count > 50:
                recommendations.append(f"🔍 Review {tool} findings - {count} issues detected")

        return recommendations


# Global quality analysis manager
quality_manager = QualityAnalysisManager()
