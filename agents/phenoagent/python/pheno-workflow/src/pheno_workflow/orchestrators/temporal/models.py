"""
Pydantic models for workflow execution.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

if TYPE_CHECKING:
    from datetime import datetime


class WorkflowExecutionResult(BaseModel):
    """
    Result of a workflow execution.
    """

    workflow_id: str
    run_id: str
    status: str
    result: dict[str, Any] | None = None
    error: str | None = None
    started_at: datetime
    completed_at: datetime | None = None
    execution_time_seconds: float | None = None


class HumanApprovalRequest(BaseModel):
    """
    Request for human approval in a workflow.
    """

    workflow_id: str
    approval_id: str
    stage: str
    description: str
    context: dict[str, Any]
    requested_at: datetime
    timeout_seconds: int
    callback_url: str | None = None


class ApprovalDecision(BaseModel):
    """
    Human approval decision.
    """

    approval_id: str
    approved: bool
    feedback: str | None = None
    decided_at: datetime
    decided_by: str | None = None


__all__ = ["ApprovalDecision", "HumanApprovalRequest", "WorkflowExecutionResult"]
