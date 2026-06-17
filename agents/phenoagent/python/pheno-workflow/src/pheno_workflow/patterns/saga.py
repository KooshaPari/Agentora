"""
Saga pattern implementation for distributed transactions.
"""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


class SagaStatus(Enum):
    """
    Saga execution status.
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    FAILED = "failed"


@dataclass
class SagaStep:
    """A step in a saga with action and compensation.

    Example:
        step = SagaStep(
            name="reserve_inventory",
            action=lambda ctx: inventory.reserve(ctx["order_id"]),
            compensation=lambda ctx: inventory.release(ctx["order_id"])
        )
    """

    name: str
    action: Callable
    compensation: Callable | None = None
    max_retries: int = 3
    timeout: float | None = None


@dataclass
class SagaContext:
    """
    Saga execution context.
    """

    saga_id: str = field(default_factory=lambda: str(uuid4()))
    data: dict[str, Any] = field(default_factory=dict)
    completed_steps: list[str] = field(default_factory=list)
    failed_step: str | None = None
    error: Exception | None = None


class Saga:
    """Saga pattern for distributed transactions with compensation.

    A saga is a sequence of local transactions where each transaction
    updates data within a single service. If a transaction fails, the
    saga executes compensating transactions to undo the completed steps.

    Example:
        # Create saga
        saga = Saga("process_order")

        # Add steps
        saga.add_step(
            name="reserve_inventory",
            action=lambda ctx: inventory.reserve(ctx["order_id"]),
            compensation=lambda ctx: inventory.release(ctx["order_id"])
        )

        saga.add_step(
            name="charge_payment",
            action=lambda ctx: payment.charge(ctx["amount"]),
            compensation=lambda ctx: payment.refund(ctx["transaction_id"])
        )

        saga.add_step(
            name="ship_order",
            action=lambda ctx: shipping.ship(ctx["order_id"]),
            compensation=lambda ctx: shipping.cancel(ctx["shipment_id"])
        )

        # Execute saga
        executor = SagaExecutor()
        result = await executor.execute(saga, {"order_id": "123", "amount": 100})
    """

    def __init__(self, name: str):
        self.name = name
        self.steps: list[SagaStep] = []

    def add_step(
        self,
        name: str,
        action: Callable,
        compensation: Callable | None = None,
        max_retries: int = 3,
        timeout: float | None = None,
    ) -> "Saga":
        """
        Add a step to the saga.
        """
        step = SagaStep(
            name=name,
            action=action,
            compensation=compensation,
            max_retries=max_retries,
            timeout=timeout,
        )
        self.steps.append(step)
        return self

    def get_steps(self) -> list[SagaStep]:
        """
        Get all saga steps.
        """
        return self.steps


class SagaExecutor:
    """Executes sagas with automatic compensation on failure.

    Features:
    - Sequential execution of steps
    - Automatic compensation on failure
    - Retry logic for failed steps
    - Timeout support
    - Async execution

    Example:
        executor = SagaExecutor()

        # Execute saga
        result = await executor.execute(saga, initial_data)

        # Check result
        if result.status == SagaStatus.COMPLETED:
            print("Success!")
        elif result.status == SagaStatus.COMPENSATED:
            print("Failed and compensated")
    """

    async def execute(
        self,
        saga: Saga,
        initial_data: dict[str, Any] | None = None,
    ) -> SagaContext:
        """Execute a saga.

        Args:
            saga: The saga to execute
            initial_data: Initial data for saga context

        Returns:
            SagaContext with execution results
        """
        context = SagaContext(data=initial_data or {})

        try:
            # Execute steps sequentially
            for step in saga.steps:
                await self._execute_step(step, context)
                context.completed_steps.append(step.name)

            return context

        except Exception as e:
            # Step failed, compensate
            context.error = e
            await self._compensate(saga, context)
            raise

    async def _execute_step(self, step: SagaStep, context: SagaContext):
        """
        Execute a single saga step with retry.
        """
        last_error = None

        for attempt in range(step.max_retries):
            try:
                # Execute with timeout if specified
                if step.timeout:
                    result = await asyncio.wait_for(
                        self._call_action(step.action, context), timeout=step.timeout,
                    )
                else:
                    result = await self._call_action(step.action, context)

                # Store result in context
                if result is not None:
                    context.data[f"{step.name}_result"] = result

                return

            except Exception as e:
                last_error = e
                if attempt < step.max_retries - 1:
                    await asyncio.sleep(2**attempt)  # Exponential backoff

        # All retries failed
        context.failed_step = step.name
        raise last_error

    async def _call_action(self, action: Callable, context: SagaContext) -> Any:
        """
        Call action (sync or async).
        """
        if asyncio.iscoroutinefunction(action):
            return await action(context)
        return action(context)

    async def _compensate(self, saga: Saga, context: SagaContext):
        """
        Compensate completed steps in reverse order.
        """
        # Get completed steps in reverse
        completed_step_names = context.completed_steps[::-1]

        for step_name in completed_step_names:
            # Find step
            step = next((s for s in saga.steps if s.name == step_name), None)
            if not step or not step.compensation:
                continue

            try:
                await self._call_action(step.compensation, context)
            except Exception as comp_error:
                # Log compensation failure but continue
                print(f"Compensation failed for {step_name}: {comp_error}")


class SagaOrchestrator:
    """Orchestrates multiple sagas with dependencies.

    Example:
        orchestrator = SagaOrchestrator()

        # Register sagas
        orchestrator.register_saga("process_order", order_saga)
        orchestrator.register_saga("update_inventory", inventory_saga)

        # Execute with dependencies
        await orchestrator.execute_with_deps(
            "process_order",
            data={"order_id": "123"},
            depends_on=["update_inventory"]
        )
    """

    def __init__(self):
        self._sagas: dict[str, Saga] = {}
        self._executor = SagaExecutor()

    def register_saga(self, name: str, saga: Saga):
        """
        Register a saga.
        """
        self._sagas[name] = saga

    async def execute_with_deps(
        self,
        saga_name: str,
        data: dict[str, Any] | None = None,
        depends_on: list[str] | None = None,
    ) -> dict[str, SagaContext]:
        """Execute saga with dependencies.

        Args:
            saga_name: Name of saga to execute
            data: Initial data
            depends_on: List of saga names that must complete first

        Returns:
            Dictionary of saga name to context
        """
        results = {}

        # Execute dependencies first
        if depends_on:
            for dep_name in depends_on:
                if dep_name not in self._sagas:
                    raise ValueError(f"Dependency saga not found: {dep_name}")

                dep_saga = self._sagas[dep_name]
                dep_result = await self._executor.execute(dep_saga, data)
                results[dep_name] = dep_result

                # Merge results into data for next saga
                if data:
                    data.update(dep_result.data)

        # Execute main saga
        saga = self._sagas.get(saga_name)
        if not saga:
            raise ValueError(f"Saga not found: {saga_name}")

        result = await self._executor.execute(saga, data)
        results[saga_name] = result

        return results
