"""
Core deployment pipeline primitives (status, stage, base class).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable


class DeploymentStatus(Enum):
    """Enumeration of high-level deployment lifecycle states.

    States mirror the internal pipeline steps and can be surfaced in TUIs or external
    monitoring systems.
    """

    IDLE = "idle"
    PREPARING = "preparing"
    BUILDING = "building"
    TESTING = "testing"
    PACKAGING = "packaging"
    UPLOADING = "uploading"
    INSTALLING = "installing"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DeploymentStage:
    """Mutable record describing a single stage within a deployment pipeline.

    Tracks timing, progress percentage, and log output so UI components and callbacks
    can present rich status updates.
    """

    def __init__(self, name: str, description: str, weight: float = 1.0):
        self.name = name
        self.description = description
        self.weight = weight  # Relative weight for progress calculation
        self.status = DeploymentStatus.IDLE
        self.progress = 0.0
        self.logs: list[str] = []
        self.start_time: float | None = None
        self.end_time: float | None = None

    def start(self) -> None:
        """Record the start timestamp and set status to ``PREPARING``.

        Notes:
            Uses ``time.time()`` to capture wall-clock timing for duration
            calculations.
        """
        import time

        self.status = DeploymentStatus.PREPARING
        self.start_time = time.time()

    def complete(self) -> None:
        """Mark the stage as completed and capture the end timestamp.

        Updates progress to 100% so aggregate progress calculations reflect the stage's
        completion.
        """
        import time

        self.status = DeploymentStatus.COMPLETE
        self.progress = 100.0
        self.end_time = time.time()

    def fail(self, error: str) -> None:
        """Mark the stage as failed and append the error message to logs.

        Args:
            error: Description of the failure encountered.
        """
        import time

        self.status = DeploymentStatus.FAILED
        self.end_time = time.time()
        self.logs.append(f"ERROR: {error}")

    def add_log(self, message: str) -> None:
        """Append a log message to the stage log history.

        Args:
            message: Log line to append.
        """
        self.logs.append(message)


class BaseDeployment(ABC):
    """Abstract deployment pipeline coordinating staged execution and callbacks.

    Subclasses define the concrete stages and the logic required to execute them. The
    base class handles progress aggregation, callbacks, and error handling.
    """

    def __init__(self, project_path: Path, config: dict[str, Any]):
        """Initialize a deployment pipeline.

        Args:
            project_path: Filesystem path containing the project to deploy.
            config: Deployment configuration dictionary (e.g., credentials,
                environment options).
        """
        self.project_path = Path(project_path)
        self.config = config
        self.stages: list[DeploymentStage] = []
        self.current_stage_index = 0
        self.overall_status = DeploymentStatus.IDLE
        self.callbacks: list[Callable[[BaseDeployment], Any]] = []

        # Initialize deployment stages
        self._init_stages()

    @abstractmethod
    def _init_stages(self) -> None:
        """Populate ``self.stages`` with deployment-stage metadata.

        Subclasses should override this method to describe their unique pipeline steps.
        The method is invoked during base class initialization.
        """

    @abstractmethod
    async def _execute_stage(self, stage: DeploymentStage) -> bool:
        """Execute a single stage of the deployment pipeline.

        Args:
            stage: Stage metadata describing what to execute next.

        Returns:
            ``True`` when execution succeeds, otherwise ``False``.
        """

    def add_callback(self, callback: Callable[[BaseDeployment], Any]) -> None:
        """Register a callback interested in pipeline progress updates.

        Args:
            callback: Callable receiving the deployment instance.
        """
        self.callbacks.append(callback)

    def _notify_callbacks(self) -> None:
        """Invoke all registered callbacks with the current pipeline state.

        Callback exceptions are caught and ignored to prevent one misbehaving observer
        from halting deployment execution.
        """
        for callback in self.callbacks:
            try:
                callback(self)
            except Exception:
                pass  # Ignore callback errors

    def get_overall_progress(self) -> float:
        """Calculate overall progress as a percentage across all stages.

        Returns:
            Floating-point percentage between 0 and 100.
        """
        if not self.stages:
            return 0.0

        total_weight = sum(stage.weight for stage in self.stages)
        completed_weight = sum(stage.weight * (stage.progress / 100.0) for stage in self.stages)

        return (completed_weight / total_weight) * 100.0

    def get_current_stage(self) -> DeploymentStage | None:
        """Retrieve the stage currently being executed.

        Returns:
            The active :class:`DeploymentStage` or ``None`` when idle.
        """
        if 0 <= self.current_stage_index < len(self.stages):
            return self.stages[self.current_stage_index]
        return None

    async def deploy(self) -> bool:
        """Execute the full deployment pipeline sequentially.

        Returns:
            ``True`` when all stages complete successfully, otherwise ``False``.
        """
        self.overall_status = DeploymentStatus.PREPARING
        self._notify_callbacks()

        try:
            for i, stage in enumerate(self.stages):
                self.current_stage_index = i
                stage.start()
                self._notify_callbacks()

                success = await self._execute_stage(stage)

                if success:
                    stage.complete()
                else:
                    stage.fail("Stage execution failed")
                    self.overall_status = DeploymentStatus.FAILED
                    self._notify_callbacks()
                    return False

                self._notify_callbacks()

            self.overall_status = DeploymentStatus.COMPLETE
            self._notify_callbacks()
            return True

        except Exception as e:
            current_stage = self.get_current_stage()
            if current_stage:
                current_stage.fail(str(e))
            self.overall_status = DeploymentStatus.FAILED
            self._notify_callbacks()
            return False


__all__ = ["BaseDeployment", "DeploymentStage", "DeploymentStatus"]
