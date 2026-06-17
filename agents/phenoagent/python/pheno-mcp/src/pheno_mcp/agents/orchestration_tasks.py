"""Task management for multi-agent orchestration."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..ports import TaskConfig

    from .orchestration_base import TaskResult, TaskStatus, WorkflowResult


class DependencyResolver:
    """Resolves task dependencies and creates execution plan."""

    def __init__(self):
        """Initialize dependency resolver."""
        self.dependencies: dict[str, Any] = {}

    def add_dependency(self, config: Any) -> None:
        """Add a task dependency."""
        self.dependencies[config.task_id] = config

    def get_execution_order(self, task_ids: list[str]) -> list[list[str]]:
        """Get execution order respecting dependencies.

        Returns tasks grouped by execution level. Tasks in the same level
        can be executed in parallel.
        """
        graph: dict[str, set[str]] = {tid: set() for tid in task_ids}
        in_degree: dict[str, int] = dict.fromkeys(task_ids, 0)

        for task_id in task_ids:
            if task_id in self.dependencies:
                deps = self.dependencies[task_id].depends_on
                for dep in deps:
                    if dep in graph:
                        graph[dep].add(task_id)
                        in_degree[task_id] += 1

        levels: list[list[str]] = []
        ready = [tid for tid, degree in in_degree.items() if degree == 0]

        while ready:
            levels.append(ready[:])
            next_ready = []

            for task_id in ready:
                for dependent in graph[task_id]:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        next_ready.append(dependent)

            ready = next_ready

        if sum(len(level) for level in levels) != len(task_ids):
            raise ValueError("Circular dependencies detected")

        return levels

    def can_execute(
        self,
        task_id: str,
        completed_tasks: set[str],
        task_results: dict[str, Any],
    ) -> tuple[bool, str | None]:
        """Check if a task can be executed."""
        if task_id not in self.dependencies:
            return True, None

        dep_config = self.dependencies[task_id]

        for dep_id in dep_config.depends_on:
            if dep_id not in completed_tasks:
                return False, f"Dependency {dep_id} not completed"

            if dep_id in task_results and not task_results[dep_id].success:
                return False, f"Dependency {dep_id} failed"

        for output_key in dep_config.required_outputs:
            found = False
            for dep_id in dep_config.depends_on:
                if dep_id in task_results:
                    result = task_results[dep_id]
                    if isinstance(result.output, dict) and output_key in result.output:
                        found = True
                        break
            if not found:
                return False, f"Required output {output_key} not found"

        if dep_config.condition:
            context = {
                dep_id: task_results[dep_id].output
                for dep_id in dep_config.depends_on
                if dep_id in task_results
            }
            if not dep_config.condition(context):
                return False, "Custom condition not met"

        return True, None


class TaskExecutionEngine:
    """Executes tasks using agent pool and adapter."""

    def __init__(
        self,
        adapter: Any,
        agent_pool: Any,
        dependency_resolver: DependencyResolver,
        task_result_class: Any,
        task_status_class: Any,
    ):
        self._adapter = adapter
        self._agent_pool = agent_pool
        self._resolver = dependency_resolver
        self._TaskResult = task_result_class
        self._TaskStatus = task_status_class

    async def execute_single_task(self, task: Any, context: dict[str, Any]) -> Any:
        """Execute a single task."""
        if not self._adapter:
            raise RuntimeError("No adapter initialized")

        task_id = task.metadata["task_id"]
        started_at = datetime.utcnow()

        agent_pair = await self._agent_pool.get_available_agent()
        if not agent_pair:
            return self._TaskResult(
                task_id=task_id,
                status=self._TaskStatus.FAILED,
                error="No available agents",
            )

        agent_id, agent_instance = agent_pair

        try:
            framework_task = await self._adapter.create_task(task, agent_instance)
            result = await self._adapter.execute_task(framework_task, context)

            completed_at = datetime.utcnow()
            duration_ms = (completed_at - started_at).total_seconds() * 1000

            await self._agent_pool.release_agent(agent_id, success=True)

            return self._TaskResult(
                task_id=task_id,
                status=self._TaskStatus.COMPLETED,
                output=result,
                agent_id=agent_id,
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=duration_ms,
            )

        except Exception as e:
            completed_at = datetime.utcnow()
            duration_ms = (completed_at - started_at).total_seconds() * 1000

            await self._agent_pool.release_agent(agent_id, success=False)

            return self._TaskResult(
                task_id=task_id,
                status=self._TaskStatus.FAILED,
                error=str(e),
                agent_id=agent_id,
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=duration_ms,
            )

    async def execute_sequential(
        self, workflow: Any, tasks: list[Any], inputs: dict[str, Any]
    ) -> Any:
        """Execute tasks sequentially."""
        context = inputs.copy()

        for task in tasks:
            task_id = task.metadata["task_id"]

            can_execute, reason = self._resolver.can_execute(
                task_id,
                set(workflow.task_results.keys()),
                workflow.task_results,
            )

            if not can_execute:
                workflow.task_results[task_id] = self._TaskResult(
                    task_id=task_id,
                    status=self._TaskStatus.SKIPPED,
                    error=reason,
                )
                continue

            result = await self.execute_single_task(task, context)
            workflow.task_results[task_id] = result

            if result.success and result.output:
                context[task_id] = result.output

        workflow.status = "success" if workflow.success else "failed"
        return workflow

    async def execute_parallel(
        self, workflow: Any, tasks: list[Any], inputs: dict[str, Any]
    ) -> Any:
        """Execute tasks in parallel respecting dependencies."""
        task_ids = [task.metadata["task_id"] for task in tasks]
        execution_levels = self._resolver.get_execution_order(task_ids)

        context = inputs.copy()

        for level in execution_levels:
            level_tasks = [task for task in tasks if task.metadata["task_id"] in level]

            results = await asyncio.gather(
                *[self.execute_single_task(task, context) for task in level_tasks],
                return_exceptions=True,
            )

            for task, result in zip(level_tasks, results, strict=False):
                task_id = task.metadata["task_id"]
                if isinstance(result, Exception):
                    workflow.task_results[task_id] = self._TaskResult(
                        task_id=task_id,
                        status=self._TaskStatus.FAILED,
                        error=str(result),
                    )
                else:
                    workflow.task_results[task_id] = result
                    if result.success and result.output:
                        context[task_id] = result.output

        workflow.status = "success" if workflow.success else "failed"
        return workflow

    async def execute_hierarchical(
        self, workflow: Any, tasks: list[Any], inputs: dict[str, Any]
    ) -> Any:
        """Execute tasks hierarchically (manager delegates to workers)."""
        if not tasks:
            workflow.status = "success"
            return workflow

        manager_task = tasks[0]
        worker_tasks = tasks[1:]

        manager_result = await self.execute_single_task(manager_task, inputs)
        workflow.task_results[manager_task.metadata["task_id"]] = manager_result

        if worker_tasks:
            worker_results = await asyncio.gather(
                *[self.execute_single_task(task, inputs) for task in worker_tasks],
            )
            for task, result in zip(worker_tasks, worker_results, strict=False):
                workflow.task_results[task.metadata["task_id"]] = result

        workflow.status = "success" if workflow.success else "failed"
        return workflow

    async def execute_conditional(
        self, workflow: Any, tasks: list[Any], inputs: dict[str, Any]
    ) -> Any:
        """Execute tasks conditionally based on previous results."""
        context = inputs.copy()

        for task in tasks:
            task_id = task.metadata["task_id"]

            can_execute, reason = self._resolver.can_execute(
                task_id,
                set(workflow.task_results.keys()),
                workflow.task_results,
            )

            if can_execute:
                result = await self.execute_single_task(task, context)
                workflow.task_results[task_id] = result
                if result.success and result.output:
                    context[task_id] = result.output
            else:
                workflow.task_results[task_id] = self._TaskResult(
                    task_id=task_id,
                    status=self._TaskStatus.SKIPPED,
                    error=reason,
                )

        workflow.status = "success" if workflow.success else "failed"
        return workflow
