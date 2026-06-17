"""
Quality analysis utility functions.
"""

import hashlib
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from .core import ImpactLevel, SeverityLevel


class QualityUtils:
    """
    Utility functions for quality analysis.
    """

    @staticmethod
    def generate_issue_id(issue_type: str, file_path: str, line: int) -> str:
        """
        Generate a unique issue ID.
        """
        content = f"{issue_type}:{file_path}:{line}"
        return hashlib.md5(content.encode()).hexdigest()[:12]

    @staticmethod
    def generate_report_id(project_name: str) -> str:
        """
        Generate a unique report ID.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{project_name}_{timestamp}_{uuid.uuid4().hex[:8]}"

    @staticmethod
    def normalize_file_path(file_path: str | Path) -> str:
        """
        Normalize file path for consistent comparison.
        """
        return str(Path(file_path).resolve())

    @staticmethod
    def matches_pattern(file_path: str, patterns: list[str]) -> bool:
        """
        Check if file path matches any of the given patterns.
        """
        return any(re.search(pattern, file_path) for pattern in patterns)

    @staticmethod
    def should_exclude_file(file_path: str, exclude_patterns: list[str]) -> bool:
        """
        Check if file should be excluded based on patterns.
        """
        return QualityUtils.matches_pattern(file_path, exclude_patterns)

    @staticmethod
    def get_file_extension(file_path: str) -> str:
        """
        Get file extension.
        """
        return Path(file_path).suffix.lower()

    @staticmethod
    def is_python_file(file_path: str) -> bool:
        """
        Check if file is a Python file.
        """
        return QualityUtils.get_file_extension(file_path) == ".py"

    @staticmethod
    def is_source_file(file_path: str) -> bool:
        """
        Check if file is a source code file.
        """
        extensions = [".py", ".js", ".ts", ".go", ".rs", ".java", ".cpp", ".c", ".h"]
        return QualityUtils.get_file_extension(file_path) in extensions

    @staticmethod
    def calculate_confidence_score(
        severity: SeverityLevel, impact: ImpactLevel, metadata: dict[str, Any],
    ) -> float:
        """
        Calculate confidence score for an issue.
        """
        base_confidence = 0.5

        # Adjust based on severity
        severity_multiplier = {
            SeverityLevel.CRITICAL: 0.9,
            SeverityLevel.HIGH: 0.8,
            SeverityLevel.MEDIUM: 0.7,
            SeverityLevel.LOW: 0.6,
        }

        # Adjust based on impact
        impact_multiplier = {
            ImpactLevel.CRITICAL: 0.9,
            ImpactLevel.HIGH: 0.8,
            ImpactLevel.MEDIUM: 0.7,
            ImpactLevel.LOW: 0.6,
        }

        confidence = base_confidence
        confidence *= severity_multiplier.get(severity, 0.7)
        confidence *= impact_multiplier.get(impact, 0.7)

        # Adjust based on metadata
        if "pattern_matches" in metadata:
            confidence += 0.1 * min(metadata["pattern_matches"], 5)

        if "context_evidence" in metadata:
            confidence += 0.1 * metadata["context_evidence"]

        return min(confidence, 1.0)

    @staticmethod
    def categorize_issue(issue_type: str, tool: str) -> str:
        """
        Categorize an issue based on type and tool.
        """
        categories = {
            "pattern_detector": {
                "god_object": "Architecture",
                "feature_envy": "Architecture",
                "data_clump": "Data Design",
                "shotgun_surgery": "Maintainability",
                "divergent_change": "Maintainability",
                "parallel_inheritance": "Inheritance",
                "lazy_class": "Design",
                "inappropriate_intimacy": "Coupling",
                "message_chain": "Coupling",
                "middle_man": "Design",
                "incomplete_library_class": "Library Usage",
                "temporary_field": "Data Design",
                "refused_bequest": "Inheritance",
                "alternative_classes": "Design",
                "duplicate_code_blocks": "Duplication",
            },
            "architectural_validator": {
                "hexagonal_architecture": "Architecture",
                "clean_architecture": "Architecture",
                "solid_principles": "Design Principles",
                "layered_architecture": "Architecture",
                "domain_driven_design": "Architecture",
                "microservices_patterns": "Architecture",
                "cqrs_pattern": "Architecture",
                "event_sourcing": "Architecture",
            },
            "performance_detector": {
                "n_plus_one_query": "Database",
                "memory_leak": "Memory",
                "blocking_calls": "I/O",
                "inefficient_loops": "Algorithm",
                "unnecessary_computations": "Algorithm",
                "large_data_structures": "Memory",
                "synchronous_operations": "Concurrency",
                "resource_leaks": "Resource Management",
                "inefficient_algorithms": "Algorithm",
                "excessive_io": "I/O",
            },
            "security_scanner": {
                "sql_injection": "Security",
                "xss_vulnerability": "Security",
                "insecure_deserialization": "Security",
                "authentication_bypass": "Security",
                "authorization_flaw": "Security",
                "input_validation": "Security",
                "cryptographic_weakness": "Security",
                "information_disclosure": "Security",
                "insecure_direct_object_reference": "Security",
                "security_misconfiguration": "Security",
            },
            "code_smell_detector": {
                "long_method": "Maintainability",
                "large_class": "Maintainability",
                "long_parameter_list": "Maintainability",
                "duplicate_code": "Duplication",
                "dead_code": "Maintainability",
                "magic_number": "Maintainability",
                "deep_nesting": "Readability",
                "long_chain": "Readability",
                "too_many_returns": "Readability",
                "high_complexity": "Complexity",
                "god_object": "Architecture",
                "feature_envy": "Coupling",
                "data_clump": "Data Design",
                "primitive_obsession": "Data Design",
                "speculative_generality": "Design",
                "shotgun_surgery": "Maintainability",
                "divergent_change": "Maintainability",
                "parallel_inheritance": "Inheritance",
                "lazy_class": "Design",
                "inappropriate_intimacy": "Coupling",
                "message_chain": "Coupling",
                "middle_man": "Design",
                "incomplete_library_class": "Library Usage",
                "temporary_field": "Data Design",
                "refused_bequest": "Inheritance",
                "alternative_classes": "Design",
                "duplicate_code_blocks": "Duplication",
            },
            "integration_gates": {
                "api_contracts": "API Design",
                "data_flow_validation": "Data Flow",
                "error_handling": "Error Handling",
                "logging_validation": "Logging",
                "security_validation": "Security",
                "monitoring_integration": "Monitoring",
                "deployment_readiness": "Deployment",
                "backward_compatibility": "Compatibility",
            },
            "atlas_health": {
                "coverage_analysis": "Testing",
                "complexity_analysis": "Complexity",
                "duplication_analysis": "Duplication",
                "dead_code_detection": "Maintainability",
                "security_analysis": "Security",
                "performance_analysis": "Performance",
                "documentation_analysis": "Documentation",
            },
        }

        tool_categories = categories.get(tool, {})
        return tool_categories.get(issue_type, "General")

    @staticmethod
    def generate_tags(issue_type: str, tool: str, severity: SeverityLevel) -> list[str]:
        """
        Generate tags for an issue.
        """
        tags = [tool, issue_type, severity.value.lower()]

        # Add category-based tags
        category = QualityUtils.categorize_issue(issue_type, tool)
        tags.append(category.lower().replace(" ", "_"))

        # Add severity-based tags
        if severity in [SeverityLevel.HIGH, SeverityLevel.CRITICAL]:
            tags.append("priority")

        if severity == SeverityLevel.CRITICAL:
            tags.append("urgent")

        return list(set(tags))  # Remove duplicates

    @staticmethod
    def format_duration(seconds: float) -> str:
        """
        Format duration in human-readable format.
        """
        if seconds < 60:
            return f"{seconds:.2f}s"
        if seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.2f}m"
        hours = seconds / 3600
        return f"{hours:.2f}h"

    @staticmethod
    def format_file_size(bytes_size: int) -> str:
        """
        Format file size in human-readable format.
        """
        for unit in ["B", "KB", "MB", "GB"]:
            if bytes_size < 1024:
                return f"{bytes_size:.2f}{unit}"
            bytes_size /= 1024
        return f"{bytes_size:.2f}TB"

    @staticmethod
    def calculate_quality_trend(current_score: float, previous_score: float) -> str:
        """
        Calculate quality trend.
        """
        if current_score > previous_score:
            return "improving"
        if current_score < previous_score:
            return "declining"
        return "stable"

    @staticmethod
    def get_priority_score(severity: SeverityLevel, impact: ImpactLevel, confidence: float) -> int:
        """
        Calculate priority score (1-10, higher is more important)
        """
        severity_scores = {
            SeverityLevel.CRITICAL: 10,
            SeverityLevel.HIGH: 8,
            SeverityLevel.MEDIUM: 5,
            SeverityLevel.LOW: 2,
        }

        impact_scores = {
            ImpactLevel.CRITICAL: 10,
            ImpactLevel.HIGH: 8,
            ImpactLevel.MEDIUM: 5,
            ImpactLevel.LOW: 2,
        }

        base_score = severity_scores.get(severity, 5)
        impact_multiplier = impact_scores.get(impact, 5) / 10.0
        confidence_multiplier = confidence

        priority = int(base_score * impact_multiplier * confidence_multiplier)
        return min(max(priority, 1), 10)

    @staticmethod
    def group_issues_by_file(issues: list[Any]) -> dict[str, list[Any]]:
        """
        Group issues by file path.
        """
        grouped = {}
        for issue in issues:
            file_path = issue.file if hasattr(issue, "file") else str(issue)
            if file_path not in grouped:
                grouped[file_path] = []
            grouped[file_path].append(issue)
        return grouped

    @staticmethod
    def group_issues_by_type(issues: list[Any]) -> dict[str, list[Any]]:
        """
        Group issues by type.
        """
        grouped = {}
        for issue in issues:
            issue_type = issue.type if hasattr(issue, "type") else str(issue)
            if issue_type not in grouped:
                grouped[issue_type] = []
            grouped[issue_type].append(issue)
        return grouped

    @staticmethod
    def group_issues_by_severity(issues: list[Any]) -> dict[str, list[Any]]:
        """
        Group issues by severity.
        """
        grouped = {}
        for issue in issues:
            severity = issue.severity.value if hasattr(issue, "severity") else "unknown"
            if severity not in grouped:
                grouped[severity] = []
            grouped[severity].append(issue)
        return grouped
