"""Generic Multi-Agent Orchestration Framework.

This module provides a framework-agnostic orchestration layer for managing
multi-agent workflows with support for CrewAI, LangGraph, AutoGen, and custom
implementations.

Key Features:
- Multi-framework support (CrewAI, LangGraph, AutoGen, Custom)
- Workflow patterns (sequential, parallel, hierarchical, conditional)
- Agent pool management with resource allocation
- Task dependency resolution and execution planning
- Result aggregation and workflow state management
- Async/await throughout for performance
- 100% type hints with generics

Example:
    ```python
    from pheno.mcp.agents.orchestration import (
        Orchestrator,
        WorkflowPattern,
        AgentPoolConfig
    )

    # Create orchestrator
    orchestrator = Orchestrator(framework="crewai")

    # Define agents
    agent1 = await orchestrator.create_agent(
        name="researcher",
        role="Research Analyst",
        goal="Find and analyze information"
    )

    # Define workflow
    workflow = orchestrator.create_workflow(
        pattern=WorkflowPattern.SEQUENTIAL,
        tasks=[task1, task2, task3]
    )

    # Execute
    result = await orchestrator.execute_workflow(workflow)
    ```
"""

from __future__ import annotations

import asyncio
import logging
from abc import abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Generic, Protocol, TypeVar, runtime_checkable
from uuid import uuid4

from ..ports import AgentConfig, TaskConfig

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    from .orchestration_tasks import DependencyResolver, TaskExecutionEngine

from .orchestration_state import AgentPool

logger = logging.getLogger(__name__)

T = TypeVar("T")
AgentT = TypeVar("AgentT")
TaskT = TypeVar("TaskT")
ResultT = TypeVar("ResultT")


class WorkflowPattern(StrEnum):
    """Supported workflow execution patterns."""

    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    HIERARCHICAL = "hierarchical"
    CONDITIONAL = "conditional"
    CUSTOM = "custom"


class AgentFramework(StrEnum):
    """Supported agent orchestration frameworks."""

    CREWAI = "crewai"
    LANGGRAPH = "langgraph"
    AUTOGEN = "autogen"
    CUSTOM = "custom"


class AgentStatus(StrEnum):
    """Agent status."""

    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"


class TaskStatus(StrEnum):
    """Task execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


@dataclass
class TaskResult:
    """Result from a single task execution."""

    task_id: str
    status: TaskStatus
    output: Any | None = None
    error: str | None = None
    agent_id: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        """Check if task completed successfully."""
        return self.status == TaskStatus.COMPLETED


@dataclass
class WorkflowResult:
    """Result from workflow execution."""

    workflow_id: str
    status: str
    pattern: WorkflowPattern
    task_results: dict[str, TaskResult] = field(default_factory=dict)
    output: Any | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    total_duration_ms: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        """Check if all tasks completed successfully."""
        return self.status == "success" and all(
            r.success for r in self.task_results.values()
        )

    @property
    def failed_tasks(self) -> list[str]:
        """Get list of failed task IDs."""
        return [
            task_id
            for task_id, result in self.task_results.items()
            if result.status == TaskStatus.FAILED
        ]


@dataclass
class FrameworkConfig:
    """Configuration for a specific framework."""

    framework: AgentFramework
    version: str | None = None
    config: dict[str, Any] = field(default_factory=dict)
    tool_registry: dict[str, Any] | None = None
    allow_delegation: bool = True
    verbose: bool = False
    max_iterations: int = 10
    timeout_seconds: float = 300.0


@dataclass
class AgentPoolConfig:
    """Configuration for agent pool management."""

    max_agents: int = 10
    max_concurrent_tasks: int = 5
    idle_timeout_seconds: float = 300.0
    health_check_interval_seconds: float = 60.0
    auto_scale: bool = False
    min_agents: int = 1


@dataclass
class WorkflowConfig:
    """Configuration for workflow execution."""

    pattern: WorkflowPattern
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    timeout_seconds: float | None = None
    continue_on_error: bool = False
    collect_metrics: bool = True


@dataclass
class DependencyConfig:
    """Task dependency configuration."""

    task_id: str
    depends_on: list[str] = field(default_factory=list)
    condition: Callable[[dict[str, Any]], bool] | None = None
    required_outputs: list[str] = field(default_factory=list)


@runtime_checkable
class FrameworkAdapterPort(Protocol[AgentT, TaskT, ResultT]):
    """Protocol for framework-specific adapters."""

    @abstractmethod
    async def create_agent(self, config: AgentConfig) -> AgentT: ...

    @abstractmethod
    async def create_task(self, config: TaskConfig, agent: AgentT) -> TaskT: ...

    @abstractmethod
    async def execute_task(self, task: TaskT, context: dict[str, Any]) -> ResultT: ...

    @abstractmethod
    async def execute_workflow(
        self,
        agents: list[AgentT],
        tasks: list[TaskT],
        pattern: WorkflowPattern,
        config: WorkflowConfig,
    ) -> ResultT: ...

    @abstractmethod
    def get_framework_name(self) -> str: ...


class Orchestrator(Generic[AgentT, TaskT, ResultT]):
    """Main orchestrator for multi-agent workflows.

    This class provides a high-level API for managing multi-agent workflows with support
    for multiple frameworks and execution patterns.
    """

    def __init__(
        self,
        framework: AgentFramework | str = AgentFramework.CUSTOM,
        framework_config: FrameworkConfig | None = None,
        pool_config: AgentPoolConfig | None = None,
    ):
        """Initialize orchestrator.

        Args:
            framework: Framework to use (crewai, langgraph, autogen, custom)
            framework_config: Framework-specific configuration
            pool_config: Agent pool configuration
        """
        from .orchestration_tasks import DependencyResolver, TaskExecutionEngine

        self.framework = (
            AgentFramework(framework) if isinstance(framework, str) else framework
        )
        self.framework_config = framework_config or FrameworkConfig(
            framework=self.framework
        )
        self.pool_config = pool_config or AgentPoolConfig()

        self.agent_pool = AgentPool(self.pool_config)
        self.dependency_resolver = DependencyResolver()
        self.adapter: FrameworkAdapterPort | None = None
        self._engine: TaskExecutionEngine

        self.workflows: dict[str, WorkflowResult] = {}
        self.tasks: dict[str, TaskConfig] = {}

        logger.info(f"Initializing Orchestrator with framework: {self.framework.value}")
        self._init_adapter()

        self._engine = TaskExecutionEngine(
            self.adapter,
            self.agent_pool,
            self.dependency_resolver,
            TaskResult,
            TaskStatus,
        )

    def _init_adapter(self) -> None:
        """Initialize framework-specific adapter."""
        try:
            if self.framework == AgentFramework.CREWAI:
                from .adapters.crewai_adapter import CrewAIAdapter

                self.adapter = CrewAIAdapter(self.framework_config)
                logger.info("CrewAI adapter initialized successfully")
            elif self.framework == AgentFramework.LANGGRAPH:
                from .adapters.langgraph_adapter import LangGraphAdapter

                self.adapter = LangGraphAdapter(self.framework_config)
                logger.info("LangGraph adapter initialized successfully")
            elif self.framework == AgentFramework.AUTOGEN:
                from .adapters.autogen_adapter import AutoGenAdapter

                self.adapter = AutoGenAdapter(self.framework_config)
                logger.info("AutoGen adapter initialized successfully")
            else:
                logger.info(
                    "Custom framework selected - adapter must be set via set_adapter()"
                )
        except ImportError as e:
            logger.exception(
                f"Failed to initialize {self.framework.value} adapter: {e}"
            )
            raise

    def set_adapter(self, adapter: FrameworkAdapterPort) -> None:
        """Set a custom framework adapter.

        Args:
            adapter: Framework adapter implementation
        """
        self.adapter = adapter

    async def create_agent(
        self,
        name: str,
        role: str,
        goal: str,
        backstory: str | None = None,
        tools: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Create an agent and add to pool."""
        if not self.adapter:
            raise RuntimeError(
                "No adapter initialized. Set framework or custom adapter."
            )

        config = AgentConfig(
            name=name,
            role=role,
            goal=goal,
            backstory=backstory,
            tools=tools,
            metadata=metadata,
        )

        agent_instance = await self.adapter.create_agent(config)
        agent_id = str(uuid4())

        await self.agent_pool.add_agent(agent_id, agent_instance, config)

        logger.info(f"Created agent '{name}' with role '{role}' (ID: {agent_id})")
        return agent_id

    def create_workflow(
        self,
        pattern: WorkflowPattern | str,
        tasks: list[TaskConfig],
        dependencies: list[DependencyConfig] | None = None,
        config: WorkflowConfig | None = None,
    ) -> str:
        """Create a workflow."""
        pattern_enum = WorkflowPattern(pattern) if isinstance(pattern, str) else pattern
        workflow_config = config or WorkflowConfig(pattern=pattern_enum)

        workflow_id = str(uuid4())

        for task in tasks:
            task_id = str(uuid4())
            task.metadata = task.metadata or {}
            task.metadata["task_id"] = task_id
            task.metadata["workflow_id"] = workflow_id
            self.tasks[task_id] = task

        if dependencies:
            for dep in dependencies:
                self.dependency_resolver.add_dependency(dep)

        self.workflows[workflow_id] = WorkflowResult(
            workflow_id=workflow_id,
            status="created",
            pattern=pattern_enum,
            started_at=None,
            metadata={"config": workflow_config},
        )

        logger.info(
            f"Created {pattern_enum.value} workflow {workflow_id} with {len(tasks)} tasks"
        )
        return workflow_id

    async def execute_workflow(
        self,
        workflow_id: str,
        inputs: dict[str, Any] | None = None,
    ) -> WorkflowResult:
        """Execute a workflow."""
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} not found")

        if not self.adapter:
            raise RuntimeError("No adapter initialized")

        workflow = self.workflows[workflow_id]
        workflow.status = "running"
        workflow.started_at = datetime.utcnow()

        workflow_tasks = [
            task
            for task in self.tasks.values()
            if task.metadata and task.metadata.get("workflow_id") == workflow_id
        ]

        logger.info(
            f"Starting workflow {workflow_id} ({workflow.pattern.value}) with {len(workflow_tasks)} tasks",
        )

        try:
            if workflow.pattern == WorkflowPattern.SEQUENTIAL:
                result = await self._engine.execute_sequential(
                    workflow, workflow_tasks, inputs or {}
                )
            elif workflow.pattern == WorkflowPattern.PARALLEL:
                result = await self._engine.execute_parallel(
                    workflow, workflow_tasks, inputs or {}
                )
            elif workflow.pattern == WorkflowPattern.HIERARCHICAL:
                result = await self._engine.execute_hierarchical(
                    workflow, workflow_tasks, inputs or {}
                )
            elif workflow.pattern == WorkflowPattern.CONDITIONAL:
                result = await self._engine.execute_conditional(
                    workflow, workflow_tasks, inputs or {}
                )
            else:
                raise ValueError(f"Unsupported pattern: {workflow.pattern}")

            workflow.completed_at = datetime.utcnow()
            if workflow.started_at:
                workflow.total_duration_ms = (
                    workflow.completed_at - workflow.started_at
                ).total_seconds() * 1000

            logger.info(
                f"Workflow {workflow_id} completed with status '{workflow.status}' "
                f"in {workflow.total_duration_ms:.2f}ms. "
                f"Successful tasks: {sum(1 for r in workflow.task_results.values() if r.success)}/{len(workflow.task_results)}",
            )

            return result

        except Exception as e:
            workflow.status = "error"
            workflow.error = str(e)
            workflow.completed_at = datetime.utcnow()
            logger.error(f"Workflow {workflow_id} failed: {e}", exc_info=True)
            raise

    async def get_workflow_status(self, workflow_id: str) -> WorkflowResult | None:
        """Get workflow status."""
        return self.workflows.get(workflow_id)

    async def get_pool_stats(self) -> dict[str, Any]:
        """Get agent pool statistics."""
        return await self.agent_pool.get_pool_stats()

    async def shutdown(self) -> None:
        """Shutdown orchestrator and clean up resources."""
        await self.agent_pool.stop_health_checks()
