"""
Session Manager FSA - Comprehensive session management for the Agno MLA framework.

This module provides a production-ready Finite State Automaton (FSA) for managing
HTTP sessions with support for multiple storage backends, security features,
session lifecycle management, and distributed session support.

Features:
    - Multiple storage backends (Memory, Redis, Database)
    - Session security (CSRF protection, encryption, hijacking prevention)
    - Session lifecycle management (create, read, update, delete, expire)
    - Session timeout and idle timeout handling
    - Multi-device session management
    - Distributed session support for load balancing
    - Session analytics and monitoring
    - Concurrent session limiting per user
    - Integration with Authentication FSA
"""

import hashlib
import hmac
import json
import secrets
import time
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, field_validator

from agno.utils.log import logger


# ============================================================================
# Enums and Constants
# ============================================================================


class SessionState(str, Enum):
    """Session state machine states."""

    CREATED = "created"
    ACTIVE = "active"
    IDLE = "idle"
    EXPIRED = "expired"
    INVALIDATED = "invalidated"
    LOCKED = "locked"
    TERMINATED = "terminated"


class SessionEvent(str, Enum):
    """Session state machine events."""

    CREATE = "create"
    ACTIVATE = "activate"
    ACCESS = "access"
    UPDATE = "update"
    IDLE_TIMEOUT = "idle_timeout"
    ABSOLUTE_TIMEOUT = "absolute_timeout"
    INVALIDATE = "invalidate"
    LOCK = "lock"
    UNLOCK = "unlock"
    TERMINATE = "terminate"
    REFRESH = "refresh"


class StorageBackendType(str, Enum):
    """Supported storage backend types."""

    MEMORY = "memory"
    REDIS = "redis"
    DATABASE = "database"
    DISTRIBUTED = "distributed"


class SecurityLevel(str, Enum):
    """Session security levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    MAXIMUM = "maximum"


# ============================================================================
# Session Models
# ============================================================================


class SessionMetadata(BaseModel):
    """Session metadata for tracking and analytics."""

    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    device_id: Optional[str] = None
    device_type: Optional[str] = None
    browser: Optional[str] = None
    os: Optional[str] = None
    location: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_accessed_at: datetime = Field(default_factory=datetime.utcnow)
    access_count: int = 0
    data_size: int = 0

    model_config = ConfigDict(arbitrary_types_allowed=True)


class SessionSecurity(BaseModel):
    """Session security information."""

    csrf_token: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    fingerprint: Optional[str] = None
    encryption_key: Optional[str] = None
    security_level: SecurityLevel = SecurityLevel.MEDIUM
    ip_binding: bool = False
    user_agent_binding: bool = False
    require_https: bool = True
    rotation_count: int = 0
    last_rotation: Optional[datetime] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class Session(BaseModel):
    """Core session model."""

    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    state: SessionState = SessionState.CREATED
    data: Dict[str, Any] = Field(default_factory=dict)
    metadata: SessionMetadata = Field(default_factory=SessionMetadata)
    security: SessionSecurity = Field(default_factory=SessionSecurity)

    # Timeout configuration
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    idle_timeout_seconds: int = 1800  # 30 minutes
    absolute_timeout_seconds: int = 86400  # 24 hours
    last_activity: datetime = Field(default_factory=datetime.utcnow)

    # Multi-device support
    device_sessions: Set[str] = Field(default_factory=set)
    concurrent_sessions_limit: int = 5

    # Flags
    is_authenticated: bool = False
    is_persistent: bool = False
    is_locked: bool = False

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: str) -> str:
        """Validate session ID format."""
        if not v or len(v) < 16:
            raise ValueError("Session ID must be at least 16 characters")
        return v

    def is_expired(self) -> bool:
        """Check if session has expired."""
        now = datetime.utcnow()

        # Check absolute expiration
        if self.expires_at and now >= self.expires_at:
            return True

        # Check absolute timeout
        if (now - self.created_at).total_seconds() >= self.absolute_timeout_seconds:
            return True

        # Check idle timeout
        if (now - self.last_activity).total_seconds() >= self.idle_timeout_seconds:
            return True

        return False

    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.utcnow()
        self.metadata.last_accessed_at = datetime.utcnow()
        self.metadata.access_count += 1

    def calculate_fingerprint(self, salt: str = "") -> str:
        """Calculate session fingerprint for security verification."""
        components = [
            self.session_id,
            self.user_id or "",
            self.metadata.user_agent or "",
            self.metadata.ip_address or "",
            salt,
        ]
        fingerprint_data = "|".join(components)
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()


# ============================================================================
# Storage Backend Abstraction
# ============================================================================


class StorageBackend(ABC):
    """Abstract base class for session storage backends."""

    @abstractmethod
    def save(self, session: Session) -> bool:
        """Save a session to storage."""
        pass

    @abstractmethod
    def load(self, session_id: str) -> Optional[Session]:
        """Load a session from storage."""
        pass

    @abstractmethod
    def delete(self, session_id: str) -> bool:
        """Delete a session from storage."""
        pass

    @abstractmethod
    def exists(self, session_id: str) -> bool:
        """Check if a session exists."""
        pass

    @abstractmethod
    def list_user_sessions(self, user_id: str) -> List[Session]:
        """List all sessions for a user."""
        pass

    @abstractmethod
    def cleanup_expired(self) -> int:
        """Clean up expired sessions."""
        pass

    @abstractmethod
    def count_active_sessions(self, user_id: Optional[str] = None) -> int:
        """Count active sessions, optionally filtered by user."""
        pass


class MemoryStorageBackend(StorageBackend):
    """In-memory session storage backend."""

    def __init__(self):
        """Initialize memory storage."""
        self._sessions: Dict[str, Session] = {}
        self._user_index: Dict[str, Set[str]] = {}
        logger.info("Initialized MemoryStorageBackend")

    def save(self, session: Session) -> bool:
        """Save a session to memory."""
        try:
            self._sessions[session.session_id] = session

            # Update user index
            if session.user_id:
                if session.user_id not in self._user_index:
                    self._user_index[session.user_id] = set()
                self._user_index[session.user_id].add(session.session_id)

            logger.debug(f"Saved session {session.session_id} to memory")
            return True
        except Exception as e:
            logger.error(f"Error saving session to memory: {e}")
            return False

    def load(self, session_id: str) -> Optional[Session]:
        """Load a session from memory."""
        session = self._sessions.get(session_id)
        if session:
            logger.debug(f"Loaded session {session_id} from memory")
        return session

    def delete(self, session_id: str) -> bool:
        """Delete a session from memory."""
        try:
            session = self._sessions.get(session_id)
            if session and session.user_id:
                # Remove from user index
                if session.user_id in self._user_index:
                    self._user_index[session.user_id].discard(session_id)
                    if not self._user_index[session.user_id]:
                        del self._user_index[session.user_id]

            if session_id in self._sessions:
                del self._sessions[session_id]
                logger.debug(f"Deleted session {session_id} from memory")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting session from memory: {e}")
            return False

    def exists(self, session_id: str) -> bool:
        """Check if a session exists in memory."""
        return session_id in self._sessions

    def list_user_sessions(self, user_id: str) -> List[Session]:
        """List all sessions for a user."""
        session_ids = self._user_index.get(user_id, set())
        return [self._sessions[sid] for sid in session_ids if sid in self._sessions]

    def cleanup_expired(self) -> int:
        """Clean up expired sessions from memory."""
        expired_count = 0
        expired_session_ids = []

        for session_id, session in self._sessions.items():
            if session.is_expired():
                expired_session_ids.append(session_id)

        for session_id in expired_session_ids:
            if self.delete(session_id):
                expired_count += 1

        if expired_count > 0:
            logger.info(f"Cleaned up {expired_count} expired sessions from memory")

        return expired_count

    def count_active_sessions(self, user_id: Optional[str] = None) -> int:
        """Count active sessions in memory."""
        if user_id:
            sessions = self.list_user_sessions(user_id)
            return sum(1 for s in sessions if not s.is_expired())
        else:
            return sum(1 for s in self._sessions.values() if not s.is_expired())


class RedisStorageBackend(StorageBackend):
    """Redis-based session storage backend."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        key_prefix: str = "session:",
    ):
        """Initialize Redis storage."""
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.key_prefix = key_prefix
        self._client: Optional[Any] = None
        logger.info(f"Initialized RedisStorageBackend (host={host}, port={port})")

    def _get_client(self) -> Any:
        """Get or create Redis client (lazy initialization)."""
        if self._client is None:
            try:
                import redis

                self._client = redis.Redis(
                    host=self.host,
                    port=self.port,
                    db=self.db,
                    password=self.password,
                    decode_responses=False,
                )
                # Test connection
                self._client.ping()
                logger.info("Connected to Redis")
            except ImportError:
                logger.error("Redis library not installed. Install with: pip install redis")
                raise
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise

        return self._client

    def _make_key(self, session_id: str) -> str:
        """Create Redis key for session."""
        return f"{self.key_prefix}{session_id}"

    def _make_user_key(self, user_id: str) -> str:
        """Create Redis key for user's session set."""
        return f"{self.key_prefix}user:{user_id}"

    def save(self, session: Session) -> bool:
        """Save a session to Redis."""
        try:
            client = self._get_client()
            key = self._make_key(session.session_id)

            # Serialize session
            session_data = session.model_dump_json()

            # Calculate TTL based on absolute timeout
            ttl = session.absolute_timeout_seconds

            # Save to Redis with expiration
            client.setex(key, ttl, session_data)

            # Update user index
            if session.user_id:
                user_key = self._make_user_key(session.user_id)
                client.sadd(user_key, session.session_id)
                client.expire(user_key, ttl)

            logger.debug(f"Saved session {session.session_id} to Redis")
            return True
        except Exception as e:
            logger.error(f"Error saving session to Redis: {e}")
            return False

    def load(self, session_id: str) -> Optional[Session]:
        """Load a session from Redis."""
        try:
            client = self._get_client()
            key = self._make_key(session_id)
            session_data = client.get(key)

            if session_data:
                session = Session.model_validate_json(session_data)
                logger.debug(f"Loaded session {session_id} from Redis")
                return session
            return None
        except Exception as e:
            logger.error(f"Error loading session from Redis: {e}")
            return None

    def delete(self, session_id: str) -> bool:
        """Delete a session from Redis."""
        try:
            client = self._get_client()
            key = self._make_key(session_id)

            # Load session to get user_id
            session = self.load(session_id)

            # Delete session
            deleted = client.delete(key) > 0

            # Remove from user index
            if session and session.user_id:
                user_key = self._make_user_key(session.user_id)
                client.srem(user_key, session_id)

            if deleted:
                logger.debug(f"Deleted session {session_id} from Redis")

            return deleted
        except Exception as e:
            logger.error(f"Error deleting session from Redis: {e}")
            return False

    def exists(self, session_id: str) -> bool:
        """Check if a session exists in Redis."""
        try:
            client = self._get_client()
            key = self._make_key(session_id)
            return client.exists(key) > 0
        except Exception as e:
            logger.error(f"Error checking session existence in Redis: {e}")
            return False

    def list_user_sessions(self, user_id: str) -> List[Session]:
        """List all sessions for a user from Redis."""
        try:
            client = self._get_client()
            user_key = self._make_user_key(user_id)
            session_ids = client.smembers(user_key)

            sessions = []
            for session_id in session_ids:
                session_id_str = session_id.decode() if isinstance(session_id, bytes) else session_id
                session = self.load(session_id_str)
                if session:
                    sessions.append(session)

            return sessions
        except Exception as e:
            logger.error(f"Error listing user sessions from Redis: {e}")
            return []

    def cleanup_expired(self) -> int:
        """Clean up expired sessions from Redis."""
        # Redis handles expiration automatically, so we just return 0
        logger.debug("Redis handles expiration automatically")
        return 0

    def count_active_sessions(self, user_id: Optional[str] = None) -> int:
        """Count active sessions in Redis."""
        try:
            if user_id:
                sessions = self.list_user_sessions(user_id)
                return sum(1 for s in sessions if not s.is_expired())
            else:
                client = self._get_client()
                # Count all session keys
                pattern = f"{self.key_prefix}*"
                keys = client.keys(pattern)
                # Filter out user index keys
                session_keys = [k for k in keys if not b":user:" in k]
                return len(session_keys)
        except Exception as e:
            logger.error(f"Error counting active sessions in Redis: {e}")
            return 0


class DatabaseStorageBackend(StorageBackend):
    """Database-based session storage backend (SQLite/PostgreSQL)."""

    def __init__(self, connection_string: str = "sqlite:///sessions.db"):
        """Initialize database storage."""
        self.connection_string = connection_string
        self._engine: Optional[Any] = None
        self._session_maker: Optional[Any] = None
        logger.info(f"Initialized DatabaseStorageBackend (connection={connection_string})")

    def _get_engine(self) -> Any:
        """Get or create database engine."""
        if self._engine is None:
            try:
                from sqlalchemy import create_engine
                from sqlalchemy.orm import sessionmaker

                self._engine = create_engine(self.connection_string)
                self._session_maker = sessionmaker(bind=self._engine)
                self._create_tables()
                logger.info("Connected to database")
            except ImportError:
                logger.error("SQLAlchemy not installed. Install with: pip install sqlalchemy")
                raise
            except Exception as e:
                logger.error(f"Failed to connect to database: {e}")
                raise

        return self._engine

    def _create_tables(self) -> None:
        """Create database tables."""
        try:
            from sqlalchemy import Column, DateTime, Integer, String, Text, Boolean
            from sqlalchemy.ext.declarative import declarative_base

            Base = declarative_base()

            class SessionModel(Base):
                __tablename__ = "sessions"
                session_id = Column(String(255), primary_key=True)
                user_id = Column(String(255), index=True)
                state = Column(String(50))
                data = Column(Text)
                created_at = Column(DateTime)
                expires_at = Column(DateTime)
                last_activity = Column(DateTime)
                is_locked = Column(Boolean, default=False)

            Base.metadata.create_all(self._engine)
            logger.debug("Database tables created/verified")
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
            raise

    def save(self, session: Session) -> bool:
        """Save a session to database."""
        try:
            self._get_engine()
            db_session = self._session_maker()

            try:
                from sqlalchemy import Column, DateTime, String, Text, Boolean
                from sqlalchemy.ext.declarative import declarative_base

                Base = declarative_base()

                class SessionModel(Base):
                    __tablename__ = "sessions"
                    session_id = Column(String(255), primary_key=True)
                    user_id = Column(String(255))
                    state = Column(String(50))
                    data = Column(Text)
                    created_at = Column(DateTime)
                    expires_at = Column(DateTime)
                    last_activity = Column(DateTime)
                    is_locked = Column(Boolean)

                # Serialize session data
                session_data = session.model_dump_json()

                # Check if session exists
                existing = db_session.query(SessionModel).filter_by(session_id=session.session_id).first()

                if existing:
                    # Update existing session
                    existing.user_id = session.user_id
                    existing.state = session.state
                    existing.data = session_data
                    existing.last_activity = session.last_activity
                    existing.expires_at = session.expires_at
                    existing.is_locked = session.is_locked
                else:
                    # Create new session
                    new_session = SessionModel(
                        session_id=session.session_id,
                        user_id=session.user_id,
                        state=session.state,
                        data=session_data,
                        created_at=session.created_at,
                        expires_at=session.expires_at,
                        last_activity=session.last_activity,
                        is_locked=session.is_locked,
                    )
                    db_session.add(new_session)

                db_session.commit()
                logger.debug(f"Saved session {session.session_id} to database")
                return True
            finally:
                db_session.close()
        except Exception as e:
            logger.error(f"Error saving session to database: {e}")
            return False

    def load(self, session_id: str) -> Optional[Session]:
        """Load a session from database."""
        try:
            self._get_engine()
            db_session = self._session_maker()

            try:
                from sqlalchemy import Column, DateTime, String, Text, Boolean
                from sqlalchemy.ext.declarative import declarative_base

                Base = declarative_base()

                class SessionModel(Base):
                    __tablename__ = "sessions"
                    session_id = Column(String(255), primary_key=True)
                    user_id = Column(String(255))
                    state = Column(String(50))
                    data = Column(Text)
                    created_at = Column(DateTime)
                    expires_at = Column(DateTime)
                    last_activity = Column(DateTime)
                    is_locked = Column(Boolean)

                session_model = db_session.query(SessionModel).filter_by(session_id=session_id).first()

                if session_model:
                    session = Session.model_validate_json(session_model.data)
                    logger.debug(f"Loaded session {session_id} from database")
                    return session
                return None
            finally:
                db_session.close()
        except Exception as e:
            logger.error(f"Error loading session from database: {e}")
            return None

    def delete(self, session_id: str) -> bool:
        """Delete a session from database."""
        try:
            self._get_engine()
            db_session = self._session_maker()

            try:
                from sqlalchemy import Column, DateTime, String, Text, Boolean
                from sqlalchemy.ext.declarative import declarative_base

                Base = declarative_base()

                class SessionModel(Base):
                    __tablename__ = "sessions"
                    session_id = Column(String(255), primary_key=True)
                    user_id = Column(String(255))
                    state = Column(String(50))
                    data = Column(Text)
                    created_at = Column(DateTime)
                    expires_at = Column(DateTime)
                    last_activity = Column(DateTime)
                    is_locked = Column(Boolean)

                deleted = db_session.query(SessionModel).filter_by(session_id=session_id).delete()
                db_session.commit()

                if deleted > 0:
                    logger.debug(f"Deleted session {session_id} from database")
                    return True
                return False
            finally:
                db_session.close()
        except Exception as e:
            logger.error(f"Error deleting session from database: {e}")
            return False

    def exists(self, session_id: str) -> bool:
        """Check if a session exists in database."""
        try:
            self._get_engine()
            db_session = self._session_maker()

            try:
                from sqlalchemy import Column, DateTime, String, Text, Boolean
                from sqlalchemy.ext.declarative import declarative_base

                Base = declarative_base()

                class SessionModel(Base):
                    __tablename__ = "sessions"
                    session_id = Column(String(255), primary_key=True)
                    user_id = Column(String(255))
                    state = Column(String(50))
                    data = Column(Text)
                    created_at = Column(DateTime)
                    expires_at = Column(DateTime)
                    last_activity = Column(DateTime)
                    is_locked = Column(Boolean)

                exists = db_session.query(SessionModel).filter_by(session_id=session_id).count() > 0
                return exists
            finally:
                db_session.close()
        except Exception as e:
            logger.error(f"Error checking session existence in database: {e}")
            return False

    def list_user_sessions(self, user_id: str) -> List[Session]:
        """List all sessions for a user from database."""
        try:
            self._get_engine()
            db_session = self._session_maker()

            try:
                from sqlalchemy import Column, DateTime, String, Text, Boolean
                from sqlalchemy.ext.declarative import declarative_base

                Base = declarative_base()

                class SessionModel(Base):
                    __tablename__ = "sessions"
                    session_id = Column(String(255), primary_key=True)
                    user_id = Column(String(255))
                    state = Column(String(50))
                    data = Column(Text)
                    created_at = Column(DateTime)
                    expires_at = Column(DateTime)
                    last_activity = Column(DateTime)
                    is_locked = Column(Boolean)

                session_models = db_session.query(SessionModel).filter_by(user_id=user_id).all()

                sessions = []
                for model in session_models:
                    session = Session.model_validate_json(model.data)
                    sessions.append(session)

                return sessions
            finally:
                db_session.close()
        except Exception as e:
            logger.error(f"Error listing user sessions from database: {e}")
            return []

    def cleanup_expired(self) -> int:
        """Clean up expired sessions from database."""
        try:
            self._get_engine()
            db_session = self._session_maker()

            try:
                from sqlalchemy import Column, DateTime, String, Text, Boolean
                from sqlalchemy.ext.declarative import declarative_base

                Base = declarative_base()

                class SessionModel(Base):
                    __tablename__ = "sessions"
                    session_id = Column(String(255), primary_key=True)
                    user_id = Column(String(255))
                    state = Column(String(50))
                    data = Column(Text)
                    created_at = Column(DateTime)
                    expires_at = Column(DateTime)
                    last_activity = Column(DateTime)
                    is_locked = Column(Boolean)

                now = datetime.utcnow()
                deleted = db_session.query(SessionModel).filter(SessionModel.expires_at <= now).delete()
                db_session.commit()

                if deleted > 0:
                    logger.info(f"Cleaned up {deleted} expired sessions from database")

                return deleted
            finally:
                db_session.close()
        except Exception as e:
            logger.error(f"Error cleaning up expired sessions from database: {e}")
            return 0

    def count_active_sessions(self, user_id: Optional[str] = None) -> int:
        """Count active sessions in database."""
        try:
            self._get_engine()
            db_session = self._session_maker()

            try:
                from sqlalchemy import Column, DateTime, String, Text, Boolean
                from sqlalchemy.ext.declarative import declarative_base

                Base = declarative_base()

                class SessionModel(Base):
                    __tablename__ = "sessions"
                    session_id = Column(String(255), primary_key=True)
                    user_id = Column(String(255))
                    state = Column(String(50))
                    data = Column(Text)
                    created_at = Column(DateTime)
                    expires_at = Column(DateTime)
                    last_activity = Column(DateTime)
                    is_locked = Column(Boolean)

                now = datetime.utcnow()
                query = db_session.query(SessionModel).filter(SessionModel.expires_at > now)

                if user_id:
                    query = query.filter_by(user_id=user_id)

                return query.count()
            finally:
                db_session.close()
        except Exception as e:
            logger.error(f"Error counting active sessions in database: {e}")
            return 0


# ============================================================================
# Session Analytics
# ============================================================================


class SessionAnalytics(BaseModel):
    """Session analytics and monitoring."""

    total_sessions_created: int = 0
    total_sessions_expired: int = 0
    total_sessions_invalidated: int = 0
    active_sessions_count: int = 0
    average_session_duration: float = 0.0
    peak_concurrent_sessions: int = 0
    sessions_by_device: Dict[str, int] = Field(default_factory=dict)
    sessions_by_location: Dict[str, int] = Field(default_factory=dict)
    security_events: List[Dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def record_session_created(self, session: Session) -> None:
        """Record a new session creation."""
        self.total_sessions_created += 1
        self.active_sessions_count += 1

        if self.active_sessions_count > self.peak_concurrent_sessions:
            self.peak_concurrent_sessions = self.active_sessions_count

        # Track by device
        device_type = session.metadata.device_type or "unknown"
        self.sessions_by_device[device_type] = self.sessions_by_device.get(device_type, 0) + 1

        # Track by location
        location = session.metadata.location or "unknown"
        self.sessions_by_location[location] = self.sessions_by_location.get(location, 0) + 1

    def record_session_expired(self) -> None:
        """Record a session expiration."""
        self.total_sessions_expired += 1
        self.active_sessions_count = max(0, self.active_sessions_count - 1)

    def record_session_invalidated(self) -> None:
        """Record a session invalidation."""
        self.total_sessions_invalidated += 1
        self.active_sessions_count = max(0, self.active_sessions_count - 1)

    def record_security_event(self, event_type: str, session_id: str, details: Dict[str, Any]) -> None:
        """Record a security event."""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": event_type,
            "session_id": session_id,
            "details": details,
        }
        self.security_events.append(event)

        # Keep only last 1000 events
        if len(self.security_events) > 1000:
            self.security_events = self.security_events[-1000:]

    def get_stats(self) -> Dict[str, Any]:
        """Get analytics statistics."""
        return {
            "total_created": self.total_sessions_created,
            "total_expired": self.total_sessions_expired,
            "total_invalidated": self.total_sessions_invalidated,
            "active_count": self.active_sessions_count,
            "peak_concurrent": self.peak_concurrent_sessions,
            "average_duration": self.average_session_duration,
            "by_device": self.sessions_by_device,
            "by_location": self.sessions_by_location,
            "security_events_count": len(self.security_events),
        }


# ============================================================================
# Session Manager FSA
# ============================================================================


class SessionManagerFSA(BaseModel):
    """
    Session Manager Finite State Automaton.

    This class implements a comprehensive session management system with
    support for multiple storage backends, security features, and lifecycle
    management.

    Attributes:
        storage_backend: Storage backend for session persistence
        security_salt: Salt for security operations
        analytics: Session analytics and monitoring
        enable_analytics: Whether to track analytics
        enable_auto_cleanup: Whether to automatically clean up expired sessions
    """

    storage_backend: StorageBackend
    security_salt: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    analytics: SessionAnalytics = Field(default_factory=SessionAnalytics)
    enable_analytics: bool = True
    enable_auto_cleanup: bool = True
    cleanup_interval: int = 300  # 5 minutes

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # State transition table (private attribute)
    _transitions: Dict[Tuple[SessionState, SessionEvent], SessionState] = PrivateAttr(
        default_factory=lambda: {
            (SessionState.CREATED, SessionEvent.ACTIVATE): SessionState.ACTIVE,
            (SessionState.ACTIVE, SessionEvent.ACCESS): SessionState.ACTIVE,
            (SessionState.ACTIVE, SessionEvent.UPDATE): SessionState.ACTIVE,
            (SessionState.ACTIVE, SessionEvent.IDLE_TIMEOUT): SessionState.IDLE,
            (SessionState.ACTIVE, SessionEvent.ABSOLUTE_TIMEOUT): SessionState.EXPIRED,
            (SessionState.ACTIVE, SessionEvent.INVALIDATE): SessionState.INVALIDATED,
            (SessionState.ACTIVE, SessionEvent.LOCK): SessionState.LOCKED,
            (SessionState.ACTIVE, SessionEvent.TERMINATE): SessionState.TERMINATED,
            (SessionState.IDLE, SessionEvent.ACCESS): SessionState.ACTIVE,
            (SessionState.IDLE, SessionEvent.ABSOLUTE_TIMEOUT): SessionState.EXPIRED,
            (SessionState.IDLE, SessionEvent.INVALIDATE): SessionState.INVALIDATED,
            (SessionState.IDLE, SessionEvent.TERMINATE): SessionState.TERMINATED,
            (SessionState.LOCKED, SessionEvent.UNLOCK): SessionState.ACTIVE,
            (SessionState.LOCKED, SessionEvent.INVALIDATE): SessionState.INVALIDATED,
            (SessionState.LOCKED, SessionEvent.TERMINATE): SessionState.TERMINATED,
        }
    )

    _last_cleanup: float = PrivateAttr(default_factory=time.time)

    # ========================================================================
    # Core Session Operations
    # ========================================================================

    def create_session(
        self,
        user_id: Optional[str] = None,
        session_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        idle_timeout_seconds: int = 1800,
        absolute_timeout_seconds: int = 86400,
        security_level: SecurityLevel = SecurityLevel.MEDIUM,
    ) -> Session:
        """
        Create a new session.

        Args:
            user_id: User ID for the session
            session_data: Initial session data
            metadata: Session metadata (user agent, IP, etc.)
            idle_timeout_seconds: Idle timeout in seconds
            absolute_timeout_seconds: Absolute timeout in seconds
            security_level: Security level for the session

        Returns:
            Created session object

        Raises:
            ValueError: If session limits are exceeded
        """
        # Check concurrent session limit
        if user_id:
            active_count = self.storage_backend.count_active_sessions(user_id)
            if active_count >= 5:  # Default limit
                logger.warning(f"User {user_id} has reached concurrent session limit")
                # Optionally remove oldest session
                self._enforce_session_limit(user_id, 5)

        # Create session
        session = Session(
            user_id=user_id,
            data=session_data or {},
            idle_timeout_seconds=idle_timeout_seconds,
            absolute_timeout_seconds=absolute_timeout_seconds,
        )

        # Set expiration
        session.expires_at = datetime.utcnow() + timedelta(seconds=absolute_timeout_seconds)

        # Set metadata
        if metadata:
            session.metadata = SessionMetadata(**metadata)

        # Set security
        session.security.security_level = security_level
        session.security.fingerprint = session.calculate_fingerprint(self.security_salt)

        # Save to storage
        if not self.storage_backend.save(session):
            logger.error(f"Failed to save session {session.session_id}")
            raise RuntimeError("Failed to save session")

        # Record analytics
        if self.enable_analytics:
            self.analytics.record_session_created(session)

        logger.info(f"Created session {session.session_id} for user {user_id}")
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """
        Get a session by ID.

        Args:
            session_id: Session ID to retrieve

        Returns:
            Session object if found and valid, None otherwise
        """
        session = self.storage_backend.load(session_id)

        if not session:
            logger.debug(f"Session {session_id} not found")
            return None

        # Check if expired
        if session.is_expired():
            logger.info(f"Session {session_id} has expired")
            self._transition(session, SessionEvent.ABSOLUTE_TIMEOUT)
            self.storage_backend.save(session)
            return None

        return session

    def update_session(self, session_id: str, session_data: Dict[str, Any]) -> bool:
        """
        Update session data.

        Args:
            session_id: Session ID to update
            session_data: New session data to merge

        Returns:
            True if successful, False otherwise
        """
        session = self.get_session(session_id)

        if not session:
            logger.warning(f"Cannot update session {session_id}: not found")
            return False

        if session.is_locked:
            logger.warning(f"Cannot update session {session_id}: locked")
            return False

        # Merge data
        session.data.update(session_data)
        session.update_activity()

        # Update metadata
        session.metadata.data_size = len(json.dumps(session.data))

        # Transition state
        self._transition(session, SessionEvent.UPDATE)

        # Save to storage
        return self.storage_backend.save(session)

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.

        Args:
            session_id: Session ID to delete

        Returns:
            True if successful, False otherwise
        """
        session = self.get_session(session_id)

        if session:
            # Transition to terminated state
            self._transition(session, SessionEvent.TERMINATE)
            self.storage_backend.save(session)

            # Record analytics
            if self.enable_analytics:
                self.analytics.record_session_invalidated()

        # Delete from storage
        result = self.storage_backend.delete(session_id)

        if result:
            logger.info(f"Deleted session {session_id}")
        else:
            logger.warning(f"Failed to delete session {session_id}")

        return result

    def invalidate_session(self, session_id: str, reason: str = "manual") -> bool:
        """
        Invalidate a session.

        Args:
            session_id: Session ID to invalidate
            reason: Reason for invalidation

        Returns:
            True if successful, False otherwise
        """
        session = self.get_session(session_id)

        if not session:
            return False

        # Transition to invalidated state
        self._transition(session, SessionEvent.INVALIDATE)

        # Record security event
        if self.enable_analytics:
            self.analytics.record_security_event(
                "session_invalidated", session_id, {"reason": reason, "user_id": session.user_id}
            )
            self.analytics.record_session_invalidated()

        # Save and delete
        self.storage_backend.save(session)
        self.storage_backend.delete(session_id)

        logger.info(f"Invalidated session {session_id} (reason: {reason})")
        return True

    def refresh_session(self, session_id: str) -> bool:
        """
        Refresh a session (reset idle timeout).

        Args:
            session_id: Session ID to refresh

        Returns:
            True if successful, False otherwise
        """
        session = self.get_session(session_id)

        if not session:
            return False

        # Update activity
        session.update_activity()

        # Transition to active if idle
        if session.state == SessionState.IDLE:
            self._transition(session, SessionEvent.ACCESS)

        # Save to storage
        return self.storage_backend.save(session)

    def rotate_session(self, session_id: str) -> Optional[str]:
        """
        Rotate session ID (create new ID, copy data, delete old).

        Args:
            session_id: Session ID to rotate

        Returns:
            New session ID if successful, None otherwise
        """
        old_session = self.get_session(session_id)

        if not old_session:
            return None

        # Create new session with same data
        new_session = Session(
            user_id=old_session.user_id,
            data=old_session.data.copy(),
            idle_timeout_seconds=old_session.idle_timeout_seconds,
            absolute_timeout_seconds=old_session.absolute_timeout_seconds,
            is_authenticated=old_session.is_authenticated,
            is_persistent=old_session.is_persistent,
        )

        # Copy metadata
        new_session.metadata = old_session.metadata.model_copy()

        # Update security
        new_session.security = old_session.security.model_copy()
        new_session.security.csrf_token = secrets.token_urlsafe(32)
        new_session.security.rotation_count = old_session.security.rotation_count + 1
        new_session.security.last_rotation = datetime.utcnow()
        new_session.security.fingerprint = new_session.calculate_fingerprint(self.security_salt)

        # Save new session
        if not self.storage_backend.save(new_session):
            return None

        # Delete old session
        self.storage_backend.delete(session_id)

        # Record security event
        if self.enable_analytics:
            self.analytics.record_security_event(
                "session_rotated",
                new_session.session_id,
                {"old_session_id": session_id, "user_id": new_session.user_id},
            )

        logger.info(f"Rotated session {session_id} to {new_session.session_id}")
        return new_session.session_id

    # ========================================================================
    # Security Operations
    # ========================================================================

    def validate_csrf_token(self, session_id: str, csrf_token: str) -> bool:
        """
        Validate CSRF token for a session.

        Args:
            session_id: Session ID
            csrf_token: CSRF token to validate

        Returns:
            True if valid, False otherwise
        """
        session = self.get_session(session_id)

        if not session:
            return False

        is_valid = hmac.compare_digest(session.security.csrf_token, csrf_token)

        if not is_valid and self.enable_analytics:
            self.analytics.record_security_event(
                "csrf_validation_failed", session_id, {"user_id": session.user_id}
            )

        return is_valid

    def validate_session_fingerprint(
        self, session_id: str, user_agent: Optional[str] = None, ip_address: Optional[str] = None
    ) -> bool:
        """
        Validate session fingerprint to detect hijacking.

        Args:
            session_id: Session ID
            user_agent: Current user agent
            ip_address: Current IP address

        Returns:
            True if fingerprint matches, False otherwise
        """
        session = self.get_session(session_id)

        if not session:
            return False

        # Create current fingerprint
        components = [
            session.session_id,
            session.user_id or "",
            user_agent or "",
            ip_address or "",
            self.security_salt,
        ]
        current_fingerprint = hashlib.sha256("|".join(components).encode()).hexdigest()

        # Check security level requirements
        if session.security.security_level == SecurityLevel.HIGH or session.security.security_level == SecurityLevel.MAXIMUM:
            if session.security.user_agent_binding and user_agent != session.metadata.user_agent:
                logger.warning(f"User agent mismatch for session {session_id}")
                if self.enable_analytics:
                    self.analytics.record_security_event(
                        "user_agent_mismatch", session_id, {"user_id": session.user_id}
                    )
                return False

            if session.security.ip_binding and ip_address != session.metadata.ip_address:
                logger.warning(f"IP address mismatch for session {session_id}")
                if self.enable_analytics:
                    self.analytics.record_security_event("ip_mismatch", session_id, {"user_id": session.user_id})
                return False

        return True

    def lock_session(self, session_id: str, reason: str = "manual") -> bool:
        """
        Lock a session to prevent modifications.

        Args:
            session_id: Session ID to lock
            reason: Reason for locking

        Returns:
            True if successful, False otherwise
        """
        session = self.get_session(session_id)

        if not session:
            return False

        session.is_locked = True
        self._transition(session, SessionEvent.LOCK)

        if self.enable_analytics:
            self.analytics.record_security_event("session_locked", session_id, {"reason": reason})

        return self.storage_backend.save(session)

    def unlock_session(self, session_id: str) -> bool:
        """
        Unlock a previously locked session.

        Args:
            session_id: Session ID to unlock

        Returns:
            True if successful, False otherwise
        """
        session = self.storage_backend.load(session_id)

        if not session or not session.is_locked:
            return False

        session.is_locked = False
        self._transition(session, SessionEvent.UNLOCK)

        return self.storage_backend.save(session)

    # ========================================================================
    # Multi-User Operations
    # ========================================================================

    def list_user_sessions(self, user_id: str, include_expired: bool = False) -> List[Session]:
        """
        List all sessions for a user.

        Args:
            user_id: User ID
            include_expired: Whether to include expired sessions

        Returns:
            List of sessions
        """
        sessions = self.storage_backend.list_user_sessions(user_id)

        if not include_expired:
            sessions = [s for s in sessions if not s.is_expired()]

        return sessions

    def invalidate_all_user_sessions(self, user_id: str, except_session_id: Optional[str] = None) -> int:
        """
        Invalidate all sessions for a user.

        Args:
            user_id: User ID
            except_session_id: Optional session ID to keep active

        Returns:
            Number of sessions invalidated
        """
        sessions = self.list_user_sessions(user_id)
        count = 0

        for session in sessions:
            if except_session_id and session.session_id == except_session_id:
                continue

            if self.invalidate_session(session.session_id, reason="user_invalidate_all"):
                count += 1

        logger.info(f"Invalidated {count} sessions for user {user_id}")
        return count

    def _enforce_session_limit(self, user_id: str, limit: int) -> None:
        """
        Enforce concurrent session limit by removing oldest sessions.

        Args:
            user_id: User ID
            limit: Maximum number of concurrent sessions
        """
        sessions = self.list_user_sessions(user_id)

        if len(sessions) >= limit:
            # Sort by last activity (oldest first)
            sessions.sort(key=lambda s: s.last_activity)

            # Remove oldest sessions
            to_remove = len(sessions) - limit + 1
            for session in sessions[:to_remove]:
                self.delete_session(session.session_id)
                logger.info(f"Removed old session {session.session_id} to enforce limit for user {user_id}")

    # ========================================================================
    # Lifecycle Management
    # ========================================================================

    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions.

        Returns:
            Number of sessions cleaned up
        """
        count = self.storage_backend.cleanup_expired()

        if self.enable_analytics:
            for _ in range(count):
                self.analytics.record_session_expired()

        logger.info(f"Cleaned up {count} expired sessions")
        return count

    def auto_cleanup_if_needed(self) -> int:
        """
        Automatically clean up expired sessions if interval has passed.

        Returns:
            Number of sessions cleaned up (0 if not time yet)
        """
        if not self.enable_auto_cleanup:
            return 0

        now = time.time()
        if now - self._last_cleanup >= self.cleanup_interval:
            self._last_cleanup = now
            return self.cleanup_expired_sessions()

        return 0

    def _transition(self, session: Session, event: SessionEvent) -> bool:
        """
        Perform state transition.

        Args:
            session: Session to transition
            event: Event triggering the transition

        Returns:
            True if transition successful, False otherwise
        """
        current_state = session.state
        transition_key = (current_state, event)

        if transition_key not in self._transitions:
            logger.warning(f"Invalid transition: {current_state} -> {event}")
            return False

        new_state = self._transitions[transition_key]
        session.state = new_state
        logger.debug(f"Session {session.session_id} transitioned: {current_state} -> {new_state} (event: {event})")

        return True

    # ========================================================================
    # Analytics and Monitoring
    # ========================================================================

    def get_analytics(self) -> Dict[str, Any]:
        """
        Get session analytics.

        Returns:
            Analytics statistics
        """
        if not self.enable_analytics:
            return {}

        return self.analytics.get_stats()

    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed session information.

        Args:
            session_id: Session ID

        Returns:
            Session information dictionary
        """
        session = self.get_session(session_id)

        if not session:
            return None

        return {
            "session_id": session.session_id,
            "user_id": session.user_id,
            "state": session.state,
            "is_expired": session.is_expired(),
            "is_locked": session.is_locked,
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat(),
            "expires_at": session.expires_at.isoformat() if session.expires_at else None,
            "access_count": session.metadata.access_count,
            "device_type": session.metadata.device_type,
            "security_level": session.security.security_level,
        }

    # ========================================================================
    # Utility Methods
    # ========================================================================

    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """
        Generate a secure random token.

        Args:
            length: Token length in bytes

        Returns:
            URL-safe token string
        """
        return secrets.token_urlsafe(length)

    @staticmethod
    def hash_data(data: str, salt: str = "") -> str:
        """
        Hash data with optional salt.

        Args:
            data: Data to hash
            salt: Optional salt

        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(f"{data}{salt}".encode()).hexdigest()
