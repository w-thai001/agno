"""Adapter Pattern FSA for agno.

This module provides a comprehensive adapter pattern implementation with support for:
- Class adapters using inheritance
- Object adapters using composition
- Two-way adapters for bidirectional conversion
- Pluggable adapters with strategy pattern
- Interface translation and mapping
- Adapter composition and chaining
- Legacy system compatibility
"""

import logging
import threading
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, Protocol
from uuid import uuid4

logger = logging.getLogger(__name__)


# ==================== Enums ====================

class AdapterType(Enum):
    """Adapter type."""
    CLASS = "class"
    OBJECT = "object"
    TWO_WAY = "two_way"
    PLUGGABLE = "pluggable"


class AdaptationDirection(Enum):
    """Adaptation direction."""
    FORWARD = "forward"
    REVERSE = "reverse"
    BIDIRECTIONAL = "bidirectional"


# ==================== Target Interface ====================

class Target(ABC):
    """Target interface - the interface clients expect."""

    @abstractmethod
    def request(self) -> str:
        """Standard request method."""
        pass

    @abstractmethod
    def get_info(self) -> Dict[str, Any]:
        """Get information."""
        pass


# ==================== Adaptee Classes ====================

class Adaptee:
    """Adaptee - existing incompatible interface."""

    def __init__(self, data: str = "default"):
        """Initialize adaptee."""
        self.data = data
        self.call_count = 0

    def specific_request(self) -> str:
        """Specific request with different signature."""
        self.call_count += 1
        return f"Specific: {self.data}"

    def get_data(self) -> str:
        """Get data in different format."""
        return self.data

    def set_data(self, data: str):
        """Set data."""
        self.data = data


class LegacySystem:
    """Legacy system with incompatible interface."""

    def __init__(self, value: int = 0):
        """Initialize legacy system."""
        self.value = value

    def legacy_operation(self) -> int:
        """Legacy operation."""
        return self.value * 2

    def legacy_get_value(self) -> int:
        """Get value in legacy format."""
        return self.value


class ModernInterface(ABC):
    """Modern interface definition."""

    @abstractmethod
    def execute(self) -> Any:
        """Execute operation."""
        pass

    @abstractmethod
    def get_result(self) -> Any:
        """Get result."""
        pass


# ==================== Class Adapter ====================

class ClassAdapter(Adaptee, Target):
    """
    Class adapter using multiple inheritance.

    Adapts Adaptee to Target interface using inheritance.
    """

    def __init__(self, data: str = "adapted"):
        """Initialize class adapter."""
        super().__init__(data)
        self.adapter_id = str(uuid4())
        self.adapter_type = AdapterType.CLASS
        self.created_at = datetime.now()

    def request(self) -> str:
        """Implement Target's request using Adaptee's specific_request."""
        return self.specific_request()

    def get_info(self) -> Dict[str, Any]:
        """Implement Target's get_info."""
        return {
            'adapter_id': self.adapter_id,
            'adapter_type': self.adapter_type.value,
            'data': self.get_data(),
            'call_count': self.call_count,
        }


# ==================== Object Adapter ====================

class ObjectAdapter(Target):
    """
    Object adapter using composition.

    Adapts Adaptee to Target interface using composition.
    """

    def __init__(self, adaptee: Adaptee):
        """Initialize object adapter."""
        self._adaptee = adaptee
        self.adapter_id = str(uuid4())
        self.adapter_type = AdapterType.OBJECT
        self.created_at = datetime.now()
        self.adaptation_count = 0

    def request(self) -> str:
        """Implement Target's request by delegating to adaptee."""
        self.adaptation_count += 1
        return self._adaptee.specific_request()

    def get_info(self) -> Dict[str, Any]:
        """Implement Target's get_info."""
        return {
            'adapter_id': self.adapter_id,
            'adapter_type': self.adapter_type.value,
            'adaptee_data': self._adaptee.get_data(),
            'adaptation_count': self.adaptation_count,
        }

    def get_adaptee(self) -> Adaptee:
        """Get wrapped adaptee."""
        return self._adaptee


# ==================== Two-Way Adapter ====================

class TwoWayAdapter:
    """
    Two-way adapter for bidirectional conversion.

    Allows conversion in both directions between interfaces.
    """

    def __init__(self, interface1: Type, interface2: Type):
        """Initialize two-way adapter."""
        self.interface1 = interface1
        self.interface2 = interface2
        self.adapter_id = str(uuid4())
        self.adapter_type = AdapterType.TWO_WAY
        self.created_at = datetime.now()
        self.forward_conversions = 0
        self.reverse_conversions = 0

    def forward_adapt(self, obj: Any) -> Any:
        """Adapt from interface1 to interface2."""
        self.forward_conversions += 1
        logger.debug(f"Forward adapting from {self.interface1} to {self.interface2}")
        # Simplified conversion logic
        return obj

    def reverse_adapt(self, obj: Any) -> Any:
        """Adapt from interface2 to interface1."""
        self.reverse_conversions += 1
        logger.debug(f"Reverse adapting from {self.interface2} to {self.interface1}")
        # Simplified conversion logic
        return obj

    def get_direction_stats(self) -> Dict[str, int]:
        """Get conversion statistics."""
        return {
            'forward': self.forward_conversions,
            'reverse': self.reverse_conversions,
        }


# ==================== Adaptation Strategies ====================

class AdaptationStrategy(ABC):
    """Base adaptation strategy."""

    @abstractmethod
    def adapt(self, source: Any) -> Any:
        """Adapt source to target."""
        pass


class DirectMappingStrategy(AdaptationStrategy):
    """Direct method mapping strategy."""

    def __init__(self, method_map: Dict[str, str]):
        """Initialize with method mapping."""
        self.method_map = method_map

    def adapt(self, source: Any) -> Any:
        """Adapt using direct method mapping."""
        # Create adapted object with mapped methods
        adapted = type('Adapted', (), {})()

        for target_method, source_method in self.method_map.items():
            if hasattr(source, source_method):
                setattr(adapted, target_method, getattr(source, source_method))

        return adapted


class TransformationStrategy(AdaptationStrategy):
    """Transformation-based strategy."""

    def __init__(self, transform_func: Callable):
        """Initialize with transformation function."""
        self.transform_func = transform_func

    def adapt(self, source: Any) -> Any:
        """Adapt using transformation function."""
        return self.transform_func(source)


# ==================== Pluggable Adapter ====================

class PluggableAdapter(Target):
    """
    Pluggable adapter using strategy pattern.

    Allows changing adaptation strategy at runtime.
    """

    def __init__(self, adaptee: Any, strategy: AdaptationStrategy):
        """Initialize pluggable adapter."""
        self._adaptee = adaptee
        self._strategy = strategy
        self.adapter_id = str(uuid4())
        self.adapter_type = AdapterType.PLUGGABLE
        self.created_at = datetime.now()
        self.strategy_changes = 0

    def request(self) -> str:
        """Implement request using current strategy."""
        adapted = self._strategy.adapt(self._adaptee)
        if hasattr(adapted, 'request'):
            return adapted.request()
        return str(adapted)

    def get_info(self) -> Dict[str, Any]:
        """Get adapter info."""
        return {
            'adapter_id': self.adapter_id,
            'adapter_type': self.adapter_type.value,
            'strategy': self._strategy.__class__.__name__,
            'strategy_changes': self.strategy_changes,
        }

    def set_strategy(self, strategy: AdaptationStrategy):
        """Change adaptation strategy."""
        self._strategy = strategy
        self.strategy_changes += 1
        logger.info(f"Strategy changed to {strategy.__class__.__name__}")


# ==================== Lazy Adapter ====================

class LazyAdapter(Target):
    """Lazy adapter - defers adaptee creation until needed."""

    def __init__(self, target_type: Type, adaptee_factory: Callable):
        """Initialize lazy adapter."""
        self.target_type = target_type
        self.adaptee_factory = adaptee_factory
        self._adaptee = None
        self._adapter = None
        self.adapter_id = str(uuid4())
        self.created_at = datetime.now()
        self.initialized = False

    def _ensure_initialized(self):
        """Ensure adaptee is created."""
        if not self.initialized:
            self._adaptee = self.adaptee_factory()
            self._adapter = ObjectAdapter(self._adaptee)
            self.initialized = True
            logger.debug("Lazy adapter initialized")

    def request(self) -> str:
        """Implement request."""
        self._ensure_initialized()
        return self._adapter.request()

    def get_info(self) -> Dict[str, Any]:
        """Get info."""
        self._ensure_initialized()
        return self._adapter.get_info()


# ==================== Data Classes ====================

@dataclass
class AdapterOp:
    """Adapter operation."""
    operation: str = ""
    adapter_type: Optional[str] = None
    source_type: Optional[Type] = None
    target_type: Optional[Type] = None
    adaptee: Optional[Any] = None
    adapter: Optional[Any] = None
    strategy: Optional[AdaptationStrategy] = None
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AdapterResult:
    """Adapter pattern pipeline result."""
    success: bool
    operations_count: int = 0
    adaptations_performed: int = 0
    errors: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    results: List[Any] = field(default_factory=list)


@dataclass
class AdapterConfig:
    """Adapter pattern configuration."""
    enable_class_adapters: bool = True
    enable_object_adapters: bool = True
    enable_two_way_adapters: bool = True
    enable_pluggable_adapters: bool = True
    enable_lazy_adapters: bool = True
    max_adapter_chain_depth: int = 10
    thread_safe: bool = True
    enable_validation: bool = True


@dataclass
class ValidationResult:
    """Configuration validation result."""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class RegisterResult:
    """Adapter registration result."""
    registered: bool
    source_type: str = ""
    target_type: str = ""
    error: Optional[str] = None


@dataclass
class TranslateResult:
    """Interface translation result."""
    translated: bool
    adapted_object: Optional[Any] = None
    method_mappings: Dict[str, str] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class AdaptationValidation:
    """Adaptation validation result."""
    valid: bool
    conformance_score: float = 0.0
    missing_methods: List[str] = field(default_factory=list)
    extra_methods: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class ComposedAdapter:
    """Composed adapter result."""
    adapter: Optional[Any] = None
    chain_length: int = 0
    composition_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass
class CompatibilityResult:
    """Interface compatibility result."""
    compatible: bool
    compatibility_score: float = 0.0
    common_methods: List[str] = field(default_factory=list)
    incompatible_methods: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class SetStrategyResult:
    """Strategy setting result."""
    success: bool
    previous_strategy: str = ""
    new_strategy: str = ""
    error: Optional[str] = None


@dataclass
class ReverseResult:
    """Reverse adaptation result."""
    success: bool
    original_object: Optional[Any] = None
    error: Optional[str] = None


@dataclass
class CloneResult:
    """Adapter clone result."""
    cloned: bool
    original_id: str = ""
    clone_id: str = ""
    error: Optional[str] = None


@dataclass
class MergeResult:
    """Adapter merge result."""
    merged: bool
    merged_adapter: Optional[Any] = None
    total_mappings: int = 0
    error: Optional[str] = None


@dataclass
class AdapterMetrics:
    """Adapter metrics."""
    adapter_id: str = ""
    adapter_type: str = ""
    adaptation_count: int = 0
    creation_time: Optional[datetime] = None
    last_adaptation: Optional[datetime] = None
    method_call_counts: Dict[str, int] = field(default_factory=dict)


@dataclass
class AdaptedObject:
    """Adapted object wrapper."""
    object: Any
    adapter: Any
    created_at: datetime = field(default_factory=datetime.now)


# ==================== Adapter Factory ====================

class AdapterFactory:
    """Factory for creating adapters."""

    def __init__(self, source_type: Type, target_type: Type):
        """Initialize adapter factory."""
        self.source_type = source_type
        self.target_type = target_type
        self.factory_id = str(uuid4())
        self.adapters_created = 0

    def create_class_adapter(self, **kwargs) -> ClassAdapter:
        """Create class adapter."""
        self.adapters_created += 1
        return ClassAdapter(**kwargs)

    def create_object_adapter(self, adaptee: Any) -> ObjectAdapter:
        """Create object adapter."""
        self.adapters_created += 1
        return ObjectAdapter(adaptee)

    def create_adapter(self, adapter_type: str, **kwargs) -> Any:
        """Create adapter of specified type."""
        if adapter_type == "class":
            return self.create_class_adapter(**kwargs)
        elif adapter_type == "object":
            if 'adaptee' in kwargs:
                return self.create_object_adapter(kwargs['adaptee'])
        return None


# ==================== Main FSA Class ====================

class AdapterPatternFSA:
    """
    Adapter Pattern FSA implementation.

    Provides adapter pattern functionality with class adapters,
    object adapters, two-way adapters, and pluggable adapters.
    """

    def __init__(self, config: AdapterConfig):
        """
        Initialize Adapter Pattern FSA.

        Args:
            config: Adapter pattern configuration
        """
        self.config = config
        self.fsa_id = str(uuid4())

        # Adapter registry - maps (source_type, target_type) to adapter class
        self.adapter_registry: Dict[tuple, Type] = {}

        # Method mappings - maps (source_type, target_type) to method map
        self.method_mappings: Dict[tuple, Dict[str, str]] = {}

        # Adapter instances
        self.adapters: Dict[str, Any] = {}

        # Metrics
        self.adaptation_count = 0
        self.validation_count = 0

        # Thread safety
        self._lock = threading.RLock() if config.thread_safe else None

        logger.info(f"Initialized AdapterPatternFSA: {self.fsa_id}")

    def _acquire_lock(self):
        """Acquire lock for thread-safe operations."""
        if self._lock:
            self._lock.acquire()

    def _release_lock(self):
        """Release lock after thread-safe operations."""
        if self._lock:
            self._lock.release()

    def validate(self, config: AdapterConfig) -> ValidationResult:
        """
        Validate adapter pattern configuration.

        Args:
            config: Configuration to validate

        Returns:
            ValidationResult with validation status
        """
        errors = []
        warnings = []

        if config.max_adapter_chain_depth < 1:
            errors.append("max_adapter_chain_depth must be positive")

        if config.max_adapter_chain_depth > 50:
            warnings.append("High max_adapter_chain_depth may impact performance")

        if not config.thread_safe:
            warnings.append("Thread safety is disabled - not recommended")

        if not (config.enable_class_adapters or config.enable_object_adapters):
            errors.append("At least one adapter type must be enabled")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def create_class_adapter(
        self,
        target_type: Type = Target,
        adaptee_type: Type = Adaptee,
        **kwargs
    ) -> Optional[ClassAdapter]:
        """
        Create class adapter.

        Args:
            target_type: Target interface type
            adaptee_type: Adaptee type
            **kwargs: Adapter parameters

        Returns:
            ClassAdapter instance or None
        """
        try:
            self._acquire_lock()

            if not self.config.enable_class_adapters:
                logger.error("Class adapters are disabled")
                return None

            adapter = ClassAdapter(**kwargs)
            self.adapters[adapter.adapter_id] = adapter
            self.adaptation_count += 1

            logger.info(f"Created class adapter: {adapter.adapter_id}")

            return adapter

        finally:
            self._release_lock()

    def create_object_adapter(
        self,
        target_type: Type = Target,
        adaptee: Any = None,
    ) -> Optional[ObjectAdapter]:
        """
        Create object adapter.

        Args:
            target_type: Target interface type
            adaptee: Adaptee instance to wrap

        Returns:
            ObjectAdapter instance or None
        """
        try:
            self._acquire_lock()

            if not self.config.enable_object_adapters:
                logger.error("Object adapters are disabled")
                return None

            if adaptee is None:
                logger.error("Adaptee is required for object adapter")
                return None

            adapter = ObjectAdapter(adaptee)
            self.adapters[adapter.adapter_id] = adapter
            self.adaptation_count += 1

            logger.info(f"Created object adapter: {adapter.adapter_id}")

            return adapter

        finally:
            self._release_lock()

    def create_two_way_adapter(
        self,
        interface1: Type,
        interface2: Type,
    ) -> Optional[TwoWayAdapter]:
        """
        Create two-way adapter.

        Args:
            interface1: First interface type
            interface2: Second interface type

        Returns:
            TwoWayAdapter instance or None
        """
        try:
            self._acquire_lock()

            if not self.config.enable_two_way_adapters:
                logger.error("Two-way adapters are disabled")
                return None

            adapter = TwoWayAdapter(interface1, interface2)
            self.adapters[adapter.adapter_id] = adapter

            logger.info(f"Created two-way adapter: {adapter.adapter_id}")

            return adapter

        finally:
            self._release_lock()

    def create_pluggable_adapter(
        self,
        target_type: Type,
        adaptee: Any,
        strategy: AdaptationStrategy,
    ) -> Optional[PluggableAdapter]:
        """
        Create pluggable adapter.

        Args:
            target_type: Target interface type
            adaptee: Adaptee instance
            strategy: Adaptation strategy

        Returns:
            PluggableAdapter instance or None
        """
        try:
            self._acquire_lock()

            if not self.config.enable_pluggable_adapters:
                logger.error("Pluggable adapters are disabled")
                return None

            adapter = PluggableAdapter(adaptee, strategy)
            self.adapters[adapter.adapter_id] = adapter
            self.adaptation_count += 1

            logger.info(f"Created pluggable adapter: {adapter.adapter_id}")

            return adapter

        finally:
            self._release_lock()

    def adapt(
        self,
        adaptee: Any,
        target_interface: Type = Target,
        adapter_type: str = "object",
    ) -> Optional[AdaptedObject]:
        """
        Adapt adaptee to target interface.

        Args:
            adaptee: Object to adapt
            target_interface: Target interface type
            adapter_type: Type of adapter to use

        Returns:
            AdaptedObject or None
        """
        try:
            self._acquire_lock()

            if adapter_type == "object":
                adapter = self.create_object_adapter(target_interface, adaptee)
            elif adapter_type == "class":
                adapter = self.create_class_adapter(target_interface, type(adaptee))
            else:
                logger.error(f"Unknown adapter type: {adapter_type}")
                return None

            if adapter:
                return AdaptedObject(
                    object=adapter,
                    adapter=adapter,
                )

            return None

        finally:
            self._release_lock()

    def register_adapter(
        self,
        source_type: Type,
        target_type: Type,
        adapter_class: Type,
        method_map: Optional[Dict[str, str]] = None,
    ) -> RegisterResult:
        """
        Register adapter for type conversion.

        Args:
            source_type: Source interface type
            target_type: Target interface type
            adapter_class: Adapter class to use
            method_map: Optional method mapping

        Returns:
            RegisterResult with registration status
        """
        try:
            self._acquire_lock()

            key = (source_type, target_type)

            if key in self.adapter_registry:
                return RegisterResult(
                    registered=False,
                    source_type=source_type.__name__,
                    target_type=target_type.__name__,
                    error="Adapter already registered for this type pair",
                )

            self.adapter_registry[key] = adapter_class

            if method_map:
                self.method_mappings[key] = method_map

            logger.info(f"Registered adapter: {source_type.__name__} -> {target_type.__name__}")

            return RegisterResult(
                registered=True,
                source_type=source_type.__name__,
                target_type=target_type.__name__,
            )

        except Exception as e:
            return RegisterResult(
                registered=False,
                source_type=source_type.__name__ if source_type else "",
                target_type=target_type.__name__ if target_type else "",
                error=str(e),
            )

        finally:
            self._release_lock()

    def get_adapter(
        self,
        source_type: Type,
        target_type: Type,
    ) -> Optional[Type]:
        """
        Retrieve adapter class.

        Args:
            source_type: Source interface type
            target_type: Target interface type

        Returns:
            Adapter class or None
        """
        try:
            self._acquire_lock()

            key = (source_type, target_type)
            return self.adapter_registry.get(key)

        finally:
            self._release_lock()

    def translate_interface(
        self,
        source: Any,
        source_interface: Type,
        target_interface: Type,
    ) -> TranslateResult:
        """
        Translate from source to target interface.

        Args:
            source: Source object
            source_interface: Source interface type
            target_interface: Target interface type

        Returns:
            TranslateResult with translation status
        """
        try:
            self._acquire_lock()

            key = (source_interface, target_interface)
            adapter_class = self.adapter_registry.get(key)

            if not adapter_class:
                return TranslateResult(
                    translated=False,
                    error="No adapter registered for this type pair",
                )

            # Create adapter instance
            if hasattr(adapter_class, '__init__'):
                try:
                    adapter = adapter_class(source)
                except:
                    adapter = adapter_class()

            method_map = self.method_mappings.get(key, {})

            logger.info(f"Translated interface: {source_interface.__name__} -> {target_interface.__name__}")

            return TranslateResult(
                translated=True,
                adapted_object=adapter,
                method_mappings=method_map,
            )

        except Exception as e:
            return TranslateResult(
                translated=False,
                error=str(e),
            )

        finally:
            self._release_lock()

    def validate_adaptation(
        self,
        adapter: Any,
        target_interface: Type,
    ) -> AdaptationValidation:
        """
        Validate adapter conformance to target interface.

        Args:
            adapter: Adapter instance
            target_interface: Target interface type

        Returns:
            AdaptationValidation with validation status
        """
        self.validation_count += 1

        errors = []
        warnings = []
        missing_methods = []
        extra_methods = []

        # Get required methods from target interface
        required_methods = [
            name for name in dir(target_interface)
            if not name.startswith('_') and callable(getattr(target_interface, name, None))
        ]

        # Get implemented methods from adapter
        adapter_methods = [
            name for name in dir(adapter)
            if not name.startswith('_') and callable(getattr(adapter, name, None))
        ]

        # Check for missing methods
        for method in required_methods:
            if method not in adapter_methods:
                missing_methods.append(method)
                errors.append(f"Missing required method: {method}")

        # Calculate conformance score
        if required_methods:
            conformance = 1.0 - (len(missing_methods) / len(required_methods))
        else:
            conformance = 1.0

        if conformance < 1.0:
            warnings.append("Adapter does not fully implement target interface")

        return AdaptationValidation(
            valid=len(errors) == 0,
            conformance_score=conformance,
            missing_methods=missing_methods,
            extra_methods=extra_methods,
            errors=errors,
            warnings=warnings,
        )

    def compose_adapters(self, adapters: List[Any]) -> ComposedAdapter:
        """
        Compose multiple adapters into a chain.

        Args:
            adapters: List of adapters to compose

        Returns:
            ComposedAdapter
        """
        try:
            self._acquire_lock()

            if len(adapters) > self.config.max_adapter_chain_depth:
                logger.warning("Adapter chain exceeds maximum depth")

            # Create composed adapter by chaining
            composed = adapters[0] if adapters else None

            for i in range(1, len(adapters)):
                # Each adapter wraps the previous
                if hasattr(adapters[i], '_adaptee'):
                    adapters[i]._adaptee = composed
                composed = adapters[i]

            logger.info(f"Composed {len(adapters)} adapters")

            return ComposedAdapter(
                adapter=composed,
                chain_length=len(adapters),
            )

        finally:
            self._release_lock()

    def get_adapted_methods(self, adapter: Any) -> List[str]:
        """
        Get list of adapted method names.

        Args:
            adapter: Adapter instance

        Returns:
            List of method names
        """
        methods = [
            name for name in dir(adapter)
            if not name.startswith('_') and callable(getattr(adapter, name))
        ]

        logger.debug(f"Found {len(methods)} methods in adapter")

        return methods

    def check_interface_compatibility(
        self,
        source: Type,
        target: Type,
    ) -> CompatibilityResult:
        """
        Check interface compatibility.

        Args:
            source: Source interface type
            target: Target interface type

        Returns:
            CompatibilityResult
        """
        # Get methods from both interfaces
        source_methods = set([
            name for name in dir(source)
            if not name.startswith('_') and callable(getattr(source, name, None))
        ])

        target_methods = set([
            name for name in dir(target)
            if not name.startswith('_') and callable(getattr(target, name, None))
        ])

        # Find common and incompatible methods
        common = list(source_methods & target_methods)
        incompatible = list(target_methods - source_methods)

        # Calculate compatibility score
        if target_methods:
            compatibility = len(common) / len(target_methods)
        else:
            compatibility = 1.0

        compatible = compatibility >= 0.5  # At least 50% compatible

        suggestions = []
        if incompatible:
            suggestions.append(f"Implement missing methods: {', '.join(incompatible[:3])}")

        logger.debug(f"Interface compatibility: {compatibility:.2f}")

        return CompatibilityResult(
            compatible=compatible,
            compatibility_score=compatibility,
            common_methods=common,
            incompatible_methods=incompatible,
            suggestions=suggestions,
        )

    def create_adapter_factory(
        self,
        source_type: Type,
        target_type: Type,
    ) -> AdapterFactory:
        """
        Create adapter factory.

        Args:
            source_type: Source interface type
            target_type: Target interface type

        Returns:
            AdapterFactory instance
        """
        factory = AdapterFactory(source_type, target_type)

        logger.info(f"Created adapter factory: {factory.factory_id}")

        return factory

    def get_adaptation_mapping(self, adapter: Any) -> Dict[str, str]:
        """
        Get adaptation method mapping.

        Args:
            adapter: Adapter instance

        Returns:
            Dictionary mapping target methods to source methods
        """
        mapping = {}

        # For class adapters, introspect the mapping
        if isinstance(adapter, ClassAdapter):
            mapping = {
                'request': 'specific_request',
                'get_info': 'get_data',
            }

        # For object adapters, check the adaptee
        elif isinstance(adapter, ObjectAdapter):
            adaptee = adapter.get_adaptee()
            adaptee_methods = [m for m in dir(adaptee) if not m.startswith('_')]
            adapter_methods = [m for m in dir(adapter) if not m.startswith('_')]

            # Simple heuristic mapping
            for am in adapter_methods:
                for em in adaptee_methods:
                    if em.lower() in am.lower() or am.lower() in em.lower():
                        mapping[am] = em
                        break

        logger.debug(f"Retrieved {len(mapping)} method mappings")

        return mapping

    def set_adaptation_strategy(
        self,
        adapter: PluggableAdapter,
        strategy: AdaptationStrategy,
    ) -> SetStrategyResult:
        """
        Set adaptation strategy for pluggable adapter.

        Args:
            adapter: Pluggable adapter instance
            strategy: New adaptation strategy

        Returns:
            SetStrategyResult
        """
        try:
            if not isinstance(adapter, PluggableAdapter):
                return SetStrategyResult(
                    success=False,
                    error="Not a pluggable adapter",
                )

            previous = adapter._strategy.__class__.__name__
            adapter.set_strategy(strategy)
            new = strategy.__class__.__name__

            logger.info(f"Changed strategy from {previous} to {new}")

            return SetStrategyResult(
                success=True,
                previous_strategy=previous,
                new_strategy=new,
            )

        except Exception as e:
            return SetStrategyResult(
                success=False,
                error=str(e),
            )

    def reverse_adapt(
        self,
        adapted: Any,
        original_interface: Type,
    ) -> ReverseResult:
        """
        Reverse adapt back to original interface.

        Args:
            adapted: Adapted object
            original_interface: Original interface type

        Returns:
            ReverseResult
        """
        try:
            # For object adapters, extract the adaptee
            if isinstance(adapted, ObjectAdapter):
                original = adapted.get_adaptee()
                return ReverseResult(
                    success=True,
                    original_object=original,
                )

            # For two-way adapters, use reverse_adapt method
            elif isinstance(adapted, TwoWayAdapter):
                original = adapted.reverse_adapt(adapted)
                return ReverseResult(
                    success=True,
                    original_object=original,
                )

            return ReverseResult(
                success=False,
                error="Cannot reverse this adapter type",
            )

        except Exception as e:
            return ReverseResult(
                success=False,
                error=str(e),
            )

    def clone_adapter(self, adapter: Any) -> CloneResult:
        """
        Clone adapter instance.

        Args:
            adapter: Adapter to clone

        Returns:
            CloneResult
        """
        try:
            self._acquire_lock()

            # Create a deep copy of the adapter
            cloned = deepcopy(adapter)

            # Assign new ID
            if hasattr(cloned, 'adapter_id'):
                original_id = adapter.adapter_id
                cloned.adapter_id = str(uuid4())

                self.adapters[cloned.adapter_id] = cloned

                logger.info(f"Cloned adapter: {original_id} -> {cloned.adapter_id}")

                return CloneResult(
                    cloned=True,
                    original_id=original_id,
                    clone_id=cloned.adapter_id,
                )

            return CloneResult(
                cloned=False,
                error="Adapter does not have adapter_id",
            )

        except Exception as e:
            return CloneResult(
                cloned=False,
                error=str(e),
            )

        finally:
            self._release_lock()

    def merge_adapters(
        self,
        adapter1: Any,
        adapter2: Any,
    ) -> MergeResult:
        """
        Merge two adapters.

        Args:
            adapter1: First adapter
            adapter2: Second adapter

        Returns:
            MergeResult
        """
        try:
            # Get method mappings from both
            map1 = self.get_adaptation_mapping(adapter1)
            map2 = self.get_adaptation_mapping(adapter2)

            # Merge mappings
            merged_map = {**map1, **map2}

            total = len(merged_map)

            logger.info(f"Merged adapters with {total} total mappings")

            return MergeResult(
                merged=True,
                merged_adapter=adapter1,  # Use first adapter as base
                total_mappings=total,
            )

        except Exception as e:
            return MergeResult(
                merged=False,
                error=str(e),
            )

    def get_adapter_metrics(self, adapter: Any) -> AdapterMetrics:
        """
        Get adapter metrics.

        Args:
            adapter: Adapter instance

        Returns:
            AdapterMetrics
        """
        metrics = AdapterMetrics()

        if hasattr(adapter, 'adapter_id'):
            metrics.adapter_id = adapter.adapter_id

        if hasattr(adapter, 'adapter_type'):
            metrics.adapter_type = adapter.adapter_type.value if isinstance(adapter.adapter_type, Enum) else str(adapter.adapter_type)

        if hasattr(adapter, 'adaptation_count'):
            metrics.adaptation_count = adapter.adaptation_count

        if hasattr(adapter, 'created_at'):
            metrics.creation_time = adapter.created_at

        # Count method calls
        if hasattr(adapter, 'call_count'):
            metrics.method_call_counts['call_count'] = adapter.call_count

        logger.debug(f"Retrieved metrics for adapter: {metrics.adapter_id}")

        return metrics

    def create_lazy_adapter(
        self,
        target_type: Type,
        adaptee_factory: Callable,
    ) -> Optional[LazyAdapter]:
        """
        Create lazy adapter.

        Args:
            target_type: Target interface type
            adaptee_factory: Factory function for creating adaptee

        Returns:
            LazyAdapter instance or None
        """
        try:
            self._acquire_lock()

            if not self.config.enable_lazy_adapters:
                logger.error("Lazy adapters are disabled")
                return None

            adapter = LazyAdapter(target_type, adaptee_factory)
            self.adapters[adapter.adapter_id] = adapter

            logger.info(f"Created lazy adapter: {adapter.adapter_id}")

            return adapter

        finally:
            self._release_lock()

    def execute(self, ops: List[AdapterOp]) -> AdapterResult:
        """
        Execute adapter pattern pipeline.

        Args:
            ops: List of adapter operations

        Returns:
            AdapterResult with pipeline result
        """
        try:
            start_time = time.time()
            adaptations_performed = 0
            errors = []
            results = []

            for op in ops:
                if op.operation == "create_class_adapter":
                    adapter = self.create_class_adapter(
                        op.target_type or Target,
                        op.source_type or Adaptee,
                        **op.params
                    )
                    if adapter:
                        adaptations_performed += 1
                        results.append(adapter)
                    else:
                        errors.append("Failed to create class adapter")

                elif op.operation == "create_object_adapter":
                    adapter = self.create_object_adapter(
                        op.target_type or Target,
                        op.adaptee,
                    )
                    if adapter:
                        adaptations_performed += 1
                        results.append(adapter)
                    else:
                        errors.append("Failed to create object adapter")

                elif op.operation == "adapt":
                    if op.adaptee:
                        adapted = self.adapt(
                            op.adaptee,
                            op.target_type or Target,
                            op.adapter_type or "object",
                        )
                        if adapted:
                            adaptations_performed += 1
                            results.append(adapted)
                        else:
                            errors.append("Failed to adapt object")

                elif op.operation == "register":
                    if op.source_type and op.target_type and op.adapter:
                        result = self.register_adapter(
                            op.source_type,
                            op.target_type,
                            type(op.adapter),
                        )
                        if result.registered:
                            results.append(result)
                        else:
                            errors.append(result.error or "Registration failed")

            execution_time = time.time() - start_time

            return AdapterResult(
                success=len(errors) == 0,
                operations_count=len(ops),
                adaptations_performed=adaptations_performed,
                errors=errors,
                execution_time=execution_time,
                results=results,
            )

        except Exception as e:
            logger.error(f"Pipeline execution failed: {str(e)}")
            return AdapterResult(
                success=False,
                errors=[str(e)],
            )
