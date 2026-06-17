"""In-Memory Session Manager.

Implementation of SessionManager for managing MCP sessions.
"""

import logging
from typing import Any

from pheno.mcp.types import McpServer, McpSession, SessionStatus
from pheno.ports.mcp import SessionManager

logger = logging.getLogger(__name__)


class InMemorySessionManager(SessionManager):
    """In-memory session manager implementation.

    Manages MCP sessions in memory with metadata tracking.

    Example:
        >>> manager = InMemorySessionManager()
        >>> session = await manager.create_session(server)
        >>> sessions = manager.list_sessions()
        >>> await manager.close_session(session)
    """

    def __init__(self):
        self._sessions: dict[str, McpSession] = {}
        self._metadata: dict[str, dict[str, Any]] = {}

    async def create_session(
        self, server: McpServer, metadata: dict[str, Any] | None = None,
    ) -> McpSession:
        """
        Create a new MCP session.
        """
        session = McpSession(
            session_id="", server=server, status=SessionStatus.CONNECTED,  # Will be auto-generated
        )

        self._sessions[session.session_id] = session
        self._metadata[session.session_id] = metadata or {}

        logger.info(f"Created session {session.session_id} for {server.name}")
        return session

    async def close_session(self, session: McpSession) -> None:
        """
        Close an MCP session.
        """
        if session.session_id in self._sessions:
            session.status = SessionStatus.DISCONNECTED
            del self._sessions[session.session_id]

            if session.session_id in self._metadata:
                del self._metadata[session.session_id]

            logger.info(f"Closed session {session.session_id}")

    async def close_all_sessions(self) -> None:
        """
        Close all active sessions.
        """
        session_ids = list(self._sessions.keys())
        for session_id in session_ids:
            session = self._sessions[session_id]
            await self.close_session(session)

        logger.info(f"Closed all sessions ({len(session_ids)} total)")

    def get_session(self, session_id: str) -> McpSession | None:
        """
        Get a session by ID.
        """
        return self._sessions.get(session_id)

    def list_sessions(
        self, server: McpServer | None = None, active_only: bool = True,
    ) -> list[McpSession]:
        """
        List sessions.
        """
        sessions = list(self._sessions.values())

        # Filter by server
        if server:
            sessions = [s for s in sessions if s.server.url == server.url]

        # Filter by active status
        if active_only:
            sessions = [s for s in sessions if s.status == SessionStatus.CONNECTED]

        return sessions

    def is_active(self, session: McpSession) -> bool:
        """
        Check if a session is active.
        """
        return session.session_id in self._sessions and session.status == SessionStatus.CONNECTED

    async def refresh_session(self, session: McpSession) -> None:
        """
        Refresh a session.
        """
        if session.session_id in self._sessions:
            session.update_activity()
            logger.info(f"Refreshed session {session.session_id}")

    def get_session_metadata(self, session: McpSession) -> dict[str, Any]:
        """
        Get metadata for a session.
        """
        return self._metadata.get(session.session_id, {}).copy()

    def set_session_metadata(self, session: McpSession, metadata: dict[str, Any]) -> None:
        """
        Set metadata for a session.
        """
        if session.session_id in self._sessions:
            self._metadata[session.session_id] = metadata
            logger.info(f"Updated metadata for session {session.session_id}")

    async def get_or_create_session(self, server: McpServer, reuse: bool = True) -> McpSession:
        """
        Get existing session or create new one.
        """
        if reuse:
            # Try to find existing session for this server
            existing = self.list_sessions(server=server, active_only=True)
            if existing:
                logger.info(f"Reusing existing session for {server.name}")
                return existing[0]

        # Create new session
        return await self.create_session(server)

    def get_session_count(self, active_only: bool = True) -> int:
        """
        Get count of sessions.
        """
        if active_only:
            return len([s for s in self._sessions.values() if s.status == SessionStatus.CONNECTED])
        return len(self._sessions)


__all__ = ["InMemorySessionManager"]
