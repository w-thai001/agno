"""Session Manager Finite State Automaton for session lifecycle management."""

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class State(Enum):
    """FSA states for session lifecycle."""
    CREATED = "created"
    ACTIVE = "active"
    EXPIRED = "expired"
    DESTROYED = "destroyed"


@dataclass
class Session:
    """Represents a user session."""
    session_id: str
    state: State
    created_at: float
    last_accessed: float
    ttl: float
    data: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if session has expired."""
        return time.time() - self.last_accessed > self.ttl

    def touch(self):
        """Update last accessed time."""
        self.last_accessed = time.time()


class SessionManagerFSA:
    """Finite State Automaton for managing user sessions."""

    def __init__(self, default_ttl: float = 3600.0, cleanup_interval: float = 60.0):
        self.default_ttl = default_ttl
        self.cleanup_interval = cleanup_interval
        self._sessions: Dict[str, Session] = {}
        self._lock = threading.Lock()
        self._cleanup_timer: Optional[threading.Timer] = None
        self._start_cleanup()
        logger.info(f"Session manager initialized (TTL: {default_ttl}s)")

    def create_session(self, session_id: Optional[str] = None, ttl: Optional[float] = None, **data) -> Session:
        """Create a new session."""
        with self._lock:
            session_id = session_id or str(uuid.uuid4())

            if session_id in self._sessions:
                raise ValueError(f"Session {session_id} already exists")

            ttl = ttl or self.default_ttl
            now = time.time()

            session = Session(
                session_id=session_id,
                state=State.CREATED,
                created_at=now,
                last_accessed=now,
                ttl=ttl,
                data=data
            )

            self._sessions[session_id] = session
            self._transition(session, State.CREATED, State.ACTIVE)
            logger.info(f"Created session {session_id} (TTL: {ttl}s)")
            return session

    def get_session(self, session_id: str, touch: bool = True) -> Optional[Session]:
        """Retrieve session by ID."""
        with self._lock:
            session = self._sessions.get(session_id)

            if not session:
                logger.debug(f"Session {session_id} not found")
                return None

            if session.state == State.DESTROYED:
                logger.debug(f"Session {session_id} is destroyed")
                return None

            if session.is_expired():
                logger.info(f"Session {session_id} expired")
                self._expire_session(session)
                return None

            if touch:
                session.touch()
                logger.debug(f"Accessed session {session_id}")

            return session

    def update_session(self, session_id: str, **data) -> bool:
        """Update session data."""
        session = self.get_session(session_id)
        if not session:
            return False

        with self._lock:
            session.data.update(data)
            session.touch()
            logger.debug(f"Updated session {session_id}")
            return True

    def destroy_session(self, session_id: str) -> bool:
        """Destroy a session."""
        with self._lock:
            session = self._sessions.get(session_id)

            if not session or session.state == State.DESTROYED:
                return False

            self._transition(session, session.state, State.DESTROYED)
            del self._sessions[session_id]
            logger.info(f"Destroyed session {session_id}")
            return True

    def extend_session(self, session_id: str, additional_ttl: float) -> bool:
        """Extend session TTL."""
        session = self.get_session(session_id, touch=False)
        if not session:
            return False

        with self._lock:
            session.ttl += additional_ttl
            session.touch()
            logger.info(f"Extended session {session_id} by {additional_ttl}s")
            return True

    def cleanup_expired(self) -> int:
        """Remove all expired sessions."""
        with self._lock:
            expired = []

            for session_id, session in list(self._sessions.items()):
                if session.is_expired() and session.state != State.DESTROYED:
                    expired.append(session)

            for session in expired:
                self._expire_session(session)

            count = len(expired)
            if count > 0:
                logger.info(f"Cleaned up {count} expired sessions")
            return count

    def get_stats(self) -> Dict[str, Any]:
        """Get session statistics."""
        with self._lock:
            active = sum(1 for s in self._sessions.values() if s.state == State.ACTIVE)
            expired = sum(1 for s in self._sessions.values() if s.state == State.EXPIRED)

            return {
                "total_sessions": len(self._sessions),
                "active_sessions": active,
                "expired_sessions": expired,
                "default_ttl": self.default_ttl
            }

    def shutdown(self):
        """Shutdown session manager and cleanup."""
        if self._cleanup_timer:
            self._cleanup_timer.cancel()
            self._cleanup_timer = None

        with self._lock:
            logger.info(f"Shutting down session manager ({len(self._sessions)} sessions)")
            self._sessions.clear()

    def _expire_session(self, session: Session):
        """Mark session as expired."""
        self._transition(session, session.state, State.EXPIRED)
        del self._sessions[session.session_id]

    def _start_cleanup(self):
        """Start periodic cleanup timer."""
        self.cleanup_expired()
        self._cleanup_timer = threading.Timer(self.cleanup_interval, self._start_cleanup)
        self._cleanup_timer.daemon = True
        self._cleanup_timer.start()

    def _transition(self, session: Session, from_state: State, to_state: State):
        """Transition session state."""
        session.state = to_state
        logger.debug(f"Session {session.session_id}: {from_state.value} -> {to_state.value}")
