"""Factory Pattern FSA for agno.

This module provides a comprehensive factory pattern implementation with support for:
- Abstract factories and concrete factory implementations
- Product hierarchies and families
- Factory registration and discovery
- Dependency injection integration
- Singleton and prototype factory variants
- Factory chaining for complex creation
- Product validation and lifecycle management
- Thread-safe operations
"""

import logging
import threading
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type
from uuid import uuid4

logger = logging.getLogger(__name__)


# ==================== Enums ====================

class FactoryType(Enum):
    """Factory type."""
    ABSTRACT = "abstract"
    CONCRETE = "concrete"
    SINGLETON = "singleton"
    PROTOTYPE = "prototype"


class ProductStatus(Enum):
    """Product status."""
    CREATED = "created"
    VALIDATED = "validated"
    INVALID = "invalid"
    DISPOSED = "disposed"


class LifecycleStage(Enum):
    """Product lifecycle stage."""
    INITIALIZATION = "initialization"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    DISPOSED = "disposed"


# ==================== Base Classes ====================

class Product(ABC):
    """Base product class."""

    def __init__(self):
        self.product_id = str(uuid4())
        self.status = ProductStatus.CREATED
        self.created_at = datetime.now()
        self.lifecycle_stage = LifecycleStage.INITIALIZATION
        self.metadata: Dict[str, Any] = {}

    @abstractmethod
    def validate(self) -> bool:
        """Validate the product."""
        pass

    def dispose(self):
        """Dispose of the product."""
        self.lifecycle_stage = LifecycleStage.DISPOSED
        self.status = ProductStatus.DISPOSED


class Factory(ABC):
    """Base factory class."""

    def __init__(self):
        self.factory_id = str(uuid4())
        self.factory_type = FactoryType.ABSTRACT
        self.created_count = 0
        self.config: Dict[str, Any] = {}
        self.dependencies: Dict[str, Any] = {}

    @abstractmethod
    def create_product(self, product_type: str, params: Dict[str, Any]) -> Optional[Product]:
        """Create a product."""
        pass

    def get_metrics(self) -> Dict[str, Any]:
        """Get factory metrics."""
        return {
            "created_count": self.created_count,
            "factory_type": self.factory_type.value,
        }


# ==================== Data Classes ====================

@dataclass
class FactoryOp:
    """Factory operation."""
    operation: str = ""
    factory_name: Optional[str] = None
    factory_type: Optional[str] = None
    factory: Optional[Factory] = None
    product_type: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)
    criteria: Optional[Dict[str, Any]] = None


@dataclass
class FactoryResult:
    """Factory pattern pipeline result."""
    success: bool
    operations_count: int = 0
    products_created: int = 0
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
    """Factory registration result."""
    registered: bool
    factory_name: str = ""
    factory_id: str = ""
    error: Optional[str] = None


@dataclass
class ProductRegisterResult:
    """Product registration result."""
    registered: bool
    product_type: str = ""
    error: Optional[str] = None


@dataclass
class CreateProductResult:
    """Product creation result."""
    created: bool
    product: Optional[Product] = None
    product_id: str = ""
    error: Optional[str] = None


@dataclass
class ProductRegistry:
    """Product type registry."""
    product_types: Dict[str, Type] = field(default_factory=dict)
    total_count: int = 0


@dataclass
class FactoryCriteria:
    """Factory selection criteria."""
    factory_type: Optional[FactoryType] = None
    supports_product: Optional[str] = None
    min_created_count: int = 0
    max_created_count: int = 1000000


@dataclass
class FactorySelectionResult:
    """Factory selection result."""
    selected: bool
    factory_name: str = ""
    factory: Optional[Factory] = None
    error: Optional[str] = None


@dataclass
class FactoryChain:
    """Factory chain for composition."""
    chain_id: str = field(default_factory=lambda: str(uuid4()))
    factories: List[Factory] = field(default_factory=list)
    current_index: int = 0


@dataclass
class ChainResult:
    """Factory chain creation result."""
    created: bool
    chain_id: str = ""
    factory_count: int = 0
    error: Optional[str] = None


@dataclass
class ProductValidation:
    """Product validation result."""
    valid: bool
    product_id: str = ""
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class ConfigureResult:
    """Factory configuration result."""
    configured: bool
    factory_name: str = ""
    error: Optional[str] = None


@dataclass
class ProductFamily:
    """Product family definition."""
    family_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    product_types: List[Type] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class FamilyResult:
    """Product family creation result."""
    created: bool
    family_id: str = ""
    family_name: str = ""
    product_count: int = 0
    error: Optional[str] = None


@dataclass
class LifecycleInfo:
    """Product lifecycle information."""
    product_id: str = ""
    stage: LifecycleStage = LifecycleStage.INITIALIZATION
    created_at: Optional[datetime] = None
    age_seconds: float = 0.0


@dataclass
class CloneResult:
    """Factory clone result."""
    cloned: bool
    source_factory: str = ""
    target_factory: str = ""
    factory_id: str = ""
    error: Optional[str] = None


@dataclass
class OverrideResult:
    """Factory override result."""
    overridden: bool
    factory_name: str = ""
    error: Optional[str] = None


@dataclass
class FactoryMetrics:
    """Factory metrics."""
    factory_name: str = ""
    factory_type: str = ""
    created_count: int = 0
    error_count: int = 0
    avg_creation_time: float = 0.0


@dataclass
class InjectionResult:
    """Dependency injection result."""
    injected: bool
    factory_name: str = ""
    dependency_count: int = 0
    error: Optional[str] = None


@dataclass
class FactoryConfig:
    """Factory pattern configuration."""
    enable_validation: bool = True
    enable_metrics: bool = True
    enable_lifecycle_tracking: bool = True
    enable_families: bool = True
    enable_singleton: bool = True
    enable_prototype: bool = True
    thread_safe: bool = True
    max_factories: int = 1000
    max_products_per_factory: int = 10000
    allow_override: bool = False


# ==================== Concrete Products ====================

class ConcreteProductA(Product):
    """Concrete product A."""

    def __init__(self, **kwargs):
        super().__init__()
        self.properties = kwargs
        self.product_type = "ProductA"

    def validate(self) -> bool:
        """Validate product A."""
        self.status = ProductStatus.VALIDATED
        self.lifecycle_stage = LifecycleStage.ACTIVE
        return True


class ConcreteProductB(Product):
    """Concrete product B."""

    def __init__(self, **kwargs):
        super().__init__()
        self.properties = kwargs
        self.product_type = "ProductB"

    def validate(self) -> bool:
        """Validate product B."""
        self.status = ProductStatus.VALIDATED
        self.lifecycle_stage = LifecycleStage.ACTIVE
        return True


class ConcreteProductC(Product):
    """Concrete product C."""

    def __init__(self, **kwargs):
        super().__init__()
        self.properties = kwargs
        self.product_type = "ProductC"

    def validate(self) -> bool:
        """Validate product C."""
        self.status = ProductStatus.VALIDATED
        self.lifecycle_stage = LifecycleStage.ACTIVE
        return True


# ==================== Concrete Factories ====================

class ConcreteFactoryA(Factory):
    """Concrete factory A."""

    def __init__(self):
        super().__init__()
        self.factory_type = FactoryType.CONCRETE
        self.supported_products = ["ProductA", "ProductB"]

    def create_product(self, product_type: str, params: Dict[str, Any]) -> Optional[Product]:
        """Create a product."""
        if product_type not in self.supported_products:
            return None

        if product_type == "ProductA":
            product = ConcreteProductA(**params)
        elif product_type == "ProductB":
            product = ConcreteProductB(**params)
        else:
            return None

        self.created_count += 1
        return product


class ConcreteFactoryB(Factory):
    """Concrete factory B."""

    def __init__(self):
        super().__init__()
        self.factory_type = FactoryType.CONCRETE
        self.supported_products = ["ProductC"]

    def create_product(self, product_type: str, params: Dict[str, Any]) -> Optional[Product]:
        """Create a product."""
        if product_type not in self.supported_products:
            return None

        if product_type == "ProductC":
            product = ConcreteProductC(**params)
        else:
            return None

        self.created_count += 1
        return product


class SingletonFactory(Factory):
    """Singleton factory - creates single instance per product type."""

    def __init__(self):
        super().__init__()
        self.factory_type = FactoryType.SINGLETON
        self.instances: Dict[str, Product] = {}
        self.supported_products = ["ProductA", "ProductB", "ProductC"]

    def create_product(self, product_type: str, params: Dict[str, Any]) -> Optional[Product]:
        """Create or return existing singleton product."""
        if product_type not in self.supported_products:
            return None

        # Return existing instance if available
        if product_type in self.instances:
            return self.instances[product_type]

        # Create new instance
        if product_type == "ProductA":
            product = ConcreteProductA(**params)
        elif product_type == "ProductB":
            product = ConcreteProductB(**params)
        elif product_type == "ProductC":
            product = ConcreteProductC(**params)
        else:
            return None

        self.instances[product_type] = product
        self.created_count += 1
        return product


class PrototypeFactory(Factory):
    """Prototype factory - creates products from prototype."""

    def __init__(self, prototype: Optional[Product] = None):
        super().__init__()
        self.factory_type = FactoryType.PROTOTYPE
        self.prototype = prototype

    def create_product(self, product_type: str, params: Dict[str, Any]) -> Optional[Product]:
        """Create product from prototype."""
        if not self.prototype:
            return None

        # Clone prototype (simplified - real implementation would deep copy)
        if isinstance(self.prototype, ConcreteProductA):
            product = ConcreteProductA(**params)
        elif isinstance(self.prototype, ConcreteProductB):
            product = ConcreteProductB(**params)
        elif isinstance(self.prototype, ConcreteProductC):
            product = ConcreteProductC(**params)
        else:
            return None

        # Copy metadata from prototype
        product.metadata = self.prototype.metadata.copy()

        self.created_count += 1
        return product


# ==================== Main FSA Class ====================

class FactoryPatternFSA:
    """
    Factory Pattern FSA implementation.

    Provides factory pattern functionality with abstract factories, product families,
    and comprehensive factory management.
    """

    def __init__(self, config: FactoryConfig):
        """
        Initialize Factory Pattern FSA.

        Args:
            config: Factory pattern configuration
        """
        self.config = config
        self.fsa_id = str(uuid4())

        # Factory storage
        self.factories: Dict[str, Factory] = {}
        self.product_registry: Dict[str, Type] = {
            "ProductA": ConcreteProductA,
            "ProductB": ConcreteProductB,
            "ProductC": ConcreteProductC,
        }

        # Product families
        self.product_families: Dict[str, ProductFamily] = {}

        # Factory chains
        self.factory_chains: Dict[str, FactoryChain] = {}

        # Metrics
        self.metrics: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.creation_times: Dict[str, List[float]] = defaultdict(list)

        # Products created (for lifecycle tracking)
        self.products: Dict[str, Product] = {}

        # Thread safety
        self._lock = threading.RLock() if config.thread_safe else None

        logger.info(f"Initialized FactoryPatternFSA: {self.fsa_id}")

    def _acquire_lock(self):
        """Acquire lock for thread-safe operations."""
        if self._lock:
            self._lock.acquire()

    def _release_lock(self):
        """Release lock after thread-safe operations."""
        if self._lock:
            self._lock.release()

    def validate(self, config: FactoryConfig) -> ValidationResult:
        """
        Validate factory pattern configuration.

        Args:
            config: Configuration to validate

        Returns:
            ValidationResult with validation status
        """
        errors = []
        warnings = []

        if config.max_factories < 1:
            errors.append("max_factories must be positive")

        if config.max_products_per_factory < 1:
            errors.append("max_products_per_factory must be positive")

        if not config.enable_validation:
            warnings.append("Product validation is disabled")

        if not config.thread_safe:
            warnings.append("Thread safety is disabled")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def create_abstract_factory(self, factory_type: str) -> Optional[Factory]:
        """
        Create an abstract factory interface.

        Args:
            factory_type: Type of factory to create

        Returns:
            Factory instance or None
        """
        try:
            self._acquire_lock()

            # For this implementation, we return a concrete factory
            # In a real system, this would return an abstract interface
            if factory_type == "FactoryA":
                factory = ConcreteFactoryA()
            elif factory_type == "FactoryB":
                factory = ConcreteFactoryB()
            elif factory_type == "Singleton":
                factory = SingletonFactory()
            elif factory_type == "Prototype":
                factory = PrototypeFactory()
            else:
                logger.error(f"Unknown factory type: {factory_type}")
                return None

            logger.info(f"Created abstract factory: {factory.factory_id}")
            return factory

        finally:
            self._release_lock()

    def create_concrete_factory(
        self,
        factory_type: str,
        implementation: Type,
    ) -> Optional[Factory]:
        """
        Create a concrete factory implementation.

        Args:
            factory_type: Type of factory
            implementation: Implementation class

        Returns:
            Factory instance or None
        """
        try:
            self._acquire_lock()

            if not issubclass(implementation, Factory):
                logger.error("Implementation must be a Factory subclass")
                return None

            factory = implementation()
            logger.info(f"Created concrete factory: {factory.factory_id}")

            return factory

        except Exception as e:
            logger.error(f"Error creating concrete factory: {str(e)}")
            return None

        finally:
            self._release_lock()

    def register_factory(self, name: str, factory: Factory) -> RegisterResult:
        """
        Register a factory.

        Args:
            name: Factory name
            factory: Factory instance

        Returns:
            RegisterResult with registration status
        """
        try:
            self._acquire_lock()

            if len(self.factories) >= self.config.max_factories:
                return RegisterResult(
                    registered=False,
                    factory_name=name,
                    error="Maximum factories reached",
                )

            if name in self.factories and not self.config.allow_override:
                return RegisterResult(
                    registered=False,
                    factory_name=name,
                    error="Factory already registered",
                )

            self.factories[name] = factory
            logger.info(f"Registered factory: {name}")

            return RegisterResult(
                registered=True,
                factory_name=name,
                factory_id=factory.factory_id,
            )

        except Exception as e:
            return RegisterResult(
                registered=False,
                factory_name=name,
                error=str(e),
            )

        finally:
            self._release_lock()

    def get_factory(self, name: str) -> Optional[Factory]:
        """
        Get a registered factory.

        Args:
            name: Factory name

        Returns:
            Factory instance or None
        """
        try:
            self._acquire_lock()

            return self.factories.get(name)

        finally:
            self._release_lock()

    def create_product(
        self,
        factory_name: str,
        product_type: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> CreateProductResult:
        """
        Create a product using a factory.

        Args:
            factory_name: Name of factory to use
            product_type: Type of product to create
            params: Product parameters

        Returns:
            CreateProductResult with creation status
        """
        try:
            self._acquire_lock()

            if factory_name not in self.factories:
                return CreateProductResult(
                    created=False,
                    error=f"Factory not found: {factory_name}",
                )

            factory = self.factories[factory_name]

            if factory.created_count >= self.config.max_products_per_factory:
                return CreateProductResult(
                    created=False,
                    error="Maximum products per factory reached",
                )

            start_time = time.time()
            params = params or {}
            product = factory.create_product(product_type, params)
            creation_time = time.time() - start_time

            if not product:
                self.error_counts[factory_name] += 1
                return CreateProductResult(
                    created=False,
                    error="Failed to create product",
                )

            # Track creation time
            if self.config.enable_metrics:
                self.creation_times[factory_name].append(creation_time)

            # Validate product if enabled
            if self.config.enable_validation:
                product.validate()

            # Track product lifecycle if enabled
            if self.config.enable_lifecycle_tracking:
                self.products[product.product_id] = product

            logger.info(f"Created product: {product.product_id}")

            return CreateProductResult(
                created=True,
                product=product,
                product_id=product.product_id,
            )

        except Exception as e:
            self.error_counts[factory_name] += 1
            return CreateProductResult(
                created=False,
                error=str(e),
            )

        finally:
            self._release_lock()

    def register_product(
        self,
        product_type: str,
        product_class: Type,
    ) -> ProductRegisterResult:
        """
        Register a product type.

        Args:
            product_type: Product type name
            product_class: Product class

        Returns:
            ProductRegisterResult with registration status
        """
        try:
            self._acquire_lock()

            if not issubclass(product_class, Product):
                return ProductRegisterResult(
                    registered=False,
                    product_type=product_type,
                    error="Product class must extend Product",
                )

            self.product_registry[product_type] = product_class
            logger.info(f"Registered product type: {product_type}")

            return ProductRegisterResult(
                registered=True,
                product_type=product_type,
            )

        except Exception as e:
            return ProductRegisterResult(
                registered=False,
                product_type=product_type,
                error=str(e),
            )

        finally:
            self._release_lock()

    def get_product_registry(self) -> ProductRegistry:
        """
        Get the product registry.

        Returns:
            ProductRegistry with registered products
        """
        try:
            self._acquire_lock()

            return ProductRegistry(
                product_types=self.product_registry.copy(),
                total_count=len(self.product_registry),
            )

        finally:
            self._release_lock()

    def select_factory(
        self,
        criteria: FactoryCriteria,
    ) -> FactorySelectionResult:
        """
        Select a factory based on criteria.

        Args:
            criteria: Selection criteria

        Returns:
            FactorySelectionResult with selected factory
        """
        try:
            self._acquire_lock()

            for name, factory in self.factories.items():
                # Check factory type
                if criteria.factory_type and factory.factory_type != criteria.factory_type:
                    continue

                # Check created count
                if not (criteria.min_created_count <= factory.created_count <= criteria.max_created_count):
                    continue

                # Check product support (for concrete factories)
                if criteria.supports_product:
                    if hasattr(factory, 'supported_products'):
                        if criteria.supports_product not in factory.supported_products:
                            continue

                # Found matching factory
                return FactorySelectionResult(
                    selected=True,
                    factory_name=name,
                    factory=factory,
                )

            return FactorySelectionResult(
                selected=False,
                error="No factory matches criteria",
            )

        finally:
            self._release_lock()

    def chain_factories(self, factories: List[Factory]) -> ChainResult:
        """
        Create a factory chain.

        Args:
            factories: List of factories to chain

        Returns:
            ChainResult with chain status
        """
        try:
            self._acquire_lock()

            chain = FactoryChain(factories=factories)
            self.factory_chains[chain.chain_id] = chain

            logger.info(f"Created factory chain: {chain.chain_id}")

            return ChainResult(
                created=True,
                chain_id=chain.chain_id,
                factory_count=len(factories),
            )

        except Exception as e:
            return ChainResult(
                created=False,
                error=str(e),
            )

        finally:
            self._release_lock()

    def validate_product(self, product: Product) -> ProductValidation:
        """
        Validate a product.

        Args:
            product: Product to validate

        Returns:
            ProductValidation with validation status
        """
        errors = []
        warnings = []

        try:
            if not self.config.enable_validation:
                warnings.append("Validation is disabled")
                return ProductValidation(
                    valid=True,
                    product_id=product.product_id,
                    warnings=warnings,
                )

            # Check if disposed before validation
            if product.lifecycle_stage == LifecycleStage.DISPOSED:
                warnings.append("Product is disposed")

            # Validate product (unless disposed)
            if product.lifecycle_stage != LifecycleStage.DISPOSED:
                is_valid = product.validate()

                if not is_valid:
                    errors.append("Product validation failed")

            if product.status == ProductStatus.INVALID:
                errors.append("Product marked as invalid")

            return ProductValidation(
                valid=len(errors) == 0,
                product_id=product.product_id,
                errors=errors,
                warnings=warnings,
            )

        except Exception as e:
            errors.append(str(e))
            return ProductValidation(
                valid=False,
                product_id=product.product_id,
                errors=errors,
            )

    def configure_factory(
        self,
        factory_name: str,
        config: Dict[str, Any],
    ) -> ConfigureResult:
        """
        Configure a factory.

        Args:
            factory_name: Factory to configure
            config: Configuration parameters

        Returns:
            ConfigureResult with configuration status
        """
        try:
            self._acquire_lock()

            if factory_name not in self.factories:
                return ConfigureResult(
                    configured=False,
                    factory_name=factory_name,
                    error="Factory not found",
                )

            factory = self.factories[factory_name]
            factory.config.update(config)

            logger.info(f"Configured factory: {factory_name}")

            return ConfigureResult(
                configured=True,
                factory_name=factory_name,
            )

        except Exception as e:
            return ConfigureResult(
                configured=False,
                factory_name=factory_name,
                error=str(e),
            )

        finally:
            self._release_lock()

    def create_product_family(
        self,
        family_name: str,
        products: List[Type],
    ) -> FamilyResult:
        """
        Create a product family.

        Args:
            family_name: Name of the family
            products: List of product types

        Returns:
            FamilyResult with family creation status
        """
        try:
            self._acquire_lock()

            if not self.config.enable_families:
                return FamilyResult(
                    created=False,
                    family_name=family_name,
                    error="Product families are disabled",
                )

            # Validate all products extend Product
            for product_class in products:
                if not issubclass(product_class, Product):
                    return FamilyResult(
                        created=False,
                        family_name=family_name,
                        error="All products must extend Product class",
                    )

            family = ProductFamily(
                name=family_name,
                product_types=products,
            )

            self.product_families[family.family_id] = family
            logger.info(f"Created product family: {family_name}")

            return FamilyResult(
                created=True,
                family_id=family.family_id,
                family_name=family_name,
                product_count=len(products),
            )

        except Exception as e:
            return FamilyResult(
                created=False,
                family_name=family_name,
                error=str(e),
            )

        finally:
            self._release_lock()

    def get_product_lifecycle(self, product: Product) -> LifecycleInfo:
        """
        Get product lifecycle information.

        Args:
            product: Product to query

        Returns:
            LifecycleInfo with lifecycle data
        """
        try:
            age_seconds = (datetime.now() - product.created_at).total_seconds()

            return LifecycleInfo(
                product_id=product.product_id,
                stage=product.lifecycle_stage,
                created_at=product.created_at,
                age_seconds=age_seconds,
            )

        except Exception as e:
            logger.error(f"Error getting lifecycle info: {str(e)}")
            return LifecycleInfo(
                product_id=product.product_id,
            )

    def clone_factory(
        self,
        source_factory: str,
        target_name: str,
    ) -> CloneResult:
        """
        Clone a factory.

        Args:
            source_factory: Source factory name
            target_name: Target factory name

        Returns:
            CloneResult with clone status
        """
        try:
            self._acquire_lock()

            if source_factory not in self.factories:
                return CloneResult(
                    cloned=False,
                    source_factory=source_factory,
                    target_factory=target_name,
                    error="Source factory not found",
                )

            if target_name in self.factories and not self.config.allow_override:
                return CloneResult(
                    cloned=False,
                    source_factory=source_factory,
                    target_factory=target_name,
                    error="Target factory already exists",
                )

            source = self.factories[source_factory]

            # Create a new instance of the same type
            if isinstance(source, ConcreteFactoryA):
                cloned = ConcreteFactoryA()
            elif isinstance(source, ConcreteFactoryB):
                cloned = ConcreteFactoryB()
            elif isinstance(source, SingletonFactory):
                cloned = SingletonFactory()
            elif isinstance(source, PrototypeFactory):
                cloned = PrototypeFactory(source.prototype if hasattr(source, 'prototype') else None)
            else:
                return CloneResult(
                    cloned=False,
                    source_factory=source_factory,
                    target_factory=target_name,
                    error="Cannot clone unknown factory type",
                )

            # Copy configuration
            cloned.config = source.config.copy()
            cloned.dependencies = source.dependencies.copy()

            self.factories[target_name] = cloned
            logger.info(f"Cloned factory {source_factory} to {target_name}")

            return CloneResult(
                cloned=True,
                source_factory=source_factory,
                target_factory=target_name,
                factory_id=cloned.factory_id,
            )

        except Exception as e:
            return CloneResult(
                cloned=False,
                source_factory=source_factory,
                target_factory=target_name,
                error=str(e),
            )

        finally:
            self._release_lock()

    def override_factory(
        self,
        factory_name: str,
        new_factory: Factory,
    ) -> OverrideResult:
        """
        Override a factory.

        Args:
            factory_name: Factory to override
            new_factory: New factory implementation

        Returns:
            OverrideResult with override status
        """
        try:
            self._acquire_lock()

            if not self.config.allow_override:
                return OverrideResult(
                    overridden=False,
                    factory_name=factory_name,
                    error="Factory override is disabled",
                )

            if factory_name not in self.factories:
                return OverrideResult(
                    overridden=False,
                    factory_name=factory_name,
                    error="Factory not found",
                )

            self.factories[factory_name] = new_factory
            logger.info(f"Overridden factory: {factory_name}")

            return OverrideResult(
                overridden=True,
                factory_name=factory_name,
            )

        except Exception as e:
            return OverrideResult(
                overridden=False,
                factory_name=factory_name,
                error=str(e),
            )

        finally:
            self._release_lock()

    def get_factory_metrics(self, factory_name: str) -> Optional[FactoryMetrics]:
        """
        Get factory metrics.

        Args:
            factory_name: Factory to query

        Returns:
            FactoryMetrics or None
        """
        try:
            self._acquire_lock()

            if factory_name not in self.factories:
                return None

            if not self.config.enable_metrics:
                return None

            factory = self.factories[factory_name]

            # Calculate average creation time
            avg_time = 0.0
            if factory_name in self.creation_times and self.creation_times[factory_name]:
                avg_time = sum(self.creation_times[factory_name]) / len(self.creation_times[factory_name])

            return FactoryMetrics(
                factory_name=factory_name,
                factory_type=factory.factory_type.value,
                created_count=factory.created_count,
                error_count=self.error_counts.get(factory_name, 0),
                avg_creation_time=avg_time,
            )

        finally:
            self._release_lock()

    def create_singleton_factory(self, factory_type: str) -> Optional[SingletonFactory]:
        """
        Create a singleton factory.

        Args:
            factory_type: Type identifier

        Returns:
            SingletonFactory instance or None
        """
        try:
            self._acquire_lock()

            if not self.config.enable_singleton:
                logger.error("Singleton factories are disabled")
                return None

            factory = SingletonFactory()
            logger.info(f"Created singleton factory: {factory.factory_id}")

            return factory

        finally:
            self._release_lock()

    def create_prototype_factory(self, prototype: Product) -> Optional[PrototypeFactory]:
        """
        Create a prototype factory.

        Args:
            prototype: Prototype product

        Returns:
            PrototypeFactory instance or None
        """
        try:
            self._acquire_lock()

            if not self.config.enable_prototype:
                logger.error("Prototype factories are disabled")
                return None

            factory = PrototypeFactory(prototype)
            logger.info(f"Created prototype factory: {factory.factory_id}")

            return factory

        finally:
            self._release_lock()

    def inject_dependencies(
        self,
        factory: Factory,
        dependencies: Dict[str, Any],
    ) -> InjectionResult:
        """
        Inject dependencies into a factory.

        Args:
            factory: Factory to inject into
            dependencies: Dependencies to inject

        Returns:
            InjectionResult with injection status
        """
        try:
            self._acquire_lock()

            factory.dependencies.update(dependencies)

            logger.info(f"Injected dependencies into factory: {factory.factory_id}")

            # Find factory name
            factory_name = ""
            for name, f in self.factories.items():
                if f == factory:
                    factory_name = name
                    break

            return InjectionResult(
                injected=True,
                factory_name=factory_name or "unknown",
                dependency_count=len(dependencies),
            )

        except Exception as e:
            return InjectionResult(
                injected=False,
                error=str(e),
            )

        finally:
            self._release_lock()

    def execute(self, ops: List[FactoryOp]) -> FactoryResult:
        """
        Execute factory pattern pipeline.

        Args:
            ops: List of factory operations

        Returns:
            FactoryResult with pipeline result
        """
        try:
            start_time = time.time()
            products_created = 0
            errors = []
            results = []

            for op in ops:
                if op.operation == "register":
                    if op.factory_name and op.factory:
                        result = self.register_factory(op.factory_name, op.factory)
                        results.append(result)
                        if not result.registered:
                            errors.append(result.error or "Registration failed")

                elif op.operation == "create_product":
                    if op.factory_name and op.product_type:
                        result = self.create_product(
                            op.factory_name,
                            op.product_type,
                            op.params,
                        )
                        results.append(result)
                        if result.created:
                            products_created += 1
                        else:
                            errors.append(result.error or "Creation failed")

                elif op.operation == "select":
                    if op.criteria:
                        criteria = FactoryCriteria(**op.criteria)
                        result = self.select_factory(criteria)
                        results.append(result)

                elif op.operation == "configure":
                    if op.factory_name:
                        result = self.configure_factory(op.factory_name, op.params)
                        results.append(result)

            execution_time = time.time() - start_time

            return FactoryResult(
                success=len(errors) == 0,
                operations_count=len(ops),
                products_created=products_created,
                errors=errors,
                execution_time=execution_time,
                results=results,
            )

        except Exception as e:
            return FactoryResult(
                success=False,
                errors=[str(e)],
            )
