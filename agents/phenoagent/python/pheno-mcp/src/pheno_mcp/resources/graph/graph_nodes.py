"""Graph node classes for the project graph system.

This module contains the core graph node classes and WBS nodes.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from ..enums import NodeStatus, NodeType
from ..project import (
    AcceptanceCriterion,
    Deliverable,
    QualityGate,
    RequirementSpec,
    TestCase,
    UseCase,
    UserStory,
)

logger = logging.getLogger(__name__)


@dataclass
class GraphNode:
    """
    A node in the project graph.
    """

    id: str
    name: str
    type: NodeType
    status: NodeStatus
    created_at: datetime
    updated_at: datetime

    # Node content and metadata
    description: str | None = None
    metadata: dict[str, Any] = None
    context: dict[str, Any] = None

    # Relationships
    dependencies: set[str] = None  # Node IDs this depends on
    dependents: set[str] = None  # Node IDs that depend on this
    parent_id: str | None = None
    children_ids: set[str] = None

    # Tool-specific information
    tool_name: str | None = None
    tool_args: dict[str, Any] = None
    tool_result: dict[str, Any] = None

    # Communication and coordination
    assigned_to: list[str] = None  # Tool names or agent IDs
    priority: int = 5  # 1-10, higher is more urgent
    estimated_duration: timedelta | None = None
    actual_duration: timedelta | None = None

    # WBS-specific fields (for backward compatibility, added to base class)
    wbs_code: str | None = None  # e.g., "1.1.2"
    assigned_team_id: str | None = None
    deliverables: list[Deliverable] = None
    acceptance_criteria: list[AcceptanceCriterion] = None
    quality_gates: list[QualityGate] = None

    # PM-specific fields
    story_points: int | None = None

    # Structured artifacts for rigorous item types
    user_story: UserStory | None = None
    requirement_spec: RequirementSpec | None = None
    use_case: UseCase | None = None
    test_cases: list[TestCase] = None

    # Relations (traceability and semantic links)
    relations: list[dict[str, str]] = (
        None  # {"type": "implements|tests|blocks|relates_to", "target": node_id}
    )

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.context is None:
            self.context = {}
        if self.dependencies is None:
            self.dependencies = set()
        if self.dependents is None:
            self.dependents = set()
        if self.children_ids is None:
            self.children_ids = set()
        if self.assigned_to is None:
            self.assigned_to = []
        if self.tool_args is None:
            self.tool_args = {}
        if self.tool_result is None:
            self.tool_result = {}
        # WBS-specific initializations
        if self.deliverables is None:
            self.deliverables = []
        if self.acceptance_criteria is None:
            self.acceptance_criteria = []
        if self.quality_gates is None:
            self.quality_gates = []
        if self.test_cases is None:
            self.test_cases = []
        if self.relations is None:
            self.relations = []


@dataclass
class WBSNode(GraphNode):
    """
    Work Breakdown Structure node with enhanced project management features.
    """

    def __init__(self, **kwargs):
        # Handle WBS-specific initialization
        super().__init__(**kwargs)

        # Generate WBS code if not provided
        if not self.wbs_code and self.parent_id:
            self.wbs_code = self._generate_wbs_code()

    def _generate_wbs_code(self) -> str:
        """
        Generate WBS code based on hierarchy position.
        """
        # This will be implemented in the ProjectGraph context
        # where we have access to the full graph structure
        return self.wbs_code or "1.0"

    def add_deliverable(self, deliverable: Deliverable) -> None:
        """
        Add a deliverable to this WBS node.
        """
        if deliverable not in self.deliverables:
            self.deliverables.append(deliverable)
            logger.info(f"Added deliverable '{deliverable.name}' to WBS node {self.name}")

    def add_acceptance_criterion(self, criterion: AcceptanceCriterion) -> None:
        """
        Add an acceptance criterion to this WBS node.
        """
        if criterion not in self.acceptance_criteria:
            self.acceptance_criteria.append(criterion)
            logger.info(f"Added acceptance criterion '{criterion.title}' to WBS node {self.name}")

    def add_quality_gate(self, quality_gate: QualityGate) -> None:
        """
        Add a quality gate to this WBS node.
        """
        if quality_gate not in self.quality_gates:
            self.quality_gates.append(quality_gate)
            logger.info(f"Added quality gate '{quality_gate.name}' to WBS node {self.name}")

    def get_completion_percentage(self) -> float:
        """
        Calculate completion percentage based on acceptance criteria and deliverables.
        """
        total_criteria = len(self.acceptance_criteria)
        total_deliverables = len(self.deliverables)

        if total_criteria == 0 and total_deliverables == 0:
            # Use basic status-based completion
            return 100.0 if self.status == NodeStatus.COMPLETED else 0.0

        criteria_score = 0.0
        if total_criteria > 0:
            satisfied_criteria = sum(1 for c in self.acceptance_criteria if c.is_satisfied())
            criteria_score = (satisfied_criteria / total_criteria) * 50.0  # 50% weight

        deliverable_score = 0.0
        if total_deliverables > 0:
            total_deliverable_completion = sum(
                d.get_acceptance_percentage() for d in self.deliverables
            )
            deliverable_score = (
                total_deliverable_completion / total_deliverables
            ) * 0.5  # 50% weight

        return criteria_score + deliverable_score

    def get_critical_blockers(self) -> list[str]:
        """
        Get critical items blocking completion.
        """
        blockers = []

        # Check for failed quality gates
        for gate in self.quality_gates:
            if gate.status.value == "failed":
                blockers.append(f"Failed quality gate: {gate.name}")

        # Check for high-priority unsatisfied criteria
        for criterion in self.acceptance_criteria:
            if criterion.priority >= 8 and not criterion.is_satisfied():
                blockers.append(f"Critical criterion not met: {criterion.title}")

        # Check for incomplete deliverables
        for deliverable in self.deliverables:
            if not deliverable.is_complete():
                critical_criteria = deliverable.get_critical_criteria()
                if critical_criteria:
                    blockers.append(f"Incomplete deliverable: {deliverable.name}")

        return blockers
