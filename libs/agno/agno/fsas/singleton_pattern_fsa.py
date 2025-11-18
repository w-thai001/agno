"""Singleton Pattern FSA for agno.

This module provides a comprehensive singleton pattern implementation with support for:
- Thread-safe singleton creation with double-checked locking
- Lazy initialization (on-demand creation)
- Eager initialization (at import time)
- Multiton pattern (keyed singletons)
- Singleton registry for global tracking
- Lifecycle management
- Serialization/deserialization support
- State validation and integrity checking
- Thread-safe operations
"""

import logging
import pickle
import threading
import time
from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type
from uuid import uuid4

logger = logging.getLogger(__name__)


# ==================== Enums ====================

class SingletonState(Enum):
    """Singleton state."""
    NOT_CREATED = "not_created"
    CREATING = "creating"
    CREATED = "created"
    DESTROYED = "destroyed"


class InitializationType(Enum):
    """Initialization type."""
    LAZY = "lazy"
    EAGER = "eager"
    MANUAL = "manual"


# ==================== Singleton Metaclass ====================

class SingletonMeta(type):
    """
    Metaclass for implementing singleton pattern.

    Uses thread-safe double-checked locking.
    """

    _instances: Dict[Type, Any] = {}
    _locks: Dict[Type, threading.Lock] = {}
    _master_lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        """Create or return singleton instance."""
        # Double-checked locking pattern
        if cls not in cls._instances:
            with cls._master_lock:
                # Get or create lock for this class
                if cls not in cls._locks:
                    cls._locks[cls] = threading.Lock()

            with cls._locks[cls]:
                if cls not in cls._instances:
                    instance = super().__call__(*args, **kwargs)
                    cls._instances[cls] = instance

        return cls._instances[cls]

    @classmethod
    def reset(mcs, cls: Type):
        """Reset singleton instance."""
        with mcs._master_lock:
            if cls in mcs._instances:
                del mcs._instances[cls]
            if cls in mcs._locks:
                del mcs._locks[cls]

    @classmethod
    def get_instance(mcs, cls: Type) -> Optional[Any]:
        """Get singleton instance if exists."""
        return mcs._instances.get(cls)


# ==================== Data Classes ====================

@dataclass
class SingletonOp:
    """Singleton operation."""
    operation: str = ""
    class_type: Optional[Type] = None
    name: Optional[str] = None
    instance: Optional[Any] = None
    key: Optional[str] = None
    lazy: bool = True
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SingletonResult:
    """Singleton pattern pipeline result."""
    success: bool
    operations_count: int = 0
    singletons_created: int = 0
    errors: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    results: List[Any] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Configuration validation result."""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class DestroyResult:
    """Singleton destruction result."""
    destroyed: bool
    class_name: str = ""
    error: Optional[str] = None


@dataclass
class RegisterResult:
    """Singleton registration result."""
    registered: bool
    singleton_name: str = ""
    error: Optional[str] = None


@dataclass
class MultitonInstance:
    """Multiton instance wrapper."""
    instance_id: str = field(default_factory=lambda: str(uuid4()))
    key: str = ""
    instance: Any = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ClearResult:
    """Multiton clear result."""
    cleared: bool
    count: int = 0
    error: Optional[str] = None


@dataclass
class DeserializationResult:
    """Deserialization result."""
    deserialized: bool
    instance: Optional[Any] = None
    error: Optional[str] = None


@dataclass
class StateValidation:
    """Singleton state validation result."""
    valid: bool
    instance_id: str = ""
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class ResetResult:
    """Singleton reset result."""
    reset: bool
    class_name: str = ""
    error: Optional[str] = None


@dataclass
class CloneResult:
    """State clone result."""
    cloned: bool
    source_id: str = ""
    target_id: str = ""
    error: Optional[str] = None


@dataclass
class LifecycleInfo:
    """Singleton lifecycle information."""
    class_name: str = ""
    state: SingletonState = SingletonState.NOT_CREATED
    initialization_type: InitializationType = InitializationType.MANUAL
    created_at: Optional[datetime] = None
    access_count: int = 0


@dataclass
class LockResult:
    """Singleton lock result."""
    locked: bool
    class_name: str = ""
    error: Optional[str] = None


@dataclass
class UnlockResult:
    """Singleton unlock result."""
    unlocked: bool
    class_name: str = ""
    error: Optional[str] = None


@dataclass
class SingletonMetrics:
    """Singleton metrics."""
    class_name: str = ""
    instance_count: int = 0
    access_count: int = 0
    creation_time: Optional[datetime] = None
    last_access: Optional[datetime] = None
    memory_size: int = 0


@dataclass
class SingletonConfig:
    """Singleton pattern configuration."""
    enable_lazy: bool = True
    enable_eager: bool = True
    enable_multiton: bool = True
    enable_serialization: bool = True
    enable_metrics: bool = True
    thread_safe: bool = True
    max_singletons: int = 1000
    max_multiton_instances: int = 100
    allow_reset: bool = True
    prevent_cloning: bool = True
    prevent_serialization_bypass: bool = True


# ==================== Singleton Classes ====================

class BaseSingleton:
    """Base singleton class with common functionality."""

    def __init__(self):
        self.singleton_id = str(uuid4())
        self.created_at = datetime.now()
        self.access_count = 0
        self.last_access: Optional[datetime] = None
        self._locked = False

    def __copy__(self):
        """Prevent copying."""
        raise TypeError("Singleton cannot be copied")

    def __deepcopy__(self, memo):
        """Prevent deep copying."""
        raise TypeError("Singleton cannot be deep copied")

    def _access(self):
        """Track access to singleton."""
        self.access_count += 1
        self.last_access = datetime.now()


class EagerSingleton(BaseSingleton, metaclass=SingletonMeta):
    """Eagerly initialized singleton."""

    _initialized = False

    def __init__(self):
        if not self._initialized:
            super().__init__()
            self.__class__._initialized = True
            self.initialization_type = InitializationType.EAGER
            logger.info(f"Eager singleton created: {self.__class__.__name__}")


class LazySingleton(BaseSingleton, metaclass=SingletonMeta):
    """Lazily initialized singleton."""

    _initialized = False

    def __init__(self):
        if not self._initialized:
            super().__init__()
            self.__class__._initialized = True
            self.initialization_type = InitializationType.LAZY
            logger.info(f"Lazy singleton created: {self.__class__.__name__}")


class ConfigurationSingleton(BaseSingleton, metaclass=SingletonMeta):
    """Configuration singleton example."""

    _initialized = False

    def __init__(self):
        if not self._initialized:
            super().__init__()
            self.__class__._initialized = True
            self.config: Dict[str, Any] = {}
            logger.info("Configuration singleton created")

    def set_config(self, key: str, value: Any):
        """Set configuration value."""
        self._access()
        self.config[key] = value

    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        self._access()
        return self.config.get(key, default)


class DatabaseConnectionSingleton(BaseSingleton, metaclass=SingletonMeta):
    """Database connection singleton example."""

    _initialized = False

    def __init__(self):
        if not self._initialized:
            super().__init__()
            self.__class__._initialized = True
            self.connection_string = ""
            self.is_connected = False
            logger.info("Database connection singleton created")

    def connect(self, connection_string: str):
        """Connect to database."""
        self._access()
        self.connection_string = connection_string
        self.is_connected = True

    def disconnect(self):
        """Disconnect from database."""
        self._access()
        self.is_connected = False


# ==================== Multiton Manager ====================

class MultitonManager:
    """Manager for multiton pattern (keyed singletons)."""

    def __init__(self):
        self.instances: Dict[Type, Dict[str, Any]] = defaultdict(dict)
        self._locks: Dict[Type, threading.Lock] = {}
        self._master_lock = threading.Lock()

    def get_instance(
        self,
        class_type: Type,
        key: str,
        *args,
        **kwargs,
    ) -> Any:
        """Get or create multiton instance."""
        # Ensure lock exists
        if class_type not in self._locks:
            with self._master_lock:
                if class_type not in self._locks:
                    self._locks[class_type] = threading.Lock()

        # Double-checked locking
        if key not in self.instances[class_type]:
            with self._locks[class_type]:
                if key not in self.instances[class_type]:
                    instance = class_type(*args, **kwargs)
                    if hasattr(instance, 'singleton_id'):
                        instance.multiton_key = key
                    self.instances[class_type][key] = instance

        return self.instances[class_type][key]

    def get_all_instances(self, class_type: Type) -> Dict[str, Any]:
        """Get all instances for a type."""
        return self.instances.get(class_type, {}).copy()

    def clear_instances(self, class_type: Type) -> int:
        """Clear all instances for a type."""
        count = len(self.instances.get(class_type, {}))
        if class_type in self.instances:
            self.instances[class_type].clear()
        return count

    def has_instance(self, class_type: Type, key: str) -> bool:
        """Check if instance exists."""
        return key in self.instances.get(class_type, {})


# ==================== Singleton Factory ====================

class SingletonFactory:
    """Factory for creating singletons."""

    def __init__(self, class_type: Type):
        self.class_type = class_type
        self.factory_id = str(uuid4())
        self.instances_created = 0

    def create_instance(self, *args, **kwargs) -> Any:
        """Create singleton instance."""
        instance = self.class_type(*args, **kwargs)
        self.instances_created += 1
        return instance

    def get_instance(self) -> Optional[Any]:
        """Get existing singleton instance."""
        return SingletonMeta.get_instance(self.class_type)


# ==================== Main FSA Class ====================

class SingletonPatternFSA:
    """
    Singleton Pattern FSA implementation.

    Provides singleton pattern functionality with thread-safe creation,
    multiton support, and lifecycle management.
    """

    def __init__(self, config: SingletonConfig):
        """
        Initialize Singleton Pattern FSA.

        Args:
            config: Singleton pattern configuration
        """
        self.config = config
        self.fsa_id = str(uuid4())

        # Singleton registry
        self.registry: Dict[str, Any] = {}
        self.lifecycle_info: Dict[Type, LifecycleInfo] = {}

        # Multiton manager
        self.multiton_manager = MultitonManager()

        # Metrics
        self.access_counts: Dict[Type, int] = defaultdict(int)
        self.creation_times: Dict[Type, datetime] = {}

        # Locks
        self.singleton_locks: Dict[Type, threading.Lock] = {}

        # Thread safety
        self._lock = threading.RLock() if config.thread_safe else None

        logger.info(f"Initialized SingletonPatternFSA: {self.fsa_id}")

    def _acquire_lock(self):
        """Acquire lock for thread-safe operations."""
        if self._lock:
            self._lock.acquire()

    def _release_lock(self):
        """Release lock after thread-safe operations."""
        if self._lock:
            self._lock.release()

    def validate(self, config: SingletonConfig) -> ValidationResult:
        """
        Validate singleton pattern configuration.

        Args:
            config: Configuration to validate

        Returns:
            ValidationResult with validation status
        """
        errors = []
        warnings = []

        if config.max_singletons < 1:
            errors.append("max_singletons must be positive")

        if config.max_multiton_instances < 1:
            errors.append("max_multiton_instances must be positive")

        if not config.thread_safe:
            warnings.append("Thread safety is disabled - not recommended")

        if not config.prevent_cloning:
            warnings.append("Clone prevention is disabled - may allow multiple instances")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def create_singleton(
        self,
        class_type: Type,
        lazy: bool = True,
        *args,
        **kwargs,
    ) -> Optional[Any]:
        """
        Create a singleton instance.

        Args:
            class_type: Class to create singleton for
            lazy: Use lazy initialization
            *args: Constructor arguments
            **kwargs: Constructor keyword arguments

        Returns:
            Singleton instance or None
        """
        try:
            self._acquire_lock()

            # Check if already exists
            existing = SingletonMeta.get_instance(class_type)
            if existing:
                logger.info(f"Singleton already exists: {class_type.__name__}")
                return existing

            # Check limits
            singleton_count = len(SingletonMeta._instances)
            if singleton_count >= self.config.max_singletons:
                logger.error("Maximum singletons reached")
                return None

            # Create instance
            if lazy and not self.config.enable_lazy:
                logger.error("Lazy initialization is disabled")
                return None

            if not lazy and not self.config.enable_eager:
                logger.error("Eager initialization is disabled")
                return None

            instance = class_type(*args, **kwargs)

            # Track lifecycle
            init_type = InitializationType.LAZY if lazy else InitializationType.EAGER
            self.lifecycle_info[class_type] = LifecycleInfo(
                class_name=class_type.__name__,
                state=SingletonState.CREATED,
                initialization_type=init_type,
                created_at=datetime.now(),
            )

            self.creation_times[class_type] = datetime.now()

            logger.info(f"Created singleton: {class_type.__name__}")

            return instance

        finally:
            self._release_lock()

    def get_singleton(self, class_type: Type) -> Optional[Any]:
        """
        Get singleton instance.

        Args:
            class_type: Class to get singleton for

        Returns:
            Singleton instance or None
        """
        try:
            self._acquire_lock()

            instance = SingletonMeta.get_instance(class_type)

            if instance:
                # Track access
                self.access_counts[class_type] += 1
                if class_type in self.lifecycle_info:
                    self.lifecycle_info[class_type].access_count += 1

                if hasattr(instance, '_access'):
                    instance._access()

            return instance

        finally:
            self._release_lock()

    def destroy_singleton(self, class_type: Type) -> DestroyResult:
        """
        Destroy a singleton instance.

        Args:
            class_type: Class to destroy singleton for

        Returns:
            DestroyResult with destruction status
        """
        try:
            self._acquire_lock()

            if not self.config.allow_reset:
                return DestroyResult(
                    destroyed=False,
                    class_name=class_type.__name__,
                    error="Singleton reset is disabled",
                )

            # Reset via metaclass
            SingletonMeta.reset(class_type)

            # Update lifecycle
            if class_type in self.lifecycle_info:
                self.lifecycle_info[class_type].state = SingletonState.DESTROYED

            logger.info(f"Destroyed singleton: {class_type.__name__}")

            return DestroyResult(
                destroyed=True,
                class_name=class_type.__name__,
            )

        except Exception as e:
            return DestroyResult(
                destroyed=False,
                class_name=class_type.__name__,
                error=str(e),
            )

        finally:
            self._release_lock()

    def register_singleton(self, name: str, instance: Any) -> RegisterResult:
        """
        Register a singleton in the registry.

        Args:
            name: Name for singleton
            instance: Singleton instance

        Returns:
            RegisterResult with registration status
        """
        try:
            self._acquire_lock()

            if name in self.registry:
                return RegisterResult(
                    registered=False,
                    singleton_name=name,
                    error="Singleton already registered with this name",
                )

            self.registry[name] = instance
            logger.info(f"Registered singleton: {name}")

            return RegisterResult(
                registered=True,
                singleton_name=name,
            )

        except Exception as e:
            return RegisterResult(
                registered=False,
                singleton_name=name,
                error=str(e),
            )

        finally:
            self._release_lock()

    def get_registered_singleton(self, name: str) -> Optional[Any]:
        """
        Get a registered singleton.

        Args:
            name: Singleton name

        Returns:
            Singleton instance or None
        """
        try:
            self._acquire_lock()

            return self.registry.get(name)

        finally:
            self._release_lock()

    def create_lazy_singleton(self, class_type: Type) -> Optional[Any]:
        """
        Create a lazy singleton.

        Args:
            class_type: Class to create singleton for

        Returns:
            Singleton instance or None
        """
        return self.create_singleton(class_type, lazy=True)

    def create_eager_singleton(self, class_type: Type) -> Optional[Any]:
        """
        Create an eager singleton.

        Args:
            class_type: Class to create singleton for

        Returns:
            Singleton instance or None
        """
        return self.create_singleton(class_type, lazy=False)

    def is_singleton(self, instance: Any) -> bool:
        """
        Check if an instance is a singleton.

        Args:
            instance: Instance to check

        Returns:
            True if instance is a singleton
        """
        class_type = type(instance)
        existing = SingletonMeta.get_instance(class_type)
        return existing is instance

    def get_singleton_count(self) -> int:
        """
        Get count of active singletons.

        Returns:
            Number of singletons
        """
        return len(SingletonMeta._instances)

    def create_multiton(
        self,
        class_type: Type,
        key: str,
        *args,
        **kwargs,
    ) -> Optional[MultitonInstance]:
        """
        Create a multiton instance.

        Args:
            class_type: Class to create instance for
            key: Instance key
            *args: Constructor arguments
            **kwargs: Constructor keyword arguments

        Returns:
            MultitonInstance or None
        """
        try:
            self._acquire_lock()

            if not self.config.enable_multiton:
                logger.error("Multiton is disabled")
                return None

            # Check limits
            existing_count = len(self.multiton_manager.instances.get(class_type, {}))
            if existing_count >= self.config.max_multiton_instances:
                logger.error("Maximum multiton instances reached")
                return None

            instance = self.multiton_manager.get_instance(
                class_type,
                key,
                *args,
                **kwargs,
            )

            multiton = MultitonInstance(
                key=key,
                instance=instance,
            )

            logger.info(f"Created multiton: {class_type.__name__}[{key}]")

            return multiton

        finally:
            self._release_lock()

    def get_multiton(self, class_type: Type, key: str) -> Optional[Any]:
        """
        Get a multiton instance.

        Args:
            class_type: Class type
            key: Instance key

        Returns:
            Multiton instance or None
        """
        try:
            self._acquire_lock()

            instances = self.multiton_manager.instances.get(class_type, {})
            return instances.get(key)

        finally:
            self._release_lock()

    def get_all_multitons(self, class_type: Type) -> Dict[str, Any]:
        """
        Get all multiton instances for a type.

        Args:
            class_type: Class type

        Returns:
            Dictionary of key to instance
        """
        try:
            self._acquire_lock()

            return self.multiton_manager.get_all_instances(class_type)

        finally:
            self._release_lock()

    def clear_multitons(self, class_type: Type) -> ClearResult:
        """
        Clear all multiton instances for a type.

        Args:
            class_type: Class type

        Returns:
            ClearResult with clear status
        """
        try:
            self._acquire_lock()

            count = self.multiton_manager.clear_instances(class_type)

            logger.info(f"Cleared {count} multiton instances for {class_type.__name__}")

            return ClearResult(
                cleared=True,
                count=count,
            )

        except Exception as e:
            return ClearResult(
                cleared=False,
                error=str(e),
            )

        finally:
            self._release_lock()

    def serialize_singleton(self, instance: Any) -> Optional[bytes]:
        """
        Serialize a singleton.

        Args:
            instance: Singleton to serialize

        Returns:
            Serialized bytes or None
        """
        try:
            if not self.config.enable_serialization:
                logger.error("Serialization is disabled")
                return None

            return pickle.dumps(instance)

        except Exception as e:
            logger.error(f"Error serializing singleton: {str(e)}")
            return None

    def deserialize_singleton(
        self,
        data: bytes,
        class_type: Type,
    ) -> DeserializationResult:
        """
        Deserialize a singleton.

        Args:
            data: Serialized data
            class_type: Expected class type

        Returns:
            DeserializationResult with deserialization status
        """
        try:
            if not self.config.enable_serialization:
                return DeserializationResult(
                    deserialized=False,
                    error="Serialization is disabled",
                )

            if self.config.prevent_serialization_bypass:
                # Check if singleton already exists
                existing = SingletonMeta.get_instance(class_type)
                if existing:
                    return DeserializationResult(
                        deserialized=False,
                        error="Singleton already exists - cannot deserialize",
                    )

            instance = pickle.loads(data)

            if not isinstance(instance, class_type):
                return DeserializationResult(
                    deserialized=False,
                    error="Deserialized instance has wrong type",
                )

            return DeserializationResult(
                deserialized=True,
                instance=instance,
            )

        except Exception as e:
            return DeserializationResult(
                deserialized=False,
                error=str(e),
            )

    def validate_singleton_state(self, instance: Any) -> StateValidation:
        """
        Validate singleton state.

        Args:
            instance: Singleton instance

        Returns:
            StateValidation with validation status
        """
        errors = []
        warnings = []

        instance_id = getattr(instance, 'singleton_id', 'unknown')

        # Check if instance is actually a singleton
        if not self.is_singleton(instance):
            errors.append("Instance is not a registered singleton")

        # Check if locked
        if hasattr(instance, '_locked') and instance._locked:
            warnings.append("Singleton is locked")

        # Check initialization
        class_type = type(instance)
        if hasattr(class_type, '_initialized') and not class_type._initialized:
            errors.append("Singleton not properly initialized")

        return StateValidation(
            valid=len(errors) == 0,
            instance_id=instance_id,
            errors=errors,
            warnings=warnings,
        )

    def reset_singleton(self, class_type: Type) -> ResetResult:
        """
        Reset a singleton (destroy and recreate).

        Args:
            class_type: Class to reset

        Returns:
            ResetResult with reset status
        """
        try:
            self._acquire_lock()

            if not self.config.allow_reset:
                return ResetResult(
                    reset=False,
                    class_name=class_type.__name__,
                    error="Singleton reset is disabled",
                )

            # Destroy existing
            self.destroy_singleton(class_type)

            # Create new
            instance = self.create_singleton(class_type)

            if instance:
                logger.info(f"Reset singleton: {class_type.__name__}")
                return ResetResult(
                    reset=True,
                    class_name=class_type.__name__,
                )
            else:
                return ResetResult(
                    reset=False,
                    class_name=class_type.__name__,
                    error="Failed to recreate singleton",
                )

        except Exception as e:
            return ResetResult(
                reset=False,
                class_name=class_type.__name__,
                error=str(e),
            )

        finally:
            self._release_lock()

    def clone_singleton_state(
        self,
        source: Any,
        target: Any,
    ) -> CloneResult:
        """
        Clone singleton state.

        Args:
            source: Source singleton
            target: Target singleton

        Returns:
            CloneResult with clone status
        """
        try:
            self._acquire_lock()

            if self.config.prevent_cloning:
                return CloneResult(
                    cloned=False,
                    source_id=getattr(source, 'singleton_id', 'unknown'),
                    target_id=getattr(target, 'singleton_id', 'unknown'),
                    error="Cloning prevention is enabled",
                )

            source_id = getattr(source, 'singleton_id', 'unknown')
            target_id = getattr(target, 'singleton_id', 'unknown')

            # Copy attributes (excluding protected ones)
            for attr, value in source.__dict__.items():
                if not attr.startswith('_'):
                    setattr(target, attr, deepcopy(value))

            logger.info(f"Cloned singleton state: {source_id} -> {target_id}")

            return CloneResult(
                cloned=True,
                source_id=source_id,
                target_id=target_id,
            )

        except Exception as e:
            return CloneResult(
                cloned=False,
                source_id=getattr(source, 'singleton_id', 'unknown'),
                target_id=getattr(target, 'singleton_id', 'unknown'),
                error=str(e),
            )

        finally:
            self._release_lock()

    def get_singleton_lifecycle(self, class_type: Type) -> Optional[LifecycleInfo]:
        """
        Get singleton lifecycle information.

        Args:
            class_type: Class to query

        Returns:
            LifecycleInfo or None
        """
        try:
            self._acquire_lock()

            return self.lifecycle_info.get(class_type)

        finally:
            self._release_lock()

    def lock_singleton(self, class_type: Type) -> LockResult:
        """
        Lock a singleton.

        Args:
            class_type: Class to lock

        Returns:
            LockResult with lock status
        """
        try:
            self._acquire_lock()

            instance = SingletonMeta.get_instance(class_type)

            if not instance:
                return LockResult(
                    locked=False,
                    class_name=class_type.__name__,
                    error="Singleton not found",
                )

            if hasattr(instance, '_locked'):
                instance._locked = True

            # Create thread lock
            if class_type not in self.singleton_locks:
                self.singleton_locks[class_type] = threading.Lock()

            self.singleton_locks[class_type].acquire()

            logger.info(f"Locked singleton: {class_type.__name__}")

            return LockResult(
                locked=True,
                class_name=class_type.__name__,
            )

        except Exception as e:
            return LockResult(
                locked=False,
                class_name=class_type.__name__,
                error=str(e),
            )

        finally:
            self._release_lock()

    def unlock_singleton(self, class_type: Type) -> UnlockResult:
        """
        Unlock a singleton.

        Args:
            class_type: Class to unlock

        Returns:
            UnlockResult with unlock status
        """
        try:
            self._acquire_lock()

            instance = SingletonMeta.get_instance(class_type)

            if not instance:
                return UnlockResult(
                    unlocked=False,
                    class_name=class_type.__name__,
                    error="Singleton not found",
                )

            if hasattr(instance, '_locked'):
                instance._locked = False

            # Release thread lock
            if class_type in self.singleton_locks:
                self.singleton_locks[class_type].release()

            logger.info(f"Unlocked singleton: {class_type.__name__}")

            return UnlockResult(
                unlocked=True,
                class_name=class_type.__name__,
            )

        except Exception as e:
            return UnlockResult(
                unlocked=False,
                class_name=class_type.__name__,
                error=str(e),
            )

        finally:
            self._release_lock()

    def get_singleton_metrics(self, class_type: Type) -> Optional[SingletonMetrics]:
        """
        Get singleton metrics.

        Args:
            class_type: Class to query

        Returns:
            SingletonMetrics or None
        """
        try:
            self._acquire_lock()

            if not self.config.enable_metrics:
                return None

            instance = SingletonMeta.get_instance(class_type)

            if not instance:
                return None

            access_count = self.access_counts.get(class_type, 0)
            creation_time = self.creation_times.get(class_type)

            last_access = None
            if hasattr(instance, 'last_access'):
                last_access = instance.last_access

            # Calculate memory size (approximate)
            memory_size = 0
            try:
                import sys
                memory_size = sys.getsizeof(instance)
            except:
                pass

            return SingletonMetrics(
                class_name=class_type.__name__,
                instance_count=1,
                access_count=access_count,
                creation_time=creation_time,
                last_access=last_access,
                memory_size=memory_size,
            )

        finally:
            self._release_lock()

    def create_singleton_factory(self, class_type: Type) -> SingletonFactory:
        """
        Create a singleton factory.

        Args:
            class_type: Class to create factory for

        Returns:
            SingletonFactory instance
        """
        return SingletonFactory(class_type)

    def execute(self, ops: List[SingletonOp]) -> SingletonResult:
        """
        Execute singleton pattern pipeline.

        Args:
            ops: List of singleton operations

        Returns:
            SingletonResult with pipeline result
        """
        try:
            start_time = time.time()
            singletons_created = 0
            errors = []
            results = []

            for op in ops:
                if op.operation == "create":
                    if op.class_type:
                        instance = self.create_singleton(op.class_type, op.lazy)
                        if instance:
                            singletons_created += 1
                            results.append(instance)
                        else:
                            errors.append("Failed to create singleton")

                elif op.operation == "get":
                    if op.class_type:
                        instance = self.get_singleton(op.class_type)
                        results.append(instance)

                elif op.operation == "register":
                    if op.name and op.instance:
                        result = self.register_singleton(op.name, op.instance)
                        results.append(result)

                elif op.operation == "multiton":
                    if op.class_type and op.key:
                        result = self.create_multiton(op.class_type, op.key)
                        results.append(result)

            execution_time = time.time() - start_time

            return SingletonResult(
                success=len(errors) == 0,
                operations_count=len(ops),
                singletons_created=singletons_created,
                errors=errors,
                execution_time=execution_time,
                results=results,
            )

        except Exception as e:
            return SingletonResult(
                success=False,
                errors=[str(e)],
            )
