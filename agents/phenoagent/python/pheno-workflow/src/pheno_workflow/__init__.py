"""Workflow-Kit: Saga patterns, declarative workflows, and orchestration utilities."""

# Pattern-based workflows and saga support
from .core.engine import WorkflowEngine as CoreWorkflowEngine  # Alias
from .core.engine import WorkflowEngine as DeclarativeWorkflowEngine

# Declarative workflow core
from .core.workflow import (
    Workflow as CoreWorkflow,  # Alias for the new decorator-based workflow
)
from .core.workflow import Workflow as DeclarativeWorkflow
from .core.workflow import (
    WorkflowContext,
    WorkflowStatus,
)
from .core.workflow import WorkflowStep as CoreWorkflowStep
from .core.workflow import step as workflow_step
from .core.workflow import workflow as workflow_definition

# Advanced orchestrators
from .orchestrators.temporal import (
    ApprovalDecision,
    HumanApprovalRequest,
    TemporalWorkflowClient,
    WorkflowExecutionResult,
)
from .patterns.saga import Saga, SagaExecutor, SagaStep
from .patterns.state_machine import State, StateMachine, Transition
from .patterns.workflow import Workflow, WorkflowEngine, WorkflowStep

__version__ = "0.1.0"

__all__ = [
    "ApprovalDecision",
    "CoreWorkflow",  # Alias for new decorator-based system
    "CoreWorkflowEngine",
    "CoreWorkflowStep",
    # Declarative workflows (Core system)
    "DeclarativeWorkflow",
    "DeclarativeWorkflowEngine",
    "HumanApprovalRequest",
    # Pattern-based workflows
    "Saga",
    "SagaExecutor",
    "SagaStep",
    "State",
    "StateMachine",
    # Orchestrators
    "TemporalWorkflowClient",
    "Transition",
    "Workflow",
    "WorkflowContext",
    "WorkflowEngine",
    "WorkflowExecutionResult",
    "WorkflowStatus",
    "WorkflowStep",
    "step",
    "workflow",
    "workflow_definition",
    "workflow_step",
]

# Backwards-compatible aliases
workflow = workflow_definition
step = workflow_step
