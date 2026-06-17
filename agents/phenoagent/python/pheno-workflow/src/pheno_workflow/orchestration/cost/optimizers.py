"""Cost optimization strategies and routing algorithms.

Provides intelligent routing decisions and optimization strategies for cost-effective
model selection and resource management.
"""

import logging
from typing import Any

from ..core.types import TaskComplexity, TaskType
from .cost_models import CostModel
from .models import CostStrategy, UsageMetrics

logger = logging.getLogger(__name__)


class RoutingOptimizer:
    """
    Optimizes model routing decisions based on cost, performance, and budget
    constraints.
    """

    def __init__(self, cost_model: CostModel):
        """Initialize routing optimizer with cost model.

        Args:
            cost_model: Cost model instance for pricing information
        """
        self.cost_model = cost_model
        self.routing_strategies = {
            "cost_first": self._cost_first_routing,
            "performance_first": self._performance_first_routing,
            "balanced": self._balanced_routing,
            "budget_aware": self._budget_aware_routing,
        }
        self.current_strategy = "balanced"

        # Performance weights for different tasks
        self.performance_weights = {
            TaskType.CODE_GENERATION: {"accuracy": 0.3, "speed": 0.2, "cost": 0.5},
            TaskType.CODE_REVIEW: {"accuracy": 0.4, "speed": 0.3, "cost": 0.3},
            TaskType.DEBUG: {"accuracy": 0.3, "speed": 0.4, "cost": 0.3},
            TaskType.REFACTOR: {"accuracy": 0.4, "speed": 0.2, "cost": 0.4},
        }

        logger.info(f"RoutingOptimizer initialized with {len(self.routing_strategies)} strategies")

    def determine_optimal_routing(
        self,
        task_type: TaskType,
        complexity: TaskComplexity,
        usage: UsageMetrics,
        remaining_budget: float,
        context: dict[str, Any] | None = None,
    ) -> CostStrategy:
        """Determine optimal routing strategy for a task.

        Args:
            task_type: Type of development task
            complexity: Task complexity level
            usage: Current usage metrics
            remaining_budget: Remaining API budget
            context: Additional task context

        Returns:
            Optimal cost strategy
        """
        # Get suitable models for this task
        suitable_models = self.cost_model.get_optimal_models_for_task(
            task_type, complexity, max_cost=remaining_budget,
        )

        if not suitable_models:
            # Fallback to any affordable model
            suitable_models = self._get_fallback_models(remaining_budget)

        # Apply routing strategy
        strategy_func = self.routing_strategies[self.current_strategy]
        selected_model = strategy_func(suitable_models, task_type, complexity, usage, context)

        # Determine cost parameters
        max_iterations = self._calculate_max_iterations(complexity, selected_model)
        max_budget = min(
            remaining_budget,
            self.cost_model.estimate_task_cost(
                selected_model["model"], task_type, complexity, iterations=max_iterations,
            ),
        )

        return CostStrategy(
            model=selected_model["model"],
            max_budget=max_budget,
            max_iterations=max_iterations,
            use_cache=True,
            estimated_cost=selected_model["estimated_cost"],
            routing_decision=self._get_routing_reason(selected_model, usage),
        )

    def _cost_first_routing(
        self,
        models: list[dict[str, Any]],
        task_type: TaskType,
        complexity: TaskComplexity,
        usage: UsageMetrics,
        context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """
        Select cheapest model that meets minimum requirements.
        """
        # Filter subscription models first (free)
        subscription_models = [m for m in models if m["is_subscription_included"]]

        if subscription_models:
            # Choose best subscription model
            return max(subscription_models, key=lambda x: x["rank_score"])

        # Otherwise, choose cheapest
        return min(models, key=lambda x: x["estimated_cost"])

    def _performance_first_routing(
        self,
        models: list[dict[str, Any]],
        task_type: TaskType,
        complexity: TaskComplexity,
        usage: UsageMetrics,
        context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """
        Select highest performance model within budget.
        """
        # Prioritize models with better performance characteristics
        performance_ranked = sorted(
            models, key=lambda x: self._calculate_performance_score(x, task_type), reverse=True,
        )

        # Return highest performing within reasonable cost
        for model in performance_ranked:
            if (
                model["estimated_cost"]
                <= self.cost_model.cost_thresholds[f"{complexity.value}_task_max"]
            ):
                return model

        # Fallback to top performer
        return performance_ranked[0]

    def _balanced_routing(
        self,
        models: list[dict[str, Any]],
        task_type: TaskType,
        complexity: TaskComplexity,
        usage: UsageMetrics,
        context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """
        Balance cost and performance based on task requirements.
        """
        weights = self.performance_weights.get(
            task_type, {"accuracy": 0.3, "speed": 0.3, "cost": 0.4},
        )

        best_model = None
        best_score = -1

        for model in models:
            score = (
                model["rank_score"] * weights["cost"]  # Cost efficiency
                + self._calculate_performance_score(model, task_type)
                * weights["accuracy"]  # Quality
                + self._calculate_speed_score(model) * weights["speed"]  # Speed
            )

            if score > best_score:
                best_score = score
                best_model = model

        return best_model

    def _budget_aware_routing(
        self,
        models: list[dict[str, Any]],
        task_type: TaskType,
        complexity: TaskComplexity,
        usage: UsageMetrics,
        context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """
        Select model based on current budget situation.
        """
        budget_utilization = usage.total_cost / self.cost_model.api_budget

        if budget_utilization > 0.8:
            # Near budget limit - prioritize subscription models
            subscription_models = [m for m in models if m["is_subscription_included"]]
            if subscription_models:
                return max(subscription_models, key=lambda x: x["rank_score"])

        elif budget_utilization > 0.5:
            # Half budget used - be conservative with costs
            max_cost = self.cost_model.cost_thresholds[f"{complexity.value}_task_min"]
            affordable_models = [m for m in models if m["estimated_cost"] <= max_cost]
            if affordable_models:
                return max(affordable_models, key=lambda x: x["rank_score"])

        # Plenty of budget - use balanced approach
        return self._balanced_routing(models, task_type, complexity, usage, context)

    def _calculate_performance_score(self, model: dict[str, Any], task_type: TaskType) -> float:
        """
        Calculate performance score for a model based on its characteristics.
        """
        # Base performance by provider
        provider_scores = {
            "openai": 0.9,
            "anthropic": 0.95,
            "deepseek": 0.8,
            "refact": 0.85,
        }

        provider_score = provider_scores.get(model["provider"], 0.7)
        context_score = min(
            1.0, model["max_context_length"] / 100000 if model["max_context_length"] else 0.5,
        )

        # Task-specific adjustments
        if task_type == TaskType.CODE_GENERATION and "coder" in model["model"].lower():
            provider_score += 0.1

        return (provider_score + context_score) / 2

    def _calculate_speed_score(self, model: dict[str, Any]) -> float:
        """
        Calculate speed score based on model characteristics.
        """
        # Smaller models are generally faster
        if "mini" in model["model"].lower():
            return 1.0
        if "haiku" in model["model"].lower():
            return 0.9
        if "small" in model["model"].lower():
            return 0.8
        if "medium" in model["model"].lower():
            return 0.7
        if "large" in model["model"].lower():
            return 0.6
        return 0.5

    def _calculate_max_iterations(self, complexity: TaskComplexity, model: dict[str, Any]) -> int:
        """
        Calculate maximum iterations based on complexity and model.
        """
        base_iterations = {
            TaskComplexity.SIMPLE: 15,
            TaskComplexity.MEDIUM: 20,
            TaskComplexity.COMPLEX: 30,
        }

        max_iterations = base_iterations.get(complexity, 20)

        # Adjust for model capabilities
        if "mini" in model["model"].lower() or "haiku" in model["model"].lower():
            max_iterations = int(max_iterations * 1.2)  # Faster models can do more iterations

        return max_iterations

    def _get_routing_reason(self, model: dict[str, Any], usage: UsageMetrics) -> str:
        """
        Generate human-readable routing decision reason.
        """
        if model["is_subscription_included"]:
            return "refact_subscription"
        if model["estimated_cost"] < 1.0:
            return "optimized_api"
        if model["estimated_cost"] > 5.0:
            return "premium_api"
        return "standard_api"

    def _get_fallback_models(self, remaining_budget: float) -> list[dict[str, Any]]:
        """
        Get fallback models when none are suitable for the task.
        """
        fallback_models = []

        # Always include subscription models
        for model_name, pricing in self.cost_model.model_pricing.items():
            if pricing.is_subscription_included:
                fallback_models.append(
                    {
                        "model": model_name,
                        "provider": pricing.provider,
                        "estimated_cost": 0.0,
                        "is_subscription_included": True,
                        "rank_score": 0.8,
                    },
                )

        # Add cheapest paid model if budget allows
        if remaining_budget > 0.5:
            cheapest_paid = min(
                [
                    (name, price)
                    for name, price in self.cost_model.model_pricing.items()
                    if not price.is_subscription_included
                ],
                key=lambda x: x[1].cost_per_1k_tokens,
            )

            fallback_models.append(
                {
                    "model": cheapest_paid[0],
                    "provider": cheapest_paid[1].provider,
                    "estimated_cost": remaining_budget * 0.8,
                    "is_subscription_included": False,
                    "rank_score": 0.6,
                },
            )

        return fallback_models

    def set_routing_strategy(self, strategy: str) -> None:
        """
        Set the routing strategy to use.
        """
        if strategy not in self.routing_strategies:
            raise ValueError(f"Unknown routing strategy: {strategy}")

        self.current_strategy = strategy
        logger.info(f"Routing strategy changed to: {strategy}")

    def get_routing_statistics(self) -> dict[str, Any]:
        """
        Get statistics about routing decisions.
        """
        return {
            "current_strategy": self.current_strategy,
            "available_strategies": list(self.routing_strategies.keys()),
            "performance_weights": self.performance_weights,
        }


class BudgetOptimizer:
    """
    Optimizes budget allocation and spending patterns.
    """

    def __init__(self, cost_model: CostModel):
        """Initialize budget optimizer with cost model.

        Args:
            cost_model: Cost model for budget calculations
        """
        self.cost_model = cost_model
        self.savings_strategies = {
            "cache_optimization": self._optimize_caching,
            "batch_processing": self._optimize_batch_processing,
            "task_prioritization": self._optimize_task_prioritization,
        }

        logger.info("BudgetOptimizer initialized")

    def optimize_usage(
        self, usage: UsageMetrics, recommendations_limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Generate optimization recommendations based on usage patterns.

        Args:
            usage: Current usage metrics
            recommendations_limit: Maximum number of recommendations

        Returns:
            List of optimization recommendations
        """
        recommendations = []

        # Analyze cache hit rate
        cache_hit_rate = usage.cache_hits / max(usage.requests_count, 1)
        if cache_hit_rate < 0.3:
            recommendations.append(
                {
                    "type": "cache_optimization",
                    "priority": "high",
                    "message": f"Low cache hit rate ({cache_hit_rate:.1%}). Enable more aggressive caching.",
                    "potential_savings": usage.total_cost * 0.2,
                    "implementation": "Enable caching for similar tasks and increase cache TTL.",
                },
            )

        # Analyze subscription utilization
        refact_rate = usage.refact_requests / max(usage.requests_count, 1)
        if refact_rate < 0.4 and usage.total_cost > self.cost_model.api_budget * 0.5:
            recommendations.append(
                {
                    "type": "subscription_optimization",
                    "priority": "medium",
                    "message": f"Low Refact usage ({refact_rate:.1%}). Route more simple tasks to Refact.",
                    "potential_savings": usage.total_cost * 0.3,
                    "implementation": "Configure routing to prefer subscription models for simple tasks.",
                },
            )

        # Budget usage warnings
        budget_utilization = usage.total_cost / self.cost_model.api_budget
        if budget_utilization > 0.8:
            recommendations.append(
                {
                    "type": "budget_warning",
                    "priority": "high",
                    "message": f"High budget utilization ({budget_utilization:.1%}). Consider cost reduction measures.",
                    "potential_savings": 0.0,
                    "implementation": "Reduce costly model usage or increase budget.",
                },
            )

        # Analyze task complexity distribution (if available)
        if hasattr(usage, "complexity_distribution"):
            complexity_savings = self._analyze_complexity_usage(usage)
            if complexity_savings:
                recommendations.extend(complexity_savings)

        # Sort by potential savings and limit
        recommendations.sort(key=lambda x: x["potential_savings"], reverse=True)
        return recommendations[:recommendations_limit]

    def _analyze_complexity_usage(self, usage: UsageMetrics) -> list[dict[str, Any]]:
        """
        Analyze usage by task complexity and recommend optimizations.
        """
        return []

        # This would need complexity distribution data in UsageMetrics
        # Placeholder implementation


    def _optimize_caching(self, usage: UsageMetrics) -> dict[str, Any]:
        """
        Generate cache optimization recommendations.
        """
        cache_hit_rate = usage.cache_hits / max(usage.requests_count, 1)

        if cache_hit_rate < 0.5:
            potential_savings = (0.5 - cache_hit_rate) * usage.total_cost

            return {
                "strategy": "enhanced_caching",
                "current_hit_rate": cache_hit_rate,
                "target_hit_rate": 0.5,
                "potential_savings": potential_savings,
                "actions": [
                    "Increase cache TTL for repeated tasks",
                    "Implement similarity-based caching",
                    "Add cache prewarming for common patterns",
                ],
            }

        return {"strategy": "enhanced_caching", "potential_savings": 0.0}

    def _optimize_batch_processing(self, usage: UsageMetrics) -> dict[str, Any]:
        """
        Generate batch processing recommendations.
        """
        # Estimate potential savings from batching similar tasks
        estimated_batchable_requests = usage.requests_count * 0.2  # Assume 20% could be batched
        batch_efficiency = 0.3  # 30% efficiency gain from batching

        potential_savings = (
            usage.total_cost
            * estimated_batchable_requests
            / usage.requests_count
            * batch_efficiency
        )

        return {
            "strategy": "batch_processing",
            "batchable_requests_estimate": estimated_batchable_requests,
            "efficiency_gain": batch_efficiency,
            "potential_savings": potential_savings,
            "actions": [
                "Group similar code reviews together",
                "Batch refactoring tasks",
                "Implement task queuing for similar operations",
            ],
        }

    def _optimize_task_prioritization(self, usage: UsageMetrics) -> dict[str, Any]:
        """
        Generate task prioritization recommendations.
        """
        # High-value tasks should use better models
        high_value_requests = usage.requests_count * 0.3  # Top 30% of tasks
        potential_quality_gain = 0.15  # 15% quality improvement

        potential_savings = (
            usage.total_cost * high_value_requests / usage.requests_count * potential_quality_gain
        )

        return {
            "strategy": "task_prioritization",
            "high_value_tasks_estimate": high_value_requests,
            "quality_improvement": potential_quality_gain,
            "potential_savings": potential_savings,
            "actions": [
                "Identify high-impact tasks for premium models",
                "Use standard models for routine tasks",
                "Implement priority-based routing",
            ],
        }

    def calculate_optimization_impact(
        self, current_usage: UsageMetrics, optimizations: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Calculate the potential impact of implementing optimizations.

        Args:
            current_usage: Current usage metrics
            optimizations: List of optimization recommendations

        Returns:
            Impact analysis
        """
        total_savings = sum(opt["potential_savings"] for opt in optimizations)

        # Calculate new usage with optimizations
        optimized_cost = max(0, current_usage.total_cost - total_savings)
        cost_reduction = (
            (total_savings / current_usage.total_cost) * 100 if current_usage.total_cost > 0 else 0
        )

        # Budget impact
        optimized_utilization = (optimized_cost / self.cost_model.api_budget) * 100
        current_utilization = (current_usage.total_cost / self.cost_model.api_budget) * 100
        utilization_reduction = current_utilization - optimized_utilization

        return {
            "current_cost": current_usage.total_cost,
            "optimized_cost": optimized_cost,
            "total_savings": total_savings,
            "cost_reduction_percentage": cost_reduction,
            "current_budget_utilization": current_utilization,
            "optimized_budget_utilization": optimized_utilization,
            "utilization_reduction": utilization_reduction,
            "optimizations_applied": len(optimizations),
            "optimizations_detail": optimizations,
        }
