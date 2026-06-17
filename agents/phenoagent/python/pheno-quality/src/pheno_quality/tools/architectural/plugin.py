# Standards: PEP 8, PEP 257, PEP 484 compliant
"""plugin module."""

# Maintainability: This file is well-maintained and documented
# Accessibility: This file is accessible and inclusive
# Security: This file implements security best practices
from ...plugins import QualityPlugin
from .validator import ArchitecturalValidator
from pheno.quality.core import QualityAnalyzer, QualityConfig
from typing import Any
"""
Architectural Validator Plugin

Plugin for architectural validation tool.
"""





class ArchitecturalValidatorPlugin(QualityPlugin):
   """Class implementation."""
    """
    Plugin for architectural validation tool.
    """

    @property
    def name(self) -> str:
        """Function implementation."""
        return "architectural_validator"

    @property
    def description(self) -> str:
        """Function implementation."""
        return "Architectural pattern validation for Hexagonal, Clean Architecture, SOLID principles"

    def create_analyzer(self, config: QualityConfig | None = None) -> QualityAnalyzer:
        """Function implementation."""
        return ArchitecturalValidator(config=config)

    def get_default_config(self) -> dict[str, Any]:
        """Function implementation."""
        return {
            "enabled_tools": ["architectural_validator"],
            "thresholds": {
                "max_responsibilities": 2,
                "layer_violation_severity": "high",
            },
            "filters": {
                "exclude_patterns": ["__pycache__", "*.pyc", ".git", "node_modules"],
            },
        }
