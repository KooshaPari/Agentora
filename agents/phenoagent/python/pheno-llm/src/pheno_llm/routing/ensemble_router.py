"""Ensemble router implementation.

This module provides the EnsembleRouter class that combines multiple routing
strategies to achieve superior model selection through ensemble voting.
"""

from __future__ import annotations

import asyncio
import logging
from collections import Counter, defaultdict
from typing import Any

from pheno.llm.ports import (
    ModelRegistryPort,
    RoutingContext,
    RoutingMetricsPort,
    RoutingResult,
)

from .ensemble_base import BaseRoutingStrategy, EnsembleConfig, EnsembleMethod
from .ensemble_strategies import (
    CapabilityMatchingStrategy,
    CostOptimizationStrategy,
    HistoricalPerformanceStrategy,
    LatencyOptimizationStrategy,
    MultiObjectiveStrategy,
    QualityVotingStrategy,
    UncertaintyBasedStrategy,
)


class EnsembleRouter:
    """Ensemble router combining multiple routing strategies.

    Combines up to 7 routing methods to achieve superior model selection:
    1. Capability Matching: Match task requirements to model capabilities
    2. Cost Optimization: Select cheapest model meeting quality threshold
    3. Latency Optimization: Select fastest model meeting quality threshold
    4. Quality Voting: Ensemble vote across quality signals
    5. Uncertainty-Based: Route based on query complexity/confidence
    6. Historical Performance: Learn from past routing decisions
    7. Multi-Objective: Balance cost, latency, and quality using Pareto optimization
    """

    def __init__(
        self,
        registry: ModelRegistryPort,
        metrics: RoutingMetricsPort | None = None,
        config: EnsembleConfig | None = None,
        logger: logging.Logger | None = None,
    ):
        """Initialize ensemble router.

        Args:
            registry: Model capability registry (required)
            metrics: Optional metrics tracker for historical performance
            config: Optional routing configuration
            logger: Optional custom logger
        """
        self.registry = registry
        self.metrics = metrics
        self.config = config or EnsembleConfig()
        self.logger = logger or logging.getLogger(__name__)

        self._strategies = self._initialize_strategies()

        self._stats = {
            "total_routes": 0,
            "method_agreement": defaultdict(float),
            "avg_confidence": 0.0,
        }

    def _initialize_strategies(self) -> dict[EnsembleMethod, BaseRoutingStrategy]:
        """Initialize all routing strategies.

        Returns:
            Dictionary mapping ensemble methods to strategy instances
        """
        strategies: dict[EnsembleMethod, BaseRoutingStrategy] = {}

        if EnsembleMethod.CAPABILITY_MATCHING in self.config.enabled_methods:
            strategies[EnsembleMethod.CAPABILITY_MATCHING] = CapabilityMatchingStrategy(
                self.registry,
                self.metrics,
                self.logger,
            )

        if EnsembleMethod.COST_OPTIMIZATION in self.config.enabled_methods:
            strategies[EnsembleMethod.COST_OPTIMIZATION] = CostOptimizationStrategy(
                self.registry,
                self.metrics,
                self.logger,
            )

        if EnsembleMethod.LATENCY_OPTIMIZATION in self.config.enabled_methods:
            strategies[EnsembleMethod.LATENCY_OPTIMIZATION] = (
                LatencyOptimizationStrategy(
                    self.registry,
                    self.metrics,
                    self.logger,
                )
            )

        if EnsembleMethod.QUALITY_VOTING in self.config.enabled_methods:
            strategies[EnsembleMethod.QUALITY_VOTING] = QualityVotingStrategy(
                self.registry,
                self.metrics,
                self.logger,
            )

        if EnsembleMethod.UNCERTAINTY_BASED in self.config.enabled_methods:
            strategies[EnsembleMethod.UNCERTAINTY_BASED] = UncertaintyBasedStrategy(
                self.registry,
                self.metrics,
                self.logger,
            )

        if EnsembleMethod.HISTORICAL_PERFORMANCE in self.config.enabled_methods:
            strategies[EnsembleMethod.HISTORICAL_PERFORMANCE] = (
                HistoricalPerformanceStrategy(
                    self.registry,
                    self.metrics,
                    self.logger,
                )
            )

        if EnsembleMethod.MULTI_OBJECTIVE in self.config.enabled_methods:
            strategies[EnsembleMethod.MULTI_OBJECTIVE] = MultiObjectiveStrategy(
                self.registry,
                self.metrics,
                self.logger,
                self.config.quality_weight,
                self.config.cost_weight,
                self.config.latency_weight,
            )

        return strategies

    async def route(self, context: RoutingContext) -> RoutingResult:
        """Route request using ensemble methods.

        Args:
            context: Routing context with query and constraints

        Returns:
            RoutingResult with selected model and reasoning
        """
        self.logger.info(f"Ensemble routing for task: {context.task_type}")

        method_votes: dict[EnsembleMethod, str] = {}

        async def execute_strategy(
            method: EnsembleMethod,
            strategy: BaseRoutingStrategy,
        ) -> tuple[EnsembleMethod, str | None]:
            try:
                model = await strategy.route(context)
                return (method, model)
            except Exception as e:
                self.logger.warning(f"Strategy {method.value} failed: {e}")
                return (method, None)

        tasks = [
            execute_strategy(method, strategy)
            for method, strategy in self._strategies.items()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                continue
            method, model = result
            if model:
                method_votes[method] = model

        decision = self._aggregate_votes(method_votes, context)
        self._update_stats(decision)

        self.logger.info(
            f"Ensemble decision: {decision.selected_model} "
            f"(confidence: {decision.confidence_score:.2f})",
        )

        return decision

    def _aggregate_votes(
        self,
        method_votes: dict[EnsembleMethod, str],
        context: RoutingContext,
    ) -> RoutingResult:
        """Aggregate votes from multiple strategies.

        Args:
            method_votes: Votes from each strategy
            context: Routing context

        Returns:
            Final routing decision
        """
        if not method_votes:
            return RoutingResult(
                selected_model=self.config.fallback_model,
                confidence_score=0.5,
                reasoning="No ensemble methods succeeded, using fallback",
                alternatives=[],
                estimated_cost=0.0,
                estimated_latency=1.0,
            )

        vote_counts = Counter(method_votes.values())

        if self.config.voting_strategy == "majority":
            winner = vote_counts.most_common(1)[0][0]
            confidence = vote_counts[winner] / len(method_votes)

        elif self.config.voting_strategy == "weighted":
            weighted_votes: dict[str, float] = defaultdict(float)
            for method, model in method_votes.items():
                weight = self.config.method_weights.get(method, 1.0)
                weighted_votes[model] += weight

            winner = max(weighted_votes, key=weighted_votes.get)  # type: ignore
            total_weight = sum(
                self.config.method_weights.get(m, 1.0) for m in method_votes
            )
            confidence = (
                weighted_votes[winner] / total_weight if total_weight > 0 else 0.5
            )

        elif vote_counts.most_common(1)[0][1] >= len(method_votes) * 0.6:
            winner = vote_counts.most_common(1)[0][0]
            confidence = vote_counts[winner] / len(method_votes)
        else:
            winner = method_votes.get(
                EnsembleMethod.MULTI_OBJECTIVE,
                self.config.fallback_model,
            )
            confidence = 0.5

        alternatives = [
            (model, count / len(method_votes))
            for model, count in vote_counts.most_common(5)
            if model != winner
        ]

        caps = self.registry.get_capabilities(winner)
        if caps:
            input_cost = caps.get("input_cost_per_1k") or 0
            output_cost = caps.get("output_cost_per_1k") or 0
            estimated_cost = (
                float(input_cost + output_cost) * context.estimated_tokens / 1000
            )
            estimated_latency = (
                0.5 if "flash" in winner.lower() or "mini" in winner.lower() else 1.5
            )
        else:
            estimated_cost = 0.0
            estimated_latency = 1.0

        reasoning = (
            f"Ensemble routing with {len(method_votes)} strategies. "
            f"Winner: {winner} with {confidence:.1%} confidence. "
            f"Methods: {', '.join(m.value for m in method_votes)}"
        )

        return RoutingResult(
            selected_model=winner,
            confidence_score=confidence,
            reasoning=reasoning,
            alternatives=alternatives,
            estimated_cost=estimated_cost,
            estimated_latency=estimated_latency,
            metadata={
                "method_votes": {m.value: model for m, model in method_votes.items()},
            },
        )

    def _update_stats(self, decision: RoutingResult):
        """Update routing statistics.

        Args:
            decision: Routing decision
        """
        self._stats["total_routes"] += 1

        n = self._stats["total_routes"]
        current_avg = self._stats["avg_confidence"]
        self._stats["avg_confidence"] = (
            current_avg * (n - 1) + decision.confidence_score
        ) / n

        if decision.metadata and "method_votes" in decision.metadata:
            method_votes = decision.metadata["method_votes"]
            if len(method_votes) > 1:
                unique_models = len(set(method_votes.values()))
                agreement_pct = (len(method_votes) - unique_models + 1) / len(
                    method_votes,
                )
                self._stats["method_agreement"]["total"] += agreement_pct

    def get_statistics(self) -> dict[str, Any]:
        """Get routing statistics.

        Returns:
            Statistics dictionary
        """
        stats = dict(self._stats)
        if self.metrics:
            try:
                metrics_stats = self.metrics.get_statistics()
                stats["metrics"] = metrics_stats
            except Exception:
                pass
        return stats

    def add_strategy(
        self, method: EnsembleMethod, strategy: BaseRoutingStrategy,
    ) -> None:
        """Add or replace a routing strategy.

        Args:
            method: Ensemble method identifier
            strategy: Strategy implementation
        """
        self._strategies[method] = strategy
        if method not in self.config.enabled_methods:
            self.config.enabled_methods.append(method)

    def remove_strategy(self, method: EnsembleMethod) -> None:
        """Remove a routing strategy.

        Args:
            method: Ensemble method to remove
        """
        if method in self._strategies:
            del self._strategies[method]
        if method in self.config.enabled_methods:
            self.config.enabled_methods.remove(method)


def create_ensemble_router(
    registry: ModelRegistryPort,
    metrics: RoutingMetricsPort | None = None,
    enabled_methods: list[EnsembleMethod] | None = None,
    voting_strategy: str = "weighted",
    **kwargs,
) -> EnsembleRouter:
    """Create an ensemble router with sensible defaults.

    Args:
        registry: Model capability registry
        metrics: Optional metrics tracker
        enabled_methods: List of methods to enable (defaults to all 7)
        voting_strategy: Voting strategy ('majority', 'weighted', 'consensus')
        **kwargs: Additional config parameters

    Returns:
        Configured EnsembleRouter instance

    Example:
        >>> router = create_ensemble_router(
        ...     registry=my_registry,
        ...     enabled_methods=[
        ...         EnsembleMethod.CAPABILITY_MATCHING,
        ...         EnsembleMethod.COST_OPTIMIZATION,
        ...         EnsembleMethod.QUALITY_VOTING,
        ...     ],
        ... )
    """
    config = EnsembleConfig(
        enabled_methods=enabled_methods or list(EnsembleMethod),
        voting_strategy=voting_strategy,
        **kwargs,
    )
    return EnsembleRouter(registry=registry, metrics=metrics, config=config)
