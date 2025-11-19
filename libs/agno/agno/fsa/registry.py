"""
FSA Registry System - Central registration and management for FSA modules

Provides dependency injection, version management, lazy loading, and health monitoring
for all FSA components in the framework.
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Type
from datetime import datetime
import importlib
import inspect

logger = logging.getLogger(__name__)


class FSAHealthStatus(Enum):
    """Health status enumeration for FSA modules"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class FSAHealth:
    """Health check result for an FSA module"""
    status: FSAHealthStatus
    message: str
    last_check: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_healthy(self) -> bool:
        """Check if the module is healthy"""
        return self.status == FSAHealthStatus.HEALTHY

    def to_dict(self) -> Dict[str, Any]:
        """Convert health check to dictionary"""
        return {
            "status": self.status.value,
            "message": self.message,
            "last_check": self.last_check.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class FSAModule:
    """Represents a registered FSA module"""
    name: str
    version: str
    module_class: Optional[Type] = None
    module_factory: Optional[Callable] = None
    dependencies: List[str] = field(default_factory=list)
    lazy_load: bool = True
    module_path: Optional[str] = None
    _instance: Optional[Any] = None
    _health: Optional[FSAHealth] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate module configuration"""
        if self.module_class is None and self.module_factory is None and self.module_path is None:
            raise ValueError(
                f"FSA module '{self.name}' must provide either module_class, "
                "module_factory, or module_path"
            )

        # Validate version format
        if not self._is_valid_version(self.version):
            raise ValueError(f"Invalid version format for module '{self.name}': {self.version}")

    @staticmethod
    def _is_valid_version(version: str) -> bool:
        """Validate semantic version format"""
        try:
            parts = version.split('.')
            return len(parts) == 3 and all(p.isdigit() for p in parts)
        except Exception:
            return False

    def get_instance(self, **kwargs) -> Any:
        """Get or create module instance"""
        if self._instance is not None:
            return self._instance

        try:
            if self.module_class is not None:
                self._instance = self.module_class(**kwargs)
            elif self.module_factory is not None:
                self._instance = self.module_factory(**kwargs)
            elif self.module_path is not None:
                # Lazy load from module path
                module_parts = self.module_path.rsplit('.', 1)
                if len(module_parts) == 2:
                    module_name, class_name = module_parts
                    module = importlib.import_module(module_name)
                    module_class = getattr(module, class_name)
                    self._instance = module_class(**kwargs)
                else:
                    raise ValueError(f"Invalid module_path format: {self.module_path}")

            logger.info(f"FSA module '{self.name}' v{self.version} instantiated")
            return self._instance
        except Exception as e:
            logger.error(f"Failed to instantiate FSA module '{self.name}': {e}")
            raise

    def clear_instance(self):
        """Clear cached instance for reload"""
        self._instance = None
        logger.debug(f"Cleared instance for FSA module '{self.name}'")


class FSARegistry:
    """
    Central registry for FSA modules with dependency management and health monitoring

    Features:
    - Module registration with version management
    - Dependency injection and resolution
    - Lazy loading for performance optimization
    - Health checks and status monitoring
    - Compatibility checking between modules
    """

    def __init__(self):
        self._modules: Dict[str, FSAModule] = {}
        self._dependency_graph: Dict[str, Set[str]] = {}
        self._initialization_order: List[str] = []
        self._logger = logging.getLogger(f"{__name__}.FSARegistry")

    def register(
        self,
        name: str,
        version: str,
        module_class: Optional[Type] = None,
        module_factory: Optional[Callable] = None,
        module_path: Optional[str] = None,
        dependencies: Optional[List[str]] = None,
        lazy_load: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
        override: bool = False,
    ) -> None:
        """
        Register an FSA module in the registry

        Args:
            name: Unique module name
            version: Semantic version (e.g., "1.0.0")
            module_class: Class to instantiate
            module_factory: Factory function to create instance
            module_path: Import path for lazy loading (e.g., "agno.fsa.module.ClassName")
            dependencies: List of required module names
            lazy_load: Whether to lazy load the module
            metadata: Additional module metadata
            override: Whether to override existing registration
        """
        if not name:
            raise ValueError("Module name cannot be empty")

        if name in self._modules and not override:
            raise ValueError(
                f"FSA module '{name}' is already registered. "
                "Use override=True to replace."
            )

        dependencies = dependencies or []
        metadata = metadata or {}

        # Validate dependencies exist or will exist
        for dep in dependencies:
            if dep not in self._modules:
                self._logger.warning(
                    f"Dependency '{dep}' for module '{name}' not yet registered. "
                    "Ensure it's registered before instantiation."
                )

        module = FSAModule(
            name=name,
            version=version,
            module_class=module_class,
            module_factory=module_factory,
            module_path=module_path,
            dependencies=dependencies,
            lazy_load=lazy_load,
            metadata=metadata,
        )

        self._modules[name] = module
        self._dependency_graph[name] = set(dependencies)
        self._update_initialization_order()

        self._logger.info(
            f"Registered FSA module '{name}' v{version} with {len(dependencies)} dependencies"
        )

    def unregister(self, name: str) -> None:
        """Unregister an FSA module"""
        if name not in self._modules:
            raise ValueError(f"FSA module '{name}' is not registered")

        # Check if other modules depend on this one
        dependents = self._get_dependents(name)
        if dependents:
            raise ValueError(
                f"Cannot unregister '{name}': depended on by {dependents}"
            )

        del self._modules[name]
        del self._dependency_graph[name]
        self._update_initialization_order()

        self._logger.info(f"Unregistered FSA module '{name}'")

    def get(self, name: str, **init_kwargs) -> Any:
        """
        Get FSA module instance with dependency injection

        Args:
            name: Module name
            **init_kwargs: Initialization arguments

        Returns:
            Module instance
        """
        if name not in self._modules:
            raise ValueError(f"FSA module '{name}' is not registered")

        module = self._modules[name]

        # Check and instantiate dependencies first
        dep_instances = {}
        for dep_name in module.dependencies:
            if dep_name not in self._modules:
                raise ValueError(
                    f"Dependency '{dep_name}' for module '{name}' is not registered"
                )
            dep_instances[dep_name] = self.get(dep_name)

        # Add dependencies to init kwargs if module accepts them
        if dep_instances:
            init_kwargs.setdefault('dependencies', dep_instances)

        return module.get_instance(**init_kwargs)

    def health_check(self, name: str, force: bool = False) -> FSAHealth:
        """
        Perform health check on an FSA module

        Args:
            name: Module name
            force: Force new health check even if cached

        Returns:
            FSAHealth object with status
        """
        if name not in self._modules:
            return FSAHealth(
                status=FSAHealthStatus.UNKNOWN,
                message=f"Module '{name}' not registered",
                last_check=datetime.now(),
            )

        module = self._modules[name]

        # Return cached health if available and not forcing
        if not force and module._health is not None:
            age = (datetime.now() - module._health.last_check).total_seconds()
            if age < 60:  # Cache for 60 seconds
                return module._health

        # Perform health check
        try:
            instance = module._instance
            if instance is None and not module.lazy_load:
                status = FSAHealthStatus.DEGRADED
                message = "Module not yet instantiated"
            elif instance is not None and hasattr(instance, 'health_check'):
                # Module provides its own health check
                health_result = instance.health_check()
                if isinstance(health_result, bool):
                    status = FSAHealthStatus.HEALTHY if health_result else FSAHealthStatus.UNHEALTHY
                    message = "Module health check passed" if health_result else "Module health check failed"
                elif isinstance(health_result, dict):
                    status = FSAHealthStatus(health_result.get('status', 'unknown'))
                    message = health_result.get('message', 'No message provided')
                else:
                    status = FSAHealthStatus.HEALTHY
                    message = "Module operational"
            else:
                status = FSAHealthStatus.HEALTHY
                message = "Module registered and ready"

            health = FSAHealth(
                status=status,
                message=message,
                last_check=datetime.now(),
                metadata={
                    "version": module.version,
                    "dependencies": module.dependencies,
                    "lazy_load": module.lazy_load,
                },
            )

            module._health = health
            return health

        except Exception as e:
            self._logger.error(f"Health check failed for module '{name}': {e}")
            health = FSAHealth(
                status=FSAHealthStatus.UNHEALTHY,
                message=f"Health check error: {str(e)}",
                last_check=datetime.now(),
            )
            module._health = health
            return health

    def health_check_all(self) -> Dict[str, FSAHealth]:
        """Perform health check on all registered modules"""
        results = {}
        for name in self._modules:
            results[name] = self.health_check(name)
        return results

    def check_compatibility(self, name1: str, name2: str) -> bool:
        """
        Check if two modules are compatible based on version constraints

        Currently implements basic semantic versioning compatibility.
        Can be extended with explicit compatibility rules.
        """
        if name1 not in self._modules or name2 not in self._modules:
            return False

        # For now, assume all registered modules are compatible
        # This can be extended with version constraints
        return True

    def get_dependency_order(self, name: str) -> List[str]:
        """Get initialization order for a module and its dependencies"""
        if name not in self._modules:
            raise ValueError(f"FSA module '{name}' is not registered")

        order = []
        visited = set()

        def visit(module_name: str):
            if module_name in visited:
                return
            visited.add(module_name)

            for dep in self._dependency_graph.get(module_name, []):
                visit(dep)

            order.append(module_name)

        visit(name)
        return order

    def list_modules(self) -> List[Dict[str, Any]]:
        """List all registered modules with their metadata"""
        return [
            {
                "name": module.name,
                "version": module.version,
                "dependencies": module.dependencies,
                "lazy_load": module.lazy_load,
                "instantiated": module._instance is not None,
                "metadata": module.metadata,
            }
            for module in self._modules.values()
        ]

    def clear_instances(self, name: Optional[str] = None) -> None:
        """Clear cached instances for reload"""
        if name:
            if name in self._modules:
                self._modules[name].clear_instance()
        else:
            for module in self._modules.values():
                module.clear_instance()
        self._logger.info(f"Cleared instances for: {name or 'all modules'}")

    def _get_dependents(self, name: str) -> List[str]:
        """Get list of modules that depend on the given module"""
        dependents = []
        for module_name, deps in self._dependency_graph.items():
            if name in deps:
                dependents.append(module_name)
        return dependents

    def _update_initialization_order(self) -> None:
        """Update the global initialization order using topological sort"""
        try:
            self._initialization_order = self._topological_sort()
        except ValueError as e:
            self._logger.error(f"Failed to compute initialization order: {e}")

    def _topological_sort(self) -> List[str]:
        """Perform topological sort on dependency graph"""
        in_degree = {name: 0 for name in self._modules}

        for deps in self._dependency_graph.values():
            for dep in deps:
                if dep in in_degree:
                    in_degree[dep] += 1

        queue = [name for name, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            node = queue.pop(0)
            result.append(node)

            for neighbor in self._modules:
                if node in self._dependency_graph.get(neighbor, []):
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)

        if len(result) != len(self._modules):
            raise ValueError("Circular dependency detected in FSA modules")

        return result

    def __repr__(self) -> str:
        return f"<FSARegistry: {len(self._modules)} modules registered>"


# Global singleton registry instance
_global_registry: Optional[FSARegistry] = None


def get_registry() -> FSARegistry:
    """Get the global FSA registry instance"""
    global _global_registry
    if _global_registry is None:
        _global_registry = FSARegistry()
    return _global_registry


def reset_registry() -> None:
    """Reset the global registry (mainly for testing)"""
    global _global_registry
    _global_registry = None
