"""Agent Manager.

Manages multiple agents with multi-tenancy support, task routing, and agent coordination
capabilities.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ..core.types import (
    AgentCapability,
    AgentType,
    TaskComplexity,
    TaskRequest,
    TaskResult,
    TaskType,
)

logger = logging.getLogger(__name__)


@dataclass
class Agent:
    """
    Represents an individual agent in the system.
    """

    agent_id: str
    agent_type: AgentType
    capabilities: AgentCapability
    status: str = "idle"  # idle, busy, error, offline
    current_task: str | None = None
    tasks_completed: int = 0
    total_execution_time: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TenantContext:
    """
    Represents a tenant's isolated context.
    """

    tenant_id: str
    agents: list[Agent] = field(default_factory=list)
    active_tasks: int = 0
    resource_limits: dict[str, Any] = field(default_factory=dict)
    last_activity: datetime = field(default_factory=datetime.now)


class AgentManager:
    """Manages multiple agents with multi-tenancy support.

    Coordinates agent registration, task routing, and load balancing.
    """

    def __init__(self, config: dict[str, Any]):
        """Initialize the agent manager.

        Args:
            config: Configuration dictionary for agent management
        """
        self.config = config
        self.agents: dict[str, Agent] = {}
        self.tenant_contexts: dict[str, TenantContext] = {}

        # Default resource limits per tenant
        self.default_limits = {
            "max_concurrent_tasks": config.get("max_concurrent_tasks", 5),
            "max_agents": config.get("max_agents", 10),
            "task_timeout": config.get("task_timeout", 3600),  # 1 hour
        }

        # Agent registry
        self._agent_capabilities: dict[AgentType, list[str]] = {}

        logger.info("Agent Manager initialized")

    async def register_agent(
        self, agent_type: AgentType, capabilities: AgentCapability, tenant_id: str | None = None,
    ) -> str:
        """Register a new agent in the system.

        Args:
            agent_type: Type of agent to register
            capabilities: Capabilities of the agent
            tenant_id: Optional tenant ID for tenant-specific agents

        Returns:
            Agent ID
        """
        agent_id = f"{agent_type.value}_{len(self.agents)}_{asyncio.get_event_loop().time()}"

        agent = Agent(
            agent_id=agent_id, agent_type=agent_type, capabilities=capabilities, status="idle",
        )

        self.agents[agent_id] = agent

        # Register in tenant context if provided
        if tenant_id:
            context = await self._get_or_create_tenant_context(tenant_id)
            context.agents.append(agent)

        # Update agent capabilities registry
        if agent_type not in self._agent_capabilities:
            self._agent_capabilities[agent_type] = []
        self._agent_capabilities[agent_type].append(agent_id)

        logger.info(f"Registered agent {agent_id} of type {agent_type.value}")
        return agent_id

    async def deregister_agent(self, agent_id: str):
        """Deregister an agent from the system.

        Args:
            agent_id: ID of the agent to deregister
        """
        if agent_id not in self.agents:
            logger.warning(f"Agent {agent_id} not found for deregistration")
            return

        agent = self.agents[agent_id]

        # Remove from capabilities registry
        if agent.agent_type in self._agent_capabilities:
            self._agent_capabilities[agent.agent_type].remove(agent_id)

        # Remove from tenant contexts
        for context in self.tenant_contexts.values():
            context.agents = [a for a in context.agents if a.agent_id != agent_id]

        del self.agents[agent_id]
        logger.info(f"Deregistered agent {agent_id}")

    async def route_task(self, task: TaskRequest) -> str:
        """Route a task to the most appropriate agent.

        Args:
            task: Task to route

        Returns:
            Agent ID selected for the task
        """
        # Get tenant context
        if task.tenant_id:
            context = await self._get_or_create_tenant_context(task.tenant_id)

            # Check resource limits
            if context.active_tasks >= context.resource_limits["max_concurrent_tasks"]:
                raise Exception(
                    f"Tenant {task.tenant_id} has reached maximum concurrent tasks limit",
                )

        # Find suitable agents for this task type
        suitable_agents = await self._find_suitable_agents(task)

        if not suitable_agents:
            raise Exception(f"No suitable agents found for task type: {task.task_type.value}")

        # Select best agent based on load balancing
        selected_agent = await self._select_best_agent(suitable_agents, task)

        logger.info(f"Routed task {task.task_id} to agent {selected_agent.agent_id}")
        return selected_agent.agent_id

    async def _find_suitable_agents(self, task: TaskRequest) -> list[Agent]:
        """Find agents suitable for a task.

        Args:
            task: Task to find agents for

        Returns:
            List of suitable agents
        """
        suitable = []

        for agent in self.agents.values():
            # Check if agent supports this task type
            if task.task_type not in agent.capabilities.supported_task_types:
                continue

            # Check if agent can handle complexity
            complexity = task.estimated_complexity or TaskComplexity.MEDIUM
            if self._complexity_level(complexity) > self._complexity_level(
                agent.capabilities.max_complexity,
            ):
                continue

            # Check if agent is available
            if agent.status == "idle":
                suitable.append(agent)

        return suitable

    def _complexity_level(self, complexity: TaskComplexity) -> int:
        """
        Get numeric level for complexity comparison.
        """
        levels = {TaskComplexity.SIMPLE: 1, TaskComplexity.MEDIUM: 2, TaskComplexity.COMPLEX: 3}
        return levels.get(complexity, 2)

    async def _select_best_agent(self, agents: list[Agent], task: TaskRequest) -> Agent:
        """Select the best agent from suitable candidates.

        Args:
            agents: List of suitable agents
            task: Task to assign

        Returns:
            Selected agent
        """
        if not agents:
            raise Exception("No agents available")

        # Simple selection: prefer agents with fewer completed tasks (load balancing)
        # In production, this could use more sophisticated metrics
        return min(agents, key=lambda a: a.tasks_completed)


    async def assign_task(self, agent_id: str, task: TaskRequest):
        """Assign a task to a specific agent.

        Args:
            agent_id: ID of the agent
            task: Task to assign
        """
        if agent_id not in self.agents:
            raise Exception(f"Agent {agent_id} not found")

        agent = self.agents[agent_id]
        agent.status = "busy"
        agent.current_task = task.task_id

        # Update tenant context
        if task.tenant_id:
            context = await self._get_or_create_tenant_context(task.tenant_id)
            context.active_tasks += 1
            context.last_activity = datetime.now()

        logger.debug(f"Assigned task {task.task_id} to agent {agent_id}")

    async def complete_task(self, agent_id: str, task_id: str, result: TaskResult):
        """Mark a task as completed by an agent.

        Args:
            agent_id: ID of the agent
            task_id: ID of the completed task
            result: Task result
        """
        if agent_id not in self.agents:
            logger.warning(f"Agent {agent_id} not found for task completion")
            return

        agent = self.agents[agent_id]
        agent.status = "idle"
        agent.current_task = None
        agent.tasks_completed += 1
        agent.total_execution_time += result.execution_time_seconds

        # Update tenant context
        for context in self.tenant_contexts.values():
            if any(a.agent_id == agent_id for a in context.agents):
                context.active_tasks = max(0, context.active_tasks - 1)
                context.last_activity = datetime.now()
                break

        logger.debug(f"Agent {agent_id} completed task {task_id}")

    async def _get_or_create_tenant_context(self, tenant_id: str) -> TenantContext:
        """Get or create tenant context.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Tenant context
        """
        if tenant_id not in self.tenant_contexts:
            self.tenant_contexts[tenant_id] = TenantContext(
                tenant_id=tenant_id, resource_limits=self.default_limits.copy(),
            )
            logger.info(f"Created tenant context for {tenant_id}")

        return self.tenant_contexts[tenant_id]

    async def discover_agents(self, task_type: TaskType | None = None) -> list[dict[str, Any]]:
        """Discover available agents, optionally filtered by task type.

        Args:
            task_type: Optional task type to filter by

        Returns:
            List of agent information
        """
        agents_info = []

        for agent in self.agents.values():
            # Filter by task type if specified
            if task_type and task_type not in agent.capabilities.supported_task_types:
                continue

            agents_info.append(
                {
                    "agent_id": agent.agent_id,
                    "agent_type": agent.agent_type.value,
                    "status": agent.status,
                    "capabilities": {
                        "supported_task_types": [
                            t.value for t in agent.capabilities.supported_task_types
                        ],
                        "max_complexity": agent.capabilities.max_complexity.value,
                        "success_rate": agent.capabilities.success_rate,
                        "cost_per_request": agent.capabilities.cost_per_request,
                    },
                    "tasks_completed": agent.tasks_completed,
                    "average_execution_time": (
                        agent.total_execution_time / max(agent.tasks_completed, 1)
                    ),
                },
            )

        return agents_info

    async def get_agent_status(self, agent_id: str) -> dict[str, Any]:
        """Get status of a specific agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Agent status dictionary
        """
        if agent_id not in self.agents:
            raise Exception(f"Agent {agent_id} not found")

        agent = self.agents[agent_id]

        return {
            "agent_id": agent.agent_id,
            "agent_type": agent.agent_type.value,
            "status": agent.status,
            "current_task": agent.current_task,
            "tasks_completed": agent.tasks_completed,
            "total_execution_time": agent.total_execution_time,
            "average_execution_time": (agent.total_execution_time / max(agent.tasks_completed, 1)),
        }

    async def get_status(self) -> dict[str, Any]:
        """Get overall agent manager status.

        Returns:
            Status dictionary
        """
        total_agents = len(self.agents)
        idle_agents = sum(1 for a in self.agents.values() if a.status == "idle")
        busy_agents = sum(1 for a in self.agents.values() if a.status == "busy")

        agent_types_count = {}
        for agent in self.agents.values():
            agent_type = agent.agent_type.value
            agent_types_count[agent_type] = agent_types_count.get(agent_type, 0) + 1

        return {
            "total_agents": total_agents,
            "idle_agents": idle_agents,
            "busy_agents": busy_agents,
            "agent_types": agent_types_count,
            "total_tenants": len(self.tenant_contexts),
            "active_tasks": sum(ctx.active_tasks for ctx in self.tenant_contexts.values()),
        }

    async def cleanup_inactive_tenants(self, max_idle_time: int = 3600):
        """Clean up tenant contexts that have been inactive.

        Args:
            max_idle_time: Maximum idle time in seconds before cleanup
        """
        now = datetime.now()
        inactive_tenants = []

        for tenant_id, context in self.tenant_contexts.items():
            idle_time = (now - context.last_activity).total_seconds()
            if context.active_tasks == 0 and idle_time > max_idle_time:
                inactive_tenants.append(tenant_id)

        for tenant_id in inactive_tenants:
            del self.tenant_contexts[tenant_id]
            logger.info(f"Cleaned up inactive tenant context: {tenant_id}")

    async def shutdown(self):
        """
        Shutdown all agents.
        """
        logger.info("Shutting down Agent Manager")

        # Mark all agents as offline
        for agent in self.agents.values():
            agent.status = "offline"

        logger.info(f"Agent Manager shutdown complete ({len(self.agents)} agents)")
