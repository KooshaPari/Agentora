"""Workflow Engine.

Orchestrates workflow execution with state persistence and monitoring.
"""

import uuid
from datetime import datetime
from typing import Any

from .workflow import Workflow, WorkflowContext, WorkflowStatus


class WorkflowEngine:
    """Workflow execution engine.

    Manages workflow lifecycle, state persistence, and integration with orchestrator
    backends.
    """

    def __init__(self, orchestrator: Any | None = None, persistence: Any | None = None):
        """Initialize workflow engine.

        Args:
            orchestrator: Optional orchestrator for distributed execution
            persistence: Optional persistence layer for workflow state
        """
        self.orchestrator = orchestrator
        self.persistence = persistence
        self.active_workflows: dict[str, Workflow] = {}

    async def execute(
        self, workflow_class: type[Workflow], inputs: dict[str, Any], workflow_id: str | None = None,
    ) -> Any:
        """Execute a workflow.

        Args:
            workflow_class: Workflow class to instantiate
            inputs: Input parameters for the workflow
            workflow_id: Optional workflow ID (generated if not provided)

        Returns:
            Workflow execution result
        """
        # Create workflow instance
        workflow = workflow_class()
        workflow.workflow_id = workflow_id or f"wf-{uuid.uuid4().hex[:8]}"
        workflow.execution_id = f"exec-{uuid.uuid4().hex[:8]}"

        # Set up context with orchestrator
        if self.orchestrator:
            workflow.context = WorkflowContext(
                workflow_id=workflow.workflow_id,
                execution_id=workflow.execution_id,
                inputs=inputs,
                orchestrator=self.orchestrator,
            )

        # Track active workflow
        self.active_workflows[workflow.workflow_id] = workflow

        try:
            # Persist initial state
            if self.persistence:
                await self._save_state(workflow)

            # Execute workflow
            result = await workflow.execute(inputs)

            # Persist final state
            if self.persistence:
                await self._save_state(workflow)

            return result

        except Exception as e:
            # Mark workflow as failed
            workflow.status = WorkflowStatus.FAILED

            # Persist error state
            if self.persistence:
                await self._save_state(workflow, error=str(e))

            raise

        finally:
            # Remove from active workflows
            self.active_workflows.pop(workflow.workflow_id, None)

    async def _save_state(self, workflow: Workflow, error: str | None = None):
        """
        Save workflow state to persistence layer.
        """
        if not self.persistence:
            return

        state = {
            "workflow_id": workflow.workflow_id,
            "execution_id": workflow.execution_id,
            "status": workflow.status.value,
            "timestamp": datetime.now().isoformat(),
        }

        if workflow.context:
            state["context_state"] = workflow.context.state
            state["context_metadata"] = workflow.context.metadata

        if error:
            state["error"] = error

        await self.persistence.save(workflow.workflow_id, state)

    async def get_workflow_status(self, workflow_id: str) -> dict[str, Any] | None:
        """
        Get workflow status from persistence or active workflows.
        """
        # Check active workflows first
        if workflow_id in self.active_workflows:
            workflow = self.active_workflows[workflow_id]
            return {
                "workflow_id": workflow_id,
                "status": workflow.status.value,
                "execution_id": workflow.execution_id,
            }

        # Check persistence
        if self.persistence:
            return await self.persistence.get(workflow_id)

        return None

    async def pause_workflow(self, workflow_id: str):
        """
        Pause a running workflow.
        """
        if workflow_id in self.active_workflows:
            workflow = self.active_workflows[workflow_id]
            workflow.status = WorkflowStatus.PAUSED
            if self.persistence:
                await self._save_state(workflow)

    async def resume_workflow(self, workflow_id: str):
        """
        Resume a paused workflow.
        """
        if workflow_id in self.active_workflows:
            workflow = self.active_workflows[workflow_id]
            if workflow.status == WorkflowStatus.PAUSED:
                workflow.status = WorkflowStatus.RUNNING
                if self.persistence:
                    await self._save_state(workflow)

    async def cancel_workflow(self, workflow_id: str):
        """
        Cancel a running workflow.
        """
        if workflow_id in self.active_workflows:
            workflow = self.active_workflows[workflow_id]
            workflow.status = WorkflowStatus.CANCELLED
            if self.persistence:
                await self._save_state(workflow)
            # Remove from active workflows
            self.active_workflows.pop(workflow_id, None)

    def list_active_workflows(self) -> dict[str, dict[str, Any]]:
        """
        List all active workflows.
        """
        return {
            wf_id: {
                "workflow_id": wf_id,
                "status": wf.status.value,
                "execution_id": wf.execution_id,
            }
            for wf_id, wf in self.active_workflows.items()
        }
