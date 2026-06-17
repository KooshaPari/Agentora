"""LLM Optimization Utilities.

This package provides optimization utilities for LLM performance and cost:

1. Provider Selection (Existing)
   - Provider score calculation
   - Preference-based routing
   - OpenRouter integration

2. Context Folding (New)
   - Hierarchical token compression
   - 40-60% token reduction
   - Semantic preservation
"""

from .context_folding import (
    ContextFoldingConfig,
    FoldingResult,
    HierarchicalContextFolder,
    TokenizerPort,
)
from .provider_selector import (
    ProviderOption,
    ProviderPreference,
    ProviderScore,
    ProviderSelector,
    QuantizationLevel,
    build_preference_payload,
)

__all__ = [
    # Context folding
    "ContextFoldingConfig",
    "FoldingResult",
    "HierarchicalContextFolder",
    # Provider selection
    "ProviderOption",
    "ProviderPreference",
    "ProviderScore",
    "ProviderSelector",
    "QuantizationLevel",
    "TokenizerPort",
    "build_preference_payload",
]
