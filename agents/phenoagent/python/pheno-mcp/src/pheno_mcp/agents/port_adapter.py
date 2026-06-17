"""AgentOrchestratorPort Adapter.

This module provides an adapter that makes the Orchestrator class compatible with the
AgentOrchestratorPort protocol defined in pheno.mcp.ports.

This allows the Orchestrator to be used anywhere an AgentOrchestratorPort implementation
is expected, ensuring compatibility with the rest of the pheno-sdk ecosystem.
"""

from __future__ import annotations

import logging
from typing import Any

from ..ports import AgentConfig, AgentOrchestratorPort, ExecutionResult, TaskConfig
from .orchestration_base import (
    AgentPoolConfig,
    FrameworkConfig,
    Orchestrator,
    WorkflowPattern,
)

logger = logging.getLogger(__name__)


class OrchestratorPortAdapter(AgentOrchestratorPort):
    """Adapter that makes Orchestrator compatible with AgentOrchestratorPort.

    This class wraps the Orchestrator to provide the interface expected by
    the AgentOrchestratorPort protocol.

    Example:
        ```python
        from pheno.mcp.agents.port_adapter import OrchestratorPortAdapter
        from pheno.mcp.ports import AgentConfig, TaskConfig

        # Create adapter
        adapter = OrchestratorPortAdapter(framework="crewai")

        # Use as AgentOrchestratorPort
        agent_id = await adapter.create_agent(
            AgentConfig(
                name="researcher",
                role="Research Analyst",
                goal="Find information"
            )
        )

        result = await adapter.execute_task(
            TaskConfig(
                description="Research AI trends",
                agent="researcher"
            )
        )
        ```
    """

    def __init__(
        self,
        framework: str = "custom",
        framework_config: FrameworkConfig | None = None,
        pool_config: AgentPoolConfig | None = None,
    ):
        """Initialize adapter.

        Args:
            framework: Framework to use (crewai, langgraph, autogen, custom)
            framework_config: Framework-specific configuration
            pool_config: Agent pool configuration
        """
        self.orchestrator = Orchestrator(
            framework=framework,
            framework_config=framework_config,
            pool_config=pool_config,
        )
        logger.info(f"Initialized OrchestratorPortAdapter with framework: {framework}")

    async def create_agent(self, config: AgentConfig) -> str:
        """Create an agent.

        Args:
            config: Agent configuration

        Returns:
            Agent ID

        Raises:
            RuntimeError: If agent creation fails
        """
        try:
            agent_id = await self.orchestrator.create_agent(
                name=config.name,
                role=config.role,
                goal=config.goal,
                backstory=config.backstory,
                tools=config.tools,
                metadata=config.metadata,
            )
            logger.info(f"Created agent via port adapter: {agent_id}")
            return agent_id

        except Exception as e:
            logger.exception(f"Failed to create agent: {e}")
            raise RuntimeError(f"Agent creation failed: {e}") from e

    async def execute_task(self, task: TaskConfig) -> ExecutionResult:
        """Execute a single task.

        Args:
            task: Task configuration

        Returns:
            Execution result

        Raises:
            RuntimeError: If task execution fails
        """
        try:
            # Create a simple sequential workflow with one task
            workflow_id = self.orchestrator.create_workflow(
                pattern=WorkflowPattern.SEQUENTIAL,
                tasks=[task],
            )

            # Execute workflow
            workflow_result = await self.orchestrator.execute_workflow(workflow_id)

            # Extract task result
            if workflow_result.task_results:
                task_result = next(iter(workflow_result.task_results.values()))

                # Convert to ExecutionResult
                return ExecutionResult(
                    task_id=task_result.task_id,
                    success=task_result.success,
                    output=task_result.output,
                    error=task_result.error,
                    duration_ms=task_result.duration_ms,
                    metadata=task_result.metadata,
                )
            return ExecutionResult(
                task_id="unknown",
                success=False,
                error="No task results generated",
            )

        except Exception as e:
            logger.exception(f"Task execution failed: {e}")
            return ExecutionResult(
                task_id=task.metadata.get("task_id", "unknown")
                if task.metadata
                else "unknown",
                success=False,
                error=str(e),
            )

    async def execute_workflow(self, tasks: list[TaskConfig]) -> list[ExecutionResult]:
        """Execute a workflow of tasks.

        Args:
            tasks: List of task configurations

        Returns:
            List of execution results

        Raises:
            RuntimeError: If workflow execution fails
        """
        try:
            # Determine pattern based on task dependencies
            has_dependencies = any(task.dependencies for task in tasks)
            pattern = (
                WorkflowPattern.PARALLEL
                if has_dependencies
                else WorkflowPattern.SEQUENTIAL
            )

            # Create workflow
            workflow_id = self.orchestrator.create_workflow(
                pattern=pattern,
                tasks=tasks,
            )

            # Execute workflow
            workflow_result = await self.orchestrator.execute_workflow(workflow_id)

            # Convert task results to ExecutionResults
            results: list[ExecutionResult] = []
            for task_result in workflow_result.task_results.values():
                results.append(
                    ExecutionResult(
                        task_id=task_result.task_id,
                        success=task_result.success,
                        output=task_result.output,
                        error=task_result.error,
                        duration_ms=task_result.duration_ms,
                        metadata=task_result.metadata,
                    ),
                )

            logger.info(f"Workflow executed: {len(results)} tasks completed")
            return results

        except Exception as e:
            logger.exception(f"Workflow execution failed: {e}")
            raise RuntimeError(f"Workflow execution failed: {e}") from e

    async def get_agent_status(self, agent_id: str) -> dict[str, Any]:
        """Get agent status.

        Args:
            agent_id: Agent identifier

        Returns:
            Dictionary with agent status information

        Raises:
            ValueError: If agent not found
        """
        try:
            agent_state = await self.orchestrator.agent_pool.get_agent_state(agent_id)

            if not agent_state:
                raise ValueError(f"Agent {agent_id} not found")

            return {
                "agent_id": agent_state.agent_id,
                "name": agent_state.name,
                "status": agent_state.status.value,
                "current_task": agent_state.current_task,
                "tasks_completed": agent_state.tasks_completed,
                "tasks_failed": agent_state.tasks_failed,
                "total_execution_time_ms": agent_state.total_execution_time_ms,
                "created_at": agent_state.created_at.isoformat(),
                "last_active_at": agent_state.last_active_at.isoformat(),
                "metadata": agent_state.metadata,
            }

        except ValueError:
            raise
        except Exception as e:
            logger.exception(f"Failed to get agent status: {e}")
            raise RuntimeError(f"Failed to get agent status: {e}") from e

    async def shutdown(self) -> None:
        """
        Shutdown the orchestrator and clean up resources.
        """
        await self.orchestrator.shutdown()
        logger.info("OrchestratorPortAdapter shut down")


__all__ = ["OrchestratorPortAdapter"]
