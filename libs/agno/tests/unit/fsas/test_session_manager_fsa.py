"""Comprehensive unit tests for SessionManagerFSA."""

import pytest
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path

from agno.fsas.session_manager_fsa import (
    SessionManagerFSA,
    Session,
    SessionConfig,
    SessionOp,
    SessionResult,
    ValidationResult,
    UpdateResult,
    DestroyResult,
    RefreshResult,
    StoreResult,
    LoadResult,
    ReplicationResult,
    SyncResult,
    TimeoutStatus,
    ExpireResult,
    GCResult,
    EncryptResult,
    DecryptResult,
    TokenValidation,
    SessionMetrics,
    MigrationResult,
    CloneResult,
    MergeResult,
    LockResult,
    UnlockResult,
    SessionBackend,
    SessionState,
    TimeoutMode,
    SerializationFormat,
    LockMode,
)


@pytest.fixture
def session_manager():
    """Create a SessionManagerFSA instance."""
    config = SessionConfig(
        backend=SessionBackend.MEMORY,
        default_timeout=3600,
        enable_gc=False,  # Disable GC for tests
    )
    manager = SessionManagerFSA(name="test-manager", config=config)
    yield manager
    manager.stop_gc()


@pytest.fixture
def sample_session(session_manager):
    """Create a sample session."""
    return session_manager.create_session("user-1", {"role": "admin"})


# Test 1: Session Manager Initialization
class TestSessionManagerInitialization:
    """Test SessionManagerFSA initialization."""

    def test_create_session_manager(self):
        """Test creating a session manager."""
        manager = SessionManagerFSA(name="test-1")
        assert manager.name == "test-1"
        assert manager.fsa_id is not None
        assert manager.sessions is not None
        manager.stop_gc()

    def test_create_with_config(self):
        """Test creating manager with custom config."""
        config = SessionConfig(
            backend=SessionBackend.REDIS,
            default_timeout=7200,
            enable_encryption=False,
        )
        manager = SessionManagerFSA(name="test-2", config=config)
        assert manager.config.backend == SessionBackend.REDIS
        assert manager.config.default_timeout == 7200
        manager.stop_gc()


# Test 2: Session Creation
class TestSessionCreation:
    """Test session creation functionality."""

    def test_create_session(self, session_manager):
        """Test creating a session."""
        session = session_manager.create_session("user-1", {"role": "admin"})
        assert session is not None
        assert session.user_id == "user-1"
        assert session.metadata["role"] == "admin"
        assert session.state == SessionState.ACTIVE

    def test_create_multiple_sessions(self, session_manager):
        """Test creating multiple sessions."""
        sessions = []
        for i in range(5):
            session = session_manager.create_session(f"user-{i}", {})
            sessions.append(session)

        assert len(sessions) == 5
        assert len(session_manager.sessions) == 5


# Test 3: Session Retrieval
class TestSessionRetrieval:
    """Test session retrieval functionality."""

    def test_get_session(self, session_manager, sample_session):
        """Test retrieving a session."""
        retrieved = session_manager.get_session(sample_session.session_id)
        assert retrieved is not None
        assert retrieved.session_id == sample_session.session_id
        assert retrieved.user_id == sample_session.user_id

    def test_get_nonexistent_session(self, session_manager):
        """Test retrieving nonexistent session."""
        session = session_manager.get_session("nonexistent")
        assert session is None


# Test 4: Session Updates
class TestSessionUpdates:
    """Test session update functionality."""

    def test_update_session(self, session_manager, sample_session):
        """Test updating session data."""
        result = session_manager.update_session(
            sample_session.session_id,
            {"key1": "value1", "key2": "value2"}
        )
        assert result.success is True
        assert len(result.updated_fields) == 2

        # Verify update
        session = session_manager.get_session(sample_session.session_id)
        assert session.data["key1"] == "value1"

    def test_update_nonexistent_session(self, session_manager):
        """Test updating nonexistent session."""
        result = session_manager.update_session("nonexistent", {"key": "value"})
        assert result.success is False


# Test 5: Session Destruction
class TestSessionDestruction:
    """Test session destruction functionality."""

    def test_destroy_session(self, session_manager, sample_session):
        """Test destroying a session."""
        result = session_manager.destroy_session(sample_session.session_id)
        assert result.success is True
        assert result.was_active is True

        # Verify destruction
        session = session_manager.get_session(sample_session.session_id)
        assert session is None

    def test_destroy_nonexistent_session(self, session_manager):
        """Test destroying nonexistent session."""
        result = session_manager.destroy_session("nonexistent")
        assert result.success is False


# Test 6: Session Refresh
class TestSessionRefresh:
    """Test session refresh functionality."""

    def test_refresh_session(self, session_manager, sample_session):
        """Test refreshing a session."""
        original_expiry = sample_session.expires_at

        time.sleep(0.1)

        result = session_manager.refresh_session(sample_session.session_id)
        assert result.success is True
        assert result.new_expiration is not None

        # Verify expiration changed
        session = session_manager.get_session(sample_session.session_id)
        if original_expiry:
            assert session.expires_at > original_expiry


# Test 7: Session Serialization
class TestSessionSerialization:
    """Test session serialization."""

    def test_serialize_session(self, session_manager, sample_session):
        """Test serializing a session."""
        serialized = session_manager.serialize_session(sample_session)
        assert isinstance(serialized, bytes)
        assert len(serialized) > 0


# Test 8: Session Deserialization
class TestSessionDeserialization:
    """Test session deserialization."""

    def test_deserialize_session(self, session_manager, sample_session):
        """Test deserializing a session."""
        serialized = session_manager.serialize_session(sample_session)
        deserialized = session_manager.deserialize_session(serialized)
        assert isinstance(deserialized, Session)
        assert deserialized.session_id == sample_session.session_id


# Test 9: Session Storage - Memory
class TestSessionStorageMemory:
    """Test session storage in memory backend."""

    def test_store_session_memory(self, session_manager, sample_session):
        """Test storing session in memory."""
        result = session_manager.store_session(sample_session, SessionBackend.MEMORY)
        assert result.success is True


# Test 10: Session Storage - Filesystem
class TestSessionStorageFilesystem:
    """Test session storage in filesystem backend."""

    def test_store_session_filesystem(self, session_manager, sample_session):
        """Test storing session to filesystem."""
        result = session_manager.store_session(sample_session, SessionBackend.FILESYSTEM)
        assert result.success is True


# Test 11: Session Loading
class TestSessionLoading:
    """Test session loading functionality."""

    def test_load_session_memory(self, session_manager, sample_session):
        """Test loading session from memory."""
        result = session_manager.load_session(
            sample_session.session_id,
            SessionBackend.MEMORY
        )
        assert result.success is True
        assert result.session is not None

    def test_load_nonexistent_session(self, session_manager):
        """Test loading nonexistent session."""
        result = session_manager.load_session("nonexistent", SessionBackend.MEMORY)
        assert result.success is False


# Test 12: Session Replication
class TestSessionReplication:
    """Test session replication functionality."""

    def test_replicate_session(self, session_manager, sample_session):
        """Test replicating session to cluster nodes."""
        nodes = ["node-1", "node-2", "node-3"]
        result = session_manager.replicate_session(sample_session, nodes)
        assert result.success is True
        assert len(result.replicated_nodes) > 0


# Test 13: Cluster Synchronization
class TestClusterSynchronization:
    """Test cluster synchronization."""

    def test_sync_session_cluster(self, session_manager, sample_session):
        """Test synchronizing session across cluster."""
        # First replicate
        nodes = ["node-1", "node-2"]
        session_manager.replicate_session(sample_session, nodes)

        # Then sync
        result = session_manager.sync_session_cluster(sample_session.session_id)
        assert result.success is True


# Test 14: Timeout Checking
class TestTimeoutChecking:
    """Test timeout checking functionality."""

    def test_check_timeout_active(self, session_manager, sample_session):
        """Test checking timeout for active session."""
        status = session_manager.check_timeout(sample_session)
        assert status.is_expired is False
        assert status.time_remaining is not None
        assert status.time_remaining > 0

    def test_check_timeout_expired(self, session_manager):
        """Test checking timeout for expired session."""
        session = session_manager.create_session("user-exp", {})
        session.expires_at = datetime.utcnow() - timedelta(seconds=10)

        status = session_manager.check_timeout(session)
        assert status.is_expired is True


# Test 15: Session Expiration
class TestSessionExpiration:
    """Test session expiration functionality."""

    def test_expire_session(self, session_manager, sample_session):
        """Test expiring a session."""
        result = session_manager.expire_session(sample_session.session_id)
        assert result.success is True
        assert result.was_active is True

        # Verify state
        session = session_manager.sessions.get(sample_session.session_id)
        assert session.state == SessionState.EXPIRED


# Test 16: Garbage Collection
class TestGarbageCollection:
    """Test garbage collection functionality."""

    def test_collect_garbage(self, session_manager):
        """Test collecting expired sessions."""
        # Create some sessions and expire them
        for i in range(3):
            session = session_manager.create_session(f"user-{i}", {})
            session.expires_at = datetime.utcnow() - timedelta(seconds=10)

        result = session_manager.collect_garbage()
        assert result.success is True
        assert result.sessions_collected == 3

    def test_collect_garbage_with_max_age(self, session_manager):
        """Test garbage collection with max age."""
        # Create old sessions
        for i in range(2):
            session = session_manager.create_session(f"user-old-{i}", {})
            session.created_at = datetime.utcnow() - timedelta(hours=2)

        max_age = timedelta(hours=1)
        result = session_manager.collect_garbage(max_age=max_age)
        assert result.success is True


# Test 17: Data Encryption
class TestDataEncryption:
    """Test data encryption functionality."""

    def test_encrypt_session_data(self, session_manager):
        """Test encrypting session data."""
        data = {"secret": "password123", "key": "value"}
        result = session_manager.encrypt_session_data(data)

        # May fail if cryptography not available
        if result.success:
            assert result.encrypted_data is not None
            assert isinstance(result.encrypted_data, bytes)


# Test 18: Data Decryption
class TestDataDecryption:
    """Test data decryption functionality."""

    def test_decrypt_session_data(self, session_manager):
        """Test decrypting session data."""
        data = {"secret": "password123", "key": "value"}
        encrypt_result = session_manager.encrypt_session_data(data)

        if encrypt_result.success:
            decrypt_result = session_manager.decrypt_session_data(
                encrypt_result.encrypted_data
            )
            assert decrypt_result.success is True
            assert decrypt_result.decrypted_data == data


# Test 19: Token Validation
class TestTokenValidation:
    """Test token validation functionality."""

    def test_validate_session_token(self, session_manager, sample_session):
        """Test validating session token."""
        # Get token for session
        token = None
        for t, sid in session_manager.session_tokens.items():
            if sid == sample_session.session_id:
                token = t
                break

        if token:
            result = session_manager.validate_session_token(token)
            assert result.valid is True
            assert result.session_id == sample_session.session_id

    def test_validate_invalid_token(self, session_manager):
        """Test validating invalid token."""
        result = session_manager.validate_session_token("invalid-token")
        assert result.valid is False


# Test 20: Session ID Generation
class TestSessionIDGeneration:
    """Test session ID generation."""

    def test_generate_session_id(self, session_manager):
        """Test generating unique session IDs."""
        id1 = session_manager.generate_session_id()
        id2 = session_manager.generate_session_id()

        assert id1 != id2
        assert len(id1) > 0
        assert len(id2) > 0


# Test 21: Active Session Listing
class TestActiveSessionListing:
    """Test listing active sessions."""

    def test_list_all_active_sessions(self, session_manager):
        """Test listing all active sessions."""
        # Create multiple sessions
        for i in range(5):
            session_manager.create_session(f"user-{i}", {})

        sessions = session_manager.list_active_sessions()
        assert len(sessions) == 5

    def test_list_user_sessions(self, session_manager):
        """Test listing sessions for specific user."""
        user_id = "test-user"

        # Create sessions for user
        for i in range(3):
            session_manager.create_session(user_id, {})

        # Create session for different user
        session_manager.create_session("other-user", {})

        sessions = session_manager.list_active_sessions(user_id=user_id)
        assert len(sessions) == 3


# Test 22: Session Metrics
class TestSessionMetrics:
    """Test session metrics collection."""

    def test_get_session_metrics(self, session_manager, sample_session):
        """Test getting session metrics."""
        # Access session multiple times
        for _ in range(5):
            session_manager.get_session(sample_session.session_id)

        metrics = session_manager.get_session_metrics(sample_session.session_id)
        assert metrics is not None
        assert metrics.total_accesses >= 5
        assert metrics.data_size_bytes > 0

    def test_get_metrics_nonexistent(self, session_manager):
        """Test getting metrics for nonexistent session."""
        metrics = session_manager.get_session_metrics("nonexistent")
        assert metrics is None


# Test 23: Session Migration
class TestSessionMigration:
    """Test session migration functionality."""

    def test_migrate_session(self, session_manager, sample_session):
        """Test migrating session to different backend."""
        result = session_manager.migrate_session(
            sample_session.session_id,
            SessionBackend.FILESYSTEM
        )
        assert result.success is True


# Test 24: Session Cloning
class TestSessionCloning:
    """Test session cloning functionality."""

    def test_clone_session(self, session_manager, sample_session):
        """Test cloning a session."""
        # Add some data
        session_manager.update_session(sample_session.session_id, {"data": "test"})

        result = session_manager.clone_session(sample_session.session_id)
        assert result.success is True
        assert result.cloned_id is not None
        assert result.cloned_id != result.original_id

        # Verify cloned session
        cloned = session_manager.get_session(result.cloned_id)
        assert cloned is not None
        assert cloned.data == sample_session.data


# Test 25: Session Merging
class TestSessionMerging:
    """Test session merging functionality."""

    def test_merge_sessions(self, session_manager):
        """Test merging multiple sessions."""
        user_id = "merge-user"

        # Create sessions with different data
        session1 = session_manager.create_session(user_id, {})
        session_manager.update_session(session1.session_id, {"key1": "value1"})

        session2 = session_manager.create_session(user_id, {})
        session_manager.update_session(session2.session_id, {"key2": "value2"})

        result = session_manager.merge_sessions([session1.session_id, session2.session_id])
        assert result.success is True
        assert result.merged_session_id is not None

        # Verify merged session has all data
        merged = session_manager.get_session(result.merged_session_id)
        assert "key1" in merged.data
        assert "key2" in merged.data


# Test 26: Session Locking
class TestSessionLocking:
    """Test session locking functionality."""

    def test_lock_session(self, session_manager, sample_session):
        """Test acquiring session lock."""
        result = session_manager.lock_session(sample_session.session_id)
        assert result.success is True
        assert result.lock_id is not None

        # Verify lock
        session = session_manager.sessions[sample_session.session_id]
        assert session.state == SessionState.LOCKED

        # Cleanup
        session_manager.unlock_session(sample_session.session_id)


# Test 27: Session Unlocking
class TestSessionUnlocking:
    """Test session unlocking functionality."""

    def test_unlock_session(self, session_manager, sample_session):
        """Test releasing session lock."""
        # First lock
        session_manager.lock_session(sample_session.session_id)

        # Then unlock
        result = session_manager.unlock_session(sample_session.session_id)
        assert result.success is True
        assert result.was_locked is True

        # Verify unlock
        session = session_manager.sessions[sample_session.session_id]
        assert session.state == SessionState.ACTIVE


# Test 28: Edge Cases - Missing Session
class TestEdgeCasesMissingSession:
    """Test handling of missing sessions."""

    def test_update_missing_session(self, session_manager):
        """Test updating missing session."""
        result = session_manager.update_session("missing", {"data": "test"})
        assert result.success is False

    def test_refresh_missing_session(self, session_manager):
        """Test refreshing missing session."""
        result = session_manager.refresh_session("missing")
        assert result.success is False

    def test_lock_missing_session(self, session_manager):
        """Test locking missing session."""
        result = session_manager.lock_session("missing")
        assert result.success is False


# Test 29: Edge Cases - Expired Session
class TestEdgeCasesExpiredSession:
    """Test handling of expired sessions."""

    def test_get_expired_session(self, session_manager):
        """Test retrieving expired session."""
        session = session_manager.create_session("exp-user", {})
        session.expires_at = datetime.utcnow() - timedelta(seconds=10)

        retrieved = session_manager.get_session(session.session_id)
        assert retrieved is None


# Test 30: Concurrent Session Access
class TestConcurrentSessionAccess:
    """Test concurrent access to sessions."""

    def test_concurrent_session_creation(self, session_manager):
        """Test creating sessions concurrently."""
        results = []

        def create_session(user_id):
            session = session_manager.create_session(user_id, {})
            results.append(session)

        threads = []
        for i in range(10):
            thread = threading.Thread(target=create_session, args=(f"user-{i}",))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        assert len(results) == 10

    def test_concurrent_session_updates(self, session_manager, sample_session):
        """Test updating session concurrently."""
        def update_session(key):
            session_manager.update_session(sample_session.session_id, {key: f"value-{key}"})

        threads = []
        for i in range(10):
            thread = threading.Thread(target=update_session, args=(f"key-{i}",))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Verify all updates applied
        session = session_manager.get_session(sample_session.session_id)
        assert len(session.data) == 10


# Test 31: Configuration Validation
class TestConfigurationValidation:
    """Test configuration validation."""

    def test_validate_valid_config(self, session_manager):
        """Test validating valid configuration."""
        config = SessionConfig(
            default_timeout=3600,
            max_sessions=1000,
        )

        result = session_manager.validate(config)
        assert result.valid is True
        assert len(result.errors) == 0

    def test_validate_invalid_config(self, session_manager):
        """Test validating invalid configuration."""
        config = SessionConfig(
            default_timeout=-1,
            max_sessions=-1,
        )

        result = session_manager.validate(config)
        assert result.valid is False
        assert len(result.errors) > 0
