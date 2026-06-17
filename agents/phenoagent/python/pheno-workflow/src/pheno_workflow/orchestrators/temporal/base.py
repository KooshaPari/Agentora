"""
Base workflow helpers.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from .context import WorkflowContext

logger = logging.getLogger(__name__)


class BaseWorkflow:
    """
    Base class for Temporal workflows.
    """

    def __init__(self):
        self.context: WorkflowContext | None = None

    async def orchestrate(self, workflow_args: dict[str, Any]) -> dict[str, Any]:
        """Main workflow orchestration method - to be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement orchestrate method")

    def setup_context(self, workflow_id: str) -> None:
        """
        Setup workflow context.
        """
        self.context = WorkflowContext(workflow_id)

    async def wait_for_approval(
        self,
        stage: str,
        description: str,
        context: dict[str, Any],
        timeout_seconds: int = 24 * 60 * 60,
    ) -> bool:
        """
        Wait for human approval during workflow execution.
        """
        if not self.context:
            raise RuntimeError("Workflow context not initialized")

        # Import lazily to avoid circular import during module initialisation.
        from .client import get_temporal_client

        client = get_temporal_client()
        approval_id = await client.request_human_approval(
            workflow_id=self.context.workflow_id,
            stage=stage,
            description=description,
            context=context,
            timeout_seconds=timeout_seconds,
        )

        timeout_time = datetime.utcnow() + timedelta(seconds=timeout_seconds)

        while datetime.utcnow() < timeout_time:
            decision = await client.get_approval_status(approval_id)
            if decision:
                return decision.approved

            await asyncio.sleep(10)

        logger.warning("Approval timeout reached for %s", approval_id)
        return False


__all__ = ["BaseWorkflow", "WorkflowContext"]
