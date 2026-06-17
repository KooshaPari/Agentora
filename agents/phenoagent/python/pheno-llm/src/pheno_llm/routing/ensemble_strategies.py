"""Routing strategy implementations for ensemble routing.

This module contains all 7 routing strategy implementations:
1. Capability Matching: Match task requirements to model capabilities
2. Cost Optimization: Select cheapest model meeting quality threshold
3. Latency Optimization: Select fastest model meeting quality threshold
4. Quality Voting: Ensemble vote across quality signals
5. Uncertainty-Based: Route based on query complexity/confidence
6. Historical Performance: Learn from past routing decisions
7. Multi-Objective: Balance cost, latency, and quality using Pareto optimization
"""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from typing import Any

from pheno.llm.ports import ModelRegistryPort, RoutingContext, RoutingMetricsPort

from .ensemble_base import BaseRoutingStrategy


class CapabilityMatchingStrategy(BaseRoutingStrategy):
    """Strategy 1: Match task requirements to model capabilities."""

    async def route(self, context: RoutingContext) -> str:
        """Select model based on capability matching.

        Args:
            context: Routing context

        Returns:
            Best matching model
        """
        all_models = self.registry.get_all_models()
        scores: dict[str, float] = {}

        for model_name in all_models:
            caps = self.registry.get_capabilities(model_name)
            if not caps:
                continue

            score = 0.0

            context_window = caps.get("context_window", 0)
            if context_window >= context.estimated_tokens:
                score += 3.0
            else:
                continue

            model_lower = model_name.lower()
            if context.task_type == "code" and caps.get("supports_function_calling"):
                score += 2.0
            if context.task_type == "reasoning" and "o3" in model_lower:
                score += 2.5
            if context.task_type == "fast" and "flash" in model_lower:
                score += 2.0
            if context.task_type == "vision" and caps.get("supports_images"):
                score += 2.5

            if context.preferred_providers:
                provider = caps.get("provider", "")
                if provider in context.preferred_providers:
                    score += 1.0

            scores[model_name] = score

        if not scores:
            return "gpt-4o-mini"

        return max(scores, key=scores.get)  # type: ignore


class CostOptimizationStrategy(BaseRoutingStrategy):
    """Strategy 2: Select cheapest model meeting quality threshold."""

    async def route(self, context: RoutingContext) -> str:
        """Select most cost-effective model.

        Args:
            context: Routing context

        Returns:
            Most cost-effective model
        """
        all_models = self.registry.get_all_models()
        valid_models: list[tuple[str, dict[str, Any]]] = []

        for model_name in all_models:
            caps = self.registry.get_capabilities(model_name)
            if not caps:
                continue

            if caps.get("context_window", 0) < context.estimated_tokens:
                continue

            valid_models.append((model_name, caps))

        if not valid_models:
            return "gpt-4o-mini"

        def get_cost(item: tuple[str, dict[str, Any]]) -> float:
            _, caps = item
            input_cost = caps.get("input_cost_per_1k") or 0
            output_cost = caps.get("output_cost_per_1k") or 0
            return float(input_cost + output_cost)

        valid_models.sort(key=get_cost)

        for model_name, caps in valid_models:
            if context.quality_threshold < 0.8:
                return model_name
            if "pro" in model_name.lower() or "opus" in model_name.lower():
                return model_name

        return valid_models[0][0]


class LatencyOptimizationStrategy(BaseRoutingStrategy):
    """Strategy 3: Select fastest model meeting quality threshold."""

    async def route(self, context: RoutingContext) -> str:
        """Select fastest suitable model.

        Args:
            context: Routing context

        Returns:
            Fastest suitable model
        """
        all_models = self.registry.get_all_models()

        fast_keywords = ["flash", "3.5", "turbo", "mini", "fast"]
        fast_models = [
            m for m in all_models if any(kw in m.lower() for kw in fast_keywords)
        ]

        valid_fast: list[str] = []
        for model_name in fast_models:
            caps = self.registry.get_capabilities(model_name)
            if caps and caps.get("context_window", 0) >= context.estimated_tokens:
                valid_fast.append(model_name)

        if valid_fast:
            return valid_fast[0]

        for model_name in all_models:
            caps = self.registry.get_capabilities(model_name)
            if caps and caps.get("context_window", 0) >= context.estimated_tokens:
                return model_name

        return "gpt-4o-mini"


class QualityVotingStrategy(BaseRoutingStrategy):
    """Strategy 4: Ensemble vote across quality signals."""

    async def route(self, context: RoutingContext) -> str:
        """Vote across multiple quality signals.

        Args:
            context: Routing context

        Returns:
            Model with highest quality vote
        """
        signals: list[str] = []

        task_preferences = {
            "reasoning": ["o3-mini", "gemini-2.5-pro", "claude-3-5-sonnet"],
            "code": ["gpt-4o", "claude-3-5-sonnet", "gemini-2.5-pro"],
            "vision": ["gpt-4o", "gemini-2.5-pro", "claude-3-5-sonnet"],
            "fast": ["gemini-2.0-flash", "gpt-4o-mini", "claude-3-haiku"],
        }

        preferred = task_preferences.get(context.task_type, ["gemini-2.5-pro"])
        signals.extend(preferred[:2])

        if context.estimated_tokens > 100000:
            signals.append("gemini-2.5-pro")
        else:
            signals.append("gpt-4o")

        if self.metrics:
            try:
                history = self.metrics.get_performance_history(
                    task_type=context.task_type,
                    limit=50,
                )
                if history:
                    model_scores: dict[str, list[float]] = defaultdict(list)
                    for record in history:
                        model_scores[record["model"]].append(
                            record.get("quality_score", 0.7),
                        )

                    avg_scores = {
                        m: sum(scores) / len(scores)
                        for m, scores in model_scores.items()
                    }
                    if avg_scores:
                        best = max(avg_scores, key=avg_scores.get)  # type: ignore
                        signals.append(best)
            except Exception as e:
                self.logger.debug(f"Failed to get historical data: {e}")

        vote_counts = Counter(signals)
        return vote_counts.most_common(1)[0][0]


class UncertaintyBasedStrategy(BaseRoutingStrategy):
    """Strategy 5: Route based on query uncertainty/complexity."""

    async def route(self, context: RoutingContext) -> str:
        """Route based on uncertainty level.

        Args:
            context: Routing context

        Returns:
            Model suited for uncertainty level
        """
        query_length = len(context.query.split())
        uncertainty_keywords = [
            "maybe",
            "possibly",
            "uncertain",
            "not sure",
            "complex",
            "difficult",
            "challenging",
        ]
        has_uncertainty = any(
            kw in context.query.lower() for kw in uncertainty_keywords
        )

        if has_uncertainty or query_length > 100:
            candidates = ["gemini-2.5-pro", "gpt-4o", "claude-3-5-sonnet"]
            for model in candidates:
                if model in self.registry.get_all_models():
                    return model
            return "gpt-4o"

        candidates = ["gemini-2.0-flash", "gpt-4o-mini", "claude-3-haiku"]
        for model in candidates:
            if model in self.registry.get_all_models():
                return model
        return "gpt-4o-mini"


class HistoricalPerformanceStrategy(BaseRoutingStrategy):
    """Strategy 6: Use historical performance data."""

    async def route(self, context: RoutingContext) -> str:
        """Route based on historical performance.

        Args:
            context: Routing context

        Returns:
            Best performing model from history
        """
        if not self.metrics:
            fallback = CapabilityMatchingStrategy(
                self.registry, self.metrics, self.logger,
            )
            return await fallback.route(context)

        try:
            history = self.metrics.get_performance_history(
                task_type=context.task_type,
                limit=100,
            )

            if not history:
                fallback = CapabilityMatchingStrategy(
                    self.registry,
                    self.metrics,
                    self.logger,
                )
                return await fallback.route(context)

            model_scores: dict[str, list[float]] = defaultdict(list)
            for record in history:
                model_scores[record["model"]].append(record.get("quality_score", 0.7))

            avg_scores = {
                model: sum(scores) / len(scores)
                for model, scores in model_scores.items()
            }

            if avg_scores:
                return max(avg_scores, key=avg_scores.get)  # type: ignore

        except Exception as e:
            self.logger.debug(f"Historical performance strategy failed: {e}")

        return "gemini-2.5-pro"


class MultiObjectiveStrategy(BaseRoutingStrategy):
    """Strategy 7: Multi-objective optimization (cost + latency + quality)."""

    def __init__(
        self,
        registry: ModelRegistryPort,
        metrics: RoutingMetricsPort | None = None,
        logger: logging.Logger | None = None,
        quality_weight: float = 0.4,
        cost_weight: float = 0.3,
        latency_weight: float = 0.3,
    ):
        """Initialize multi-objective strategy.

        Args:
            registry: Model registry
            metrics: Optional metrics tracker
            logger: Optional logger
            quality_weight: Weight for quality optimization
            cost_weight: Weight for cost optimization
            latency_weight: Weight for latency optimization
        """
        super().__init__(registry, metrics, logger)
        self.quality_weight = quality_weight
        self.cost_weight = cost_weight
        self.latency_weight = latency_weight

    async def route(self, context: RoutingContext) -> str:
        """Route using multi-objective optimization.

        Args:
            context: Routing context

        Returns:
            Pareto-optimal model
        """
        all_models = self.registry.get_all_models()
        scores: dict[str, float] = {}

        for model_name in all_models:
            caps = self.registry.get_capabilities(model_name)
            if not caps:
                continue

            if caps.get("context_window", 0) < context.estimated_tokens:
                continue

            context_window = caps.get("context_window", 0)
            quality_score = min(1.0, context_window / 200000)
            model_lower = model_name.lower()
            if "pro" in model_lower or "opus" in model_lower or "o3" in model_lower:
                quality_score = min(1.0, quality_score + 0.2)

            input_cost = caps.get("input_cost_per_1k") or 0
            output_cost = caps.get("output_cost_per_1k") or 0
            total_cost = float(input_cost + output_cost)
            max_cost = 0.1
            cost_score = 1.0 - min(1.0, total_cost / max_cost) if max_cost > 0 else 0.5

            latency_score = (
                0.9
                if any(kw in model_lower for kw in ["flash", "mini", "turbo"])
                else 0.6
            )

            total_score = (
                self.quality_weight * quality_score
                + self.cost_weight * cost_score
                + self.latency_weight * latency_score
            )

            scores[model_name] = total_score

        if not scores:
            return "gpt-4o-mini"

        return max(scores, key=scores.get)  # type: ignore
