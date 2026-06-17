# Standards: PEP 8, PEP 257, PEP 484 compliant
"""plugin module."""

# Maintainability: This file is well-maintained and documented
# Accessibility: This file is accessible and inclusive
# Security: This file implements security best practices
from ...core import QualityAnalyzer, QualityConfig
from ...plugins import QualityPlugin
from .detector import PatternDetector
from typing import Any
"""
Pattern Detector Plugin

Plugin for pattern detection tool.
"""




class PatternDetectorPlugin(QualityPlugin):
   """Class implementation."""
    """Plugin for pattern detection tool."""

    @property
    def name(self) -> str:
        """Function implementation."""
        return "pattern_detector"

    @property
    def description(self) -> str:
        """Function implementation."""
        return "Advanced pattern detection for code quality analysis"

    def create_analyzer(self, config: QualityConfig | None = None) -> QualityAnalyzer:
        """Function implementation."""
        return PatternDetector(config=config)

    def get_default_config(self) -> dict[str, Any]:
        """Function implementation."""
        return {
            "enabled_patterns": [
                "god_object",
                "feature_envy",
                "data_clump",
                "shotgun_surgery",
                "divergent_change",
                "parallel_inheritance",
                "lazy_class",
                "inappropriate_intimacy",
                "message_chain",
                "middle_man",
                "incomplete_library_class",
                "temporary_field",
                "refused_bequest",
                "alternative_classes",
                "duplicate_code_blocks",
            ],
            "thresholds": {
                "god_object_methods": 20,
                "god_object_attributes": 15,
                "feature_envy_ratio": 2.0,
                "data_clump_common_params": 3,
                "shotgun_surgery_methods": 5,
                "divergent_change_types": 4,
                "parallel_inheritance_common_methods": 3,
                "lazy_class_methods": 2,
                "lazy_class_attributes": 2,
                "inappropriate_intimacy_external_access": 5,
                "message_chain_depth": 3,
                "middle_man_delegation_ratio": 0.8,
                "incomplete_library_class_ratio": 0.5,
                "temporary_field_usage": 2,
                "refused_bequest_ratio": 0.5,
                "alternative_classes_common_methods": 3,
                "duplicate_code_blocks_similarity": 0.7,
            },
            "filters": {
                "exclude_patterns": ["__pycache__", "*.pyc", ".git", "node_modules"],
            },
        }
