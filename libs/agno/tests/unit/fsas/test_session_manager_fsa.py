"""
Comprehensive unit tests for Session Manager FSA.

Tests cover:
    - Session creation and lifecycle
    - State transitions
    - Storage backends (Memory, Redis, Database)
    - Security features (CSRF, fingerprinting, session hijacking)
    - Session timeout and expiration
    - Multi-device session management
    - Session analytics
    - Concurrent session limiting
"""

import json
import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest

from agno.fsas.infrastructure.session_manager_fsa import (
    DatabaseStorageBackend,
    MemoryStorageBackend,
    RedisStorageBackend,
    SecurityLevel,
    Session,
    SessionAnalytics,
    SessionEvent,
    SessionManagerFSA,
    SessionMetadata,
    SessionSecurity,
    SessionState,
    StorageBackend,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def memory_backend():
    """Create a memory storage backend."""
    return MemoryStorageBackend()


@pytest.fixture
def session_manager(memory_backend):
    """Create a session manager with memory backend."""
    return SessionManagerFSA(storage_backend=memory_backend)


@pytest.fixture
def sample_session():
    """Create a sample session for testing."""
    return Session(
        session_id="test-session-123",
        user_id="user-456",
        data={"key": "value", "counter": 0},
        idle_timeout_seconds=1800,
        absolute_timeout_seconds=86400,
    )


@pytest.fixture
def sample_metadata():
    """Create sample session metadata."""
    return {
        "user_agent": "Mozilla/5.0",
        "ip_address": "192.168.1.1",
        "device_id": "device-123",
        "device_type": "desktop",
        "browser": "Chrome",
        "os": "Windows",
        "location": "US",
    }


# ============================================================================
# Session Model Tests
# ============================================================================


def test_session_creation():
    """Test basic session creation."""
    session = Session()

    assert session.session_id is not None
    assert len(session.session_id) >= 16
    assert session.state == SessionState.CREATED
    assert session.data == {}
    assert session.is_authenticated is False
    assert session.is_persistent is False
    assert session.is_locked is False


def test_session_validation():
    """Test session ID validation."""
    with pytest.raises(ValueError):
        Session(session_id="short")


def test_session_expiration_check():
    """Test session expiration detection."""
    # Create session that expires in the past
    session = Session()
    session.expires_at = datetime.utcnow() - timedelta(hours=1)

    assert session.is_expired() is True

    # Create session that expires in the future
    session2 = Session()
    session2.expires_at = datetime.utcnow() + timedelta(hours=1)

    assert session2.is_expired() is False


def test_session_idle_timeout():
    """Test idle timeout detection."""
    session = Session(idle_timeout_seconds=10)
    session.last_activity = datetime.utcnow() - timedelta(seconds=20)

    assert session.is_expired() is True


def test_session_absolute_timeout():
    """Test absolute timeout detection."""
    session = Session(absolute_timeout_seconds=10)
    session.created_at = datetime.utcnow() - timedelta(seconds=20)

    assert session.is_expired() is True


def test_session_update_activity():
    """Test session activity update."""
    session = Session()
    initial_activity = session.last_activity
    initial_count = session.metadata.access_count

    time.sleep(0.01)  # Small delay
    session.update_activity()

    assert session.last_activity > initial_activity
    assert session.metadata.access_count == initial_count + 1


def test_session_fingerprint_calculation():
    """Test session fingerprint calculation."""
    session = Session(session_id="test-session-123456", user_id="user-456")
    session.metadata.user_agent = "Mozilla/5.0"
    session.metadata.ip_address = "192.168.1.1"

    fingerprint1 = session.calculate_fingerprint("salt123")
    fingerprint2 = session.calculate_fingerprint("salt123")
    fingerprint3 = session.calculate_fingerprint("different-salt")

    assert fingerprint1 == fingerprint2
    assert fingerprint1 != fingerprint3
    assert len(fingerprint1) == 64  # SHA256 hex length


# ============================================================================
# Memory Storage Backend Tests
# ============================================================================


def test_memory_backend_save(memory_backend, sample_session):
    """Test saving a session to memory backend."""
    result = memory_backend.save(sample_session)

    assert result is True
    assert memory_backend.exists(sample_session.session_id) is True


def test_memory_backend_load(memory_backend, sample_session):
    """Test loading a session from memory backend."""
    memory_backend.save(sample_session)
    loaded = memory_backend.load(sample_session.session_id)

    assert loaded is not None
    assert loaded.session_id == sample_session.session_id
    assert loaded.user_id == sample_session.user_id
    assert loaded.data == sample_session.data


def test_memory_backend_delete(memory_backend, sample_session):
    """Test deleting a session from memory backend."""
    memory_backend.save(sample_session)
    result = memory_backend.delete(sample_session.session_id)

    assert result is True
    assert memory_backend.exists(sample_session.session_id) is False


def test_memory_backend_list_user_sessions(memory_backend):
    """Test listing user sessions from memory backend."""
    session1 = Session(user_id="user-123")
    session2 = Session(user_id="user-123")
    session3 = Session(user_id="user-456")

    memory_backend.save(session1)
    memory_backend.save(session2)
    memory_backend.save(session3)

    user_sessions = memory_backend.list_user_sessions("user-123")

    assert len(user_sessions) == 2
    assert all(s.user_id == "user-123" for s in user_sessions)


def test_memory_backend_cleanup_expired(memory_backend):
    """Test cleaning up expired sessions from memory backend."""
    # Create expired session
    expired_session = Session()
    expired_session.expires_at = datetime.utcnow() - timedelta(hours=1)
    memory_backend.save(expired_session)

    # Create active session
    active_session = Session()
    active_session.expires_at = datetime.utcnow() + timedelta(hours=1)
    memory_backend.save(active_session)

    # Cleanup
    count = memory_backend.cleanup_expired()

    assert count == 1
    assert memory_backend.exists(expired_session.session_id) is False
    assert memory_backend.exists(active_session.session_id) is True


def test_memory_backend_count_active_sessions(memory_backend):
    """Test counting active sessions in memory backend."""
    # Create active sessions
    session1 = Session(user_id="user-123")
    session2 = Session(user_id="user-123")
    session3 = Session(user_id="user-456")

    memory_backend.save(session1)
    memory_backend.save(session2)
    memory_backend.save(session3)

    # Create expired session
    expired = Session(user_id="user-123")
    expired.expires_at = datetime.utcnow() - timedelta(hours=1)
    memory_backend.save(expired)

    count_all = memory_backend.count_active_sessions()
    count_user = memory_backend.count_active_sessions("user-123")

    assert count_all == 3
    assert count_user == 2


# ============================================================================
# Session Manager Core Operations Tests
# ============================================================================


def test_create_session_basic(session_manager):
    """Test basic session creation through manager."""
    session = session_manager.create_session(user_id="user-123")

    assert session is not None
    assert session.session_id is not None
    assert session.user_id == "user-123"
    assert session.state == SessionState.CREATED
    assert session_manager.storage_backend.exists(session.session_id)


def test_create_session_with_data(session_manager, sample_metadata):
    """Test creating session with initial data and metadata."""
    session_data = {"preference": "dark_mode", "language": "en"}

    session = session_manager.create_session(
        user_id="user-123", session_data=session_data, metadata=sample_metadata, security_level=SecurityLevel.HIGH
    )

    assert session.data == session_data
    assert session.metadata.user_agent == "Mozilla/5.0"
    assert session.metadata.ip_address == "192.168.1.1"
    assert session.security.security_level == SecurityLevel.HIGH


def test_get_session(session_manager):
    """Test getting a session by ID."""
    created_session = session_manager.create_session(user_id="user-123")
    retrieved_session = session_manager.get_session(created_session.session_id)

    assert retrieved_session is not None
    assert retrieved_session.session_id == created_session.session_id
    assert retrieved_session.user_id == created_session.user_id


def test_get_nonexistent_session(session_manager):
    """Test getting a non-existent session."""
    session = session_manager.get_session("nonexistent-session-id-12345")

    assert session is None


def test_get_expired_session(session_manager):
    """Test getting an expired session."""
    session = session_manager.create_session(user_id="user-123", absolute_timeout_seconds=1)

    # Wait for expiration
    time.sleep(1.1)

    retrieved = session_manager.get_session(session.session_id)

    assert retrieved is None


def test_update_session(session_manager):
    """Test updating session data."""
    session = session_manager.create_session(user_id="user-123", session_data={"counter": 0})

    result = session_manager.update_session(session.session_id, {"counter": 5, "new_key": "value"})

    assert result is True

    updated = session_manager.get_session(session.session_id)
    assert updated.data["counter"] == 5
    assert updated.data["new_key"] == "value"


def test_update_locked_session(session_manager):
    """Test updating a locked session (should fail)."""
    session = session_manager.create_session(user_id="user-123")
    session_manager.lock_session(session.session_id)

    result = session_manager.update_session(session.session_id, {"key": "value"})

    assert result is False


def test_delete_session(session_manager):
    """Test deleting a session."""
    session = session_manager.create_session(user_id="user-123")
    result = session_manager.delete_session(session.session_id)

    assert result is True
    assert session_manager.get_session(session.session_id) is None


def test_invalidate_session(session_manager):
    """Test invalidating a session."""
    session = session_manager.create_session(user_id="user-123")
    result = session_manager.invalidate_session(session.session_id, reason="security_breach")

    assert result is True
    assert session_manager.get_session(session.session_id) is None


def test_refresh_session(session_manager):
    """Test refreshing a session."""
    session = session_manager.create_session(user_id="user-123")
    original_activity = session.last_activity

    time.sleep(0.01)
    result = session_manager.refresh_session(session.session_id)

    assert result is True

    refreshed = session_manager.get_session(session.session_id)
    assert refreshed.last_activity > original_activity


def test_rotate_session(session_manager):
    """Test rotating a session ID."""
    session = session_manager.create_session(user_id="user-123", session_data={"key": "value"})
    original_id = session.session_id

    new_id = session_manager.rotate_session(original_id)

    assert new_id is not None
    assert new_id != original_id

    # Old session should not exist
    assert session_manager.get_session(original_id) is None

    # New session should exist with same data
    new_session = session_manager.get_session(new_id)
    assert new_session is not None
    assert new_session.data["key"] == "value"
    assert new_session.security.rotation_count == 1


# ============================================================================
# Security Tests
# ============================================================================


def test_csrf_token_generation(session_manager):
    """Test CSRF token is generated for new sessions."""
    session = session_manager.create_session(user_id="user-123")

    assert session.security.csrf_token is not None
    assert len(session.security.csrf_token) > 20


def test_validate_csrf_token(session_manager):
    """Test CSRF token validation."""
    session = session_manager.create_session(user_id="user-123")
    csrf_token = session.security.csrf_token

    # Valid token
    assert session_manager.validate_csrf_token(session.session_id, csrf_token) is True

    # Invalid token
    assert session_manager.validate_csrf_token(session.session_id, "wrong-token") is False


def test_session_fingerprint_validation(session_manager):
    """Test session fingerprint validation."""
    metadata = {"user_agent": "Mozilla/5.0", "ip_address": "192.168.1.1"}

    session = session_manager.create_session(user_id="user-123", metadata=metadata, security_level=SecurityLevel.HIGH)

    # Enable binding
    loaded = session_manager.storage_backend.load(session.session_id)
    loaded.security.user_agent_binding = True
    loaded.security.ip_binding = True
    session_manager.storage_backend.save(loaded)

    # Same fingerprint should validate
    assert (
        session_manager.validate_session_fingerprint(session.session_id, "Mozilla/5.0", "192.168.1.1") is True
    )

    # Different user agent should fail
    assert session_manager.validate_session_fingerprint(session.session_id, "Chrome/1.0", "192.168.1.1") is False

    # Different IP should fail
    assert session_manager.validate_session_fingerprint(session.session_id, "Mozilla/5.0", "10.0.0.1") is False


def test_lock_and_unlock_session(session_manager):
    """Test locking and unlocking sessions."""
    session = session_manager.create_session(user_id="user-123")

    # Activate session first
    loaded = session_manager.storage_backend.load(session.session_id)
    session_manager._transition(loaded, SessionEvent.ACTIVATE)
    session_manager.storage_backend.save(loaded)

    # Lock session
    result = session_manager.lock_session(session.session_id, reason="suspicious_activity")
    assert result is True

    locked = session_manager.get_session(session.session_id)
    assert locked.is_locked is True
    assert locked.state == SessionState.LOCKED

    # Unlock session
    result = session_manager.unlock_session(session.session_id)
    assert result is True

    unlocked = session_manager.get_session(session.session_id)
    assert unlocked.is_locked is False
    assert unlocked.state == SessionState.ACTIVE


# ============================================================================
# Multi-User Operations Tests
# ============================================================================


def test_list_user_sessions(session_manager):
    """Test listing all sessions for a user."""
    session1 = session_manager.create_session(user_id="user-123")
    session2 = session_manager.create_session(user_id="user-123")
    session3 = session_manager.create_session(user_id="user-456")

    sessions = session_manager.list_user_sessions("user-123")

    assert len(sessions) == 2
    assert all(s.user_id == "user-123" for s in sessions)


def test_invalidate_all_user_sessions(session_manager):
    """Test invalidating all sessions for a user."""
    session1 = session_manager.create_session(user_id="user-123")
    session2 = session_manager.create_session(user_id="user-123")
    session3 = session_manager.create_session(user_id="user-123")

    count = session_manager.invalidate_all_user_sessions("user-123")

    assert count == 3
    assert len(session_manager.list_user_sessions("user-123")) == 0


def test_invalidate_all_except_current(session_manager):
    """Test invalidating all user sessions except current one."""
    session1 = session_manager.create_session(user_id="user-123")
    session2 = session_manager.create_session(user_id="user-123")
    session3 = session_manager.create_session(user_id="user-123")

    count = session_manager.invalidate_all_user_sessions("user-123", except_session_id=session2.session_id)

    assert count == 2

    remaining = session_manager.list_user_sessions("user-123")
    assert len(remaining) == 1
    assert remaining[0].session_id == session2.session_id


def test_concurrent_session_limit_enforcement(session_manager):
    """Test enforcement of concurrent session limits."""
    # Create 6 sessions (exceeds default limit of 5)
    sessions = []
    for i in range(6):
        session = session_manager.create_session(user_id="user-123")
        sessions.append(session)

    # Check that oldest sessions were removed
    user_sessions = session_manager.list_user_sessions("user-123")
    assert len(user_sessions) <= 5


# ============================================================================
# State Transition Tests
# ============================================================================


def test_state_transition_created_to_active(session_manager):
    """Test state transition from CREATED to ACTIVE."""
    session = session_manager.create_session(user_id="user-123")
    assert session.state == SessionState.CREATED

    # Activate session
    loaded = session_manager.storage_backend.load(session.session_id)
    session_manager._transition(loaded, SessionEvent.ACTIVATE)
    session_manager.storage_backend.save(loaded)

    updated = session_manager.get_session(session.session_id)
    assert updated.state == SessionState.ACTIVE


def test_state_transition_active_to_idle(session_manager):
    """Test state transition from ACTIVE to IDLE."""
    session = session_manager.create_session(user_id="user-123")

    loaded = session_manager.storage_backend.load(session.session_id)
    session_manager._transition(loaded, SessionEvent.ACTIVATE)
    session_manager._transition(loaded, SessionEvent.IDLE_TIMEOUT)
    session_manager.storage_backend.save(loaded)

    updated = session_manager.get_session(session.session_id)
    assert updated.state == SessionState.IDLE


def test_state_transition_idle_to_active(session_manager):
    """Test state transition from IDLE back to ACTIVE."""
    session = session_manager.create_session(user_id="user-123")

    loaded = session_manager.storage_backend.load(session.session_id)
    session_manager._transition(loaded, SessionEvent.ACTIVATE)
    session_manager._transition(loaded, SessionEvent.IDLE_TIMEOUT)
    session_manager._transition(loaded, SessionEvent.ACCESS)
    session_manager.storage_backend.save(loaded)

    updated = session_manager.get_session(session.session_id)
    assert updated.state == SessionState.ACTIVE


# ============================================================================
# Analytics Tests
# ============================================================================


def test_analytics_session_created(session_manager):
    """Test analytics tracking for session creation."""
    initial_count = session_manager.analytics.total_sessions_created

    session_manager.create_session(user_id="user-123")

    assert session_manager.analytics.total_sessions_created == initial_count + 1
    assert session_manager.analytics.active_sessions_count == initial_count + 1


def test_analytics_session_invalidated(session_manager):
    """Test analytics tracking for session invalidation."""
    session = session_manager.create_session(user_id="user-123")
    initial_count = session_manager.analytics.total_sessions_invalidated

    session_manager.invalidate_session(session.session_id)

    assert session_manager.analytics.total_sessions_invalidated == initial_count + 1


def test_analytics_security_events(session_manager):
    """Test analytics tracking for security events."""
    session = session_manager.create_session(user_id="user-123")
    initial_count = len(session_manager.analytics.security_events)

    session_manager.lock_session(session.session_id, reason="test")

    assert len(session_manager.analytics.security_events) == initial_count + 1


def test_get_analytics(session_manager):
    """Test getting analytics statistics."""
    session_manager.create_session(user_id="user-123")
    session_manager.create_session(user_id="user-456")

    stats = session_manager.get_analytics()

    assert "total_created" in stats
    assert "active_count" in stats
    assert "peak_concurrent" in stats
    assert stats["total_created"] >= 2


def test_get_session_info(session_manager, sample_metadata):
    """Test getting detailed session information."""
    session = session_manager.create_session(user_id="user-123", metadata=sample_metadata)

    info = session_manager.get_session_info(session.session_id)

    assert info is not None
    assert info["session_id"] == session.session_id
    assert info["user_id"] == "user-123"
    assert info["state"] == SessionState.CREATED
    assert info["is_expired"] is False
    assert info["device_type"] == "desktop"


# ============================================================================
# Cleanup Tests
# ============================================================================


def test_cleanup_expired_sessions(session_manager):
    """Test cleanup of expired sessions."""
    # Create expired session
    expired = session_manager.create_session(user_id="user-123", absolute_timeout_seconds=1)

    # Create active session
    active = session_manager.create_session(user_id="user-456")

    # Wait for expiration
    time.sleep(1.1)

    count = session_manager.cleanup_expired_sessions()

    assert count == 1
    assert session_manager.storage_backend.exists(expired.session_id) is False
    assert session_manager.storage_backend.exists(active.session_id) is True


def test_auto_cleanup_interval(session_manager):
    """Test automatic cleanup based on interval."""
    session_manager.cleanup_interval = 1

    # Create expired session
    session_manager.create_session(user_id="user-123", absolute_timeout_seconds=1)

    time.sleep(1.1)

    # First call should clean up
    count1 = session_manager.auto_cleanup_if_needed()
    assert count1 == 1

    # Immediate second call should not clean up (interval not passed)
    count2 = session_manager.auto_cleanup_if_needed()
    assert count2 == 0


# ============================================================================
# Utility Methods Tests
# ============================================================================


def test_generate_secure_token():
    """Test secure token generation."""
    token1 = SessionManagerFSA.generate_secure_token()
    token2 = SessionManagerFSA.generate_secure_token()

    assert len(token1) > 20
    assert len(token2) > 20
    assert token1 != token2


def test_hash_data():
    """Test data hashing."""
    hash1 = SessionManagerFSA.hash_data("test_data", "salt123")
    hash2 = SessionManagerFSA.hash_data("test_data", "salt123")
    hash3 = SessionManagerFSA.hash_data("test_data", "different_salt")

    assert hash1 == hash2
    assert hash1 != hash3
    assert len(hash1) == 64  # SHA256 hex length


# ============================================================================
# Redis Backend Tests (mocked)
# ============================================================================


def test_redis_backend_initialization():
    """Test Redis backend initialization."""
    backend = RedisStorageBackend(host="localhost", port=6379, db=0)

    assert backend.host == "localhost"
    assert backend.port == 6379
    assert backend.db == 0


def test_redis_backend_save():
    """Test saving to Redis backend (mocked)."""
    try:
        import redis
    except ImportError:
        pytest.skip("Redis library not installed")

    with patch("redis.Redis") as mock_redis_class:
        mock_client = MagicMock()
        mock_redis_class.return_value = mock_client

        backend = RedisStorageBackend()
        session = Session(user_id="user-123")

        result = backend.save(session)

        assert result is True
        assert mock_client.setex.called


def test_redis_backend_load():
    """Test loading from Redis backend (mocked)."""
    try:
        import redis
    except ImportError:
        pytest.skip("Redis library not installed")

    with patch("redis.Redis") as mock_redis_class:
        mock_client = MagicMock()
        mock_redis_class.return_value = mock_client

        session = Session(user_id="user-123")
        mock_client.get.return_value = session.model_dump_json()

        backend = RedisStorageBackend()
        loaded = backend.load(session.session_id)

        assert loaded is not None
        assert loaded.user_id == "user-123"


# ============================================================================
# Database Backend Tests (integration-style, using SQLite in memory)
# ============================================================================


def test_database_backend_initialization():
    """Test database backend initialization."""
    backend = DatabaseStorageBackend(connection_string="sqlite:///:memory:")

    assert backend.connection_string == "sqlite:///:memory:"


def test_database_backend_operations():
    """Test basic database backend operations."""
    try:
        import sqlalchemy
    except ImportError:
        pytest.skip("SQLAlchemy not installed")

    backend = DatabaseStorageBackend(connection_string="sqlite:///:memory:")
    session = Session(user_id="user-123", session_data={"key": "value"})

    # Test save
    result = backend.save(session)
    assert result is True

    # Test exists
    assert backend.exists(session.session_id) is True

    # Test load
    loaded = backend.load(session.session_id)
    assert loaded is not None
    assert loaded.user_id == "user-123"

    # Test delete
    result = backend.delete(session.session_id)
    assert result is True
    assert backend.exists(session.session_id) is False


# ============================================================================
# Edge Cases and Error Handling Tests
# ============================================================================


def test_session_manager_with_disabled_analytics():
    """Test session manager with analytics disabled."""
    backend = MemoryStorageBackend()
    manager = SessionManagerFSA(storage_backend=backend, enable_analytics=False)

    session = manager.create_session(user_id="user-123")

    stats = manager.get_analytics()
    assert stats == {}


def test_update_nonexistent_session(session_manager):
    """Test updating a non-existent session."""
    result = session_manager.update_session("nonexistent-id", {"key": "value"})

    assert result is False


def test_delete_nonexistent_session(session_manager):
    """Test deleting a non-existent session."""
    result = session_manager.delete_session("nonexistent-id")

    # Should return False since session doesn't exist
    assert result is False


def test_refresh_nonexistent_session(session_manager):
    """Test refreshing a non-existent session."""
    result = session_manager.refresh_session("nonexistent-id")

    assert result is False


def test_rotate_nonexistent_session(session_manager):
    """Test rotating a non-existent session."""
    new_id = session_manager.rotate_session("nonexistent-id")

    assert new_id is None


def test_session_metadata_tracking(session_manager, sample_metadata):
    """Test comprehensive session metadata tracking."""
    session = session_manager.create_session(user_id="user-123", metadata=sample_metadata)

    assert session.metadata.user_agent == "Mozilla/5.0"
    assert session.metadata.ip_address == "192.168.1.1"
    assert session.metadata.device_type == "desktop"
    assert session.metadata.browser == "Chrome"
    assert session.metadata.os == "Windows"
    assert session.metadata.location == "US"
    assert session.metadata.access_count == 0

    # Update activity
    session_manager.refresh_session(session.session_id)
    updated = session_manager.get_session(session.session_id)

    assert updated.metadata.access_count == 1
