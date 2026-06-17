"""MCP Domain Types.

Core domain types for Model Context Protocol. These are pure domain objects with no
framework dependencies.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable


class ToolStatus(Enum):
    """
    Status of a tool execution.
    """

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SessionStatus(Enum):
    """
    Status of an MCP session.
    """

    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


@dataclass
class McpServer:
    """MCP server configuration.

    Represents an MCP server that can be connected to.

    Example:
        >>> server = McpServer(
        ...     url="http://localhost:8000",
        ...     name="local-mcp",
        ...     auth_token="secret"
        ... )
    """

    url: str
    name: str | None = None
    auth_token: str | None = None
    timeout: int = 30
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.name is None:
            self.name = self.url


@dataclass
class McpSession:
    """MCP session.

    Represents an active connection to an MCP server.

    Example:
        >>> session = McpSession(
        ...     session_id="session-123",
        ...     server=server,
        ...     status=SessionStatus.CONNECTED
        ... )
    """

    session_id: str
    server: McpServer
    status: SessionStatus = SessionStatus.CONNECTING
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.session_id:
            self.session_id = str(uuid.uuid4())

    def is_active(self) -> bool:
        """
        Check if session is active.
        """
        return self.status == SessionStatus.CONNECTED

    def update_activity(self) -> None:
        """
        Update last activity timestamp.
        """
        self.last_activity = datetime.now()


@dataclass
class McpTool:
    """MCP tool definition.

    Represents a tool that can be executed via MCP.

    Example:
        >>> tool = McpTool(
        ...     name="search",
        ...     description="Search documentation",
        ...     parameters={"query": {"type": "string", "required": True}}
        ... )
    """

    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)
    category: str | None = None
    tags: list[str] = field(default_factory=list)
    version: str = "1.0.0"
    metadata: dict[str, Any] = field(default_factory=dict)
    handler: Callable | None = None

    def __hash__(self):
        """
        Make tool hashable for use in sets/dicts.
        """
        return hash(self.name)

    def __eq__(self, other):
        """
        Equality based on name.
        """
        return isinstance(other, McpTool) and self.name == other.name


@dataclass
class ToolExecution:
    """Tool execution context.

    Tracks the execution of a tool with parameters and results.

    Example:
        >>> execution = ToolExecution(
        ...     tool=tool,
        ...     parameters={"query": "hello"},
        ...     session=session
        ... )
    """

    execution_id: str
    tool: McpTool
    parameters: dict[str, Any]
    session: McpSession | None = None
    status: ToolStatus = ToolStatus.PENDING
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: ToolResult | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.execution_id:
            self.execution_id = str(uuid.uuid4())

    def start(self) -> None:
        """
        Mark execution as started.
        """
        self.status = ToolStatus.RUNNING
        self.started_at = datetime.now()

    def complete(self, result: ToolResult) -> None:
        """
        Mark execution as completed.
        """
        self.status = ToolStatus.SUCCESS
        self.completed_at = datetime.now()
        self.result = result

    def fail(self, error: str) -> None:
        """
        Mark execution as failed.
        """
        self.status = ToolStatus.FAILED
        self.completed_at = datetime.now()
        self.error = error

    def duration_seconds(self) -> float | None:
        """
        Get execution duration in seconds.
        """
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


@dataclass
class ToolResult:
    """Tool execution result.

    Contains the output and metadata from a tool execution.

    Example:
        >>> result = ToolResult(
        ...     output={"results": [...]},
        ...     success=True,
        ...     metadata={"execution_time": 1.23}
        ... )
    """

    output: Any
    success: bool = True
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_success(self) -> bool:
        """
        Check if result is successful.
        """
        return self.success and self.error is None


@dataclass
class Resource:
    """MCP resource.

    Represents a resource accessible via MCP URI.

    Example:
        >>> resource = Resource(
        ...     uri="db://users/123",
        ...     data={"name": "Alice", "email": "alice@example.com"},
        ...     resource_type="user"
        ... )
    """

    uri: str
    data: Any
    resource_type: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def update(self, data: Any) -> None:
        """
        Update resource data.
        """
        self.data = data
        self.updated_at = datetime.now()


@dataclass
class WorkflowExecution:
    """Workflow execution tracking.

    Tracks the execution of a multi-step workflow.

    Example:
        >>> workflow = WorkflowExecution(
        ...     workflow_id="data-pipeline",
        ...     steps=["extract", "transform", "load"]
        ... )
    """

    workflow_id: str
    steps: list[str]
    current_step: int = 0
    status: ToolStatus = ToolStatus.PENDING
    started_at: datetime | None = None
    completed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    results: dict[str, Any] = field(default_factory=dict)

    def start(self) -> None:
        """
        Start workflow execution.
        """
        self.status = ToolStatus.RUNNING
        self.started_at = datetime.now()

    def complete_step(self, step: str, result: Any) -> None:
        """
        Complete a workflow step.
        """
        self.results[step] = result
        self.current_step += 1

    def complete(self) -> None:
        """
        Complete workflow execution.
        """
        self.status = ToolStatus.SUCCESS
        self.completed_at = datetime.now()

    def fail(self, error: str) -> None:
        """
        Fail workflow execution.
        """
        self.status = ToolStatus.FAILED
        self.completed_at = datetime.now()
        self.metadata["error"] = error


__all__ = [
    "McpServer",
    "McpSession",
    "McpTool",
    "Resource",
    "SessionStatus",
    "ToolExecution",
    "ToolResult",
    "ToolStatus",
    "WorkflowExecution",
]
