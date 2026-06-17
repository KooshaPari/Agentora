"""
Simple workflow engine for background jobs.
"""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4


class WorkflowStatus(Enum):
    """
    Workflow execution status.
    """

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkflowStep:
    """
    A step in a workflow.
    """

    name: str
    handler: Callable
    retry_on_failure: bool = True
    max_retries: int = 3


@dataclass
class WorkflowExecution:
    """
    Workflow execution state.
    """

    workflow_id: str = field(default_factory=lambda: str(uuid4()))
    status: WorkflowStatus = WorkflowStatus.PENDING
    current_step: int = 0
    context: dict[str, Any] = field(default_factory=dict)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None


class Workflow:
    """Simple workflow definition.

    Example:
        workflow = Workflow("process_data")

        workflow.add_step("fetch", fetch_data)
        workflow.add_step("transform", transform_data)
        workflow.add_step("save", save_data)

        engine = WorkflowEngine()
        await engine.execute(workflow, {"input": "data"})
    """

    def __init__(self, name: str):
        self.name = name
        self.steps: list[WorkflowStep] = []

    def add_step(
        self,
        name: str,
        handler: Callable,
        retry_on_failure: bool = True,
        max_retries: int = 3,
    ) -> "Workflow":
        """
        Add a step to the workflow.
        """
        step = WorkflowStep(
            name=name,
            handler=handler,
            retry_on_failure=retry_on_failure,
            max_retries=max_retries,
        )
        self.steps.append(step)
        return self


class WorkflowEngine:
    """Simple workflow execution engine.

    Example:
        engine = WorkflowEngine()
        execution = await engine.execute(workflow, context)
    """

    async def execute(
        self,
        workflow: Workflow,
        context: dict[str, Any] | None = None,
    ) -> WorkflowExecution:
        """
        Execute a workflow.
        """
        execution = WorkflowExecution(
            context=context or {},
            started_at=datetime.utcnow(),
            status=WorkflowStatus.RUNNING,
        )

        try:
            for i, step in enumerate(workflow.steps):
                execution.current_step = i
                await self._execute_step(step, execution)

            execution.status = WorkflowStatus.COMPLETED
            execution.completed_at = datetime.utcnow()

        except Exception as e:
            execution.status = WorkflowStatus.FAILED
            execution.error = str(e)
            raise

        return execution

    async def _execute_step(
        self,
        step: WorkflowStep,
        execution: WorkflowExecution,
    ):
        """
        Execute a workflow step.
        """
        for attempt in range(step.max_retries if step.retry_on_failure else 1):
            try:
                if asyncio.iscoroutinefunction(step.handler):
                    result = await step.handler(execution.context)
                else:
                    result = step.handler(execution.context)

                if result is not None:
                    execution.context[f"{step.name}_result"] = result

                return

            except Exception:
                if attempt == step.max_retries - 1 or not step.retry_on_failure:
                    raise
                await asyncio.sleep(2**attempt)
