"""Analysis classes for the project graph system.

This module contains classes for critical path analysis and communication.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any


@dataclass
class CriticalPathAnalysis:
    """
    Results of critical path analysis.
    """

    critical_path: list[str]  # List of node IDs in critical path
    critical_path_duration: timedelta
    total_project_duration: timedelta
    slack_times: dict[str, timedelta]  # Node ID to slack time
    critical_activities: list[str]  # Node IDs with zero slack

    def get_critical_path_names(self, graph: "ProjectGraph") -> list[str]:
        """
        Get names of nodes in the critical path.
        """
        return [
            graph.nodes[node_id].name for node_id in self.critical_path if node_id in graph.nodes
        ]

    def is_critical(self, node_id: str) -> bool:
        """
        Check if a node is on the critical path.
        """
        return node_id in self.critical_activities

    def get_slack_time(self, node_id: str) -> timedelta:
        """
        Get slack time for a node.
        """
        return self.slack_times.get(node_id, timedelta(0))


@dataclass
class CommunicationMessage:
    """
    A message in the project graph communication system.
    """

    id: str
    from_node: str
    to_nodes: list[str]
    message_type: str
    content: dict[str, Any]
    timestamp: datetime
    read_by: set[str] = None

    def __post_init__(self):
        if self.read_by is None:
            self.read_by = set()
