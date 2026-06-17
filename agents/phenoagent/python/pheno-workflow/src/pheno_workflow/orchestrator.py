"""
Workflow Orchestration Engine.

This module provides comprehensive workflow orchestration capabilities including:
- DAG-based workflow definitions
- Sequential and parallel step execution
- Conditional branching (if/else logic)
- Error handling and retry mechanisms
- Workflow state tracking and persistence
- Event emission on state changes
- Workflow triggers (time-based, event-based, manual)

The orchestrator can be enhanced with Temporal for distributed workflows in the future.
"""

import asyncio
import logging
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class WorkflowStatus(Enum):
    """Workflow execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class StepStatus(Enum):
    """Step execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


class TriggerType(Enum):
    """Workflow trigger types."""

    MANUAL = "manual"
    SCHEDULED = "scheduled"
    EVENT = "event"
    WEBHOOK = "webhook"


@dataclass
class StepResult:
    """Result of a step execution."""

    step_id: str
    status: StepStatus
    output: Any = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    retry_count: int = 0


@dataclass
class WorkflowStep:
    """
    Represents a single step in a workflow.

    Attributes:
        step_id: Unique identifier for the step
        handler: Callable that executes the step logic
        dependencies: List of step IDs that must complete before this step
        condition: Optional callable that determines if step should execute
        retry_policy: Retry configuration (max_retries, backoff_factor)
        timeout: Maximum execution time in seconds
        parallel: Whether this step can run in parallel with others
        on_failure: Behavior on failure ('fail', 'continue', 'skip_branch')
        metadata: Additional metadata for the step
    """

    step_id: str
    handler: Callable
    dependencies: list[str] = field(default_factory=list)
    condition: Callable[[dict[str, Any]], bool] | None = None
    retry_policy: dict[str, Any] = field(default_factory=lambda: {"max_retries": 3, "backoff_factor": 2})
    timeout: int | None = None
    parallel: bool = False
    on_failure: str = "fail"  # 'fail', 'continue', 'skip_branch'
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowDefinition:
    """
    Defines a workflow as a DAG of steps.

    Attributes:
        workflow_id: Unique identifier for the workflow
        name: Human-readable name
        steps: Dictionary of step_id -> WorkflowStep
        description: Optional description
        timeout: Maximum workflow execution time in seconds
        tags: Tags for categorization
    """

    workflow_id: str
    name: str
    steps: dict[str, WorkflowStep] = field(default_factory=dict)
    description: str = ""
    timeout: int | None = None
    tags: list[str] = field(default_factory=list)

    def add_step(self, step: WorkflowStep) -> "WorkflowDefinition":
        """Add a step to the workflow."""
        self.steps[step.step_id] = step
        return self

    def validate(self) -> tuple[bool, list[str]]:
        """
        Validate the workflow definition.

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Check for cycles
        if self._has_cycle():
            errors.append("Workflow contains cycles")

        # Check for invalid dependencies
        for step_id, step in self.steps.items():
            for dep in step.dependencies:
                if dep not in self.steps:
                    errors.append(f"Step {step_id} has invalid dependency: {dep}")

        return len(errors) == 0, errors

    def _has_cycle(self) -> bool:
        """Check if the workflow has cycles using DFS."""
        visited = set()
        rec_stack = set()

        def visit(step_id: str) -> bool:
            # Skip if step doesn't exist (will be caught by dependency validation)
            if step_id not in self.steps:
                return False

            visited.add(step_id)
            rec_stack.add(step_id)

            for dep in self.steps[step_id].dependencies:
                if dep not in visited:
                    if visit(dep):
                        return True
                elif dep in rec_stack:
                    return True

            rec_stack.remove(step_id)
            return False

        return any(step_id not in visited and visit(step_id) for step_id in self.steps)


@dataclass
class WorkflowExecution:
    """
    Represents a running or completed workflow execution.

    Tracks state, results, and events for a workflow instance.
    """

    execution_id: str = field(default_factory=lambda: str(uuid4()))
    workflow_id: str = ""
    status: WorkflowStatus = WorkflowStatus.PENDING
    context: dict[str, Any] = field(default_factory=dict)
    step_results: dict[str, StepResult] = field(default_factory=dict)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    events: list[dict[str, Any]] = field(default_factory=list)
    trigger_type: TriggerType = TriggerType.MANUAL
    trigger_data: dict[str, Any] = field(default_factory=dict)

    def emit_event(self, event_type: str, data: dict[str, Any] | None = None):
        """Emit a workflow event."""
        event = {
            "type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data or {},
        }
        self.events.append(event)
        logger.info(f"Event emitted: {event_type} for execution {self.execution_id}")


@dataclass
class WorkflowTrigger:
    """
    Defines when and how a workflow should be triggered.

    Supports manual, scheduled, and event-based triggers.
    """

    trigger_id: str = field(default_factory=lambda: str(uuid4()))
    trigger_type: TriggerType = TriggerType.MANUAL
    workflow_id: str = ""
    schedule: str | None = None  # Cron expression for scheduled triggers
    event_pattern: dict[str, Any] | None = None  # Pattern for event-based triggers
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


class WorkflowOrchestrator:
    """
    Main orchestrator for executing workflows.

    Features:
    - Sequential and parallel execution
    - Conditional branching
    - Error handling and retries
    - State persistence
    - Event emission
    - Workflow triggers
    """

    def __init__(self, state_backend: dict[str, Any] | None = None):
        """
        Initialize the orchestrator.

        Args:
            state_backend: Optional dictionary for state persistence (can be replaced with DB)
        """
        self.workflows: dict[str, WorkflowDefinition] = {}
        self.executions: dict[str, WorkflowExecution] = {}
        self.triggers: dict[str, WorkflowTrigger] = {}
        self.state_backend = state_backend or {}
        self.event_handlers: dict[str, list[Callable]] = defaultdict(list)

    def register_workflow(self, workflow: WorkflowDefinition):
        """Register a workflow definition."""
        is_valid, errors = workflow.validate()
        if not is_valid:
            raise ValueError(f"Invalid workflow: {errors}")

        self.workflows[workflow.workflow_id] = workflow
        logger.info(f"Registered workflow: {workflow.name} ({workflow.workflow_id})")

    def register_trigger(self, trigger: WorkflowTrigger):
        """Register a workflow trigger."""
        if trigger.workflow_id not in self.workflows:
            raise ValueError(f"Workflow {trigger.workflow_id} not found")

        self.triggers[trigger.trigger_id] = trigger
        logger.info(f"Registered trigger: {trigger.trigger_id} for {trigger.workflow_id}")

    def on_event(self, event_type: str, handler: Callable):
        """Register an event handler."""
        self.event_handlers[event_type].append(handler)

    async def execute_workflow(
        self,
        workflow_id: str,
        context: dict[str, Any] | None = None,
        trigger_type: TriggerType = TriggerType.MANUAL,
        trigger_data: dict[str, Any] | None = None,
    ) -> WorkflowExecution:
        """
        Execute a workflow.

        Args:
            workflow_id: ID of the workflow to execute
            context: Initial context/input data
            trigger_type: How the workflow was triggered
            trigger_data: Additional trigger information

        Returns:
            WorkflowExecution object with results
        """
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} not found")

        workflow = self.workflows[workflow_id]
        execution = WorkflowExecution(
            workflow_id=workflow_id,
            context=context or {},
            trigger_type=trigger_type,
            trigger_data=trigger_data or {},
        )

        self.executions[execution.execution_id] = execution
        execution.started_at = datetime.utcnow()
        execution.status = WorkflowStatus.RUNNING
        execution.emit_event("workflow.started", {"workflow_id": workflow_id})

        await self._notify_event_handlers("workflow.started", execution)

        try:
            # Execute steps in topological order with parallelism
            await self._execute_steps(workflow, execution)

            execution.status = WorkflowStatus.COMPLETED
            execution.completed_at = datetime.utcnow()
            execution.emit_event("workflow.completed")
            await self._notify_event_handlers("workflow.completed", execution)

        except asyncio.CancelledError:
            execution.status = WorkflowStatus.CANCELLED
            execution.error = "Workflow cancelled"
            execution.emit_event("workflow.cancelled")
            await self._notify_event_handlers("workflow.cancelled", execution)
            raise

        except Exception as e:
            execution.status = WorkflowStatus.FAILED
            execution.error = str(e)
            execution.completed_at = datetime.utcnow()
            execution.emit_event("workflow.failed", {"error": str(e)})
            await self._notify_event_handlers("workflow.failed", execution)
            logger.error(f"Workflow {workflow_id} failed: {e}", exc_info=True)
            raise

        finally:
            # Persist state
            await self._persist_execution(execution)

        return execution

    async def _execute_steps(
        self, workflow: WorkflowDefinition, execution: WorkflowExecution,
    ):
        """Execute workflow steps in topological order with parallelism."""
        # Build execution plan
        execution_plan = self._build_execution_plan(workflow)

        for wave in execution_plan:
            # Execute steps in current wave (can be parallel)
            tasks = []
            for step_id in wave:
                step = workflow.steps[step_id]

                # Check if step should be executed based on condition
                if step.condition and not await self._evaluate_condition(
                    step.condition, execution.context,
                ):
                    result = StepResult(
                        step_id=step_id,
                        status=StepStatus.SKIPPED,
                        started_at=datetime.utcnow(),
                        completed_at=datetime.utcnow(),
                    )
                    execution.step_results[step_id] = result
                    execution.emit_event("step.skipped", {"step_id": step_id})
                    continue

                # Check if dependencies succeeded
                if not self._dependencies_succeeded(step, execution):
                    result = StepResult(
                        step_id=step_id,
                        status=StepStatus.SKIPPED,
                        started_at=datetime.utcnow(),
                        completed_at=datetime.utcnow(),
                    )
                    execution.step_results[step_id] = result
                    execution.emit_event(
                        "step.skipped", {"step_id": step_id, "reason": "dependency_failed"},
                    )
                    continue

                # Execute step
                task = self._execute_step(step, execution)
                tasks.append(task)

            # Wait for all steps in wave to complete
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

    def _build_execution_plan(
        self, workflow: WorkflowDefinition,
    ) -> list[list[str]]:
        """
        Build execution plan as waves of steps that can run in parallel.

        Returns:
            List of waves, where each wave is a list of step IDs
        """
        # Calculate in-degree for each step
        in_degree = dict.fromkeys(workflow.steps, 0)
        for step in workflow.steps.values():
            for _dep in step.dependencies:
                in_degree[step.step_id] += 1

        # Build waves
        waves = []
        remaining = set(workflow.steps.keys())

        while remaining:
            # Find steps with no dependencies
            wave = [
                step_id
                for step_id in remaining
                if in_degree[step_id] == 0
            ]

            if not wave:
                # This shouldn't happen if validation passed
                raise RuntimeError("Circular dependency detected")

            waves.append(wave)

            # Remove wave from remaining and update in-degrees
            for step_id in wave:
                remaining.remove(step_id)
                for other_step in workflow.steps.values():
                    if step_id in other_step.dependencies:
                        in_degree[other_step.step_id] -= 1

        return waves

    async def _execute_step(
        self, step: WorkflowStep, execution: WorkflowExecution,
    ) -> StepResult:
        """Execute a single step with retry logic."""
        result = StepResult(
            step_id=step.step_id,
            status=StepStatus.PENDING,
        )
        execution.step_results[step.step_id] = result

        result.started_at = datetime.utcnow()
        result.status = StepStatus.RUNNING
        execution.emit_event("step.started", {"step_id": step.step_id})
        await self._notify_event_handlers("step.started", execution)

        max_retries = step.retry_policy.get("max_retries", 3)
        backoff_factor = step.retry_policy.get("backoff_factor", 2)

        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    result.status = StepStatus.RETRYING
                    result.retry_count = attempt
                    execution.emit_event(
                        "step.retrying", {"step_id": step.step_id, "attempt": attempt},
                    )
                    await asyncio.sleep(backoff_factor**attempt)

                # Execute with timeout if specified
                if step.timeout:
                    output = await asyncio.wait_for(
                        self._call_handler(step.handler, execution.context),
                        timeout=step.timeout,
                    )
                else:
                    output = await self._call_handler(step.handler, execution.context)

                # Success
                result.status = StepStatus.COMPLETED
                result.output = output
                result.completed_at = datetime.utcnow()

                # Update context with step output
                execution.context[f"step_{step.step_id}_output"] = output

                execution.emit_event(
                    "step.completed", {"step_id": step.step_id, "output": output},
                )
                await self._notify_event_handlers("step.completed", execution)

                return result

            except TimeoutError:
                error_msg = f"Step {step.step_id} timed out after {step.timeout}s"
                logger.warning(error_msg)

                if attempt == max_retries:
                    result.status = StepStatus.FAILED
                    result.error = error_msg
                    result.completed_at = datetime.utcnow()
                    execution.emit_event(
                        "step.failed", {"step_id": step.step_id, "error": error_msg},
                    )
                    await self._notify_event_handlers("step.failed", execution)

                    if step.on_failure == "fail":
                        raise
                    if step.on_failure == "continue":
                        return result

            except Exception as e:
                error_msg = f"Step {step.step_id} failed: {e!s}"
                logger.error(error_msg, exc_info=True)

                if attempt == max_retries:
                    result.status = StepStatus.FAILED
                    result.error = error_msg
                    result.completed_at = datetime.utcnow()
                    execution.emit_event(
                        "step.failed", {"step_id": step.step_id, "error": error_msg},
                    )
                    await self._notify_event_handlers("step.failed", execution)

                    if step.on_failure == "fail":
                        raise
                    if step.on_failure == "continue":
                        return result

        return result

    async def _call_handler(self, handler: Callable, context: dict[str, Any]) -> Any:
        """Call a step handler, supporting both sync and async functions."""
        if asyncio.iscoroutinefunction(handler):
            return await handler(context)
        # Run sync functions in executor to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, handler, context)

    async def _evaluate_condition(
        self, condition: Callable, context: dict[str, Any],
    ) -> bool:
        """Evaluate a condition function."""
        if asyncio.iscoroutinefunction(condition):
            return await condition(context)
        return condition(context)

    def _dependencies_succeeded(
        self, step: WorkflowStep, execution: WorkflowExecution,
    ) -> bool:
        """Check if all dependencies completed successfully."""
        for dep_id in step.dependencies:
            if dep_id not in execution.step_results:
                return False
            if execution.step_results[dep_id].status != StepStatus.COMPLETED:
                return False
        return True

    async def _persist_execution(self, execution: WorkflowExecution):
        """Persist execution state to backend."""
        self.state_backend[execution.execution_id] = {
            "execution_id": execution.execution_id,
            "workflow_id": execution.workflow_id,
            "status": execution.status.value,
            "started_at": execution.started_at.isoformat() if execution.started_at else None,
            "completed_at": execution.completed_at.isoformat()
            if execution.completed_at
            else None,
            "error": execution.error,
            "trigger_type": execution.trigger_type.value,
            "step_count": len(execution.step_results),
            "successful_steps": sum(
                1
                for r in execution.step_results.values()
                if r.status == StepStatus.COMPLETED
            ),
            "failed_steps": sum(
                1 for r in execution.step_results.values() if r.status == StepStatus.FAILED
            ),
        }
        logger.debug(f"Persisted execution {execution.execution_id}")

    async def _notify_event_handlers(self, event_type: str, execution: WorkflowExecution):
        """Notify registered event handlers."""
        if event_type in self.event_handlers:
            for handler in self.event_handlers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(execution)
                    else:
                        handler(execution)
                except Exception as e:
                    logger.exception(f"Error in event handler for {event_type}: {e}")

    def get_execution(self, execution_id: str) -> WorkflowExecution | None:
        """Get execution by ID."""
        return self.executions.get(execution_id)

    def list_executions(
        self, workflow_id: str | None = None, status: WorkflowStatus | None = None,
    ) -> list[WorkflowExecution]:
        """List executions with optional filters."""
        executions = list(self.executions.values())

        if workflow_id:
            executions = [e for e in executions if e.workflow_id == workflow_id]

        if status:
            executions = [e for e in executions if e.status == status]

        return executions

    async def cancel_execution(self, execution_id: str):
        """Cancel a running execution."""
        execution = self.executions.get(execution_id)
        if not execution:
            raise ValueError(f"Execution {execution_id} not found")

        if execution.status not in (WorkflowStatus.RUNNING, WorkflowStatus.PENDING):
            raise ValueError(f"Cannot cancel execution in status {execution.status}")

        execution.status = WorkflowStatus.CANCELLED
        execution.completed_at = datetime.utcnow()
        execution.emit_event("workflow.cancelled")
        await self._persist_execution(execution)

    async def pause_execution(self, execution_id: str):
        """Pause a running execution."""
        execution = self.executions.get(execution_id)
        if not execution:
            raise ValueError(f"Execution {execution_id} not found")

        if execution.status != WorkflowStatus.RUNNING:
            raise ValueError(f"Cannot pause execution in status {execution.status}")

        execution.status = WorkflowStatus.PAUSED
        execution.emit_event("workflow.paused")

    async def resume_execution(self, execution_id: str):
        """Resume a paused execution."""
        execution = self.executions.get(execution_id)
        if not execution:
            raise ValueError(f"Execution {execution_id} not found")

        if execution.status != WorkflowStatus.PAUSED:
            raise ValueError(f"Cannot resume execution in status {execution.status}")

        execution.status = WorkflowStatus.RUNNING
        execution.emit_event("workflow.resumed")

        # Continue execution (simplified - would need more sophisticated state tracking)
        workflow = self.workflows[execution.workflow_id]
        await self._execute_steps(workflow, execution)


# Utility functions for building workflows


def build_simple_workflow(
    name: str, steps: list[tuple[str, Callable]], workflow_id: str | None = None,
) -> WorkflowDefinition:
    """
    Build a simple sequential workflow.

    Args:
        name: Workflow name
        steps: List of (step_id, handler) tuples
        workflow_id: Optional workflow ID

    Returns:
        WorkflowDefinition
    """
    workflow = WorkflowDefinition(
        workflow_id=workflow_id or f"workflow_{name.lower().replace(' ', '_')}",
        name=name,
    )

    previous_step_id = None
    for step_id, handler in steps:
        dependencies = [previous_step_id] if previous_step_id else []
        step = WorkflowStep(
            step_id=step_id,
            handler=handler,
            dependencies=dependencies,
        )
        workflow.add_step(step)
        previous_step_id = step_id

    return workflow


def build_parallel_workflow(
    name: str,
    parallel_steps: list[tuple[str, Callable]],
    workflow_id: str | None = None,
) -> WorkflowDefinition:
    """
    Build a workflow with parallel steps.

    Args:
        name: Workflow name
        parallel_steps: List of (step_id, handler) tuples to run in parallel
        workflow_id: Optional workflow ID

    Returns:
        WorkflowDefinition
    """
    workflow = WorkflowDefinition(
        workflow_id=workflow_id or f"workflow_{name.lower().replace(' ', '_')}",
        name=name,
    )

    for step_id, handler in parallel_steps:
        step = WorkflowStep(
            step_id=step_id,
            handler=handler,
            parallel=True,
        )
        workflow.add_step(step)

    return workflow
