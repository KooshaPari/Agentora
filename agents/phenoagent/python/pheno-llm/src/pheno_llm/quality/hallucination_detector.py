"""
Heuristics for detecting hallucination and thrash patterns in LLM outputs.

The detectors are intentionally conservative – they focus on symptoms that
can be learned from telemetry (confirmation loops, repetitive empty work,
gibberish bursts, malformed tool syntax).  This keeps the signals useful for
scoring providers without requiring message-specific annotations.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, MutableMapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum

CONFIRMATION_PATTERNS = (
    "would you like me",
    "should i proceed",
    "shall i continue",
    "do you want me to",
)

POSITIVE_ACKS = (
    "yes",
    "yeah",
    "please do",
    "go ahead",
    "proceed",
    "carry on",
    "sure",
)

CHECK_PATTERNS = (
    "let me check",
    "checking",
    "i will check",
)

PROGRESS_PATTERNS = (
    "i checked",
    "i have checked",
    "it's done",
    "all done",
    "completed",
    "finished",
)

GIBBERISH_REGEX = re.compile(r"[A-Za-z0-9\s,.!?()\[\]{}:;'\"]")
TOOL_TAG_REGEX = re.compile(r"<[A-Za-z0-9_.:-]+>")


class BehaviourFlag(StrEnum):
    """Flag identifiers understood by the router."""

    CONFIRMATION_LOOP = "confirmation_loop"
    REPETITIVE_STALL = "repetitive_stall"
    STALLED_PROGRESS = "stalled_progress"
    RANDOM_HALLUCINATION = "random_hallucination"
    TOOL_SYNTAX_ERROR = "tool_syntax_error"


@dataclass(slots=True)
class BehaviourSignals:
    """Structured detection result."""

    flags: MutableMapping[BehaviourFlag, float] = field(default_factory=dict)

    @property
    def severity(self) -> float:
        """Return overall severity as the maximum flag score."""

        return max(self.flags.values(), default=0.0)

    def as_dict(self) -> Mapping[str, float]:
        """Serialise flags for persistence."""

        return {flag.value: score for flag, score in self.flags.items()}

    def add(self, flag: BehaviourFlag, score: float) -> None:
        """Accumulate the strongest signal for a flag."""

        current = self.flags.get(flag, 0.0)
        self.flags[flag] = max(current, 0.0, min(1.0, score))


def detect_behavioural_flags(
    conversation: Sequence[object],
) -> BehaviourSignals:
    """
    Analyse a conversation for thrash / hallucination patterns.

    Args:
        conversation: Sequence of chat messages.  Each item may be a plain
            string, a mapping with ``role``/``content`` keys or a Pydantic-like
            object exposing ``role`` and ``content`` attributes.
    """

    signals = BehaviourSignals()
    normalised = _normalise_messages(conversation)

    if not normalised:
        return signals

    _detect_confirmation_loop(normalised, signals)
    _detect_repetitive_stall(normalised, signals)
    _detect_stalled_progress(normalised, signals)
    _detect_random_hallucination(normalised, signals)
    _detect_tool_syntax(normalised, signals)

    return signals


def _normalise_messages(conversation: Sequence[object]) -> list[tuple[str, str]]:
    """Convert heterogeneous message structures to (role, content) tuples."""

    normalised: list[tuple[str, str]] = []
    for message in conversation:
        role = "assistant"
        content: str | None = None

        if isinstance(message, str):
            content = message
        elif isinstance(message, Mapping):
            role = str(message.get("role") or role).lower()
            content_val = message.get("content")
            content = _flatten_content(content_val)
        else:
            if hasattr(message, "role"):
                role = str(message.role).lower()
            if hasattr(message, "content"):
                content = _flatten_content(message.content)

        if content is None:
            continue

        normalised.append((role, content.strip()))

    return normalised


def _flatten_content(content: object) -> str | None:
    """Flatten content which may be str, list, or dict into text."""

    if content is None:
        return None
    if isinstance(content, str):
        return content
    if isinstance(content, (list, tuple)):
        return "\n".join(_flatten_content(item) or "" for item in content if item) or None
    if isinstance(content, Mapping):
        return "\n".join(f"{key}: {_flatten_content(value) or ''}" for key, value in content.items())
    return str(content)


def _detect_confirmation_loop(
    messages: Sequence[tuple[str, str]],
    signals: BehaviourSignals,
) -> None:
    """Detect repeated confirmation requests after explicit approval."""

    confirmation_indices = [
        idx
        for idx, (role, text) in enumerate(messages)
        if role == "assistant" and any(pattern in text.lower() for pattern in CONFIRMATION_PATTERNS)
    ]

    if len(confirmation_indices) < 2:
        return

    approvals = {
        idx
        for idx, (role, text) in enumerate(messages)
        if role == "user" and any(ack in text.lower() for ack in POSITIVE_ACKS)
    }

    for confirm_idx in confirmation_indices[1:]:
        if any(approval_idx > confirmation_indices[0] and approval_idx < confirm_idx for approval_idx in approvals):
            # Re-asking after approval – treat severity based on how many loops occurred
            loops = sum(
                1
                for idx in confirmation_indices
                if idx > confirmation_indices[0]
            )
            signals.add(BehaviourFlag.CONFIRMATION_LOOP, min(1.0, 0.4 + loops * 0.15))
            break


def _detect_repetitive_stall(
    messages: Sequence[tuple[str, str]],
    signals: BehaviourSignals,
) -> None:
    """Detect repeated 'Let me check' style stall messages."""

    streak = 0
    max_streak = 0
    for role, text in messages:
        if role != "assistant":
            streak = 0
            continue
        lower = text.lower()
        if any(pattern in lower for pattern in CHECK_PATTERNS):
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0

    if max_streak >= 3:
        severity = min(1.0, 0.35 + 0.15 * (max_streak - 3))
        signals.add(BehaviourFlag.REPETITIVE_STALL, severity)


def _detect_stalled_progress(
    messages: Sequence[tuple[str, str]],
    signals: BehaviourSignals,
) -> None:
    """
    Detect when the assistant claims progress without evidence (Type C).

    Simple heuristic: if an assistant message starts with "let me check" and the
    very next assistant message (ignoring user responses) is a short confirmation
    such as "I checked X, all done" without substantive content.
    """

    pending_check: str | None = None
    for role, text in messages:
        if role != "assistant":
            continue
        lower = text.lower()
        if any(pattern in lower for pattern in CHECK_PATTERNS):
            pending_check = lower
            continue

        if pending_check and any(marker in lower for marker in PROGRESS_PATTERNS):
            if len(text.strip()) < 40:
                signals.add(BehaviourFlag.STALLED_PROGRESS, 0.5)
            pending_check = None


def _detect_random_hallucination(
    messages: Sequence[tuple[str, str]],
    signals: BehaviourSignals,
) -> None:
    """Flag bursts of gibberish or random unicode."""

    for role, text in messages:
        if role != "assistant":
            continue

        cleaned = "".join(ch for ch in text if GIBBERISH_REGEX.match(ch))
        if not text:
            continue

        junk_ratio = 1.0 - (len(cleaned) / len(text))
        if len(text) > 40 and junk_ratio > 0.35:
            # Scale severity by junk ratio
            signals.add(BehaviourFlag.RANDOM_HALLUCINATION, min(1.0, junk_ratio + 0.1))
            break


def _detect_tool_syntax(
    messages: Sequence[tuple[str, str]],
    signals: BehaviourSignals,
) -> None:
    """Identify malformed tool tags such as `<x.ai:functioncall>`."""

    for role, text in messages:
        if role != "assistant":
            continue

        if TOOL_TAG_REGEX.search(text):
            if "</" not in text and "<tool_call>" not in text.lower():
                signals.add(BehaviourFlag.TOOL_SYNTAX_ERROR, 0.6)
                break
