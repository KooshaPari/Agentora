"""
Expose agent factories for clink.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import AgentOutput, BaseCLIAgent, CLIAgentError
from .claude import ClaudeAgent
from .codex import CodexAgent
from .gemini import GeminiAgent

if TYPE_CHECKING:
    from clink.models import ResolvedCLIClient

__all__ = [
    "AgentOutput",
    "BaseCLIAgent",
    "CLIAgentError",
    "create_agent",
]


def create_agent(client: ResolvedCLIClient) -> BaseCLIAgent:
    name = (client.runner or client.name).lower()
    if name == "gemini":
        return GeminiAgent(client)
    if name == "codex":
        return CodexAgent(client)
    if name == "claude":
        return ClaudeAgent(client)
    raise ValueError(f"Unsupported CLI runner '{client.runner}' for '{client.name}'")
