"""CrewAI Framework Adapter.

This module provides integration with the CrewAI framework for multi-agent
orchestration. It implements the FrameworkAdapterPort protocol.

CrewAI is a framework for orchestrating role-playing, autonomous AI agents.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from ..orchestration import (
    FrameworkConfig,
    WorkflowConfig,
    WorkflowPattern,
)

if TYPE_CHECKING:
    from ...ports import AgentConfig, TaskConfig

logger = logging.getLogger(__name__)


class CrewAIAdapter:
    """
    Adapter for CrewAI framework integration.
    """

    def __init__(self, config: FrameworkConfig):
        """Initialize CrewAI adapter.

        Args:
            config: Framework configuration
        """
        self.config = config
        self.tool_registry = config.tool_registry or {}
        self.agents: dict[str, Any] = {}
        self.tasks: list[Any] = []
        self._crewai_available = self._check_availability()

    def _check_availability(self) -> bool:
        """Check if CrewAI is available.

        Returns:
            True if CrewAI can be imported
        """
        try:
            import crewai  # noqa: F401

            return True
        except ImportError:
            logger.warning("CrewAI not installed. Install with: pip install crewai>=0.80.0")
            return False

    def get_framework_name(self) -> str:
        """Get the framework name.

        Returns:
            Framework name string
        """
        return "crewai"

    async def create_agent(self, config: AgentConfig) -> Any:
        """Create a CrewAI agent.

        Args:
            config: Agent configuration

        Returns:
            CrewAI Agent instance

        Raises:
            ImportError: If CrewAI is not available
            RuntimeError: If agent creation fails
        """
        if not self._crewai_available:
            raise ImportError(
                "CrewAI is not available. Please install it: pip install crewai>=0.80.0",
            )

        try:
            from crewai import Agent

            # Resolve tools from registry
            agent_tools = self._resolve_tools(config.tools or [])

            # Build LLM config
            llm_config = self.config.config.get("llm_config", {})

            # Create agent
            agent = Agent(
                role=config.role,
                goal=config.goal,
                backstory=config.backstory or "",
                tools=agent_tools,
                allow_delegation=self.config.allow_delegation,
                verbose=self.config.verbose,
                llm=llm_config.get("model"),
            )

            # Store agent reference
            self.agents[config.name] = agent
            logger.info(f"Created CrewAI agent: {config.name} with {len(agent_tools)} tools")

            return agent

        except Exception as e:
            logger.exception(f"Failed to create agent {config.name}: {e}")
            raise RuntimeError(f"Failed to create agent: {e}") from e

    async def create_task(self, config: TaskConfig, agent: Any) -> Any:
        """Create a CrewAI task.

        Args:
            config: Task configuration
            agent: CrewAI Agent instance

        Returns:
            CrewAI Task instance

        Raises:
            ImportError: If CrewAI is not available
            RuntimeError: If task creation fails
        """
        if not self._crewai_available:
            raise ImportError("CrewAI is not available")

        try:
            from crewai import Task

            # Resolve context tasks (dependencies)
            context_tasks = []
            if config.dependencies:
                for _dep_id in config.dependencies:
                    # Look up dependency task
                    # In practice, tasks would be stored and looked up
                    pass

            # Create task
            task = Task(
                description=config.description,
                agent=agent,
                expected_output=config.expected_output or "Task completion result",
                context=context_tasks if context_tasks else None,
                async_execution=False,  # Handled by orchestrator
            )

            # Store task reference
            self.tasks.append(task)
            logger.info(f"Created task for agent {agent.role}: {config.description[:50]}...")

            return task

        except Exception as e:
            logger.exception(f"Failed to create task: {e}")
            raise RuntimeError(f"Failed to create task: {e}") from e

    async def execute_task(self, task: Any, context: dict[str, Any]) -> Any:
        """Execute a CrewAI task.

        Args:
            task: CrewAI Task instance
            context: Execution context with input variables

        Returns:
            Task execution result

        Raises:
            RuntimeError: If task execution fails
        """
        try:
            # Execute task synchronously (CrewAI is sync)
            # Run in thread pool to not block async loop
            return await asyncio.to_thread(task.execute, context=context)


        except Exception as e:
            logger.exception(f"Task execution failed: {e}")
            raise RuntimeError(f"Task execution failed: {e}") from e

    async def execute_workflow(
        self,
        agents: list[Any],
        tasks: list[Any],
        pattern: WorkflowPattern,
        config: WorkflowConfig,
    ) -> dict[str, Any]:
        """Execute a complete CrewAI workflow.

        Args:
            agents: List of CrewAI Agent instances
            tasks: List of CrewAI Task instances
            pattern: Workflow pattern (sequential/hierarchical)
            config: Workflow configuration

        Returns:
            Workflow execution result

        Raises:
            ImportError: If CrewAI is not available
            RuntimeError: If workflow execution fails
        """
        if not self._crewai_available:
            raise ImportError("CrewAI is not available")

        try:
            from crewai import Crew

            # Map workflow pattern to CrewAI process
            if pattern == WorkflowPattern.SEQUENTIAL:
                process = "sequential"
            elif pattern == WorkflowPattern.HIERARCHICAL:
                process = "hierarchical"
            else:
                # CrewAI only supports sequential and hierarchical
                process = "sequential"
                logger.warning(
                    f"Pattern {pattern} not natively supported by CrewAI, "
                    f"falling back to sequential",
                )

            # Create crew
            crew = Crew(
                agents=agents,
                tasks=tasks,
                process=process,
                verbose=self.config.verbose,
            )

            logger.info(f"Created crew with {len(agents)} agents and {len(tasks)} tasks")

            # Execute crew
            result = await asyncio.to_thread(crew.kickoff, inputs={})

            # Extract task results
            task_results = {}
            for idx, task in enumerate(crew.tasks):
                task_results[f"task_{idx}"] = {
                    "description": task.description,
                    "output": getattr(task, "output", None),
                    "agent": task.agent.role if hasattr(task, "agent") else None,
                }

            return {
                "status": "success",
                "output": result,
                "task_results": task_results,
                "metadata": {
                    "agents_count": len(crew.agents),
                    "tasks_count": len(crew.tasks),
                },
            }

        except Exception as e:
            logger.exception(f"Crew execution failed: {e}")
            return {
                "status": "error",
                "output": None,
                "task_results": {},
                "metadata": {"error": str(e)},
            }

    def _resolve_tools(self, tool_names: list[str]) -> list[Any]:
        """Resolve tool names to actual tool functions.

        Args:
            tool_names: List of tool names to resolve

        Returns:
            List of tool functions/callables
        """
        resolved = []
        for name in tool_names:
            # Try to get from registry
            tool_entry = self.tool_registry.get(name)
            if tool_entry:
                # Handle different registry formats
                if callable(tool_entry):
                    resolved.append(tool_entry)
                elif isinstance(tool_entry, dict) and "function" in tool_entry:
                    resolved.append(tool_entry["function"])
                else:
                    logger.warning(f"Tool '{name}' found but not in expected format")
            else:
                logger.warning(f"Tool '{name}' not found in registry")

        return resolved

    def integrate_with_langgraph(self, crew: Any) -> dict[str, Any]:
        """Create LangGraph integration points for a crew.

        This method generates a LangGraph-compatible node definition that can be
        integrated into existing LangGraph workflows.

        Args:
            crew: CrewAI Crew instance

        Returns:
            LangGraph node configuration
        """

        async def crew_node(state: dict[str, Any]) -> dict[str, Any]:
            """
            LangGraph node that executes the crew.
            """
            result = await asyncio.to_thread(crew.kickoff, inputs=state)

            # Extract task results
            task_results = {}
            for idx, task in enumerate(crew.tasks):
                task_results[f"task_{idx}"] = {
                    "description": task.description,
                    "output": getattr(task, "output", None),
                    "agent": task.agent.role if hasattr(task, "agent") else None,
                }

            return {
                "crew_output": result,
                "crew_status": "success",
                "task_results": task_results,
                "metadata": {
                    "agents_count": len(crew.agents),
                    "tasks_count": len(crew.tasks),
                },
            }

        return {
            "node_name": "crewai_execution",
            "node_function": crew_node,
            "description": "Execute CrewAI crew as part of LangGraph workflow",
            "input_keys": ["task_description", "context"],
            "output_keys": ["crew_output", "crew_status", "task_results", "metadata"],
        }


__all__ = ["CrewAIAdapter"]
