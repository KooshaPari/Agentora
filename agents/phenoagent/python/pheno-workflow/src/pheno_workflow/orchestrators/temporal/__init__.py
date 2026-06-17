"""
Temporal Workflow Orchestration Client.
"""

import logging

from .base import BaseWorkflow, WorkflowContext
from .client import TemporalWorkflowClient, get_temporal_client

# Temporal compatibility - check if temporal is available
try:
    import temporalio

    TEMPORAL_AVAILABLE = True
    from temporalio import Client, Worker, workflow
    from temporalio.client import TLSConfig
    from temporalio.common import RetryPolicy
except ImportError:
    TEMPORAL_AVAILABLE = False

    # Create dummy classes for when temporal is not available
    class workflow:
        def __call__(self, *args, **kwargs):
            raise RuntimeError("Temporal is not available")

    class Client:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("Temporal is not available")

    class Worker:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("Temporal is not available")

    class RetryPolicy:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("Temporal is not available")

    class TLSConfig:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("Temporal is not available")


from .decorators import workflow_activity, workflow_signal
from .models import ApprovalDecision, HumanApprovalRequest, WorkflowExecutionResult

__all__ = [
    "TEMPORAL_AVAILABLE",
    "ApprovalDecision",
    "BaseWorkflow",
    "Client",
    "HumanApprovalRequest",
    "RetryPolicy",
    "TLSConfig",
    "TemporalWorkflowClient",
    "Worker",
    "WorkflowContext",
    "WorkflowExecutionResult",
    "get_temporal_client",
    "workflow",
    "workflow_activity",
    "workflow_signal",
]

logger = logging.getLogger(__name__)
logger.info("Temporal workflow client module initialized")
