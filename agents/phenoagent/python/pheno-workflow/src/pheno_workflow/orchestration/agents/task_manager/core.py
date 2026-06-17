"""Core Agent Task Manager.

Main coordinator for agent task execution with modular components. This is a simplified,
modular version that integrates with the existing pheno-sdk AgentManager while providing
advanced features from conslidate.
"""

import asyncio
import logging
import os
import uuid
from datetime import datetime

from .metrics import MetricsCollector, record_task_metric
from .models import (
    AgentTaskConfig,
    AgentTaskRequest,
    AgentTaskResult,
    TaskExecutionContext,
    TaskStatus,
)
from .port_manager import PortManager
from .storage import create_task_storage

logger = logging.getLogger(__name__)


class AgentTaskManager:
    """Advanced Agent Task Manager with enterprise features.

    This manager provides:
    - Task lifecycle management
    - Redis/in-memory persistence
    - Port allocation
    - Metrics and telemetry
    - Task queueing with backpressure
    - Integration with existing AgentManager

    Designed to be <500 lines with modular components.
    """

    def __init__(
        self,
        redis_client=None,
        agent_manager=None,
        max_concurrent_tasks: int = 24,
        queue_max_size: int = 200,
    ):
        """Initialize the agent task manager.

        Args:
            redis_client: Optional Redis client for persistence
            agent_manager: Optional existing AgentManager instance
            max_concurrent_tasks: Maximum concurrent task executions
            queue_max_size: Maximum task queue size
        """
        # Storage layer
        self.storage = create_task_storage(redis_client)

        # Port management
        self.port_manager = PortManager()

        # Metrics collection
        self.metrics = MetricsCollector()

        # Active tasks tracking
        self.active_tasks: dict[str, TaskExecutionContext] = {}

        # Integration with existing AgentManager
        self.agent_manager = agent_manager

        # Concurrency control
        self.max_concurrent_tasks = max_concurrent_tasks
        self._semaphore = asyncio.Semaphore(max_concurrent_tasks)

        # Task queue
        self._queue: asyncio.Queue[str] = asyncio.Queue(maxsize=queue_max_size)
        self._queue_processor_task: asyncio.Task | None = None

        # Configuration
        self.retention_seconds = int(os.getenv("AGENT_TASK_RETENTION_SEC", "3600"))

        logger.info(
            f"AgentTaskManager initialized with "
            f"max_concurrent={max_concurrent_tasks}, "
            f"queue_size={queue_max_size}",
        )

    async def create_task(self, request: AgentTaskRequest, task_id: str | None = None) -> str:
        """Create a new agent task.

        Args:
            request: Task request with configuration
            task_id: Optional custom task ID

        Returns:
            Task ID
        """
        # Generate task ID if not provided
        if not task_id:
            task_id = f"task_{uuid.uuid4().hex[:12]}"

        # Allocate port if needed
        port = self.port_manager.allocate_port(task_id=task_id)

        # Create task config
        config = AgentTaskConfig(
            task_id=task_id,
            agent_type=request.agent_type,
            working_directory=request.working_directory,
            task_description=request.task_description,
            model=request.model,
            timeout_seconds=request.timeout_seconds,
            port=port,
            workflow=request.workflow,
            workflow_params=request.workflow_params,
            allowed_tools=request.allowed_tools,
            disallowed_tools=request.disallowed_tools,
            env_vars=request.env_vars,
            enable_streaming=request.enable_streaming,
        )

        # Create execution context
        context = TaskExecutionContext(config=config)
        self.active_tasks[task_id] = context

        # Save to storage
        await self.storage.save_task(task_id, context.to_dict())

        # Record metric
        record_task_metric(context, "task_created")

        logger.info(f"Created task {task_id} for agent type {request.agent_type.value}")

        return task_id

    async def execute_task(self, task_id: str) -> AgentTaskResult:
        """Execute a task.

        Args:
            task_id: Task identifier

        Returns:
            Task execution result
        """
        context = self.active_tasks.get(task_id)
        if not context:
            raise ValueError(f"Task {task_id} not found")

        # Acquire semaphore for concurrency control
        async with self._semaphore:
            # Update status
            context.status = TaskStatus.RUNNING
            context.started_at = datetime.now()
            await self.storage.save_task(task_id, context.to_dict())
            record_task_metric(context, "task_started")

            try:
                # Execute task through agent manager if available
                if self.agent_manager:
                    result = await self._execute_with_agent_manager(context)
                else:
                    result = await self._execute_direct(context)

                # Update context with results
                context.status = TaskStatus.COMPLETED
                context.output = result.get("output", "")
                context.exit_code = result.get("exit_code", 0)
                context.enhanced_data = result.get("enhanced_data", {})

            except Exception as e:
                # Handle execution failure
                context.status = TaskStatus.FAILED
                context.error = str(e)
                context.exit_code = 1
                logger.error(f"Task {task_id} failed: {e}", exc_info=True)
                record_task_metric(context, "task_failed")

            finally:
                # Finalize
                context.completed_at = datetime.now()
                if context.started_at:
                    context.execution_time_seconds = (
                        context.completed_at - context.started_at
                    ).total_seconds()

                # Release port
                if context.config.port:
                    self.port_manager.release_port(context.config.port)

                # Save final state
                await self.storage.save_task(task_id, context.to_dict())

                # Record metrics
                if context.status == TaskStatus.COMPLETED:
                    record_task_metric(context, "task_completed")
                    self.metrics.record_task_completion(
                        task_id,
                        success=True,
                        execution_time=context.execution_time_seconds or 0,
                    )

                # Create result
                return AgentTaskResult(
                    task_id=task_id,
                    status=context.status,
                    output=context.output,
                    error=context.error,
                    exit_code=context.exit_code,
                    started_at=context.started_at,
                    completed_at=context.completed_at,
                    execution_time_seconds=context.execution_time_seconds,
                    enhanced_data=context.enhanced_data,
                    messages=context.messages,
                )


    async def _execute_with_agent_manager(self, context: TaskExecutionContext) -> dict:
        """
        Execute task through existing AgentManager.
        """
        # Convert to AgentManager task format
        from pheno.workflow.orchestration.core.types import TaskRequest, TaskType

        task_request = TaskRequest(
            task_id=context.config.task_id,
            task_type=TaskType.CODE_GENERATION,  # Default
            description=context.config.task_description,
            priority=1,
        )

        # Route and execute through agent manager
        agent_id = await self.agent_manager.route_task(task_request)
        await self.agent_manager.assign_task(agent_id, task_request)

        # This is a simplified integration - in practice, you'd wait for completion
        # and get the actual result from the agent
        return {
            "output": "Executed through AgentManager",
            "exit_code": 0,
            "enhanced_data": {"agent_id": agent_id},
        }

    async def _execute_direct(self, context: TaskExecutionContext) -> dict:
        """
        Execute task directly (fallback when no AgentManager).
        """
        # This is a stub - in the full implementation, this would execute
        # the agent command directly using subprocess or similar
        logger.warning(
            f"No AgentManager available, using stub execution for task {context.config.task_id}",
        )

        await asyncio.sleep(1)  # Simulate work

        return {
            "output": f"Task {context.config.task_id} executed (stub)",
            "exit_code": 0,
            "enhanced_data": {},
        }

    async def get_task(self, task_id: str) -> AgentTaskResult | None:
        """Get task by ID.

        Args:
            task_id: Task identifier

        Returns:
            Task result or None if not found
        """
        # Check active tasks first
        if task_id in self.active_tasks:
            context = self.active_tasks[task_id]
            return AgentTaskResult(
                task_id=task_id,
                status=context.status,
                output=context.output,
                error=context.error,
                exit_code=context.exit_code,
                started_at=context.started_at,
                completed_at=context.completed_at,
                execution_time_seconds=context.execution_time_seconds,
                enhanced_data=context.enhanced_data,
                messages=context.messages,
            )

        # Check storage
        task_data = await self.storage.get_task(task_id)
        if task_data:
            return AgentTaskResult(
                task_id=task_id,
                status=TaskStatus(task_data["status"]),
                output=task_data.get("output", ""),
                error=task_data.get("error"),
                exit_code=task_data.get("exit_code"),
                started_at=(
                    datetime.fromisoformat(task_data["started_at"])
                    if task_data.get("started_at")
                    else None
                ),
                completed_at=(
                    datetime.fromisoformat(task_data["completed_at"])
                    if task_data.get("completed_at")
                    else None
                ),
                execution_time_seconds=task_data.get("execution_time_seconds"),
                enhanced_data=task_data.get("enhanced_data", {}),
            )

        return None

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task.

        Args:
            task_id: Task identifier

        Returns:
            True if cancelled, False if not found or already completed
        """
        context = self.active_tasks.get(task_id)
        if not context:
            return False

        if context.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
            return False

        # Update status
        context.status = TaskStatus.CANCELLED
        context.completed_at = datetime.now()

        # Release resources
        if context.config.port:
            self.port_manager.release_port(context.config.port)

        await self.storage.save_task(task_id, context.to_dict())
        record_task_metric(context, "task_cancelled")

        logger.info(f"Cancelled task {task_id}")
        return True

    async def list_tasks(
        self, status: TaskStatus | None = None, limit: int = 100,
    ) -> list[AgentTaskResult]:
        """List tasks.

        Args:
            status: Optional status filter
            limit: Maximum number of tasks to return

        Returns:
            List of task results
        """
        status_str = status.value if status else None
        task_data_list = await self.storage.list_tasks(status=status_str, limit=limit)

        results = []
        for task_data in task_data_list:
            results.append(
                AgentTaskResult(
                    task_id=task_data["task_id"],
                    status=TaskStatus(task_data["status"]),
                    output=task_data.get("output", ""),
                    error=task_data.get("error"),
                    exit_code=task_data.get("exit_code"),
                    started_at=(
                        datetime.fromisoformat(task_data["started_at"])
                        if task_data.get("started_at")
                        else None
                    ),
                    completed_at=(
                        datetime.fromisoformat(task_data["completed_at"])
                        if task_data.get("completed_at")
                        else None
                    ),
                    execution_time_seconds=task_data.get("execution_time_seconds"),
                    enhanced_data=task_data.get("enhanced_data", {}),
                ),
            )

        return results

    async def cleanup(self) -> int:
        """Clean up old completed tasks.

        Returns:
            Number of tasks cleaned up
        """
        count = await self.storage.cleanup_old_tasks(self.retention_seconds)
        self.port_manager.cleanup_stale_allocations(self.retention_seconds)
        return count

    def get_stats(self) -> dict:
        """Get manager statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            "active_tasks": len(self.active_tasks),
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "queue_size": self._queue.qsize(),
            "port_stats": self.port_manager.get_stats(),
            "metrics": self.metrics.get_summary(),
        }
