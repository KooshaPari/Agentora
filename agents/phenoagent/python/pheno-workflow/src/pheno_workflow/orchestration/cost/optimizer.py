"""Cost Optimizer.

Provides intelligent cost optimization through subscription management, Redis-based
caching, and smart routing strategies.
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Any

from ..core.types import TaskComplexity, TaskType

# Re-export new components for backward compatibility
from .cost_models import CostModel
from .models import UsageMetrics
from .optimizers import BudgetOptimizer, RoutingOptimizer
from .workflow_integration import CostAwareWorkflow

logger = logging.getLogger(__name__)


class CostOptimizer:
    """
    Provides intelligent cost optimization using subscription management, caching, and
    smart routing strategies.
    """

    def __init__(self, config: dict[str, Any]):
        """Initialize cost optimizer.

        Args:
            config: Configuration dictionary for cost optimization
        """
        self.config = config

        # Initialize cache layer
        self.redis_client = self._init_redis_client(config)

        # Initialize components
        self.cost_model = CostModel(config)
        self.routing_optimizer = RoutingOptimizer(self.cost_model)
        self.budget_optimizer = BudgetOptimizer(self.cost_model)
        self.workflow = CostAwareWorkflow(
            self.cost_model, self.routing_optimizer, self.budget_optimizer,
        )

        # Subscription configuration
        self.refact_api_key = config.get("refact_api_key")
        self.refact_base_url = config.get("refact_base_url", "https://api.refact.ai")

        # Usage tracking
        self.usage_metrics: dict[str, UsageMetrics] = {}

        # Cache settings
        self.cache_enabled = config.get("cache_enabled", True)
        self.cache_ttl = config.get("cache_ttl", 86400)  # 24 hours
        self.similarity_threshold = config.get("similarity_threshold", 0.85)

        logger.info(f"Cost Optimizer initialized (cache: {self.cache_enabled})")

    def _init_redis_client(self, config: dict[str, Any]) -> Any | None:
        """Initialize Redis client with fallback to in-memory cache.

        Args:
            config: Configuration dictionary

        Returns:
            Redis client or None
        """
        try:
            import redis

            redis_url = config.get("redis_url", "redis://localhost:6379")
            client = redis.Redis.from_url(redis_url, decode_responses=True)
            # Test connection
            client.ping()
            logger.info("Redis client initialized successfully")
            return client
        except Exception as e:
            logger.warning(f"Redis not available: {e}. Using in-memory cache fallback.")
            # In-memory fallback
            return {}

    async def get_strategy(
        self,
        task_type: TaskType,
        complexity: TaskComplexity,
        tenant_id: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Get optimal cost strategy for a task.

        Args:
            task_type: Type of development task
            complexity: Estimated task complexity
            tenant_id: Tenant identifier
            context: Optional task context

        Returns:
            Cost optimization strategy
        """
        # Use the workflow to get strategy
        execution_plan = await self.workflow.start_task_execution(
            task_id=f"strategy_{datetime.now().timestamp()}",
            task_type=task_type,
            complexity=complexity,
            tenant_id=tenant_id,
            context=context,
        )

        # Extract strategy components
        strategy = execution_plan["strategy"]

        return {
            "model": strategy.model,
            "max_budget": strategy.max_budget,
            "max_iterations": strategy.max_iterations,
            "use_cache": strategy.use_cache,
            "estimated_cost": strategy.estimated_cost,
            "routing_decision": strategy.routing_decision,
            "remaining_budget": execution_plan["max_budget"],
        }

    async def check_cache(
        self, task_description: str, task_context: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Check if a similar task result exists in cache.

        Args:
            task_description: Description of task
            task_context: Optional task context information

        Returns:
            Cached result if found, None otherwise
        """
        if not self.cache_enabled:
            return None

        # Create cache key from task description and context
        cache_key = self._generate_cache_key(task_description, task_context or {})

        try:
            if isinstance(self.redis_client, dict):
                # In-memory fallback
                cached_result = self.redis_client.get(f"task_cache:{cache_key}")
            else:
                # Redis client
                cached_result = self.redis_client.get(f"task_cache:{cache_key}")

            if cached_result:
                logger.debug(f"Cache hit for key: {cache_key}")
                if isinstance(cached_result, str):
                    return json.loads(cached_result)
                return cached_result

        except Exception as e:
            logger.exception(f"Cache lookup error: {e!s}")

        return None

    async def store_cache(
        self, task_description: str, task_context: dict[str, Any] | None, result: dict[str, Any],
    ):
        """Store task result in cache.

        Args:
            task_description: Description of task
            task_context: Optional task context information
            result: Task result to cache
        """
        if not self.cache_enabled:
            return

        cache_key = self._generate_cache_key(task_description, task_context or {})

        try:
            result_json = json.dumps(result)

            if isinstance(self.redis_client, dict):
                # In-memory fallback with simple expiry tracking
                self.redis_client[f"task_cache:{cache_key}"] = result_json
            else:
                # Redis client
                self.redis_client.setex(f"task_cache:{cache_key}", self.cache_ttl, result_json)

            logger.debug(f"Cached result for key: {cache_key}")
        except Exception as e:
            logger.exception(f"Cache storage error: {e!s}")

    def _generate_cache_key(self, description: str, context: dict[str, Any]) -> str:
        """Generate cache key from task description and context.

        Args:
            description: Task description
            context: Task context

        Returns:
            Cache key string
        """
        # Normalize and hash description and context
        normalized_desc = description.lower().strip()
        context_str = json.dumps(context, sort_keys=True) if context else ""

        combined = f"{normalized_desc}:{context_str}"
        return hashlib.md5(combined.encode()).hexdigest()

    async def update_usage(
        self, tenant_id: str, cost: float, routing_decision: str, cache_hit: bool = False,
    ):
        """Update usage metrics for a tenant.

        Args:
            tenant_id: Tenant identifier
            cost: Cost of operation
            routing_decision: Which routing was used
            cache_hit: Whether this was a cache hit
        """
        usage = await self._get_usage_metrics(tenant_id)

        usage.requests_count += 1
        usage.total_cost += cost

        if cache_hit:
            usage.cache_hits += 1
        else:
            usage.cache_misses += 1

        if routing_decision == "refact_subscription":
            usage.refact_requests += 1
        else:
            usage.api_requests += 1

        logger.debug(f"Updated usage for tenant {tenant_id}: ${usage.total_cost:.2f} total cost")

    async def get_cost_summary(self, tenant_id: str | None = None) -> dict[str, Any]:
        """Get cost summary for a tenant or overall system.

        Args:
            tenant_id: Optional tenant ID to filter costs

        Returns:
            Cost summary dictionary
        """
        if tenant_id:
            usage = await self._get_usage_metrics(tenant_id)
            return {
                "tenant_id": tenant_id,
                "total_requests": usage.requests_count,
                "total_cost": usage.total_cost,
                "cache_hit_rate": usage.cache_hits / max(usage.requests_count, 1),
                "refact_usage_percentage": usage.refact_requests / max(usage.requests_count, 1),
                "remaining_budget": self.cost_model.api_budget - usage.total_cost,
                "last_reset": usage.last_reset.isoformat(),
            }
        # Overall system summary
        total_cost = sum(usage.total_cost for usage in self.usage_metrics.values())
        total_requests = sum(usage.requests_count for usage in self.usage_metrics.values())
        total_cache_hits = sum(usage.cache_hits for usage in self.usage_metrics.values())
        total_refact_requests = sum(
            usage.refact_requests for usage in self.usage_metrics.values()
        )

        return {
            "total_tenants": len(self.usage_metrics),
            "total_requests": total_requests,
            "total_cost": total_cost,
            "monthly_budget": self.cost_model.monthly_budget,
            "remaining_budget": self.cost_model.api_budget - total_cost,
            "cache_hit_rate": total_cache_hits / max(total_requests, 1),
            "refact_usage_percentage": total_refact_requests / max(total_requests, 1),
            "estimated_monthly_savings": self._calculate_savings(),
        }

    def _calculate_savings(self) -> float:
        """Calculate estimated monthly savings from optimization.

        Returns:
            Estimated savings amount
        """
        total_requests = sum(usage.requests_count for usage in self.usage_metrics.values())
        sum(usage.refact_requests for usage in self.usage_metrics.values())
        sum(usage.cache_hits for usage in self.usage_metrics.values())

        if total_requests == 0:
            return 0.0

        # Estimate what costs would have been without optimization
        baseline_cost_per_request = 2.0  # Estimated average cost per request without optimization
        baseline_total_cost = total_requests * baseline_cost_per_request

        # Actual cost
        actual_cost = sum(usage.total_cost for usage in self.usage_metrics.values())
        actual_cost += self.cost_model.refact_subscription_cost  # Add subscription cost

        return max(0.0, baseline_total_cost - actual_cost)

    async def get_routing_recommendations(self, tenant_id: str) -> dict[str, Any]:
        """Get routing recommendations for a tenant based on usage patterns.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Routing recommendations
        """
        usage = await self._get_usage_metrics(tenant_id)
        recommendations = self.budget_optimizer.optimize_usage(usage)

        return {
            "tenant_id": tenant_id,
            "recommendations": recommendations,
            "total_potential_savings": sum(r["potential_savings"] for r in recommendations),
        }

    async def get_status(self) -> dict[str, Any]:
        """Get cost optimizer status.

        Returns:
            Status dictionary
        """
        return {
            "subscription_tier": self.cost_model.subscription_tier,
            "monthly_budget": self.cost_model.monthly_budget,
            "refact_subscription_cost": self.cost_model.refact_subscription_cost,
            "api_budget": self.cost_model.api_budget,
            "active_tenants": len(self.usage_metrics),
            "cache_enabled": self.cache_enabled,
            "cache_ttl": self.cache_ttl,
            "cache_type": "redis" if not isinstance(self.redis_client, dict) else "in-memory",
        }

    async def shutdown(self):
        """
        Shutdown cost optimizer.
        """
        logger.info("Cost Optimizer shutdown complete")

    # Helper methods delegating to components
    async def _get_usage_metrics(self, tenant_id: str) -> UsageMetrics:
        """Get current usage metrics for a tenant.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Current usage metrics
        """
        if tenant_id not in self.usage_metrics:
            self.usage_metrics[tenant_id] = UsageMetrics(tenant_id=tenant_id)

        usage = self.usage_metrics[tenant_id]

        # Reset monthly if needed
        if datetime.now() - usage.last_reset > timedelta(days=30):
            usage.requests_count = 0
            usage.total_cost = 0.0
            usage.cache_hits = 0
            usage.cache_misses = 0
            usage.refact_requests = 0
            usage.api_requests = 0
            usage.last_reset = datetime.now()

        return usage
