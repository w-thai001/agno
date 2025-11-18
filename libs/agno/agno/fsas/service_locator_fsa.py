"""
Service Locator FSA - Service location and discovery system.

This module provides a comprehensive service locator pattern implementation with
support for service registration, dynamic lookup, lazy initialization, caching,
plugin architecture, and service discovery.
"""

import importlib
import importlib.util
import inspect
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Type, TypeVar
from uuid import uuid4

try:
    from agno.utils.log import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


# ==================== Enums and Constants ====================

class ServiceScope(Enum):
    """Service lifecycle scopes."""
    SINGLETON = "singleton"  # Single instance shared
    TRANSIENT = "transient"  # New instance each time


class ServiceStatus(Enum):
    """Service registration status."""
    REGISTERED = "registered"
    ACTIVE = "active"
    CACHED = "cached"
    UNREGISTERED = "unregistered"
    ERROR = "error"


class PluginStatus(Enum):
    """Plugin loading status."""
    LOADED = "loaded"
    UNLOADED = "unloaded"
    ERROR = "error"


# ==================== Data Classes ====================

@dataclass
class ServiceMetadata:
    """Service metadata information."""
    service_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    service_type: Optional[Type] = None
    version: str = "1.0.0"
    dependencies: List[str] = field(default_factory=list)
    description: str = ""
    registered_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)


@dataclass
class ServiceRegistration:
    """Service registration information."""
    registration_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    service_type: Optional[Type] = None
    factory: Optional[Callable] = None
    instance: Optional[Any] = None
    scope: ServiceScope = ServiceScope.TRANSIENT
    metadata: Optional[ServiceMetadata] = None
    status: ServiceStatus = ServiceStatus.REGISTERED


@dataclass
class PluginInfo:
    """Plugin information."""
    plugin_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    path: str = ""
    module: Optional[Any] = None
    services: List[str] = field(default_factory=list)
    status: PluginStatus = PluginStatus.LOADED
    loaded_at: datetime = field(default_factory=datetime.now)


@dataclass
class ServiceInfo:
    """Service information summary."""
    name: str
    service_type: str
    scope: ServiceScope
    status: ServiceStatus
    version: str = "1.0.0"


@dataclass
class LocatorOp:
    """Service locator operation."""
    operation: str
    service_name: Optional[str] = None
    service_type: Optional[Type] = None
    factory: Optional[Callable] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LocatorResult:
    """Service locator pipeline result."""
    success: bool
    operations_count: int = 0
    services_affected: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    execution_time: float = 0.0


@dataclass
class ValidationResult:
    """Configuration validation result."""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class RegisterResult:
    """Service registration result."""
    registered: bool
    registration_id: str = ""
    service_name: str = ""
    error: Optional[str] = None


@dataclass
class LocateResult:
    """Service location result."""
    found: bool
    service: Optional[Any] = None
    service_name: str = ""
    error: Optional[str] = None


@dataclass
class ResolveResult:
    """Service resolution result."""
    resolved: bool
    service: Optional[Any] = None
    from_cache: bool = False
    error: Optional[str] = None


@dataclass
class CreateResult:
    """Service creation result."""
    created: bool
    service: Optional[Any] = None
    error: Optional[str] = None


@dataclass
class CacheResult:
    """Service caching result."""
    cached: bool
    service_name: str = ""
    error: Optional[str] = None


@dataclass
class InvalidateResult:
    """Cache invalidation result."""
    invalidated: bool
    service_name: str = ""
    error: Optional[str] = None


@dataclass
class DiscoveryResult:
    """Service discovery result."""
    discovered: bool
    services_found: List[str] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class PluginLoadResult:
    """Plugin loading result."""
    loaded: bool
    plugin_name: str = ""
    services_registered: int = 0
    error: Optional[str] = None


@dataclass
class PluginUnloadResult:
    """Plugin unloading result."""
    unloaded: bool
    plugin_name: str = ""
    services_unregistered: int = 0
    error: Optional[str] = None


@dataclass
class VersionResult:
    """Version setting result."""
    success: bool
    service_name: str = ""
    version: str = ""
    error: Optional[str] = None


@dataclass
class UnregisterResult:
    """Service unregistration result."""
    unregistered: bool
    service_name: str = ""
    error: Optional[str] = None


@dataclass
class ClearResult:
    """Registry clearing result."""
    cleared: bool
    cleared_count: int = 0


@dataclass
class AvailabilityResult:
    """Service availability result."""
    available: bool
    service_name: str = ""
    status: Optional[ServiceStatus] = None


@dataclass
class DependencyList:
    """Service dependencies."""
    service_name: str
    dependencies: List[str] = field(default_factory=list)
    resolved: bool = True


@dataclass
class FactoryRegisterResult:
    """Factory registration result."""
    registered: bool
    service_name: str = ""
    singleton: bool = False
    error: Optional[str] = None


@dataclass
class OverrideResult:
    """Service override result."""
    overridden: bool
    service_name: str = ""
    error: Optional[str] = None


@dataclass
class CloneResult:
    """Service cloning result."""
    cloned: bool
    source: str = ""
    target: str = ""
    error: Optional[str] = None


@dataclass
class LocatorConfig:
    """Service Locator configuration."""
    enable_caching: bool = True
    enable_lazy_loading: bool = True
    enable_plugins: bool = True
    enable_discovery: bool = True
    thread_safe: bool = True
    cache_singletons: bool = True
    allow_override: bool = True
    validate_on_registration: bool = True
    max_cache_size: int = 1000


# ==================== Type Variable ====================

T = TypeVar('T')


# ==================== Main FSA Class ====================

class ServiceLocatorFSA:
    """
    Service Locator Finite State Automaton.

    Provides service location and discovery with support for registration,
    dynamic lookup, lazy initialization, caching, and plugin architecture.
    """

    def __init__(self, config: Optional[LocatorConfig] = None):
        """
        Initialize the service locator.

        Args:
            config: Locator configuration
        """
        self.config = config or LocatorConfig()
        self.fsa_id = str(uuid4())

        # Thread safety
        self._lock = threading.RLock() if self.config.thread_safe else None

        # Service registry
        self.services: Dict[str, ServiceRegistration] = {}
        self.service_cache: Dict[str, Any] = {}
        self.type_registry: Dict[Type, Set[str]] = defaultdict(set)

        # Plugin management
        self.plugins: Dict[str, PluginInfo] = {}

        # Service metadata
        self.metadata_store: Dict[str, ServiceMetadata] = {}

        logger.info(f"Initialized ServiceLocatorFSA {self.fsa_id}")

    def _acquire_lock(self):
        """Acquire thread lock if enabled."""
        if self._lock:
            self._lock.acquire()

    def _release_lock(self):
        """Release thread lock if enabled."""
        if self._lock:
            self._lock.release()

    def execute(self, locator_ops: List[LocatorOp]) -> LocatorResult:
        """
        Execute service locator pipeline.

        Args:
            locator_ops: List of locator operations

        Returns:
            LocatorResult with execution status
        """
        start_time = datetime.now()
        operations_count = 0
        services_affected = []
        errors = []

        try:
            self._acquire_lock()

            for op in locator_ops:
                try:
                    if op.operation == "register" and op.service_name and op.factory:
                        result = self.register_service(
                            op.service_name,
                            op.service_type or type(None),
                            op.factory
                        )
                        if result.registered:
                            operations_count += 1
                            services_affected.append(op.service_name)

                    elif op.operation == "get" and op.service_name:
                        service = self.get_service(op.service_name)
                        if service:
                            operations_count += 1
                            services_affected.append(op.service_name)

                    elif op.operation == "locate" and op.service_type:
                        result = self.locate_service(op.service_type)
                        if result.found:
                            operations_count += 1

                except Exception as e:
                    errors.append(f"Error in operation {op.operation}: {str(e)}")

            execution_time = (datetime.now() - start_time).total_seconds()

            return LocatorResult(
                success=len(errors) == 0,
                operations_count=operations_count,
                services_affected=services_affected,
                errors=errors,
                execution_time=execution_time,
            )

        finally:
            self._release_lock()

    def validate(self, locator_config: LocatorConfig) -> ValidationResult:
        """
        Validate locator configuration.

        Args:
            locator_config: Configuration to validate

        Returns:
            ValidationResult with validation status
        """
        errors = []
        warnings = []

        # Validate cache size
        if locator_config.max_cache_size < 0:
            errors.append("max_cache_size must be non-negative")

        # Warnings
        if not locator_config.thread_safe:
            warnings.append("Thread safety is disabled")

        if not locator_config.enable_caching:
            warnings.append("Service caching is disabled")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def register_service(
        self,
        name: str,
        service_type: Type,
        factory: Callable,
        scope: ServiceScope = ServiceScope.TRANSIENT,
    ) -> RegisterResult:
        """
        Register a service with the locator.

        Args:
            name: Service name
            service_type: Service type
            factory: Factory function to create service
            scope: Service scope

        Returns:
            RegisterResult with registration status
        """
        try:
            self._acquire_lock()

            # Check for duplicate registration
            if name in self.services and not self.config.allow_override:
                return RegisterResult(
                    registered=False,
                    error=f"Service {name} already registered",
                )

            # Validate factory
            if self.config.validate_on_registration and not callable(factory):
                return RegisterResult(
                    registered=False,
                    error="Factory must be callable",
                )

            # Create metadata
            metadata = ServiceMetadata(
                name=name,
                service_type=service_type,
            )

            # Create registration
            registration = ServiceRegistration(
                name=name,
                service_type=service_type,
                factory=factory,
                scope=scope,
                metadata=metadata,
                status=ServiceStatus.REGISTERED,
            )

            self.services[name] = registration
            self.metadata_store[name] = metadata
            self.type_registry[service_type].add(name)

            logger.info(f"Registered service: {name} with scope {scope.value}")

            return RegisterResult(
                registered=True,
                registration_id=registration.registration_id,
                service_name=name,
            )

        except Exception as e:
            return RegisterResult(
                registered=False,
                error=str(e),
            )

        finally:
            self._release_lock()

    def get_service(self, name: str) -> Optional[Any]:
        """
        Get a service instance by name.

        Args:
            name: Service name

        Returns:
            Service instance or None
        """
        try:
            self._acquire_lock()

            if name not in self.services:
                logger.error(f"Service not found: {name}")
                return None

            registration = self.services[name]

            # Check cache for singletons
            if registration.scope == ServiceScope.SINGLETON:
                if name in self.service_cache:
                    logger.debug(f"Returning cached service: {name}")
                    return self.service_cache[name]

            # Create instance
            if registration.instance:
                return registration.instance

            if registration.factory:
                instance = registration.factory()

                # Cache singleton
                if registration.scope == ServiceScope.SINGLETON and self.config.enable_caching:
                    self.service_cache[name] = instance
                    registration.status = ServiceStatus.CACHED

                registration.status = ServiceStatus.ACTIVE
                return instance

            return None

        except Exception as e:
            logger.error(f"Error getting service {name}: {e}")
            return None

        finally:
            self._release_lock()

    def locate_service(self, interface: Type[T]) -> LocateResult:
        """
        Locate a service by interface type.

        Args:
            interface: Service interface type

        Returns:
            LocateResult with located service
        """
        try:
            self._acquire_lock()

            # Find services implementing the interface
            service_names = self.type_registry.get(interface, set())

            if not service_names:
                return LocateResult(
                    found=False,
                    error=f"No service found for interface {interface}",
                )

            # Get first matching service
            service_name = next(iter(service_names))
            service = self.get_service(service_name)

            if service:
                return LocateResult(
                    found=True,
                    service=service,
                    service_name=service_name,
                )
            else:
                return LocateResult(
                    found=False,
                    error=f"Failed to get service {service_name}",
                )

        except Exception as e:
            return LocateResult(
                found=False,
                error=str(e),
            )

        finally:
            self._release_lock()

    def resolve_service(
        self,
        name: str,
        lazy: bool = False,
    ) -> ResolveResult:
        """
        Resolve a service with lazy loading option.

        Args:
            name: Service name
            lazy: Whether to use lazy loading

        Returns:
            ResolveResult with resolved service
        """
        try:
            self._acquire_lock()

            if name not in self.services:
                return ResolveResult(
                    resolved=False,
                    error=f"Service not found: {name}",
                )

            # Check cache first
            if name in self.service_cache:
                return ResolveResult(
                    resolved=True,
                    service=self.service_cache[name],
                    from_cache=True,
                )

            # Lazy loading
            if lazy and self.config.enable_lazy_loading:
                # Return a lazy proxy (simplified - just return factory)
                registration = self.services[name]
                return ResolveResult(
                    resolved=True,
                    service=registration.factory,
                    from_cache=False,
                )

            # Eager loading
            service = self.get_service(name)

            if service:
                return ResolveResult(
                    resolved=True,
                    service=service,
                    from_cache=False,
                )
            else:
                return ResolveResult(
                    resolved=False,
                    error=f"Failed to resolve service: {name}",
                )

        except Exception as e:
            return ResolveResult(
                resolved=False,
                error=str(e),
            )

        finally:
            self._release_lock()

    def create_service(
        self,
        name: str,
        factory: Callable,
    ) -> CreateResult:
        """
        Create a service instance using a factory.

        Args:
            name: Service name
            factory: Factory function

        Returns:
            CreateResult with created service
        """
        try:
            if not callable(factory):
                return CreateResult(
                    created=False,
                    error="Factory must be callable",
                )

            service = factory()

            return CreateResult(
                created=True,
                service=service,
            )

        except Exception as e:
            return CreateResult(
                created=False,
                error=str(e),
            )

    def cache_service(
        self,
        name: str,
        instance: Any,
    ) -> CacheResult:
        """
        Cache a service instance.

        Args:
            name: Service name
            instance: Service instance

        Returns:
            CacheResult with caching status
        """
        try:
            self._acquire_lock()

            if not self.config.enable_caching:
                return CacheResult(
                    cached=False,
                    error="Caching is disabled",
                )

            # Check cache size limit
            if len(self.service_cache) >= self.config.max_cache_size:
                return CacheResult(
                    cached=False,
                    error="Cache size limit reached",
                )

            self.service_cache[name] = instance

            if name in self.services:
                self.services[name].status = ServiceStatus.CACHED

            return CacheResult(
                cached=True,
                service_name=name,
            )

        except Exception as e:
            return CacheResult(
                cached=False,
                error=str(e),
            )

        finally:
            self._release_lock()

    def invalidate_cache(self, name: str) -> InvalidateResult:
        """
        Invalidate cached service.

        Args:
            name: Service name

        Returns:
            InvalidateResult with invalidation status
        """
        try:
            self._acquire_lock()

            if name not in self.service_cache:
                return InvalidateResult(
                    invalidated=False,
                    error=f"Service {name} not in cache",
                )

            del self.service_cache[name]

            if name in self.services:
                self.services[name].status = ServiceStatus.REGISTERED

            return InvalidateResult(
                invalidated=True,
                service_name=name,
            )

        except Exception as e:
            return InvalidateResult(
                invalidated=False,
                error=str(e),
            )

        finally:
            self._release_lock()

    def discover_services(self, package: str) -> DiscoveryResult:
        """
        Auto-discover services in a package.

        Args:
            package: Package name to scan

        Returns:
            DiscoveryResult with discovered services
        """
        try:
            if not self.config.enable_discovery:
                return DiscoveryResult(
                    discovered=False,
                    error="Service discovery is disabled",
                )

            services_found = []

            try:
                # Try to import package
                module = importlib.import_module(package)

                # Scan for service classes/functions
                for name, obj in inspect.getmembers(module):
                    if inspect.isclass(obj) or inspect.isfunction(obj):
                        # Check for service marker (simplified)
                        if hasattr(obj, '__service__'):
                            service_name = getattr(obj, '__service_name__', name)
                            services_found.append(service_name)

            except ImportError as e:
                return DiscoveryResult(
                    discovered=False,
                    error=f"Failed to import package: {str(e)}",
                )

            return DiscoveryResult(
                discovered=True,
                services_found=services_found,
            )

        except Exception as e:
            return DiscoveryResult(
                discovered=False,
                error=str(e),
            )

    def load_plugin(self, plugin_path: str) -> PluginLoadResult:
        """
        Load a service plugin.

        Args:
            plugin_path: Path to plugin file

        Returns:
            PluginLoadResult with loading status
        """
        try:
            self._acquire_lock()

            if not self.config.enable_plugins:
                return PluginLoadResult(
                    loaded=False,
                    error="Plugins are disabled",
                )

            path = Path(plugin_path)

            if not path.exists():
                return PluginLoadResult(
                    loaded=False,
                    error=f"Plugin file not found: {plugin_path}",
                )

            # Load module
            spec = importlib.util.spec_from_file_location(path.stem, plugin_path)
            if not spec or not spec.loader:
                return PluginLoadResult(
                    loaded=False,
                    error="Failed to load plugin spec",
                )

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Register plugin
            plugin_info = PluginInfo(
                name=path.stem,
                path=plugin_path,
                module=module,
                status=PluginStatus.LOADED,
            )

            # Auto-register services from plugin
            services_registered = 0
            if hasattr(module, 'register_services'):
                module.register_services(self)
                services_registered = len(plugin_info.services)

            self.plugins[path.stem] = plugin_info

            logger.info(f"Loaded plugin: {path.stem}")

            return PluginLoadResult(
                loaded=True,
                plugin_name=path.stem,
                services_registered=services_registered,
            )

        except Exception as e:
            return PluginLoadResult(
                loaded=False,
                error=str(e),
            )

        finally:
            self._release_lock()

    def unload_plugin(self, plugin_name: str) -> PluginUnloadResult:
        """
        Unload a service plugin.

        Args:
            plugin_name: Plugin name

        Returns:
            PluginUnloadResult with unloading status
        """
        try:
            self._acquire_lock()

            if plugin_name not in self.plugins:
                return PluginUnloadResult(
                    unloaded=False,
                    error=f"Plugin not found: {plugin_name}",
                )

            plugin = self.plugins[plugin_name]

            # Unregister plugin services
            services_unregistered = 0
            for service_name in plugin.services:
                if service_name in self.services:
                    self.unregister_service(service_name)
                    services_unregistered += 1

            plugin.status = PluginStatus.UNLOADED
            del self.plugins[plugin_name]

            return PluginUnloadResult(
                unloaded=True,
                plugin_name=plugin_name,
                services_unregistered=services_unregistered,
            )

        except Exception as e:
            return PluginUnloadResult(
                unloaded=False,
                error=str(e),
            )

        finally:
            self._release_lock()

    def get_service_metadata(self, name: str) -> Optional[ServiceMetadata]:
        """
        Get service metadata.

        Args:
            name: Service name

        Returns:
            ServiceMetadata or None
        """
        return self.metadata_store.get(name)

    def set_service_version(
        self,
        name: str,
        version: str,
    ) -> VersionResult:
        """
        Set service version.

        Args:
            name: Service name
            version: Version string

        Returns:
            VersionResult with status
        """
        try:
            self._acquire_lock()

            if name not in self.metadata_store:
                return VersionResult(
                    success=False,
                    error=f"Service metadata not found: {name}",
                )

            self.metadata_store[name].version = version

            return VersionResult(
                success=True,
                service_name=name,
                version=version,
            )

        except Exception as e:
            return VersionResult(
                success=False,
                error=str(e),
            )

        finally:
            self._release_lock()

    def get_all_services(self) -> List[ServiceInfo]:
        """
        Get all registered services.

        Returns:
            List of ServiceInfo
        """
        try:
            self._acquire_lock()

            services = []

            for name, registration in self.services.items():
                service_info = ServiceInfo(
                    name=name,
                    service_type=registration.service_type.__name__ if registration.service_type else "Unknown",
                    scope=registration.scope,
                    status=registration.status,
                    version=registration.metadata.version if registration.metadata else "1.0.0",
                )
                services.append(service_info)

            return services

        finally:
            self._release_lock()

    def unregister_service(self, name: str) -> UnregisterResult:
        """
        Unregister a service.

        Args:
            name: Service name

        Returns:
            UnregisterResult with status
        """
        try:
            self._acquire_lock()

            if name not in self.services:
                return UnregisterResult(
                    unregistered=False,
                    error=f"Service not found: {name}",
                )

            registration = self.services[name]

            # Remove from type registry
            if registration.service_type:
                self.type_registry[registration.service_type].discard(name)

            # Remove from cache
            if name in self.service_cache:
                del self.service_cache[name]

            # Remove metadata
            if name in self.metadata_store:
                del self.metadata_store[name]

            # Remove registration
            del self.services[name]

            logger.info(f"Unregistered service: {name}")

            return UnregisterResult(
                unregistered=True,
                service_name=name,
            )

        except Exception as e:
            return UnregisterResult(
                unregistered=False,
                error=str(e),
            )

        finally:
            self._release_lock()

    def clear_registry(self) -> ClearResult:
        """
        Clear all service registrations.

        Returns:
            ClearResult with status
        """
        try:
            self._acquire_lock()

            cleared_count = len(self.services)

            self.services.clear()
            self.service_cache.clear()
            self.type_registry.clear()
            self.metadata_store.clear()

            return ClearResult(
                cleared=True,
                cleared_count=cleared_count,
            )

        finally:
            self._release_lock()

    def check_service_availability(self, name: str) -> AvailabilityResult:
        """
        Check if a service is available.

        Args:
            name: Service name

        Returns:
            AvailabilityResult with availability status
        """
        try:
            self._acquire_lock()

            if name not in self.services:
                return AvailabilityResult(
                    available=False,
                    service_name=name,
                )

            registration = self.services[name]

            return AvailabilityResult(
                available=True,
                service_name=name,
                status=registration.status,
            )

        finally:
            self._release_lock()

    def get_service_dependencies(self, name: str) -> DependencyList:
        """
        Get service dependencies.

        Args:
            name: Service name

        Returns:
            DependencyList with dependencies
        """
        try:
            self._acquire_lock()

            if name not in self.metadata_store:
                return DependencyList(
                    service_name=name,
                    dependencies=[],
                    resolved=False,
                )

            metadata = self.metadata_store[name]

            return DependencyList(
                service_name=name,
                dependencies=metadata.dependencies,
                resolved=True,
            )

        finally:
            self._release_lock()

    def register_service_factory(
        self,
        name: str,
        factory: Callable,
        singleton: bool = False,
    ) -> FactoryRegisterResult:
        """
        Register a service factory.

        Args:
            name: Service name
            factory: Factory function
            singleton: Whether to use singleton scope

        Returns:
            FactoryRegisterResult with status
        """
        scope = ServiceScope.SINGLETON if singleton else ServiceScope.TRANSIENT

        result = self.register_service(
            name=name,
            service_type=type(None),
            factory=factory,
            scope=scope,
        )

        return FactoryRegisterResult(
            registered=result.registered,
            service_name=name,
            singleton=singleton,
            error=result.error,
        )

    def override_service(
        self,
        name: str,
        new_factory: Callable,
    ) -> OverrideResult:
        """
        Override an existing service.

        Args:
            name: Service name
            new_factory: New factory function

        Returns:
            OverrideResult with status
        """
        try:
            self._acquire_lock()

            if not self.config.allow_override:
                return OverrideResult(
                    overridden=False,
                    error="Service override is disabled",
                )

            if name not in self.services:
                return OverrideResult(
                    overridden=False,
                    error=f"Service not found: {name}",
                )

            # Update factory
            self.services[name].factory = new_factory

            # Invalidate cache
            if name in self.service_cache:
                del self.service_cache[name]

            return OverrideResult(
                overridden=True,
                service_name=name,
            )

        except Exception as e:
            return OverrideResult(
                overridden=False,
                error=str(e),
            )

        finally:
            self._release_lock()

    def clone_service(
        self,
        source: str,
        target: str,
    ) -> CloneResult:
        """
        Clone a service registration.

        Args:
            source: Source service name
            target: Target service name

        Returns:
            CloneResult with status
        """
        try:
            self._acquire_lock()

            if source not in self.services:
                return CloneResult(
                    cloned=False,
                    error=f"Source service not found: {source}",
                )

            if target in self.services and not self.config.allow_override:
                return CloneResult(
                    cloned=False,
                    error=f"Target service already exists: {target}",
                )

            source_reg = self.services[source]

            # Clone registration
            cloned_reg = ServiceRegistration(
                name=target,
                service_type=source_reg.service_type,
                factory=source_reg.factory,
                scope=source_reg.scope,
                metadata=ServiceMetadata(
                    name=target,
                    service_type=source_reg.service_type,
                    version=source_reg.metadata.version if source_reg.metadata else "1.0.0",
                ),
                status=ServiceStatus.REGISTERED,
            )

            self.services[target] = cloned_reg
            self.metadata_store[target] = cloned_reg.metadata

            if source_reg.service_type:
                self.type_registry[source_reg.service_type].add(target)

            return CloneResult(
                cloned=True,
                source=source,
                target=target,
            )

        except Exception as e:
            return CloneResult(
                cloned=False,
                error=str(e),
            )

        finally:
            self._release_lock()

    def __del__(self):
        """Cleanup on destruction."""
        try:
            self.clear_registry()
        except:
            pass
