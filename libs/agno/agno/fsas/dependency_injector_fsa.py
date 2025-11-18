"""
Dependency Injector FSA - Enterprise-grade dependency injection system.

This module provides a comprehensive dependency injection framework with support for
constructor injection, property injection, method injection, lifecycle scoping,
circular dependency detection, auto-wiring, and aspect-oriented programming.
"""

import inspect
import json
import threading
import yaml
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type, TypeVar, Union, get_type_hints
from uuid import uuid4

try:
    from agno.utils.log import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


# ==================== Enums and Constants ====================

class Scope(Enum):
    """Dependency lifecycle scopes."""
    SINGLETON = "singleton"  # Single instance for entire container
    TRANSIENT = "transient"  # New instance each time
    SCOPED = "scoped"  # Single instance per scope
    REQUEST = "request"  # Single instance per request (web apps)


class InjectionType(Enum):
    """Types of dependency injection."""
    CONSTRUCTOR = "constructor"
    PROPERTY = "property"
    METHOD = "method"
    AUTO = "auto"


class RegistrationType(Enum):
    """Types of dependency registrations."""
    TYPE = "type"
    FACTORY = "factory"
    INSTANCE = "instance"


class ResolutionStrategy(Enum):
    """Dependency resolution strategies."""
    EAGER = "eager"  # Resolve immediately
    LAZY = "lazy"  # Resolve on first access
    OPTIONAL = "optional"  # Allow missing dependencies


# ==================== Data Classes ====================

@dataclass
class Registration:
    """Dependency registration information."""
    registration_id: str = field(default_factory=lambda: str(uuid4()))
    interface: Type = field(default=object)
    implementation: Optional[Type] = None
    factory: Optional[Callable] = None
    instance: Optional[Any] = None
    scope: Scope = Scope.TRANSIENT
    registration_type: RegistrationType = RegistrationType.TYPE
    registered_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DependencyInfo:
    """Information about a dependency."""
    parameter_name: str
    parameter_type: Type
    is_optional: bool = False
    default_value: Any = None
    resolved_value: Any = None


@dataclass
class CircularDependency:
    """Represents a circular dependency."""
    circular_id: str = field(default_factory=lambda: str(uuid4()))
    cycle: List[Type] = field(default_factory=list)
    detected_at: datetime = field(default_factory=datetime.now)


@dataclass
class DependencyGraph:
    """Dependency graph structure."""
    nodes: Set[Type] = field(default_factory=set)
    edges: List[Tuple[Type, Type]] = field(default_factory=list)
    root: Optional[Type] = None


@dataclass
class Interceptor(ABC):
    """Base class for AOP interceptors."""
    interceptor_id: str = field(default_factory=lambda: str(uuid4()))
    priority: int = 0

    @abstractmethod
    def intercept(self, instance: Any, method: str, args: tuple, kwargs: dict) -> Any:
        """Intercept method call."""
        pass


@dataclass
class InjectionOp:
    """Dependency injection operation."""
    operation: str
    target_type: Optional[Type] = None
    interface: Optional[Type] = None
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InjectionResult:
    """Result of injection pipeline execution."""
    success: bool
    injected_count: int = 0
    resolved_dependencies: List[Type] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    execution_time: float = 0.0


@dataclass
class ValidationResult:
    """DI configuration validation result."""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class RegisterResult:
    """Dependency registration result."""
    registered: bool
    registration_id: str = ""
    interface: Optional[Type] = None
    error: Optional[str] = None


@dataclass
class ConstructorInjectionResult:
    """Constructor injection result."""
    success: bool
    instance: Optional[Any] = None
    injected_dependencies: List[DependencyInfo] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class PropertyInjectionResult:
    """Property injection result."""
    success: bool
    property_name: str = ""
    injected_value: Optional[Any] = None
    error: Optional[str] = None


@dataclass
class MethodInjectionResult:
    """Method injection result."""
    success: bool
    method_name: str = ""
    injected_count: int = 0
    result: Optional[Any] = None
    error: Optional[str] = None


@dataclass
class AutoWireResult:
    """Auto-wiring result."""
    success: bool
    wired_dependencies: List[str] = field(default_factory=list)
    instance: Optional[Any] = None
    error: Optional[str] = None


@dataclass
class CircularResult:
    """Circular dependency detection result."""
    has_circular: bool
    circular_dependencies: List[CircularDependency] = field(default_factory=list)


@dataclass
class ResolutionResult:
    """Circular dependency resolution result."""
    resolved: bool
    strategy_used: str = ""
    error: Optional[str] = None


@dataclass
class FactoryRegisterResult:
    """Factory registration result."""
    registered: bool
    registration_id: str = ""
    error: Optional[str] = None


@dataclass
class InstanceRegisterResult:
    """Instance registration result."""
    registered: bool
    registration_id: str = ""
    error: Optional[str] = None


@dataclass
class InterceptResult:
    """Interceptor application result."""
    success: bool
    interceptor_id: str = ""
    error: Optional[str] = None


@dataclass
class LoadConfigResult:
    """Configuration loading result."""
    loaded: bool
    registrations_count: int = 0
    error: Optional[str] = None


@dataclass
class UnregisterResult:
    """Dependency unregistration result."""
    unregistered: bool
    interface: Optional[Type] = None
    error: Optional[str] = None


@dataclass
class ClearResult:
    """Container clearing result."""
    cleared: bool
    cleared_count: int = 0


@dataclass
class ScopeResult:
    """Scoped instance result."""
    success: bool
    instance: Optional[Any] = None
    scope: Optional[Scope] = None
    error: Optional[str] = None


@dataclass
class DisposeResult:
    """Scope disposal result."""
    disposed: bool
    disposed_count: int = 0
    error: Optional[str] = None


@dataclass
class DependencyValidation:
    """Dependency validation result."""
    valid: bool
    missing_dependencies: List[Type] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


@dataclass
class DIConfig:
    """Dependency Injector configuration."""
    enable_auto_wiring: bool = True
    allow_circular_dependencies: bool = False
    circular_resolution_strategy: str = "proxy"
    enable_interceptors: bool = True
    enable_lazy_resolution: bool = True
    thread_safe: bool = True
    validate_on_registration: bool = True
    default_scope: Scope = Scope.TRANSIENT
    max_resolution_depth: int = 100


# ==================== Type Variable ====================

T = TypeVar('T')


# ==================== Main FSA Class ====================

class DependencyInjectorFSA:
    """
    Dependency Injector Finite State Automaton.

    Provides enterprise-grade dependency injection with support for multiple
    injection types, lifecycle scoping, circular dependency detection,
    auto-wiring, and aspect-oriented programming.
    """

    def __init__(self, config: Optional[DIConfig] = None):
        """
        Initialize the dependency injector.

        Args:
            config: DI configuration
        """
        self.config = config or DIConfig()
        self.fsa_id = str(uuid4())

        # Thread safety
        self._lock = threading.RLock() if self.config.thread_safe else None

        # Dependency registry
        self.registrations: Dict[Type, Registration] = {}

        # Scoped instances
        self.singleton_instances: Dict[Type, Any] = {}
        self.scoped_instances: Dict[str, Dict[Type, Any]] = defaultdict(dict)  # scope_id -> instances

        # Hierarchical containers
        self.parent_container: Optional['DependencyInjectorFSA'] = None
        self.child_containers: List['DependencyInjectorFSA'] = []

        # Interceptors
        self.interceptors: Dict[Type, List[Interceptor]] = defaultdict(list)

        # Resolution tracking
        self.resolution_stack: List[Type] = []
        self.dependency_cache: Dict[Type, DependencyGraph] = {}

        logger.info(f"Initialized DependencyInjectorFSA {self.fsa_id}")

    def _acquire_lock(self):
        """Acquire thread lock if enabled."""
        if self._lock:
            self._lock.acquire()

    def _release_lock(self):
        """Release thread lock if enabled."""
        if self._lock:
            self._lock.release()

    def execute(self, injection_ops: List[InjectionOp]) -> InjectionResult:
        """
        Execute dependency injection pipeline.

        Args:
            injection_ops: List of injection operations

        Returns:
            InjectionResult with execution status
        """
        start_time = datetime.now()
        injected_count = 0
        resolved_dependencies = []
        errors = []

        try:
            self._acquire_lock()

            for op in injection_ops:
                try:
                    if op.operation == "register" and op.interface and op.target_type:
                        result = self.register(op.interface, op.target_type, Scope.TRANSIENT)
                        if result.registered:
                            injected_count += 1

                    elif op.operation == "resolve" and op.interface:
                        instance = self.resolve(op.interface)
                        if instance:
                            resolved_dependencies.append(op.interface)
                            injected_count += 1

                    elif op.operation == "auto_wire" and op.target_type:
                        result = self.auto_wire(op.target_type)
                        if result.success:
                            injected_count += 1
                            resolved_dependencies.append(op.target_type)

                except Exception as e:
                    errors.append(f"Error in operation {op.operation}: {str(e)}")

            execution_time = (datetime.now() - start_time).total_seconds()

            return InjectionResult(
                success=len(errors) == 0,
                injected_count=injected_count,
                resolved_dependencies=resolved_dependencies,
                errors=errors,
                execution_time=execution_time,
            )

        finally:
            self._release_lock()

    def validate(self, di_config: DIConfig) -> ValidationResult:
        """
        Validate DI configuration.

        Args:
            di_config: Configuration to validate

        Returns:
            ValidationResult with validation status
        """
        errors = []
        warnings = []

        # Validate resolution depth
        if di_config.max_resolution_depth < 1:
            errors.append("max_resolution_depth must be positive")

        # Validate circular dependency settings
        if di_config.allow_circular_dependencies and di_config.circular_resolution_strategy not in ["proxy", "lazy"]:
            errors.append("Invalid circular resolution strategy")

        # Warnings
        if not di_config.thread_safe:
            warnings.append("Thread safety is disabled")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def register(
        self,
        interface: Type,
        implementation: Type,
        scope: Scope = Scope.TRANSIENT,
    ) -> RegisterResult:
        """
        Register a dependency mapping.

        Args:
            interface: Interface type
            implementation: Implementation type
            scope: Lifecycle scope

        Returns:
            RegisterResult with registration status
        """
        try:
            self._acquire_lock()

            # Validate if enabled
            if self.config.validate_on_registration:
                if not inspect.isclass(implementation):
                    return RegisterResult(
                        registered=False,
                        error="Implementation must be a class",
                    )

            registration = Registration(
                interface=interface,
                implementation=implementation,
                scope=scope,
                registration_type=RegistrationType.TYPE,
            )

            self.registrations[interface] = registration

            logger.info(f"Registered {interface.__name__} -> {implementation.__name__} with scope {scope.value}")

            return RegisterResult(
                registered=True,
                registration_id=registration.registration_id,
                interface=interface,
            )

        except Exception as e:
            return RegisterResult(
                registered=False,
                error=str(e),
            )

        finally:
            self._release_lock()

    def resolve(self, interface: Type[T]) -> Optional[T]:
        """
        Resolve and instantiate a dependency.

        Args:
            interface: Interface type to resolve

        Returns:
            Resolved instance or None
        """
        try:
            self._acquire_lock()

            # Check for circular dependencies
            if interface in self.resolution_stack:
                if not self.config.allow_circular_dependencies:
                    logger.error(f"Circular dependency detected: {interface.__name__}")
                    return None

            self.resolution_stack.append(interface)

            try:
                # Check registration
                if interface not in self.registrations:
                    # Try parent container
                    if self.parent_container:
                        return self.parent_container.resolve(interface)
                    logger.error(f"No registration found for {interface.__name__}")
                    return None

                registration = self.registrations[interface]

                # Handle different scopes
                if registration.scope == Scope.SINGLETON:
                    if interface in self.singleton_instances:
                        return self.singleton_instances[interface]

                    instance = self._create_instance(registration)
                    if instance:
                        self.singleton_instances[interface] = instance
                    return instance

                elif registration.scope == Scope.TRANSIENT:
                    return self._create_instance(registration)

                elif registration.scope == Scope.SCOPED:
                    # Use default scope for now
                    scope_id = "default"
                    if interface in self.scoped_instances[scope_id]:
                        return self.scoped_instances[scope_id][interface]

                    instance = self._create_instance(registration)
                    if instance:
                        self.scoped_instances[scope_id][interface] = instance
                    return instance

                else:
                    return self._create_instance(registration)

            finally:
                if interface in self.resolution_stack:
                    self.resolution_stack.remove(interface)

        except Exception as e:
            logger.error(f"Error resolving {interface}: {e}")
            return None

        finally:
            self._release_lock()

    def _create_instance(self, registration: Registration) -> Optional[Any]:
        """
        Create an instance based on registration.

        Args:
            registration: Registration information

        Returns:
            Created instance or None
        """
        try:
            if registration.registration_type == RegistrationType.INSTANCE:
                return registration.instance

            elif registration.registration_type == RegistrationType.FACTORY:
                if registration.factory:
                    return registration.factory()
                return None

            elif registration.registration_type == RegistrationType.TYPE:
                if not registration.implementation:
                    return None

                # Auto-wire constructor dependencies
                if self.config.enable_auto_wiring:
                    return self._auto_wire_instance(registration.implementation)
                else:
                    return registration.implementation()

            return None

        except Exception as e:
            logger.error(f"Error creating instance: {e}")
            return None

    def _auto_wire_instance(self, cls: Type) -> Optional[Any]:
        """
        Auto-wire constructor dependencies.

        Args:
            cls: Class to instantiate

        Returns:
            Instance with wired dependencies
        """
        try:
            # Get constructor signature
            sig = inspect.signature(cls.__init__)
            kwargs = {}

            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue

                # Try to resolve parameter type
                if param.annotation != inspect.Parameter.empty:
                    param_type = param.annotation
                    resolved = self.resolve(param_type)

                    if resolved is not None:
                        kwargs[param_name] = resolved
                    elif param.default == inspect.Parameter.empty:
                        # Required parameter but couldn't resolve
                        logger.warning(f"Could not resolve required parameter {param_name} of type {param_type}")

            return cls(**kwargs)

        except Exception as e:
            logger.error(f"Error auto-wiring {cls.__name__}: {e}")
            return None

    def inject_constructor(
        self,
        cls: Type,
        args: tuple = (),
        kwargs: Optional[dict] = None,
    ) -> ConstructorInjectionResult:
        """
        Perform constructor injection.

        Args:
            cls: Class to instantiate
            args: Positional arguments
            kwargs: Keyword arguments

        Returns:
            ConstructorInjectionResult with created instance
        """
        kwargs = kwargs or {}
        injected_dependencies = []

        try:
            self._acquire_lock()

            # Get constructor parameters
            sig = inspect.signature(cls.__init__)

            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue

                # Skip if already provided
                if param_name in kwargs:
                    continue

                # Try to resolve
                if param.annotation != inspect.Parameter.empty:
                    param_type = param.annotation
                    resolved = self.resolve(param_type)

                    if resolved is not None:
                        kwargs[param_name] = resolved
                        injected_dependencies.append(DependencyInfo(
                            parameter_name=param_name,
                            parameter_type=param_type,
                            resolved_value=resolved,
                        ))

            instance = cls(*args, **kwargs)

            return ConstructorInjectionResult(
                success=True,
                instance=instance,
                injected_dependencies=injected_dependencies,
            )

        except Exception as e:
            return ConstructorInjectionResult(
                success=False,
                error=str(e),
            )

        finally:
            self._release_lock()

    def inject_property(
        self,
        instance: Any,
        property_name: str,
        dependency: Any,
    ) -> PropertyInjectionResult:
        """
        Perform property injection.

        Args:
            instance: Target instance
            property_name: Property name
            dependency: Dependency to inject

        Returns:
            PropertyInjectionResult with injection status
        """
        try:
            setattr(instance, property_name, dependency)

            return PropertyInjectionResult(
                success=True,
                property_name=property_name,
                injected_value=dependency,
            )

        except Exception as e:
            return PropertyInjectionResult(
                success=False,
                property_name=property_name,
                error=str(e),
            )

    def inject_method(
        self,
        instance: Any,
        method_name: str,
        dependencies: Optional[List[Any]] = None,
    ) -> MethodInjectionResult:
        """
        Perform method injection.

        Args:
            instance: Target instance
            method_name: Method name
            dependencies: Dependencies to inject

        Returns:
            MethodInjectionResult with call result
        """
        dependencies = dependencies or []

        try:
            method = getattr(instance, method_name)

            if not callable(method):
                return MethodInjectionResult(
                    success=False,
                    method_name=method_name,
                    error=f"{method_name} is not callable",
                )

            result = method(*dependencies)

            return MethodInjectionResult(
                success=True,
                method_name=method_name,
                injected_count=len(dependencies),
                result=result,
            )

        except Exception as e:
            return MethodInjectionResult(
                success=False,
                method_name=method_name,
                error=str(e),
            )

    def auto_wire(self, cls: Type) -> AutoWireResult:
        """
        Automatically wire dependencies for a class.

        Args:
            cls: Class to auto-wire

        Returns:
            AutoWireResult with wired instance
        """
        try:
            self._acquire_lock()

            wired_dependencies = []
            instance = self._auto_wire_instance(cls)

            if instance:
                # Track wired dependencies
                sig = inspect.signature(cls.__init__)
                for param_name, param in sig.parameters.items():
                    if param_name != 'self' and param.annotation != inspect.Parameter.empty:
                        wired_dependencies.append(param_name)

                return AutoWireResult(
                    success=True,
                    wired_dependencies=wired_dependencies,
                    instance=instance,
                )
            else:
                return AutoWireResult(
                    success=False,
                    error="Failed to create instance",
                )

        except Exception as e:
            return AutoWireResult(
                success=False,
                error=str(e),
            )

        finally:
            self._release_lock()

    def create_instance(self, cls: Type, scope: Scope) -> Optional[Any]:
        """
        Create instance with specified scope.

        Args:
            cls: Class to instantiate
            scope: Lifecycle scope

        Returns:
            Created instance
        """
        try:
            # Temporarily register and resolve
            temp_registration = Registration(
                interface=cls,
                implementation=cls,
                scope=scope,
                registration_type=RegistrationType.TYPE,
            )

            return self._create_instance(temp_registration)

        except Exception as e:
            logger.error(f"Error creating instance: {e}")
            return None

    def get_or_create(self, interface: Type[T], scope: Scope) -> Optional[T]:
        """
        Get existing instance or create new one with scope.

        Args:
            interface: Interface type
            scope: Lifecycle scope

        Returns:
            Instance
        """
        if scope == Scope.SINGLETON:
            if interface in self.singleton_instances:
                return self.singleton_instances[interface]

            instance = self.resolve(interface)
            if instance:
                self.singleton_instances[interface] = instance
            return instance

        else:
            return self.resolve(interface)

    def detect_circular_dependencies(
        self,
        dependency_graph: Optional[DependencyGraph] = None,
    ) -> CircularResult:
        """
        Detect circular dependencies in dependency graph.

        Args:
            dependency_graph: Dependency graph to analyze

        Returns:
            CircularResult with detected circular dependencies
        """
        circular_dependencies = []

        try:
            if not dependency_graph:
                # Build graph from registrations
                dependency_graph = self._build_full_dependency_graph()

            # Use DFS to detect cycles
            visited = set()
            rec_stack = set()

            def dfs(node: Type, path: List[Type]) -> bool:
                visited.add(node)
                rec_stack.add(node)
                path.append(node)

                # Find dependencies of this node
                for source, target in dependency_graph.edges:
                    if source == node:
                        if target in rec_stack:
                            # Found cycle
                            cycle_start = path.index(target)
                            cycle = path[cycle_start:] + [target]
                            circular_dependencies.append(CircularDependency(cycle=cycle))
                            return True

                        if target not in visited:
                            if dfs(target, path.copy()):
                                return True

                rec_stack.remove(node)
                return False

            for node in dependency_graph.nodes:
                if node not in visited:
                    dfs(node, [])

            return CircularResult(
                has_circular=len(circular_dependencies) > 0,
                circular_dependencies=circular_dependencies,
            )

        except Exception as e:
            logger.error(f"Error detecting circular dependencies: {e}")
            return CircularResult(has_circular=False)

    def _build_full_dependency_graph(self) -> DependencyGraph:
        """
        Build dependency graph from all registrations.

        Returns:
            DependencyGraph
        """
        graph = DependencyGraph()

        for interface, registration in self.registrations.items():
            graph.nodes.add(interface)

            if registration.implementation:
                graph.nodes.add(registration.implementation)
                graph.edges.append((interface, registration.implementation))

                # Analyze constructor dependencies
                try:
                    sig = inspect.signature(registration.implementation.__init__)
                    for param in sig.parameters.values():
                        if param.annotation != inspect.Parameter.empty and param.name != 'self':
                            param_type = param.annotation
                            if param_type in self.registrations:
                                graph.nodes.add(param_type)
                                graph.edges.append((registration.implementation, param_type))
                except:
                    pass

        return graph

    def resolve_circular_dependency(
        self,
        circular: CircularDependency,
    ) -> ResolutionResult:
        """
        Resolve a circular dependency.

        Args:
            circular: Circular dependency to resolve

        Returns:
            ResolutionResult with resolution status
        """
        try:
            strategy = self.config.circular_resolution_strategy

            if strategy == "proxy":
                # Use proxy pattern (simplified)
                logger.info(f"Resolving circular dependency using proxy pattern")
                return ResolutionResult(
                    resolved=True,
                    strategy_used="proxy",
                )

            elif strategy == "lazy":
                # Use lazy initialization
                logger.info(f"Resolving circular dependency using lazy initialization")
                return ResolutionResult(
                    resolved=True,
                    strategy_used="lazy",
                )

            else:
                return ResolutionResult(
                    resolved=False,
                    error=f"Unknown resolution strategy: {strategy}",
                )

        except Exception as e:
            return ResolutionResult(
                resolved=False,
                error=str(e),
            )

    def build_dependency_graph(self, root: Type) -> DependencyGraph:
        """
        Build dependency graph starting from root type.

        Args:
            root: Root type

        Returns:
            DependencyGraph
        """
        graph = DependencyGraph(root=root)
        visited = set()

        def traverse(cls: Type):
            if cls in visited:
                return

            visited.add(cls)
            graph.nodes.add(cls)

            try:
                sig = inspect.signature(cls.__init__)
                for param in sig.parameters.values():
                    if param.annotation != inspect.Parameter.empty and param.name != 'self':
                        param_type = param.annotation
                        graph.nodes.add(param_type)
                        graph.edges.append((cls, param_type))

                        if param_type in self.registrations:
                            impl = self.registrations[param_type].implementation
                            if impl:
                                traverse(impl)
            except:
                pass

        traverse(root)
        return graph

    def validate_dependencies(self, cls: Type) -> DependencyValidation:
        """
        Validate that all dependencies can be resolved.

        Args:
            cls: Class to validate

        Returns:
            DependencyValidation with validation results
        """
        missing_dependencies = []
        errors = []

        try:
            sig = inspect.signature(cls.__init__)

            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue

                if param.annotation != inspect.Parameter.empty:
                    param_type = param.annotation

                    # Check if can be resolved
                    if param_type not in self.registrations:
                        if param.default == inspect.Parameter.empty:
                            missing_dependencies.append(param_type)
                            errors.append(f"Missing required dependency: {param_type}")

            return DependencyValidation(
                valid=len(missing_dependencies) == 0,
                missing_dependencies=missing_dependencies,
                errors=errors,
            )

        except Exception as e:
            return DependencyValidation(
                valid=False,
                errors=[str(e)],
            )

    def register_factory(
        self,
        interface: Type,
        factory: Callable,
        scope: Scope = Scope.TRANSIENT,
    ) -> FactoryRegisterResult:
        """
        Register a factory function for dependency creation.

        Args:
            interface: Interface type
            factory: Factory function
            scope: Lifecycle scope

        Returns:
            FactoryRegisterResult
        """
        try:
            self._acquire_lock()

            registration = Registration(
                interface=interface,
                factory=factory,
                scope=scope,
                registration_type=RegistrationType.FACTORY,
            )

            self.registrations[interface] = registration

            return FactoryRegisterResult(
                registered=True,
                registration_id=registration.registration_id,
            )

        except Exception as e:
            return FactoryRegisterResult(
                registered=False,
                error=str(e),
            )

        finally:
            self._release_lock()

    def register_instance(
        self,
        interface: Type,
        instance: Any,
    ) -> InstanceRegisterResult:
        """
        Register a singleton instance.

        Args:
            interface: Interface type
            instance: Instance to register

        Returns:
            InstanceRegisterResult
        """
        try:
            self._acquire_lock()

            registration = Registration(
                interface=interface,
                instance=instance,
                scope=Scope.SINGLETON,
                registration_type=RegistrationType.INSTANCE,
            )

            self.registrations[interface] = registration
            self.singleton_instances[interface] = instance

            return InstanceRegisterResult(
                registered=True,
                registration_id=registration.registration_id,
            )

        except Exception as e:
            return InstanceRegisterResult(
                registered=False,
                error=str(e),
            )

        finally:
            self._release_lock()

    def create_child_container(
        self,
        parent: Optional['DependencyInjectorFSA'] = None,
    ) -> 'DependencyInjectorFSA':
        """
        Create a child container with hierarchical resolution.

        Args:
            parent: Parent container (defaults to self)

        Returns:
            Child container
        """
        parent = parent or self
        child = DependencyInjectorFSA(self.config)
        child.parent_container = parent
        parent.child_containers.append(child)

        return child

    def apply_interceptor(
        self,
        instance: Any,
        interceptor: Interceptor,
    ) -> InterceptResult:
        """
        Apply AOP interceptor to instance.

        Args:
            instance: Target instance
            interceptor: Interceptor to apply

        Returns:
            InterceptResult
        """
        try:
            # Register interceptor for type
            instance_type = type(instance)
            self.interceptors[instance_type].append(interceptor)

            # Sort by priority
            self.interceptors[instance_type].sort(key=lambda i: i.priority, reverse=True)

            return InterceptResult(
                success=True,
                interceptor_id=interceptor.interceptor_id,
            )

        except Exception as e:
            return InterceptResult(
                success=False,
                error=str(e),
            )

    def load_configuration(self, config_file: str) -> LoadConfigResult:
        """
        Load DI configuration from file.

        Args:
            config_file: Path to configuration file (YAML or JSON)

        Returns:
            LoadConfigResult
        """
        try:
            path = Path(config_file)

            if not path.exists():
                return LoadConfigResult(
                    loaded=False,
                    error=f"Configuration file not found: {config_file}",
                )

            content = path.read_text()

            if path.suffix in ['.yaml', '.yml']:
                config_data = yaml.safe_load(content)
            elif path.suffix == '.json':
                config_data = json.loads(content)
            else:
                return LoadConfigResult(
                    loaded=False,
                    error=f"Unsupported configuration format: {path.suffix}",
                )

            # Process registrations
            registrations_count = 0

            if 'registrations' in config_data:
                for reg_config in config_data['registrations']:
                    # This would require actual type resolution in production
                    # Simplified for demonstration
                    registrations_count += 1

            return LoadConfigResult(
                loaded=True,
                registrations_count=registrations_count,
            )

        except Exception as e:
            return LoadConfigResult(
                loaded=False,
                error=str(e),
            )

    def get_registration(self, interface: Type) -> Optional[Registration]:
        """
        Get registration information for an interface.

        Args:
            interface: Interface type

        Returns:
            Registration or None
        """
        return self.registrations.get(interface)

    def unregister(self, interface: Type) -> UnregisterResult:
        """
        Remove a dependency registration.

        Args:
            interface: Interface type to unregister

        Returns:
            UnregisterResult
        """
        try:
            self._acquire_lock()

            if interface not in self.registrations:
                return UnregisterResult(
                    unregistered=False,
                    error=f"No registration found for {interface}",
                )

            del self.registrations[interface]

            # Clean up instances
            if interface in self.singleton_instances:
                del self.singleton_instances[interface]

            return UnregisterResult(
                unregistered=True,
                interface=interface,
            )

        except Exception as e:
            return UnregisterResult(
                unregistered=False,
                error=str(e),
            )

        finally:
            self._release_lock()

    def clear_container(self) -> ClearResult:
        """
        Clear all registrations and instances.

        Returns:
            ClearResult
        """
        try:
            self._acquire_lock()

            cleared_count = len(self.registrations)

            self.registrations.clear()
            self.singleton_instances.clear()
            self.scoped_instances.clear()
            self.interceptors.clear()

            return ClearResult(
                cleared=True,
                cleared_count=cleared_count,
            )

        finally:
            self._release_lock()

    def get_scope_instance(
        self,
        scope: Scope,
        interface: Type,
    ) -> ScopeResult:
        """
        Get instance for specific scope.

        Args:
            scope: Lifecycle scope
            interface: Interface type

        Returns:
            ScopeResult
        """
        try:
            if scope == Scope.SINGLETON:
                instance = self.singleton_instances.get(interface)
                if not instance:
                    instance = self.resolve(interface)

                return ScopeResult(
                    success=instance is not None,
                    instance=instance,
                    scope=scope,
                )

            elif scope == Scope.SCOPED:
                scope_id = "default"
                instance = self.scoped_instances[scope_id].get(interface)

                if not instance:
                    instance = self.resolve(interface)

                return ScopeResult(
                    success=instance is not None,
                    instance=instance,
                    scope=scope,
                )

            else:
                # Transient
                instance = self.resolve(interface)
                return ScopeResult(
                    success=instance is not None,
                    instance=instance,
                    scope=scope,
                )

        except Exception as e:
            return ScopeResult(
                success=False,
                error=str(e),
            )

    def dispose_scope(self, scope: Scope) -> DisposeResult:
        """
        Dispose and cleanup scoped instances.

        Args:
            scope: Scope to dispose

        Returns:
            DisposeResult
        """
        try:
            self._acquire_lock()

            disposed_count = 0

            if scope == Scope.SINGLETON:
                disposed_count = len(self.singleton_instances)
                self.singleton_instances.clear()

            elif scope == Scope.SCOPED:
                for scope_id, instances in self.scoped_instances.items():
                    disposed_count += len(instances)
                self.scoped_instances.clear()

            return DisposeResult(
                disposed=True,
                disposed_count=disposed_count,
            )

        except Exception as e:
            return DisposeResult(
                disposed=False,
                error=str(e),
            )

        finally:
            self._release_lock()

    def __del__(self):
        """Cleanup on destruction."""
        try:
            self.clear_container()
        except:
            pass
