"""Cost models and financial calculations.

Provides cost modeling, budget management, and financial analysis
for workflow optimization and resource allocation.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from ..core.types import TaskComplexity, TaskType
from .models import CostStrategy, UsageMetrics

logger = logging.getLogger(__name__)


@dataclass
class ModelPricing:
    """Pricing information for AI models."""
    name: str
    cost_per_1k_tokens: float
    is_subscription_included: bool = False
    max_context_length: Optional[int] = None
    provider: str = "openai"


class CostModel:
    """
    Manages cost calculations and budget models for different AI models.

    Provides pricing information, cost estimation, and budget analysis
    for making intelligent routing decisions.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize cost model with configuration.

        Args:
            config: Configuration containing pricing and budget information
        """
        self.config = config

        # Budget configuration
        self.monthly_budget = config.get('monthly_budget', 60.0)
        self.refact_subscription_cost = config.get('refact_subscription_cost', 10.0)
        self.api_budget = self.monthly_budget - self.refact_subscription_cost
        self.subscription_tier = config.get('subscription_tier', 'pro')

        # Initialize model pricing
        self.model_pricing = self._initialize_model_pricing(config)

        # Cost thresholds
        self.cost_thresholds = {
            'simple_task_max': 1.0,
            'medium_task_min': 2.0,
            'medium_task_max': 5.0,
            'complex_task_min': 5.0,
            'complex_task_max': 15.0,
        }

        logger.info(f"Cost Model initialized: API budget ${self.api_budget:.2f}, {len(self.model_pricing)} models configured")

    def _initialize_model_pricing(self, config: Dict[str, Any]) -> Dict[str, ModelPricing]:
        """Initialize model pricing from configuration."""
        # Default pricing configuration
        default_costs = {
            'refact-small': ModelPricing('refact-small', 0.0, True, provider='refact'),
            'refact-medium': ModelPricing('refact-medium', 0.0, True, provider='refact'),
            'refact-large': ModelPricing('refact-large', 0.0, True, provider='refact'),
            'gpt-4o': ModelPricing('gpt-4o', 0.03, False, 128000, 'openai'),
            'gpt-4o-mini': ModelPricing('gpt-4o-mini', 0.0015, False, 128000, 'openai'),
            'claude-3-5-sonnet': ModelPricing('claude-3-5-sonnet', 0.015, False, 200000, 'anthropic'),
            'claude-3-haiku': ModelPricing('claude-3-haiku', 0.0025, False, 200000, 'anthropic'),
            'deepseek-coder': ModelPricing('deepseek-coder', 0.0005, False, 32768, 'deepseek'),
        }

        # Override with config-provided costs if available
        if 'model_costs' in config:
            for model_name, cost_per_1k in config['model_costs'].items():
                if model_name in default_costs:
                    default_costs[model_name].cost_per_1k_tokens = cost_per_1k
                else:
                    # Add new model
                    default_costs[model_name] = ModelPricing(model_name, cost_per_1k)

        return default_costs

    def estimate_task_cost(
        self,
        model: str,
        task_type: TaskType,
        complexity: TaskComplexity,
        estimated_tokens: Optional[int] = None,
        iterations: int = 1
    ) -> float:
        """
        Estimate cost for a task with a specific model.

        Args:
            model: Model name
            task_type: Type of task
            complexity: Task complexity
            estimated_tokens: Estimated token count (optional)
            iterations: Number of iterations

        Returns:
            Estimated cost in USD
        """
        model_pricing = self.model_pricing.get(model)
        if not model_pricing:
            logger.warning(f"Unknown model: {model}")
            return 0.0

        # Free for subscription models
        if model_pricing.is_subscription_included:
            return 0.0

        # Estimate tokens if not provided
        if estimated_tokens is None:
            estimated_tokens = self._estimate_tokens(task_type, complexity)

        # Calculate cost
        cost_per_iteration = (estimated_tokens / 1000) * model_pricing.cost_per_1k_tokens
        total_cost = cost_per_iteration * iterations

        return total_cost

    def _estimate_tokens(self, task_type: TaskType, complexity: TaskComplexity) -> int:
        """Estimated token count based on task type and complexity."""
        # Token estimations by task type and complexity
       /token_estimates = {
            TaskType.CODE_REVIEW: {
                TaskComplexity.SIMPLE: 2000,
                TaskComplexity.MEDIUM: 5000,
                TaskComplexity.COMPLEX: 8000,
            },
            TaskType.CODE_GENERATION: {
                TaskComplexity.SIMPLE: 1500,
                TaskComplexity.MEDIUM: 4000,
                TaskComplexity.COMPLEX: 7000,
            },
            TaskType.DEBUG: {
                TaskComplexity.SIMPLE: 3000,
                TaskComplexity.MEDIUM: 6000,
                TaskComplexity.COMPLEX: 10000,
            },
            TaskType.REFACTOR: {
                TaskComplexity.SIMPLE: 2500,
                TaskComplexity.MEDIUM: 6000,
                TaskComplexity.COMPLEX: 12000,
            },
        }

        default_estimates = {
            TaskComplexity.SIMPLE: 2000,
            TaskComplexity.MEDIUM: 5000,
            TaskComplexity.COMPLEX: 8000,
        }

        task_estimates = token_estimates.get(task_type, default_estimates)
        return task_estimates.get(complexity, 2000)

    def calculate_budget_efficiency(
        self,
        usage_metrics: UsageMetrics,
        period_days: int = 30
    ) -> Dict[str, Any]:
        """
        Calculate budget efficiency metrics.

        Args:
            usage_metrics: Current usage metrics
            period_days: Analysis period in days

        Returns:
            Budget efficiency analysis
        """
        daily_budget = self.api_budget / period_days
        daily_actual_cost = usage_metrics.total_cost / period_days

        efficiency = {
            'total_budget': self.api_budget,
            'total_cost': usage_metrics.total_cost,
            'remaining_budget': self.api_budget - usage_metrics.total_cost,
            'budget_utilization': (usage_metrics.total_cost / self.api_budget) * 100,
            'daily_budget': daily_budget,
            'daily_actual_cost': daily_actual_cost,
            'daily_efficiency': (daily_actual_cost / daily_budget) * 100,
        }

        # Add subscription value analysis
        subtotal_cost = usage_metrics.total_cost - self.refact_subscription_cost
        if subtotal_cost > 0:
            efficiency['subscription_value'] = (
                usage_metrics.refact_requests / usage_metrics.requests_count
            ) * self.refact_subscription_cost
        else:
            efficiency['subscription_value'] = self.refact_subscription_cost

        return efficiency

    def get_optimal_models_for_task(
        self,
        task_type: TaskType,
        complexity: TaskComplexity,
        max_cost: Optional[float] = None,
        preferred_providers: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get optimal models ranked by cost-effectiveness for a task.

        Args:
            task_type: Type of task
            complexity: Task complexity
            max_cost: Maximum acceptable cost (optional)
            preferred_providers: Preferred model providers (optional)

        Returns:
            Ranked list of suitable models with cost estimates
        """
        suitable_models = []

        for model_name, pricing in self.model_pricing.items():
            # Skip if provider is not preferred (if specified)
            if preferred_providers and pricing.provider not in preferred_providers:
                continue

            # Estimate cost for this model
            estimated_cost = self.estimate_task_cost(model_name, task_type, complexity)

            # Skip if exceeds max cost
            if max_cost and estimated_cost > max_cost:
                continue

            suitable_models.append({
                'model': model_name,
                'provider': pricing.provider,
                'estimated_cost': estimated_cost,
                'is_subscription_included': pricing.is_subscription_included,
                'max_context_length': pricing.max_context_length,
                'cost_per_1k_tokens': pricing.cost_per_1k_tokens,
                'rank_score': self._calculate_model_score(model_name, task_type, complexity, estimated_cost),
            })

        # Sort by rank score (higher is better)
        suitable_models.sort(key=lambda x: x['rank_score'], reverse=True)

        return suitable_models

    def _calculate_model_score(
        self,
        model: str,
        task_type: TaskType,
        complexity: TaskComplexity,
        estimated_cost: float
    ) -> float:
        """
        Calculate score for model selection.

        Higher score indicates better fit.
        """
        pricing = self.model_pricing[model]

        # Base score from cost (lower cost = higher score, but free models penalize slightly if too expensive)
        if pricing.is_subscription_included:
            cost_score = 0.9  # Good score for subscription models
        else:
            # Normalize cost to 0-1 scale (lower is better)
            max_reasonable_cost = 10.0  # $10 is considered max reasonable cost
            cost_score = max(0, (max_reasonable_cost - estimated_cost) / max_reasonable_cost)

        # Complexity-specific adjustments
        complexity_bonus = {
            TaskComplexity.SIMPLE: 0.1,  # Prefer simpler models for simple tasks
            TaskComplexity.MEDIUM: 0.0,
            TaskComplexity.COMPLEX: -0.1,  # Prefer more capable models for complex tasks
        }

        # Provider preferences
        provider_scores = {
            'openai': 1.0,
            'anthropic': 0.95,
            'deepseek': 0.85,
            'refact': 1.1,  # Boost for subscription models
        }

        provider_score = provider_scores.get(pricing.provider, 0.8)

        total_score = (
            cost_score * 0.6 +  # Cost is most important
            provider_score * 0.3 +  # Provider preference
            complexity_bonus[complexity]  # Complexity adjustment
        )

        return max(0, min(1, total_score))

    def calculate_monthly_projection(
        self,
        current_usage: UsageMetrics,
        days_elapsed: int = 0
    ) -> Dict[str, Any]:
        """
        Calculate projected monthly costs based on current usage.

        Args:
            current_usage: Current usage metrics
            days_elapsed: Number of days elapsed in month (0 for current date)

        Returns:
            Monthly cost projection
        """
        if days_elapsed == 0:
            # Calculate from last reset
            if current_usage.last_reset:
                days_elapsed = (datetime.now(timezone.utc) - current_usage.last_reset).days
            else:
                days_elapsed = 1

        if days_elapsed == 0:
            days_elapsed = 1  # Avoid division by zero

        # Calculate daily averages
        daily_requests = current_usage.requests_count / days_elapsed
        daily_cost = current_usage.total_cost / days_elapsed
        daily_api_requests = current_usage.api_requests / days_elapsed
        daily_refact_requests = current_usage.refact_requests / days_elapsed

        # Project to full month (30 days)
        projected_requests = daily_requests * 30
        projected_cost = daily_cost * 30 + self.refact_subscription_cost
        projected_api_requests = daily_api_requests * 30
        projected_refact_requests = daily_refact_requests * 30

        # Calculate if within budget
        within_budget = projected_cost <= self.monthly_budget
        remaining_days = 30 - days_elapsed

        return {
            'days_elapsed': days_elapsed,
            'remaining_days': remaining_days,
            'current_usage': {
                'requests': current_usage.requests_count,
                'cost': current_usage.total_cost,
                'api_requests': current_usage.api_requests,
                'refact_requests': current_usage.refact_requests,
            },
            'daily_averages': {
                'requests': daily_requests,
                'cost': daily_cost,
                'api_requests': daily_api_requests,
                'refact_requests': daily_refact_requests,
            },
            'monthly_projections': {
                'total_requests': projected_requests,
                'total_cost': projected_cost,
                'api_requests': projected_api_requests,
                'refact_requests': projected_refact_requests,
                'within_budget': within_budget,
                'budget_overrun': max(0, projected_cost - self.monthly_budget),
                'budget_utilization': (projected_cost / self.monthly_budget) * 100,
            },
            'warnings': self._generate_projection_warnings(projected_cost, days_elapsed),
        }

    def _generate_projection_warnings(self, projected_cost: float, days_elapsed: int) -> List[str]:
        """Generate warnings based on cost projections."""
        warnings = []

        # Budget overrun warning
        if projected_cost > self.monthly_budget:
            warnings.append(f"Projected over budget by ${projected_cost - self.monthly_budget:.2f}")

        # High spending rate warning
        if days_elapsed > 0:
            projected_daily_rate = projected_cost / 30
            current_daily_rate = projected_cost / (30 + days_elapsed)

            if current_daily_rate > projected_daily_rate * 1.2:
                warnings.append("Current spending rate is higher than projected monthly average")

        # Early month high spending
        if days_elapsed < 10 and projected_cost > self.monthly_budget * 0.5:
            warnings.append("High spending early in month - consider reducing usage")

        return warnings

    def get_pricing_info(self, model: Optional[str] = None) -> Any:
        """
        Get pricing information for specific model or all models.

        Args:
            model: Specific model name (optional)

        Returns:
            Pricing information
        """
        if model:
            pricing = self.model_pricing.get(model)
            if not pricing:
                raise ValueError(f"Model not found: {model}")
            return pricing

        # Return all pricing information as dictionary
        return {
            'models': {
                name: {
                    'cost_per_1k_tokens': pricing.cost_per_1k_tokens,
                    'is_subscription_included': pricing.is_subscription_included,
                    'max_context_length': pricing.max_context_length,
                    'provider': pricing.provider
                }
                for name, pricing in self.model_pricing.items()
            },
            'budget': {
                'monthly_budget': self.monthly_budget,
                'refact_subscription_cost': self.refact_subscription_cost,
                'api_budget': self.api_budget,
                'subscription_tier': self.subscription_tier,
            }
        }
