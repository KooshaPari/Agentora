"""
pheno.orchestrator - Multi-agent orchestration

Provides multi-agent orchestration and coordination capabilities.

Migrated from orchestrator-kit into pheno namespace.

Usage:
    from pheno.workflow.orchestration import Orchestrator, Agent, AgentStatus

    # Create orchestrator
    orchestrator = Orchestrator()

    # Register agents
    orchestrator.register(Agent(name="agent-1", capabilities=["task-a"]))
    orchestrator.register(Agent(name="agent-2", capabilities=["task-b"]))

    # Orchestrate tasks
    await orchestrator.execute(tasks)
"""

from __future__ import annotations

from .orchestrator import Agent, AgentStatus, Orchestrator

__version__ = "0.1.0"
__all__ = ["Agent", "AgentStatus", "Orchestrator"]
