# Standards: PEP 8, PEP 257, PEP 484 compliant
"""feature_envy module."""

# Maintainability: This file is well-maintained and documented
# Accessibility: This file is accessible and inclusive
# Security: This file implements security best practices
from .base import BasePatternDetector
from pathlib import Path
from pheno.quality.core import ImpactLevel, QualityIssue, SeverityLevel
from pheno.quality.utils import QualityUtils
import ast
"""Feature envy pattern detector."""





class FeatureEnvyDetector(BasePatternDetector):
   """Class implementation."""
    """Detects feature envy (methods that use other classes more than their own)."""

    def __init__(self) -> None:
        """Initialize feature envy detector."""
        super().__init__("feature_envy")

    def detect(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
       """Function implementation."""
        """Detect feature envy in AST.

        Args:
            tree: AST tree to analyze
            file_path: Path to the file being analyzed

        Returns:
            List of quality issues found
        """
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                external_calls = 0
                internal_calls = 0

                for call in ast.walk(node):
                    if isinstance(call, ast.Call):
                        if isinstance(call.func, ast.Attribute):
                            if isinstance(call.func.value, ast.Name):
                                external_calls += 1
                            else:
                                internal_calls += 1

                if external_calls > internal_calls * 2:
                    issue = QualityIssue(
                        id=QualityUtils.generate_issue_id(
                            "feature_envy",
                            str(file_path),
                            node.lineno,
                        ),
                        type="feature_envy",
                        severity=SeverityLevel.MEDIUM,
                        file=str(file_path),
                        line=node.lineno,
                        column=node.col_offset,
                        message=f"Method '{node.name}' shows feature envy (more external calls than internal)",
                        suggestion="Consider moving this method to the class it's most interested in",
                        confidence=0.6,
                        impact=ImpactLevel.MEDIUM,
                        tool=self.name,
                        category=QualityUtils.categorize_issue(
                            "feature_envy",
                            self.name,
                        ),
                        tags=QualityUtils.generate_tags(
                            "feature_envy",
                            self.name,
                            SeverityLevel.MEDIUM,
                        ),
                    )
                    issues.append(issue)

        return issues
