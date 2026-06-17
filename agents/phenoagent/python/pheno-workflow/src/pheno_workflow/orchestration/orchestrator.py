"""
Multi-agent orchestrator.
"""

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any


class AgentStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Agent:
    """
    Agent definition.
    """

    name: str
    handler: Callable
    dependencies: list[str] = None
    status: AgentStatus = AgentStatus.IDLE
    result: Any = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class Orchestrator:
    """
    Orchestrate multiple agents with dependencies.
    """

    def __init__(self):
        self.agents: dict[str, Agent] = {}
        self.results: dict[str, Any] = {}

    def register_agent(self, name: str, handler: Callable, dependencies: list[str] | None = None):
        """
        Register an agent.
        """
        self.agents[name] = Agent(name=name, handler=handler, dependencies=dependencies or [])
        return self

    async def execute(self, agent_name: str | None = None) -> dict[str, Any]:
        """
        Execute agents (all or specific one).
        """
        if agent_name:
            return await self._execute_agent(agent_name)

        # Execute all agents in dependency order
        executed = set()
        for name in self.agents:
            if name not in executed:
                await self._execute_with_deps(name, executed)

        return self.results

    async def _execute_with_deps(self, name: str, executed: set):
        """
        Execute agent with dependencies.
        """
        agent = self.agents[name]

        # Execute dependencies first
        for dep in agent.dependencies:
            if dep not in executed:
                await self._execute_with_deps(dep, executed)

        # Execute agent
        if name not in executed:
            await self._execute_agent(name)
            executed.add(name)

    async def _execute_agent(self, name: str) -> Any:
        """
        Execute single agent.
        """
        agent = self.agents[name]

        # Check dependencies
        dep_results = {dep: self.results.get(dep) for dep in agent.dependencies}

        agent.status = AgentStatus.RUNNING
        try:
            result = await agent.handler(**dep_results)
            agent.status = AgentStatus.COMPLETED
            agent.result = result
            self.results[name] = result
            return result
        except Exception as e:
            agent.status = AgentStatus.FAILED
            agent.result = str(e)
            raise

    def get_status(self) -> dict[str, str]:
        """
        Get status of all agents.
        """
        return {name: agent.status.value for name, agent in self.agents.items()}
