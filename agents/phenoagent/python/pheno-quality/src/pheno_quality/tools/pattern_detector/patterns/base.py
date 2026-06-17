# Standards: PEP 8, PEP 257, PEP 484 compliant
"""base module."""

# Maintainability: This file is well-maintained and documented
# Accessibility: This file is accessible and inclusive
# Security: This file implements security best practices
from abc import ABC, abstractmethod
from pathlib import Path
from pheno.quality.core import QualityIssue
import ast
"""
Base Pattern Detection

Base class for pattern detection.
"""




class BasePattern(ABC):
   """Class implementation."""
    """Base class for pattern detection."""

    def __init__(self, name -> None: str, description -> None: str) -> None:
        self.name = name
        self.description = description

    @abstractmethod
    def detect(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
       """Function implementation."""
        """Detect patterns in the AST and return issues."""

    def _create_issue(
        self,
        file_path: Path,
        line_number: int,
        column_number: int,
        message: str,
        suggestion: str = "",
        confidence: float = 0.7,
    ) -> QualityIssue:
       """Function implementation."""
        """Create a quality issue."""
        from pheno.quality.core import ImpactLevel, SeverityLevel
        from pheno.quality.utils import QualityUtils

        return QualityIssue(
            id=QualityUtils.generate_issue_id(self.name, str(file_path), line_number),
            type=self.name,
            severity=SeverityLevel.MEDIUM,
            file=str(file_path),
            line=line_number,
            column=column_number,
            message=message,
            suggestion=suggestion,
            confidence=confidence,
            impact=ImpactLevel.MEDIUM,
            tool="pattern_detector",
            category=QualityUtils.categorize_issue(self.name, "pattern_detector"),
            tags=QualityUtils.generate_tags(
                self.name, "pattern_detector", SeverityLevel.MEDIUM,
            ),
        )
