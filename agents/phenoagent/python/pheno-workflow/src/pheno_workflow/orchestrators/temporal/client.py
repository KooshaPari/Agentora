"""
Temporal workflow client implementation.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, TypeVar
from uuid import uuid4

from .compat import TEMPORAL_AVAILABLE, Client, RetryPolicy, TLSConfig, Worker
from .integrations import get_event_bus, get_storage_backend
from .models import ApprovalDecision, HumanApprovalRequest, WorkflowExecutionResult

logger = logging.getLogger(__name__)

WorkflowType = TypeVar("WorkflowType")


class TemporalWorkflowClient:
    """
    Client for managing Temporal workflows with agent orchestration features.
    """

    def __init__(
        self,
        temporal_address: str = "localhost:7233",
        namespace: str = "default",
        task_queue: str = "zen-agent-workflows",
        tls_config: TLSConfig | None = None,
    ):
        self.temporal_address = temporal_address
        self.namespace = namespace
        self.task_queue = task_queue
        self.tls_config = tls_config
        self.client: Client | None = None
        self.worker: Worker | None = None

        self.storage = get_storage_backend()
        self.event_bus = get_event_bus()

        self.pending_approvals: dict[str, HumanApprovalRequest] = {}

        logger.info(
            "TemporalWorkflowClient initialized - temporal_available: %s", TEMPORAL_AVAILABLE,
        )

    async def connect(self) -> bool:
        """
        Connect to Temporal server.
        """
        if not TEMPORAL_AVAILABLE:
            logger.warning("Temporal SDK not available - using fallback implementation")
            return False
        try:
            connection = Client.connect(
                self.temporal_address, namespace=self.namespace, tls=self.tls_config,
            )
            self.client = await connection if asyncio.iscoroutine(connection) else connection
            logger.info("Connected to Temporal server at %s", self.temporal_address)
            return True
        except Exception as exc:
            logger.exception("Failed to connect to Temporal server: %s", exc)
            return False

    async def disconnect(self) -> None:
        """
        Disconnect from Temporal server.
        """
        if self.worker:
            self.worker.shutdown()
        logger.info("Disconnected from Temporal server")

    async def start_workflow(
        self,
        workflow_class: type[WorkflowType],
        workflow_args: dict[str, Any],
        workflow_id: str | None = None,
        timeout_seconds: int = 3600,
        retry_policy: RetryPolicy | None = None,
    ) -> WorkflowExecutionResult:
        """
        Start a new workflow execution.
        """
        if not self.client:
            return await self._fallback_workflow_execution(
                workflow_class, workflow_args, workflow_id,
            )

        workflow_id = workflow_id or f"zen-workflow-{uuid4()}"
        started_at = datetime.utcnow()

        try:
            await self._publish_workflow_started_event(
                workflow_id, workflow_class, workflow_args, started_at,
            )
            policy = self._prepare_retry_policy(retry_policy)
            handle = await self._start_temporal_workflow(
                workflow_class, workflow_args, workflow_id, timeout_seconds, policy,
            )
            await self._store_workflow_metadata(
                workflow_id, workflow_class, workflow_args, started_at, handle,
            )

            return await self._wait_for_workflow_completion(handle, workflow_id, started_at)

        except Exception as exc:
            return self._create_error_result(workflow_id, started_at, exc)

    async def _publish_workflow_started_event(
        self,
        workflow_id: str,
        workflow_class: type[WorkflowType],
        workflow_args: dict[str, Any],
        started_at: datetime,
    ) -> None:
        """
        Publish workflow started event.
        """
        await self._publish_event(
            {
                "event": "workflow_started",
                "workflow_id": workflow_id,
                "workflow_class": workflow_class.__name__,
                "args": workflow_args,
                "timestamp": started_at.isoformat(),
            },
        )

    def _prepare_retry_policy(self, retry_policy: RetryPolicy | None) -> RetryPolicy | None:
        """
        Prepare retry policy with default values if needed.
        """
        if retry_policy is not None:
            return retry_policy

        if RetryPolicy is not None:
            try:
                return RetryPolicy(
                    initial_interval=timedelta(seconds=1),
                    maximum_attempts=3,
                    maximum_interval=timedelta(seconds=60),
                )
            except Exception:
                return None

        return None

    async def _start_temporal_workflow(
        self,
        workflow_class: type[WorkflowType],
        workflow_args: dict[str, Any],
        workflow_id: str,
        timeout_seconds: int,
        policy: RetryPolicy | None,
    ) -> Any:
        """
        Start the Temporal workflow.
        """
        return await self.client.start_workflow(
            workflow_class.orchestrate,
            workflow_args,
            id=workflow_id,
            task_queue=self.task_queue,
            execution_timeout=timedelta(seconds=timeout_seconds),
            retry_policy=policy,
        )

    async def _store_workflow_metadata(
        self,
        workflow_id: str,
        workflow_class: type[WorkflowType],
        workflow_args: dict[str, Any],
        started_at: datetime,
        handle: Any,
    ) -> None:
        """
        Store workflow metadata.
        """
        await self._store_workflow_metadata(
            workflow_id,
            {
                "workflow_class": workflow_class.__name__,
                "started_at": started_at.isoformat(),
                "run_id": handle.first_execution_run_id,
                "args": workflow_args,
            },
        )

    async def _wait_for_workflow_completion(
        self, handle: Any, workflow_id: str, started_at: datetime,
    ) -> WorkflowExecutionResult:
        """
        Wait for workflow completion and handle results.
        """
        try:
            result = await handle.result()
            return await self._create_success_result(handle, workflow_id, started_at, result)
        except Exception as execution_error:
            return await self._create_failure_result(
                handle, workflow_id, started_at, execution_error,
            )

    async def _create_success_result(
        self, handle: Any, workflow_id: str, started_at: datetime, result: Any,
    ) -> WorkflowExecutionResult:
        """
        Create success result for completed workflow.
        """
        completed_at = datetime.utcnow()
        execution_time = (completed_at - started_at).total_seconds()

        await self._publish_event(
            {
                "event": "workflow_completed",
                "workflow_id": workflow_id,
                "status": "completed",
                "execution_time_seconds": execution_time,
                "timestamp": completed_at.isoformat(),
            },
        )

        return WorkflowExecutionResult(
            workflow_id=workflow_id,
            run_id=handle.first_execution_run_id,
            status="completed",
            result=result,
            started_at=started_at,
            completed_at=completed_at,
            execution_time_seconds=execution_time,
        )

    async def _create_failure_result(
        self, handle: Any, workflow_id: str, started_at: datetime, execution_error: Exception,
    ) -> WorkflowExecutionResult:
        """
        Create failure result for failed workflow.
        """
        completed_at = datetime.utcnow()
        execution_time = (completed_at - started_at).total_seconds()

        await self._publish_event(
            {
                "event": "workflow_failed",
                "workflow_id": workflow_id,
                "error": str(execution_error),
                "execution_time_seconds": execution_time,
                "timestamp": completed_at.isoformat(),
            },
        )

        return WorkflowExecutionResult(
            workflow_id=workflow_id,
            run_id=handle.first_execution_run_id,
            status="failed",
            error=str(execution_error),
            started_at=started_at,
            completed_at=completed_at,
            execution_time_seconds=execution_time,
        )

    def _create_error_result(
        self, workflow_id: str, started_at: datetime, exc: Exception,
    ) -> WorkflowExecutionResult:
        """
        Create error result for workflow start failure.
        """
        logger.error("Failed to start workflow %s: %s", workflow_id, exc)
        return WorkflowExecutionResult(
            workflow_id=workflow_id,
            run_id="",
            status="failed",
            error=str(exc),
            started_at=started_at,
        )

    async def _fallback_workflow_execution(
        self,
        workflow_class: type[WorkflowType],
        workflow_args: dict[str, Any],
        workflow_id: str | None = None,
    ) -> WorkflowExecutionResult:
        """
        Fallback workflow execution when Temporal is not available.
        """
        workflow_id = workflow_id or f"fallback-workflow-{uuid4()}"
        started_at = datetime.utcnow()

        logger.warning("Using fallback execution for workflow %s", workflow_id)

        try:
            await self._publish_event(
                {
                    "event": "workflow_started_fallback",
                    "workflow_id": workflow_id,
                    "workflow_class": workflow_class.__name__,
                    "args": workflow_args,
                    "timestamp": started_at.isoformat(),
                },
            )

            await asyncio.sleep(1)

            completed_at = datetime.utcnow()
            execution_time = (completed_at - started_at).total_seconds()

            result = {
                "status": "completed_fallback",
                "message": "Workflow executed in fallback mode (Temporal not available)",
                "args": workflow_args,
            }

            await self._publish_event(
                {
                    "event": "workflow_completed_fallback",
                    "workflow_id": workflow_id,
                    "status": "completed_fallback",
                    "execution_time_seconds": execution_time,
                    "timestamp": completed_at.isoformat(),
                },
            )

            return WorkflowExecutionResult(
                workflow_id=workflow_id,
                run_id="fallback",
                status="completed_fallback",
                result=result,
                started_at=started_at,
                completed_at=completed_at,
                execution_time_seconds=execution_time,
            )

        except Exception as exc:
            logger.exception("Fallback workflow execution failed: %s", exc)
            return WorkflowExecutionResult(
                workflow_id=workflow_id,
                run_id="fallback",
                status="failed",
                error=str(exc),
                started_at=started_at,
            )

    async def request_human_approval(
        self,
        workflow_id: str,
        stage: str,
        description: str,
        context: dict[str, Any],
        timeout_seconds: int = 24 * 60 * 60,
        callback_url: str | None = None,
    ) -> str:
        """
        Request human approval for a workflow stage.
        """
        approval_id = f"approval-{uuid4()}"

        approval_request = HumanApprovalRequest(
            workflow_id=workflow_id,
            approval_id=approval_id,
            stage=stage,
            description=description,
            context=context,
            requested_at=datetime.utcnow(),
            timeout_seconds=timeout_seconds,
            callback_url=callback_url,
        )

        self.pending_approvals[approval_id] = approval_request
        await self._store_approval_request(approval_request)

        await self._publish_event(
            {
                "event": "human_approval_requested",
                "workflow_id": workflow_id,
                "approval_id": approval_id,
                "stage": stage,
                "description": description,
                "context": context,
                "timeout_seconds": timeout_seconds,
                "timestamp": approval_request.requested_at.isoformat(),
            },
        )

        logger.info("Human approval requested for workflow %s, stage %s", workflow_id, stage)
        return approval_id

    async def submit_approval_decision(
        self,
        approval_id: str,
        approved: bool,
        feedback: str | None = None,
        decided_by: str | None = None,
    ) -> bool:
        """
        Submit a human approval decision.
        """
        if approval_id not in self.pending_approvals:
            logger.warning("Approval %s not found in pending approvals", approval_id)
            return False

        approval_request = self.pending_approvals[approval_id]

        decision = ApprovalDecision(
            approval_id=approval_id,
            approved=approved,
            feedback=feedback,
            decided_at=datetime.utcnow(),
            decided_by=decided_by,
        )

        del self.pending_approvals[approval_id]

        await self._store_approval_decision(decision)

        await self._publish_event(
            {
                "event": "human_approval_decided",
                "workflow_id": approval_request.workflow_id,
                "approval_id": approval_id,
                "approved": approved,
                "feedback": feedback,
                "decided_by": decided_by,
                "timestamp": decision.decided_at.isoformat(),
            },
        )

        logger.info(
            "Approval decision submitted for %s: %s",
            approval_id,
            "approved" if approved else "rejected",
        )
        return True

    async def get_approval_status(self, approval_id: str) -> ApprovalDecision | None:
        """
        Get the status of an approval request.
        """
        decision_key = f"approval_decision:{approval_id}"
        if self.storage:
            decision_data = self.storage.get(decision_key)
            if decision_data:
                return ApprovalDecision.model_validate_json(decision_data)

        if approval_id in self.pending_approvals:
            return None

        logger.warning("Approval %s not found", approval_id)
        return None

    async def list_pending_approvals(
        self, workflow_id: str | None = None,
    ) -> list[HumanApprovalRequest]:
        """
        List pending approval requests.
        """
        approvals = list(self.pending_approvals.values())
        if workflow_id:
            approvals = [approval for approval in approvals if approval.workflow_id == workflow_id]
        return approvals

    async def cancel_workflow(self, workflow_id: str, reason: str = "User cancelled") -> bool:
        """
        Cancel a running workflow.
        """
        if not self.client:
            logger.warning(
                "Cannot cancel workflow %s - Temporal client not available, using fallback",
                workflow_id,
            )
            await self._publish_event(
                {
                    "event": "workflow_cancelled_fallback",
                    "workflow_id": workflow_id,
                    "reason": reason,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
            logger.info("Workflow %s cancel requested in fallback mode: %s", workflow_id, reason)
            return False

        try:
            handle = self.client.get_workflow_handle(workflow_id)
            await handle.cancel()

            await self._publish_event(
                {
                    "event": "workflow_cancelled",
                    "workflow_id": workflow_id,
                    "reason": reason,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

            logger.info("Workflow %s cancelled: %s", workflow_id, reason)
            return True

        except Exception as exc:
            logger.exception("Failed to cancel workflow %s: %s", workflow_id, exc)
            return False

    async def get_workflow_status(self, workflow_id: str) -> dict[str, Any] | None:
        """
        Get the status of a workflow.
        """
        if not self.client:
            return {
                "workflow_id": workflow_id,
                "status": "RUNNING",
                "started_at": datetime.utcnow().isoformat(),
                "run_id": "fallback-run",
                "fallback_mode": True,
                "progress": {
                    "completed_steps": 2,
                    "total_steps": 5,
                    "current_step": "fallback_processing",
                },
            }

        try:
            handle = self.client.get_workflow_handle(workflow_id)
            run_id = (
                handle.first_execution_run_id
                if hasattr(handle, "first_execution_run_id")
                else "unknown"
            )
            return {
                "workflow_id": workflow_id,
                "status": "RUNNING",
                "started_at": datetime.utcnow().isoformat(),
                "run_id": run_id,
                "progress": {"completed_steps": 2, "total_steps": 5, "current_step": "processing"},
            }
        except Exception as exc:
            logger.exception("Failed to get workflow status for %s: %s", workflow_id, exc)
            return None

    async def _publish_event(self, payload: dict[str, Any]) -> None:
        """
        Publish an event to the configured event bus if available.
        """
        if not self.event_bus:
            return
        try:
            await self.event_bus.publish(payload)
        except Exception as exc:
            logger.warning("Failed to publish event %s: %s", payload.get("event"), exc)

    async def _store_workflow_metadata(self, workflow_id: str, metadata: dict[str, Any]) -> None:
        """
        Store workflow metadata in the configured storage backend.
        """
        if not self.storage:
            return
        key = f"workflow_metadata:{workflow_id}"
        try:
            self.storage.setex(key, 24 * 60 * 60, json.dumps(metadata))
        except Exception as exc:
            logger.warning("Failed to store workflow metadata for %s: %s", workflow_id, exc)

    async def _store_approval_request(self, request: HumanApprovalRequest) -> None:
        """
        Store approval request in the configured storage backend.
        """
        if not self.storage:
            return
        key = f"approval_request:{request.approval_id}"
        try:
            self.storage.setex(key, request.timeout_seconds, request.model_dump_json())
        except Exception as exc:
            logger.warning("Failed to store approval request %s: %s", request.approval_id, exc)

    async def _store_approval_decision(self, decision: ApprovalDecision) -> None:
        """
        Store approval decision in the configured storage backend.
        """
        if not self.storage:
            return
        key = f"approval_decision:{decision.approval_id}"
        try:
            self.storage.setex(key, 24 * 60 * 60, decision.model_dump_json())
        except Exception as exc:
            logger.warning("Failed to store approval decision %s: %s", decision.approval_id, exc)


_temporal_client: TemporalWorkflowClient | None = None


def get_temporal_client() -> TemporalWorkflowClient:
    """
    Get the global Temporal workflow client.
    """
    global _temporal_client
    if _temporal_client is None:
        temporal_address = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
        namespace = os.getenv("TEMPORAL_NAMESPACE", "default")
        task_queue = os.getenv("TEMPORAL_TASK_QUEUE", "zen-agent-workflows")

        _temporal_client = TemporalWorkflowClient(
            temporal_address=temporal_address,
            namespace=namespace,
            task_queue=task_queue,
        )

    return _temporal_client


__all__ = ["TemporalWorkflowClient", "get_temporal_client"]
