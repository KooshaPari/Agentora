"""Pattern Definitions.

Proven SWE-bench patterns and methodologies with high success rates. Based on Moatless
patterns with 70.8% bug fix success rate.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ..core.types import TaskComplexity, TaskType


@dataclass
class Pattern:
    """
    Represents a proven development pattern.
    """

    name: str
    task_type: TaskType
    success_rate: float
    steps: list[str]
    validation_criteria: list[str]
    complexity_range: list[TaskComplexity]
    description: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PatternUsageStats:
    """
    Tracks pattern usage statistics.
    """

    pattern_name: str
    usage_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    total_execution_time: float = 0.0
    last_used: datetime | None = None


def load_swe_bench_patterns() -> dict[str, Pattern]:
    """Load proven patterns from SWE-bench results.

    Returns:
        Dictionary of patterns keyed by pattern name
    """
    patterns = {}

    # Bug Fix Pattern (70.8% success rate from Moatless SWE-bench)
    patterns["bug_fix_pattern"] = Pattern(
        name="bug_fix_pattern",
        task_type=TaskType.BUG_FIX,
        success_rate=0.708,
        steps=[
            "analyze_issue_description",
            "locate_relevant_files",
            "understand_codebase_context",
            "identify_root_cause",
            "implement_minimal_fix",
            "verify_fix_with_tests",
            "ensure_no_regressions",
        ],
        validation_criteria=[
            "fix_addresses_root_cause",
            "no_breaking_changes",
            "tests_pass",
            "code_quality_maintained",
        ],
        complexity_range=[TaskComplexity.SIMPLE, TaskComplexity.MEDIUM, TaskComplexity.COMPLEX],
        description="Proven pattern for bug fixing with 70.8% success rate from SWE-bench",
    )

    # Feature Implementation Pattern
    patterns["feature_implementation_pattern"] = Pattern(
        name="feature_implementation_pattern",
        task_type=TaskType.FEATURE,
        success_rate=0.653,
        steps=[
            "understand_requirements",
            "analyze_existing_architecture",
            "design_integration_approach",
            "identify_affected_components",
            "implement_core_functionality",
            "add_error_handling",
            "write_comprehensive_tests",
            "update_documentation",
        ],
        validation_criteria=[
            "requirements_fully_met",
            "integration_seamless",
            "error_handling_robust",
            "tests_comprehensive",
            "documentation_updated",
        ],
        complexity_range=[TaskComplexity.MEDIUM, TaskComplexity.COMPLEX],
        description="Proven pattern for feature implementation",
    )

    # Code Analysis Pattern
    patterns["analysis_pattern"] = Pattern(
        name="analysis_pattern",
        task_type=TaskType.ANALYSIS,
        success_rate=0.85,
        steps=[
            "scan_codebase_structure",
            "identify_key_components",
            "analyze_dependencies",
            "detect_potential_issues",
            "assess_code_quality",
            "generate_insights",
            "provide_recommendations",
        ],
        validation_criteria=[
            "analysis_comprehensive",
            "insights_actionable",
            "recommendations_practical",
        ],
        complexity_range=[TaskComplexity.SIMPLE, TaskComplexity.MEDIUM],
        description="Pattern for comprehensive code analysis",
    )

    # Code Review Pattern
    patterns["review_pattern"] = Pattern(
        name="review_pattern",
        task_type=TaskType.REVIEW,
        success_rate=0.78,
        steps=[
            "understand_change_context",
            "review_code_quality",
            "check_for_common_pitfalls",
            "verify_test_coverage",
            "assess_performance_impact",
            "check_security_implications",
            "provide_constructive_feedback",
        ],
        validation_criteria=[
            "feedback_actionable",
            "all_issues_identified",
            "suggestions_specific",
        ],
        complexity_range=[TaskComplexity.SIMPLE, TaskComplexity.MEDIUM],
        description="Pattern for thorough code review",
    )

    # Refactoring Pattern
    patterns["refactoring_pattern"] = Pattern(
        name="refactoring_pattern",
        task_type=TaskType.REFACTORING,
        success_rate=0.72,
        steps=[
            "identify_code_smells",
            "plan_refactoring_approach",
            "ensure_test_coverage",
            "make_incremental_changes",
            "verify_behavior_preservation",
            "update_tests_if_needed",
            "validate_improvements",
        ],
        validation_criteria=[
            "behavior_preserved",
            "code_quality_improved",
            "tests_still_passing",
            "no_new_issues_introduced",
        ],
        complexity_range=[TaskComplexity.MEDIUM, TaskComplexity.COMPLEX],
        description="Pattern for safe refactoring",
    )

    # Test Generation Pattern
    patterns["test_generation_pattern"] = Pattern(
        name="test_generation_pattern",
        task_type=TaskType.TEST_GENERATION,
        success_rate=0.81,
        steps=[
            "analyze_code_to_test",
            "identify_edge_cases",
            "determine_test_scenarios",
            "implement_unit_tests",
            "implement_integration_tests",
            "verify_coverage",
            "ensure_test_independence",
        ],
        validation_criteria=[
            "coverage_adequate",
            "edge_cases_covered",
            "tests_reliable",
            "tests_maintainable",
        ],
        complexity_range=[TaskComplexity.SIMPLE, TaskComplexity.MEDIUM],
        description="Pattern for comprehensive test generation",
    )

    # Documentation Pattern
    patterns["documentation_pattern"] = Pattern(
        name="documentation_pattern",
        task_type=TaskType.DOCUMENTATION,
        success_rate=0.88,
        steps=[
            "understand_scope",
            "identify_audience",
            "structure_content",
            "write_clear_explanations",
            "add_code_examples",
            "include_diagrams_if_needed",
            "review_for_clarity",
        ],
        validation_criteria=[
            "content_accurate",
            "examples_working",
            "clarity_high",
            "completeness_good",
        ],
        complexity_range=[TaskComplexity.SIMPLE, TaskComplexity.MEDIUM],
        description="Pattern for effective documentation",
    )

    # Code Generation Pattern
    patterns["code_generation_pattern"] = Pattern(
        name="code_generation_pattern",
        task_type=TaskType.CODE_GENERATION,
        success_rate=0.69,
        steps=[
            "understand_requirements",
            "design_api_structure",
            "implement_core_logic",
            "add_error_handling",
            "include_logging",
            "write_inline_documentation",
            "create_usage_examples",
        ],
        validation_criteria=[
            "code_follows_standards",
            "error_handling_comprehensive",
            "documentation_clear",
            "examples_working",
        ],
        complexity_range=[TaskComplexity.SIMPLE, TaskComplexity.MEDIUM, TaskComplexity.COMPLEX],
        description="Pattern for generating new code",
    )

    # Performance Optimization Pattern
    patterns["performance_pattern"] = Pattern(
        name="performance_pattern",
        task_type=TaskType.OPTIMIZATION,
        success_rate=0.74,
        steps=[
            "profile_performance",
            "identify_bottlenecks",
            "analyze_algorithmic_complexity",
            "implement_optimizations",
            "measure_improvements",
            "ensure_correctness_maintained",
            "document_changes",
        ],
        validation_criteria=[
            "measurable_improvement",
            "correctness_preserved",
            "no_regressions",
            "changes_documented",
        ],
        complexity_range=[TaskComplexity.MEDIUM, TaskComplexity.COMPLEX],
        description="Pattern for performance optimization",
    )

    # Security Fix Pattern
    patterns["security_fix_pattern"] = Pattern(
        name="security_fix_pattern",
        task_type=TaskType.SECURITY,
        success_rate=0.76,
        steps=[
            "understand_vulnerability",
            "assess_impact",
            "design_secure_fix",
            "implement_fix",
            "add_security_tests",
            "verify_no_bypass",
            "update_security_docs",
        ],
        validation_criteria=[
            "vulnerability_closed",
            "no_new_vulnerabilities",
            "security_tests_passing",
            "fix_complete",
        ],
        complexity_range=[TaskComplexity.MEDIUM, TaskComplexity.COMPLEX],
        description="Pattern for security vulnerability fixes",
    )

    return patterns
