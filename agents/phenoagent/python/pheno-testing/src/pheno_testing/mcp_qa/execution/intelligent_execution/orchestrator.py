"""Main orchestrator combining all optimization strategies."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .dependency_analyzer import DependencyAnalyzer
from .failfast import FailFastOptimizer
from .predictive_engine import PredictiveExecutionEngine
from .prewarmer import TestPreWarmer
from .sharding import TestSharding
from .types import TestExecution

logger = logging.getLogger(__name__)


class IntelligentExecutionOrchestrator:
    """Main orchestrator combining all optimization strategies."""

    def __init__(
        self,
        history_file: Path = None,
        warmup_enabled: bool = True,
        fail_fast: bool = False,
        failure_threshold: int = 1,
        shard_index: int = 0,
        total_shards: int = 1,
        max_workers: int = 4,
    ):
        self.pre_warmer = TestPreWarmer()
        self.execution_engine = PredictiveExecutionEngine(history_file)
        self.dependency_analyzer = DependencyAnalyzer()
        self.fail_fast_optimizer = FailFastOptimizer(
            enabled=fail_fast, failure_threshold=failure_threshold
        )
        self.sharding = TestSharding(shard_index, total_shards)
        self.warmup_enabled = warmup_enabled
        self.max_workers = max_workers

    async def prepare_execution(
        self, tests: List[TestExecution], warmup_config: Optional[Dict[str, Any]] = None
    ) -> List[TestExecution]:
        """Prepare tests for execution with all optimizations."""
        logger.info(f"Preparing {len(tests)} tests for execution...")

        if self.warmup_enabled and warmup_config:
            await self.pre_warmer.warmup_all(**warmup_config)

        for test in tests:
            if test.dependencies:
                self.dependency_analyzer.add_dependencies(test.test_id, test.dependencies)

        cycles = self.dependency_analyzer.detect_cycles()
        if cycles:
            logger.warning(f"Found {len(cycles)} dependency cycles")
            for cycle in cycles:
                logger.warning(f"  Cycle: {' -> '.join(cycle)}")

        sharded_tests = self.sharding.shard_balanced(tests)

        total_runtime = self.execution_engine.predict_total_runtime(sharded_tests)
        logger.info(f"Predicted runtime: {total_runtime:.1f}s")

        return sharded_tests

    def schedule_execution(self, tests: List[TestExecution]) -> List[List[TestExecution]]:
        """Create optimized execution schedule.

        Returns batches respecting dependencies and optimizing parallelism.
        """
        test_ids = [t.test_id for t in tests]
        levels = self.dependency_analyzer.topological_sort(test_ids)

        all_batches = []
        for level in levels:
            level_tests = [t for t in tests if t.test_id in level]
            batches = self.execution_engine.schedule_tests(level_tests, self.max_workers)
            all_batches.extend(batches)

        return all_batches

    def record_result(
        self, test_id: str, duration: float, failed: bool, category: str, tool: str
    ) -> bool:
        """Record test result.

        Returns True if execution should continue, False if should stop.
        """
        self.execution_engine.record_execution(test_id, duration, failed)

        if failed:
            return self.fail_fast_optimizer.record_failure(test_id, category, tool)

        return True

    def finalize(self) -> None:
        """Finalize execution and save state."""
        self.execution_engine.save_history()
        logger.info("Execution orchestrator finalized")
