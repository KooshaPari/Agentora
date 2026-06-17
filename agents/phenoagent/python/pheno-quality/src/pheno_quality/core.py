"""
Core quality analysis classes and interfaces.
"""

import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class SeverityLevel(Enum):
    """
    Quality issue severity levels.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ImpactLevel(Enum):
    """
    Quality issue impact levels.
    """

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


@dataclass
class QualityIssue:
    """
    Represents a quality analysis issue.
    """

    id: str
    type: str
    severity: SeverityLevel
    file: str
    line: int
    column: int
    message: str
    suggestion: str
    confidence: float
    impact: ImpactLevel
    tool: str
    category: str = ""
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary.
        """
        return {
            "id": self.id,
            "type": self.type,
            "severity": self.severity.value,
            "file": self.file,
            "line": self.line,
            "column": self.column,
            "message": self.message,
            "suggestion": self.suggestion,
            "confidence": self.confidence,
            "impact": self.impact.value,
            "tool": self.tool,
            "category": self.category,
            "tags": self.tags,
            "metadata": self.metadata,
        }


@dataclass
class QualityMetrics:
    """
    Quality analysis metrics.
    """

    total_issues: int = 0
    issues_by_severity: dict[str, int] = field(default_factory=dict)
    issues_by_type: dict[str, int] = field(default_factory=dict)
    issues_by_tool: dict[str, int] = field(default_factory=dict)
    issues_by_impact: dict[str, int] = field(default_factory=dict)
    files_affected: int = 0
    quality_score: float = 0.0
    analysis_duration: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary.
        """
        return {
            "total_issues": self.total_issues,
            "issues_by_severity": self.issues_by_severity,
            "issues_by_type": self.issues_by_type,
            "issues_by_tool": self.issues_by_tool,
            "issues_by_impact": self.issues_by_impact,
            "files_affected": self.files_affected,
            "quality_score": self.quality_score,
            "analysis_duration": self.analysis_duration,
        }


@dataclass
class QualityConfig:
    """
    Quality analysis configuration.
    """

    enabled_tools: list[str] = field(default_factory=list)
    thresholds: dict[str, Any] = field(default_factory=dict)
    filters: dict[str, Any] = field(default_factory=dict)
    output_format: str = "json"
    output_path: str | None = None
    include_metadata: bool = True
    parallel_analysis: bool = True
    max_workers: int = 4
    timeout_seconds: int = 300

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary.
        """
        return {
            "enabled_tools": self.enabled_tools,
            "thresholds": self.thresholds,
            "filters": self.filters,
            "output_format": self.output_format,
            "output_path": self.output_path,
            "include_metadata": self.include_metadata,
            "parallel_analysis": self.parallel_analysis,
            "max_workers": self.max_workers,
            "timeout_seconds": self.timeout_seconds,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QualityConfig":
        """
        Create from dictionary.
        """
        return cls(**data)


class QualityReport:
    """
    Comprehensive quality analysis report.
    """

    def __init__(self, project_name: str = "", config: QualityConfig | None = None):
        self.project_name = project_name
        self.config = config or QualityConfig()
        self.issues: list[QualityIssue] = []
        self.metrics = QualityMetrics()
        self.tool_reports: dict[str, dict[str, Any]] = {}
        self.analysis_start_time = time.time()
        self.analysis_end_time: float | None = None
        self.metadata: dict[str, Any] = {}

    def add_issue(self, issue: QualityIssue) -> None:
        """
        Add a quality issue to the report.
        """
        self.issues.append(issue)

    def add_issues(self, issues: list[QualityIssue]) -> None:
        """
        Add multiple quality issues to the report.
        """
        self.issues.extend(issues)

    def add_tool_report(self, tool_name: str, report: dict[str, Any]) -> None:
        """
        Add a tool-specific report.
        """
        self.tool_reports[tool_name] = report

    def finalize(self) -> None:
        """
        Finalize the report and calculate metrics.
        """
        self.analysis_end_time = time.time()
        self.metrics.analysis_duration = self.analysis_end_time - self.analysis_start_time

        # Calculate metrics
        self.metrics.total_issues = len(self.issues)
        self.metrics.files_affected = len({issue.file for issue in self.issues})

        # Count by severity
        for issue in self.issues:
            severity = issue.severity.value
            self.metrics.issues_by_severity[severity] = (
                self.metrics.issues_by_severity.get(severity, 0) + 1
            )

        # Count by type
        for issue in self.issues:
            issue_type = issue.type
            self.metrics.issues_by_type[issue_type] = (
                self.metrics.issues_by_type.get(issue_type, 0) + 1
            )

        # Count by tool
        for issue in self.issues:
            tool = issue.tool
            self.metrics.issues_by_tool[tool] = self.metrics.issues_by_tool.get(tool, 0) + 1

        # Count by impact
        for issue in self.issues:
            impact = issue.impact.value
            self.metrics.issues_by_impact[impact] = self.metrics.issues_by_impact.get(impact, 0) + 1

        # Calculate quality score
        self.metrics.quality_score = self._calculate_quality_score()

    def _calculate_quality_score(self) -> float:
        """
        Calculate overall quality score (0-100)
        """
        if not self.issues:
            return 100.0

        score = 100.0

        # Deduct points based on severity
        for issue in self.issues:
            if issue.severity == SeverityLevel.CRITICAL:
                score -= 10.0
            elif issue.severity == SeverityLevel.HIGH:
                score -= 5.0
            elif issue.severity == SeverityLevel.MEDIUM:
                score -= 2.0
            elif issue.severity == SeverityLevel.LOW:
                score -= 0.5

        return max(score, 0.0)

    def get_issues_by_severity(self, severity: SeverityLevel) -> list[QualityIssue]:
        """
        Get issues filtered by severity.
        """
        return [issue for issue in self.issues if issue.severity == severity]

    def get_issues_by_tool(self, tool: str) -> list[QualityIssue]:
        """
        Get issues filtered by tool.
        """
        return [issue for issue in self.issues if issue.tool == tool]

    def get_issues_by_type(self, issue_type: str) -> list[QualityIssue]:
        """
        Get issues filtered by type.
        """
        return [issue for issue in self.issues if issue.type == issue_type]

    def get_issues_by_file(self, file_path: str) -> list[QualityIssue]:
        """
        Get issues filtered by file.
        """
        return [issue for issue in self.issues if issue.file == file_path]

    def to_dict(self) -> dict[str, Any]:
        """
        Convert report to dictionary.
        """
        return {
            "project_name": self.project_name,
            "config": self.config.to_dict(),
            "issues": [issue.to_dict() for issue in self.issues],
            "metrics": self.metrics.to_dict(),
            "tool_reports": self.tool_reports,
            "analysis_start_time": self.analysis_start_time,
            "analysis_end_time": self.analysis_end_time,
            "metadata": self.metadata,
        }

    def to_json(self, indent: int = 2) -> str:
        """
        Convert report to JSON string.
        """
        return json.dumps(self.to_dict(), indent=indent, default=str)


class QualityAnalyzer(ABC):
    """
    Abstract base class for quality analysis tools.
    """

    def __init__(self, name: str, config: QualityConfig | None = None):
        self.name = name
        self.config = config or QualityConfig()
        self.issues: list[QualityIssue] = []

    @abstractmethod
    def analyze_file(self, file_path: Path) -> list[QualityIssue]:
        """
        Analyze a single file and return quality issues.
        """

    @abstractmethod
    def analyze_directory(self, directory_path: Path) -> list[QualityIssue]:
        """
        Analyze a directory and return quality issues.
        """

    def get_issues(self) -> list[QualityIssue]:
        """
        Get all detected issues.
        """
        return self.issues

    def clear_issues(self) -> None:
        """
        Clear all detected issues.
        """
        self.issues.clear()

    def get_metrics(self) -> dict[str, Any]:
        """
        Get analysis metrics.
        """
        if not self.issues:
            return {"total_issues": 0}

        return {
            "total_issues": len(self.issues),
            "issues_by_severity": {
                severity.value: len([i for i in self.issues if i.severity == severity])
                for severity in SeverityLevel
            },
            "issues_by_type": {
                issue_type: len([i for i in self.issues if i.type == issue_type])
                for issue_type in {i.type for i in self.issues}
            },
        }
