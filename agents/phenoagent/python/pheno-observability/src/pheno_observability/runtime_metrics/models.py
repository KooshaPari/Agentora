"""
Data structures for runtime metrics tracking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from datetime import datetime


class MetricCategory(StrEnum):
    """
    Categories of metrics tracked for each request.
    """

    COST = "cost"
    SPEED = "speed"
    QUALITY = "quality"
    CHAIN = "chain"


@dataclass(slots=True)
class RequestContext:
    """
    Captures request context at the time routing begins.
    """

    request_id: str
    task_type: str
    started_at: datetime
    user_id: str | None = None
    session_id: str | None = None
    input_tokens: int | None = None
    input_characters: int | None = None
    task_complexity: float | None = None
    task_risk: str | None = None
    routing_policy: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ModelSelection:
    """
    Details about the model selection step.
    """

    model_used: str | None
    candidate_models: list[str] = field(default_factory=list)
    selection_method: str | None = None
    model_tier: str | None = None


@dataclass(slots=True)
class ModelPerformance:
    """
    Quantitative metrics captured after the response is produced.
    """

    response_tokens: int | None
    latency_ms: float
    cost_in_usd: float
    cost_out_usd: float
    total_cost_usd: float | None = None
    fallback_used: bool = False
    error_occurred: bool = False
    response_characters: int | None = None
    chain_length: int = 1
    chain_position: int = 1
    cascade_cost_usd: float | None = None
    ttft_ms: float | None = None
    throughput_tps: float | None = None


@dataclass(slots=True)
class QualityAssessment:
    """
    Optional human or automated quality signals.
    """

    quality_score: float | None = None
    human_feedback_score: float | None = None
    was_successful: bool = True
    validation_passed: bool | None = None
    refinement_needed: bool | None = None


@dataclass(slots=True)
class MetricsRecord:
    """
    Flattened metrics payload ready for persistence.
    """

    request_id: str
    timestamp: datetime
    task_type: str
    model_used: str | None
    candidate_models: list[str]
    input_tokens: int | None
    input_characters: int | None
    task_complexity: float | None
    task_risk: str | None
    response_tokens: int | None
    response_characters: int | None
    latency_ms: float | None
    cost_in_usd: float | None
    cost_out_usd: float | None
    total_cost_usd: float | None
    cascade_cost_usd: float | None
    ttft_ms: float | None
    throughput_tps: float | None
    fallback_used: bool
    error_occurred: bool
    quality_score: float | None
    human_feedback_score: float | None
    was_successful: bool
    validation_passed: bool | None
    refinement_needed: bool | None
    chain_length: int
    chain_position: int
    user_id: str | None
    session_id: str | None
    model_tier: str | None
    routing_policy: str | None
    selection_method: str | None
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        """
        Return a dictionary representation suitable for persistence.
        """
        return {
            "request_id": self.request_id,
            "timestamp": self.timestamp.isoformat(),
            "task_type": self.task_type,
            "model_used": self.model_used,
            "candidate_models": self.candidate_models,
            "input_tokens": self.input_tokens,
            "input_characters": self.input_characters,
            "task_complexity": self.task_complexity,
            "task_risk": self.task_risk,
            "response_tokens": self.response_tokens,
            "response_characters": self.response_characters,
            "latency_ms": self.latency_ms,
            "cost_in_usd": self.cost_in_usd,
            "cost_out_usd": self.cost_out_usd,
            "total_cost_usd": self.total_cost_usd,
            "cascade_cost_usd": self.cascade_cost_usd,
            "ttft_ms": self.ttft_ms,
            "throughput_tps": self.throughput_tps,
            "fallback_used": self.fallback_used,
            "error_occurred": self.error_occurred,
            "quality_score": self.quality_score,
            "human_feedback_score": self.human_feedback_score,
            "was_successful": self.was_successful,
            "validation_passed": self.validation_passed,
            "refinement_needed": self.refinement_needed,
            "chain_length": self.chain_length,
            "chain_position": self.chain_position,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "model_tier": self.model_tier,
            "routing_policy": self.routing_policy,
            "selection_method": self.selection_method,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class PartialMetrics:
    """
    In-flight metrics before they are flushed to storage.
    """

    context: RequestContext
    selection: ModelSelection | None = None
    performance: ModelPerformance | None = None
    quality: QualityAssessment | None = None


def build_metrics_record(partial: PartialMetrics) -> MetricsRecord:
    """
    Construct a `MetricsRecord` from partial metrics information.
    """

    context = partial.context
    selection = partial.selection or ModelSelection(model_used=None, candidate_models=[])
    performance = partial.performance
    quality = partial.quality or QualityAssessment()

    total_cost = None
    if performance:
        total_cost = (
            performance.total_cost_usd
            if performance.total_cost_usd is not None
            else performance.cost_in_usd + performance.cost_out_usd
        )

    return MetricsRecord(
        request_id=context.request_id,
        timestamp=context.started_at,
        task_type=context.task_type,
        model_used=selection.model_used,
        candidate_models=selection.candidate_models,
        input_tokens=context.input_tokens,
        input_characters=context.input_characters,
        task_complexity=context.task_complexity,
        task_risk=context.task_risk,
        response_tokens=performance.response_tokens if performance else None,
        response_characters=performance.response_characters if performance else None,
        latency_ms=performance.latency_ms if performance else None,
        cost_in_usd=performance.cost_in_usd if performance else None,
        cost_out_usd=performance.cost_out_usd if performance else None,
        total_cost_usd=total_cost,
        cascade_cost_usd=performance.cascade_cost_usd if performance else None,
        ttft_ms=performance.ttft_ms if performance else None,
        throughput_tps=performance.throughput_tps if performance else None,
        fallback_used=performance.fallback_used if performance else False,
        error_occurred=performance.error_occurred if performance else False,
        quality_score=quality.quality_score,
        human_feedback_score=quality.human_feedback_score,
        was_successful=quality.was_successful,
        validation_passed=quality.validation_passed,
        refinement_needed=quality.refinement_needed,
        chain_length=performance.chain_length if performance else 1,
        chain_position=performance.chain_position if performance else 1,
        user_id=context.user_id,
        session_id=context.session_id,
        model_tier=selection.model_tier,
        routing_policy=context.routing_policy,
        selection_method=selection.selection_method,
        metadata=context.metadata,
    )
