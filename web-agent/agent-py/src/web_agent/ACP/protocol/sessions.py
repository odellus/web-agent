"""Agent Client Protocol (ACP) session management.

This module provides session management functionality for ACP, including
session creation, state tracking, and cleanup.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class SessionState:
    """ACP session state."""

    session_id: str
    working_directory: Path
    created_at: float
    last_activity: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    mode: str = "execute"
    model: str = "qwen3:latest"
    is_active: bool = True
    message_count: int = 0
    tool_calls: int = 0

    def update_activity(self):
        """Update the last activity timestamp."""
        self.last_activity = time.time()

    def increment_message_count(self):
        """Increment the message counter."""
        self.message_count += 1
        self.update_activity()

    def increment_tool_calls(self):
        """Increment the tool call counter."""
        self.tool_calls += 1
        self.update_activity()


class SessionManager:
    """Manages ACP sessions with lifecycle and cleanup."""

    def __init__(self, session_timeout: float = 3600.0, max_sessions: int = 100):
        """Initialize session manager.

        Args:
            session_timeout: Session timeout in seconds (default: 1 hour)
            max_sessions: Maximum number of concurrent sessions
        """
        self.sessions: Dict[str, SessionState] = {}
        self.session_timeout = session_timeout
        self.max_sessions = max_sessions
        self._cleanup_task: Optional[asyncio.Task] = None
        self._cleanup_interval = 300.0  # 5 minutes
        self._running = False

    async def start(self):
        """Start the session manager and cleanup task."""
        if self._running:
            return

        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Session manager started")

    async def stop(self):
        """Stop the session manager and cleanup task."""
        if not self._running:
            return

        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # Clear all sessions
        self.sessions.clear()
        logger.info("Session manager stopped")

    async def create_session(
        self,
        session_id: str,
        working_directory: Path,
        metadata: Optional[Dict[str, Any]] = None,
        mode: str = "execute",
        model: str = "qwen3:latest",
    ) -> SessionState:
        """Create a new session.

        Args:
            session_id: Unique session identifier
            working_directory: Working directory for the session
            metadata: Optional session metadata
            mode: Initial session mode
            model: Initial model to use

        Returns:
            Created session state

        Raises:
            RuntimeError: If maximum sessions reached
            ValueError: If session ID already exists
        """
        if len(self.sessions) >= self.max_sessions:
            raise RuntimeError(f"Maximum sessions ({self.max_sessions}) reached")

        if session_id in self.sessions:
            raise ValueError(f"Session {session_id} already exists")

        session = SessionState(
            session_id=session_id,
            working_directory=working_directory,
            created_at=time.time(),
            last_activity=time.time(),
            metadata=metadata or {},
            mode=mode,
            model=model,
        )

        self.sessions[session_id] = session
        logger.info(f"Created session {session_id} in {working_directory}")

        return session

    async def get_session(self, session_id: str) -> Optional[SessionState]:
        """Get a session by ID.

        Args:
            session_id: Session identifier

        Returns:
            Session state or None if not found
        """
        session = self.sessions.get(session_id)
        if session and session.is_active:
            session.update_activity()
            return session
        return None

    async def update_session(self, session_id: str, **kwargs) -> Optional[SessionState]:
        """Update session properties.

        Args:
            session_id: Session identifier
            **kwargs: Properties to update

        Returns:
            Updated session state or None if not found
        """
        session = await self.get_session(session_id)
        if not session:
            return None

        for key, value in kwargs.items():
            if hasattr(session, key):
                setattr(session, key, value)

        session.update_activity()
        logger.debug(f"Updated session {session_id}: {kwargs}")

        return session

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session.

        Args:
            session_id: Session identifier

        Returns:
            True if session was deleted, False if not found
        """
        session = self.sessions.pop(session_id, None)
        if session:
            logger.info(f"Deleted session {session_id}")
            return True
        return False

    async def list_sessions(self) -> List[SessionState]:
        """List all active sessions.

        Returns:
            List of active session states
        """
        return [session for session in self.sessions.values() if session.is_active]

    async def get_expired_sessions(self) -> List[str]:
        """Get list of expired session IDs.

        Returns:
            List of expired session IDs
        """
        current_time = time.time()
        expired = []

        for session_id, session in self.sessions.items():
            if current_time - session.last_activity > self.session_timeout:
                expired.append(session_id)

        return expired

    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions.

        Returns:
            Number of sessions cleaned up
        """
        expired_ids = await self.get_expired_sessions()
        cleaned = 0

        for session_id in expired_ids:
            if await self.delete_session(session_id):
                cleaned += 1
                logger.info(f"Cleaned up expired session {session_id}")

        return cleaned

    async def _cleanup_loop(self):
        """Background cleanup loop."""
        while self._running:
            try:
                await asyncio.sleep(self._cleanup_interval)
                cleaned = await self.cleanup_expired_sessions()
                if cleaned > 0:
                    logger.info(f"Cleaned up {cleaned} expired sessions")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")

    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics.

        Returns:
            Dictionary with session statistics
        """
        active_sessions = len(self.sessions)
        total_messages = sum(s.message_count for s in self.sessions.values())
        total_tool_calls = sum(s.tool_calls for s in self.sessions.values())

        return {
            "active_sessions": active_sessions,
            "max_sessions": self.max_sessions,
            "total_messages": total_messages,
            "total_tool_calls": total_tool_calls,
            "session_timeout": self.session_timeout,
        }


# Global session manager instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get the global session manager instance.

    Returns:
        Session manager instance
    """
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


async def initialize_session_manager(
    session_timeout: float = 3600.0, max_sessions: int = 100
) -> SessionManager:
    """Initialize the global session manager.

    Args:
        session_timeout: Session timeout in seconds
        max_sessions: Maximum number of concurrent sessions

    Returns:
        Initialized session manager
    """
    global _session_manager
    _session_manager = SessionManager(
        session_timeout=session_timeout, max_sessions=max_sessions
    )
    await _session_manager.start()
    return _session_manager
