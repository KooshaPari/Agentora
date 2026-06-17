"""AutoGen Framework Adapter.

This module provides integration with the AutoGen framework for multi-agent
orchestration. It implements the FrameworkAdapterPort protocol.

AutoGen is a framework for building LLM applications with multiple conversational agents
that can work together to solve tasks. It supports different agent types including
AssistantAgent, UserProxyAgent, and GroupChat for multi-agent conversations.

Key Features:
- Multi-agent conversations
- Human-in-the-loop interactions
- Code execution capabilities
- Group chat orchestration
- Flexible agent configurations

Example:
    ```python
    from pheno.mcp.agents.orchestration import Orchestrator, WorkflowPattern
    from pheno.mcp.ports import AgentConfig, TaskConfig

    # Create orchestrator with AutoGen
    orchestrator = Orchestrator(framework="autogen")

    # Create agents
    agent_id = await orchestrator.create_agent(
        name="assistant",
        role="Coding Assistant",
        goal="Help write and review code"
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


class AutoGenAdapter:
    """Adapter for AutoGen framework integration.

    This adapter provides integration between pheno-sdk's orchestration layer and
    AutoGen's conversational multi-agent system.
    """

    def __init__(self, config: FrameworkConfig):
        """Initialize AutoGen adapter.

        Args:
            config: Framework configuration
        """
        self.config = config
        self.tool_registry = config.tool_registry or {}
        self.agents: dict[str, Any] = {}
        self.group_chats: dict[str, Any] = {}
        self._autogen_available = self._check_availability()

        if self._autogen_available:
            logger.info("AutoGen adapter initialized successfully")
        else:
            logger.warning("AutoGen not installed. Install with: pip install pyautogen>=0.2.0")

    def _check_availability(self) -> bool:
        """Check if AutoGen is available.

        Returns:
            True if AutoGen can be imported
        """
        try:
            import autogen  # noqa: F401

            return True
        except ImportError:
            return False

    def get_framework_name(self) -> str:
        """Get the framework name.

        Returns:
            Framework name string
        """
        return "autogen"

    async def create_agent(self, config: AgentConfig) -> Any:
        """Create an AutoGen conversational agent.

        Creates either an AssistantAgent or UserProxyAgent based on the role
        and configuration.

        Args:
            config: Agent configuration

        Returns:
            AutoGen agent instance

        Raises:
            ImportError: If AutoGen is not available
            RuntimeError: If agent creation fails
        """
        if not self._autogen_available:
            raise ImportError(
                "AutoGen is not available. Please install it: pip install pyautogen>=0.2.0",
            )

        try:
            from autogen import AssistantAgent, UserProxyAgent

            # Resolve tools from registry
            agent_tools = self._resolve_tools(config.tools or [])

            # Build LLM config
            llm_config = self._build_llm_config()

            # Build system message
            system_message = self._build_system_message(config)

            # Determine agent type based on role
            is_user_proxy = "proxy" in config.role.lower() or "user" in config.role.lower()

            if is_user_proxy:
                # Create UserProxyAgent
                agent = UserProxyAgent(
                    name=config.name,
                    system_message=system_message,
                    code_execution_config=(
                        {
                            "work_dir": "coding",
                            "use_docker": False,  # Can be configured
                        }
                        if self.config.config.get("enable_code_execution", False)
                        else False
                    ),
                    human_input_mode=self.config.config.get("human_input_mode", "NEVER"),
                    max_consecutive_auto_reply=self.config.max_iterations,
                    is_termination_msg=lambda x: x.get("content", "")
                    .rstrip()
                    .endswith("TERMINATE"),
                )
                logger.info(f"Created UserProxyAgent: {config.name}")
            else:
                # Create AssistantAgent
                agent = AssistantAgent(
                    name=config.name,
                    system_message=system_message,
                    llm_config=llm_config,
                    max_consecutive_auto_reply=self.config.max_iterations,
                    is_termination_msg=lambda x: x.get("content", "")
                    .rstrip()
                    .endswith("TERMINATE"),
                )
                logger.info(f"Created AssistantAgent: {config.name} with LLM config")

            # Register tools/functions if available
            if agent_tools and hasattr(agent, "register_function"):
                for tool in agent_tools:
                    if callable(tool):
                        agent.register_function(function_map={tool.__name__: tool})

            # Store agent reference
            self.agents[config.name] = {
                "agent": agent,
                "config": config,
                "tools": agent_tools,
            }

            return agent

        except Exception as e:
            logger.exception(f"Failed to create agent {config.name}: {e}")
            raise RuntimeError(f"Failed to create agent: {e}") from e

    async def create_task(self, config: TaskConfig, agent: Any) -> Any:
        """Create an AutoGen task.

        In AutoGen, tasks are represented as messages to be sent to agents.

        Args:
            config: Task configuration
            agent: AutoGen agent instance

        Returns:
            Task configuration

        Raises:
            ImportError: If AutoGen is not available
            RuntimeError: If task creation fails
        """
        if not self._autogen_available:
            raise ImportError("AutoGen is not available")

        try:
            # Create task representation
            task_data = {
                "message": config.description,
                "agent": agent,
                "config": config,
                "expected_output": config.expected_output,
            }

            logger.info(f"Created AutoGen task for agent {agent.name}")

            return task_data

        except Exception as e:
            logger.exception(f"Failed to create task: {e}")
            raise RuntimeError(f"Failed to create task: {e}") from e

    async def execute_task(self, task: Any, context: dict[str, Any]) -> Any:
        """Execute an AutoGen task.

        Args:
            task: AutoGen task configuration
            context: Execution context with input variables

        Returns:
            Task execution result

        Raises:
            RuntimeError: If task execution fails
        """
        try:
            agent = task["agent"]
            message = task["message"]

            # Format message with context if needed
            if context:
                try:
                    formatted_message = message.format(**context)
                except KeyError:
                    formatted_message = message

            # Execute task by generating a reply
            # For single task execution, we use generate_reply
            return await asyncio.to_thread(
                agent.generate_reply, messages=[{"content": formatted_message, "role": "user"}],
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
        """Execute a complete AutoGen workflow.

        This creates either a sequential conversation or a GroupChat based on the pattern.

        Args:
            agents: List of AutoGen agent instances
            tasks: List of AutoGen task configurations
            pattern: Workflow pattern (sequential/hierarchical/parallel)
            config: Workflow configuration

        Returns:
            Workflow execution result

        Raises:
            ImportError: If AutoGen is not available
            RuntimeError: If workflow execution fails
        """
        if not self._autogen_available:
            raise ImportError("AutoGen is not available")

        try:

            # Extract actual agent instances
            agent_instances = [agent for agent in agents if hasattr(agent, "name")]

            if pattern == WorkflowPattern.SEQUENTIAL:
                # Sequential execution - agents take turns
                result = await self._execute_sequential_conversation(agent_instances, tasks, config)

            elif pattern == WorkflowPattern.HIERARCHICAL:
                # Hierarchical - first agent is manager, others are workers
                result = await self._execute_hierarchical_groupchat(agent_instances, tasks, config)

            elif pattern == WorkflowPattern.PARALLEL:
                # Parallel - all agents can contribute
                result = await self._execute_parallel_groupchat(agent_instances, tasks, config)

            elif pattern == WorkflowPattern.CONDITIONAL:
                # Conditional - agents selected based on conditions
                result = await self._execute_conditional_groupchat(agent_instances, tasks, config)

            else:
                raise ValueError(f"Unsupported pattern: {pattern}")

            logger.info(f"AutoGen workflow completed with {len(agent_instances)} agents")

            return result

        except Exception as e:
            logger.exception(f"AutoGen workflow execution failed: {e}")
            return {
                "status": "error",
                "output": None,
                "task_results": {},
                "metadata": {"error": str(e)},
            }

    async def _execute_sequential_conversation(
        self,
        agents: list[Any],
        tasks: list[Any],
        config: WorkflowConfig,
    ) -> dict[str, Any]:
        """Execute sequential conversation between agents.

        Args:
            agents: List of AutoGen agents
            tasks: List of tasks
            config: Workflow configuration

        Returns:
            Workflow result
        """
        if not agents or not tasks:
            return {
                "status": "success",
                "output": None,
                "task_results": {},
                "metadata": {},
            }

        # Use first agent as initiator
        initiator = agents[0]
        recipient = agents[1] if len(agents) > 1 else agents[0]

        # Combine task messages
        message = "\n\n".join([task["message"] for task in tasks])

        # Execute conversation
        chat_result = await asyncio.to_thread(
            initiator.initiate_chat,
            recipient,
            message=message,
            max_turns=self.config.max_iterations,
        )

        # Extract results
        task_results = {}
        for i, task in enumerate(tasks):
            task_results[f"task_{i}"] = {
                "description": task["config"].description,
                "output": (
                    chat_result.chat_history[-1].get("content")
                    if chat_result.chat_history
                    else None
                ),
                "agent": task["agent"].name,
            }

        return {
            "status": "success",
            "output": chat_result.summary if hasattr(chat_result, "summary") else None,
            "task_results": task_results,
            "metadata": {
                "chat_history": (
                    chat_result.chat_history if hasattr(chat_result, "chat_history") else []
                ),
                "agents_count": len(agents),
            },
        }

    async def _execute_hierarchical_groupchat(
        self,
        agents: list[Any],
        tasks: list[Any],
        config: WorkflowConfig,
    ) -> dict[str, Any]:
        """Execute hierarchical group chat with manager.

        Args:
            agents: List of AutoGen agents (first is manager)
            tasks: List of tasks
            config: Workflow configuration

        Returns:
            Workflow result
        """
        from autogen import GroupChat, GroupChatManager

        # Create group chat with custom speaker selection
        groupchat = GroupChat(
            agents=agents,
            messages=[],
            max_round=self.config.max_iterations,
            speaker_selection_method="round_robin",  # Can customize
        )

        # First agent is the manager
        manager = GroupChatManager(
            groupchat=groupchat,
            llm_config=self._build_llm_config(),
        )

        # Initiate group chat
        message = "\n\n".join([task["message"] for task in tasks])

        await asyncio.to_thread(
            agents[0].initiate_chat,
            manager,
            message=message,
        )

        # Extract results
        task_results = {}
        for i, task in enumerate(tasks):
            task_results[f"task_{i}"] = {
                "description": task["config"].description,
                "output": groupchat.messages[-1].get("content") if groupchat.messages else None,
                "agent": task["agent"].name,
            }

        return {
            "status": "success",
            "output": groupchat.messages[-1].get("content") if groupchat.messages else None,
            "task_results": task_results,
            "metadata": {
                "messages": groupchat.messages,
                "agents_count": len(agents),
            },
        }

    async def _execute_parallel_groupchat(
        self,
        agents: list[Any],
        tasks: list[Any],
        config: WorkflowConfig,
    ) -> dict[str, Any]:
        """Execute parallel group chat where all agents can contribute.

        Args:
            agents: List of AutoGen agents
            tasks: List of tasks
            config: Workflow configuration

        Returns:
            Workflow result
        """
        from autogen import GroupChat, GroupChatManager

        # Create group chat allowing all agents to speak
        groupchat = GroupChat(
            agents=agents,
            messages=[],
            max_round=self.config.max_iterations,
            speaker_selection_method="auto",  # Automatic speaker selection
        )

        manager = GroupChatManager(
            groupchat=groupchat,
            llm_config=self._build_llm_config(),
        )

        # Combine all task messages
        message = "\n\n".join([task["message"] for task in tasks])

        # Initiate group chat
        await asyncio.to_thread(
            agents[0].initiate_chat,
            manager,
            message=message,
        )

        # Extract results
        task_results = {}
        for i, task in enumerate(tasks):
            task_results[f"task_{i}"] = {
                "description": task["config"].description,
                "output": groupchat.messages[-1].get("content") if groupchat.messages else None,
                "agent": task["agent"].name,
            }

        return {
            "status": "success",
            "output": groupchat.messages[-1].get("content") if groupchat.messages else None,
            "task_results": task_results,
            "metadata": {
                "messages": groupchat.messages,
                "agents_count": len(agents),
            },
        }

    async def _execute_conditional_groupchat(
        self,
        agents: list[Any],
        tasks: list[Any],
        config: WorkflowConfig,
    ) -> dict[str, Any]:
        """Execute conditional group chat with custom speaker selection.

        Args:
            agents: List of AutoGen agents
            tasks: List of tasks
            config: Workflow configuration

        Returns:
            Workflow result
        """
        from autogen import GroupChat, GroupChatManager

        # Define custom speaker selection function
        def custom_speaker_selection(last_speaker, groupchat):
            """
            Custom logic for selecting next speaker based on conditions.
            """
            # Simple round-robin for now - can be enhanced with task dependencies
            messages = groupchat.messages
            if not messages:
                return agents[0]

            # Find current speaker index
            current_idx = agents.index(last_speaker) if last_speaker in agents else 0
            next_idx = (current_idx + 1) % len(agents)
            return agents[next_idx]

        # Create group chat with custom selection
        groupchat = GroupChat(
            agents=agents,
            messages=[],
            max_round=self.config.max_iterations,
            speaker_selection_method=custom_speaker_selection,
        )

        manager = GroupChatManager(
            groupchat=groupchat,
            llm_config=self._build_llm_config(),
        )

        # Combine task messages
        message = "\n\n".join([task["message"] for task in tasks])

        # Execute
        await asyncio.to_thread(
            agents[0].initiate_chat,
            manager,
            message=message,
        )

        # Extract results
        task_results = {}
        for i, task in enumerate(tasks):
            task_results[f"task_{i}"] = {
                "description": task["config"].description,
                "output": groupchat.messages[-1].get("content") if groupchat.messages else None,
                "agent": task["agent"].name,
            }

        return {
            "status": "success",
            "output": groupchat.messages[-1].get("content") if groupchat.messages else None,
            "task_results": task_results,
            "metadata": {
                "messages": groupchat.messages,
                "agents_count": len(agents),
            },
        }

    def _build_llm_config(self) -> dict[str, Any]:
        """Build LLM configuration for AutoGen.

        Returns:
            LLM configuration dictionary
        """
        llm_config = self.config.config.get("llm_config", {})

        # Default configuration
        default_config = {
            "timeout": self.config.timeout_seconds,
            "cache_seed": 42,  # For caching
            "config_list": [
                {
                    "model": llm_config.get("model", "gpt-4"),
                    "api_key": llm_config.get("api_key", ""),
                },
            ],
            "temperature": llm_config.get("temperature", 0),
        }

        # Merge with provided config
        return {**default_config, **llm_config}

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

        parts.append("Reply 'TERMINATE' when the task is complete.")

        return "\n\n".join(parts)

    def _resolve_tools(self, tool_names: list[str]) -> list[Any]:
        """Resolve tool names to callable functions.

        Args:
            tool_names: List of tool names to resolve

        Returns:
            List of callable functions
        """
        resolved = []
        for name in tool_names:
            # Try to get from registry
            tool_entry = self.tool_registry.get(name)
            if tool_entry:
                if callable(tool_entry):
                    resolved.append(tool_entry)
                elif isinstance(tool_entry, dict) and "function" in tool_entry:
                    resolved.append(tool_entry["function"])
                else:
                    logger.warning(f"Tool '{name}' found but not in expected format")
            else:
                logger.warning(f"Tool '{name}' not found in registry")

        return resolved

    def create_teaching_agent(self, student_agent: Any) -> dict[str, Any]:
        """Create a teaching configuration where one agent teaches another.

        This is a special AutoGen pattern for knowledge transfer.

        Args:
            student_agent: The agent that will learn

        Returns:
            Teaching configuration
        """
        if not self._autogen_available:
            logger.warning("AutoGen not available for teaching agent")
            return {}

        try:
            from autogen import AssistantAgent

            # Create teacher agent
            teacher = AssistantAgent(
                name="teacher",
                system_message="You are a patient teacher. Explain concepts clearly and check understanding.",
                llm_config=self._build_llm_config(),
            )

            return {
                "teacher": teacher,
                "student": student_agent,
                "pattern": "teaching",
                "description": "One-on-one teaching session",
            }

        except Exception as e:
            logger.exception(f"Failed to create teaching agent: {e}")
            return {}


__all__ = ["AutoGenAdapter"]
