"""Unit tests for FactoryPatternFSA."""

import pytest
import time

from agno.fsas.factory_pattern_fsa import (
    FactoryPatternFSA,
    Factory,
    Product,
    FactoryConfig,
    FactoryType,
    ProductStatus,
    LifecycleStage,
    ConcreteProductA,
    ConcreteProductB,
    ConcreteProductC,
    ConcreteFactoryA,
    ConcreteFactoryB,
    SingletonFactory,
    PrototypeFactory,
    FactoryOp,
    FactoryResult,
    ValidationResult,
    RegisterResult,
    ProductRegisterResult,
    CreateProductResult,
    ProductRegistry,
    FactoryCriteria,
    FactorySelectionResult,
    FactoryChain,
    ChainResult,
    ProductValidation,
    ConfigureResult,
    ProductFamily,
    FamilyResult,
    LifecycleInfo,
    CloneResult,
    OverrideResult,
    FactoryMetrics,
    InjectionResult,
)


# ==================== Mock Classes ====================

class MockProduct(Product):
    """Mock product for testing."""

    def __init__(self, **kwargs):
        super().__init__()
        self.properties = kwargs

    def validate(self) -> bool:
        """Validate the product."""
        self.status = ProductStatus.VALIDATED
        self.lifecycle_stage = LifecycleStage.ACTIVE
        return True


class MockFactory(Factory):
    """Mock factory for testing."""

    def __init__(self):
        super().__init__()
        self.factory_type = FactoryType.CONCRETE

    def create_product(self, product_type: str, params: dict) -> Product:
        """Create a product."""
        product = MockProduct(**params)
        self.created_count += 1
        return product


# ==================== Fixtures ====================

@pytest.fixture
def factory_pattern():
    """Create factory pattern instance."""
    config = FactoryConfig()
    return FactoryPatternFSA(config)


@pytest.fixture
def configured_pattern():
    """Create pre-configured factory pattern."""
    config = FactoryConfig(
        enable_validation=True,
        enable_metrics=True,
        enable_lifecycle_tracking=True,
        enable_families=True,
        thread_safe=True,
    )
    pattern = FactoryPatternFSA(config)

    # Register a factory
    factory = ConcreteFactoryA()
    pattern.register_factory("test_factory", factory)

    return pattern


# ==================== Test Classes ====================

class TestFactoryPatternBasics:
    """Test basic factory pattern functionality."""

    def test_initialization(self):
        """Test factory pattern initialization."""
        config = FactoryConfig()
        pattern = FactoryPatternFSA(config)
        assert pattern.config == config
        assert pattern.fsa_id is not None

    def test_initialization_with_custom_config(self):
        """Test initialization with custom configuration."""
        config = FactoryConfig(
            enable_validation=False,
            enable_metrics=False,
        )
        pattern = FactoryPatternFSA(config)
        assert pattern.config.enable_validation is False
        assert pattern.config.enable_metrics is False

    def test_validation_success(self, factory_pattern):
        """Test successful configuration validation."""
        config = FactoryConfig(max_factories=500)
        result = factory_pattern.validate(config)
        assert result.valid is True

    def test_validation_failure(self, factory_pattern):
        """Test configuration validation failure."""
        config = FactoryConfig(max_factories=-1)
        result = factory_pattern.validate(config)
        assert result.valid is False
        assert len(result.errors) > 0


class TestAbstractFactoryCreation:
    """Test abstract factory creation."""

    def test_create_abstract_factory(self, factory_pattern):
        """Test creating an abstract factory."""
        factory = factory_pattern.create_abstract_factory("FactoryA")
        assert factory is not None
        assert isinstance(factory, ConcreteFactoryA)

    def test_create_unknown_factory_type(self, factory_pattern):
        """Test creating unknown factory type."""
        factory = factory_pattern.create_abstract_factory("Unknown")
        assert factory is None

    def test_create_singleton_abstract_factory(self, factory_pattern):
        """Test creating singleton abstract factory."""
        factory = factory_pattern.create_abstract_factory("Singleton")
        assert factory is not None
        assert isinstance(factory, SingletonFactory)


class TestConcreteFactoryCreation:
    """Test concrete factory creation."""

    def test_create_concrete_factory(self, factory_pattern):
        """Test creating a concrete factory."""
        factory = factory_pattern.create_concrete_factory("FactoryA", ConcreteFactoryA)
        assert factory is not None
        assert isinstance(factory, ConcreteFactoryA)

    def test_create_concrete_factory_invalid_type(self, factory_pattern):
        """Test creating concrete factory with invalid type."""
        factory = factory_pattern.create_concrete_factory("Invalid", MockProduct)
        assert factory is None


class TestFactoryRegistration:
    """Test factory registration."""

    def test_register_factory(self, factory_pattern):
        """Test registering a factory."""
        factory = ConcreteFactoryA()
        result = factory_pattern.register_factory("my_factory", factory)
        assert result.registered is True
        assert result.factory_name == "my_factory"

    def test_register_duplicate_factory(self):
        """Test registering duplicate factory."""
        config = FactoryConfig(allow_override=False)
        pattern = FactoryPatternFSA(config)

        factory1 = ConcreteFactoryA()
        pattern.register_factory("dup_factory", factory1)

        factory2 = ConcreteFactoryA()
        result = pattern.register_factory("dup_factory", factory2)
        assert result.registered is False

    def test_register_with_override(self):
        """Test registering factory with override allowed."""
        config = FactoryConfig(allow_override=True)
        pattern = FactoryPatternFSA(config)

        factory1 = ConcreteFactoryA()
        pattern.register_factory("factory", factory1)

        factory2 = ConcreteFactoryA()
        result = pattern.register_factory("factory", factory2)
        assert result.registered is True


class TestFactoryRetrieval:
    """Test factory retrieval."""

    def test_get_factory(self, configured_pattern):
        """Test getting a factory."""
        factory = configured_pattern.get_factory("test_factory")
        assert factory is not None
        assert isinstance(factory, ConcreteFactoryA)

    def test_get_nonexistent_factory(self, factory_pattern):
        """Test getting non-existent factory."""
        factory = factory_pattern.get_factory("nonexistent")
        assert factory is None


class TestProductCreation:
    """Test product creation."""

    def test_create_product(self, configured_pattern):
        """Test creating a product."""
        result = configured_pattern.create_product(
            "test_factory",
            "ProductA",
            {"key": "value"}
        )
        assert result.created is True
        assert result.product is not None
        assert isinstance(result.product, ConcreteProductA)

    def test_create_product_unknown_factory(self, factory_pattern):
        """Test creating product with unknown factory."""
        result = factory_pattern.create_product(
            "nonexistent",
            "ProductA",
            {}
        )
        assert result.created is False

    def test_create_product_unsupported_type(self, configured_pattern):
        """Test creating unsupported product type."""
        result = configured_pattern.create_product(
            "test_factory",
            "ProductC",  # FactoryA doesn't support ProductC
            {}
        )
        assert result.created is False


class TestProductRegistration:
    """Test product registration."""

    def test_register_product(self, factory_pattern):
        """Test registering a product type."""
        result = factory_pattern.register_product("CustomProduct", MockProduct)
        assert result.registered is True
        assert result.product_type == "CustomProduct"

    def test_register_invalid_product(self, factory_pattern):
        """Test registering invalid product type."""
        result = factory_pattern.register_product("Invalid", dict)
        assert result.registered is False


class TestProductRegistryQueries:
    """Test product registry queries."""

    def test_get_product_registry(self, factory_pattern):
        """Test getting product registry."""
        registry = factory_pattern.get_product_registry()
        assert isinstance(registry, ProductRegistry)
        assert registry.total_count > 0

    def test_registry_contains_default_products(self, factory_pattern):
        """Test registry contains default products."""
        registry = factory_pattern.get_product_registry()
        assert "ProductA" in registry.product_types
        assert "ProductB" in registry.product_types
        assert "ProductC" in registry.product_types


class TestFactorySelection:
    """Test factory selection."""

    def test_select_factory_by_type(self, configured_pattern):
        """Test selecting factory by type."""
        criteria = FactoryCriteria(factory_type=FactoryType.CONCRETE)
        result = configured_pattern.select_factory(criteria)
        assert result.selected is True
        assert result.factory is not None

    def test_select_factory_by_product_support(self, configured_pattern):
        """Test selecting factory by supported product."""
        criteria = FactoryCriteria(supports_product="ProductA")
        result = configured_pattern.select_factory(criteria)
        assert result.selected is True

    def test_select_factory_no_match(self, factory_pattern):
        """Test selection with no matching factory."""
        criteria = FactoryCriteria(factory_type=FactoryType.SINGLETON)
        result = factory_pattern.select_factory(criteria)
        assert result.selected is False


class TestFactoryChaining:
    """Test factory chaining."""

    def test_chain_factories(self, factory_pattern):
        """Test creating a factory chain."""
        factory1 = ConcreteFactoryA()
        factory2 = ConcreteFactoryB()

        result = factory_pattern.chain_factories([factory1, factory2])
        assert result.created is True
        assert result.factory_count == 2

    def test_chain_empty_factories(self, factory_pattern):
        """Test chaining empty factory list."""
        result = factory_pattern.chain_factories([])
        assert result.created is True
        assert result.factory_count == 0


class TestProductValidation:
    """Test product validation."""

    def test_validate_product(self, factory_pattern):
        """Test validating a product."""
        product = ConcreteProductA()
        result = factory_pattern.validate_product(product)
        assert result.valid is True

    def test_validate_disposed_product(self, factory_pattern):
        """Test validating disposed product."""
        product = ConcreteProductA()
        product.dispose()

        result = factory_pattern.validate_product(product)
        assert len(result.warnings) > 0


class TestFactoryConfiguration:
    """Test factory configuration."""

    def test_configure_factory(self, configured_pattern):
        """Test configuring a factory."""
        result = configured_pattern.configure_factory(
            "test_factory",
            {"setting": "value"}
        )
        assert result.configured is True

    def test_configure_nonexistent_factory(self, factory_pattern):
        """Test configuring non-existent factory."""
        result = factory_pattern.configure_factory("nonexistent", {})
        assert result.configured is False


class TestProductFamilyCreation:
    """Test product family creation."""

    def test_create_product_family(self, factory_pattern):
        """Test creating a product family."""
        result = factory_pattern.create_product_family(
            "TestFamily",
            [ConcreteProductA, ConcreteProductB]
        )
        assert result.created is True
        assert result.product_count == 2

    def test_create_family_disabled(self):
        """Test creating family when disabled."""
        config = FactoryConfig(enable_families=False)
        pattern = FactoryPatternFSA(config)

        result = pattern.create_product_family(
            "TestFamily",
            [ConcreteProductA]
        )
        assert result.created is False

    def test_create_family_invalid_products(self, factory_pattern):
        """Test creating family with invalid products."""
        result = factory_pattern.create_product_family(
            "InvalidFamily",
            [dict, list]
        )
        assert result.created is False


class TestProductLifecycleQueries:
    """Test product lifecycle queries."""

    def test_get_product_lifecycle(self, factory_pattern):
        """Test getting product lifecycle."""
        product = ConcreteProductA()
        time.sleep(0.1)

        lifecycle = factory_pattern.get_product_lifecycle(product)
        assert lifecycle.product_id == product.product_id
        assert lifecycle.stage == LifecycleStage.INITIALIZATION
        assert lifecycle.age_seconds > 0


class TestFactoryCloning:
    """Test factory cloning."""

    def test_clone_factory(self, configured_pattern):
        """Test cloning a factory."""
        result = configured_pattern.clone_factory("test_factory", "cloned_factory")
        assert result.cloned is True
        assert result.source_factory == "test_factory"
        assert result.target_factory == "cloned_factory"

    def test_clone_nonexistent_factory(self, factory_pattern):
        """Test cloning non-existent factory."""
        result = factory_pattern.clone_factory("nonexistent", "target")
        assert result.cloned is False


class TestFactoryOverride:
    """Test factory override."""

    def test_override_factory(self):
        """Test overriding a factory."""
        config = FactoryConfig(allow_override=True)
        pattern = FactoryPatternFSA(config)

        factory1 = ConcreteFactoryA()
        pattern.register_factory("factory", factory1)

        factory2 = ConcreteFactoryB()
        result = pattern.override_factory("factory", factory2)
        assert result.overridden is True

    def test_override_disabled(self):
        """Test override when disabled."""
        config = FactoryConfig(allow_override=False)
        pattern = FactoryPatternFSA(config)

        factory1 = ConcreteFactoryA()
        pattern.register_factory("factory", factory1)

        factory2 = ConcreteFactoryB()
        result = pattern.override_factory("factory", factory2)
        assert result.overridden is False


class TestFactoryMetrics:
    """Test factory metrics."""

    def test_get_factory_metrics(self, configured_pattern):
        """Test getting factory metrics."""
        # Create some products
        configured_pattern.create_product("test_factory", "ProductA", {})
        configured_pattern.create_product("test_factory", "ProductB", {})

        metrics = configured_pattern.get_factory_metrics("test_factory")
        assert metrics is not None
        assert metrics.created_count == 2

    def test_get_metrics_disabled(self):
        """Test getting metrics when disabled."""
        config = FactoryConfig(enable_metrics=False)
        pattern = FactoryPatternFSA(config)

        factory = ConcreteFactoryA()
        pattern.register_factory("factory", factory)

        metrics = pattern.get_factory_metrics("factory")
        assert metrics is None


class TestSingletonFactory:
    """Test singleton factory."""

    def test_create_singleton_factory(self, factory_pattern):
        """Test creating a singleton factory."""
        factory = factory_pattern.create_singleton_factory("SingletonFactory")
        assert factory is not None
        assert isinstance(factory, SingletonFactory)

    def test_singleton_returns_same_instance(self, factory_pattern):
        """Test singleton factory returns same instance."""
        factory = SingletonFactory()
        factory_pattern.register_factory("singleton", factory)

        result1 = factory_pattern.create_product("singleton", "ProductA", {"key": "value"})
        result2 = factory_pattern.create_product("singleton", "ProductA", {"key": "value"})

        assert result1.product is result2.product

    def test_singleton_disabled(self):
        """Test singleton when disabled."""
        config = FactoryConfig(enable_singleton=False)
        pattern = FactoryPatternFSA(config)

        factory = pattern.create_singleton_factory("Singleton")
        assert factory is None


class TestPrototypeFactory:
    """Test prototype factory."""

    def test_create_prototype_factory(self, factory_pattern):
        """Test creating a prototype factory."""
        prototype = ConcreteProductA()
        factory = factory_pattern.create_prototype_factory(prototype)
        assert factory is not None
        assert isinstance(factory, PrototypeFactory)

    def test_prototype_creates_from_prototype(self, factory_pattern):
        """Test prototype factory creates from prototype."""
        prototype = ConcreteProductA()
        prototype.metadata["template"] = "value"

        factory = PrototypeFactory(prototype)
        factory_pattern.register_factory("prototype", factory)

        result = factory_pattern.create_product("prototype", "ProductA", {})
        assert result.created is True
        assert "template" in result.product.metadata

    def test_prototype_disabled(self):
        """Test prototype when disabled."""
        config = FactoryConfig(enable_prototype=False)
        pattern = FactoryPatternFSA(config)

        prototype = ConcreteProductA()
        factory = pattern.create_prototype_factory(prototype)
        assert factory is None


class TestDependencyInjection:
    """Test dependency injection."""

    def test_inject_dependencies(self, configured_pattern):
        """Test injecting dependencies into factory."""
        factory = configured_pattern.get_factory("test_factory")
        dependencies = {"service": "value", "config": "data"}

        result = configured_pattern.inject_dependencies(factory, dependencies)
        assert result.injected is True
        assert result.dependency_count == 2


class TestExecuteMethod:
    """Test execute method."""

    def test_execute_operations(self, factory_pattern):
        """Test executing factory pattern operations."""
        factory = ConcreteFactoryA()
        ops = [
            FactoryOp(
                operation="register",
                factory_name="new_factory",
                factory=factory,
            ),
        ]

        result = factory_pattern.execute(ops)
        assert isinstance(result, FactoryResult)
        assert result.success is True

    def test_execute_multiple_ops(self, factory_pattern):
        """Test executing multiple operations."""
        factory = ConcreteFactoryA()
        ops = [
            FactoryOp(operation="register", factory_name="factory", factory=factory),
            FactoryOp(
                operation="create_product",
                factory_name="factory",
                product_type="ProductA",
                params={"key": "value"},
            ),
        ]

        result = factory_pattern.execute(ops)
        assert result.success is True
        assert result.products_created == 1


class TestEdgeCases:
    """Test edge cases and error scenarios."""

    def test_create_product_max_limit(self):
        """Test creating products up to max limit."""
        config = FactoryConfig(max_products_per_factory=2)
        pattern = FactoryPatternFSA(config)

        factory = ConcreteFactoryA()
        pattern.register_factory("factory", factory)

        # Create up to limit
        pattern.create_product("factory", "ProductA", {})
        pattern.create_product("factory", "ProductB", {})

        # Try to exceed limit
        result = pattern.create_product("factory", "ProductA", {})
        assert result.created is False

    def test_register_factory_max_limit(self):
        """Test registering factories up to max limit."""
        config = FactoryConfig(max_factories=2)
        pattern = FactoryPatternFSA(config)

        factory1 = ConcreteFactoryA()
        factory2 = ConcreteFactoryB()
        factory3 = ConcreteFactoryA()

        pattern.register_factory("f1", factory1)
        pattern.register_factory("f2", factory2)

        result = pattern.register_factory("f3", factory3)
        assert result.registered is False


class TestThreadSafety:
    """Test thread safety."""

    def test_thread_safe_pattern(self):
        """Test thread-safe pattern creation."""
        config = FactoryConfig(thread_safe=True)
        pattern = FactoryPatternFSA(config)
        assert pattern._lock is not None

    def test_non_thread_safe_pattern(self):
        """Test non-thread-safe pattern."""
        config = FactoryConfig(thread_safe=False)
        pattern = FactoryPatternFSA(config)
        assert pattern._lock is None


class TestComplexProductHierarchies:
    """Test complex product hierarchies."""

    def test_multiple_product_types(self, factory_pattern):
        """Test creating multiple product types."""
        factory = ConcreteFactoryA()
        factory_pattern.register_factory("factory", factory)

        result1 = factory_pattern.create_product("factory", "ProductA", {"data": "a"})
        result2 = factory_pattern.create_product("factory", "ProductB", {"data": "b"})

        assert result1.created is True
        assert result2.created is True
        assert type(result1.product) != type(result2.product)


class TestMultiFactoryScenarios:
    """Test multi-factory scenarios."""

    def test_multiple_factories_different_products(self, factory_pattern):
        """Test multiple factories creating different products."""
        factoryA = ConcreteFactoryA()
        factoryB = ConcreteFactoryB()

        factory_pattern.register_factory("factoryA", factoryA)
        factory_pattern.register_factory("factoryB", factoryB)

        resultA = factory_pattern.create_product("factoryA", "ProductA", {})
        resultB = factory_pattern.create_product("factoryB", "ProductC", {})

        assert resultA.created is True
        assert resultB.created is True


class TestProductFamilyConsistency:
    """Test product family consistency."""

    def test_family_product_consistency(self, factory_pattern):
        """Test product family maintains consistency."""
        result = factory_pattern.create_product_family(
            "ConsistentFamily",
            [ConcreteProductA, ConcreteProductB, ConcreteProductC]
        )
        assert result.created is True

        # Verify family exists
        family = factory_pattern.product_families.get(result.family_id)
        assert family is not None
        assert len(family.product_types) == 3
