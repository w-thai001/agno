"""Unit tests for SingletonPatternFSA."""

import pytest
import pickle
import threading
import time
from typing import Any

from agno.fsas.singleton_pattern_fsa import (
    SingletonPatternFSA,
    SingletonConfig,
    SingletonMeta,
    BaseSingleton,
    EagerSingleton,
    LazySingleton,
    ConfigurationSingleton,
    DatabaseConnectionSingleton,
    MultitonManager,
    SingletonFactory,
    SingletonOp,
    SingletonResult,
    ValidationResult,
    DestroyResult,
    RegisterResult,
    MultitonInstance,
    ClearResult,
    DeserializationResult,
    StateValidation,
    ResetResult,
    CloneResult,
    LockResult,
    UnlockResult,
    SingletonMetrics,
)


# ==================== Test Singletons ====================

class TestSingleton(BaseSingleton, metaclass=SingletonMeta):
    """Test singleton class."""

    def __init__(self, value: str = "default"):
        super().__init__()
        self.value = value
        self.counter = 0

    def increment(self):
        """Increment counter."""
        self.counter += 1


class AnotherSingleton(BaseSingleton, metaclass=SingletonMeta):
    """Another test singleton class."""

    def __init__(self):
        super().__init__()
        self.data = {}


class RegularClass:
    """Regular non-singleton class for testing."""

    def __init__(self, value: str = "default"):
        self.value = value


class EagerTestSingleton(EagerSingleton):
    """Eager test singleton."""

    def __init__(self):
        super().__init__()
        self.initialized = True


class LazyTestSingleton(LazySingleton):
    """Lazy test singleton."""

    def __init__(self):
        super().__init__()
        self.initialized = True


# ==================== Fixtures ====================

@pytest.fixture
def singleton_pattern():
    """Create singleton pattern instance."""
    config = SingletonConfig()
    pattern = SingletonPatternFSA(config)

    # Clean up singletons before test
    SingletonMeta._instances.clear()
    SingletonMeta._locks.clear()
    pattern.multiton_manager.instances.clear()

    yield pattern

    # Clean up after test
    SingletonMeta._instances.clear()
    SingletonMeta._locks.clear()
    pattern.multiton_manager.instances.clear()


@pytest.fixture
def configured_pattern():
    """Create pre-configured singleton pattern."""
    config = SingletonConfig(
        enable_lazy=True,
        enable_eager=True,
        enable_multiton=True,
        thread_safe=True,
    )
    pattern = SingletonPatternFSA(config)

    # Clean up singletons before test
    SingletonMeta._instances.clear()
    SingletonMeta._locks.clear()
    pattern.multiton_manager.instances.clear()

    yield pattern

    # Clean up after test
    SingletonMeta._instances.clear()
    SingletonMeta._locks.clear()
    pattern.multiton_manager.instances.clear()


# ==================== Test Classes ====================

class TestSingletonPatternBasics:
    """Test basic singleton pattern functionality."""

    def test_initialization(self):
        """Test singleton pattern initialization."""
        config = SingletonConfig()
        pattern = SingletonPatternFSA(config)
        assert pattern.config == config
        assert pattern.fsa_id is not None

    def test_initialization_with_custom_config(self):
        """Test initialization with custom configuration."""
        config = SingletonConfig(
            enable_lazy=False,
            enable_eager=True,
        )
        pattern = SingletonPatternFSA(config)
        assert pattern.config.enable_lazy is False
        assert pattern.config.enable_eager is True

    def test_validation_success(self, singleton_pattern):
        """Test successful configuration validation."""
        config = SingletonConfig(max_singletons=500)
        result = singleton_pattern.validate(config)
        assert result.valid is True

    def test_validation_failure(self, singleton_pattern):
        """Test configuration validation failure."""
        config = SingletonConfig(max_singletons=-1)
        result = singleton_pattern.validate(config)
        assert result.valid is False
        assert len(result.errors) > 0


class TestSingletonCreation:
    """Test singleton creation."""

    def test_create_singleton_lazy(self, singleton_pattern):
        """Test creating a lazy singleton."""
        instance = singleton_pattern.create_singleton(TestSingleton, lazy=True)
        assert instance is not None
        assert isinstance(instance, TestSingleton)

    def test_create_singleton_eager(self, singleton_pattern):
        """Test creating an eager singleton."""
        instance = singleton_pattern.create_singleton(EagerTestSingleton, lazy=False)
        assert instance is not None
        assert isinstance(instance, EagerTestSingleton)

    def test_create_singleton_returns_same_instance(self, singleton_pattern):
        """Test that creating singleton twice returns same instance."""
        instance1 = singleton_pattern.create_singleton(TestSingleton)
        instance2 = singleton_pattern.create_singleton(TestSingleton)
        assert instance1 is instance2

    def test_create_lazy_initialization_disabled(self):
        """Test creating lazy singleton when disabled."""
        config = SingletonConfig(enable_lazy=False)
        pattern = SingletonPatternFSA(config)
        instance = pattern.create_singleton(TestSingleton, lazy=True)
        assert instance is None


class TestSingletonRetrieval:
    """Test singleton retrieval."""

    def test_get_singleton(self, singleton_pattern):
        """Test getting a singleton."""
        singleton_pattern.create_singleton(TestSingleton)
        instance = singleton_pattern.get_singleton(TestSingleton)
        assert instance is not None
        assert isinstance(instance, TestSingleton)

    def test_get_nonexistent_singleton(self, singleton_pattern):
        """Test getting non-existent singleton."""
        instance = singleton_pattern.get_singleton(TestSingleton)
        assert instance is None

    def test_get_singleton_returns_same_instance(self, singleton_pattern):
        """Test that get_singleton returns same instance."""
        created = singleton_pattern.create_singleton(TestSingleton)
        retrieved = singleton_pattern.get_singleton(TestSingleton)
        assert created is retrieved


class TestSingletonDestruction:
    """Test singleton destruction."""

    def test_destroy_singleton(self, singleton_pattern):
        """Test destroying a singleton."""
        singleton_pattern.create_singleton(TestSingleton)
        result = singleton_pattern.destroy_singleton(TestSingleton)
        assert result.destroyed is True

    def test_destroy_nonexistent_singleton(self):
        """Test destroying non-existent singleton with reset disabled."""
        config = SingletonConfig(allow_reset=False)
        pattern = SingletonPatternFSA(config)
        result = pattern.destroy_singleton(TestSingleton)
        assert result.destroyed is False
        assert result.error == "Singleton reset is disabled"

    def test_destroy_removes_instance(self, singleton_pattern):
        """Test that destroy removes instance."""
        singleton_pattern.create_singleton(TestSingleton)
        singleton_pattern.destroy_singleton(TestSingleton)
        instance = singleton_pattern.get_singleton(TestSingleton)
        assert instance is None


class TestSingletonRegistration:
    """Test singleton registration."""

    def test_register_singleton(self, singleton_pattern):
        """Test registering a singleton."""
        instance = TestSingleton("test")
        result = singleton_pattern.register_singleton("test_singleton", instance)
        assert result.registered is True
        assert result.singleton_name == "test_singleton"

    def test_register_duplicate_singleton(self, singleton_pattern):
        """Test registering duplicate singleton."""
        instance1 = TestSingleton("test1")
        singleton_pattern.register_singleton("dup_singleton", instance1)

        instance2 = TestSingleton("test2")
        result = singleton_pattern.register_singleton("dup_singleton", instance2)
        assert result.registered is False
        assert "already registered" in result.error

    def test_get_registered_singleton(self, singleton_pattern):
        """Test getting a registered singleton."""
        instance = TestSingleton("test1")
        singleton_pattern.register_singleton("my_singleton", instance)

        retrieved = singleton_pattern.get_registered_singleton("my_singleton")
        assert retrieved is instance


class TestSingletonTypeQueries:
    """Test singleton type queries."""

    def test_is_singleton_instance(self, singleton_pattern):
        """Test checking if instance is a singleton."""
        instance = singleton_pattern.create_singleton(TestSingleton)
        is_singleton = singleton_pattern.is_singleton(instance)
        assert is_singleton is True

    def test_is_not_singleton_instance(self, singleton_pattern):
        """Test checking non-singleton instance."""
        instance = RegularClass()
        is_singleton = singleton_pattern.is_singleton(instance)
        assert is_singleton is False

    def test_count_singletons(self, singleton_pattern):
        """Test counting singletons."""
        singleton_pattern.create_singleton(TestSingleton)
        singleton_pattern.create_singleton(AnotherSingleton)
        count = singleton_pattern.get_singleton_count()
        assert count == 2


class TestMultitonCreation:
    """Test multiton creation."""

    def test_create_multiton(self, singleton_pattern):
        """Test creating a multiton instance."""
        multiton = singleton_pattern.create_multiton(TestSingleton, "key1")
        assert multiton is not None
        assert multiton.key == "key1"

    def test_create_multiton_disabled(self):
        """Test creating multiton when disabled."""
        config = SingletonConfig(enable_multiton=False)
        pattern = SingletonPatternFSA(config)
        multiton = pattern.create_multiton(TestSingleton, "key1")
        assert multiton is None

    def test_create_multiton_different_keys(self, singleton_pattern):
        """Test creating multitons with different keys."""
        multiton1 = singleton_pattern.create_multiton(RegularClass, "key1")
        multiton2 = singleton_pattern.create_multiton(RegularClass, "key2")
        assert multiton1 is not None
        assert multiton2 is not None
        assert multiton1.instance is not multiton2.instance


class TestMultitonRetrieval:
    """Test multiton retrieval."""

    def test_get_multiton(self, singleton_pattern):
        """Test getting a multiton instance."""
        singleton_pattern.create_multiton(TestSingleton, "key1")
        instance = singleton_pattern.get_multiton(TestSingleton, "key1")
        assert instance is not None

    def test_get_nonexistent_multiton(self, singleton_pattern):
        """Test getting non-existent multiton."""
        instance = singleton_pattern.get_multiton(TestSingleton, "nonexistent")
        assert instance is None

    def test_get_multiton_returns_same_instance(self, singleton_pattern):
        """Test that multiton returns same instance for same key."""
        created = singleton_pattern.create_multiton(TestSingleton, "key1")
        retrieved = singleton_pattern.get_multiton(TestSingleton, "key1")
        assert created.instance is retrieved


class TestMultitonListing:
    """Test multiton listing."""

    def test_get_all_multitons(self, singleton_pattern):
        """Test getting all multiton instances."""
        singleton_pattern.create_multiton(TestSingleton, "key1")
        singleton_pattern.create_multiton(TestSingleton, "key2")
        multitons = singleton_pattern.get_all_multitons(TestSingleton)
        assert len(multitons) == 2
        assert "key1" in multitons
        assert "key2" in multitons

    def test_get_all_multitons_empty(self, singleton_pattern):
        """Test getting all multitons for class with none."""
        multitons = singleton_pattern.get_all_multitons(TestSingleton)
        assert len(multitons) == 0


class TestMultitonClearing:
    """Test multiton clearing."""

    def test_clear_multitons(self, singleton_pattern):
        """Test clearing all multitons for a class."""
        singleton_pattern.create_multiton(TestSingleton, "key1")
        singleton_pattern.create_multiton(TestSingleton, "key2")

        result = singleton_pattern.clear_multitons(TestSingleton)
        assert result.cleared is True
        assert result.count == 2

    def test_clear_multitons_empty(self, singleton_pattern):
        """Test clearing when no multitons exist."""
        result = singleton_pattern.clear_multitons(TestSingleton)
        assert result.cleared is True
        assert result.count == 0


class TestSingletonSerialization:
    """Test singleton serialization."""

    def test_serialize_singleton(self, singleton_pattern):
        """Test serializing a singleton."""
        instance = singleton_pattern.create_singleton(TestSingleton)
        instance.value = "serialized"

        data = singleton_pattern.serialize_singleton(instance)
        assert data is not None
        assert isinstance(data, bytes)

    def test_serialize_disabled(self):
        """Test serialization when disabled."""
        config = SingletonConfig(enable_serialization=False)
        pattern = SingletonPatternFSA(config)

        instance = TestSingleton()
        data = pattern.serialize_singleton(instance)
        assert data is None


class TestSingletonDeserialization:
    """Test singleton deserialization."""

    def test_deserialize_singleton(self, singleton_pattern):
        """Test deserializing a singleton."""
        # Create and serialize
        instance = TestSingleton("test_value")
        data = pickle.dumps(instance)

        # Clear and deserialize
        SingletonMeta._instances.clear()

        result = singleton_pattern.deserialize_singleton(data, TestSingleton)
        assert result.deserialized is True
        assert result.instance is not None
        assert result.instance.value == "test_value"

    def test_deserialize_prevents_bypass(self, singleton_pattern):
        """Test that deserialization prevents singleton bypass."""
        # Create singleton
        singleton_pattern.create_singleton(TestSingleton)

        # Try to deserialize when singleton exists
        data = pickle.dumps(TestSingleton("different"))
        result = singleton_pattern.deserialize_singleton(data, TestSingleton)
        assert result.deserialized is False


class TestStateValidation:
    """Test state validation."""

    def test_validate_singleton_state(self, singleton_pattern):
        """Test validating singleton state."""
        instance = singleton_pattern.create_singleton(TestSingleton)
        validation = singleton_pattern.validate_singleton_state(instance)
        assert validation.valid is True

    def test_validate_invalid_state(self, singleton_pattern):
        """Test validating invalid singleton state."""
        instance = RegularClass()
        # Don't register it - should fail validation
        validation = singleton_pattern.validate_singleton_state(instance)
        assert validation.valid is False
        assert len(validation.errors) > 0
        assert "not a registered singleton" in validation.errors[0]


class TestSingletonReset:
    """Test singleton reset."""

    def test_reset_singleton(self, singleton_pattern):
        """Test resetting a singleton."""
        instance = singleton_pattern.create_singleton(TestSingleton)
        instance.counter = 10

        result = singleton_pattern.reset_singleton(TestSingleton)
        assert result.reset is True

        # Get new instance
        new_instance = singleton_pattern.get_singleton(TestSingleton)
        assert new_instance.counter == 0

    def test_reset_nonexistent_singleton(self):
        """Test resetting singleton when reset disabled."""
        config = SingletonConfig(allow_reset=False)
        pattern = SingletonPatternFSA(config)
        result = pattern.reset_singleton(TestSingleton)
        assert result.reset is False
        assert result.error == "Singleton reset is disabled"


class TestLifecycleQueries:
    """Test lifecycle queries."""

    def test_get_singleton_lifecycle(self, singleton_pattern):
        """Test getting singleton lifecycle information."""
        singleton_pattern.create_singleton(TestSingleton)
        lifecycle = singleton_pattern.get_singleton_lifecycle(TestSingleton)
        assert lifecycle is not None
        assert lifecycle.class_name == "TestSingleton"
        assert lifecycle.created_at is not None

    def test_get_nonexistent_lifecycle(self, singleton_pattern):
        """Test getting lifecycle for non-existent singleton."""
        lifecycle = singleton_pattern.get_singleton_lifecycle(TestSingleton)
        assert lifecycle is None

    def test_lifecycle_tracks_initialization_type(self, singleton_pattern):
        """Test that lifecycle tracks initialization type."""
        singleton_pattern.create_singleton(TestSingleton, lazy=True)
        lifecycle = singleton_pattern.get_singleton_lifecycle(TestSingleton)
        assert lifecycle is not None
        from agno.fsas.singleton_pattern_fsa import InitializationType
        assert lifecycle.initialization_type == InitializationType.LAZY


class TestSingletonLocking:
    """Test singleton locking."""

    def test_lock_singleton(self, singleton_pattern):
        """Test locking a singleton."""
        singleton_pattern.create_singleton(TestSingleton)
        result = singleton_pattern.lock_singleton(TestSingleton)
        assert result.locked is True

    def test_lock_and_unlock_cycle(self, singleton_pattern):
        """Test locking and unlocking a singleton."""
        singleton_pattern.create_singleton(TestSingleton)

        # Lock the singleton
        lock_result = singleton_pattern.lock_singleton(TestSingleton)
        assert lock_result.locked is True

        # Verify it's in singleton_locks
        assert TestSingleton in singleton_pattern.singleton_locks

        # Unlock it
        unlock_result = singleton_pattern.unlock_singleton(TestSingleton)
        assert unlock_result.unlocked is True


class TestSingletonUnlocking:
    """Test singleton unlocking."""

    def test_unlock_singleton(self, singleton_pattern):
        """Test unlocking a singleton."""
        singleton_pattern.create_singleton(TestSingleton)
        singleton_pattern.lock_singleton(TestSingleton)

        result = singleton_pattern.unlock_singleton(TestSingleton)
        assert result.unlocked is True

    def test_unlock_nonexistent_singleton(self, singleton_pattern):
        """Test unlocking non-existent singleton."""
        result = singleton_pattern.unlock_singleton(TestSingleton)
        assert result.unlocked is False
        assert result.error == "Singleton not found"


class TestSingletonMetrics:
    """Test singleton metrics."""

    def test_get_singleton_metrics(self, singleton_pattern):
        """Test getting singleton metrics."""
        instance = singleton_pattern.create_singleton(TestSingleton)

        metrics = singleton_pattern.get_singleton_metrics(TestSingleton)
        assert metrics is not None
        assert metrics.access_count >= 0

    def test_metrics_track_access(self, singleton_pattern):
        """Test that metrics track access."""
        singleton_pattern.create_singleton(TestSingleton)

        # Access multiple times
        singleton_pattern.get_singleton(TestSingleton)
        singleton_pattern.get_singleton(TestSingleton)

        metrics = singleton_pattern.get_singleton_metrics(TestSingleton)
        assert metrics.access_count >= 2


class TestClonePrevention:
    """Test clone prevention."""

    def test_singleton_copy_prevented(self, singleton_pattern):
        """Test that singleton cannot be copied."""
        import copy

        instance = singleton_pattern.create_singleton(TestSingleton)

        with pytest.raises(TypeError):
            copy.copy(instance)

    def test_singleton_deepcopy_prevented(self, singleton_pattern):
        """Test that singleton cannot be deep copied."""
        import copy

        instance = singleton_pattern.create_singleton(TestSingleton)

        with pytest.raises(TypeError):
            copy.deepcopy(instance)


class TestThreadSafety:
    """Test thread safety."""

    def test_thread_safe_pattern(self):
        """Test thread-safe pattern creation."""
        config = SingletonConfig(thread_safe=True)
        pattern = SingletonPatternFSA(config)
        assert pattern._lock is not None

    def test_non_thread_safe_pattern(self):
        """Test non-thread-safe pattern."""
        config = SingletonConfig(thread_safe=False)
        pattern = SingletonPatternFSA(config)
        assert pattern._lock is None

    def test_concurrent_singleton_creation(self, singleton_pattern):
        """Test concurrent singleton creation returns same instance."""
        instances = []

        def create_singleton():
            instance = singleton_pattern.create_singleton(TestSingleton)
            instances.append(instance)

        threads = [threading.Thread(target=create_singleton) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # All instances should be the same
        assert all(inst is instances[0] for inst in instances)


class TestExecuteMethod:
    """Test execute method."""

    def test_execute_operations(self, singleton_pattern):
        """Test executing singleton pattern operations."""
        ops = [
            SingletonOp(operation="create", class_type=TestSingleton, lazy=True),
        ]

        result = singleton_pattern.execute(ops)
        assert isinstance(result, SingletonResult)
        assert result.success is True

    def test_execute_multiple_ops(self, singleton_pattern):
        """Test executing multiple operations."""
        ops = [
            SingletonOp(operation="create", class_type=TestSingleton),
            SingletonOp(operation="get", class_type=TestSingleton),
        ]

        result = singleton_pattern.execute(ops)
        assert result.success is True


class TestEdgeCases:
    """Test edge cases and error scenarios."""

    def test_max_singletons_limit(self):
        """Test max singletons limit."""
        config = SingletonConfig(max_singletons=1)
        pattern = SingletonPatternFSA(config)

        pattern.create_singleton(TestSingleton)
        instance = pattern.create_singleton(AnotherSingleton)
        assert instance is None

    def test_serialization_disabled(self):
        """Test operations when serialization is disabled."""
        config = SingletonConfig(enable_serialization=False)
        pattern = SingletonPatternFSA(config)

        instance = TestSingleton()
        data = pattern.serialize_singleton(instance)
        assert data is None

    def test_metrics_disabled(self):
        """Test metrics when disabled."""
        config = SingletonConfig(enable_metrics=False)
        pattern = SingletonPatternFSA(config)

        pattern.create_singleton(TestSingleton)
        metrics = pattern.get_singleton_metrics(TestSingleton)
        assert metrics is None


class TestComplexScenarios:
    """Test complex scenarios."""

    def test_multiton_with_different_classes(self, singleton_pattern):
        """Test multiton pattern with different classes."""
        multiton1 = singleton_pattern.create_multiton(TestSingleton, "key1")
        multiton2 = singleton_pattern.create_multiton(AnotherSingleton, "key1")

        assert multiton1 is not None
        assert multiton2 is not None
        assert type(multiton1.instance) != type(multiton2.instance)

    def test_lazy_and_eager_initialization(self, singleton_pattern):
        """Test both lazy and eager initialization."""
        lazy = singleton_pattern.create_singleton(LazyTestSingleton, lazy=True)
        eager = singleton_pattern.create_singleton(EagerTestSingleton, lazy=False)

        assert lazy is not None
        assert eager is not None

    def test_serialization_roundtrip(self, singleton_pattern):
        """Test complete serialization roundtrip."""
        # Create and modify singleton
        instance = singleton_pattern.create_singleton(TestSingleton)
        instance.value = "roundtrip_test"
        instance.counter = 42

        # Serialize
        data = singleton_pattern.serialize_singleton(instance)

        # Clear singletons
        singleton_pattern.destroy_singleton(TestSingleton)

        # Deserialize
        result = singleton_pattern.deserialize_singleton(data, TestSingleton)

        # Verify
        assert result.deserialized is True
        assert result.instance.value == "roundtrip_test"
        assert result.instance.counter == 42
