"""
LLM Ports - Abstract interfaces for LLM integrations.

This module defines ports (interfaces) for LLM operations to enable pluggable
implementations across different providers (OpenAI, Anthropic, etc.).
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable


class ModelProvider(StrEnum):
    """
    Supported LLM model providers.
    """

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    COHERE = "cohere"
    CUSTOM = "custom"


@dataclass
class LLMRequest:
    """
    Standardized LLM request.
    """

    prompt: str
    model: str
    temperature: float = 0.7
    max_tokens: int | None = None
    top_p: float | None = None
    stop_sequences: list[str] | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class LLMResponse:
    """
    Standardized LLM response.
    """

    content: str
    model: str
    tokens_used: int | None = None
    tokens_prompt: int | None = None
    tokens_completion: int | None = None
    finish_reason: str | None = None
    metadata: dict[str, Any] | None = None


@runtime_checkable
class LLMClientPort(Protocol):
    """
    Port for LLM client implementations.
    """

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Generate text from an LLM.
        """
        ...

    async def generate_with_streaming(self, request: LLMRequest):
        """
        Generate text with streaming response.
        """
        ...

    def get_model_info(self, model: str) -> dict[str, Any]:
        """
        Get information about a model.
        """
        ...


@runtime_checkable
class ContextStoragePort(Protocol):
    """
    Port for context storage implementations.
    """

    async def save(self, context_id: str, content: str, metadata: dict | None = None) -> str:
        """
        Save context to storage.
        """
        ...

    async def load(self, context_id: str) -> str:
        """
        Load context from storage.
        """
        ...

    async def delete(self, context_id: str) -> bool:
        """
        Delete context from storage.
        """
        ...

    async def exists(self, context_id: str) -> bool:
        """
        Check if context exists.
        """
        ...


@runtime_checkable
class ModelRouterPort(Protocol):
    """
    Port for model routing implementations.
    """

    def select_model(self, task: str, constraints: dict | None = None) -> str:
        """
        Select optimal model for a task.
        """
        ...

    async def route(self, request: LLMRequest) -> LLMResponse:
        """
        Route request to optimal model.
        """
        ...

    def get_available_models(self) -> list[str]:
        """
        Get list of available models.
        """
        ...


@dataclass
class RoutingContext:
    """
    Context for routing decisions with constraints and preferences.
    """

    query: str
    task_type: str = "general"
    estimated_tokens: int = 0
    quality_threshold: float = 0.7
    cost_budget: float | None = None
    latency_budget: float | None = None
    preferred_providers: list[str] | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class RoutingResult:
    """
    Result of a routing decision with rationale.
    """

    selected_model: str
    confidence_score: float
    reasoning: str
    alternatives: list[tuple[str, float]]
    estimated_cost: float
    estimated_latency: float
    metadata: dict[str, Any] | None = None


@runtime_checkable
class RoutingStrategyPort(Protocol):
    """
    Port for individual routing strategy implementations.
    """

    async def route(self, context: RoutingContext) -> str:
        """Route request using this strategy.

        Args:
            context: Routing context with query and constraints

        Returns:
            Selected model name
        """
        ...

    def get_name(self) -> str:
        """
        Get the name of this routing strategy.
        """
        ...


@runtime_checkable
class ModelRegistryPort(Protocol):
    """
    Port for model capability registry.
    """

    def get_capabilities(self, model_name: str) -> dict[str, Any] | None:
        """
        Get capabilities for a specific model.
        """
        ...

    def get_all_models(self) -> list[str]:
        """
        Get all available model names.
        """
        ...

    def search_models(
        self,
        min_context_window: int | None = None,
        supports_images: bool | None = None,
        supports_function_calling: bool | None = None,
        max_cost_per_1k: float | None = None,
    ) -> list[str]:
        """
        Search for models matching criteria.
        """
        ...


@runtime_checkable
class RoutingMetricsPort(Protocol):
    """
    Port for tracking routing performance metrics.
    """

    def record_decision(
        self,
        model: str,
        task_type: str,
        quality_score: float,
        latency: float,
        cost: float,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Record a routing decision and its outcomes.
        """
        ...

    def get_performance_history(
        self, task_type: str | None = None, limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Get historical performance data.
        """
        ...

    def get_statistics(self) -> dict[str, Any]:
        """
        Get overall routing statistics.
        """
        ...


# Protocol Optimization Ports (Phase 3.4)


@runtime_checkable
class BatchingStrategyPort(Protocol):
    """
    Port for request batching strategies.
    """

    async def add_request(self, request: Any) -> None:
        """
        Add a request to the batch queue.
        """
        ...

    async def get_next_batch(self) -> list[Any]:
        """
        Get the next batch of requests to process.
        """
        ...

    async def process_batch(self, batch: list[Any], processor: Any) -> list[Any]:
        """
        Process a batch of requests.
        """
        ...

    def get_metrics(self) -> list[Any]:
        """
        Get batching metrics.
        """
        ...


@runtime_checkable
class CompressionPort(Protocol):
    """
    Port for payload compression strategies.
    """

    def compress_payload(self, payload: dict[str, Any]) -> bytes:
        """
        Compress a request payload.
        """
        ...

    def decompress_payload(self, compressed: bytes) -> dict[str, Any]:
        """
        Decompress a response payload.
        """
        ...

    def get_stats(self) -> dict[str, Any]:
        """
        Get compression statistics.
        """
        ...


@runtime_checkable
class ConnectionPoolPort(Protocol):
    """
    Port for connection pooling strategies.
    """

    async def acquire(self) -> Any:
        """
        Acquire a connection from the pool.
        """
        ...

    async def release(self, conn: Any) -> None:
        """
        Release a connection back to the pool.
        """
        ...

    def get_stats(self) -> dict[str, Any]:
        """
        Get connection pool statistics.
        """
        ...


@runtime_checkable
class ProtocolPort(Protocol):
    """
    Port for protocol implementations (HTTP/2, WebSocket, gRPC).
    """

    async def send_request(
        self,
        payload: dict[str, Any],
        priority: int = 1,
        callback: Any | None = None,
    ) -> dict[str, Any]:
        """
        Send a request through the protocol.
        """
        ...

    def get_stats(self) -> dict[str, Any]:
        """
        Get protocol statistics.
        """
        ...
