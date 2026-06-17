"""
Quality evaluation helpers for LLM outputs.
"""

from .hallucination_detector import (
    BehaviourFlag,
    BehaviourSignals,
    detect_behavioural_flags,
)

__all__ = [
    "BehaviourFlag",
    "BehaviourSignals",
    "detect_behavioural_flags",
]
