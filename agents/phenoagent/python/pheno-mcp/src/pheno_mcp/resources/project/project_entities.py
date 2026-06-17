"""Project management entities for the project graph system.

This module contains classes for managing project deliverables, acceptance criteria,
quality gates, and other project management entities.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ..enums import AcceptanceStatus, QualityGateStatus

logger = logging.getLogger(__name__)


@dataclass
class AcceptanceCriterion:
    """
    Represents an acceptance criterion with verification methods.
    """

    id: str
    title: str
    description: str
    verification_method: str  # "demo", "test", "review", "inspection"
    status: AcceptanceStatus = AcceptanceStatus.PENDING
    priority: int = 5  # 1-10, higher is more critical
    assigned_verifier: str | None = None
    verification_notes: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    verified_at: datetime | None = None

    def verify(self, verifier_id: str, passed: bool, notes: str = "") -> bool:
        """
        Verify the acceptance criterion.
        """
        self.assigned_verifier = verifier_id
        self.verification_notes = notes
        self.verified_at = datetime.now()

        if passed:
            self.status = AcceptanceStatus.ACCEPTED
            logger.info(f"Acceptance criterion {self.id} ({self.title}) verified successfully")
        else:
            self.status = AcceptanceStatus.REJECTED
            logger.warning(
                f"Acceptance criterion {self.id} ({self.title}) failed verification: {notes}",
            )

        return passed

    def is_satisfied(self) -> bool:
        """
        Check if the criterion is satisfied.
        """
        return self.status == AcceptanceStatus.ACCEPTED


@dataclass
class Deliverable:
    """
    Represents a project deliverable with acceptance criteria.
    """

    id: str
    name: str
    description: str
    due_date: datetime | None = None
    completion_date: datetime | None = None
    acceptance_criteria: list[AcceptanceCriterion] = field(default_factory=list)
    deliverable_type: str = "document"  # "document", "software", "service", "milestone"
    assigned_team_id: str | None = None
    file_paths: list[str] = field(default_factory=list)

    def add_acceptance_criterion(self, criterion: AcceptanceCriterion) -> None:
        """
        Add an acceptance criterion to the deliverable.
        """
        self.acceptance_criteria.append(criterion)
        logger.info(f"Added acceptance criterion '{criterion.title}' to deliverable {self.name}")

    def get_acceptance_percentage(self) -> float:
        """
        Get the percentage of acceptance criteria that are satisfied.
        """
        if not self.acceptance_criteria:
            return 0.0

        satisfied = sum(1 for criterion in self.acceptance_criteria if criterion.is_satisfied())
        return (satisfied / len(self.acceptance_criteria)) * 100.0

    def is_complete(self) -> bool:
        """
        Check if all acceptance criteria are satisfied.
        """
        return all(criterion.is_satisfied() for criterion in self.acceptance_criteria)

    def get_critical_criteria(self) -> list[AcceptanceCriterion]:
        """
        Get high priority acceptance criteria that are not satisfied.
        """
        return [
            criterion
            for criterion in self.acceptance_criteria
            if criterion.priority >= 8 and not criterion.is_satisfied()
        ]


@dataclass
class QualityGate:
    """
    Represents a quality gate for milestone validation.
    """

    id: str
    name: str
    description: str
    milestone_id: str
    criteria: list[AcceptanceCriterion] = field(default_factory=list)
    status: QualityGateStatus = QualityGateStatus.OPEN
    required_approvers: list[str] = field(default_factory=list)
    approvals: dict[str, bool] = field(default_factory=dict)  # approver_id -> approved
    created_at: datetime = field(default_factory=datetime.now)
    closed_at: datetime | None = None

    def add_criterion(self, criterion: AcceptanceCriterion) -> None:
        """
        Add a criterion to the quality gate.
        """
        self.criteria.append(criterion)
        logger.info(f"Added criterion '{criterion.title}' to quality gate {self.name}")

    def add_approval(self, approver_id: str, approved: bool, notes: str = "") -> None:
        """
        Add an approval decision from an approver.
        """
        self.approvals[approver_id] = approved
        logger.info(
            f"Quality gate {self.name}: {approver_id} {'approved' if approved else 'rejected'}",
        )

        # Check if we can close the gate
        self._evaluate_gate_status()

    def _evaluate_gate_status(self) -> None:
        """
        Evaluate and update the quality gate status.
        """
        # Check if all criteria are satisfied
        all_criteria_passed = all(criterion.is_satisfied() for criterion in self.criteria)

        # Check if all required approvals are obtained
        all_approved = True
        for approver_id in self.required_approvers:
            if approver_id not in self.approvals or not self.approvals[approver_id]:
                all_approved = False
                break

        if all_criteria_passed and all_approved:
            self.status = QualityGateStatus.PASSED
            self.closed_at = datetime.now()
            logger.info(f"Quality gate {self.name} PASSED")
        elif len(self.approvals) == len(self.required_approvers):
            # All approvers have responded
            if not all_approved:
                self.status = QualityGateStatus.FAILED
                self.closed_at = datetime.now()
                logger.warning(f"Quality gate {self.name} FAILED - not all approvers approved")

    def get_progress(self) -> dict[str, Any]:
        """
        Get progress information for the quality gate.
        """
        criteria_progress = (
            sum(1 for c in self.criteria if c.is_satisfied()) / max(len(self.criteria), 1) * 100
        )
        approval_progress = (
            len([a for a in self.approvals.values() if a])
            / max(len(self.required_approvers), 1)
            * 100
        )

        return {
            "criteria_progress": criteria_progress,
            "approval_progress": approval_progress,
            "overall_progress": min(criteria_progress, approval_progress),
            "status": self.status.value,
            "can_pass": criteria_progress == 100 and approval_progress == 100,
        }


@dataclass
class UserStory:
    """Strict user story template.

    Enforces: As a <persona>, I want <goal>, so that <benefit>.
    Acceptance criteria live on the node (GraphNode.acceptance_criteria).
    """

    persona: str
    goal: str
    benefit: str
    story_points: int | None = None


@dataclass
class RequirementSpec:
    """
    Formal requirement specification.
    """

    id: str
    title: str
    description: str
    requirement_type: str = "functional"  # functional | non_functional
    is_verifiable: bool = True
    priority: int | None = None  # 1-10
    source: str | None = None


@dataclass
class UseCase:
    """
    Structured use case with flows.
    """

    id: str
    title: str
    actors: list[str]
    preconditions: list[str] = field(default_factory=list)
    trigger: str | None = None
    main_flow: list[str] = field(default_factory=list)
    alt_flows: list[list[str]] = field(default_factory=list)
    postconditions: list[str] = field(default_factory=list)


@dataclass
class TestCase:
    """
    Executable test case linked to an acceptance criterion or item.
    """

    id: str
    name: str
    test_type: str = "bdd"  # bdd | ui | api | unit | integration
    command: str | None = None  # runner command or reference
    acceptance_criterion_id: str | None = None
    last_result: str = "unknown"  # passed | failed | unknown
    last_run_at: datetime | None = None
    evidence_paths: list[str] = field(default_factory=list)
