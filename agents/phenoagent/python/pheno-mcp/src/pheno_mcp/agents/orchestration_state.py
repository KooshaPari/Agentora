"""State management for multi-agent orchestration."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AgentState:
    """Current state of an agent."""

    agent_id: str
    name: str
    status: str
    current_task: str | None = None
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_execution_time_ms: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_active_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


class AgentPool:
    """Manages a pool of agents for task execution."""

    def __init__(self, config: Any):
        """Initialize agent pool.

        Args:
            config: Agent pool configuration
        """
        from .orchestration_base import AgentStatus

        self.config = config
        self.agents: dict[str, AgentState] = {}
        self.agent_instances: dict[str, Any] = {}
        self._lock = asyncio.Lock()
        self._task_queue: asyncio.Queue[str] = asyncio.Queue()
        self._health_check_task: asyncio.Task | None = None
        self._status_enum = AgentStatus

    async def add_agent(self, agent_id: str, agent_instance: Any, config: Any) -> None:
        """Add an agent to the pool."""
        async with self._lock:
            if len(self.agents) >= self.config.max_agents:
                logger.warning(
                    f"Agent pool at capacity ({self.config.max_agents}), cannot add agent {agent_id}",
                )
                raise ValueError(
                    f"Agent pool at maximum capacity: {self.config.max_agents}"
                )

            self.agents[agent_id] = AgentState(
                agent_id=agent_id,
                name=config.name,
                status=self._status_enum.IDLE,
            )
            self.agent_instances[agent_id] = agent_instance
            logger.info(
                f"Added agent {agent_id} ({config.name}) to pool. Pool size: {len(self.agents)}",
            )

    async def get_available_agent(self) -> tuple[str, Any] | None:
        """Get an available agent for task execution."""
        async with self._lock:
            for agent_id, state in self.agents.items():
                if state.status == self._status_enum.IDLE:
                    state.status = self._status_enum.BUSY
                    state.last_active_at = datetime.utcnow()
                    logger.debug(f"Agent {agent_id} allocated for task execution")
                    return agent_id, self.agent_instances[agent_id]
            logger.warning("No idle agents available in pool")
        return None

    async def release_agent(self, agent_id: str, success: bool = True) -> None:
        """Release an agent back to the pool."""
        async with self._lock:
            if agent_id in self.agents:
                state = self.agents[agent_id]
                state.status = self._status_enum.IDLE
                state.last_active_at = datetime.utcnow()
                if success:
                    state.tasks_completed += 1
                    logger.debug(
                        f"Agent {agent_id} released (success). Total completed: {state.tasks_completed}",
                    )
                else:
                    state.tasks_failed += 1
                    logger.warning(
                        f"Agent {agent_id} released (failed). Total failed: {state.tasks_failed}",
                    )
            else:
                logger.error(f"Attempted to release unknown agent: {agent_id}")

    async def get_agent_state(self, agent_id: str) -> AgentState | None:
        """Get the current state of an agent."""
        async with self._lock:
            return self.agents.get(agent_id)

    async def get_pool_stats(self) -> dict[str, Any]:
        """Get pool statistics."""
        async with self._lock:
            return {
                "total_agents": len(self.agents),
                "idle_agents": sum(
                    1
                    for s in self.agents.values()
                    if s.status == self._status_enum.IDLE
                ),
                "busy_agents": sum(
                    1
                    for s in self.agents.values()
                    if s.status == self._status_enum.BUSY
                ),
                "error_agents": sum(
                    1
                    for s in self.agents.values()
                    if s.status == self._status_enum.ERROR
                ),
                "total_tasks_completed": sum(
                    s.tasks_completed for s in self.agents.values()
                ),
                "total_tasks_failed": sum(s.tasks_failed for s in self.agents.values()),
            }

    async def start_health_checks(self) -> None:
        """Start periodic health checks for agents."""
        if self._health_check_task is None:
            self._health_check_task = asyncio.create_task(self._health_check_loop())

    async def stop_health_checks(self) -> None:
        """Stop health checks."""
        if self._health_check_task:
            self._health_check_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._health_check_task
            self._health_check_task = None

    async def _health_check_loop(self) -> None:
        """Periodic health check loop."""
        while True:
            await asyncio.sleep(self.config.health_check_interval_seconds)
            async with self._lock:
                now = datetime.utcnow()
                for state in self.agents.values():
                    if state.status == self._status_enum.IDLE:
                        idle_seconds = (now - state.last_active_at).total_seconds()
                        if idle_seconds > self.config.idle_timeout_seconds:
                            pass
