"""Generic Task Management with LLM Integration.

Extends pheno-sdk's async task orchestration with LLM-powered features like session
titling, status updates, and progress tracking.
"""

from __future__ import annotations

import asyncio

# Import with module path to avoid async keyword issues
import importlib
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

orchestration_module = importlib.import_module("pheno.async.orchestration")
TaskExecutor = orchestration_module.TaskExecutor
TaskResult = orchestration_module.TaskResult
TaskStatus = orchestration_module.TaskStatus

from .content_generation import ContentGenerator

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


class EnhancedTaskStatus(Enum):
    """
    Enhanced task status with additional states.
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"
    SCHEDULED = "scheduled"
    PAUSED = "paused"


@dataclass
class ProgressUpdate:
    """
    Progress update for a task with LLM-generated content.
    """

    timestamp: str
    step: str
    progress: float  # 0.0 to 1.0
    message: str
    details: dict[str, Any] | None = None
    llm_generated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "step": self.step,
            "progress": self.progress,
            "message": self.message,
            "details": self.details,
            "llm_generated": self.llm_generated,
        }


@dataclass
class EnhancedTaskResult(TaskResult):
    """
    Enhanced task result with LLM features.
    """

    # Original TaskResult fields
    task_id: str
    status: TaskStatus
    result: Any = None
    error: Exception | None = None
    execution_time: float = 0.0
    retry_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    # Enhanced fields
    session_id: str = ""
    agent_name: str = ""
    session_title: str = ""
    initial_prompt: str = ""
    progress_history: list[ProgressUpdate] = field(default_factory=list)
    current_step: str = ""
    progress: float = 0.0
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict[str, Any]:
        base_to_dict = getattr(TaskResult, "to_dict", None)
        if callable(base_to_dict):
            base_dict = base_to_dict(self)
        else:
            base_dict = {
                "task_id": self.task_id,
                "status": self.status.value if isinstance(self.status, TaskStatus) else self.status,
                "result": self.result,
                "error": str(self.error) if self.error is not None else None,
                "execution_time": self.execution_time,
                "retry_count": self.retry_count,
                "metadata": self.metadata,
                "created_at": (
                    self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at
                ),
                "completed_at": (
                    self.completed_at.isoformat()
                    if isinstance(self.completed_at, datetime)
                    else self.completed_at
                ),
            }
        base_dict.update(
            {
                "session_id": self.session_id,
                "agent_name": self.agent_name,
                "session_title": self.session_title,
                "initial_prompt": self.initial_prompt,
                "progress_history": [p.to_dict() for p in self.progress_history],
                "current_step": self.current_step,
                "progress": self.progress,
                "started_at": self.started_at,
            },
        )
        return base_dict


class EnhancedTaskManager:
    """
    Enhanced task manager with LLM integration.
    """

    def __init__(
        self,
        output_dir: str = ".tasks",
        content_generator: ContentGenerator | None = None,
        enable_llm_features: bool = True,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Task storage
        self.tasks: dict[str, EnhancedTaskResult] = {}
        self.background_tasks: dict[str, asyncio.Task] = {}

        # LLM features
        self.enable_llm_features = enable_llm_features
        self.content_generator = content_generator or ContentGenerator()

        # Agent naming
        self.agent_names: list[str] = []
        self._initialize_agent_names()

    def _initialize_agent_names(self):
        """
        Initialize agent names for task assignment.
        """
        adjectives = [
            "Swift",
            "Clever",
            "Bright",
            "Wise",
            "Quick",
            "Sharp",
            "Keen",
            "Smart",
            "Agile",
            "Nimble",
            "Bold",
            "Brave",
            "Daring",
            "Fearless",
            "Valiant",
            "Calm",
            "Steady",
            "Patient",
            "Focused",
            "Diligent",
            "Creative",
            "Inventive",
        ]
        nouns = [
            "Falcon",
            "Eagle",
            "Hawk",
            "Owl",
            "Raven",
            "Wolf",
            "Fox",
            "Bear",
            "Lion",
            "Tiger",
            "Dolphin",
            "Whale",
            "Shark",
            "Orca",
            "Seal",
            "Phoenix",
            "Dragon",
            "Griffin",
            "Sphinx",
            "Pegasus",
            "Arrow",
            "Bolt",
        ]

        import random

        self.agent_names = [f"{adj}-{noun}" for adj in adjectives for noun in nouns]
        random.shuffle(self.agent_names)

    def create_session(self) -> str:
        """
        Create a new session ID.
        """
        return str(uuid.uuid4())

    def get_agent_name(self, session_id: str) -> str:
        """
        Get agent name for session.
        """
        if not self.agent_names:
            return f"Agent-{session_id[:8]}"

        # Use session ID to deterministically select agent
        index = hash(session_id) % len(self.agent_names)
        return self.agent_names[index]

    async def create_task(
        self,
        func: Callable[..., Any],
        *args,
        session_id: str | None = None,
        initial_prompt: str = "",
        **kwargs,
    ) -> str:
        """
        Create a new task with LLM features.
        """
        if session_id is None:
            session_id = self.create_session()

        # Generate session title if LLM features are enabled
        session_title = ""
        if self.enable_llm_features and initial_prompt:
            try:
                response = await self.content_generator.generate_title(
                    initial_prompt, session_id=session_id,
                )
                session_title = response.content
            except Exception as e:
                logger.warning(f"Failed to generate session title: {e}")
                session_title = (
                    initial_prompt[:50] + "..." if len(initial_prompt) > 50 else initial_prompt
                )

        # Create task result
        task_result = EnhancedTaskResult(
            task_id=session_id,
            status=TaskStatus.PENDING,
            session_id=session_id,
            agent_name=self.get_agent_name(session_id),
            session_title=session_title,
            initial_prompt=initial_prompt,
            started_at=datetime.now().isoformat(),
        )

        self.tasks[session_id] = task_result
        self._save_task(task_result)

        return session_id

    async def update_progress(
        self,
        session_id: str,
        step: str,
        progress: float,
        message: str = "",
        details: dict[str, Any] | None = None,
        use_llm_status: bool = True,
    ):
        """
        Update task progress with optional LLM-generated status.
        """
        task = self.tasks.get(session_id)
        if not task:
            logger.warning(f"Task {session_id} not found")
            return

        # Generate LLM status if enabled
        final_message = message
        if use_llm_status and self.enable_llm_features and task.initial_prompt:
            try:
                response = await self.content_generator.generate_status_update(
                    task.initial_prompt, step, progress, session_id=session_id,
                )
                if response.success:
                    final_message = response.content
            except Exception as e:
                logger.debug(f"Failed to generate LLM status: {e}")

        # Create progress update
        update = ProgressUpdate(
            timestamp=datetime.now().isoformat(),
            step=step,
            progress=progress,
            message=final_message,
            details=details,
            llm_generated=use_llm_status and self.enable_llm_features,
        )

        # Update task
        task.progress_history.append(update)
        task.current_step = step
        task.progress = progress

        self._save_task(task)
        logger.info(f"Task {session_id} progress: {step} ({progress:.1%}) - {final_message}")

    async def run_task(
        self, session_id: str, func: Callable[..., Any], *args, **kwargs,
    ) -> EnhancedTaskResult:
        """
        Run a task with progress tracking.
        """
        task = self.tasks.get(session_id)
        if not task:
            raise ValueError(f"Task {session_id} not found")

        # Update status to running
        task.status = TaskStatus.RUNNING
        self._save_task(task)

        # Create background task
        async def _run_with_tracking():
            try:
                await self.update_progress(session_id, "initialization", 0.0, "Starting task")

                # Execute the function
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)

                # Update progress
                await self.update_progress(
                    session_id, "completed", 1.0, "Task completed successfully",
                )

                # Update task result
                task.status = TaskStatus.COMPLETED
                task.result = result
                task.completed_at = datetime.now().isoformat()
                task.execution_time = time.time() - time.mktime(
                    datetime.fromisoformat(task.started_at).timetuple(),
                )

                self._save_task(task)
                return task

            except Exception as e:
                logger.exception(f"Task {session_id} failed: {e}")

                # Update progress
                await self.update_progress(session_id, "failed", 1.0, f"Task failed: {e!s}")

                # Update task result
                task.status = TaskStatus.FAILED
                task.error = e
                task.completed_at = datetime.now().isoformat()

                self._save_task(task)
                return task

        # Run the task
        return await _run_with_tracking()

    def get_task(self, session_id: str) -> EnhancedTaskResult | None:
        """
        Get task by session ID.
        """
        return self.tasks.get(session_id)

    def list_tasks(self, status: TaskStatus | None = None) -> list[EnhancedTaskResult]:
        """
        List tasks, optionally filtered by status.
        """
        tasks = list(self.tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return tasks

    def _save_task(self, task: EnhancedTaskResult):
        """
        Save task to file.
        """
        task_file = self.output_dir / f"{task.session_id}.json"
        try:
            with open(task_file, "w") as f:
                json.dump(task.to_dict(), f, indent=2, default=str)
        except Exception as e:
            logger.exception(f"Failed to save task {task.session_id}: {e}")

    def _load_task(self, session_id: str) -> EnhancedTaskResult | None:
        """
        Load task from file.
        """
        task_file = self.output_dir / f"{session_id}.json"
        try:
            if task_file.exists():
                with open(task_file) as f:
                    data = json.load(f)

                # Convert back to EnhancedTaskResult
                return EnhancedTaskResult(
                    task_id=data["task_id"],
                    status=TaskStatus(data["status"]),
                    result=data.get("result"),
                    error=data.get("error"),
                    execution_time=data.get("execution_time", 0.0),
                    retry_count=data.get("retry_count", 0),
                    metadata=data.get("metadata", {}),
                    session_id=data.get("session_id", ""),
                    agent_name=data.get("agent_name", ""),
                    session_title=data.get("session_title", ""),
                    initial_prompt=data.get("initial_prompt", ""),
                    progress_history=[
                        ProgressUpdate(**p) for p in data.get("progress_history", [])
                    ],
                    current_step=data.get("current_step", ""),
                    progress=data.get("progress", 0.0),
                    started_at=data.get(
                        "started_at", datetime.now().isoformat(),
                    ),
                )
        except Exception as e:
            logger.exception(f"Failed to load task {session_id}: {e}")
        return None


# Global instance for easy access
_default_manager: EnhancedTaskManager | None = None


def get_task_manager(
    output_dir: str = ".tasks", enable_llm_features: bool = True,
) -> EnhancedTaskManager:
    """
    Get the global task manager instance.
    """
    global _default_manager
    if _default_manager is None:
        _default_manager = EnhancedTaskManager(output_dir, enable_llm_features)
    return _default_manager
