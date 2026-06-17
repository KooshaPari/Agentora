"""Predictive execution engine that learns from historical test times."""

import json
import logging
import time
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List

from .types import TestExecution, TestMetrics

logger = logging.getLogger(__name__)


class PredictiveExecutionEngine:
    """Learns from historical test times to optimize execution order."""

    def __init__(self, history_file: Path = None):
        self.history_file = history_file or Path(".test_history.json")
        self.metrics: Dict[str, TestMetrics] = {}
        self.load_history()

    def load_history(self) -> None:
        """Load historical test metrics."""
        if self.history_file.exists():
            try:
                with open(self.history_file, "r") as f:
                    data = json.load(f)
                    self.metrics = {k: TestMetrics(**v) for k, v in data.items()}
                logger.info(f"Loaded history for {len(self.metrics)} tests")
            except Exception as e:
                logger.warning(f"Failed to load test history: {e}")
                self.metrics = {}
        else:
            logger.info("No test history found, starting fresh")
            self.metrics = {}

    def save_history(self) -> None:
        """Save historical test metrics."""
        try:
            data = {k: asdict(v) for k, v in self.metrics.items()}
            with open(self.history_file, "w") as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Saved history for {len(self.metrics)} tests")
        except Exception as e:
            logger.error(f"Failed to save test history: {e}")

    def record_execution(
        self, test_id: str, duration: float, failed: bool = False, dependencies: List[str] = None
    ) -> None:
        """Record test execution metrics."""
        if dependencies is None:
            dependencies = []

        current_time = time.time()

        if test_id in self.metrics:
            metric = self.metrics[test_id]
            total_duration = metric.avg_duration * metric.run_count + duration
            metric.run_count += 1
            metric.avg_duration = total_duration / metric.run_count
            metric.last_duration = duration
            metric.last_run = current_time
            if failed:
                metric.failure_count += 1
            metric.dependencies = list(set(metric.dependencies + dependencies))
        else:
            self.metrics[test_id] = TestMetrics(
                test_id=test_id,
                avg_duration=duration,
                run_count=1,
                last_duration=duration,
                failure_count=1 if failed else 0,
                last_run=current_time,
                dependencies=dependencies,
            )

    def get_estimated_duration(self, test_id: str) -> float:
        """Get estimated duration for a test."""
        if test_id in self.metrics:
            metric = self.metrics[test_id]
            return 0.7 * metric.avg_duration + 0.3 * metric.last_duration
        return 1.0

    def schedule_tests(
        self, tests: List[TestExecution], max_workers: int = 4
    ) -> List[List[TestExecution]]:
        """Schedule tests for optimal execution.

        Returns batches of tests that can run in parallel.
        """
        logger.info(f"Scheduling {len(tests)} tests with {max_workers} workers")

        for test in tests:
            test.estimated_duration = self.get_estimated_duration(test.test_id)

        sorted_tests = sorted(tests, key=lambda t: t.estimated_duration, reverse=True)

        batches = []
        current_batch = []
        current_batch_time = 0.0

        for test in sorted_tests:
            if len(current_batch) < max_workers:
                current_batch.append(test)
                current_batch_time = max(current_batch_time, test.estimated_duration)
            else:
                batches.append(current_batch)
                current_batch = [test]
                current_batch_time = test.estimated_duration

        if current_batch:
            batches.append(current_batch)

        logger.info(f"Created {len(batches)} execution batches")
        return batches

    def predict_total_runtime(self, tests: List[TestExecution]) -> float:
        """Predict total runtime for test suite."""
        total_duration = 0.0
        for test in tests:
            duration = self.get_estimated_duration(test.test_id)
            total_duration += duration
        return total_duration

    def adaptive_worker_allocation(
        self, tests: List[TestExecution], total_workers: int = 8
    ) -> Dict[str, int]:
        """Allocate workers adaptively based on test durations.

        Slow tests get more workers, fast tests share workers.
        """
        total_time = sum(self.get_estimated_duration(t.test_id) for t in tests)

        if total_time == 0:
            return {"default": total_workers}

        category_times: Dict[str, float] = defaultdict(float)
        for test in tests:
            duration = self.get_estimated_duration(test.test_id)
            category_times[test.category] += duration

        allocations = {}
        remaining_workers = total_workers

        for category, cat_time in sorted(category_times.items(), key=lambda x: x[1], reverse=True):
            proportion = cat_time / total_time
            workers = max(1, int(proportion * total_workers))
            workers = min(workers, remaining_workers)
            allocations[category] = workers
            remaining_workers -= workers

            if remaining_workers <= 0:
                break

        if remaining_workers > 0:
            for category in allocations:
                if remaining_workers <= 0:
                    break
                allocations[category] += 1
                remaining_workers -= 1

        logger.info(f"Worker allocation: {allocations}")
        return allocations
