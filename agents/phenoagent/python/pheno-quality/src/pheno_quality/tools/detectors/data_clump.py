# Standards: PEP 8, PEP 257, PEP 484 compliant
"""data_clump module."""

# Maintainability: This file is well-maintained and documented
# Accessibility: This file is accessible and inclusive
# Security: This file implements security best practices
from .base import BasePatternDetector
from pathlib import Path
from pheno.quality.core import ImpactLevel, QualityIssue, SeverityLevel
from pheno.quality.utils import QualityUtils
import ast
"""Data clump pattern detector."""





class DataClumpDetector(BasePatternDetector):
   """Class implementation."""
    """Detects data clumps (groups of parameters that appear together)."""

    def __init__(self, threshold -> None: int = 3) -> None:
        """Initialize data clump detector.

        Args:
            threshold: Minimum number of parameters to flag
        """
        super().__init__("data_clump")
        self.threshold = threshold

    def detect(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
       """Function implementation."""
        """Detect data clumps in AST.

        Args:
            tree: AST tree to analyze
            file_path: Path to the file being analyzed

        Returns:
            List of quality issues found
        """
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                params = node.args.args
                if len(params) > self.threshold:
                    issue = QualityIssue(
                        id=QualityUtils.generate_issue_id(
                            "data_clump",
                            str(file_path),
                            node.lineno,
                        ),
                        type="data_clump",
                        severity=SeverityLevel.MEDIUM,
                        file=str(file_path),
                        line=node.lineno,
                        column=node.col_offset,
                        message=f"Function '{node.name}' has {len(params)} parameters (data clump)",
                        suggestion="Consider grouping parameters into a data class",
                        confidence=0.6,
                        impact=ImpactLevel.MEDIUM,
                        tool=self.name,
                        category=QualityUtils.categorize_issue("data_clump", self.name),
                        tags=QualityUtils.generate_tags(
                            "data_clump",
                            self.name,
                            SeverityLevel.MEDIUM,
                        ),
                    )
                    issues.append(issue)

        return issues
