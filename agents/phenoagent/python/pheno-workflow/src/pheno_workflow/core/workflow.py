"""Core Workflow Classes.

Base classes and decorators for defining workflows.
"""

import asyncio
import inspect
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, TypeVar

T = TypeVar("T")


class WorkflowStatus(Enum):
    """
    Workflow execution status.
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


@dataclass
class WorkflowStep:
    """
    Represents a single step in a workflow.
    """

    name: str
    func: Callable
    inputs: list[str] | None = None
    outputs: list[str] | None = None
    retry_count: int = 3
    timeout: int | None = None
    compensate: str | None = None  # Name of compensation function


@dataclass
class WorkflowContext:
    """
    Context passed to workflow steps.
    """

    workflow_id: str
    execution_id: str
    inputs: dict[str, Any]
    state: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    orchestrator: Any | None = None

    async def call_service(self, service: str, method: str, *args, **kwargs) -> Any:
        """
        Call a service method (integrates with orchestrator).
        """
        if self.orchestrator:
            # Try to import orchestrator-kit if available
            try:
                from orchestrator_kit import TaskRequest

                task = TaskRequest(
                    id=f"{self.workflow_id}-{service}-{method}",
                    type=f"{service}.{method}",
                    payload={"args": args, "kwargs": kwargs},
                    priority=1,
                )
                result = await self.orchestrator.execute_task(task)
                return result.result
            except ImportError:
                pass

        # Fallback: just log the service call
        print(f"Service call: {service}.{method}(*{args}, **{kwargs})")
        return None


class Workflow:
    """
    Base workflow class.
    """

    def __init__(self):
        self.steps: list[WorkflowStep] = []
        self.status = WorkflowStatus.PENDING
        self.workflow_id: str | None = None
        self.execution_id: str | None = None
        self.context: WorkflowContext | None = None
        self._discover_steps()

    def _discover_steps(self):
        """
        Discover workflow steps from methods.
        """
        for name, method in inspect.getmembers(self, predicate=inspect.ismethod):
            if hasattr(method, "__workflow_step__"):
                step_config = method.__workflow_step__
                self.steps.append(WorkflowStep(name=name, func=method, **step_config))

    async def execute(self, inputs: dict[str, Any]) -> Any:
        """
        Execute the workflow.
        """
        self.status = WorkflowStatus.RUNNING

        try:
            self.context = WorkflowContext(
                workflow_id=self.workflow_id or f"wf-{id(self)}",
                execution_id=self.execution_id or f"exec-{id(self)}-{datetime.now().timestamp()}",
                inputs=inputs,
            )

            result = await self._execute_steps(self.context)
            self.status = WorkflowStatus.COMPLETED
            return result

        except Exception:
            self.status = WorkflowStatus.FAILED
            raise

    async def _execute_steps(self, ctx: WorkflowContext) -> Any:
        """
        Execute workflow steps in sequence.
        """
        result = None

        for step in self.steps:
            # Execute step with retry logic
            for attempt in range(step.retry_count):
                try:
                    if step.timeout:
                        result = await asyncio.wait_for(step.func(ctx), timeout=step.timeout)
                    else:
                        result = await step.func(ctx)

                    # Store result in context
                    ctx.state[step.name] = result
                    break

                except Exception:
                    if attempt < step.retry_count - 1:
                        # Retry with exponential backoff
                        await asyncio.sleep(2**attempt)
                        continue
                    # All retries exhausted
                    raise

        return result

    async def compensate(self):
        """
        Run compensation for all executed steps (for saga pattern).
        """
        if not self.context:
            return

        # Compensate in reverse order
        for step in reversed(self.steps):
            if step.compensate and step.name in self.context.state:
                compensation_func = getattr(self, step.compensate, None)
                if compensation_func:
                    try:
                        result = self.context.state[step.name]
                        await compensation_func(self.context, result)
                    except Exception as e:
                        print(f"Compensation failed for {step.name}: {e}")


def workflow(cls: type[T]) -> type[T]:
    """
    Decorator to mark a class as a workflow.
    """
    if not issubclass(cls, Workflow):
        raise TypeError(f"{cls.__name__} must inherit from Workflow")
    cls.__workflow__ = True
    return cls


def step(
    name: str | None = None,
    inputs: list[str] | None = None,
    outputs: list[str] | None = None,
    retry_count: int = 3,
    timeout: int | None = None,
    compensate: str | None = None,
):
    """
    Decorator to mark a method as a workflow step.
    """

    def decorator(func: Callable) -> Callable:
        func.__workflow_step__ = {
            "inputs": inputs,
            "outputs": outputs,
            "retry_count": retry_count,
            "timeout": timeout,
            "compensate": compensate,
        }
        return func

    return decorator
