"""
Quality analysis report exporters.
"""

import csv
import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

from .core import QualityReport, SeverityLevel


class QualityExporter(ABC):
    """
    Abstract base class for quality report exporters.
    """

    @abstractmethod
    def export(self, report: QualityReport, output_path: str | Path) -> bool:
        """
        Export a quality report.
        """

    @abstractmethod
    def get_file_extension(self) -> str:
        """
        Get the file extension for this exporter.
        """


class JSONExporter(QualityExporter):
    """
    Export quality reports to JSON format.
    """

    def export(self, report: QualityReport, output_path: str | Path) -> bool:
        """
        Export report to JSON.
        """
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(report.to_dict(), f, indent=2, default=str)

            return True
        except Exception:
            return False

    def get_file_extension(self) -> str:
        return ".json"


class HTMLExporter(QualityExporter):
    """
    Export quality reports to HTML format.
    """

    def export(self, report: QualityReport, output_path: str | Path) -> bool:
        """
        Export report to HTML.
        """
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            html_content = self._generate_html(report)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            return True
        except Exception:
            return False

    def _generate_html(self, report: QualityReport) -> str:
        """
        Generate HTML content.
        """
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Quality Analysis Report - {report.project_name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f4f4f4; padding: 20px; border-radius: 5px; }}
        .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
        .metric {{ background-color: #f9f9f9; padding: 15px; border-radius: 5px; text-align: center; }}
        .metric h3 {{ margin: 0 0 10px 0; color: #333; }}
        .metric .value {{ font-size: 24px; font-weight: bold; color: #007acc; }}
        .issues {{ margin: 20px 0; }}
        .issue {{ border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px; }}
        .issue.high {{ border-left: 5px solid #ff4444; }}
        .issue.medium {{ border-left: 5px solid #ffaa00; }}
        .issue.low {{ border-left: 5px solid #00aa44; }}
        .issue.critical {{ border-left: 5px solid #aa0000; }}
        .issue-header {{ font-weight: bold; margin-bottom: 10px; }}
        .issue-message {{ margin: 5px 0; }}
        .issue-suggestion {{ margin: 5px 0; font-style: italic; color: #666; }}
        .severity-critical {{ color: #aa0000; }}
        .severity-high {{ color: #ff4444; }}
        .severity-medium {{ color: #ffaa00; }}
        .severity-low {{ color: #00aa44; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Quality Analysis Report</h1>
        <p><strong>Project:</strong> {report.project_name}</p>
        <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>Analysis Duration:</strong> {report.metrics.analysis_duration:.2f} seconds</p>
    </div>

    <div class="metrics">
        <div class="metric">
            <h3>Total Issues</h3>
            <div class="value">{report.metrics.total_issues}</div>
        </div>
        <div class="metric">
            <h3>Quality Score</h3>
            <div class="value">{report.metrics.quality_score:.1f}/100</div>
        </div>
        <div class="metric">
            <h3>Files Affected</h3>
            <div class="value">{report.metrics.files_affected}</div>
        </div>
    </div>

    <div class="issues">
        <h2>Issues by Severity</h2>
"""

        # Add issues by severity
        for severity in SeverityLevel:
            issues = report.get_issues_by_severity(severity)
            if issues:
                html += f'<h3 class="severity-{severity.value}">{severity.value.title()} ({len(issues)} issues)</h3>'
                for issue in issues[:10]:  # Limit to first 10 issues per severity
                    html += f"""
                    <div class="issue {severity.value}">
                        <div class="issue-header">
                            {issue.type} in {issue.file}:{issue.line} (Tool: {issue.tool})
                        </div>
                        <div class="issue-message">{issue.message}</div>
                        <div class="issue-suggestion">Suggestion: {issue.suggestion}</div>
                    </div>
                    """
                if len(issues) > 10:
                    html += (
                        f"<p><em>... and {len(issues) - 10} more {severity.value} issues</em></p>"
                    )

        html += """
    </div>
</body>
</html>
"""
        return html

    def get_file_extension(self) -> str:
        return ".html"


class MarkdownExporter(QualityExporter):
    """
    Export quality reports to Markdown format.
    """

    def export(self, report: QualityReport, output_path: str | Path) -> bool:
        """
        Export report to Markdown.
        """
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            markdown_content = self._generate_markdown(report)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)

            return True
        except Exception:
            return False

    def _generate_markdown(self, report: QualityReport) -> str:
        """
        Generate Markdown content.
        """
        md = f"""# Quality Analysis Report

**Project:** {report.project_name}
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Analysis Duration:** {report.metrics.analysis_duration:.2f} seconds

## Summary

- **Total Issues:** {report.metrics.total_issues}
- **Quality Score:** {report.metrics.quality_score:.1f}/100
- **Files Affected:** {report.metrics.files_affected}

## Issues by Severity

"""

        # Add issues by severity
        for severity in SeverityLevel:
            issues = report.get_issues_by_severity(severity)
            if issues:
                md += f"### {severity.value.title()} ({len(issues)} issues)\n\n"
                for issue in issues[:5]:  # Limit to first 5 issues per severity
                    md += f"**{issue.type}** in `{issue.file}:{issue.line}` (Tool: {issue.tool})\n"
                    md += f"- {issue.message}\n"
                    md += f"- *Suggestion:* {issue.suggestion}\n\n"
                if len(issues) > 5:
                    md += f"*... and {len(issues) - 5} more {severity.value} issues*\n\n"

        return md

    def get_file_extension(self) -> str:
        return ".md"


class CSVExporter(QualityExporter):
    """
    Export quality reports to CSV format.
    """

    def export(self, report: QualityReport, output_path: str | Path) -> bool:
        """
        Export report to CSV.
        """
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)

                # Write header
                writer.writerow(
                    [
                        "ID",
                        "Type",
                        "Severity",
                        "File",
                        "Line",
                        "Column",
                        "Message",
                        "Suggestion",
                        "Confidence",
                        "Impact",
                        "Tool",
                        "Category",
                    ],
                )

                # Write issues
                for issue in report.issues:
                    writer.writerow(
                        [
                            issue.id,
                            issue.type,
                            issue.severity.value,
                            issue.file,
                            issue.line,
                            issue.column,
                            issue.message,
                            issue.suggestion,
                            issue.confidence,
                            issue.impact.value,
                            issue.tool,
                            issue.category,
                        ],
                    )

            return True
        except Exception:
            return False

    def get_file_extension(self) -> str:
        return ".csv"


class XMLExporter(QualityExporter):
    """
    Export quality reports to XML format.
    """

    def export(self, report: QualityReport, output_path: str | Path) -> bool:
        """
        Export report to XML.
        """
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            xml_content = self._generate_xml(report)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(xml_content)

            return True
        except Exception:
            return False

    def _generate_xml(self, report: QualityReport) -> str:
        """
        Generate XML content.
        """
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<quality-report project="{report.project_name}" generated="{datetime.now().isoformat()}">
    <summary>
        <total-issues>{report.metrics.total_issues}</total-issues>
        <quality-score>{report.metrics.quality_score:.1f}</quality-score>
        <files-affected>{report.metrics.files_affected}</files-affected>
        <analysis-duration>{report.metrics.analysis_duration:.2f}</analysis-duration>
    </summary>
    <issues>
"""

        for issue in report.issues:
            xml += f"""        <issue id="{issue.id}" type="{issue.type}" severity="{issue.severity.value}">
            <file>{issue.file}</file>
            <line>{issue.line}</line>
            <column>{issue.column}</column>
            <message>{issue.message}</message>
            <suggestion>{issue.suggestion}</suggestion>
            <confidence>{issue.confidence}</confidence>
            <impact>{issue.impact.value}</impact>
            <tool>{issue.tool}</tool>
            <category>{issue.category}</category>
        </issue>
"""

        xml += """    </issues>
</quality-report>"""
        return xml

    def get_file_extension(self) -> str:
        return ".xml"
