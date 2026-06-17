"""
Provider option scoring and preference construction.

These helpers are intentionally model-agnostic so that any consumer (router,
CLI tools, notebooks) can evaluate OpenRouter provider variants using a
consistent value function.  The selector balances quantisation quality,
effective token pricing, throughput and optional learned performance
overrides (latency, quality) to produce an ordered list of providers together
with the preference payload understood by the OpenRouter API.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


class QuantizationLevel(StrEnum):
    """Supported quantisation identifiers normalised to OpenRouter semantics."""

    INT4 = "int4"
    INT8 = "int8"
    FP4 = "fp4"
    FP6 = "fp6"
    FP8 = "fp8"
    FP16 = "fp16"
    BF16 = "bf16"
    FP32 = "fp32"
    UNKNOWN = "unknown"

    @classmethod
    def from_string(cls, value: str | None) -> QuantizationLevel:
        """Gracefully map arbitrary strings to the known enum values."""

        if not value:
            return cls.UNKNOWN

        normalised = value.strip().lower()
        for member in cls:
            if normalised == member.value:
                return member
        return cls.UNKNOWN


@dataclass(slots=True)
class ProviderOption:
    """Raw provider data for scoring."""

    slug: str
    prompt_price_per_1k: float
    completion_price_per_1k: float
    throughput_tokens_per_s: float | None = None
    quantization: QuantizationLevel = QuantizationLevel.UNKNOWN
    latency_ms: float | None = None
    reliability_score: float | None = None  # 0.0 - 1.0
    extra: dict[str, object] = field(default_factory=dict)

    @property
    def blended_price(self) -> float:
        """
        Effective blended price per 1K tokens.

        We treat prompt + completion symmetrically because the router may not
        know the exact split when computing preferences.
        """

        return self.prompt_price_per_1k + self.completion_price_per_1k


@dataclass(slots=True)
class ProviderScore:
    """Scoring breakdown for a provider."""

    option: ProviderOption
    quantization_score: float
    cost_score: float
    throughput_score: float
    reliability_score: float
    latency_score: float
    composite: float


@dataclass(slots=True)
class ProviderPreference:
    """OpenRouter compatible preference payload."""

    order: list[str] = field(default_factory=list)
    allow_fallbacks: bool = True
    quantizations: list[str] = field(default_factory=list)
    sort: str | None = None
    max_price: dict[str, float] | None = None

    def as_dict(self) -> dict[str, object]:
        """Return a serialisable representation with falsy values stripped."""

        payload: dict[str, object] = {}
        if self.order:
            payload["order"] = self.order
        payload["allow_fallbacks"] = self.allow_fallbacks
        if self.quantizations:
            payload["quantizations"] = self.quantizations
        if self.sort:
            payload["sort"] = self.sort
        if self.max_price:
            payload["max_price"] = self.max_price
        return payload


class ProviderSelector:
    """Score providers using configurable objective weights."""

    def __init__(
        self,
        *,
        quantization_weight: float = 0.35,
        cost_weight: float = 0.35,
        throughput_weight: float = 0.2,
        reliability_weight: float = 0.07,
        latency_weight: float = 0.03,
    ) -> None:
        total = (
            quantization_weight
            + cost_weight
            + throughput_weight
            + reliability_weight
            + latency_weight
        )
        if total <= 0:
            raise ValueError("Sum of weights must be positive")

        # Normalise weights so callers can pass intuitive ratios
        self.weights = {
            "quantization": quantization_weight / total,
            "cost": cost_weight / total,
            "throughput": throughput_weight / total,
            "reliability": reliability_weight / total,
            "latency": latency_weight / total,
        }

    def score_options(
        self,
        options: Sequence[ProviderOption],
        *,
        predicted_quality: dict[str, float] | None = None,
    ) -> list[ProviderScore]:
        """
        Score each provider option.

        Args:
            options: Iterable of provider candidates.
            predicted_quality: Optional mapping of provider slug to an
                externally learned quality multiplier (0-1).  Allows the router
                to integrate regression/bandit outputs.
        """

        if not options:
            return []

        # Pre-compute normalisation anchors
        blended_prices = [o.blended_price for o in options]
        min_price = min(blended_prices)
        max_price = max(blended_prices)
        price_range = max(max_price - min_price, 1e-6)

        throughputs = [o.throughput_tokens_per_s or 0.0 for o in options]
        max_throughput = max(throughputs)
        min_throughput = min(throughputs)
        throughput_range = max(max_throughput - min_throughput, 1e-6)

        latencies = [o.latency_ms or 0.0 for o in options if o.latency_ms is not None]
        max_latency = max(latencies) if latencies else None
        min_latency = min(latencies) if latencies else None
        latency_range = (
            max(max_latency - min_latency, 1e-6) if max_latency is not None else None
        )

        scores: list[ProviderScore] = []

        for option in options:
            quant_score = self._quantization_value(option.quantization)

            cost_score = 1.0 - (option.blended_price - min_price) / price_range
            cost_score = max(0.0, min(1.0, cost_score))

            throughput_baseline = (option.throughput_tokens_per_s or min_throughput)
            throughput_score = (
                (throughput_baseline - min_throughput) / throughput_range
                if throughput_range > 0
                else 0.0
            )
            # Smooth diminishing returns so modest differences do not dominate cost
            throughput_score = throughput_score ** 0.75

            reliability_score = option.reliability_score
            if reliability_score is None:
                reliability_score = 0.75  # neutral prior
            else:
                reliability_score = max(0.0, min(1.0, reliability_score))

            if latency_range is not None and option.latency_ms is not None:
                latency_score = 1.0 - (option.latency_ms - min_latency) / latency_range
            else:
                latency_score = 0.75
            latency_score = max(0.0, min(1.0, latency_score))

            quality_multiplier = 1.0
            if predicted_quality and option.slug in predicted_quality:
                quality_multiplier = max(0.0, min(1.5, predicted_quality[option.slug]))

            composite = (
                self.weights["quantization"] * quant_score
                + self.weights["cost"] * cost_score
                + self.weights["throughput"] * throughput_score
                + self.weights["reliability"] * reliability_score
                + self.weights["latency"] * latency_score
            ) * quality_multiplier

            scores.append(
                ProviderScore(
                    option=option,
                    quantization_score=quant_score,
                    cost_score=cost_score,
                    throughput_score=throughput_score,
                    reliability_score=reliability_score,
                    latency_score=latency_score,
                    composite=composite,
                ),
            )

        scores.sort(key=lambda s: s.composite, reverse=True)
        return scores

    @staticmethod
    def _quantization_value(level: QuantizationLevel) -> float:
        """Translate quantisation preference into a [0,1] score."""

        weighting = {
            QuantizationLevel.INT4: 1.0,
            QuantizationLevel.FP4: 0.98,
            QuantizationLevel.INT8: 0.92,
            QuantizationLevel.FP6: 0.9,
            QuantizationLevel.FP8: 0.85,
            QuantizationLevel.FP16: 0.65,
            QuantizationLevel.BF16: 0.6,
            QuantizationLevel.FP32: 0.4,
            QuantizationLevel.UNKNOWN: 0.55,
        }
        return weighting.get(level, 0.55)


def build_preference_payload(
    scores: Sequence[ProviderScore],
    *,
    max_candidates: int = 5,
    prefer_lowest_price: bool = True,
) -> ProviderPreference:
    """
    Convert scores into an OpenRouter preference payload.

    Args:
        scores: Ranked provider scores (highest composite first).
        max_candidates: Maximum providers to include in the ordered list.
        prefer_lowest_price: When true, use price sorting unless throughput
            weight clearly dominates.
    """

    if not scores:
        return ProviderPreference()

    ordered = scores[:max_candidates]

    quantizations = []
    for score in ordered:
        q = score.option.quantization.value
        if q != QuantizationLevel.UNKNOWN.value and q not in quantizations:
            quantizations.append(q)

    # Determine sort strategy. If throughput advantage is significant, mimic :nitro.
    mean_cost_score = sum(s.cost_score for s in ordered) / len(ordered)
    mean_throughput_score = sum(s.throughput_score for s in ordered) / len(ordered)
    sort_field: str | None
    if not prefer_lowest_price and mean_throughput_score > mean_cost_score * 1.1:
        sort_field = "throughput"
    else:
        sort_field = "price"

    ordered[0].option.blended_price
    max_price = {
        "prompt": ordered[0].option.prompt_price_per_1k,
        "completion": ordered[0].option.completion_price_per_1k,
    }

    return ProviderPreference(
        order=[score.option.slug for score in ordered],
        allow_fallbacks=True,
        quantizations=quantizations,
        sort=sort_field,
        max_price=max_price,
    )
