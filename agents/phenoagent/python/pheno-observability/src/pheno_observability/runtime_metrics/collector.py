"""
Runtime metrics collector implementation.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from pheno.observability.runtime_metrics.models import (
    MetricsRecord,
    ModelPerformance,
    ModelSelection,
    PartialMetrics,
    QualityAssessment,
    RequestContext,
    build_metrics_record,
)
from pheno.observability.runtime_metrics.storage import (
    MetricsStorage,
    NoOpMetricsStorage,
    SqliteMetricsStorage,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Collects request lifecycle metrics and persists them in batches.
    """

    def __init__(
        self,
        storage_backend: MetricsStorage | None = None,
        flush_batch_size: int = 100,
    ) -> None:
        self._storage: MetricsStorage = storage_backend or NoOpMetricsStorage()
        self._flush_batch_size = flush_batch_size
        self._inflight: dict[str, PartialMetrics] = {}
        self._cache: list[MetricsRecord] = []

        logger.info("MetricsCollector initialized", extra={"component": "runtime_metrics"})

    @classmethod
    def from_sqlite(
        cls,
        database_path,
        *,
        flush_batch_size: int = 100,
    ) -> MetricsCollector:
        """
        Create a collector wired to an SQLite database.
        """

        storage = SqliteMetricsStorage(Path(database_path))
        return cls(storage_backend=storage, flush_batch_size=flush_batch_size)

    def record_request_start(
        self,
        request_id: str,
        task_type: str,
        user_id: str | None = None,
        session_id: str | None = None,
        input_tokens: int | None = None,
        input_characters: int | None = None,
        *,
        task_complexity: float | None = None,
        task_risk: str | None = None,
        routing_policy: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> None:
        """
        Mark the beginning of a request.
        """

        context = RequestContext(
            request_id=request_id,
            task_type=task_type,
            started_at=datetime.now(tz=UTC),
            user_id=user_id,
            session_id=session_id,
            input_tokens=input_tokens,
            input_characters=input_characters,
            task_complexity=task_complexity,
            task_risk=task_risk,
            routing_policy=routing_policy,
            metadata=metadata or {},
        )
        self._inflight[request_id] = PartialMetrics(context=context)
        logger.debug(
            "runtime_metrics:request_start",
            extra={
                "component": "runtime_metrics",
                "request_id": request_id,
                "task_type": task_type,
            },
        )

    def record_model_selection(
        self,
        request_id: str,
        model_used: str | None,
        candidate_models: Sequence[str],
        *,
        selection_method: str | None = None,
        model_tier: str | None = None,
    ) -> None:
        """
        Attach model selection information to an in-flight request.
        """

        partial = self._require_request(request_id)
        if not partial:
            return

        partial.selection = ModelSelection(
            model_used=model_used,
            candidate_models=list(candidate_models),
            selection_method=selection_method,
            model_tier=model_tier,
        )
        logger.debug(
            "runtime_metrics:model_selection",
            extra={
                "component": "runtime_metrics",
                "request_id": request_id,
                "model_used": model_used,
                "candidate_models": list(candidate_models),
                "selection_method": selection_method,
            },
        )

    def record_model_performance(
        self,
        request_id: str,
        response_tokens: int | None,
        latency_ms: float,
        cost_in_usd: float,
        cost_out_usd: float,
        *,
        input_tokens: int | None = None,
        response_characters: int | None = None,
        fallback_used: bool = False,
        error_occurred: bool = False,
        chain_length: int = 1,
        chain_position: int = 1,
        total_cost_usd: float | None = None,
        cascade_cost_usd: float | None = None,
        ttft_ms: float | None = None,
        throughput_tps: float | None = None,
    ) -> None:
        """
        Record quantitative metrics once the model responds.
        """

        partial = self._require_request(request_id)
        if not partial:
            return

        if input_tokens is not None:
            partial.context.input_tokens = input_tokens

        partial.performance = ModelPerformance(
            response_tokens=response_tokens,
            response_characters=response_characters,
            latency_ms=latency_ms,
            cost_in_usd=cost_in_usd,
            cost_out_usd=cost_out_usd,
            total_cost_usd=total_cost_usd,
            fallback_used=fallback_used,
            error_occurred=error_occurred,
            chain_length=chain_length,
            chain_position=chain_position,
            cascade_cost_usd=cascade_cost_usd,
            ttft_ms=ttft_ms,
            throughput_tps=throughput_tps,
        )
        logger.debug(
            "runtime_metrics:model_performance",
            extra={
                "component": "runtime_metrics",
                "request_id": request_id,
                "latency_ms": latency_ms,
                "cost_in_usd": cost_in_usd,
                "cost_out_usd": cost_out_usd,
            },
        )

    def record_quality_assessment(
        self,
        request_id: str,
        *,
        quality_score: float | None = None,
        human_feedback_score: float | None = None,
        was_successful: bool = True,
        validation_passed: bool | None = None,
        refinement_needed: bool | None = None,
    ) -> None:
        """
        Attach quality metrics collected post-response.
        """

        partial = self._require_request(request_id)
        if not partial:
            return

        partial.quality = QualityAssessment(
            quality_score=quality_score,
            human_feedback_score=human_feedback_score,
            was_successful=was_successful,
            validation_passed=validation_passed,
            refinement_needed=refinement_needed,
        )
        logger.debug(
            "runtime_metrics:quality_assessment",
            extra={
                "component": "runtime_metrics",
                "request_id": request_id,
                "quality_score": quality_score,
                "human_feedback_score": human_feedback_score,
            },
        )

    def finalize_request(self, request_id: str) -> MetricsRecord | None:
        """
        Finalize an in-flight request and cache the resulting record.
        """

        partial = self._inflight.pop(request_id, None)
        if not partial:
            logger.warning(
                "runtime_metrics:missing_request",
                extra={"component": "runtime_metrics", "request_id": request_id},
            )
            return None

        record = build_metrics_record(partial)
        self._cache.append(record)
        logger.debug(
            "runtime_metrics:request_finalized",
            extra={
                "component": "runtime_metrics",
                "request_id": request_id,
                "latency_ms": record.latency_ms,
                "model_used": record.model_used,
            },
        )

        if len(self._cache) >= self._flush_batch_size:
            self.flush_cache()
        return record

    def flush_cache(self) -> None:
        """
        Persist all cached records using the configured storage backend.
        """

        if not self._cache:
            return

        try:
            self._storage.write_records(self._cache)
            logger.info(
                "runtime_metrics:flushed",
                extra={"component": "runtime_metrics", "count": len(self._cache)},
            )
        finally:
            self._cache.clear()

    def get_cached_records(self) -> list[MetricsRecord]:
        """
        Return a copy of cached records (useful for testing).
        """

        return list(self._cache)

    def inflight_request_ids(self) -> Iterable[str]:
        """
        Iterate over in-flight request IDs.
        """

        return list(self._inflight.keys())

    def _require_request(self, request_id: str) -> PartialMetrics | None:
        partial = self._inflight.get(request_id)
        if not partial:
            logger.warning(
                "runtime_metrics:missing_context",
                extra={"component": "runtime_metrics", "request_id": request_id},
            )
        return partial
