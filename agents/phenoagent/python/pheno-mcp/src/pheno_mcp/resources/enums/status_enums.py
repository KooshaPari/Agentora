"""Status enums and enumeration types for the project graph system.

This module contains all the enumeration types used throughout the project graph.
"""

from enum import Enum


class NodeType(Enum):
    """
    Types of nodes in the project graph.
    """

    PROJECT = "project"
    TASK = "task"
    TOOL_EXECUTION = "tool_execution"
    WORKFLOW = "workflow"
    RESOURCE = "resource"
    MILESTONE = "milestone"
    COMMUNICATION = "communication"
    # WBS-specific node types
    WBS_PROJECT = "wbs_project"
    WBS_WORK_PACKAGE = "wbs_work_package"
    WBS_ACTIVITY = "wbs_activity"
    QUALITY_GATE = "quality_gate"
    DELIVERABLE = "deliverable"
    # PM/Portfolio-specific node types
    PORTFOLIO = "portfolio"
    PROGRAM = "program"
    SUBPROJECT = "subproject"
    EPIC = "epic"
    STORY = "story"
    BUG = "bug"
    REQUIREMENT = "requirement"
    USE_CASE = "use_case"
    TEST_CASE = "test_case"
    ITERATION = "iteration"
    RELEASE = "release"


class NodeStatus(Enum):
    """
    Status of nodes in the project graph.
    """

    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"


class AcceptanceStatus(Enum):
    """
    Status of acceptance criteria.
    """

    PENDING = "pending"
    IN_REVIEW = "in_review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    NOT_APPLICABLE = "not_applicable"


class QualityGateStatus(Enum):
    """
    Status of quality gates.
    """

    OPEN = "open"
    IN_REVIEW = "in_review"
    PASSED = "passed"
    FAILED = "failed"
    WAIVED = "waived"
