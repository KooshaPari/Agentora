"""
Real-time team presence tracking.
"""

import time
from typing import Dict, List, Optional

from .models import PresenceInfo


class TeamPresenceTracker:
    """
    Track who's testing what in real-time.
    """

    def __init__(self):
        self.presence: Dict[str, PresenceInfo] = {}
        self.timeout = 300  # 5 minutes timeout

    def update_presence(
        self, user: str, endpoint: str, test_name: Optional[str] = None, status: str = "testing"
    ):
        """
        Update user presence information.
        """
        self.presence[user] = PresenceInfo(
            user=user, endpoint=endpoint, test_name=test_name, status=status, last_seen=time.time()
        )

    def remove_presence(self, user: str):
        """
        Remove user presence.
        """
        self.presence.pop(user, None)

    def get_presence(self, user: str) -> Optional[PresenceInfo]:
        """
        Get presence information for a user.
        """
        return self.presence.get(user)

    def get_all_presence(self) -> List[PresenceInfo]:
        """
        Get all presence information.
        """
        current_time = time.time()
        stale_users = [
            user
            for user, info in self.presence.items()
            if current_time - info.last_seen > self.timeout
        ]
        for user in stale_users:
            self.presence.pop(user)

        return list(self.presence.values())

    def who_is_testing(self, test_name: str) -> List[str]:
        """
        Get list of users currently testing a specific test.
        """
        return [
            info.user
            for info in self.presence.values()
            if info.test_name == test_name and info.status == "testing"
        ]

    def who_is_on_endpoint(self, endpoint: str) -> List[str]:
        """
        Get list of users on a specific endpoint.
        """
        return [info.user for info in self.presence.values() if info.endpoint == endpoint]
