"""Team management classes for the project graph system.

This module contains classes for managing teams and team members.
"""

from dataclasses import dataclass, field


@dataclass
class TeamMember:
    """
    Represents a team member with skills and availability.
    """

    id: str
    name: str
    email: str
    skills: set[str] = field(default_factory=set)
    availability: float = 1.0  # 0.0 to 1.0, representing percentage availability
    hourly_rate: float | None = None
    role: str = "developer"

    def __post_init__(self):
        if not isinstance(self.skills, set):
            self.skills = set(self.skills) if self.skills else set()


@dataclass
class Team:
    """
    Represents a team with multiple members.
    """

    id: str
    name: str
    members: list[TeamMember] = field(default_factory=list)
    lead_id: str | None = None
    budget: float | None = None

    def get_total_capacity(self) -> float:
        """
        Get total team capacity (sum of all member availability).
        """
        return sum(member.availability for member in self.members)

    def get_skills(self) -> set[str]:
        """
        Get all skills available in the team.
        """
        skills = set()
        for member in self.members:
            skills.update(member.skills)
        return skills

    def get_member(self, member_id: str) -> TeamMember | None:
        """
        Get a team member by ID.
        """
        for member in self.members:
            if member.id == member_id:
                return member
        return None
