"""Task Management Models.

Data models for agent task management system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class TaskStatus(Enum):
    """
    Task execution status.
    """

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class AgentType(Enum):
    """
    Types of agents in the system.
    """

    CLAUDE = "claude"
    AIDER = "aider"
    FASTMCP = "fastmcp"
    CUSTOM = "custom"


@dataclass
class AgentTaskConfig:
    """
    Configuration for agent task execution.
    """

    # Task identification
    task_id: str
    agent_type: AgentType

    # Execution settings
    working_directory: str
    task_description: str
    model: str | None = None

    # Resource limits
    timeout_seconds: int = 3600
    max_retries: int = 3

    # Port management
    port: int | None = None

    # Workflow integration
    workflow: str | None = None
    workflow_params: dict[str, Any] = field(default_factory=dict)

    # Tools and permissions
    allowed_tools: list[str] = field(default_factory=list)
    disallowed_tools: list[str] = field(default_factory=list)

    # Environment
    env_vars: dict[str, str] = field(default_factory=dict)

    # Streaming
    enable_streaming: bool = True

    # Smart contract validation
    validate_contract: bool = False
    contract_criteria: dict[str, Any] | None = None


@dataclass
class TaskExecutionContext:
    """
    Context for task execution with runtime information.
    """

    config: AgentTaskConfig

    # Status tracking
    status: TaskStatus = TaskStatus.PENDING
    started_at: datetime | None = None
    completed_at: datetime | None = None

    # Results
    output: str = ""
    error: str | None = None
    exit_code: int | None = None

    # Performance metrics
    execution_time_seconds: float | None = None

    # Enhanced data (from FastMCP, etc.)
    enhanced_data: dict[str, Any] = field(default_factory=dict)

    # Streaming messages
    messages: list[dict[str, Any]] = field(default_factory=list)

    # Process management
    process_id: int | None = None

    # Retry tracking
    retry_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary for storage/serialization.
        """
        return {
            "task_id": self.config.task_id,
            "agent_type": self.config.agent_type.value,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "output": self.output[:1000] if self.output else "",  # Truncate for storage
            "error": self.error,
            "exit_code": self.exit_code,
            "execution_time_seconds": self.execution_time_seconds,
            "enhanced_data": self.enhanced_data,
            "retry_count": self.retry_count,
        }


@dataclass
class AgentTaskRequest:
    """
    Request to create and execute an agent task.
    """

    agent_type: AgentType
    task_description: str
    working_directory: str
    model: str | None = None
    timeout_seconds: int = 3600
    workflow: str | None = None
    workflow_params: dict[str, Any] = field(default_factory=dict)
    allowed_tools: list[str] = field(default_factory=list)
    disallowed_tools: list[str] = field(default_factory=list)
    env_vars: dict[str, str] = field(default_factory=dict)
    enable_streaming: bool = True


@dataclass
class AgentTaskResult:
    """
    Result of agent task execution.
    """

    task_id: str
    status: TaskStatus
    output: str
    error: str | None = None
    exit_code: int | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    execution_time_seconds: float | None = None
    enhanced_data: dict[str, Any] = field(default_factory=dict)
    messages: list[dict[str, Any]] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """
        Check if task completed successfully.
        """
        return self.status == TaskStatus.COMPLETED and self.exit_code == 0

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary.
        """
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "output": self.output,
            "error": self.error,
            "exit_code": self.exit_code,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "execution_time_seconds": self.execution_time_seconds,
            "enhanced_data": self.enhanced_data,
            "success": self.success,
        }


@dataclass
class PortAllocation:
    """
    Port allocation information.
    """

    port: int
    agent_id: str | None
    allocated_at: datetime
    task_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary.
        """
        return {
            "port": self.port,
            "agent_id": self.agent_id,
            "allocated_at": self.allocated_at.isoformat(),
            "task_id": self.task_id,
        }
