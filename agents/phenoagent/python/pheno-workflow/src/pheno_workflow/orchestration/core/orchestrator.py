"""Hybrid Orchestrator.

Main orchestration layer that coordinates multiple agents with intelligent routing, cost
optimization, and pattern-based execution strategies.

Based on proven patterns from OpenHands, Refact.AI, and Moatless integration.
"""

import asyncio
import logging
from typing import Any

from ..agents.manager import AgentManager
from ..core.types import (
    ExecutionStrategy,
    TaskComplexity,
    TaskRequest,
    TaskResult,
    TaskType,
)
from ..cost.optimizer import CostOptimizer
from ..patterns.engine import PatternEngine

logger = logging.getLogger(__name__)


class HybridOrchestrator:
    """
    Main orchestrator that coordinates multiple agents and strategies to provide optimal
    automated task execution with cost optimization and pattern-based guidance.
    """

    def __init__(self, config: dict[str, Any]):
        """Initialize the hybrid orchestrator.

        Args:
            config: Configuration dictionary containing settings for all components

        Config structure:
            {
                "agents": {...},  # Agent configurations
                "cost_optimization": {...},  # Cost optimizer config
                "patterns": {...},  # Pattern engine config
                "redis_url": "redis://localhost:6379",
                "monthly_budget": 60.0
            }
        """
        self.config = config

        # Initialize core components
        self.agent_manager = AgentManager(config.get("agents", {}))
        self.cost_optimizer = CostOptimizer(config.get("cost_optimization", {}))
        self.pattern_engine = PatternEngine(config.get("patterns", {}))

        # Task tracking
        self.task_history: list[TaskResult] = []
        self.active_tasks: dict[str, TaskRequest] = {}

        # Performance metrics
        self.success_rate = 0.0
        self.average_cost = 0.0
        self.average_execution_time = 0.0

        logger.info(
            "Hybrid Orchestrator initialized with AgentManager, CostOptimizer, and PatternEngine",
        )

    async def process_task(self, task: TaskRequest) -> TaskResult:
        """Process a development task using the hybrid orchestration approach.

        Args:
            task: The task request to process

        Returns:
            TaskResult containing the outcome and metrics
        """
        start_time = asyncio.get_event_loop().time()

        try:
            logger.info(f"Processing task {task.task_id}: {task.task_type.value}")

            # Track active task
            self.active_tasks[task.task_id] = task

            # Step 1: Analyze task complexity if not provided
            if not task.estimated_complexity:
                task.estimated_complexity = await self._analyze_complexity(task)

            # Step 2: Get cost optimization strategy
            tenant_id = task.tenant_id or "default"
            cost_strategy = await self.cost_optimizer.get_strategy(
                task.task_type, task.estimated_complexity, tenant_id, task.context,
            )

            # Step 3: Check cache for similar tasks
            cached_result = None
            if cost_strategy.get("use_cache", True):
                cached_result = await self.cost_optimizer.check_cache(
                    task.description, task.context,
                )

            if cached_result:
                logger.info(f"Task {task.task_id} satisfied from cache")
                await self.cost_optimizer.update_usage(tenant_id, 0.0, "cache", cache_hit=True)

                execution_time = asyncio.get_event_loop().time() - start_time
                task_result = TaskResult(
                    task_id=task.task_id,
                    success=True,
                    result=cached_result,
                    execution_time_seconds=execution_time,
                    cost_usd=0.0,
                    cached=True,
                    provider_used="cache",
                )

                self.task_history.append(task_result)
                self._update_metrics()
                del self.active_tasks[task.task_id]

                return task_result

            # Step 4: Get relevant patterns from pattern engine
            patterns = await self.pattern_engine.get_patterns(
                task.task_type, task.description, task.estimated_complexity, task.context,
            )

            # Step 5: Route task to appropriate agent
            agent_id = await self.agent_manager.route_task(task)
            await self.agent_manager.assign_task(agent_id, task)

            # Step 6: Execute task with selected strategy
            if task.strategy == ExecutionStrategy.PARALLEL:
                result = await self._execute_parallel(task, cost_strategy, patterns)
            elif task.strategy == ExecutionStrategy.SWARM:
                result = await self._execute_swarm(task, cost_strategy, patterns)
            else:
                result = await self._execute_sequential(task, cost_strategy, patterns)

            # Step 7: Calculate metrics
            execution_time = asyncio.get_event_loop().time() - start_time
            actual_cost = result.get("cost", cost_strategy.get("estimated_cost", 0.0))

            task_result = TaskResult(
                task_id=task.task_id,
                success=result.get("success", False),
                result=result,
                execution_time_seconds=execution_time,
                cost_usd=actual_cost,
                tokens_used=result.get("tokens", 0),
                provider_used=result.get(
                    "provider", cost_strategy.get("routing_decision", "unknown"),
                ),
                cached=False,
            )

            # Step 8: Update usage metrics and cache result
            await self.cost_optimizer.update_usage(
                tenant_id,
                actual_cost,
                cost_strategy.get("routing_decision", "unknown"),
                cache_hit=False,
            )

            if task_result.success and cost_strategy.get("use_cache", True):
                await self.cost_optimizer.store_cache(task.description, task.context, result)

            # Step 9: Update pattern outcome
            if patterns and patterns.get("selected_pattern"):
                await self.pattern_engine.update_pattern_outcome(
                    patterns["selected_pattern"], task_result.success, execution_time,
                )

            # Step 10: Mark task as completed for agent
            await self.agent_manager.complete_task(agent_id, task.task_id, task_result)

            # Update history
            self.task_history.append(task_result)
            self._update_metrics()

            # Clean up
            del self.active_tasks[task.task_id]

            logger.info(
                f"Task {task.task_id} completed: "
                f"success={task_result.success}, "
                f"time={execution_time:.2f}s, "
                f"cost=${task_result.cost_usd:.4f}, "
                f"provider={task_result.provider_used}",
            )

            return task_result

        except Exception as e:
            logger.error(f"Task {task.task_id} failed: {e!s}", exc_info=True)

            error_result = TaskResult(
                task_id=task.task_id,
                success=False,
                error_message=str(e),
                execution_time_seconds=asyncio.get_event_loop().time() - start_time,
            )

            self.task_history.append(error_result)
            if task.task_id in self.active_tasks:
                del self.active_tasks[task.task_id]

            return error_result

    async def _analyze_complexity(self, task: TaskRequest) -> TaskComplexity:
        """Analyze task complexity based on description and context.

        Args:
            task: The task to analyze

        Returns:
            Estimated TaskComplexity
        """
        # Simple heuristics - can be enhanced with ML
        description_length = len(task.description.split())

        if description_length < 50:
            return TaskComplexity.SIMPLE
        if description_length < 200:
            return TaskComplexity.MEDIUM
        return TaskComplexity.COMPLEX

    async def _select_strategy(self, task: TaskRequest) -> ExecutionStrategy:
        """Select optimal execution strategy for the task.

        Args:
            task: The task to analyze

        Returns:
            Recommended ExecutionStrategy
        """
        # Use provided strategy if set
        if task.strategy != ExecutionStrategy.SEQUENTIAL:
            return task.strategy

        # Auto-select based on task type and complexity
        if task.task_type in [TaskType.FEATURE, TaskType.REFACTOR]:
            if task.estimated_complexity == TaskComplexity.COMPLEX:
                return ExecutionStrategy.HIERARCHICAL

        return ExecutionStrategy.SEQUENTIAL

    async def _execute_sequential(
        self, task: TaskRequest, cost_strategy: dict[str, Any], patterns: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute task sequentially with cost optimization and pattern guidance.

        Args:
            task: The task to execute
            cost_strategy: Cost optimization strategy
            patterns: Pattern guidance

        Returns:
            Execution result
        """
        logger.info(
            f"Executing task {task.task_id} sequentially with {cost_strategy.get('routing_decision')}",
        )

        # Placeholder implementation - to be replaced with actual execution logic
        return {
            "success": True,
            "provider": cost_strategy.get("routing_decision", "sequential_executor"),
            "model": cost_strategy.get("model", "unknown"),
            "cost": cost_strategy.get("estimated_cost", 0.0),
            "tokens": 0,
            "pattern_used": patterns.get("selected_pattern") if patterns else None,
            "steps_followed": patterns.get("steps", []) if patterns else [],
        }

    async def _execute_parallel(
        self, task: TaskRequest, cost_strategy: dict[str, Any], patterns: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute task with parallel agent coordination.

        Args:
            task: The task to execute
            cost_strategy: Cost optimization strategy
            patterns: Pattern guidance

        Returns:
            Execution result
        """
        logger.info(f"Executing task {task.task_id} in parallel")

        # Placeholder implementation - to be replaced with actual parallel execution
        return {
            "success": True,
            "provider": "parallel_executor",
            "model": cost_strategy.get("model", "unknown"),
            "cost": cost_strategy.get("estimated_cost", 0.0),
            "tokens": 0,
            "pattern_used": patterns.get("selected_pattern") if patterns else None,
        }

    async def _execute_swarm(
        self, task: TaskRequest, cost_strategy: dict[str, Any], patterns: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute task using swarm coordination.

        Args:
            task: The task to execute
            cost_strategy: Cost optimization strategy
            patterns: Pattern guidance

        Returns:
            Execution result
        """
        logger.info(f"Executing task {task.task_id} via swarm")

        # Placeholder implementation - to be replaced with actual swarm execution
        return {
            "success": True,
            "provider": "swarm_executor",
            "model": cost_strategy.get("model", "unknown"),
            "cost": cost_strategy.get("estimated_cost", 0.0),
            "tokens": 0,
            "pattern_used": patterns.get("selected_pattern") if patterns else None,
        }

    def _update_metrics(self) -> None:
        """
        Update orchestrator performance metrics.
        """
        if not self.task_history:
            return

        successful_tasks = [t for t in self.task_history if t.success]
        self.success_rate = len(successful_tasks) / len(self.task_history)

        if self.task_history:
            self.average_cost = sum(t.cost_usd for t in self.task_history) / len(self.task_history)
            self.average_execution_time = sum(
                t.execution_time_seconds for t in self.task_history
            ) / len(self.task_history)

    def get_metrics(self) -> dict[str, Any]:
        """Get current orchestrator metrics.

        Returns:
            Dictionary of metrics
        """
        return {
            "total_tasks": len(self.task_history),
            "active_tasks": len(self.active_tasks),
            "success_rate": self.success_rate,
            "average_cost_usd": self.average_cost,
            "average_execution_time_seconds": self.average_execution_time,
        }

    async def get_status(self) -> dict[str, Any]:
        """Get comprehensive status of all orchestrator components.

        Returns:
            Status dictionary with all component states
        """
        return {
            "orchestrator": {"status": "operational", "metrics": self.get_metrics()},
            "agent_manager": await self.agent_manager.get_status(),
            "cost_optimizer": await self.cost_optimizer.get_status(),
            "pattern_engine": await self.pattern_engine.get_status(),
        }

    async def get_cost_summary(self, tenant_id: str | None = None) -> dict[str, Any]:
        """Get cost summary from the cost optimizer.

        Args:
            tenant_id: Optional tenant ID to filter by

        Returns:
            Cost summary dictionary
        """
        return await self.cost_optimizer.get_cost_summary(tenant_id)

    async def get_pattern_analytics(self) -> dict[str, Any]:
        """Get pattern usage analytics.

        Returns:
            Pattern analytics dictionary
        """
        return await self.pattern_engine.get_pattern_analytics()

    async def discover_agents(self, task_type: TaskType | None = None) -> list[dict[str, Any]]:
        """Discover available agents.

        Args:
            task_type: Optional task type to filter by

        Returns:
            List of available agents
        """
        return await self.agent_manager.discover_agents(task_type)

    async def shutdown(self):
        """
        Gracefully shutdown all components.
        """
        logger.info("Shutting down Hybrid Orchestrator")

        await self.agent_manager.shutdown()
        await self.cost_optimizer.shutdown()
        await self.pattern_engine.shutdown()

        logger.info("Hybrid Orchestrator shutdown complete")
