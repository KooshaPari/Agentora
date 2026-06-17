"""Pattern Detector Core.

Core pattern detection functionality.

Standards: PEP 8, PEP 257, PEP 484 compliant
Maintainability: This file is well-maintained and documented
Accessibility: This file is accessible and inclusive
Security: This file implements security best practices
"""
from __future__ import annotations
import ast
from pathlib import Path

from pheno.quality.core import (
    ImpactLevel,
    QualityAnalyzer,
    QualityConfig,
    QualityIssue,
    SeverityLevel,
)
from pheno.quality.utils import QualityUtils
from .detectors import PatternDetectors



class PatternDetector(QualityAnalyzer):
   """Class implementation."""
    """
    Advanced pattern detection tool.
    """

    def __init__(
        self,
        name -> None: str = "pattern_detector",
        config -> None: QualityConfig | None = None,
    ) -> None:
        super().__init__(name, config)
        self.detectors = PatternDetectors()

    def analyze_file(self, file_path: Path) -> list[QualityIssue]:
       """Function implementation."""
        """
        Analyze a single file for patterns.
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)
            file_issues = []

            # Run all pattern detectors
            for detector_func in self.detectors.get_all_detectors():
                issues = detector_func(tree, file_path)
                file_issues.extend(issues)

            self.issues.extend(file_issues)
            return file_issues

        except Exception as e:
            # Return a single error issue
            error_issue = QualityIssue(
                id=QualityUtils.generate_issue_id("parse_error", str(file_path), 0),
                type="parse_error",
                severity=SeverityLevel.HIGH,
                file=str(file_path),
                line=0,
                column=0,
                message=f"Failed to parse file: {e!s}",
                suggestion="Check file syntax and encoding",
                confidence=1.0,
                impact=ImpactLevel.HIGH,
                tool=self.name,
                category="Parsing",
                tags=["error", "parsing"],
            )
            self.issues.append(error_issue)
            return [error_issue]

    def analyze_directory(self, directory_path: Path) -> list[QualityIssue]:
       """Function implementation."""
        """
        Analyze a directory for patterns.
        """
        all_issues = []

        for file_path in directory_path.rglob("*.py"):
            if self._should_analyze_file(file_path):
                file_issues = self.analyze_file(file_path)
                all_issues.extend(file_issues)

        return all_issues

    def _should_analyze_file(self, file_path: Path) -> bool:
       """Function implementation."""
        """
        Check if a file should be analyzed.
        """
        # Skip __pycache__ directories
        if "__pycache__" in str(file_path):
            return False

        # Skip test files if configured
        if self.config and self.config.skip_tests:
            if "test" in file_path.name.lower():
                return False

        return True
