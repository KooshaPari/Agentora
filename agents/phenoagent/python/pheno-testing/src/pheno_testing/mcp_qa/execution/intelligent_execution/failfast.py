"""Fail-fast strategies to save execution time."""

import logging
from collections import defaultdict
from typing import Dict, List, Optional, Set

from .types import TestExecution

logger = logging.getLogger(__name__)


class FailFastOptimizer:
    """Implements fail-fast strategies to save execution time."""

    def __init__(
        self,
        enabled: bool = False,
        failure_threshold: int = 1,
        stop_on_category_failure: bool = True,
    ):
        self.enabled = enabled
        self.failure_threshold = failure_threshold
        self.stop_on_category_failure = stop_on_category_failure
        self.failures: Dict[str, List[str]] = defaultdict(list)
        self.stopped_categories: Set[str] = set()
        self.stopped_tools: Set[str] = set()

    def record_failure(self, test_id: str, category: str, tool: str) -> bool:
        """Record a test failure.

        Returns True if execution should continue, False if should stop.
        """
        if not self.enabled:
            return True

        self.failures[category].append(test_id)

        if self.stop_on_category_failure:
            self.stopped_categories.add(category)
            self.stopped_tools.add(tool)
            logger.warning(f"Stopping category '{category}' due to failure in {test_id}")
            return False

        total_failures = sum(len(f) for f in self.failures.values())
        if total_failures >= self.failure_threshold:
            logger.warning(
                f"Reached failure threshold ({self.failure_threshold}), stopping execution"
            )
            return False

        return True

    def should_skip_test(self, test: TestExecution) -> bool:
        """Check if a test should be skipped due to fail-fast."""
        if not self.enabled:
            return False

        if test.category in self.stopped_categories:
            logger.debug(f"Skipping {test.test_id} - category stopped")
            return True

        if test.tool in self.stopped_tools:
            logger.debug(f"Skipping {test.test_id} - tool stopped")
            return True

        return False

    def get_skip_reason(self, test: TestExecution) -> Optional[str]:
        """Get reason why a test was skipped."""
        if test.category in self.stopped_categories:
            return f"Category '{test.category}' stopped after failure"
        if test.tool in self.stopped_tools:
            return f"Tool '{test.tool}' stopped after failure"
        return None
