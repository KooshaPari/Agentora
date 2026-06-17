"""Orchestrator Core Types.

Common types and enums used across orchestration modules.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class TaskComplexity(Enum):
    """
    Task complexity levels for routing decisions.
    """

    SIMPLE = "simple"  # Basic queries, simple fixes (< 100 LOC)
    MEDIUM = "medium"  # Code analysis, moderate fixes (100-500 LOC)
    COMPLEX = "complex"  # Full implementations, complex debugging (> 500 LOC)


class TaskType(Enum):
    """
    Types of development tasks.
    """

    ANALYSIS = "analysis"  # Code analysis, understanding
    BUG_FIX = "bug_fix"  # Bug fixes, error resolution
    FEATURE = "feature"  # New feature implementation
    REVIEW = "review"  # Code review, PR analysis
    REFACTOR = "refactor"  # Code refactoring, optimization
    TEST = "test"  # Test writing, coverage improvement
    DOCUMENTATION = "documentation"  # Documentation updates


class ExecutionStrategy(Enum):
    """
    Strategy for task execution.
    """

    SEQUENTIAL = "sequential"  # Execute tasks one by one
    PARALLEL = "parallel"  # Execute independent tasks in parallel
    HIERARCHICAL = "hierarchical"  # Parent-child task hierarchy
    SWARM = "swarm"  # Distributed swarm execution


class AgentType(Enum):
    """
    Types of agents in the system.
    """

    ORCHESTRATOR = "orchestrator"  # Main orchestration agent
    EXECUTOR = "executor"  # Task execution agent
    ANALYZER = "analyzer"  # Analysis specialist
    REVIEWER = "reviewer"  # Code review specialist
    OPTIMIZER = "optimizer"  # Cost/performance optimizer


@dataclass
class TaskRequest:
    """
    Represents a development task request.
    """

    task_id: str
    task_type: TaskType
    description: str
    repository_url: str | None = None
    context: dict[str, Any] = field(default_factory=dict)
    tenant_id: str | None = None
    priority: int = 1  # 1-5, 5 being highest
    estimated_complexity: TaskComplexity | None = None
    deadline: datetime | None = None
    strategy: ExecutionStrategy = ExecutionStrategy.SEQUENTIAL
    parent_task_id: str | None = None


@dataclass
class TaskResult:
    """
    Result of a completed task.
    """

    task_id: str
    success: bool
    result: Any = None
    error_message: str | None = None
    provider_used: str | None = None
    execution_time_seconds: float = 0.0
    cost_usd: float = 0.0
    tokens_used: int = 0
    cached: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentCapability:
    """
    Capabilities of an agent.
    """

    agent_type: AgentType
    supported_task_types: list[TaskType]
    max_complexity: TaskComplexity
    cost_per_request: float = 0.0
    average_execution_time: float = 0.0
    success_rate: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)
