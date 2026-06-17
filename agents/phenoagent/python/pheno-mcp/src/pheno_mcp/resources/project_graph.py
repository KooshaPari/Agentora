"""
Project Graph Cross-Communication System with LangGraph Integration - Refactored Version

Enables cross-tool communication and coordination for complex project workflows.
Implements a project graph that tracks dependencies, state, and communication
between different tools and processes within the MCP ecosystem.

Features:
- Project state tracking and coordination
- Cross-tool communication protocols
- Dependency management and resolution
- Workflow orchestration and scheduling
- Context sharing and persistence
- Multi-tool collaboration patterns
- LangGraph state persistence and checkpointing
- Visual graph representation for organizational workflows
"""

# Simple logging for pheno-sdk
import logging
import uuid
from dataclasses import asdict
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

from .analysis import CommunicationMessage, CriticalPathAnalysis

# Import our refactored modules
from .enums import NodeStatus, NodeType
from .graph import GraphNode, WBSNode
from .project import (
    AcceptanceCriterion,
    Deliverable,
    QualityGate,
    RequirementSpec,
    TestCase,
    UseCase,
    UserStory,
)
from .team import Team, TeamMember

# Export key classes for easy access
__all__ = [
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
    "Team",
    "TeamMember",
    "TestCase",
    "UseCase",
    "UserStory",
    "WBSNode",
]


class ProjectGraph:
    """Project graph for cross-tool communication and workflow orchestration.

    Manages the state and coordination of complex multi-tool projects by:
    - Tracking dependencies between tasks and tools
    - Facilitating communication between different tool executions
    - Managing project state and context sharing
    - Orchestrating workflow execution based on dependencies
    """

    def __init__(self, project_id: str | None = None):
        self.project_id = project_id or str(uuid.uuid4())
        self.nodes: dict[str, GraphNode] = {}
        self.messages: list[CommunicationMessage] = []
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.metadata: dict[str, Any] = {}  # Add metadata attribute for pm_admin compatibility

        # Execution state
        self.execution_queue: list[str] = []
        self.active_nodes: set[str] = set()
        self.completed_nodes: set[str] = set()

        # WBS-specific attributes
        self.teams: dict[str, Team] = {}
        self.critical_path_analysis: CriticalPathAnalysis | None = None
        self.wbs_counter: dict[str, int] = {}  # For generating WBS codes

        logger.info(f"Initialized project graph: {self.project_id}")

        # PM state model (Kanban/Scrum-like). Stored per node in node.metadata['pm_state']
        self.pm_states: list[str] = [
            "new",
            "triage",
            "verifying",
            "ready",
            "in_progress",
            "review",
            "changes_requested",
            "done",
            "closed",
        ]
        # Allowed transitions map (subset; minimal viable)
        self.pm_allowed_transitions: dict[str, set[str]] = {
            "new": {"triage"},
            "triage": {"verifying", "ready"},
            "verifying": {"ready", "needs_info"},
            "ready": {"in_progress"},
            "in_progress": {"review", "blocked"},
            "review": {"done", "changes_requested"},
            "changes_requested": {"in_progress"},
            "done": {"closed"},
        }

    def add_team(self, team: Team) -> None:
        """
        Add a team to the project.
        """
        self.teams[team.id] = team
        logger.info(f"Added team '{team.name}' with {len(team.members)} members")

    def create_wbs_node(
        self,
        name: str,
        node_type: NodeType,
        description: str | None = None,
        parent_id: str | None = None,
        assigned_team_id: str | None = None,
        estimated_duration: timedelta | None = None,
        deliverables: list[Deliverable] | None = None,
        acceptance_criteria: list[AcceptanceCriterion] | None = None,
        priority: int = 5,
    ) -> str:
        """
        Create a WBS node with enhanced project management features.
        """

        # Generate WBS code
        wbs_code = self._generate_wbs_code(parent_id)

        # Create the node using regular create_node first
        node_id = self.create_node(
            name=name,
            node_type=node_type,
            description=description,
            parent_id=parent_id,
            priority=priority,
        )

        # Convert to WBSNode and enhance with WBS-specific features
        node = self.nodes[node_id]
        node.wbs_code = wbs_code
        node.assigned_team_id = assigned_team_id
        node.estimated_duration = estimated_duration

        if deliverables:
            node.deliverables.extend(deliverables)
        if acceptance_criteria:
            node.acceptance_criteria.extend(acceptance_criteria)

        # Validate team assignment
        if assigned_team_id and assigned_team_id not in self.teams:
            logger.warning(f"Team {assigned_team_id} not found for WBS node {node_id}")

        logger.info(f"Created WBS node {node_id} ({name}) with code {wbs_code}")
        return node_id

    def create_node(
        self,
        name: str,
        node_type: NodeType,
        description: str | None = None,
        parent_id: str | None = None,
        priority: int = 5,
        tool_name: str | None = None,
        tool_args: dict[str, Any] | None = None,
        assigned_to: list[str] | None = None,
        estimated_duration: timedelta | None = None,
    ) -> str:
        """
        Create a new node in the project graph.
        """
        node_id = str(uuid.uuid4())
        now = datetime.now()

        node = GraphNode(
            id=node_id,
            name=name,
            type=node_type,
            status=NodeStatus.PLANNED,
            created_at=now,
            updated_at=now,
            description=description,
            parent_id=parent_id,
            priority=priority,
            tool_name=tool_name,
            tool_args=tool_args or {},
            assigned_to=assigned_to or [],
            estimated_duration=estimated_duration,
        )

        self.nodes[node_id] = node

        # Update parent-child relationships
        if parent_id and parent_id in self.nodes:
            self.nodes[parent_id].children_ids.add(node_id)

        # Initialize PM state
        node.metadata["pm_state"] = "new"

        self.updated_at = now
        logger.info(f"Created node {node_id} ({name}) of type {node_type.value}")

        return node_id

    def add_dependency(self, from_node_id: str, to_node_id: str) -> None:
        """
        Add a dependency between two nodes.
        """
        if from_node_id not in self.nodes or to_node_id not in self.nodes:
            logger.error("Cannot add dependency: one or both nodes not found")
            return

        self.nodes[from_node_id].dependencies.add(to_node_id)
        self.nodes[to_node_id].dependents.add(from_node_id)

        logger.info(f"Added dependency: {from_node_id} depends on {to_node_id}")

    def remove_dependency(self, from_node_id: str, to_node_id: str) -> None:
        """
        Remove a dependency between two nodes.
        """
        if from_node_id in self.nodes:
            self.nodes[from_node_id].dependencies.discard(to_node_id)
        if to_node_id in self.nodes:
            self.nodes[to_node_id].dependents.discard(from_node_id)

        logger.info(f"Removed dependency: {from_node_id} no longer depends on {to_node_id}")

    def get_ready_nodes(self) -> list[str]:
        """
        Get nodes that are ready to execute (all dependencies satisfied).
        """
        ready = []
        for node_id, node in self.nodes.items():
            if node.status == NodeStatus.PLANNED:
                # Check if all dependencies are completed
                if all(
                    dep_id in self.completed_nodes or dep_id not in self.nodes
                    for dep_id in node.dependencies
                ):
                    ready.append(node_id)
        return ready

    def start_node(self, node_id: str) -> bool:
        """
        Start execution of a node.
        """
        if node_id not in self.nodes:
            logger.error(f"Node {node_id} not found")
            return False

        node = self.nodes[node_id]
        if node.status != NodeStatus.PLANNED:
            logger.warning(f"Node {node_id} is not in planned status")
            return False

        node.status = NodeStatus.IN_PROGRESS
        node.updated_at = datetime.now()
        self.active_nodes.add(node_id)

        logger.info(f"Started execution of node {node_id} ({node.name})")
        return True

    def complete_node(self, node_id: str, result: dict[str, Any] | None = None) -> bool:
        """
        Mark a node as completed.
        """
        if node_id not in self.nodes:
            logger.error(f"Node {node_id} not found")
            return False

        node = self.nodes[node_id]
        node.status = NodeStatus.COMPLETED
        node.updated_at = datetime.now()
        node.tool_result = result or {}

        self.active_nodes.discard(node_id)
        self.completed_nodes.add(node_id)

        logger.info(f"Completed node {node_id} ({node.name})")
        return True

    def fail_node(self, node_id: str, error: str | None = None) -> bool:
        """
        Mark a node as failed.
        """
        if node_id not in self.nodes:
            logger.error(f"Node {node_id} not found")
            return False

        node = self.nodes[node_id]
        node.status = NodeStatus.FAILED
        node.updated_at = datetime.now()
        if error:
            node.metadata["error"] = error

        self.active_nodes.discard(node_id)

        logger.warning(f"Failed node {node_id} ({node.name}): {error or 'Unknown error'}")
        return True

    def send_message(
        self,
        from_node: str,
        to_nodes: list[str],
        message_type: str,
        content: dict[str, Any],
    ) -> str:
        """
        Send a message between nodes.
        """
        message_id = str(uuid.uuid4())
        message = CommunicationMessage(
            id=message_id,
            from_node=from_node,
            to_nodes=to_nodes,
            message_type=message_type,
            content=content,
            timestamp=datetime.now(),
        )

        self.messages.append(message)
        logger.info(f"Sent message {message_id} from {from_node} to {to_nodes}")

        return message_id

    def get_messages_for_node(self, node_id: str) -> list[CommunicationMessage]:
        """
        Get all messages for a specific node.
        """
        return [msg for msg in self.messages if node_id in msg.to_nodes]

    def get_node_status(self, node_id: str) -> NodeStatus | None:
        """
        Get the status of a specific node.
        """
        if node_id in self.nodes:
            return self.nodes[node_id].status
        return None

    def get_project_summary(self) -> dict[str, Any]:
        """
        Get a summary of the project state.
        """
        total_nodes = len(self.nodes)
        completed = len(self.completed_nodes)
        active = len(self.active_nodes)
        planned = total_nodes - completed - active

        return {
            "project_id": self.project_id,
            "total_nodes": total_nodes,
            "completed": completed,
            "active": active,
            "planned": planned,
            "completion_percentage": (completed / total_nodes * 100) if total_nodes > 0 else 0,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def _generate_wbs_code(self, parent_id: str | None = None) -> str:
        """
        Generate WBS code for a new node.
        """
        if parent_id is None:
            # Root level
            self.wbs_counter[""] = self.wbs_counter.get("", 0) + 1
            return f"{self.wbs_counter['']}.0"
        # Child level
        parent_code = self.nodes.get(parent_id, {}).wbs_code or "1.0"
        parent_code.count(".") + 1
        level_key = parent_code

        self.wbs_counter[level_key] = self.wbs_counter.get(level_key, 0) + 1
        return f"{parent_code}.{self.wbs_counter[level_key]}"

    def get_critical_path(self) -> CriticalPathAnalysis | None:
        """
        Calculate and return critical path analysis.
        """
        # This is a simplified implementation
        # In practice, this would use proper critical path method (CPM) algorithm

        if not self.nodes:
            return None

        # For now, return a basic analysis
        # A full implementation would calculate actual critical path
        all_nodes = list(self.nodes.keys())
        critical_path = all_nodes[:3] if len(all_nodes) >= 3 else all_nodes

        total_duration = sum(
            (node.estimated_duration or timedelta(hours=1)).total_seconds()
            for node in self.nodes.values()
        )

        critical_duration = sum(
            (self.nodes[node_id].estimated_duration or timedelta(hours=1)).total_seconds()
            for node_id in critical_path
        )

        self.critical_path_analysis = CriticalPathAnalysis(
            critical_path=critical_path,
            critical_path_duration=timedelta(seconds=critical_duration),
            total_project_duration=timedelta(seconds=total_duration),
            slack_times={node_id: timedelta(0) for node_id in critical_path},
            critical_activities=critical_path,
        )

        return self.critical_path_analysis

    def export_to_dict(self) -> dict[str, Any]:
        """
        Export the project graph to a dictionary.
        """
        return {
            "project_id": self.project_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "nodes": {node_id: asdict(node) for node_id, node in self.nodes.items()},
            "messages": [asdict(msg) for msg in self.messages],
            "metadata": self.metadata,
        }

    def import_from_dict(self, data: dict[str, Any]) -> None:
        """
        Import a project graph from a dictionary.
        """
        self._import_basic_properties(data)
        self._import_nodes(data)
        self._import_messages(data)

        logger.info(
            f"Imported project graph with {len(self.nodes)} nodes and {len(self.messages)} messages",
        )

    def _import_basic_properties(self, data: dict[str, Any]) -> None:
        """
        Import basic graph properties from data.
        """
        self.project_id = data.get("project_id", str(uuid.uuid4()))
        self.created_at = datetime.fromisoformat(data.get("created_at", datetime.now().isoformat()))
        self.updated_at = datetime.fromisoformat(data.get("updated_at", datetime.now().isoformat()))
        self.metadata = data.get("metadata", {})

    def _import_nodes(self, data: dict[str, Any]) -> None:
        """
        Import nodes from data.
        """
        self.nodes = {}
        for node_id, node_data in data.get("nodes", {}).items():
            processed_node_data = self._process_node_data(node_data)
            self.nodes[node_id] = GraphNode(**processed_node_data)

    def _process_node_data(self, node_data: dict[str, Any]) -> dict[str, Any]:
        """
        Process node data by converting types and enums.
        """
        # Convert datetime strings back to datetime objects
        if "created_at" in node_data:
            node_data["created_at"] = datetime.fromisoformat(node_data["created_at"])
        if "updated_at" in node_data:
            node_data["updated_at"] = datetime.fromisoformat(node_data["updated_at"])

        # Convert NodeType and NodeStatus enums
        if "type" in node_data:
            node_data["type"] = NodeType(node_data["type"])
        if "status" in node_data:
            node_data["status"] = NodeStatus(node_data["status"])

        return node_data

    def _import_messages(self, data: dict[str, Any]) -> None:
        """
        Import messages from data.
        """
        self.messages = []
        for msg_data in data.get("messages", []):
            processed_msg_data = self._process_message_data(msg_data)
            self.messages.append(CommunicationMessage(**processed_msg_data))

    def _process_message_data(self, msg_data: dict[str, Any]) -> dict[str, Any]:
        """
        Process message data by converting types.
        """
        if "timestamp" in msg_data:
            msg_data["timestamp"] = datetime.fromisoformat(msg_data["timestamp"])
        return msg_data
