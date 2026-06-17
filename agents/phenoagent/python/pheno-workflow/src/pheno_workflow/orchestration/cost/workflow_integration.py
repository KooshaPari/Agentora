"""Workflow integration for cost optimization.

Provides integration hooks and utilities for embedding cost optimization into workflow
orchestration and task execution pipelines.
"""

import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from ..core.types import TaskComplexity, TaskType
from .cost_models import CostModel
from .models import UsageMetrics
from .optimizers import BudgetOptimizer, RoutingOptimizer

logger = logging.getLogger(__name__)


class CostAwareWorkflow:
    """Integrates cost optimization into workflow execution.

    Provides hooks and utilities for embedding cost-aware decisions throughout the task
    execution pipeline.
    """

    def __init__(
        self,
        cost_model: CostModel,
        routing_optimizer: RoutingOptimizer,
        budget_optimizer: BudgetOptimizer,
    ):
        """Initialize cost-aware workflow.

        Args:
            cost_model: Cost model for calculations
            routing_optimizer: Routing optimizer for model selection
            budget_optimizer: Budget optimizer for recommendations
        """
        self.cost_model = cost_model
        self.routing_optimizer = routing_optimizer
        self.budget_optimizer = budget_optimizer

        # Execution tracking
        self.active_tasks: dict[str, dict[str, Any]] = {}
        self.execution_history: list[dict[str, Any]] = []

        # Workflow hooks
        self.pre_execution_hooks: list[Callable] = []
        self.post_execution_hooks: list[Callable] = []
        self.decision_hooks: list[Callable] = []

        # Cost thresholds for intervention
        self.intervention_thresholds = {
            "single_task_cost": 10.0,
            "hourly_spend_rate": 20.0,
            "budget_utilization": 0.9,
        }

        logger.info("CostAwareWorkflow initialized")

    async def start_task_execution(
        self,
        task_id: str,
        task_type: TaskType,
        complexity: TaskComplexity,
        tenant_id: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Start task execution with cost optimization.

        Args:
            task_id: Unique task identifier
            task_type: Type of task
            complexity: Task complexity
            tenant_id: Tenant identifier
            context: Additional task context

        Returns:
            Execution plan with cost information
        """
        # Get current usage metrics
        usage = await self._get_usage_metrics(tenant_id)
        remaining_budget = self.cost_model.api_budget - usage.total_cost

        # Determine optimal strategy
        strategy = await self.routing_optimizer.determine_optimal_routing(
            task_type, complexity, usage, remaining_budget, context,
        )

        # Create execution plan
        execution_plan = {
            "task_id": task_id,
            "task_type": task_type,
            "complexity": complexity,
            "tenant_id": tenant_id,
            "strategy": strategy,
            "estimated_cost": strategy.estimated_cost,
            "max_budget": strategy.max_budget,
            "max_iterations": strategy.max_iterations,
            "context": context,
            "start_time": datetime.now(UTC),
        }

        # Check if cost intervention is needed
        intervention = self._check_cost_intervention(strategy, usage)
        if intervention:
            execution_plan["intervention"] = intervention
            logger.warning(f"Cost intervention triggered for task {task_id}: {intervention}")

        # Execute pre-execution hooks
        await self._execute_hooks(self.pre_execution_hooks, "pre_execution", execution_plan)

        # Track active task
        self.active_tasks[task_id] = execution_plan

        logger.info(f"Started task {task_id} with strategy: {strategy.routing_decision}")

        return execution_plan

    async def complete_task_execution(
        self,
        task_id: str,
        actual_cost: float,
        actual_tokens_used: int,
        result_success: bool,
        additional_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Complete task execution and update cost tracking.

        Args:
            task_id: Task identifier
            actual_cost: Actual cost incurred
            actual_tokens_used: Actual tokens consumed
            result_success: Whether task was successful
            additional_context: Additional execution context

        Returns:
            Execution summary with cost analysis
        """
        if task_id not in self.active_tasks:
            logger.error(f"Task {task_id} not found in active tasks")
            return {"error": "Task not found"}

        execution_plan = self.active_tasks[task_id]
        end_time = datetime.now(UTC)
        duration = (end_time - execution_plan["start_time"]).total_seconds()

        # Create execution summary
        execution_summary = {
            "task_id": task_id,
            "tenant_id": execution_plan["tenant_id"],
            "task_type": execution_plan["task_type"],
            "complexity": execution_plan["complexity"],
            "estimated_cost": execution_plan["estimated_cost"],
            "actual_cost": actual_cost,
            "cost_variance": actual_cost - execution_plan["estimated_cost"],
            "actual_tokens_used": actual_tokens_used,
            "result_success": result_success,
            "duration_seconds": duration,
            "strategy_used": execution_plan["strategy"].routing_decision,
            "model_used": execution_plan["strategy"].model,
            "start_time": execution_plan["start_time"],
            "end_time": end_time,
            "context": additional_context,
        }

        # Calculate cost efficiency
        if execution_summary["estimated_cost"] > 0:
            execution_summary["cost_efficiency"] = execution_summary["estimated_cost"] / actual_cost
        else:
            execution_summary["cost_efficiency"] = 1.0

        # Update usage metrics
        await self._update_usage_metrics(
            execution_plan["tenant_id"],
            actual_cost,
            execution_plan["strategy"].routing_decision,
            execution_summary,
        )

        # Execute post-execution hooks
        await self._execute_hooks(self.post_execution_hooks, "post_execution", execution_summary)

        # Move to history
        self.execution_history.append(execution_summary)
        del self.active_tasks[task_id]

        # Limit history size
        if len(self.execution_history) > 10000:
            self.execution_history = self.execution_history[-5000:]

        logger.info(f"Completed task {task_id} with cost ${actual_cost:.4f}")

        return execution_summary

    def add_pre_execution_hook(self, hook: Callable) -> None:
        """
        Add a hook to be called before task execution.
        """
        self.pre_execution_hooks.append(hook)
        logger.info("Added pre-execution hook")

    def add_post_execution_hook(self, hook: Callable) -> None:
        """
        Add a hook to be called after task execution.
        """
        self.post_execution_hooks.append(hook)
        logger.info("Added post-execution hook")

    def add_decision_hook(self, hook: Callable) -> None:
        """
        Add a hook to be called during routing decisions.
        """
        self.decision_hooks.append(hook)
        logger.info("Added decision hook")

    async def get_workflow_analytics(
        self, tenant_id: str | None = None, time_window_hours: int = 24,
    ) -> dict[str, Any]:
        """Get workflow analytics and insights.

        Args:
            tenant_id: Optional tenant filter
            time_window_hours: Time window for analysis

        Returns:
            Workflow analytics
        """
        # Filter history by time window and tenant
        cutoff_time = datetime.now(UTC) - timedelta(hours=time_window_hours)
        recent_history = [
            exec_summary
            for exec_summary in self.execution_history
            if exec_summary["end_time"] > cutoff_time
            and (not tenant_id or exec_summary["tenant_id"] == tenant_id)
        ]

        if not recent_history:
            return {"message": "No execution history in specified window"}

        # Calculate analytics
        total_tasks = len(recent_history)
        total_cost = sum(exec_summary["actual_cost"] for exec_summary in recent_history)
        successful_tasks = sum(
            1 for exec_summary in recent_history if exec_summary["result_success"]
        )

        # Cost analysis
        avg_cost_per_task = total_cost / total_tasks if total_tasks > 0 else 0
        cost_variance_analysis = self._analyze_cost_variance(recent_history)

        # Strategy distribution
        strategy_distribution = {}
        for exec_summary in recent_history:
            strategy = exec_summary["strategy_used"]
            strategy_distribution[strategy] = strategy_distribution.get(strategy, 0) + 1

        # Performance metrics
        avg_duration = (
            sum(exec_summary["duration_seconds"] for exec_summary in recent_history) / total_tasks
        )
        avg_cost_efficiency = (
            sum(exec_summary["cost_efficiency"] for exec_summary in recent_history) / total_tasks
        )

        # Trend analysis
        cost_trend = self._analyze_cost_trend(recent_history)

        return {
            "time_window_hours": time_window_hours,
            "tenant_id": tenant_id,
            "summary": {
                "total_tasks": total_tasks,
                "successful_tasks": successful_tasks,
                "success_rate": (successful_tasks / total_tasks) * 100 if total_tasks > 0 else 0,
                "total_cost": total_cost,
                "avg_cost_per_task": avg_cost_per_task,
                "avg_duration_seconds": avg_duration,
                "avg_cost_efficiency": avg_cost_efficiency,
            },
            "cost_analysis": cost_variance_analysis,
            "strategy_distribution": strategy_distribution,
            "performance_trends": cost_trend,
            "active_tasks_count": len(self.active_tasks),
        }

    def _check_cost_intervention(
        self, strategy: "UsageMetrics", usage: UsageMetrics,
    ) -> dict[str, Any] | None:
        """
        Check if cost intervention is needed.
        """
        interventions = []

        # Check single task cost
        if strategy.estimated_cost > self.intervention_thresholds["single_task_cost"]:
            interventions.append(
                {
                    "type": "high_task_cost",
                    "message": f"Task cost ${strategy.estimated_cost:.2f} exceeds threshold",
                    "suggested_action": "Consider breaking down into smaller tasks",
                },
            )

        # Check budget utilization
        budget_utilization = usage.total_cost / self.cost_model.api_budget
        if budget_utilization > self.intervention_thresholds["budget_utilization"]:
            interventions.append(
                {
                    "type": "budget_exhaustion",
                    "message": f"Budget utilization {budget_utilization:.1%} is high",
                    "suggested_action": "Consider subscription models or cost reduction",
                },
            )

        return interventions[0] if interventions else None

    def _analyze_cost_variance(self, execution_history: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Analyze cost variance in execution history.
        """
        if not execution_history:
            return {}

        costs = [exec_summary["actual_cost"] for exec_summary in execution_history]
        cost_variances = [exec_summary["cost_variance"] for exec_summary in execution_history]

        return {
            "min_cost": min(costs),
            "max_cost": max(costs),
            "avg_cost": sum(costs) / len(costs),
            "cost_std_dev": self._calculate_std_dev(costs),
            "avg_estimation_error": sum(abs(v) for v in cost_variances) / len(cost_variances),
            "estimation_accuracy": sum(1 for v in cost_variances if abs(v) < 0.1)
            / len(cost_variances),
        }

    def _analyze_cost_trend(self, execution_history: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Analyze cost trends over time.
        """
        if len(execution_history) < 2:
            return {"trend": "insufficient_data"}

        # Sort by end time
        sorted_history = sorted(execution_history, key=lambda x: x["end_time"])

        # Calculate trend
        first_half = sorted_history[: len(sorted_history) // 2]
        second_half = sorted_history[len(sorted_history) // 2 :]

        first_half_avg = sum(exec_summary["actual_cost"] for exec_summary in first_half) / len(
            first_half,
        )
        second_half_avg = sum(exec_summary["actual_cost"] for exec_summary in second_half) / len(
            second_half,
        )

        trend_direction = "increasing" if second_half_avg > first_half_avg else "decreasing"
        trend_magnitude = (
            abs(second_half_avg - first_half_avg) / first_half_avg if first_half_avg > 0 else 0
        )

        return {
            "trend": trend_direction,
            "magnitude": trend_magnitude,
            "first_half_avg": first_half_avg,
            "second_half_avg": second_half_avg,
        }

    def _calculate_std_dev(self, values: list[float]) -> float:
        """
        Calculate standard deviation.
        """
        if len(values) < 2:
            return 0.0

        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return variance**0.5

    async def _get_usage_metrics(self, tenant_id: str) -> UsageMetrics:
        """
        Get usage metrics for a tenant.
        """
        # This would integrate with the main CostOptimizer's usage tracking
        # For now, return empty metrics
        return UsageMetrics(tenant_id=tenant_id)

    async def _update_usage_metrics(
        self, tenant_id: str, cost: float, routing_decision: str, execution_summary: dict[str, Any],
    ) -> None:
        """
        Update usage metrics with execution results.
        """
        # This would integrate with the main CostOptimizer

    async def _execute_hooks(
        self, hooks: list[Callable], hook_type: str, data: dict[str, Any],
    ) -> None:
        """
        Execute all hooks of a specific type.
        """
        for hook in hooks:
            try:
                await hook(hook_type, data)
            except Exception as e:
                logger.exception(f"Hook execution failed: {e}")


class TaskScheduler:
    """
    Schedules tasks with cost optimization and prioritization.
    """

    def __init__(self, cost_aware_workflow: CostAwareWorkflow):
        """Initialize task scheduler.

        Args:
            cost_aware_workflow: Cost-aware workflow instance
        """
        self.workflow = cost_aware_workflow
        self.task_queue: list[dict[str, Any]] = []
        self.scheduling_strategies = {
            "cost_first": self._cost_first_scheduling,
            "time_first": self._time_first_scheduling,
            "balanced": self._balanced_scheduling,
        }
        self.current_strategy = "balanced"

        # Scheduling constraints
        self.max_concurrent_tasks = 5
        self.max_hourly_spend = 50.0

        logger.info("TaskScheduler initialized")

    async def schedule_task(
        self,
        task_id: str,
        task_type: TaskType,
        complexity: TaskComplexity,
        tenant_id: str,
        priority: int = 5,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Schedule a task with cost optimization.

        Args:
            task_id: Task identifier
            task_type: Type of task
            complexity: Task complexity
            tenant_id: Tenant identifier
            priority: Task priority (1-10, lower is higher priority)
            context: Additional context

        Returns:
            Scheduling result
        """
        # Add to queue
        task_data = {
            "task_id": task_id,
            "task_type": task_type,
            "complexity": complexity,
            "tenant_id": tenant_id,
            "priority": priority,
            "context": context,
            "submission_time": datetime.now(UTC),
            "status": "queued",
        }

        self.task_queue.append(task_data)

        # Apply scheduling strategy
        scheduled_execution = await self._apply_scheduling_strategy(task_data)

        logger.info(f"Scheduled task {task_id} with priority {priority}")

        return scheduled_execution

    async def _apply_scheduling_strategy(self, task_data: dict[str, Any]) -> dict[str, Any]:
        """
        Apply current scheduling strategy to a task.
        """
        strategy_func = self.scheduling_strategies[self.current_strategy]

        # Estimate cost for this task
        usage = await self.workflow._get_usage_metrics(task_data["tenant_id"])
        remaining_budget = self.workflow.cost_model.api_budget - usage.total_cost

        strategy = await self.workflow.routing_optimizer.determine_optimal_routing(
            task_data["task_type"],
            task_data["complexity"],
            usage,
            remaining_budget,
            task_data["context"],
        )

        # Apply strategy-specific scheduling logic
        return await strategy_func(task_data, strategy)


    async def _cost_first_scheduling(
        self, task_data: dict[str, Any], strategy: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Schedule with cost as primary consideration.
        """
        # Delay execution if cost is too high and budget is limited
        usage = await self.workflow._get_usage_metrics(task_data["tenant_id"])
        remaining_budget = self.workflow.cost_model.api_budget - usage.total_cost

        if strategy["estimated_cost"] > remaining_budget * 0.3:
            # Schedule for later when more budget is available
            estimated_delay = timedelta(hours=2)
            scheduled_time = datetime.now(UTC) + estimated_delay

            return {
                "task_id": task_data["task_id"],
                "scheduled_time": scheduled_time,
                "reason": "Delayed due to cost constraints",
                "estimated_cost": strategy["estimated_cost"],
            }

        # Execute immediately
        return await self.workflow.start_task_execution(
            task_data["task_id"],
            task_data["task_type"],
            task_data["complexity"],
            task_data["tenant_id"],
            task_data["context"],
        )

    async def _balanced_scheduling(
        self, task_data: dict[str, Any], strategy: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Schedule with balanced consideration of cost, time, and priority.
        """
        # Check immediate execution possibility
        sum(
            exec_plan["estimated_cost"] for exec_plan in self.workflow.active_tasks.values()
        )

        if len(self.workflow.active_tasks) < self.max_concurrent_tasks:
            # Can execute immediately
            return await self.workflow.start_task_execution(
                task_data["task_id"],
                task_data["task_type"],
                task_data["complexity"],
                task_data["tenant_id"],
                task_data["context"],
            )

        # Schedule with delay due to concurrency
        estimated_delay = timedelta(minutes=5 * len(self.workflow.active_tasks))
        scheduled_time = datetime.now(UTC) + estimated_delay

        return {
            "task_id": task_data["task_id"],
            "scheduled_time": scheduled_time,
            "reason": "Delayed due to concurrency limits",
            "estimated_cost": strategy["estimated_cost"],
        }

    async def _time_first_scheduling(
        self, task_data: dict[str, Any], strategy: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Schedule with execution time as primary consideration.
        """
        # Just execute immediately, prioritizing speed over cost
        return await self.workflow.start_task_execution(
            task_data["task_id"],
            task_data["task_type"],
            task_data["complexity"],
            task_data["tenant_id"],
            task_data["context"],
        )

    def set_scheduling_strategy(self, strategy: str) -> None:
        """
        Set task scheduling strategy.
        """
        if strategy not in self.scheduling_strategies:
            raise ValueError(f"Unknown scheduling strategy: {strategy}")

        self.current_strategy = strategy
        logger.info(f"Scheduling strategy changed to: {strategy}")

    async def get_queue_status(self) -> dict[str, Any]:
        """
        Get status of task queue.
        """
        queue_by_priority = {}
        for task in self.task_queue:
            priority = task["priority"]
            if priority not in queue_by_priority:
                queue_by_priority[priority] = []
            queue_by_priority[priority].append(task)

        return {
            "queue_length": len(self.task_queue),
            "active_tasks": len(self.workflow.active_tasks),
            "tasks_by_priority": queue_by_priority,
            "scheduling_strategy": self.current_strategy,
        }
