"""Advanced Agent Task Management System.

This module provides enterprise-grade agent task lifecycle management with:
- Redis integration for persistence
- Streaming protocol support
- Smart contract validation
- FastMCP integration
- Health monitoring
- Event sourcing
- Task queueing with backpressure

The system is modularized for maintainability (<500 lines per file).
"""

from .core import AgentTaskManager
from .metrics import record_task_metric
from .models import AgentTaskConfig, TaskExecutionContext

__all__ = [
    "AgentTaskConfig",
    "AgentTaskManager",
    "TaskExecutionContext",
    "record_task_metric",
]

__version__ = "1.0.0"
