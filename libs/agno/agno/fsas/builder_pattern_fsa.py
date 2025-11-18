"""Builder Pattern FSA for agno.

This module provides a comprehensive builder pattern implementation with support for:
- Step-by-step object construction
- Fluent interfaces with method chaining
- Director classes for construction orchestration
- Build step validation
- Immutable result objects
- Build state management (save/restore)
- Construction history tracking
- Builder cloning and merging
- Thread-safe operations
"""

import logging
import threading
import time
from abc import ABC, abstractmethod
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type
from uuid import uuid4

logger = logging.getLogger(__name__)


# ==================== Enums ====================

class BuildState(Enum):
    """Build state."""
    INITIALIZED = "initialized"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RESET = "reset"


class StepStatus(Enum):
    """Build step status."""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


# ==================== Base Classes ====================

class Product:
    """Base product class."""

    def __init__(self):
        self.product_id = str(uuid4())
        self.created_at = datetime.now()
        self.properties: Dict[str, Any] = {}
        self.is_immutable = False

    def set_property(self, key: str, value: Any):
        """Set a property."""
        if self.is_immutable:
            raise ValueError("Cannot modify immutable product")
        self.properties[key] = value

    def get_property(self, key: str, default: Any = None) -> Any:
        """Get a property."""
        return self.properties.get(key, default)

    def make_immutable(self):
        """Make the product immutable."""
        self.is_immutable = True


class Builder(ABC):
    """Abstract builder interface."""

    def __init__(self):
        self.builder_id = str(uuid4())
        self.state = BuildState.INITIALIZED
        self.product: Optional[Product] = None
        self.build_steps: List['BuildStep'] = []
        self.current_step = 0
        self.fluent_methods: Dict[str, Callable] = {}
        self.build_history: List[Dict[str, Any]] = []

    @abstractmethod
    def reset(self):
        """Reset the builder."""
        pass

    @abstractmethod
    def get_result(self) -> Product:
        """Get the constructed product."""
        pass


class Director:
    """Director for orchestrating construction."""

    def __init__(self, builder: Builder):
        self.director_id = str(uuid4())
        self.builder = builder
        self.algorithm: Optional[Callable] = None

    def construct(self):
        """Execute construction algorithm."""
        if self.algorithm:
            self.algorithm(self.builder)


# ==================== Data Classes ====================

@dataclass
class BuildStep:
    """Build step definition."""
    step_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    status: StepStatus = StepStatus.PENDING
    executed_at: Optional[datetime] = None
    error: Optional[str] = None


@dataclass
class BuilderOp:
    """Builder operation."""
    operation: str = ""
    builder_name: Optional[str] = None
    builder_type: Optional[str] = None
    builder: Optional[Builder] = None
    step_name: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)
    steps: List[BuildStep] = field(default_factory=list)


@dataclass
class BuilderResult:
    """Builder pattern pipeline result."""
    success: bool
    operations_count: int = 0
    products_built: int = 0
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
class RegisterResult:
    """Builder registration result."""
    registered: bool
    builder_name: str = ""
    builder_id: str = ""
    error: Optional[str] = None


@dataclass
class StepResult:
    """Build step execution result."""
    executed: bool
    step_name: str = ""
    error: Optional[str] = None
    execution_time: float = 0.0


@dataclass
class StepValidation:
    """Build step validation result."""
    valid: bool
    step_name: str = ""
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class ResetResult:
    """Builder reset result."""
    reset: bool
    builder_id: str = ""
    error: Optional[str] = None


@dataclass
class DirectorResult:
    """Director construction result."""
    constructed: bool
    director_id: str = ""
    steps_executed: int = 0
    error: Optional[str] = None


@dataclass
class FluentResult:
    """Fluent method addition result."""
    added: bool
    method_name: str = ""
    error: Optional[str] = None


@dataclass
class ChainResult:
    """Build step chain execution result."""
    executed: bool
    steps_completed: int = 0
    errors: List[str] = field(default_factory=list)


@dataclass
class BuildContext:
    """Build context for passing state."""
    context_id: str = field(default_factory=lambda: str(uuid4()))
    params: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class BuildStateSnapshot:
    """Builder state snapshot."""
    snapshot_id: str = field(default_factory=lambda: str(uuid4()))
    builder_id: str = ""
    state: BuildState = BuildState.INITIALIZED
    product_snapshot: Optional[Dict[str, Any]] = None
    current_step: int = 0
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class RestoreResult:
    """State restoration result."""
    restored: bool
    snapshot_id: str = ""
    error: Optional[str] = None


@dataclass
class BuildHistory:
    """Construction history."""
    builder_id: str = ""
    steps: List[BuildStep] = field(default_factory=list)
    history_entries: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ImmutableProduct:
    """Immutable product wrapper."""
    product_id: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    frozen_at: datetime = field(default_factory=datetime.now)


@dataclass
class CloneResult:
    """Builder clone result."""
    cloned: bool
    original_id: str = ""
    clone_id: str = ""
    error: Optional[str] = None


@dataclass
class MergeResult:
    """Builder merge result."""
    merged: bool
    merged_builder_id: str = ""
    source_count: int = 0
    error: Optional[str] = None


@dataclass
class ProductValidation:
    """Product validation result."""
    valid: bool
    product_id: str = ""
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class BuilderMetrics:
    """Builder metrics."""
    builder_id: str = ""
    steps_completed: int = 0
    steps_failed: int = 0
    total_build_time: float = 0.0
    avg_step_time: float = 0.0


@dataclass
class BuilderConfig:
    """Builder pattern configuration."""
    enable_validation: bool = True
    enable_history: bool = True
    enable_immutability: bool = True
    enable_state_snapshots: bool = True
    enable_fluent_interface: bool = True
    enable_directors: bool = True
    thread_safe: bool = True
    max_builders: int = 1000
    max_steps_per_builder: int = 100
    allow_override: bool = False


# ==================== Concrete Products ====================

class House(Product):
    """House product."""

    def __init__(self):
        super().__init__()
        self.product_type = "House"


class Car(Product):
    """Car product."""

    def __init__(self):
        super().__init__()
        self.product_type = "Car"


class Computer(Product):
    """Computer product."""

    def __init__(self):
        super().__init__()
        self.product_type = "Computer"


# ==================== Concrete Builders ====================

class HouseBuilder(Builder):
    """Builder for constructing houses."""

    def __init__(self):
        super().__init__()
        self.product = House()

    def reset(self):
        """Reset the builder."""
        self.product = House()
        self.state = BuildState.INITIALIZED
        self.current_step = 0
        self.build_steps.clear()
        if self.build_history:
            self.build_history.append({
                "action": "reset",
                "timestamp": datetime.now(),
            })

    def get_result(self) -> Product:
        """Get the constructed house."""
        if self.state != BuildState.COMPLETED:
            raise ValueError("Construction not completed")
        return self.product

    def build_foundation(self, material: str = "concrete") -> 'HouseBuilder':
        """Build foundation (fluent method)."""
        self.product.set_property("foundation", material)
        self.state = BuildState.IN_PROGRESS
        if self.build_history is not None:
            self.build_history.append({
                "action": "build_foundation",
                "material": material,
                "timestamp": datetime.now(),
            })
        return self

    def build_walls(self, material: str = "brick") -> 'HouseBuilder':
        """Build walls (fluent method)."""
        self.product.set_property("walls", material)
        if self.build_history is not None:
            self.build_history.append({
                "action": "build_walls",
                "material": material,
                "timestamp": datetime.now(),
            })
        return self

    def build_roof(self, material: str = "tile") -> 'HouseBuilder':
        """Build roof (fluent method)."""
        self.product.set_property("roof", material)
        self.state = BuildState.COMPLETED
        if self.build_history is not None:
            self.build_history.append({
                "action": "build_roof",
                "material": material,
                "timestamp": datetime.now(),
            })
        return self


class CarBuilder(Builder):
    """Builder for constructing cars."""

    def __init__(self):
        super().__init__()
        self.product = Car()

    def reset(self):
        """Reset the builder."""
        self.product = Car()
        self.state = BuildState.INITIALIZED
        self.current_step = 0
        self.build_steps.clear()
        if self.build_history:
            self.build_history.append({
                "action": "reset",
                "timestamp": datetime.now(),
            })

    def get_result(self) -> Product:
        """Get the constructed car."""
        if self.state != BuildState.COMPLETED:
            raise ValueError("Construction not completed")
        return self.product

    def build_engine(self, engine_type: str = "V6") -> 'CarBuilder':
        """Build engine (fluent method)."""
        self.product.set_property("engine", engine_type)
        self.state = BuildState.IN_PROGRESS
        if self.build_history is not None:
            self.build_history.append({
                "action": "build_engine",
                "engine_type": engine_type,
                "timestamp": datetime.now(),
            })
        return self

    def build_wheels(self, count: int = 4) -> 'CarBuilder':
        """Build wheels (fluent method)."""
        self.product.set_property("wheels", count)
        if self.build_history is not None:
            self.build_history.append({
                "action": "build_wheels",
                "count": count,
                "timestamp": datetime.now(),
            })
        return self

    def build_body(self, color: str = "red") -> 'CarBuilder':
        """Build body (fluent method)."""
        self.product.set_property("body_color", color)
        self.state = BuildState.COMPLETED
        if self.build_history is not None:
            self.build_history.append({
                "action": "build_body",
                "color": color,
                "timestamp": datetime.now(),
            })
        return self


class ComputerBuilder(Builder):
    """Builder for constructing computers."""

    def __init__(self):
        super().__init__()
        self.product = Computer()

    def reset(self):
        """Reset the builder."""
        self.product = Computer()
        self.state = BuildState.INITIALIZED
        self.current_step = 0
        self.build_steps.clear()
        if self.build_history:
            self.build_history.append({
                "action": "reset",
                "timestamp": datetime.now(),
            })

    def get_result(self) -> Product:
        """Get the constructed computer."""
        if self.state != BuildState.COMPLETED:
            raise ValueError("Construction not completed")
        return self.product

    def add_cpu(self, model: str = "Intel i7") -> 'ComputerBuilder':
        """Add CPU (fluent method)."""
        self.product.set_property("cpu", model)
        self.state = BuildState.IN_PROGRESS
        if self.build_history is not None:
            self.build_history.append({
                "action": "add_cpu",
                "model": model,
                "timestamp": datetime.now(),
            })
        return self

    def add_ram(self, size_gb: int = 16) -> 'ComputerBuilder':
        """Add RAM (fluent method)."""
        self.product.set_property("ram", size_gb)
        if self.build_history is not None:
            self.build_history.append({
                "action": "add_ram",
                "size_gb": size_gb,
                "timestamp": datetime.now(),
            })
        return self

    def add_storage(self, size_gb: int = 512) -> 'ComputerBuilder':
        """Add storage (fluent method)."""
        self.product.set_property("storage", size_gb)
        self.state = BuildState.COMPLETED
        if self.build_history is not None:
            self.build_history.append({
                "action": "add_storage",
                "size_gb": size_gb,
                "timestamp": datetime.now(),
            })
        return self


# ==================== Lazy Builder ====================

class LazyBuilder(Builder):
    """Lazy builder with deferred construction."""

    def __init__(self, builder_factory: Callable):
        super().__init__()
        self.builder_factory = builder_factory
        self.actual_builder: Optional[Builder] = None
        self.deferred_operations: List[tuple] = []

    def _ensure_builder(self):
        """Ensure actual builder is created."""
        if self.actual_builder is None:
            self.actual_builder = self.builder_factory()

    def reset(self):
        """Reset the builder."""
        if self.actual_builder:
            self.actual_builder.reset()
        else:
            self.deferred_operations.clear()

    def get_result(self) -> Product:
        """Get the constructed product."""
        self._ensure_builder()
        # Execute deferred operations
        for method_name, args, kwargs in self.deferred_operations:
            method = getattr(self.actual_builder, method_name)
            method(*args, **kwargs)
        self.deferred_operations.clear()
        return self.actual_builder.get_result()

    def defer_operation(self, method_name: str, *args, **kwargs):
        """Defer an operation."""
        self.deferred_operations.append((method_name, args, kwargs))


# ==================== Directors ====================

class HouseDirector(Director):
    """Director for building houses."""

    def construct_simple_house(self):
        """Construct a simple house."""
        if isinstance(self.builder, HouseBuilder):
            self.builder.build_foundation("concrete")
            self.builder.build_walls("brick")
            self.builder.build_roof("tile")

    def construct_luxury_house(self):
        """Construct a luxury house."""
        if isinstance(self.builder, HouseBuilder):
            self.builder.build_foundation("reinforced_concrete")
            self.builder.build_walls("marble")
            self.builder.build_roof("slate")


class CarDirector(Director):
    """Director for building cars."""

    def construct_sports_car(self):
        """Construct a sports car."""
        if isinstance(self.builder, CarBuilder):
            self.builder.build_engine("V8")
            self.builder.build_wheels(4)
            self.builder.build_body("red")

    def construct_suv(self):
        """Construct an SUV."""
        if isinstance(self.builder, CarBuilder):
            self.builder.build_engine("V6")
            self.builder.build_wheels(4)
            self.builder.build_body("black")


# ==================== Main FSA Class ====================

class BuilderPatternFSA:
    """
    Builder Pattern FSA implementation.

    Provides builder pattern functionality with fluent interfaces, directors,
    and comprehensive construction management.
    """

    def __init__(self, config: BuilderConfig):
        """
        Initialize Builder Pattern FSA.

        Args:
            config: Builder pattern configuration
        """
        self.config = config
        self.fsa_id = str(uuid4())

        # Builder storage
        self.builders: Dict[str, Builder] = {}
        self.directors: Dict[str, Director] = {}
        self.contexts: Dict[str, BuildContext] = {}
        self.snapshots: Dict[str, BuildStateSnapshot] = {}

        # Builder factories
        self.builder_factories: Dict[str, Callable] = {
            "house": HouseBuilder,
            "car": CarBuilder,
            "computer": ComputerBuilder,
        }

        # Metrics
        self.build_times: Dict[str, List[float]] = {}
        self.step_times: Dict[str, List[float]] = {}

        # Thread safety
        self._lock = threading.RLock() if config.thread_safe else None

        logger.info(f"Initialized BuilderPatternFSA: {self.fsa_id}")

    def _acquire_lock(self):
        """Acquire lock for thread-safe operations."""
        if self._lock:
            self._lock.acquire()

    def _release_lock(self):
        """Release lock after thread-safe operations."""
        if self._lock:
            self._lock.release()

    def validate(self, config: BuilderConfig) -> ValidationResult:
        """
        Validate builder pattern configuration.

        Args:
            config: Configuration to validate

        Returns:
            ValidationResult with validation status
        """
        errors = []
        warnings = []

        if config.max_builders < 1:
            errors.append("max_builders must be positive")

        if config.max_steps_per_builder < 1:
            errors.append("max_steps_per_builder must be positive")

        if not config.enable_validation:
            warnings.append("Build step validation is disabled")

        if not config.thread_safe:
            warnings.append("Thread safety is disabled")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def create_builder(self, builder_type: str) -> Optional[Builder]:
        """
        Create a builder instance.

        Args:
            builder_type: Type of builder to create

        Returns:
            Builder instance or None
        """
        try:
            self._acquire_lock()

            if builder_type not in self.builder_factories:
                logger.error(f"Unknown builder type: {builder_type}")
                return None

            factory = self.builder_factories[builder_type]
            builder = factory()

            logger.info(f"Created builder: {builder.builder_id}")
            return builder

        finally:
            self._release_lock()

    def register_builder(self, name: str, builder: Builder) -> RegisterResult:
        """
        Register a builder.

        Args:
            name: Builder name
            builder: Builder instance

        Returns:
            RegisterResult with registration status
        """
        try:
            self._acquire_lock()

            if len(self.builders) >= self.config.max_builders:
                return RegisterResult(
                    registered=False,
                    builder_name=name,
                    error="Maximum builders reached",
                )

            if name in self.builders and not self.config.allow_override:
                return RegisterResult(
                    registered=False,
                    builder_name=name,
                    error="Builder already registered",
                )

            self.builders[name] = builder
            logger.info(f"Registered builder: {name}")

            return RegisterResult(
                registered=True,
                builder_name=name,
                builder_id=builder.builder_id,
            )

        except Exception as e:
            return RegisterResult(
                registered=False,
                builder_name=name,
                error=str(e),
            )

        finally:
            self._release_lock()

    def get_builder(self, name: str) -> Optional[Builder]:
        """
        Get a registered builder.

        Args:
            name: Builder name

        Returns:
            Builder instance or None
        """
        try:
            self._acquire_lock()

            return self.builders.get(name)

        finally:
            self._release_lock()

    def build_step(
        self,
        builder: Builder,
        step_name: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> StepResult:
        """
        Execute a build step.

        Args:
            builder: Builder to use
            step_name: Name of step to execute
            params: Step parameters

        Returns:
            StepResult with execution status
        """
        try:
            self._acquire_lock()

            start_time = time.time()
            params = params or {}

            # Check if method exists
            if not hasattr(builder, step_name):
                return StepResult(
                    executed=False,
                    step_name=step_name,
                    error=f"Step method not found: {step_name}",
                )

            # Execute step
            method = getattr(builder, step_name)
            method(**params)

            execution_time = time.time() - start_time

            # Track step time
            if builder.builder_id not in self.step_times:
                self.step_times[builder.builder_id] = []
            self.step_times[builder.builder_id].append(execution_time)

            # Create step record
            step = BuildStep(
                name=step_name,
                params=params,
                status=StepStatus.COMPLETED,
                executed_at=datetime.now(),
            )
            builder.build_steps.append(step)

            logger.info(f"Executed build step: {step_name}")

            return StepResult(
                executed=True,
                step_name=step_name,
                execution_time=execution_time,
            )

        except Exception as e:
            return StepResult(
                executed=False,
                step_name=step_name,
                error=str(e),
            )

        finally:
            self._release_lock()

    def validate_step(
        self,
        builder: Builder,
        step_name: str,
    ) -> StepValidation:
        """
        Validate a build step.

        Args:
            builder: Builder to validate
            step_name: Step name

        Returns:
            StepValidation with validation status
        """
        errors = []
        warnings = []

        if not self.config.enable_validation:
            warnings.append("Validation is disabled")
            return StepValidation(
                valid=True,
                step_name=step_name,
                warnings=warnings,
            )

        # Check if step method exists
        if not hasattr(builder, step_name):
            errors.append(f"Step method not found: {step_name}")

        # Check if builder is in valid state
        if builder.state == BuildState.FAILED:
            errors.append("Builder is in failed state")

        if builder.state == BuildState.COMPLETED:
            warnings.append("Builder already completed")

        return StepValidation(
            valid=len(errors) == 0,
            step_name=step_name,
            errors=errors,
            warnings=warnings,
        )

    def reset_builder(self, builder: Builder) -> ResetResult:
        """
        Reset a builder.

        Args:
            builder: Builder to reset

        Returns:
            ResetResult with reset status
        """
        try:
            self._acquire_lock()

            builder.reset()
            logger.info(f"Reset builder: {builder.builder_id}")

            return ResetResult(
                reset=True,
                builder_id=builder.builder_id,
            )

        except Exception as e:
            return ResetResult(
                reset=False,
                builder_id=builder.builder_id,
                error=str(e),
            )

        finally:
            self._release_lock()

    def get_result(self, builder: Builder) -> Optional[Product]:
        """
        Get the constructed product.

        Args:
            builder: Builder to get result from

        Returns:
            Product or None
        """
        try:
            self._acquire_lock()

            return builder.get_result()

        except Exception as e:
            logger.error(f"Error getting result: {str(e)}")
            return None

        finally:
            self._release_lock()

    def create_director(
        self,
        director_type: str,
        builder: Builder,
    ) -> Optional[Director]:
        """
        Create a director.

        Args:
            director_type: Type of director
            builder: Builder to use

        Returns:
            Director instance or None
        """
        try:
            self._acquire_lock()

            if not self.config.enable_directors:
                logger.error("Directors are disabled")
                return None

            if director_type == "house":
                director = HouseDirector(builder)
            elif director_type == "car":
                director = CarDirector(builder)
            else:
                logger.error(f"Unknown director type: {director_type}")
                return None

            self.directors[director.director_id] = director
            logger.info(f"Created director: {director.director_id}")

            return director

        finally:
            self._release_lock()

    def construct_with_director(
        self,
        director: Director,
        algorithm_name: Optional[str] = None,
    ) -> DirectorResult:
        """
        Use director for construction.

        Args:
            director: Director to use
            algorithm_name: Algorithm method name

        Returns:
            DirectorResult with construction status
        """
        try:
            self._acquire_lock()

            if not self.config.enable_directors:
                return DirectorResult(
                    constructed=False,
                    director_id=director.director_id,
                    error="Directors are disabled",
                )

            # Execute algorithm
            if algorithm_name:
                if not hasattr(director, algorithm_name):
                    return DirectorResult(
                        constructed=False,
                        director_id=director.director_id,
                        error=f"Algorithm not found: {algorithm_name}",
                    )
                method = getattr(director, algorithm_name)
                method()
            else:
                director.construct()

            steps_executed = len(director.builder.build_steps)

            logger.info(f"Director completed construction: {director.director_id}")

            return DirectorResult(
                constructed=True,
                director_id=director.director_id,
                steps_executed=steps_executed,
            )

        except Exception as e:
            return DirectorResult(
                constructed=False,
                director_id=director.director_id,
                error=str(e),
            )

        finally:
            self._release_lock()

    def add_fluent_method(
        self,
        builder: Builder,
        method_name: str,
        handler: Callable,
    ) -> FluentResult:
        """
        Add a fluent method to builder.

        Args:
            builder: Builder to modify
            method_name: Method name
            handler: Method handler

        Returns:
            FluentResult with addition status
        """
        try:
            self._acquire_lock()

            if not self.config.enable_fluent_interface:
                return FluentResult(
                    added=False,
                    method_name=method_name,
                    error="Fluent interface is disabled",
                )

            builder.fluent_methods[method_name] = handler
            logger.info(f"Added fluent method: {method_name}")

            return FluentResult(
                added=True,
                method_name=method_name,
            )

        except Exception as e:
            return FluentResult(
                added=False,
                method_name=method_name,
                error=str(e),
            )

        finally:
            self._release_lock()

    def chain_build_steps(
        self,
        builder: Builder,
        steps: List[BuildStep],
    ) -> ChainResult:
        """
        Execute a chain of build steps.

        Args:
            builder: Builder to use
            steps: Steps to execute

        Returns:
            ChainResult with execution status
        """
        try:
            self._acquire_lock()

            steps_completed = 0
            errors = []

            for step in steps:
                result = self.build_step(builder, step.name, step.params)
                if result.executed:
                    steps_completed += 1
                else:
                    errors.append(result.error or "Step failed")

            return ChainResult(
                executed=len(errors) == 0,
                steps_completed=steps_completed,
                errors=errors,
            )

        except Exception as e:
            return ChainResult(
                executed=False,
                errors=[str(e)],
            )

        finally:
            self._release_lock()

    def create_build_context(self, params: Dict[str, Any]) -> BuildContext:
        """
        Create a build context.

        Args:
            params: Context parameters

        Returns:
            BuildContext instance
        """
        try:
            self._acquire_lock()

            context = BuildContext(params=params)
            self.contexts[context.context_id] = context

            logger.info(f"Created build context: {context.context_id}")

            return context

        finally:
            self._release_lock()

    def save_build_state(self, builder: Builder) -> Optional[BuildStateSnapshot]:
        """
        Save builder state.

        Args:
            builder: Builder to save

        Returns:
            BuildStateSnapshot or None
        """
        try:
            self._acquire_lock()

            if not self.config.enable_state_snapshots:
                logger.error("State snapshots are disabled")
                return None

            # Create snapshot
            product_snapshot = None
            if builder.product:
                product_snapshot = {
                    "properties": builder.product.properties.copy(),
                    "is_immutable": builder.product.is_immutable,
                }

            snapshot = BuildStateSnapshot(
                builder_id=builder.builder_id,
                state=builder.state,
                product_snapshot=product_snapshot,
                current_step=builder.current_step,
            )

            self.snapshots[snapshot.snapshot_id] = snapshot
            logger.info(f"Saved build state: {snapshot.snapshot_id}")

            return snapshot

        finally:
            self._release_lock()

    def restore_build_state(
        self,
        builder: Builder,
        snapshot: BuildStateSnapshot,
    ) -> RestoreResult:
        """
        Restore builder state.

        Args:
            builder: Builder to restore
            snapshot: State snapshot

        Returns:
            RestoreResult with restoration status
        """
        try:
            self._acquire_lock()

            if not self.config.enable_state_snapshots:
                return RestoreResult(
                    restored=False,
                    snapshot_id=snapshot.snapshot_id,
                    error="State snapshots are disabled",
                )

            # Restore state
            builder.state = snapshot.state
            builder.current_step = snapshot.current_step

            # Restore product
            if snapshot.product_snapshot and builder.product:
                builder.product.properties = snapshot.product_snapshot["properties"].copy()
                builder.product.is_immutable = snapshot.product_snapshot["is_immutable"]

            logger.info(f"Restored build state: {snapshot.snapshot_id}")

            return RestoreResult(
                restored=True,
                snapshot_id=snapshot.snapshot_id,
            )

        except Exception as e:
            return RestoreResult(
                restored=False,
                snapshot_id=snapshot.snapshot_id,
                error=str(e),
            )

        finally:
            self._release_lock()

    def get_build_history(self, builder: Builder) -> BuildHistory:
        """
        Get build history.

        Args:
            builder: Builder to query

        Returns:
            BuildHistory with construction history
        """
        try:
            self._acquire_lock()

            if not self.config.enable_history:
                return BuildHistory(
                    builder_id=builder.builder_id,
                )

            return BuildHistory(
                builder_id=builder.builder_id,
                steps=builder.build_steps.copy(),
                history_entries=builder.build_history.copy(),
            )

        finally:
            self._release_lock()

    def make_immutable(self, product: Product) -> Optional[ImmutableProduct]:
        """
        Make product immutable.

        Args:
            product: Product to freeze

        Returns:
            ImmutableProduct or None
        """
        try:
            self._acquire_lock()

            if not self.config.enable_immutability:
                logger.error("Immutability is disabled")
                return None

            product.make_immutable()

            immutable = ImmutableProduct(
                product_id=product.product_id,
                properties=product.properties.copy(),
            )

            logger.info(f"Made product immutable: {product.product_id}")

            return immutable

        finally:
            self._release_lock()

    def clone_builder(self, builder: Builder) -> CloneResult:
        """
        Clone a builder.

        Args:
            builder: Builder to clone

        Returns:
            CloneResult with clone status
        """
        try:
            self._acquire_lock()

            # Create new builder of same type
            if isinstance(builder, HouseBuilder):
                cloned = HouseBuilder()
            elif isinstance(builder, CarBuilder):
                cloned = CarBuilder()
            elif isinstance(builder, ComputerBuilder):
                cloned = ComputerBuilder()
            else:
                return CloneResult(
                    cloned=False,
                    original_id=builder.builder_id,
                    error="Cannot clone unknown builder type",
                )

            # Copy state
            cloned.state = builder.state
            cloned.current_step = builder.current_step
            if builder.product and cloned.product:
                cloned.product.properties = builder.product.properties.copy()

            logger.info(f"Cloned builder: {builder.builder_id}")

            return CloneResult(
                cloned=True,
                original_id=builder.builder_id,
                clone_id=cloned.builder_id,
            )

        except Exception as e:
            return CloneResult(
                cloned=False,
                original_id=builder.builder_id,
                error=str(e),
            )

        finally:
            self._release_lock()

    def merge_builders(self, builders: List[Builder]) -> MergeResult:
        """
        Merge multiple builders.

        Args:
            builders: Builders to merge

        Returns:
            MergeResult with merge status
        """
        try:
            self._acquire_lock()

            if not builders:
                return MergeResult(
                    merged=False,
                    error="No builders to merge",
                )

            # Create new builder (use first builder's type)
            first_builder = builders[0]
            if isinstance(first_builder, HouseBuilder):
                merged = HouseBuilder()
            elif isinstance(first_builder, CarBuilder):
                merged = CarBuilder()
            elif isinstance(first_builder, ComputerBuilder):
                merged = ComputerBuilder()
            else:
                return MergeResult(
                    merged=False,
                    error="Cannot merge unknown builder type",
                )

            # Merge properties from all builders
            for builder in builders:
                if builder.product and merged.product:
                    merged.product.properties.update(builder.product.properties)

            logger.info(f"Merged {len(builders)} builders")

            return MergeResult(
                merged=True,
                merged_builder_id=merged.builder_id,
                source_count=len(builders),
            )

        except Exception as e:
            return MergeResult(
                merged=False,
                error=str(e),
            )

        finally:
            self._release_lock()

    def validate_product(
        self,
        product: Product,
        schema: Dict[str, Any],
    ) -> ProductValidation:
        """
        Validate a product.

        Args:
            product: Product to validate
            schema: Validation schema

        Returns:
            ProductValidation with validation status
        """
        errors = []
        warnings = []

        if not self.config.enable_validation:
            warnings.append("Validation is disabled")
            return ProductValidation(
                valid=True,
                product_id=product.product_id,
                warnings=warnings,
            )

        # Validate required properties
        required = schema.get("required", [])
        for prop in required:
            if prop not in product.properties:
                errors.append(f"Missing required property: {prop}")

        # Validate property types
        types = schema.get("types", {})
        for prop, expected_type in types.items():
            if prop in product.properties:
                actual_value = product.properties[prop]
                if not isinstance(actual_value, expected_type):
                    errors.append(f"Property {prop} has wrong type")

        return ProductValidation(
            valid=len(errors) == 0,
            product_id=product.product_id,
            errors=errors,
            warnings=warnings,
        )

    def get_builder_metrics(self, builder: Builder) -> BuilderMetrics:
        """
        Get builder metrics.

        Args:
            builder: Builder to query

        Returns:
            BuilderMetrics with statistics
        """
        try:
            self._acquire_lock()

            completed = sum(1 for s in builder.build_steps if s.status == StepStatus.COMPLETED)
            failed = sum(1 for s in builder.build_steps if s.status == StepStatus.FAILED)

            # Calculate average step time
            avg_step_time = 0.0
            if builder.builder_id in self.step_times:
                times = self.step_times[builder.builder_id]
                if times:
                    avg_step_time = sum(times) / len(times)

            return BuilderMetrics(
                builder_id=builder.builder_id,
                steps_completed=completed,
                steps_failed=failed,
                avg_step_time=avg_step_time,
            )

        finally:
            self._release_lock()

    def create_lazy_builder(self, builder_type: str) -> Optional[LazyBuilder]:
        """
        Create a lazy builder.

        Args:
            builder_type: Type of builder

        Returns:
            LazyBuilder instance or None
        """
        try:
            self._acquire_lock()

            if builder_type not in self.builder_factories:
                logger.error(f"Unknown builder type: {builder_type}")
                return None

            factory = self.builder_factories[builder_type]
            lazy_builder = LazyBuilder(factory)

            logger.info(f"Created lazy builder: {lazy_builder.builder_id}")

            return lazy_builder

        finally:
            self._release_lock()

    def execute(self, ops: List[BuilderOp]) -> BuilderResult:
        """
        Execute builder pattern pipeline.

        Args:
            ops: List of builder operations

        Returns:
            BuilderResult with pipeline result
        """
        try:
            start_time = time.time()
            products_built = 0
            errors = []
            results = []

            for op in ops:
                if op.operation == "create":
                    if op.builder_type:
                        builder = self.create_builder(op.builder_type)
                        if builder:
                            results.append(builder)
                        else:
                            errors.append("Failed to create builder")

                elif op.operation == "register":
                    if op.builder_name and op.builder:
                        result = self.register_builder(op.builder_name, op.builder)
                        results.append(result)
                        if not result.registered:
                            errors.append(result.error or "Registration failed")

                elif op.operation == "build_step":
                    if op.builder and op.step_name:
                        result = self.build_step(op.builder, op.step_name, op.params)
                        results.append(result)
                        if not result.executed:
                            errors.append(result.error or "Step failed")

                elif op.operation == "get_result":
                    if op.builder:
                        product = self.get_result(op.builder)
                        if product:
                            products_built += 1
                            results.append(product)
                        else:
                            errors.append("Failed to get result")

                elif op.operation == "chain":
                    if op.builder and op.steps:
                        result = self.chain_build_steps(op.builder, op.steps)
                        results.append(result)

            execution_time = time.time() - start_time

            return BuilderResult(
                success=len(errors) == 0,
                operations_count=len(ops),
                products_built=products_built,
                errors=errors,
                execution_time=execution_time,
                results=results,
            )

        except Exception as e:
            return BuilderResult(
                success=False,
                errors=[str(e)],
            )
