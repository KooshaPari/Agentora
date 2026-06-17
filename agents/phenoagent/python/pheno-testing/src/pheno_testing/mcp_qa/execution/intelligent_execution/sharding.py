"""Test sharding for parallel execution across machines/processes."""

import hashlib
import logging
from collections import defaultdict
from typing import Dict, List

from .types import TestExecution

logger = logging.getLogger(__name__)


class TestSharding:
    """Divides tests across multiple machines/processes."""

    def __init__(self, shard_index: int = 0, total_shards: int = 1):
        if total_shards < 1:
            raise ValueError("total_shards must be >= 1")
        if shard_index < 0 or shard_index >= total_shards:
            raise ValueError(f"shard_index must be in range [0, {total_shards})")

        self.shard_index = shard_index
        self.total_shards = total_shards
        logger.info(f"Sharding: {shard_index + 1}/{total_shards}")

    def shard_by_hash(self, tests: List[TestExecution]) -> List[TestExecution]:
        """Shard tests using consistent hashing."""
        if self.total_shards == 1:
            return tests

        sharded = []
        for test in tests:
            test_hash = int(hashlib.md5(test.test_id.encode()).hexdigest(), 16)
            if test_hash % self.total_shards == self.shard_index:
                test.shard_id = self.shard_index
                sharded.append(test)

        logger.info(
            f"Shard {self.shard_index + 1}/{self.total_shards}: {len(sharded)}/{len(tests)} tests"
        )
        return sharded

    def shard_by_category(self, tests: List[TestExecution]) -> List[TestExecution]:
        """Shard tests by category."""
        if self.total_shards == 1:
            return tests

        categories: Dict[str, List[TestExecution]] = defaultdict(list)
        for test in tests:
            categories[test.category].append(test)

        sorted_categories = sorted(categories.items())
        sharded = []

        for idx, (category, cat_tests) in enumerate(sorted_categories):
            if idx % self.total_shards == self.shard_index:
                for test in cat_tests:
                    test.shard_id = self.shard_index
                    sharded.append(test)

        logger.info(
            f"Shard {self.shard_index + 1}/{self.total_shards}: {len(sharded)}/{len(tests)} tests"
        )
        return sharded

    def shard_by_tool(self, tests: List[TestExecution]) -> List[TestExecution]:
        """Shard tests by tool."""
        if self.total_shards == 1:
            return tests

        tools: Dict[str, List[TestExecution]] = defaultdict(list)
        for test in tests:
            tools[test.tool].append(test)

        sorted_tools = sorted(tools.items())
        sharded = []

        for idx, (tool, tool_tests) in enumerate(sorted_tools):
            if idx % self.total_shards == self.shard_index:
                for test in tool_tests:
                    test.shard_id = self.shard_index
                    sharded.append(test)

        logger.info(
            f"Shard {self.shard_index + 1}/{self.total_shards}: {len(sharded)}/{len(tests)} tests"
        )
        return sharded

    def shard_balanced(self, tests: List[TestExecution]) -> List[TestExecution]:
        """Shard tests with load balancing.

        Distributes tests evenly by estimated duration.
        """
        if self.total_shards == 1:
            return tests

        sorted_tests = sorted(tests, key=lambda t: t.estimated_duration, reverse=True)

        shard_times = [0.0] * self.total_shards
        shard_tests: List[List[TestExecution]] = [[] for _ in range(self.total_shards)]

        for test in sorted_tests:
            min_shard = min(range(self.total_shards), key=lambda i: shard_times[i])
            shard_tests[min_shard].append(test)
            shard_times[min_shard] += test.estimated_duration
            test.shard_id = min_shard

        sharded = shard_tests[self.shard_index]
        logger.info(
            f"Shard {self.shard_index + 1}/{self.total_shards}: "
            f"{len(sharded)}/{len(tests)} tests "
            f"(~{shard_times[self.shard_index]:.1f}s)"
        )
        return sharded
