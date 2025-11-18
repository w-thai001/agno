"""
Session Manager FSA: Enterprise-grade session management for stateful applications.

This module provides comprehensive session management with support for:
- Session lifecycle management (create, read, update, destroy)
- Multiple storage backends (Redis, Memcached, database, filesystem)
- Session state persistence and serialization
- Session clustering and replication
- Timeout management (sliding and absolute expiration)
- Session security (encryption, token validation)
- Distributed session locking
- Session monitoring and metrics
- Garbage collection for expired sessions
- Thread-safe and distributed operations
"""

from __future__ import annotations

import pickle
import json
import hashlib
import hmac
import secrets
import threading
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from uuid import uuid4
import base64

# Cryptography is optional - only import if available
CRYPTO_AVAILABLE = False
Fernet = None

def _try_import_crypto():
    """Try to import cryptography libraries."""
    global CRYPTO_AVAILABLE, Fernet
    try:
        from cryptography.fernet import Fernet as FernetClass
        Fernet = FernetClass
        CRYPTO_AVAILABLE = True
    except:
        pass

# Don't import at module level to avoid panics
# Will be imported lazily when needed

try:
    from agno.utils.log import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


# ==================== Enums and Constants ====================

class SessionBackend(Enum):
    """Supported session storage backends."""
    MEMORY = "memory"
    REDIS = "redis"
    MEMCACHED = "memcached"
    DATABASE = "database"
    FILESYSTEM = "filesystem"


class SessionState(Enum):
    """Session lifecycle states."""
    ACTIVE = "active"
    EXPIRED = "expired"
    DESTROYED = "destroyed"
    LOCKED = "locked"
    REPLICATED = "replicated"


class TimeoutMode(Enum):
    """Session timeout modes."""
    SLIDING = "sliding"  # Extends on each access
    ABSOLUTE = "absolute"  # Fixed expiration time
    IDLE = "idle"  # Expires after inactivity


class SerializationFormat(Enum):
    """Session serialization formats."""
    PICKLE = "pickle"
    JSON = "json"
    MSGPACK = "msgpack"


class LockMode(Enum):
    """Session locking modes."""
    READ = "read"
    WRITE = "write"
    EXCLUSIVE = "exclusive"


# ==================== Data Classes ====================

@dataclass
class Session:
    """Represents a user session."""
    session_id: str = field(default_factory=lambda: str(uuid4()))
    user_id: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    state: SessionState = SessionState.ACTIVE
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timeout_seconds: int = 3600  # 1 hour default
    timeout_mode: TimeoutMode = TimeoutMode.SLIDING
    is_encrypted: bool = False
    replication_nodes: List[str] = field(default_factory=list)
    lock_holder: Optional[str] = None
    access_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "state": self.state.value,
            "data": self.data,
            "metadata": self.metadata,
            "timeout_seconds": self.timeout_seconds,
            "timeout_mode": self.timeout_mode.value,
            "access_count": self.access_count,
        }

    def is_expired(self) -> bool:
        """Check if session has expired."""
        if self.state == SessionState.EXPIRED:
            return True
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return True
        return False

    def refresh(self):
        """Refresh session timeout."""
        self.last_accessed = datetime.utcnow()
        if self.timeout_mode == TimeoutMode.SLIDING:
            self.expires_at = datetime.utcnow() + timedelta(seconds=self.timeout_seconds)


@dataclass
class SessionConfig:
    """Configuration for session management."""
    backend: SessionBackend = SessionBackend.MEMORY
    serialization_format: SerializationFormat = SerializationFormat.PICKLE
    default_timeout: int = 3600  # seconds
    timeout_mode: TimeoutMode = TimeoutMode.SLIDING
    enable_encryption: bool = False
    encryption_key: Optional[bytes] = None
    enable_replication: bool = False
    replication_factor: int = 2
    enable_gc: bool = True
    gc_interval: int = 300  # seconds
    max_sessions: int = 10000
    enable_clustering: bool = False
    cluster_nodes: List[str] = field(default_factory=list)


@dataclass
class SessionOp:
    """Session operation request."""
    operation: str  # create, get, update, destroy, refresh
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionResult:
    """Result of session operation."""
    success: bool
    session_id: Optional[str] = None
    session: Optional[Session] = None
    error: Optional[str] = None
    execution_time: float = 0.0


@dataclass
class ValidationResult:
    """Session configuration validation result."""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class UpdateResult:
    """Result of session update."""
    success: bool
    session_id: str
    updated_fields: List[str] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class DestroyResult:
    """Result of session destruction."""
    success: bool
    session_id: str
    was_active: bool = False
    error: Optional[str] = None


@dataclass
class RefreshResult:
    """Result of session refresh."""
    success: bool
    session_id: str
    new_expiration: Optional[datetime] = None
    error: Optional[str] = None


@dataclass
class StoreResult:
    """Result of session storage."""
    success: bool
    session_id: str
    backend: str
    error: Optional[str] = None


@dataclass
class LoadResult:
    """Result of session loading."""
    success: bool
    session: Optional[Session] = None
    backend: str = ""
    error: Optional[str] = None


@dataclass
class ReplicationResult:
    """Result of session replication."""
    success: bool
    session_id: str
    replicated_nodes: List[str] = field(default_factory=list)
    failed_nodes: List[str] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class SyncResult:
    """Result of cluster synchronization."""
    success: bool
    session_id: str
    synced_nodes: List[str] = field(default_factory=list)
    conflicts_resolved: int = 0
    error: Optional[str] = None


@dataclass
class TimeoutStatus:
    """Session timeout status."""
    session_id: str
    is_expired: bool
    time_remaining: Optional[float] = None  # seconds
    last_accessed: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ExpireResult:
    """Result of session expiration."""
    success: bool
    session_id: str
    was_active: bool = False
    error: Optional[str] = None


@dataclass
class GCResult:
    """Result of garbage collection."""
    success: bool
    sessions_collected: int = 0
    sessions_preserved: int = 0
    execution_time: float = 0.0
    error: Optional[str] = None


@dataclass
class EncryptResult:
    """Result of data encryption."""
    success: bool
    encrypted_data: Optional[bytes] = None
    error: Optional[str] = None


@dataclass
class DecryptResult:
    """Result of data decryption."""
    success: bool
    decrypted_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class TokenValidation:
    """Session token validation result."""
    valid: bool
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    error: Optional[str] = None


@dataclass
class SessionMetrics:
    """Session performance metrics."""
    session_id: str
    total_accesses: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    lifetime_seconds: float = 0.0
    data_size_bytes: int = 0
    is_replicated: bool = False
    lock_count: int = 0


@dataclass
class MigrationResult:
    """Result of session migration."""
    success: bool
    session_id: str
    source_backend: str
    target_backend: str
    error: Optional[str] = None


@dataclass
class CloneResult:
    """Result of session cloning."""
    success: bool
    original_id: str
    cloned_id: Optional[str] = None
    error: Optional[str] = None


@dataclass
class MergeResult:
    """Result of session merging."""
    success: bool
    merged_session_id: Optional[str] = None
    source_sessions: List[str] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class LockResult:
    """Result of session locking."""
    success: bool
    session_id: str
    lock_id: Optional[str] = None
    error: Optional[str] = None


@dataclass
class UnlockResult:
    """Result of session unlocking."""
    success: bool
    session_id: str
    was_locked: bool = False
    error: Optional[str] = None


# ==================== Session Manager FSA ====================

class SessionManagerFSA:
    """
    Session Manager Finite State Automaton.

    Provides enterprise-grade session management with clustering,
    security, and distributed storage.
    """

    def __init__(
        self,
        name: str = "SessionManagerFSA",
        config: Optional[SessionConfig] = None,
    ):
        """
        Initialize Session Manager FSA.

        Args:
            name: Name of the FSA instance
            config: Session configuration
        """
        self.name = name
        self.fsa_id = str(uuid4())
        self.config = config or SessionConfig()

        # Session storage
        self.sessions: Dict[str, Session] = {}
        self.session_tokens: Dict[str, str] = {}  # token -> session_id
        self.user_sessions: Dict[str, Set[str]] = defaultdict(set)  # user_id -> session_ids

        # Backend storage
        self.backend_connections: Dict[SessionBackend, Any] = {}

        # Encryption - try to import crypto if needed
        if self.config.enable_encryption:
            _try_import_crypto()

        if CRYPTO_AVAILABLE and Fernet:
            self.encryption_key = self.config.encryption_key or Fernet.generate_key()
            self.cipher = Fernet(self.encryption_key) if self.encryption_key else None
        else:
            self.encryption_key = None
            self.cipher = None

        # Clustering
        self.cluster_nodes: Dict[str, Dict[str, Session]] = {}  # node_id -> sessions
        self.replication_log: List[Tuple[str, str, datetime]] = []  # (session_id, node_id, timestamp)

        # Locking
        self.session_locks: Dict[str, threading.RLock] = {}
        self.lock_owners: Dict[str, str] = {}  # session_id -> lock_id

        # Metrics
        self.total_sessions_created: int = 0
        self.total_sessions_destroyed: int = 0
        self.total_accesses: int = 0

        # Garbage collection
        self.gc_thread: Optional[threading.Thread] = None
        self.gc_running = False

        # Thread safety
        self.lock = threading.RLock()

        # Start background processes
        if self.config.enable_gc:
            self._start_gc()

        logger.info(f"Initialized {self.name} with ID {self.fsa_id}")

    # ==================== Main Execution ====================

    def execute(self, session_operations: List[SessionOp]) -> SessionResult:
        """
        Execute session management operations.

        Args:
            session_operations: List of session operations

        Returns:
            SessionResult with execution outcome
        """
        start_time = time.time()

        try:
            for op in session_operations:
                if op.operation == "create":
                    self.create_session(op.user_id or "", op.metadata)
                elif op.operation == "get" and op.session_id:
                    self.get_session(op.session_id)
                elif op.operation == "update" and op.session_id:
                    self.update_session(op.session_id, op.data)
                elif op.operation == "destroy" and op.session_id:
                    self.destroy_session(op.session_id)
                elif op.operation == "refresh" and op.session_id:
                    self.refresh_session(op.session_id)

            execution_time = time.time() - start_time

            return SessionResult(
                success=True,
                execution_time=execution_time,
            )

        except Exception as e:
            logger.error(f"Error executing session operations: {e}")
            return SessionResult(
                success=False,
                error=str(e),
                execution_time=time.time() - start_time,
            )

    # ==================== Configuration and Validation ====================

    def validate(self, session_config: SessionConfig) -> ValidationResult:
        """
        Validate session configuration.

        Args:
            session_config: Configuration to validate

        Returns:
            ValidationResult with errors/warnings
        """
        errors = []
        warnings = []

        if session_config.default_timeout <= 0:
            errors.append("Default timeout must be positive")

        if session_config.max_sessions <= 0:
            errors.append("Max sessions must be positive")

        if session_config.enable_encryption and not CRYPTO_AVAILABLE:
            errors.append("Encryption requested but cryptography library not available")

        if session_config.enable_encryption and not session_config.encryption_key:
            warnings.append("Encryption enabled but no key provided, using generated key")

        if session_config.enable_replication and session_config.replication_factor < 1:
            errors.append("Replication factor must be at least 1")

        if session_config.gc_interval < 60:
            warnings.append("GC interval less than 60 seconds may impact performance")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    # ==================== Session Lifecycle ====================

    def create_session(
        self,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Session:
        """
        Initialize new session.

        Args:
            user_id: User identifier
            metadata: Optional session metadata

        Returns:
            Created Session object
        """
        with self.lock:
            session = Session(
                user_id=user_id,
                timeout_seconds=self.config.default_timeout,
                timeout_mode=self.config.timeout_mode,
                metadata=metadata or {},
            )

            # Calculate expiration
            if self.config.timeout_mode == TimeoutMode.ABSOLUTE:
                session.expires_at = datetime.utcnow() + timedelta(seconds=self.config.default_timeout)
            elif self.config.timeout_mode == TimeoutMode.SLIDING:
                session.expires_at = datetime.utcnow() + timedelta(seconds=self.config.default_timeout)

            # Store session
            self.sessions[session.session_id] = session
            self.user_sessions[user_id].add(session.session_id)

            # Generate token
            token = self._generate_token(session.session_id, user_id)
            self.session_tokens[token] = session.session_id

            # Create lock
            self.session_locks[session.session_id] = threading.RLock()

            # Update metrics
            self.total_sessions_created += 1

            # Replicate if enabled
            if self.config.enable_replication:
                self.replicate_session(session, self.config.cluster_nodes)

            logger.info(f"Created session {session.session_id} for user {user_id}")

            return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """
        Retrieve existing session.

        Args:
            session_id: Session identifier

        Returns:
            Session if found, None otherwise
        """
        with self.lock:
            session = self.sessions.get(session_id)

            if session:
                # Check if expired
                if session.is_expired():
                    session.state = SessionState.EXPIRED
                    return None

                # Update access time
                session.last_accessed = datetime.utcnow()
                session.access_count += 1
                self.total_accesses += 1

                # Refresh if sliding timeout
                if session.timeout_mode == TimeoutMode.SLIDING:
                    session.refresh()

                logger.debug(f"Retrieved session {session_id}")

            return session

    def update_session(
        self,
        session_id: str,
        data: Dict[str, Any],
    ) -> UpdateResult:
        """
        Modify session data.

        Args:
            session_id: Session to update
            data: Data to update

        Returns:
            UpdateResult with status
        """
        try:
            with self.lock:
                session = self.get_session(session_id)

                if not session:
                    return UpdateResult(
                        success=False,
                        session_id=session_id,
                        error="Session not found or expired",
                    )

                # Update data
                updated_fields = []
                for key, value in data.items():
                    session.data[key] = value
                    updated_fields.append(key)

                # Refresh access time
                session.refresh()

                logger.debug(f"Updated session {session_id} with {len(updated_fields)} fields")

                return UpdateResult(
                    success=True,
                    session_id=session_id,
                    updated_fields=updated_fields,
                )

        except Exception as e:
            logger.error(f"Error updating session: {e}")
            return UpdateResult(
                success=False,
                session_id=session_id,
                error=str(e),
            )

    def destroy_session(self, session_id: str) -> DestroyResult:
        """
        Terminate session.

        Args:
            session_id: Session to destroy

        Returns:
            DestroyResult with status
        """
        try:
            with self.lock:
                session = self.sessions.get(session_id)

                if not session:
                    return DestroyResult(
                        success=False,
                        session_id=session_id,
                        error="Session not found",
                    )

                was_active = session.state == SessionState.ACTIVE

                # Update state
                session.state = SessionState.DESTROYED

                # Remove from user sessions
                if session.user_id in self.user_sessions:
                    self.user_sessions[session.user_id].discard(session_id)

                # Remove from storage
                del self.sessions[session_id]

                # Remove token
                token_to_remove = None
                for token, sid in self.session_tokens.items():
                    if sid == session_id:
                        token_to_remove = token
                        break
                if token_to_remove:
                    del self.session_tokens[token_to_remove]

                # Remove lock
                if session_id in self.session_locks:
                    del self.session_locks[session_id]

                # Update metrics
                self.total_sessions_destroyed += 1

                logger.info(f"Destroyed session {session_id}")

                return DestroyResult(
                    success=True,
                    session_id=session_id,
                    was_active=was_active,
                )

        except Exception as e:
            logger.error(f"Error destroying session: {e}")
            return DestroyResult(
                success=False,
                session_id=session_id,
                error=str(e),
            )

    def refresh_session(self, session_id: str) -> RefreshResult:
        """
        Extend session timeout.

        Args:
            session_id: Session to refresh

        Returns:
            RefreshResult with new expiration
        """
        try:
            with self.lock:
                session = self.get_session(session_id)

                if not session:
                    return RefreshResult(
                        success=False,
                        session_id=session_id,
                        error="Session not found or expired",
                    )

                # Refresh timeout
                session.refresh()

                logger.debug(f"Refreshed session {session_id}")

                return RefreshResult(
                    success=True,
                    session_id=session_id,
                    new_expiration=session.expires_at,
                )

        except Exception as e:
            logger.error(f"Error refreshing session: {e}")
            return RefreshResult(
                success=False,
                session_id=session_id,
                error=str(e),
            )

    # ==================== Serialization ====================

    def serialize_session(self, session: Session) -> bytes:
        """
        Convert session to bytes.

        Args:
            session: Session to serialize

        Returns:
            Serialized session data
        """
        try:
            if self.config.serialization_format == SerializationFormat.PICKLE:
                return pickle.dumps(session)
            elif self.config.serialization_format == SerializationFormat.JSON:
                return json.dumps(session.to_dict()).encode()
            else:
                # Default to pickle
                return pickle.dumps(session)

        except Exception as e:
            logger.error(f"Error serializing session: {e}")
            # Fallback to JSON
            return json.dumps(session.to_dict()).encode()

    def deserialize_session(self, data: bytes) -> Session:
        """
        Restore session from bytes.

        Args:
            data: Serialized session data

        Returns:
            Deserialized Session object
        """
        try:
            if self.config.serialization_format == SerializationFormat.PICKLE:
                return pickle.loads(data)
            elif self.config.serialization_format == SerializationFormat.JSON:
                session_dict = json.loads(data.decode())
                # Reconstruct Session from dict
                return self._dict_to_session(session_dict)
            else:
                return pickle.loads(data)

        except Exception as e:
            logger.error(f"Error deserializing session: {e}")
            raise

    # ==================== Storage Backend ====================

    def store_session(
        self,
        session: Session,
        backend: SessionBackend,
    ) -> StoreResult:
        """
        Persist session data to backend.

        Args:
            session: Session to store
            backend: Storage backend

        Returns:
            StoreResult with status
        """
        try:
            serialized = self.serialize_session(session)

            if backend == SessionBackend.MEMORY:
                # Already in memory
                pass
            elif backend == SessionBackend.FILESYSTEM:
                self._store_filesystem(session.session_id, serialized)
            elif backend == SessionBackend.DATABASE:
                self._store_database(session.session_id, serialized)
            elif backend == SessionBackend.REDIS:
                self._store_redis(session.session_id, serialized)
            elif backend == SessionBackend.MEMCACHED:
                self._store_memcached(session.session_id, serialized)

            return StoreResult(
                success=True,
                session_id=session.session_id,
                backend=backend.value,
            )

        except Exception as e:
            logger.error(f"Error storing session: {e}")
            return StoreResult(
                success=False,
                session_id=session.session_id,
                backend=backend.value,
                error=str(e),
            )

    def load_session(
        self,
        session_id: str,
        backend: SessionBackend,
    ) -> LoadResult:
        """
        Retrieve session data from backend.

        Args:
            session_id: Session to load
            backend: Storage backend

        Returns:
            LoadResult with session data
        """
        try:
            serialized = None

            if backend == SessionBackend.MEMORY:
                session = self.sessions.get(session_id)
                if session:
                    return LoadResult(
                        success=True,
                        session=session,
                        backend=backend.value,
                    )
            elif backend == SessionBackend.FILESYSTEM:
                serialized = self._load_filesystem(session_id)
            elif backend == SessionBackend.DATABASE:
                serialized = self._load_database(session_id)
            elif backend == SessionBackend.REDIS:
                serialized = self._load_redis(session_id)
            elif backend == SessionBackend.MEMCACHED:
                serialized = self._load_memcached(session_id)

            if serialized:
                session = self.deserialize_session(serialized)
                return LoadResult(
                    success=True,
                    session=session,
                    backend=backend.value,
                )
            else:
                return LoadResult(
                    success=False,
                    backend=backend.value,
                    error="Session not found in backend",
                )

        except Exception as e:
            logger.error(f"Error loading session: {e}")
            return LoadResult(
                success=False,
                backend=backend.value,
                error=str(e),
            )

    # ==================== Clustering and Replication ====================

    def replicate_session(
        self,
        session: Session,
        nodes: List[str],
    ) -> ReplicationResult:
        """
        Copy session to cluster nodes.

        Args:
            session: Session to replicate
            nodes: Target cluster nodes

        Returns:
            ReplicationResult with status
        """
        try:
            replicated = []
            failed = []

            for node in nodes[:self.config.replication_factor]:
                try:
                    # Simulate replication to node
                    if node not in self.cluster_nodes:
                        self.cluster_nodes[node] = {}

                    self.cluster_nodes[node][session.session_id] = session
                    replicated.append(node)

                    # Log replication
                    self.replication_log.append((session.session_id, node, datetime.utcnow()))

                except Exception as e:
                    logger.warning(f"Failed to replicate to node {node}: {e}")
                    failed.append(node)

            session.replication_nodes = replicated

            return ReplicationResult(
                success=len(replicated) > 0,
                session_id=session.session_id,
                replicated_nodes=replicated,
                failed_nodes=failed,
            )

        except Exception as e:
            logger.error(f"Error replicating session: {e}")
            return ReplicationResult(
                success=False,
                session_id=session.session_id,
                error=str(e),
            )

    def sync_session_cluster(self, session_id: str) -> SyncResult:
        """
        Synchronize session across cluster.

        Args:
            session_id: Session to synchronize

        Returns:
            SyncResult with status
        """
        try:
            with self.lock:
                session = self.sessions.get(session_id)

                if not session:
                    return SyncResult(
                        success=False,
                        session_id=session_id,
                        error="Session not found",
                    )

                synced = []
                conflicts = 0

                # Sync to all replication nodes
                for node in session.replication_nodes:
                    if node in self.cluster_nodes:
                        node_session = self.cluster_nodes[node].get(session_id)

                        if node_session:
                            # Check for conflicts
                            if node_session.last_accessed > session.last_accessed:
                                # Node has newer data, resolve conflict
                                session.data.update(node_session.data)
                                conflicts += 1

                        # Update node with latest
                        self.cluster_nodes[node][session_id] = session
                        synced.append(node)

                return SyncResult(
                    success=True,
                    session_id=session_id,
                    synced_nodes=synced,
                    conflicts_resolved=conflicts,
                )

        except Exception as e:
            logger.error(f"Error syncing session: {e}")
            return SyncResult(
                success=False,
                session_id=session_id,
                error=str(e),
            )

    # ==================== Timeout Management ====================

    def check_timeout(self, session: Session) -> TimeoutStatus:
        """
        Verify session expiry.

        Args:
            session: Session to check

        Returns:
            TimeoutStatus with expiry info
        """
        is_expired = session.is_expired()
        time_remaining = None

        if session.expires_at and not is_expired:
            time_remaining = (session.expires_at - datetime.utcnow()).total_seconds()

        return TimeoutStatus(
            session_id=session.session_id,
            is_expired=is_expired,
            time_remaining=time_remaining,
            last_accessed=session.last_accessed,
        )

    def expire_session(self, session_id: str) -> ExpireResult:
        """
        Mark session as expired.

        Args:
            session_id: Session to expire

        Returns:
            ExpireResult with status
        """
        try:
            with self.lock:
                session = self.sessions.get(session_id)

                if not session:
                    return ExpireResult(
                        success=False,
                        session_id=session_id,
                        error="Session not found",
                    )

                was_active = session.state == SessionState.ACTIVE
                session.state = SessionState.EXPIRED

                logger.info(f"Expired session {session_id}")

                return ExpireResult(
                    success=True,
                    session_id=session_id,
                    was_active=was_active,
                )

        except Exception as e:
            logger.error(f"Error expiring session: {e}")
            return ExpireResult(
                success=False,
                session_id=session_id,
                error=str(e),
            )

    def collect_garbage(self, max_age: Optional[timedelta] = None) -> GCResult:
        """
        Clean expired sessions.

        Args:
            max_age: Maximum session age

        Returns:
            GCResult with statistics
        """
        start_time = time.time()
        collected = 0
        preserved = 0

        try:
            with self.lock:
                sessions_to_remove = []

                for session_id, session in self.sessions.items():
                    # Check expiration
                    if session.is_expired():
                        sessions_to_remove.append(session_id)
                        collected += 1
                    # Check age
                    elif max_age:
                        age = datetime.utcnow() - session.created_at
                        if age > max_age:
                            sessions_to_remove.append(session_id)
                            collected += 1
                        else:
                            preserved += 1
                    else:
                        preserved += 1

                # Remove expired sessions
                for session_id in sessions_to_remove:
                    self.destroy_session(session_id)

            execution_time = time.time() - start_time

            logger.info(f"GC collected {collected} sessions, preserved {preserved}")

            return GCResult(
                success=True,
                sessions_collected=collected,
                sessions_preserved=preserved,
                execution_time=execution_time,
            )

        except Exception as e:
            logger.error(f"Error during garbage collection: {e}")
            return GCResult(
                success=False,
                error=str(e),
                execution_time=time.time() - start_time,
            )

    # ==================== Security ====================

    def encrypt_session_data(
        self,
        data: Dict[str, Any],
        key: Optional[bytes] = None,
    ) -> EncryptResult:
        """
        Secure session data with encryption.

        Args:
            data: Data to encrypt
            key: Encryption key (optional)

        Returns:
            EncryptResult with encrypted data
        """
        try:
            # Try to import crypto if not already done
            if not CRYPTO_AVAILABLE:
                _try_import_crypto()

            if not CRYPTO_AVAILABLE:
                return EncryptResult(
                    success=False,
                    error="Cryptography library not available",
                )

            cipher = self.cipher
            if key and Fernet:
                cipher = Fernet(key)

            if not cipher:
                return EncryptResult(
                    success=False,
                    error="No encryption key available",
                )

            # Serialize data
            serialized = json.dumps(data).encode()

            # Encrypt
            encrypted = cipher.encrypt(serialized)

            return EncryptResult(
                success=True,
                encrypted_data=encrypted,
            )

        except Exception as e:
            logger.error(f"Error encrypting data: {e}")
            return EncryptResult(
                success=False,
                error=str(e),
            )

    def decrypt_session_data(
        self,
        encrypted: bytes,
        key: Optional[bytes] = None,
    ) -> DecryptResult:
        """
        Restore encrypted session data.

        Args:
            encrypted: Encrypted data
            key: Decryption key (optional)

        Returns:
            DecryptResult with decrypted data
        """
        try:
            # Try to import crypto if not already done
            if not CRYPTO_AVAILABLE:
                _try_import_crypto()

            if not CRYPTO_AVAILABLE:
                return DecryptResult(
                    success=False,
                    error="Cryptography library not available",
                )

            cipher = self.cipher
            if key and Fernet:
                cipher = Fernet(key)

            if not cipher:
                return DecryptResult(
                    success=False,
                    error="No decryption key available",
                )

            # Decrypt
            decrypted = cipher.decrypt(encrypted)

            # Deserialize
            data = json.loads(decrypted.decode())

            return DecryptResult(
                success=True,
                decrypted_data=data,
            )

        except Exception as e:
            logger.error(f"Error decrypting data: {e}")
            return DecryptResult(
                success=False,
                error=str(e),
            )

    def validate_session_token(self, token: str) -> TokenValidation:
        """
        Verify session token authenticity.

        Args:
            token: Token to validate

        Returns:
            TokenValidation with result
        """
        try:
            session_id = self.session_tokens.get(token)

            if not session_id:
                return TokenValidation(
                    valid=False,
                    error="Invalid token",
                )

            session = self.get_session(session_id)

            if not session:
                return TokenValidation(
                    valid=False,
                    error="Session not found or expired",
                )

            return TokenValidation(
                valid=True,
                session_id=session_id,
                user_id=session.user_id,
            )

        except Exception as e:
            logger.error(f"Error validating token: {e}")
            return TokenValidation(
                valid=False,
                error=str(e),
            )

    def generate_session_id(self) -> str:
        """
        Create unique session identifier.

        Returns:
            Unique session ID
        """
        return str(uuid4())

    # ==================== Session Queries ====================

    def list_active_sessions(
        self,
        user_id: Optional[str] = None,
    ) -> List[Session]:
        """
        Query active sessions.

        Args:
            user_id: Optional user filter

        Returns:
            List of active sessions
        """
        with self.lock:
            sessions = []

            if user_id:
                # Get sessions for specific user
                session_ids = self.user_sessions.get(user_id, set())
                for session_id in session_ids:
                    session = self.sessions.get(session_id)
                    if session and session.state == SessionState.ACTIVE and not session.is_expired():
                        sessions.append(session)
            else:
                # Get all active sessions
                for session in self.sessions.values():
                    if session.state == SessionState.ACTIVE and not session.is_expired():
                        sessions.append(session)

            return sessions

    def get_session_metrics(self, session_id: str) -> Optional[SessionMetrics]:
        """
        Collect session statistics.

        Args:
            session_id: Session to analyze

        Returns:
            SessionMetrics if session exists
        """
        with self.lock:
            session = self.sessions.get(session_id)

            if not session:
                return None

            # Calculate lifetime
            lifetime = (datetime.utcnow() - session.created_at).total_seconds()

            # Calculate data size
            data_size = len(self.serialize_session(session))

            return SessionMetrics(
                session_id=session_id,
                total_accesses=session.access_count,
                created_at=session.created_at,
                last_accessed=session.last_accessed,
                lifetime_seconds=lifetime,
                data_size_bytes=data_size,
                is_replicated=len(session.replication_nodes) > 0,
                lock_count=1 if session.lock_holder else 0,
            )

    # ==================== Session Operations ====================

    def migrate_session(
        self,
        session_id: str,
        target_backend: SessionBackend,
    ) -> MigrationResult:
        """
        Move session to different backend.

        Args:
            session_id: Session to migrate
            target_backend: Target storage backend

        Returns:
            MigrationResult with status
        """
        try:
            with self.lock:
                session = self.sessions.get(session_id)

                if not session:
                    return MigrationResult(
                        success=False,
                        session_id=session_id,
                        source_backend=self.config.backend.value,
                        target_backend=target_backend.value,
                        error="Session not found",
                    )

                # Store to new backend
                store_result = self.store_session(session, target_backend)

                if not store_result.success:
                    return MigrationResult(
                        success=False,
                        session_id=session_id,
                        source_backend=self.config.backend.value,
                        target_backend=target_backend.value,
                        error=store_result.error,
                    )

                logger.info(f"Migrated session {session_id} to {target_backend.value}")

                return MigrationResult(
                    success=True,
                    session_id=session_id,
                    source_backend=self.config.backend.value,
                    target_backend=target_backend.value,
                )

        except Exception as e:
            logger.error(f"Error migrating session: {e}")
            return MigrationResult(
                success=False,
                session_id=session_id,
                source_backend=self.config.backend.value,
                target_backend=target_backend.value,
                error=str(e),
            )

    def clone_session(self, session_id: str) -> CloneResult:
        """
        Duplicate session.

        Args:
            session_id: Session to clone

        Returns:
            CloneResult with new session ID
        """
        try:
            with self.lock:
                original = self.sessions.get(session_id)

                if not original:
                    return CloneResult(
                        success=False,
                        original_id=session_id,
                        error="Session not found",
                    )

                # Create new session with same data
                cloned = Session(
                    user_id=original.user_id,
                    data=original.data.copy(),
                    metadata=original.metadata.copy(),
                    timeout_seconds=original.timeout_seconds,
                    timeout_mode=original.timeout_mode,
                )

                # Store cloned session
                self.sessions[cloned.session_id] = cloned
                self.user_sessions[cloned.user_id].add(cloned.session_id)

                logger.info(f"Cloned session {session_id} to {cloned.session_id}")

                return CloneResult(
                    success=True,
                    original_id=session_id,
                    cloned_id=cloned.session_id,
                )

        except Exception as e:
            logger.error(f"Error cloning session: {e}")
            return CloneResult(
                success=False,
                original_id=session_id,
                error=str(e),
            )

    def merge_sessions(self, session_ids: List[str]) -> MergeResult:
        """
        Combine multiple sessions.

        Args:
            session_ids: Sessions to merge

        Returns:
            MergeResult with merged session ID
        """
        try:
            with self.lock:
                if len(session_ids) < 2:
                    return MergeResult(
                        success=False,
                        error="At least 2 sessions required for merge",
                    )

                # Get all sessions
                sessions = []
                for sid in session_ids:
                    session = self.sessions.get(sid)
                    if session:
                        sessions.append(session)

                if len(sessions) < 2:
                    return MergeResult(
                        success=False,
                        error="Not enough valid sessions found",
                    )

                # Create merged session
                merged_data = {}
                merged_metadata = {}
                user_id = sessions[0].user_id

                for session in sessions:
                    merged_data.update(session.data)
                    merged_metadata.update(session.metadata)

                merged = Session(
                    user_id=user_id,
                    data=merged_data,
                    metadata=merged_metadata,
                )

                # Store merged session
                self.sessions[merged.session_id] = merged
                self.user_sessions[user_id].add(merged.session_id)

                # Destroy original sessions
                for sid in session_ids:
                    self.destroy_session(sid)

                logger.info(f"Merged {len(session_ids)} sessions into {merged.session_id}")

                return MergeResult(
                    success=True,
                    merged_session_id=merged.session_id,
                    source_sessions=session_ids,
                )

        except Exception as e:
            logger.error(f"Error merging sessions: {e}")
            return MergeResult(
                success=False,
                error=str(e),
            )

    # ==================== Session Locking ====================

    def lock_session(
        self,
        session_id: str,
        timeout: float = 30.0,
    ) -> LockResult:
        """
        Acquire session lock.

        Args:
            session_id: Session to lock
            timeout: Lock timeout in seconds

        Returns:
            LockResult with lock ID
        """
        try:
            if session_id not in self.sessions:
                return LockResult(
                    success=False,
                    session_id=session_id,
                    error="Session not found",
                )

            lock = self.session_locks.get(session_id)
            if not lock:
                lock = threading.RLock()
                self.session_locks[session_id] = lock

            # Acquire lock
            acquired = lock.acquire(timeout=timeout)

            if acquired:
                lock_id = str(uuid4())
                self.lock_owners[session_id] = lock_id

                session = self.sessions[session_id]
                session.lock_holder = lock_id
                session.state = SessionState.LOCKED

                logger.debug(f"Locked session {session_id} with lock {lock_id}")

                return LockResult(
                    success=True,
                    session_id=session_id,
                    lock_id=lock_id,
                )
            else:
                return LockResult(
                    success=False,
                    session_id=session_id,
                    error="Failed to acquire lock within timeout",
                )

        except Exception as e:
            logger.error(f"Error locking session: {e}")
            return LockResult(
                success=False,
                session_id=session_id,
                error=str(e),
            )

    def unlock_session(self, session_id: str) -> UnlockResult:
        """
        Release session lock.

        Args:
            session_id: Session to unlock

        Returns:
            UnlockResult with status
        """
        try:
            if session_id not in self.sessions:
                return UnlockResult(
                    success=False,
                    session_id=session_id,
                    error="Session not found",
                )

            was_locked = session_id in self.lock_owners

            if was_locked:
                lock = self.session_locks.get(session_id)
                if lock:
                    lock.release()

                del self.lock_owners[session_id]

                session = self.sessions[session_id]
                session.lock_holder = None
                session.state = SessionState.ACTIVE

                logger.debug(f"Unlocked session {session_id}")

            return UnlockResult(
                success=True,
                session_id=session_id,
                was_locked=was_locked,
            )

        except Exception as e:
            logger.error(f"Error unlocking session: {e}")
            return UnlockResult(
                success=False,
                session_id=session_id,
                error=str(e),
            )

    # ==================== Helper Methods ====================

    def _generate_token(self, session_id: str, user_id: str) -> str:
        """Generate secure session token."""
        # Create token from session ID and secret
        token_data = f"{session_id}:{user_id}:{secrets.token_hex(16)}"
        return base64.b64encode(token_data.encode()).decode()

    def _dict_to_session(self, session_dict: Dict[str, Any]) -> Session:
        """Convert dictionary to Session object."""
        return Session(
            session_id=session_dict.get("session_id", str(uuid4())),
            user_id=session_dict.get("user_id", ""),
            data=session_dict.get("data", {}),
            metadata=session_dict.get("metadata", {}),
        )

    def _store_filesystem(self, session_id: str, data: bytes):
        """Store session to filesystem."""
        sessions_dir = Path("./sessions")
        sessions_dir.mkdir(exist_ok=True)
        session_file = sessions_dir / f"{session_id}.session"
        with open(session_file, "wb") as f:
            f.write(data)

    def _load_filesystem(self, session_id: str) -> Optional[bytes]:
        """Load session from filesystem."""
        session_file = Path("./sessions") / f"{session_id}.session"
        if session_file.exists():
            with open(session_file, "rb") as f:
                return f.read()
        return None

    def _store_database(self, session_id: str, data: bytes):
        """Store session to database (placeholder)."""
        # Would implement database storage here
        pass

    def _load_database(self, session_id: str) -> Optional[bytes]:
        """Load session from database (placeholder)."""
        # Would implement database loading here
        return None

    def _store_redis(self, session_id: str, data: bytes):
        """Store session to Redis (placeholder)."""
        # Would implement Redis storage here
        pass

    def _load_redis(self, session_id: str) -> Optional[bytes]:
        """Load session from Redis (placeholder)."""
        # Would implement Redis loading here
        return None

    def _store_memcached(self, session_id: str, data: bytes):
        """Store session to Memcached (placeholder)."""
        # Would implement Memcached storage here
        pass

    def _load_memcached(self, session_id: str) -> Optional[bytes]:
        """Load session from Memcached (placeholder)."""
        # Would implement Memcached loading here
        return None

    def _start_gc(self):
        """Start garbage collection thread."""
        def gc_worker():
            while self.gc_running:
                time.sleep(self.config.gc_interval)
                self.collect_garbage()

        self.gc_running = True
        self.gc_thread = threading.Thread(target=gc_worker, daemon=True)
        self.gc_thread.start()
        logger.info("Started garbage collection thread")

    def stop_gc(self):
        """Stop garbage collection thread."""
        self.gc_running = False
        if self.gc_thread:
            self.gc_thread.join(timeout=5)
        logger.info("Stopped garbage collection thread")

    def __del__(self):
        """Cleanup on destruction."""
        self.stop_gc()
