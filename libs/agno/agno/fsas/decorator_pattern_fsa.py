"""Decorator Pattern FSA for agno.

This module provides a comprehensive decorator pattern implementation with support for:
- Component decoration and behavior enhancement
- Dynamic feature addition without subclassing
- Decorator stacking with multiple layers
- Decoration validation and verification
- Decorator composition and chaining
- Thread-safe decoration operations
- Async decorator support
"""

import asyncio
import logging
import threading
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Type
from uuid import uuid4

logger = logging.getLogger(__name__)


# ==================== Enums ====================

class DecoratorState(Enum):
    """Decorator state."""
    UNDECORATED = "undecorated"
    DECORATING = "decorating"
    DECORATED = "decorated"
    UNWRAPPED = "unwrapped"


class DecoratorType(Enum):
    """Decorator type."""
    LOGGING = "logging"
    CACHING = "caching"
    VALIDATION = "validation"
    TIMING = "timing"
    RETRY = "retry"
    AUTHORIZATION = "authorization"
    COMPRESSION = "compression"
    ENCRYPTION = "encryption"
    CUSTOM = "custom"


# ==================== Component Interface ====================

class Component(ABC):
    """Base component interface."""

    def __init__(self):
        """Initialize component."""
        self.component_id = str(uuid4())
        self.created_at = datetime.now()
        self.state = DecoratorState.UNDECORATED

    @abstractmethod
    def operation(self) -> Any:
        """Execute component operation."""
        pass

    @abstractmethod
    def get_description(self) -> str:
        """Get component description."""
        pass


# ==================== Concrete Components ====================

class ConcreteComponent(Component):
    """Concrete component implementation."""

    def __init__(self, value: Any = None):
        """Initialize concrete component."""
        super().__init__()
        self.value = value
        self.operation_count = 0

    def operation(self) -> Any:
        """Execute operation."""
        self.operation_count += 1
        logger.debug(f"ConcreteComponent operation: {self.value}")
        return self.value

    def get_description(self) -> str:
        """Get description."""
        return f"ConcreteComponent(value={self.value})"


class DataComponent(Component):
    """Data component for data processing."""

    def __init__(self, data: Dict[str, Any]):
        """Initialize data component."""
        super().__init__()
        self.data = data
        self.access_count = 0

    def operation(self) -> Any:
        """Execute data operation."""
        self.access_count += 1
        return self.data

    def get_description(self) -> str:
        """Get description."""
        return f"DataComponent(keys={list(self.data.keys())})"


class ServiceComponent(Component):
    """Service component for service operations."""

    def __init__(self, service_name: str):
        """Initialize service component."""
        super().__init__()
        self.service_name = service_name
        self.request_count = 0

    def operation(self) -> Any:
        """Execute service operation."""
        self.request_count += 1
        return f"Service {self.service_name} executed"

    def get_description(self) -> str:
        """Get description."""
        return f"ServiceComponent(name={self.service_name})"


# ==================== Abstract Decorator ====================

class Decorator(Component):
    """Abstract decorator base class."""

    def __init__(self, component: Component):
        """Initialize decorator."""
        super().__init__()
        self._component = component
        self.decorator_type = DecoratorType.CUSTOM
        self.state = DecoratorState.DECORATED

    def operation(self) -> Any:
        """Execute decorated operation."""
        return self._component.operation()

    def get_description(self) -> str:
        """Get description."""
        return f"{self.__class__.__name__}({self._component.get_description()})"

    def get_component(self) -> Component:
        """Get wrapped component."""
        return self._component


# ==================== Concrete Decorators ====================

class LoggingDecorator(Decorator):
    """Logging decorator."""

    def __init__(self, component: Component):
        """Initialize logging decorator."""
        super().__init__(component)
        self.decorator_type = DecoratorType.LOGGING
        self.log_entries = []

    def operation(self) -> Any:
        """Execute with logging."""
        self.log_entries.append({
            'timestamp': datetime.now(),
            'action': 'operation_start',
        })
        logger.info(f"Logging: Operation starting on {self._component.get_description()}")

        result = self._component.operation()

        self.log_entries.append({
            'timestamp': datetime.now(),
            'action': 'operation_complete',
            'result': result,
        })
        logger.info(f"Logging: Operation completed with result: {result}")

        return result


class CachingDecorator(Decorator):
    """Caching decorator."""

    def __init__(self, component: Component):
        """Initialize caching decorator."""
        super().__init__(component)
        self.decorator_type = DecoratorType.CACHING
        self.cache: Dict[str, Any] = {}
        self.hits = 0
        self.misses = 0

    def operation(self) -> Any:
        """Execute with caching."""
        cache_key = "operation_result"

        if cache_key in self.cache:
            self.hits += 1
            logger.debug(f"Cache hit: {cache_key}")
            return self.cache[cache_key]

        self.misses += 1
        logger.debug(f"Cache miss: {cache_key}")
        result = self._component.operation()
        self.cache[cache_key] = result

        return result

    def clear_cache(self):
        """Clear cache."""
        self.cache.clear()
        logger.info("Cache cleared")


class ValidationDecorator(Decorator):
    """Validation decorator."""

    def __init__(self, component: Component, validator: Optional[Callable] = None):
        """Initialize validation decorator."""
        super().__init__(component)
        self.decorator_type = DecoratorType.VALIDATION
        self.validator = validator or (lambda x: x is not None)
        self.validation_count = 0
        self.validation_failures = 0

    def operation(self) -> Any:
        """Execute with validation."""
        result = self._component.operation()

        self.validation_count += 1

        if not self.validator(result):
            self.validation_failures += 1
            logger.warning(f"Validation failed for result: {result}")
            raise ValueError(f"Validation failed: {result}")

        logger.debug(f"Validation passed for result: {result}")
        return result


class TimingDecorator(Decorator):
    """Timing decorator."""

    def __init__(self, component: Component):
        """Initialize timing decorator."""
        super().__init__(component)
        self.decorator_type = DecoratorType.TIMING
        self.execution_times = []

    def operation(self) -> Any:
        """Execute with timing."""
        start_time = time.time()

        result = self._component.operation()

        end_time = time.time()
        execution_time = end_time - start_time

        self.execution_times.append(execution_time)
        logger.info(f"Execution time: {execution_time:.6f}s")

        return result

    def get_average_time(self) -> float:
        """Get average execution time."""
        if not self.execution_times:
            return 0.0
        return sum(self.execution_times) / len(self.execution_times)


class RetryDecorator(Decorator):
    """Retry decorator."""

    def __init__(self, component: Component, max_retries: int = 3):
        """Initialize retry decorator."""
        super().__init__(component)
        self.decorator_type = DecoratorType.RETRY
        self.max_retries = max_retries
        self.retry_count = 0

    def operation(self) -> Any:
        """Execute with retry logic."""
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                result = self._component.operation()
                if attempt > 0:
                    logger.info(f"Succeeded on retry {attempt}")
                return result
            except Exception as e:
                self.retry_count += 1
                last_exception = e
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt < self.max_retries - 1:
                    time.sleep(0.1 * (attempt + 1))  # Exponential backoff

        logger.error(f"All {self.max_retries} retries failed")
        raise last_exception


class AuthorizationDecorator(Decorator):
    """Authorization decorator."""

    def __init__(self, component: Component, required_role: str = "user"):
        """Initialize authorization decorator."""
        super().__init__(component)
        self.decorator_type = DecoratorType.AUTHORIZATION
        self.required_role = required_role
        self.current_role = "guest"
        self.auth_checks = 0
        self.auth_failures = 0

    def set_role(self, role: str):
        """Set current user role."""
        self.current_role = role

    def operation(self) -> Any:
        """Execute with authorization check."""
        self.auth_checks += 1

        if self.current_role != self.required_role:
            self.auth_failures += 1
            logger.warning(f"Authorization failed: required={self.required_role}, current={self.current_role}")
            raise PermissionError(f"Unauthorized: requires {self.required_role}")

        logger.debug(f"Authorization passed for role: {self.current_role}")
        return self._component.operation()


class CompressionDecorator(Decorator):
    """Compression decorator."""

    def __init__(self, component: Component):
        """Initialize compression decorator."""
        super().__init__(component)
        self.decorator_type = DecoratorType.COMPRESSION
        self.compression_ratio = 0.0

    def operation(self) -> Any:
        """Execute with compression simulation."""
        result = self._component.operation()

        # Simulate compression
        original_size = len(str(result))
        compressed_size = original_size // 2  # Simulated 50% compression
        self.compression_ratio = compressed_size / original_size if original_size > 0 else 0

        logger.debug(f"Compression ratio: {self.compression_ratio:.2f}")

        return result


class EncryptionDecorator(Decorator):
    """Encryption decorator."""

    def __init__(self, component: Component, key: str = "default_key"):
        """Initialize encryption decorator."""
        super().__init__(component)
        self.decorator_type = DecoratorType.ENCRYPTION
        self.key = key
        self.encrypted_count = 0

    def operation(self) -> Any:
        """Execute with encryption simulation."""
        result = self._component.operation()

        # Simulate encryption
        encrypted = f"encrypted_{self.key}_{result}"
        self.encrypted_count += 1

        logger.debug(f"Data encrypted with key: {self.key}")

        return encrypted


# ==================== Data Classes ====================

@dataclass
class DecoratorOp:
    """Decorator operation."""
    operation: str = ""
    component_type: Optional[str] = None
    decorator_type: Optional[str] = None
    component: Optional[Component] = None
    decorator: Optional[Decorator] = None
    decorators: List[Decorator] = field(default_factory=list)
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DecoratorResult:
    """Decorator pattern pipeline result."""
    success: bool
    operations_count: int = 0
    decorations_applied: int = 0
    errors: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    results: List[Any] = field(default_factory=list)


@dataclass
class DecoratorConfig:
    """Decorator pattern configuration."""
    enable_caching: bool = True
    enable_validation: bool = True
    enable_logging: bool = True
    enable_timing: bool = True
    max_decorator_depth: int = 10
    thread_safe: bool = True
    enable_async: bool = False
    enable_composition: bool = True


@dataclass
class ValidationResult:
    """Configuration validation result."""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class RegisterResult:
    """Decorator registration result."""
    registered: bool
    decorator_name: str = ""
    error: Optional[str] = None


@dataclass
class StackResult:
    """Decorator stacking result."""
    stacked: bool
    layers: int = 0
    decorated_component: Optional[Decorator] = None
    error: Optional[str] = None


@dataclass
class DecorationValidation:
    """Decoration validation result."""
    valid: bool
    depth: int = 0
    decorator_types: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class ComposedDecorator:
    """Composed decorator result."""
    decorator_class: Optional[Type] = None
    component_types: List[Type] = field(default_factory=list)
    composition_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass
class DecoratorChain:
    """Decorator chain configuration."""
    chain_id: str = field(default_factory=lambda: str(uuid4()))
    decorators: List[Type] = field(default_factory=list)
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChainResult:
    """Decorator chain application result."""
    applied: bool
    chain_length: int = 0
    decorated_component: Optional[Decorator] = None
    error: Optional[str] = None


@dataclass
class RemoveResult:
    """Decorator removal result."""
    removed: bool
    decorator_name: str = ""
    remaining_layers: int = 0
    error: Optional[str] = None


@dataclass
class CloneResult:
    """Decorator clone result."""
    cloned: bool
    original_id: str = ""
    clone_id: str = ""
    error: Optional[str] = None


@dataclass
class MergeResult:
    """Decorator merge result."""
    merged: bool
    total_decorators: int = 0
    merged_component: Optional[Decorator] = None
    error: Optional[str] = None


@dataclass
class ReorderResult:
    """Decorator reorder result."""
    reordered: bool
    new_order: List[str] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class DecoratorMetrics:
    """Decorator metrics."""
    component_id: str = ""
    decorator_count: int = 0
    decorator_types: List[str] = field(default_factory=list)
    total_operations: int = 0
    creation_time: Optional[datetime] = None
    last_operation: Optional[datetime] = None


@dataclass
class ConditionalDecorator:
    """Conditional decorator wrapper."""
    decorator: Decorator
    condition: Callable[[], bool]
    conditional_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass
class DecoratedComponent:
    """Decorated component wrapper."""
    component: Decorator
    decoration_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)


# ==================== Decorator Factory ====================

class DecoratorFactory:
    """Factory for creating decorators."""

    _decorator_types: Dict[str, Type[Decorator]] = {
        "logging": LoggingDecorator,
        "caching": CachingDecorator,
        "validation": ValidationDecorator,
        "timing": TimingDecorator,
        "retry": RetryDecorator,
        "authorization": AuthorizationDecorator,
        "compression": CompressionDecorator,
        "encryption": EncryptionDecorator,
    }

    @classmethod
    def create(cls, decorator_type: str, component: Component, **kwargs) -> Optional[Decorator]:
        """Create decorator instance."""
        decorator_class = cls._decorator_types.get(decorator_type)
        if not decorator_class:
            logger.error(f"Unknown decorator type: {decorator_type}")
            return None

        try:
            return decorator_class(component, **kwargs)
        except Exception as e:
            logger.error(f"Failed to create decorator: {str(e)}")
            return None

    @classmethod
    def register(cls, name: str, decorator_class: Type[Decorator]) -> bool:
        """Register custom decorator type."""
        if name in cls._decorator_types:
            logger.warning(f"Decorator type already registered: {name}")
            return False

        cls._decorator_types[name] = decorator_class
        logger.info(f"Registered decorator type: {name}")
        return True

    @classmethod
    def get_registered_types(cls) -> List[str]:
        """Get all registered decorator types."""
        return list(cls._decorator_types.keys())


# ==================== Main FSA Class ====================

class DecoratorPatternFSA:
    """
    Decorator Pattern FSA implementation.

    Provides decorator pattern functionality with stacking, composition,
    and comprehensive decoration management.
    """

    def __init__(self, config: DecoratorConfig):
        """
        Initialize Decorator Pattern FSA.

        Args:
            config: Decorator pattern configuration
        """
        self.config = config
        self.fsa_id = str(uuid4())

        # Component registry
        self.components: Dict[str, Component] = {}
        self.decorators: Dict[str, Decorator] = {}

        # Decorator registry
        self.decorator_registry: Dict[str, Type[Decorator]] = {}

        # Metrics
        self.decoration_count = 0
        self.operation_count = 0

        # Thread safety
        self._lock = threading.RLock() if config.thread_safe else None

        logger.info(f"Initialized DecoratorPatternFSA: {self.fsa_id}")

    def _acquire_lock(self):
        """Acquire lock for thread-safe operations."""
        if self._lock:
            self._lock.acquire()

    def _release_lock(self):
        """Release lock after thread-safe operations."""
        if self._lock:
            self._lock.release()

    def validate(self, config: DecoratorConfig) -> ValidationResult:
        """
        Validate decorator pattern configuration.

        Args:
            config: Configuration to validate

        Returns:
            ValidationResult with validation status
        """
        errors = []
        warnings = []

        if config.max_decorator_depth < 1:
            errors.append("max_decorator_depth must be positive")

        if config.max_decorator_depth > 100:
            warnings.append("High max_decorator_depth may impact performance")

        if not config.thread_safe:
            warnings.append("Thread safety is disabled - not recommended")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def create_component(self, component_type: str = "concrete", **kwargs) -> Optional[Component]:
        """
        Create base component.

        Args:
            component_type: Type of component to create
            **kwargs: Component parameters

        Returns:
            Component instance or None
        """
        try:
            self._acquire_lock()

            if component_type == "concrete":
                component = ConcreteComponent(kwargs.get('value'))
            elif component_type == "data":
                component = DataComponent(kwargs.get('data', {}))
            elif component_type == "service":
                component = ServiceComponent(kwargs.get('service_name', 'default'))
            else:
                logger.error(f"Unknown component type: {component_type}")
                return None

            self.components[component.component_id] = component
            logger.info(f"Created component: {component_type}")

            return component

        finally:
            self._release_lock()

    def create_decorator(
        self,
        decorator_type: str,
        component: Component,
        **kwargs
    ) -> Optional[Decorator]:
        """
        Create decorator instance.

        Args:
            decorator_type: Type of decorator
            component: Component to decorate
            **kwargs: Decorator parameters

        Returns:
            Decorator instance or None
        """
        try:
            self._acquire_lock()

            decorator = DecoratorFactory.create(decorator_type, component, **kwargs)

            if decorator:
                self.decorators[decorator.component_id] = decorator
                self.decoration_count += 1
                logger.info(f"Created decorator: {decorator_type}")

            return decorator

        finally:
            self._release_lock()

    def decorate(self, component: Component, decorator: Decorator) -> Optional[DecoratedComponent]:
        """
        Apply decorator to component.

        Args:
            component: Component to decorate
            decorator: Decorator to apply

        Returns:
            DecoratedComponent or None
        """
        try:
            self._acquire_lock()

            if not isinstance(decorator, Decorator):
                logger.error("Invalid decorator type")
                return None

            decorated = DecoratedComponent(
                component=decorator,
                decoration_count=1,
            )

            logger.info(f"Decorated component: {component.component_id}")

            return decorated

        finally:
            self._release_lock()

    def register_decorator(self, name: str, decorator_class: Type[Decorator]) -> RegisterResult:
        """
        Register decorator type.

        Args:
            name: Decorator name
            decorator_class: Decorator class

        Returns:
            RegisterResult with registration status
        """
        try:
            self._acquire_lock()

            if name in self.decorator_registry:
                return RegisterResult(
                    registered=False,
                    decorator_name=name,
                    error="Decorator already registered",
                )

            self.decorator_registry[name] = decorator_class
            DecoratorFactory.register(name, decorator_class)

            logger.info(f"Registered decorator: {name}")

            return RegisterResult(
                registered=True,
                decorator_name=name,
            )

        except Exception as e:
            return RegisterResult(
                registered=False,
                decorator_name=name,
                error=str(e),
            )

        finally:
            self._release_lock()

    def get_decorator(self, name: str) -> Optional[Type[Decorator]]:
        """
        Retrieve decorator class.

        Args:
            name: Decorator name

        Returns:
            Decorator class or None
        """
        try:
            self._acquire_lock()

            return self.decorator_registry.get(name)

        finally:
            self._release_lock()

    def stack_decorators(
        self,
        component: Component,
        decorators: List[str],
        **kwargs
    ) -> StackResult:
        """
        Apply multiple decorators.

        Args:
            component: Base component
            decorators: List of decorator types
            **kwargs: Decorator parameters

        Returns:
            StackResult with stacking status
        """
        try:
            self._acquire_lock()

            if len(decorators) > self.config.max_decorator_depth:
                return StackResult(
                    stacked=False,
                    error="Exceeds max decorator depth",
                )

            current = component

            for decorator_type in decorators:
                decorator = self.create_decorator(decorator_type, current, **kwargs)
                if not decorator:
                    return StackResult(
                        stacked=False,
                        layers=decorators.index(decorator_type),
                        error=f"Failed to create decorator: {decorator_type}",
                    )
                current = decorator

            logger.info(f"Stacked {len(decorators)} decorators")

            return StackResult(
                stacked=True,
                layers=len(decorators),
                decorated_component=current if isinstance(current, Decorator) else None,
            )

        except Exception as e:
            return StackResult(
                stacked=False,
                error=str(e),
            )

        finally:
            self._release_lock()

    def unwrap_decorator(self, decorated: Decorator) -> Optional[Component]:
        """
        Remove outer decorator.

        Args:
            decorated: Decorated component

        Returns:
            Inner component or None
        """
        try:
            self._acquire_lock()

            if not isinstance(decorated, Decorator):
                logger.error("Not a decorator")
                return None

            inner = decorated.get_component()
            logger.info(f"Unwrapped decorator: {decorated.__class__.__name__}")

            return inner

        finally:
            self._release_lock()

    def get_base_component(self, decorated: Component) -> Component:
        """
        Get innermost component.

        Args:
            decorated: Decorated component

        Returns:
            Base component
        """
        try:
            self._acquire_lock()

            current = decorated

            while isinstance(current, Decorator):
                current = current.get_component()

            logger.debug(f"Found base component: {current.component_id}")

            return current

        finally:
            self._release_lock()

    def validate_decoration(self, decorator: Decorator) -> DecorationValidation:
        """
        Verify decorator validity.

        Args:
            decorator: Decorator to validate

        Returns:
            DecorationValidation with validation status
        """
        errors = []
        warnings = []
        decorator_types = []
        depth = 0

        current = decorator

        while isinstance(current, Decorator):
            depth += 1
            decorator_types.append(current.__class__.__name__)

            if depth > self.config.max_decorator_depth:
                errors.append("Exceeds max decorator depth")
                break

            current = current.get_component()

        if depth == 0:
            errors.append("Not a decorated component")

        if depth > 5:
            warnings.append("Deep decorator stack may impact performance")

        return DecorationValidation(
            valid=len(errors) == 0,
            depth=depth,
            decorator_types=decorator_types,
            errors=errors,
            warnings=warnings,
        )

    def compose_decorators(self, decorators: List[Type[Decorator]]) -> ComposedDecorator:
        """
        Combine decorator types.

        Args:
            decorators: List of decorator classes

        Returns:
            ComposedDecorator
        """
        if not self.config.enable_composition:
            logger.warning("Decorator composition is disabled")
            return ComposedDecorator()

        # Create composed decorator class dynamically
        composed = ComposedDecorator(
            component_types=decorators,
        )

        logger.info(f"Composed {len(decorators)} decorator types")

        return composed

    def apply_decorator_chain(
        self,
        component: Component,
        chain: DecoratorChain
    ) -> ChainResult:
        """
        Sequential decoration.

        Args:
            component: Base component
            chain: Decorator chain configuration

        Returns:
            ChainResult with application status
        """
        try:
            self._acquire_lock()

            current = component

            for decorator_class in chain.decorators:
                # Get decorator type name
                decorator_name = decorator_class.__name__.replace('Decorator', '').lower()

                decorator = self.create_decorator(
                    decorator_name,
                    current,
                    **chain.params
                )

                if not decorator:
                    return ChainResult(
                        applied=False,
                        error=f"Failed to apply decorator: {decorator_name}",
                    )

                current = decorator

            logger.info(f"Applied decorator chain: {chain.chain_id}")

            return ChainResult(
                applied=True,
                chain_length=len(chain.decorators),
                decorated_component=current if isinstance(current, Decorator) else None,
            )

        except Exception as e:
            return ChainResult(
                applied=False,
                error=str(e),
            )

        finally:
            self._release_lock()

    def get_decorator_chain(self, decorated: Decorator) -> List[Decorator]:
        """
        Query decorator stack.

        Args:
            decorated: Decorated component

        Returns:
            List of decorators from outer to inner
        """
        try:
            self._acquire_lock()

            chain = []
            current = decorated

            while isinstance(current, Decorator):
                chain.append(current)
                current = current.get_component()

            logger.debug(f"Retrieved decorator chain of length {len(chain)}")

            return chain

        finally:
            self._release_lock()

    def count_decorators(self, decorated: Component) -> int:
        """
        Count decoration layers.

        Args:
            decorated: Decorated component

        Returns:
            Number of decorators
        """
        try:
            self._acquire_lock()

            count = 0
            current = decorated

            while isinstance(current, Decorator):
                count += 1
                current = current.get_component()

            return count

        finally:
            self._release_lock()

    def has_decorator(self, decorated: Component, decorator_type: Type[Decorator]) -> bool:
        """
        Check decorator presence.

        Args:
            decorated: Decorated component
            decorator_type: Decorator type to check

        Returns:
            True if decorator is present
        """
        try:
            self._acquire_lock()

            current = decorated

            while isinstance(current, Decorator):
                if isinstance(current, decorator_type):
                    return True
                current = current.get_component()

            return False

        finally:
            self._release_lock()

    def remove_decorator(
        self,
        decorated: Decorator,
        decorator_type: Type[Decorator]
    ) -> RemoveResult:
        """
        Strip specific decorator.

        Args:
            decorated: Decorated component
            decorator_type: Decorator type to remove

        Returns:
            RemoveResult with removal status
        """
        try:
            self._acquire_lock()

            # Build chain without the specified decorator
            chain = []
            current = decorated

            while isinstance(current, Decorator):
                if not isinstance(current, decorator_type):
                    chain.append((current.__class__, current))
                current = current.get_component()

            if len(chain) == self.count_decorators(decorated):
                return RemoveResult(
                    removed=False,
                    decorator_name=decorator_type.__name__,
                    error="Decorator not found",
                )

            # Rebuild decorator stack
            base = self.get_base_component(decorated)
            rebuilt = base

            for dec_class, original_dec in reversed(chain):
                # Create new decorator instance
                decorator_name = dec_class.__name__.replace('Decorator', '').lower()
                rebuilt = self.create_decorator(decorator_name, rebuilt)

            remaining = self.count_decorators(rebuilt)

            logger.info(f"Removed decorator: {decorator_type.__name__}")

            return RemoveResult(
                removed=True,
                decorator_name=decorator_type.__name__,
                remaining_layers=remaining,
            )

        except Exception as e:
            return RemoveResult(
                removed=False,
                decorator_name=decorator_type.__name__,
                error=str(e),
            )

        finally:
            self._release_lock()

    def clone_decorated(self, decorated: Decorator) -> CloneResult:
        """
        Duplicate decorated object.

        Args:
            decorated: Decorated component to clone

        Returns:
            CloneResult with clone status
        """
        try:
            self._acquire_lock()

            # Get decorator chain
            chain = self.get_decorator_chain(decorated)
            base = self.get_base_component(decorated)

            # Clone base component
            if isinstance(base, ConcreteComponent):
                cloned_base = ConcreteComponent(base.value)
            elif isinstance(base, DataComponent):
                cloned_base = DataComponent(deepcopy(base.data))
            elif isinstance(base, ServiceComponent):
                cloned_base = ServiceComponent(base.service_name)
            else:
                return CloneResult(
                    cloned=False,
                    original_id=decorated.component_id,
                    error="Unsupported component type",
                )

            # Reapply decorators
            current = cloned_base
            for decorator in reversed(chain):
                decorator_name = decorator.__class__.__name__.replace('Decorator', '').lower()
                current = self.create_decorator(decorator_name, current)

            logger.info(f"Cloned decorated component: {decorated.component_id}")

            return CloneResult(
                cloned=True,
                original_id=decorated.component_id,
                clone_id=current.component_id if current else "",
            )

        except Exception as e:
            return CloneResult(
                cloned=False,
                original_id=decorated.component_id,
                error=str(e),
            )

        finally:
            self._release_lock()

    def merge_decorations(
        self,
        decorated1: Decorator,
        decorated2: Decorator
    ) -> MergeResult:
        """
        Combine decorations.

        Args:
            decorated1: First decorated component
            decorated2: Second decorated component

        Returns:
            MergeResult with merge status
        """
        try:
            self._acquire_lock()

            # Get both decorator chains
            chain1 = self.get_decorator_chain(decorated1)
            chain2 = self.get_decorator_chain(decorated2)

            # Get base component from first
            base = self.get_base_component(decorated1)

            # Merge decorator types (avoid duplicates)
            merged_types = []
            for dec in chain1 + chain2:
                dec_type = dec.__class__.__name__.replace('Decorator', '').lower()
                if dec_type not in merged_types:
                    merged_types.append(dec_type)

            # Apply merged decorators
            current = base
            for dec_type in reversed(merged_types):
                current = self.create_decorator(dec_type, current)

            total = len(merged_types)

            logger.info(f"Merged {total} unique decorators")

            return MergeResult(
                merged=True,
                total_decorators=total,
                merged_component=current if isinstance(current, Decorator) else None,
            )

        except Exception as e:
            return MergeResult(
                merged=False,
                error=str(e),
            )

        finally:
            self._release_lock()

    def get_decoration_order(self, decorated: Decorator) -> List[str]:
        """
        Query decorator sequence.

        Args:
            decorated: Decorated component

        Returns:
            List of decorator names from outer to inner
        """
        try:
            self._acquire_lock()

            order = []
            current = decorated

            while isinstance(current, Decorator):
                order.append(current.__class__.__name__)
                current = current.get_component()

            return order

        finally:
            self._release_lock()

    def reorder_decorators(
        self,
        decorated: Decorator,
        order: List[str]
    ) -> ReorderResult:
        """
        Change decorator sequence.

        Args:
            decorated: Decorated component
            order: New decorator order (outer to inner)

        Returns:
            ReorderResult with reorder status
        """
        try:
            self._acquire_lock()

            # Get current decorators
            current_chain = self.get_decorator_chain(decorated)
            current_types = {d.__class__.__name__: d for d in current_chain}

            # Validate order
            if set(order) != set(current_types.keys()):
                return ReorderResult(
                    reordered=False,
                    error="Order must contain exactly the current decorators",
                )

            # Get base component
            base = self.get_base_component(decorated)

            # Apply decorators in new order
            current = base
            for decorator_name in reversed(order):
                dec_type = decorator_name.replace('Decorator', '').lower()
                current = self.create_decorator(dec_type, current)

            logger.info(f"Reordered decorators: {order}")

            return ReorderResult(
                reordered=True,
                new_order=order,
            )

        except Exception as e:
            return ReorderResult(
                reordered=False,
                error=str(e),
            )

        finally:
            self._release_lock()

    def get_decorator_metrics(self, decorated: Decorator) -> DecoratorMetrics:
        """
        Collect decoration statistics.

        Args:
            decorated: Decorated component

        Returns:
            DecoratorMetrics
        """
        try:
            self._acquire_lock()

            count = self.count_decorators(decorated)
            types = self.get_decoration_order(decorated)
            base = self.get_base_component(decorated)

            # Count total operations
            total_ops = 0
            current = decorated
            while isinstance(current, Decorator):
                if hasattr(current, 'operation_count'):
                    total_ops += current.operation_count
                current = current.get_component()

            return DecoratorMetrics(
                component_id=decorated.component_id,
                decorator_count=count,
                decorator_types=types,
                total_operations=total_ops,
                creation_time=decorated.created_at,
            )

        finally:
            self._release_lock()

    def create_conditional_decorator(
        self,
        condition: Callable[[], bool],
        decorator: Decorator
    ) -> ConditionalDecorator:
        """
        Conditional decoration.

        Args:
            condition: Condition function
            decorator: Decorator to apply conditionally

        Returns:
            ConditionalDecorator wrapper
        """
        conditional = ConditionalDecorator(
            decorator=decorator,
            condition=condition,
        )

        logger.info(f"Created conditional decorator: {decorator.__class__.__name__}")

        return conditional

    def execute(self, ops: List[DecoratorOp]) -> DecoratorResult:
        """
        Execute decorator pattern pipeline.

        Args:
            ops: List of decorator operations

        Returns:
            DecoratorResult with pipeline result
        """
        try:
            start_time = time.time()
            decorations_applied = 0
            errors = []
            results = []

            for op in ops:
                if op.operation == "create_component":
                    component = self.create_component(
                        op.component_type or "concrete",
                        **op.params
                    )
                    if component:
                        results.append(component)
                    else:
                        errors.append("Failed to create component")

                elif op.operation == "create_decorator":
                    if op.component:
                        decorator = self.create_decorator(
                            op.decorator_type or "logging",
                            op.component,
                            **op.params
                        )
                        if decorator:
                            decorations_applied += 1
                            results.append(decorator)
                        else:
                            errors.append("Failed to create decorator")

                elif op.operation == "stack":
                    if op.component and op.decorators:
                        decorator_names = [d for d in op.decorators if isinstance(d, str)]
                        result = self.stack_decorators(op.component, decorator_names, **op.params)
                        if result.stacked:
                            decorations_applied += result.layers
                            results.append(result.decorated_component)
                        else:
                            errors.append(result.error or "Stacking failed")

            execution_time = time.time() - start_time

            return DecoratorResult(
                success=len(errors) == 0,
                operations_count=len(ops),
                decorations_applied=decorations_applied,
                errors=errors,
                execution_time=execution_time,
                results=results,
            )

        except Exception as e:
            logger.error(f"Pipeline execution failed: {str(e)}")
            return DecoratorResult(
                success=False,
                errors=[str(e)],
            )
