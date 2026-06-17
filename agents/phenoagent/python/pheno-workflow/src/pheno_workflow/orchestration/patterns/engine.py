"""Pattern Engine.

Provides proven SWE-bench patterns and methodologies for high-success-rate automated
software development. Based on Moatless patterns with 70.8% bug fix success rate.
"""

import logging
from datetime import datetime
from typing import Any

from ..core.types import TaskComplexity, TaskType
from .definitions import Pattern, PatternUsageStats, load_swe_bench_patterns

logger = logging.getLogger(__name__)


class PatternEngine:
    """
    Provides proven SWE-bench patterns and methodologies to guide task execution for
    optimal success rates.
    """

    def __init__(self, config: dict[str, Any]):
        """Initialize the pattern engine.

        Args:
            config: Configuration dictionary for pattern engine
        """
        self.config = config
        self.patterns = load_swe_bench_patterns()
        self.pattern_usage_stats: dict[str, PatternUsageStats] = {}

        logger.info(f"Pattern Engine initialized with {len(self.patterns)} patterns")

    async def get_patterns(
        self,
        task_type: TaskType,
        description: str,
        complexity: TaskComplexity | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Get relevant patterns for a task.

        Args:
            task_type: Type of development task
            description: Task description
            complexity: Optional task complexity
            context: Optional task context

        Returns:
            Dictionary containing selected pattern and guidance
        """
        # Find patterns matching the task type
        matching_patterns = [
            pattern for pattern in self.patterns.values() if pattern.task_type == task_type
        ]

        if not matching_patterns:
            logger.warning(f"No patterns found for task type: {task_type.value}")
            return {}

        # Filter by complexity if provided
        if complexity:
            matching_patterns = [p for p in matching_patterns if complexity in p.complexity_range]

        if not matching_patterns:
            logger.warning(
                f"No patterns found for {task_type.value} with complexity {complexity.value}",
            )
            return {}

        # Select the pattern with highest success rate
        selected_pattern = max(matching_patterns, key=lambda p: p.success_rate)

        # Update usage statistics
        await self._update_pattern_usage(selected_pattern.name)

        # Customize pattern based on context
        customized_steps = await self._customize_pattern_steps(
            selected_pattern, description, context,
        )

        logger.info(
            f"Selected pattern '{selected_pattern.name}' for {task_type.value} "
            f"(success rate: {selected_pattern.success_rate:.1%})",
        )

        return {
            "selected_pattern": selected_pattern.name,
            "success_rate": selected_pattern.success_rate,
            "steps": customized_steps,
            "validation_criteria": selected_pattern.validation_criteria,
            "description": selected_pattern.description,
            "guidance": await self._generate_guidance(selected_pattern, description, context),
        }

    async def _customize_pattern_steps(
        self, pattern: Pattern, description: str, context: dict[str, Any] | None,
    ) -> list[str]:
        """Customize pattern steps based on specific task context.

        Args:
            pattern: Selected pattern
            description: Task description
            context: Task context

        Returns:
            Customized list of steps
        """
        customized_steps = pattern.steps.copy()

        # Add context-specific customizations
        if context:
            if context.get("repository_url"):
                # Add repository-specific steps
                if "analyze_issue_description" in customized_steps:
                    idx = customized_steps.index("analyze_issue_description")
                    customized_steps.insert(idx + 1, "clone_and_setup_repository")

            if context.get("has_tests", True):
                # Ensure test-related steps are included
                if (
                    "verify_fix_with_tests" not in customized_steps
                    and pattern.task_type == TaskType.BUG_FIX
                ):
                    customized_steps.append("run_existing_tests")

            if context.get("requires_documentation"):
                # Add documentation steps
                if "update_documentation" not in customized_steps:
                    customized_steps.append("update_relevant_documentation")

        return customized_steps

    async def _generate_guidance(
        self, pattern: Pattern, description: str, context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Generate specific guidance for applying the pattern.

        Args:
            pattern: Selected pattern
            description: Task description
            context: Task context

        Returns:
            Guidance dictionary
        """
        guidance = {
            "approach": f"Follow the {pattern.name} with {pattern.success_rate:.1%} success rate",
            "key_principles": [],
            "common_pitfalls": [],
            "success_indicators": pattern.validation_criteria,
        }

        # Add pattern-specific guidance
        if pattern.task_type == TaskType.BUG_FIX:
            guidance["key_principles"] = [
                "Focus on minimal, targeted fixes",
                "Understand root cause before implementing",
                "Preserve existing functionality",
                "Add tests to prevent regression",
            ]
            guidance["common_pitfalls"] = [
                "Fixing symptoms instead of root cause",
                "Making changes too broad in scope",
                "Not testing edge cases",
                "Breaking existing functionality",
            ]

        elif pattern.task_type == TaskType.FEATURE:
            guidance["key_principles"] = [
                "Design for maintainability",
                "Follow existing code patterns",
                "Implement comprehensive error handling",
                "Write tests before implementation",
            ]
            guidance["common_pitfalls"] = [
                "Not considering integration points",
                "Insufficient error handling",
                "Poor test coverage",
                "Not following existing patterns",
            ]

        elif pattern.task_type == TaskType.ANALYSIS:
            guidance["key_principles"] = [
                "Be thorough and systematic",
                "Focus on actionable insights",
                "Consider multiple perspectives",
                "Provide clear recommendations",
            ]
            guidance["common_pitfalls"] = [
                "Surface-level analysis",
                "Missing critical components",
                "Vague recommendations",
                "Not considering context",
            ]

        elif pattern.task_type == TaskType.REVIEW:
            guidance["key_principles"] = [
                "Provide constructive feedback",
                "Focus on important issues",
                "Explain the reasoning",
                "Suggest improvements",
            ]
            guidance["common_pitfalls"] = [
                "Being overly critical",
                "Missing security issues",
                "Not checking test coverage",
                "Ignoring performance implications",
            ]

        elif pattern.task_type == TaskType.REFACTOR:
            guidance["key_principles"] = [
                "Make incremental changes",
                "Preserve functionality",
                "Improve code quality",
                "Update tests accordingly",
            ]
            guidance["common_pitfalls"] = [
                "Making too many changes at once",
                "Breaking existing functionality",
                "Not updating tests",
                "Introducing performance regressions",
            ]

        return guidance

    async def validate_step_completion(
        self, pattern_name: str, step: str, result: dict[str, Any],
    ) -> bool:
        """Validate that a pattern step was completed successfully.

        Args:
            pattern_name: Name of the pattern being followed
            step: Step that was completed
            result: Result of the step execution

        Returns:
            True if step was completed successfully
        """
        if pattern_name not in self.patterns:
            return False

        pattern = self.patterns[pattern_name]

        # Basic validation
        if not result.get("success", False):
            return False

        # Step-specific validation
        if step == "verify_fix_with_tests" and pattern.task_type == TaskType.BUG_FIX:
            return result.get("tests_passed", False)

        if step == "implement_core_functionality" and pattern.task_type == TaskType.FEATURE:
            return result.get("functionality_implemented", False)

        if step == "verify_coverage" and pattern.task_type == TaskType.TEST:
            return result.get("coverage_threshold_met", False)

        # Default validation
        return True

    async def _update_pattern_usage(self, pattern_name: str):
        """Update usage statistics for a pattern.

        Args:
            pattern_name: Name of the pattern used
        """
        if pattern_name not in self.pattern_usage_stats:
            self.pattern_usage_stats[pattern_name] = PatternUsageStats(pattern_name=pattern_name)

        stats = self.pattern_usage_stats[pattern_name]
        stats.usage_count += 1
        stats.last_used = datetime.now()

    async def update_pattern_outcome(self, pattern_name: str, success: bool, execution_time: float):
        """Update pattern outcome statistics.

        Args:
            pattern_name: Name of the pattern used
            success: Whether the pattern execution was successful
            execution_time: Time taken to execute the pattern
        """
        if pattern_name not in self.pattern_usage_stats:
            return

        stats = self.pattern_usage_stats[pattern_name]

        if success:
            stats.success_count += 1
        else:
            stats.failure_count += 1

        stats.total_execution_time += execution_time

    async def get_pattern_analytics(self) -> dict[str, Any]:
        """Get analytics on pattern usage and effectiveness.

        Returns:
            Analytics dictionary
        """
        analytics = {"total_patterns": len(self.patterns), "pattern_performance": {}}

        for pattern_name, stats in self.pattern_usage_stats.items():
            total_uses = stats.success_count + stats.failure_count
            success_rate = stats.success_count / max(total_uses, 1)
            avg_execution_time = stats.total_execution_time / max(total_uses, 1)

            analytics["pattern_performance"][pattern_name] = {
                "usage_count": stats.usage_count,
                "success_rate": success_rate,
                "average_execution_time": avg_execution_time,
                "theoretical_success_rate": self.patterns[pattern_name].success_rate,
                "performance_delta": success_rate - self.patterns[pattern_name].success_rate,
                "last_used": stats.last_used.isoformat() if stats.last_used else None,
            }

        return analytics

    async def get_status(self) -> dict[str, Any]:
        """Get pattern engine status.

        Returns:
            Status dictionary
        """
        total_usage = sum(stats.usage_count for stats in self.pattern_usage_stats.values())

        most_used = max(
            self.pattern_usage_stats.items(),
            key=lambda x: x[1].usage_count,
            default=("none", PatternUsageStats("none")),
        )

        return {
            "total_patterns": len(self.patterns),
            "total_pattern_usage": total_usage,
            "most_used_pattern": most_used[0],
            "patterns_by_task_type": self._get_patterns_by_task_type(),
        }

    def _get_patterns_by_task_type(self) -> dict[str, int]:
        """
        Get count of patterns by task type.
        """
        counts = {}
        for pattern in self.patterns.values():
            task_type = pattern.task_type.value
            counts[task_type] = counts.get(task_type, 0) + 1
        return counts

    async def shutdown(self):
        """
        Shutdown pattern engine.
        """
        logger.info("Pattern Engine shutdown complete")
