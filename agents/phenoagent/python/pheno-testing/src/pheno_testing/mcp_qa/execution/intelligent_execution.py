"""Intelligent test execution optimizer for maximizing test suite performance.

Features:
- Pre-warming connections and fixtures
- Predictive execution based on historical data
- Dependency-aware scheduling
- Fail-fast optimization
- Test sharding for parallel execution
"""

import asyncio
import hashlib
import importlib
import json
import logging
import re
import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class TestMetrics:
    """
    Historical metrics for a test.
    """

    test_id: str
    avg_duration: float
    run_count: int
    last_duration: float
    failure_count: int
    last_run: float
    dependencies: List[str] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


@dataclass
class TestExecution:
    """
    Test execution request.
    """

    test_id: str
    test_func: Callable
    category: str
    tool: str
    estimated_duration: float = 0.0
    dependencies: List[str] = None
    shard_id: Optional[int] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class TestPreWarmer:
    """
    Pre-warms connections, fixtures, and resources before test execution.
    """

    def __init__(self):
        self.warmed_connections: Set[str] = set()
        self.compiled_patterns: Dict[str, re.Pattern] = {}
        self.loaded_modules: Dict[str, Any] = {}
        self._warmup_tasks: List[asyncio.Task] = []

    async def warm_mcp_connections(self, connection_configs: List[Dict[str, Any]]) -> None:
        """
        Pre-establish MCP connections in parallel.
        """
        logger.info(f"Pre-warming {len(connection_configs)} MCP connections...")

        async def warm_single_connection(config: Dict[str, Any]) -> None:
            try:
                conn_id = config.get("connection_id", "unknown")
                # Simulate connection establishment
                await asyncio.sleep(0.1)  # Replace with actual connection logic
                self.warmed_connections.add(conn_id)
                logger.debug(f"Warmed connection: {conn_id}")
            except Exception as e:
                logger.warning(f"Failed to warm connection {config}: {e}")

        tasks = [warm_single_connection(config) for config in connection_configs]
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info(f"Warmed {len(self.warmed_connections)} connections")

    async def warm_oauth_tokens(self, oauth_configs: List[Dict[str, Any]]) -> None:
        """
        Pre-authenticate OAuth tokens in background.
        """
        logger.info(f"Pre-authenticating {len(oauth_configs)} OAuth tokens...")

        async def authenticate_token(config: Dict[str, Any]) -> None:
            try:
                # Simulate OAuth authentication
                await asyncio.sleep(0.2)  # Replace with actual OAuth logic
                logger.debug(f"Authenticated OAuth for {config.get('service', 'unknown')}")
            except Exception as e:
                logger.warning(f"Failed to authenticate OAuth {config}: {e}")

        tasks = [authenticate_token(config) for config in oauth_configs]
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("OAuth pre-authentication complete")

    async def warm_fixtures(self, fixtures: List[Callable]) -> Dict[str, Any]:
        """
        Pre-initialize test fixtures in parallel.
        """
        logger.info(f"Warming up {len(fixtures)} fixtures...")
        warmed_fixtures = {}

        async def warm_fixture(fixture: Callable) -> Tuple[str, Any]:
            try:
                fixture_name = fixture.__name__
                # Call fixture to initialize it
                if asyncio.iscoroutinefunction(fixture):
                    result = await fixture()
                else:
                    result = fixture()
                return fixture_name, result
            except Exception as e:
                logger.warning(f"Failed to warm fixture {fixture.__name__}: {e}")
                return fixture.__name__, None

        tasks = [warm_fixture(f) for f in fixtures]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for name, result in results:
            if result is not None:
                warmed_fixtures[name] = result

        logger.info(f"Warmed {len(warmed_fixtures)} fixtures")
        return warmed_fixtures

    def preload_modules(self, module_names: List[str]) -> None:
        """
        Pre-load test modules in parallel.
        """
        logger.info(f"Pre-loading {len(module_names)} modules...")

        for module_name in module_names:
            try:
                module = importlib.import_module(module_name)
                self.loaded_modules[module_name] = module
                logger.debug(f"Loaded module: {module_name}")
            except Exception as e:
                logger.warning(f"Failed to load module {module_name}: {e}")

        logger.info(f"Loaded {len(self.loaded_modules)} modules")

    def compile_patterns(self, patterns: Dict[str, str]) -> None:
        """
        Pre-compile regex patterns.
        """
        logger.info(f"Pre-compiling {len(patterns)} regex patterns...")

        for name, pattern in patterns.items():
            try:
                self.compiled_patterns[name] = re.compile(pattern)
                logger.debug(f"Compiled pattern: {name}")
            except Exception as e:
                logger.warning(f"Failed to compile pattern {name}: {e}")

        logger.info(f"Compiled {len(self.compiled_patterns)} patterns")

    async def warmup_all(
        self,
        connections: Optional[List[Dict[str, Any]]] = None,
        oauth_configs: Optional[List[Dict[str, Any]]] = None,
        fixtures: Optional[List[Callable]] = None,
        modules: Optional[List[str]] = None,
        patterns: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Warm up all resources in parallel.
        """
        logger.info("Starting comprehensive warmup...")
        start_time = time.time()

        tasks = []
        if connections:
            tasks.append(self.warm_mcp_connections(connections))
        if oauth_configs:
            tasks.append(self.warm_oauth_tokens(oauth_configs))

        fixture_task = None
        if fixtures:
            fixture_task = self.warm_fixtures(fixtures)
            tasks.append(fixture_task)

        # Run async tasks in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Run synchronous tasks
        if modules:
            self.preload_modules(modules)
        if patterns:
            self.compile_patterns(patterns)

        warmed_fixtures = {}
        if fixture_task and results:
            warmed_fixtures = results[-1] if isinstance(results[-1], dict) else {}

        duration = time.time() - start_time
        logger.info(f"Warmup completed in {duration:.2f}s")

        return {
            "fixtures": warmed_fixtures,
            "connections": list(self.warmed_connections),
            "modules": list(self.loaded_modules.keys()),
            "patterns": list(self.compiled_patterns.keys()),
            "duration": duration,
        }


class PredictiveExecutionEngine:
    """
    Learns from historical test times to optimize execution order.
    """

    def __init__(self, history_file: Path = None):
        self.history_file = history_file or Path(".test_history.json")
        self.metrics: Dict[str, TestMetrics] = {}
        self.load_history()

    def load_history(self) -> None:
        """
        Load historical test metrics.
        """
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
        """
        Save historical test metrics.
        """
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
        """
        Record test execution metrics.
        """
        if dependencies is None:
            dependencies = []

        current_time = time.time()

        if test_id in self.metrics:
            metric = self.metrics[test_id]
            # Update running average
            total_duration = metric.avg_duration * metric.run_count + duration
            metric.run_count += 1
            metric.avg_duration = total_duration / metric.run_count
            metric.last_duration = duration
            metric.last_run = current_time
            if failed:
                metric.failure_count += 1
            # Update dependencies
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
        """
        Get estimated duration for a test.
        """
        if test_id in self.metrics:
            # Weighted average: 70% historical average, 30% last run
            metric = self.metrics[test_id]
            return 0.7 * metric.avg_duration + 0.3 * metric.last_duration
        return 1.0  # Default estimate for new tests

    def schedule_tests(
        self, tests: List[TestExecution], max_workers: int = 4
    ) -> List[List[TestExecution]]:
        """Schedule tests for optimal execution.

        Returns batches of tests that can run in parallel.
        """
        logger.info(f"Scheduling {len(tests)} tests with {max_workers} workers")

        # Estimate durations
        for test in tests:
            test.estimated_duration = self.get_estimated_duration(test.test_id)

        # Sort by estimated duration (slowest first)
        sorted_tests = sorted(tests, key=lambda t: t.estimated_duration, reverse=True)

        # Group into batches for parallel execution
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
        """
        Predict total runtime for test suite.
        """
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
        # Calculate total estimated time
        total_time = sum(self.get_estimated_duration(t.test_id) for t in tests)

        if total_time == 0:
            return {"default": total_workers}

        # Group tests by category
        category_times: Dict[str, float] = defaultdict(float)
        for test in tests:
            duration = self.get_estimated_duration(test.test_id)
            category_times[test.category] += duration

        # Allocate workers proportionally
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

        # Distribute remaining workers
        if remaining_workers > 0:
            for category in allocations:
                if remaining_workers <= 0:
                    break
                allocations[category] += 1
                remaining_workers -= 1

        logger.info(f"Worker allocation: {allocations}")
        return allocations


class DependencyAnalyzer:
    """
    Analyzes and respects test dependencies.
    """

    def __init__(self):
        self.dependency_graph: Dict[str, Set[str]] = defaultdict(set)
        self.reverse_graph: Dict[str, Set[str]] = defaultdict(set)

    def add_dependency(self, test_id: str, depends_on: str) -> None:
        """Add a dependency: test_id depends on depends_on."""
        self.dependency_graph[test_id].add(depends_on)
        self.reverse_graph[depends_on].add(test_id)

    def add_dependencies(self, test_id: str, depends_on: List[str]) -> None:
        """
        Add multiple dependencies for a test.
        """
        for dep in depends_on:
            self.add_dependency(test_id, dep)

    def get_dependencies(self, test_id: str) -> Set[str]:
        """
        Get all tests that this test depends on.
        """
        return self.dependency_graph.get(test_id, set())

    def get_dependents(self, test_id: str) -> Set[str]:
        """
        Get all tests that depend on this test.
        """
        return self.reverse_graph.get(test_id, set())

    def topological_sort(self, test_ids: List[str]) -> List[List[str]]:
        """Sort tests respecting dependencies.

        Returns levels where each level can run in parallel.
        """
        # Build in-degree map
        in_degree = {test_id: 0 for test_id in test_ids}
        for test_id in test_ids:
            for dep in self.dependency_graph.get(test_id, set()):
                if dep in in_degree:
                    in_degree[test_id] += 1

        # Find tests with no dependencies
        levels = []
        current_level = [t for t in test_ids if in_degree[t] == 0]

        while current_level:
            levels.append(current_level)
            next_level = []

            for test_id in current_level:
                # Reduce in-degree for dependents
                for dependent in self.reverse_graph.get(test_id, set()):
                    if dependent in in_degree:
                        in_degree[dependent] -= 1
                        if in_degree[dependent] == 0:
                            next_level.append(dependent)

            current_level = next_level

        # Check for cycles
        scheduled = sum(len(level) for level in levels)
        if scheduled < len(test_ids):
            logger.warning(
                f"Dependency cycle detected: {scheduled}/{len(test_ids)} tests scheduled"
            )

        logger.info(f"Created {len(levels)} dependency levels")
        return levels

    def detect_cycles(self) -> List[List[str]]:
        """
        Detect dependency cycles in the graph.
        """
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(node: str, path: List[str]) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in self.dependency_graph.get(node, set()):
                if neighbor not in visited:
                    dfs(neighbor, path.copy())
                elif neighbor in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(neighbor)
                    cycles.append(path[cycle_start:] + [neighbor])

            rec_stack.remove(node)

        for node in self.dependency_graph:
            if node not in visited:
                dfs(node, [])

        return cycles


class FailFastOptimizer:
    """
    Implements fail-fast strategies to save execution time.
    """

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

        # Check if should stop category
        if self.stop_on_category_failure:
            self.stopped_categories.add(category)
            self.stopped_tools.add(tool)
            logger.warning(f"Stopping category '{category}' due to failure in {test_id}")
            return False

        # Check failure threshold
        total_failures = sum(len(f) for f in self.failures.values())
        if total_failures >= self.failure_threshold:
            logger.warning(
                f"Reached failure threshold ({self.failure_threshold}), " f"stopping execution"
            )
            return False

        return True

    def should_skip_test(self, test: TestExecution) -> bool:
        """
        Check if a test should be skipped due to fail-fast.
        """
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
        """
        Get reason why a test was skipped.
        """
        if test.category in self.stopped_categories:
            return f"Category '{test.category}' stopped after failure"
        if test.tool in self.stopped_tools:
            return f"Tool '{test.tool}' stopped after failure"
        return None


class TestSharding:
    """
    Divides tests across multiple machines/processes.
    """

    def __init__(self, shard_index: int = 0, total_shards: int = 1):
        if total_shards < 1:
            raise ValueError("total_shards must be >= 1")
        if shard_index < 0 or shard_index >= total_shards:
            raise ValueError(f"shard_index must be in range [0, {total_shards})")

        self.shard_index = shard_index
        self.total_shards = total_shards
        logger.info(f"Sharding: {shard_index + 1}/{total_shards}")

    def shard_by_hash(self, tests: List[TestExecution]) -> List[TestExecution]:
        """
        Shard tests using consistent hashing.
        """
        if self.total_shards == 1:
            return tests

        sharded = []
        for test in tests:
            test_hash = int(hashlib.md5(test.test_id.encode()).hexdigest(), 16)
            if test_hash % self.total_shards == self.shard_index:
                test.shard_id = self.shard_index
                sharded.append(test)

        logger.info(
            f"Shard {self.shard_index + 1}/{self.total_shards}: "
            f"{len(sharded)}/{len(tests)} tests"
        )
        return sharded

    def shard_by_category(self, tests: List[TestExecution]) -> List[TestExecution]:
        """
        Shard tests by category.
        """
        if self.total_shards == 1:
            return tests

        # Group by category
        categories: Dict[str, List[TestExecution]] = defaultdict(list)
        for test in tests:
            categories[test.category].append(test)

        # Assign categories to shards round-robin
        sorted_categories = sorted(categories.items())
        sharded = []

        for idx, (category, cat_tests) in enumerate(sorted_categories):
            if idx % self.total_shards == self.shard_index:
                for test in cat_tests:
                    test.shard_id = self.shard_index
                    sharded.append(test)

        logger.info(
            f"Shard {self.shard_index + 1}/{self.total_shards}: "
            f"{len(sharded)}/{len(tests)} tests"
        )
        return sharded

    def shard_by_tool(self, tests: List[TestExecution]) -> List[TestExecution]:
        """
        Shard tests by tool.
        """
        if self.total_shards == 1:
            return tests

        # Group by tool
        tools: Dict[str, List[TestExecution]] = defaultdict(list)
        for test in tests:
            tools[test.tool].append(test)

        # Assign tools to shards round-robin
        sorted_tools = sorted(tools.items())
        sharded = []

        for idx, (tool, tool_tests) in enumerate(sorted_tools):
            if idx % self.total_shards == self.shard_index:
                for test in tool_tests:
                    test.shard_id = self.shard_index
                    sharded.append(test)

        logger.info(
            f"Shard {self.shard_index + 1}/{self.total_shards}: "
            f"{len(sharded)}/{len(tests)} tests"
        )
        return sharded

    def shard_balanced(self, tests: List[TestExecution]) -> List[TestExecution]:
        """Shard tests with load balancing.

        Distributes tests evenly by estimated duration.
        """
        if self.total_shards == 1:
            return tests

        # Sort by estimated duration (descending)
        sorted_tests = sorted(tests, key=lambda t: t.estimated_duration, reverse=True)

        # Distribute using greedy algorithm
        shard_times = [0.0] * self.total_shards
        shard_tests: List[List[TestExecution]] = [[] for _ in range(self.total_shards)]

        for test in sorted_tests:
            # Assign to shard with least total time
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


class IntelligentExecutionOrchestrator:
    """
    Main orchestrator combining all optimization strategies.
    """

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
        """
        Prepare tests for execution with all optimizations.
        """
        logger.info(f"Preparing {len(tests)} tests for execution...")

        # Phase 1: Warmup (if enabled)
        if self.warmup_enabled and warmup_config:
            await self.pre_warmer.warmup_all(**warmup_config)

        # Phase 2: Build dependency graph
        for test in tests:
            if test.dependencies:
                self.dependency_analyzer.add_dependencies(test.test_id, test.dependencies)

        # Check for dependency cycles
        cycles = self.dependency_analyzer.detect_cycles()
        if cycles:
            logger.warning(f"Found {len(cycles)} dependency cycles")
            for cycle in cycles:
                logger.warning(f"  Cycle: {' -> '.join(cycle)}")

        # Phase 3: Apply sharding
        sharded_tests = self.sharding.shard_balanced(tests)

        # Phase 4: Predict runtime
        total_runtime = self.execution_engine.predict_total_runtime(sharded_tests)
        logger.info(f"Predicted runtime: {total_runtime:.1f}s")

        return sharded_tests

    def schedule_execution(self, tests: List[TestExecution]) -> List[List[TestExecution]]:
        """Create optimized execution schedule.

        Returns batches respecting dependencies and optimizing parallelism.
        """
        # Get dependency levels
        test_ids = [t.test_id for t in tests]
        levels = self.dependency_analyzer.topological_sort(test_ids)

        # Schedule each level with predictive engine
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
        # Record in execution engine
        self.execution_engine.record_execution(test_id, duration, failed)

        # Check fail-fast
        if failed:
            return self.fail_fast_optimizer.record_failure(test_id, category, tool)

        return True

    def finalize(self) -> None:
        """
        Finalize execution and save state.
        """
        self.execution_engine.save_history()
        logger.info("Execution orchestrator finalized")


# Example usage and configuration
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Example test executions
    test_executions = [
        TestExecution(
            test_id="test_supabase_list_projects",
            test_func=lambda: None,
            category="integration",
            tool="supabase",
        ),
        TestExecution(
            test_id="test_render_deploy",
            test_func=lambda: None,
            category="integration",
            tool="render",
            dependencies=["test_render_auth"],
        ),
        TestExecution(
            test_id="test_render_auth",
            test_func=lambda: None,
            category="integration",
            tool="render",
        ),
    ]

    # Create orchestrator
    orchestrator = IntelligentExecutionOrchestrator(
        warmup_enabled=True,
        fail_fast=True,
        failure_threshold=3,
        shard_index=0,
        total_shards=1,
        max_workers=4,
    )

    # Prepare execution
    async def main():
        prepared_tests = await orchestrator.prepare_execution(
            test_executions,
            warmup_config={
                "connections": [{"connection_id": "supabase"}],
                "modules": ["tests.test_supabase", "tests.test_render"],
            },
        )

        # Schedule execution
        batches = orchestrator.schedule_execution(prepared_tests)
        print(f"Created {len(batches)} execution batches")

        # Finalize
        orchestrator.finalize()

    asyncio.run(main())
