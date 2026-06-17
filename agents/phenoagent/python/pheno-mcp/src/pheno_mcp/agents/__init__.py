"""Multi-Agent Orchestration for MCP.

This module provides framework-agnostic orchestration for multi-agent workflows
with support for CrewAI, LangGraph, AutoGen, and custom implementations.

Quick Start:
    ```python
    from pheno.mcp.agents import (
        Orchestrator,
        WorkflowPattern,
        AgentPoolConfig,
    )

    # Create orchestrator with CrewAI
    orchestrator = Orchestrator(framework="crewai")

    # Create agents
    agent_id = await orchestrator.create_agent(
        name="researcher",
        role="Research Analyst",
        goal="Find and analyze information",
        backstory="Expert with 10 years experience",
        tools=["web_search", "analyze"]
    )

    # Create workflow
    workflow_id = orchestrator.create_workflow(
        pattern=WorkflowPattern.SEQUENTIAL,
        tasks=[task1, task2, task3]
    )

    # Execute
    result = await orchestrator.execute_workflow(workflow_id)
    ```
"""

from .orchestration_base import (
    AgentFramework,
    AgentPoolConfig,
    AgentStatus,
    DependencyConfig,
    FrameworkAdapterPort,
    FrameworkConfig,
    Orchestrator,
    TaskResult,
    TaskStatus,
    WorkflowConfig,
    WorkflowPattern,
    WorkflowResult,
)
from .orchestration_state import AgentPool, AgentState
from .orchestration_tasks import DependencyResolver, TaskExecutionEngine
from .port_adapter import OrchestratorPortAdapter

__all__ = [
    "AgentFramework",
    "AgentPool",
    "AgentPoolConfig",
    "AgentState",
    "AgentStatus",
    "DependencyConfig",
    "DependencyResolver",
    "FrameworkAdapterPort",
    "FrameworkConfig",
    "Orchestrator",
    "OrchestratorPortAdapter",
    "TaskResult",
    "TaskStatus",
    "WorkflowConfig",
    "WorkflowPattern",
    "WorkflowResult",
]
