"""
MCP Ports - Abstract interfaces for MCP tool and agent operations.

This module defines ports for pluggable tool registration, validation,
and agent orchestration across different frameworks.
"""

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable


class ToolFramework(StrEnum):
    """
    Supported tool frameworks.
    """

    FASTMCP = "fastmcp"
    LANGCHAIN = "langchain"
    ANTHROPIC = "anthropic"
    CUSTOM = "custom"


class AgentFramework(StrEnum):
    """
    Supported agent orchestration frameworks.
    """

    CREWAI = "crewai"
    LANGGRAPH = "langgraph"
    AUTOGEN = "autogen"
    CUSTOM = "custom"


@dataclass
class ToolSchema:
    """
    Standard tool schema.
    """

    name: str
    description: str
    parameters: dict[str, Any]
    required: list[str] | None = None
    returns: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class ToolResult:
    """
    Standard tool execution result.
    """

    success: bool
    output: Any | None = None
    error: str | None = None
    duration_ms: float | None = None
    metadata: dict[str, Any] | None = None


@runtime_checkable
class ToolRegistryPort(Protocol):
    """
    Port for tool registration implementations.
    """

    def register_tool(self, name: str, func: Callable, schema: ToolSchema | None = None) -> None:
        """
        Register a tool.
        """
        ...

    def unregister_tool(self, name: str) -> bool:
        """
        Unregister a tool.
        """
        ...

    def get_tool(self, name: str) -> Callable | None:
        """
        Get a registered tool.
        """
        ...

    def list_tools(self) -> list[str]:
        """
        List all registered tools.
        """
        ...

    async def execute_tool(self, name: str, **kwargs) -> ToolResult:
        """
        Execute a tool.
        """
        ...


@runtime_checkable
class DecoratorPort(Protocol):
    """
    Port for decorator-based tool registration.
    """

    def apply_decorator(self, func: Callable, **options: Any) -> Callable:
        """
        Apply decorator to a function.
        """
        ...

    def extract_metadata(self, func: Callable) -> dict[str, Any]:
        """
        Extract metadata from decorated function.
        """
        ...


@runtime_checkable
class SchemaGeneratorPort(Protocol):
    """
    Port for schema generation from various sources.
    """

    def from_signature(self, func: Callable) -> dict[str, Any]:
        """
        Generate schema from function signature.
        """
        ...

    def from_pydantic(self, model: type) -> dict[str, Any]:
        """
        Generate schema from Pydantic model.
        """
        ...

    def from_dict(self, schema_dict: dict[str, Any]) -> dict[str, Any]:
        """
        Normalize schema from dictionary.
        """
        ...


@runtime_checkable
class ValidationPort(Protocol):
    """
    Port for input validation.
    """

    def validate(self, inputs: dict[str, Any], schema: dict[str, Any]) -> tuple[bool, str | None]:
        """Validate inputs against schema.

        Returns:
            (is_valid, error_message)
        """
        ...

    def coerce_types(self, inputs: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
        """
        Coerce input types to match schema.
        """
        ...


@dataclass
class AgentConfig:
    """
    Standard agent configuration.
    """

    name: str
    role: str
    goal: str
    backstory: str | None = None
    tools: list[str] | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class TaskConfig:
    """
    Standard task configuration.
    """

    description: str
    agent: str
    expected_output: str | None = None
    dependencies: list[str] | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class ExecutionResult:
    """
    Standard task execution result.
    """

    task_id: str
    success: bool
    output: Any | None = None
    error: str | None = None
    duration_ms: float | None = None
    metadata: dict[str, Any] | None = None


@runtime_checkable
class AgentOrchestratorPort(Protocol):
    """
    Port for agent orchestration implementations.
    """

    async def create_agent(self, config: AgentConfig) -> str:
        """
        Create an agent.
        """
        ...

    async def execute_task(self, task: TaskConfig) -> ExecutionResult:
        """
        Execute a task.
        """
        ...

    async def execute_workflow(self, tasks: list[TaskConfig]) -> list[ExecutionResult]:
        """
        Execute a workflow of tasks.
        """
        ...

    async def get_agent_status(self, agent_id: str) -> dict[str, Any]:
        """
        Get agent status.
        """
        ...
