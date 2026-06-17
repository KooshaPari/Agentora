"""LLM Routing Module - Intelligent model selection and routing.

This module provides advanced routing strategies for selecting optimal LLM models
based on task requirements, cost constraints, latency requirements, and quality goals.

Key Components:
- EnsembleRouter: Main router combining 7 routing strategies
- Individual strategies for specific optimization goals
- Configurable voting and aggregation mechanisms
- Historical performance tracking
- Multi-objective optimization

Example:
    Basic usage with ensemble routing:

    >>> from pheno.llm.routing import EnsembleRouter, EnsembleConfig, EnsembleMethod
    >>> from pheno.llm.ports import RoutingContext
    >>>
    >>> # Configure router
    >>> config = EnsembleConfig(
    ...     enabled_methods=[
    ...         EnsembleMethod.CAPABILITY_MATCHING,
    ...         EnsembleMethod.COST_OPTIMIZATION,
    ...         EnsembleMethod.QUALITY_VOTING,
    ...     ],
    ...     voting_strategy="weighted",
    ... )
    >>>
    >>> # Create router
    >>> router = EnsembleRouter(registry=my_registry, config=config)
    >>>
    >>> # Route request
    >>> context = RoutingContext(
    ...     query="Explain quantum computing",
    ...     task_type="reasoning",
    ...     estimated_tokens=1000,
    ... )
    >>> result = await router.route(context)
    >>> print(f"Selected: {result.selected_model}")
"""

from pheno.llm.routing.ensemble import (
    BaseRoutingStrategy,
    CapabilityMatchingStrategy,
    CostOptimizationStrategy,
    EnsembleConfig,
    EnsembleMethod,
    EnsembleRouter,
    HistoricalPerformanceStrategy,
    LatencyOptimizationStrategy,
    MultiObjectiveStrategy,
    QualityVotingStrategy,
    UncertaintyBasedStrategy,
    create_ensemble_router,
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
