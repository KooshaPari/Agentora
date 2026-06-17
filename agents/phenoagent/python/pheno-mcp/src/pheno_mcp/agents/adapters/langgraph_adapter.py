"""LangGraph Framework Adapter.

This module provides integration with the LangGraph framework for multi-agent
orchestration. It implements the FrameworkAdapterPort protocol.

LangGraph is a framework for building stateful, multi-actor applications with LLMs.
It uses a graph-based approach where nodes represent computation and edges represent
data flow between computations.

Key Features:
- State management with typed state schemas
- Graph-based workflow definition
- Conditional routing and cycles
- Checkpointing and persistence
- Human-in-the-loop support

Example:
    ```python
    from pheno.mcp.agents.orchestration import Orchestrator, WorkflowPattern
    from pheno.mcp.ports import AgentConfig, TaskConfig

    # Create orchestrator with LangGraph
    orchestrator = Orchestrator(framework="langgraph")

    # Create agents
    agent_id = await orchestrator.create_agent(
        name="researcher",
        role="Research Assistant",
        goal="Research and analyze topics"
    )

    # Create and execute workflow
    workflow_id = orchestrator.create_workflow(
        pattern=WorkflowPattern.SEQUENTIAL,
        tasks=[task1, task2]
    )
    result = await orchestrator.execute_workflow(workflow_id)
    ```
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


class LangGraphAdapter:
    """Adapter for LangGraph framework integration.

    This adapter provides integration between pheno-sdk's orchestration layer and
    LangGraph's graph-based workflow system.
    """

    def __init__(self, config: FrameworkConfig):
        """Initialize LangGraph adapter.

        Args:
            config: Framework configuration
        """
        self.config = config
        self.tool_registry = config.tool_registry or {}
        self.agents: dict[str, Any] = {}
        self.graphs: dict[str, Any] = {}
        self._langgraph_available = self._check_availability()

        if self._langgraph_available:
            logger.info("LangGraph adapter initialized successfully")
        else:
            logger.warning("LangGraph not installed. Install with: pip install langgraph>=0.1.0")

    def _check_availability(self) -> bool:
        """Check if LangGraph is available.

        Returns:
            True if LangGraph can be imported
        """
        try:
            import langgraph  # noqa: F401

            return True
        except ImportError:
            return False

    def get_framework_name(self) -> str:
        """Get the framework name.

        Returns:
            Framework name string
        """
        return "langgraph"

    async def create_agent(self, config: AgentConfig) -> Any:
        """Create a LangGraph agent node.

        In LangGraph, an "agent" is typically a node in the graph that performs
        agent-like behavior (calling tools, making decisions, etc.).

        Args:
            config: Agent configuration

        Returns:
            Agent node configuration

        Raises:
            ImportError: If LangGraph is not available
            RuntimeError: If agent creation fails
        """
        if not self._langgraph_available:
            raise ImportError(
                "LangGraph is not available. Please install it: pip install langgraph>=0.1.0",
            )

        try:
            from langchain_core.messages import SystemMessage

            # Resolve tools from registry
            agent_tools = self._resolve_tools(config.tools or [])

            # Build system message from config
            system_message = self._build_system_message(config)

            # Create agent node function
            async def agent_node(state: dict[str, Any]) -> dict[str, Any]:
                """
                Agent node that processes state and returns updates.
                """
                messages = state.get("messages", [])

                # Add system message if not present
                if not messages or not isinstance(messages[0], SystemMessage):
                    messages = [SystemMessage(content=system_message), *messages]

                # Get LLM from config
                llm_config = self.config.config.get("llm_config", {})
                llm = llm_config.get("model")

                if not llm:
                    # Create default LLM if none provided
                    from langchain_openai import ChatOpenAI

                    llm = ChatOpenAI(temperature=0)

                # Bind tools to LLM if available
                if agent_tools:
                    llm = llm.bind_tools(agent_tools)

                # Invoke LLM
                response = await llm.ainvoke(messages)

                # Update state with response
                return {
                    "messages": [*messages, response],
                    "agent_output": (
                        response.content if hasattr(response, "content") else str(response)
                    ),
                }

            # Store agent configuration
            agent_data = {
                "node_function": agent_node,
                "config": config,
                "tools": agent_tools,
                "system_message": system_message,
            }

            self.agents[config.name] = agent_data

            logger.info(
                f"Created LangGraph agent node: {config.name} with {len(agent_tools)} tools",
            )

            return agent_data

        except Exception as e:
            logger.exception(f"Failed to create agent {config.name}: {e}")
            raise RuntimeError(f"Failed to create agent: {e}") from e

    async def create_task(self, config: TaskConfig, agent: Any) -> Any:
        """Create a LangGraph task.

        In LangGraph, a task is represented as a node invocation with specific inputs.

        Args:
            config: Task configuration
            agent: LangGraph agent node configuration

        Returns:
            Task configuration

        Raises:
            ImportError: If LangGraph is not available
            RuntimeError: If task creation fails
        """
        if not self._langgraph_available:
            raise ImportError("LangGraph is not available")

        try:
            from langchain_core.messages import HumanMessage

            # Create task function
            async def task_function(state: dict[str, Any]) -> dict[str, Any]:
                """
                Task function that invokes the agent with task description.
                """
                # Add task description as a message
                messages = state.get("messages", [])
                task_message = HumanMessage(content=config.description)
                messages.append(task_message)

                # Update state with task message
                task_state = state.copy()
                task_state["messages"] = messages

                # Invoke agent node
                return await agent["node_function"](task_state)


            task_data = {
                "function": task_function,
                "config": config,
                "agent": agent,
            }

            logger.info(f"Created LangGraph task for agent {agent['config'].name}")

            return task_data

        except Exception as e:
            logger.exception(f"Failed to create task: {e}")
            raise RuntimeError(f"Failed to create task: {e}") from e

    async def execute_task(self, task: Any, context: dict[str, Any]) -> Any:
        """Execute a LangGraph task.

        Args:
            task: LangGraph task configuration
            context: Execution context with input variables

        Returns:
            Task execution result

        Raises:
            RuntimeError: If task execution fails
        """
        try:
            # Build initial state from context
            state = context.copy()
            if "messages" not in state:
                state["messages"] = []

            # Execute task function
            result = await task["function"](state)

            # Extract output
            return result.get(
                "agent_output", result.get("messages", [])[-1] if result.get("messages") else None,
            )


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
        """Execute a complete LangGraph workflow.

        This creates a StateGraph that represents the workflow and executes it.

        Args:
            agents: List of LangGraph agent configurations
            tasks: List of LangGraph task configurations
            pattern: Workflow pattern (sequential/parallel/hierarchical/conditional)
            config: Workflow configuration

        Returns:
            Workflow execution result

        Raises:
            ImportError: If LangGraph is not available
            RuntimeError: If workflow execution fails
        """
        if not self._langgraph_available:
            raise ImportError("LangGraph is not available")

        try:
            from langgraph.graph import END, StateGraph
            from typing_extensions import TypedDict

            # Define state schema
            class WorkflowState(TypedDict):
                """
                State schema for the workflow.
                """

                messages: list
                task_outputs: dict
                current_task: int
                completed: bool

            # Create state graph
            graph = StateGraph(WorkflowState)

            # Add nodes based on pattern
            if pattern == WorkflowPattern.SEQUENTIAL:
                # Add tasks sequentially
                for i, task in enumerate(tasks):
                    node_name = f"task_{i}"
                    graph.add_node(node_name, task["function"])

                # Add sequential edges
                graph.set_entry_point("task_0")
                for i in range(len(tasks) - 1):
                    graph.add_edge(f"task_{i}", f"task_{i+1}")
                graph.add_edge(f"task_{len(tasks)-1}", END)

            elif pattern == WorkflowPattern.PARALLEL:
                # Add a dispatcher node
                async def dispatcher(state: WorkflowState) -> WorkflowState:
                    """
                    Dispatch to parallel tasks.
                    """
                    return state

                graph.add_node("dispatcher", dispatcher)
                graph.set_entry_point("dispatcher")

                # Add parallel task nodes
                for i, task in enumerate(tasks):
                    node_name = f"task_{i}"
                    graph.add_node(node_name, task["function"])
                    graph.add_edge("dispatcher", node_name)
                    graph.add_edge(node_name, END)

            elif pattern == WorkflowPattern.HIERARCHICAL:
                # First task is manager
                if tasks:
                    graph.add_node("manager", tasks[0]["function"])
                    graph.set_entry_point("manager")

                    # Add worker nodes
                    for i, task in enumerate(tasks[1:], start=1):
                        node_name = f"worker_{i}"
                        graph.add_node(node_name, task["function"])
                        graph.add_edge("manager", node_name)
                        graph.add_edge(node_name, END)

            elif pattern == WorkflowPattern.CONDITIONAL:
                # Add tasks with conditional routing
                for i, task in enumerate(tasks):
                    node_name = f"task_{i}"
                    graph.add_node(node_name, task["function"])

                # Add conditional edges (simplified - actual conditions would be in task config)
                if tasks:
                    graph.set_entry_point("task_0")
                    for i in range(len(tasks) - 1):
                        # In real implementation, this would check task conditions
                        graph.add_edge(f"task_{i}", f"task_{i+1}")
                    graph.add_edge(f"task_{len(tasks)-1}", END)

            else:
                raise ValueError(f"Unsupported pattern: {pattern}")

            # Compile graph
            compiled_graph = graph.compile()

            logger.info(
                f"Created LangGraph workflow with {len(tasks)} tasks using {pattern.value} pattern",
            )

            # Execute graph
            initial_state: WorkflowState = {
                "messages": [],
                "task_outputs": {},
                "current_task": 0,
                "completed": False,
            }

            # Run graph
            final_state = await compiled_graph.ainvoke(initial_state)

            # Extract results
            task_results = {}
            for i, task in enumerate(tasks):
                task_key = f"task_{i}"
                task_results[task_key] = {
                    "description": task["config"].description,
                    "output": final_state.get("task_outputs", {}).get(task_key),
                    "agent": task["agent"]["config"].name if "agent" in task else None,
                }

            return {
                "status": "success",
                "output": (
                    final_state.get("messages", [])[-1] if final_state.get("messages") else None
                ),
                "task_results": task_results,
                "metadata": {
                    "pattern": pattern.value,
                    "tasks_count": len(tasks),
                    "final_state": final_state,
                },
            }

        except Exception as e:
            logger.exception(f"LangGraph workflow execution failed: {e}")
            return {
                "status": "error",
                "output": None,
                "task_results": {},
                "metadata": {"error": str(e)},
            }

    def _resolve_tools(self, tool_names: list[str]) -> list[Any]:
        """Resolve tool names to LangChain tools.

        Args:
            tool_names: List of tool names to resolve

        Returns:
            List of LangChain tool objects
        """
        resolved = []
        for name in tool_names:
            # Try to get from registry
            tool_entry = self.tool_registry.get(name)
            if tool_entry:
                # Convert to LangChain tool if needed
                if callable(tool_entry):
                    # Wrap callable in LangChain tool
                    try:
                        from langchain_core.tools import tool

                        @tool
                        def wrapped_tool(*args, **kwargs):
                            """
                            Tool from registry.
                            """
                            return tool_entry(*args, **kwargs)

                        resolved.append(wrapped_tool)
                    except ImportError:
                        logger.warning(
                            f"Cannot create LangChain tool from '{name}' - langchain not available",
                        )
                elif isinstance(tool_entry, dict) and "function" in tool_entry:
                    # Extract function and wrap
                    try:
                        from langchain_core.tools import tool

                        @tool
                        def wrapped_tool(*args, **kwargs):
                            """
                            Tool from registry.
                            """
                            return tool_entry["function"](*args, **kwargs)

                        resolved.append(wrapped_tool)
                    except ImportError:
                        logger.warning(
                            f"Cannot create LangChain tool from '{name}' - langchain not available",
                        )
                else:
                    # Assume it's already a LangChain tool
                    resolved.append(tool_entry)
            else:
                logger.warning(f"Tool '{name}' not found in registry")

        return resolved

    def _build_system_message(self, config: AgentConfig) -> str:
        """Build system message from agent configuration.

        Args:
            config: Agent configuration

        Returns:
            System message string
        """
        parts = [
            f"You are a {config.role}.",
            f"Your goal: {config.goal}",
        ]

        if config.backstory:
            parts.append(f"Background: {config.backstory}")

        if config.tools:
            parts.append(f"You have access to the following tools: {', '.join(config.tools)}")

        return "\n\n".join(parts)

    def create_langgraph_crew_integration(self, crew_agents: list[Any]) -> dict[str, Any]:
        """Create a LangGraph node that can execute a CrewAI crew.

        This allows hybrid workflows combining LangGraph's graph-based orchestration
        with CrewAI's multi-agent capabilities.

        Args:
            crew_agents: List of CrewAI agents to wrap in a LangGraph node

        Returns:
            LangGraph node configuration
        """
        if not self._langgraph_available:
            logger.warning("LangGraph not available for crew integration")
            return {}

        async def crew_node(state: dict[str, Any]) -> dict[str, Any]:
            """
            LangGraph node that executes CrewAI agents.
            """
            try:
                from crewai import Crew

                # Extract inputs from state
                inputs = state.get("inputs", {})

                # Create and run crew
                crew = Crew(
                    agents=crew_agents,
                    tasks=[],  # Tasks would be derived from state
                    verbose=self.config.verbose,
                )

                result = await asyncio.to_thread(crew.kickoff, inputs=inputs)

                # Update state with crew results
                return {
                    "crew_output": result,
                    "crew_status": "success",
                }

            except Exception as e:
                logger.exception(f"Crew execution in LangGraph node failed: {e}")
                return {
                    "crew_output": None,
                    "crew_status": "error",
                    "error": str(e),
                }

        return {
            "node_name": "crewai_crew",
            "node_function": crew_node,
            "description": "Execute CrewAI crew within LangGraph workflow",
        }


__all__ = ["LangGraphAdapter"]
