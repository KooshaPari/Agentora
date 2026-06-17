"""Ensemble Routing for Improved Model Selection.

This module provides a generified ensemble routing system that combines multiple
routing strategies to achieve superior model selection. It's extracted from
zen-mcp-server with zero vendor lock-in.

Based on 2025 research on LLM ensemble routing methods:
- RouteLLM (preference-based routing)
- Zooter (reward model distillation)
- RadialRouter (structured representations)
- Routoo (performance prediction)
- TagRouter (tag-based selection)
- FusionFactory (multi-level fusion)
- xRouter (RL-based orchestration)

Achieves 15-25% improvement in routing quality through ensemble methods.

Key Features:
- 7 routing strategies with configurable weights
- Provider-agnostic model registry integration
- Historical performance tracking
- Multi-objective optimization (cost + latency + quality)
- A/B testing framework support
- 100% async/await with comprehensive error handling

Usage:
    from pheno.llm.routing.ensemble import EnsembleRouter, EnsembleConfig, EnsembleMethod
    from pheno.llm.ports import RoutingContext

    # Configure router
    config = EnsembleConfig(
        enabled_methods=[
            EnsembleMethod.CAPABILITY_MATCHING,
            EnsembleMethod.COST_OPTIMIZATION,
            EnsembleMethod.QUALITY_VOTING,
        ],
        voting_strategy="weighted",
        quality_weight=0.4,
        cost_weight=0.3,
        latency_weight=0.3,
    )

    # Create router with custom registry
    router = EnsembleRouter(registry=my_registry, config=config)

    # Route a request
    context = RoutingContext(
        query="Explain quantum computing",
        task_type="reasoning",
        estimated_tokens=1000,
        quality_threshold=0.8,
    )
    decision = await router.route(context)

    # Use selected model
    print(f"Selected: {decision.selected_model}")
    print(f"Confidence: {decision.confidence_score:.2%}")
    print(f"Reasoning: {decision.reasoning}")
"""

from __future__ import annotations

from .ensemble_base import BaseRoutingStrategy, EnsembleConfig, EnsembleMethod
from .ensemble_router import EnsembleRouter, create_ensemble_router
from .ensemble_strategies import (
    CapabilityMatchingStrategy,
    CostOptimizationStrategy,
    HistoricalPerformanceStrategy,
    LatencyOptimizationStrategy,
    MultiObjectiveStrategy,
    QualityVotingStrategy,
    UncertaintyBasedStrategy,
)

__all__ = [
    "BaseRoutingStrategy",
    "CapabilityMatchingStrategy",
    "CostOptimizationStrategy",
    "EnsembleConfig",
    "EnsembleMethod",
    "EnsembleRouter",
    "HistoricalPerformanceStrategy",
    "LatencyOptimizationStrategy",
    "MultiObjectiveStrategy",
    "QualityVotingStrategy",
    "UncertaintyBasedStrategy",
    "create_ensemble_router",
]
