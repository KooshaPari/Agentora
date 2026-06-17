"""
Shared MCP resource templates and scheme helpers.
"""

from .project_graph import (
    AcceptanceCriterion,
    CommunicationMessage,
    CriticalPathAnalysis,
    Deliverable,
    GraphNode,
    NodeStatus,
    NodeType,
    ProjectGraph,
    QualityGate,
    RequirementSpec,
    Team,
    TeamMember,
    TestCase,
    UseCase,
    UserStory,
    WBSNode,
)
from .registry import ResourceRegistry
from .schemes import ResourceSchemeHandler, ResourceSchemeRegistry
from .shared_templates import ALL_SHARED_TEMPLATES, get_shared_templates
from .template_engine import (
    ResourceAnnotation,
    ResourceContext,
    ResourceParameter,
    ResourceTemplate,
    ResourceTemplateEngine,
)

__all__ = [
    "ALL_SHARED_TEMPLATES",
    "AcceptanceCriterion",
    "CommunicationMessage",
    "CriticalPathAnalysis",
    "Deliverable",
    "GraphNode",
    "NodeStatus",
    "NodeType",
    "ProjectGraph",
    "QualityGate",
    "RequirementSpec",
    "ResourceAnnotation",
    "ResourceContext",
    "ResourceParameter",
    "ResourceRegistry",
    "ResourceSchemeHandler",
    "ResourceSchemeRegistry",
    "ResourceTemplate",
    "ResourceTemplateEngine",
    "Team",
    "TeamMember",
    "TestCase",
    "UseCase",
    "UserStory",
    "WBSNode",
    "get_shared_templates",
]
