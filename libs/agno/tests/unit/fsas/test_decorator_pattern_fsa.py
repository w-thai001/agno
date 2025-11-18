"""Unit tests for DecoratorPatternFSA."""

import pytest
import threading
import time

from agno.fsas.decorator_pattern_fsa import (
    DecoratorPatternFSA,
    DecoratorConfig,
    Component,
    ConcreteComponent,
    DataComponent,
    ServiceComponent,
    Decorator,
    LoggingDecorator,
    CachingDecorator,
    ValidationDecorator,
    TimingDecorator,
    RetryDecorator,
    AuthorizationDecorator,
    CompressionDecorator,
    EncryptionDecorator,
    DecoratorFactory,
    DecoratorChain,
    DecoratorOp,
    DecoratorResult,
    ValidationResult,
    RegisterResult,
    StackResult,
    DecorationValidation,
    ComposedDecorator,
    ChainResult,
    RemoveResult,
    CloneResult,
    MergeResult,
    ReorderResult,
    DecoratorMetrics,
    ConditionalDecorator,
    DecoratedComponent,
)


# ==================== Fixtures ====================

@pytest.fixture
def decorator_pattern():
    """Create decorator pattern instance."""
    config = DecoratorConfig()
    return DecoratorPatternFSA(config)


@pytest.fixture
def configured_pattern():
    """Create pre-configured decorator pattern."""
    config = DecoratorConfig(
        enable_caching=True,
        enable_validation=True,
        enable_logging=True,
        enable_timing=True,
        thread_safe=True,
    )
    return DecoratorPatternFSA(config)


@pytest.fixture
def sample_component():
    """Create sample component."""
    return ConcreteComponent("test_value")


# ==================== Test Classes ====================

class TestDecoratorPatternBasics:
    """Test basic decorator pattern functionality."""

    def test_initialization(self):
        """Test decorator pattern initialization."""
        config = DecoratorConfig()
        pattern = DecoratorPatternFSA(config)
        assert pattern.config == config
        assert pattern.fsa_id is not None

    def test_initialization_with_custom_config(self):
        """Test initialization with custom configuration."""
        config = DecoratorConfig(
            enable_caching=False,
            max_decorator_depth=5,
        )
        pattern = DecoratorPatternFSA(config)
        assert pattern.config.enable_caching is False
        assert pattern.config.max_decorator_depth == 5

    def test_validation_success(self, decorator_pattern):
        """Test successful configuration validation."""
        config = DecoratorConfig(max_decorator_depth=20)
        result = decorator_pattern.validate(config)
        assert result.valid is True

    def test_validation_failure(self, decorator_pattern):
        """Test configuration validation failure."""
        config = DecoratorConfig(max_decorator_depth=-1)
        result = decorator_pattern.validate(config)
        assert result.valid is False
        assert len(result.errors) > 0


class TestComponentCreation:
    """Test component creation."""

    def test_create_concrete_component(self, decorator_pattern):
        """Test creating concrete component."""
        component = decorator_pattern.create_component("concrete", value="test")
        assert component is not None
        assert isinstance(component, ConcreteComponent)
        assert component.value == "test"

    def test_create_data_component(self, decorator_pattern):
        """Test creating data component."""
        component = decorator_pattern.create_component("data", data={"key": "value"})
        assert component is not None
        assert isinstance(component, DataComponent)
        assert component.data["key"] == "value"

    def test_create_service_component(self, decorator_pattern):
        """Test creating service component."""
        component = decorator_pattern.create_component("service", service_name="api")
        assert component is not None
        assert isinstance(component, ServiceComponent)
        assert component.service_name == "api"

    def test_create_unknown_component(self, decorator_pattern):
        """Test creating unknown component type."""
        component = decorator_pattern.create_component("unknown")
        assert component is None


class TestDecoratorCreation:
    """Test decorator creation."""

    def test_create_logging_decorator(self, decorator_pattern, sample_component):
        """Test creating logging decorator."""
        decorator = decorator_pattern.create_decorator("logging", sample_component)
        assert decorator is not None
        assert isinstance(decorator, LoggingDecorator)

    def test_create_caching_decorator(self, decorator_pattern, sample_component):
        """Test creating caching decorator."""
        decorator = decorator_pattern.create_decorator("caching", sample_component)
        assert decorator is not None
        assert isinstance(decorator, CachingDecorator)

    def test_create_validation_decorator(self, decorator_pattern, sample_component):
        """Test creating validation decorator."""
        decorator = decorator_pattern.create_decorator("validation", sample_component)
        assert decorator is not None
        assert isinstance(decorator, ValidationDecorator)

    def test_create_timing_decorator(self, decorator_pattern, sample_component):
        """Test creating timing decorator."""
        decorator = decorator_pattern.create_decorator("timing", sample_component)
        assert decorator is not None
        assert isinstance(decorator, TimingDecorator)


class TestComponentDecoration:
    """Test component decoration."""

    def test_decorate_component(self, decorator_pattern, sample_component):
        """Test decorating a component."""
        decorator = LoggingDecorator(sample_component)
        decorated = decorator_pattern.decorate(sample_component, decorator)
        assert decorated is not None
        assert isinstance(decorated, DecoratedComponent)
        assert decorated.decoration_count == 1

    def test_decorated_operation(self, sample_component):
        """Test decorated component operation."""
        decorator = LoggingDecorator(sample_component)
        result = decorator.operation()
        assert result == "test_value"
        assert len(decorator.log_entries) > 0


class TestDecoratorRegistration:
    """Test decorator registration."""

    def test_register_custom_decorator(self, decorator_pattern):
        """Test registering custom decorator."""
        class CustomDecorator(Decorator):
            def operation(self):
                return f"custom_{self._component.operation()}"

        result = decorator_pattern.register_decorator("custom", CustomDecorator)
        assert result.registered is True
        assert result.decorator_name == "custom"

    def test_register_duplicate_decorator(self, decorator_pattern):
        """Test registering duplicate decorator."""
        class CustomDecorator(Decorator):
            pass

        decorator_pattern.register_decorator("dup", CustomDecorator)
        result = decorator_pattern.register_decorator("dup", CustomDecorator)
        assert result.registered is False


class TestDecoratorRetrieval:
    """Test decorator retrieval."""

    def test_get_registered_decorator(self, decorator_pattern):
        """Test getting registered decorator."""
        class CustomDecorator(Decorator):
            pass

        decorator_pattern.register_decorator("test_dec", CustomDecorator)
        retrieved = decorator_pattern.get_decorator("test_dec")
        assert retrieved == CustomDecorator

    def test_get_nonexistent_decorator(self, decorator_pattern):
        """Test getting non-existent decorator."""
        retrieved = decorator_pattern.get_decorator("nonexistent")
        assert retrieved is None


class TestDecoratorStacking:
    """Test decorator stacking."""

    def test_stack_multiple_decorators(self, decorator_pattern, sample_component):
        """Test stacking multiple decorators."""
        decorators = ["logging", "caching", "timing"]
        result = decorator_pattern.stack_decorators(sample_component, decorators)
        assert result.stacked is True
        assert result.layers == 3
        assert result.decorated_component is not None

    def test_stack_exceeds_max_depth(self, decorator_pattern, sample_component):
        """Test stacking exceeds maximum depth."""
        config = DecoratorConfig(max_decorator_depth=2)
        pattern = DecoratorPatternFSA(config)

        decorators = ["logging", "caching", "timing"]
        result = pattern.stack_decorators(sample_component, decorators)
        assert result.stacked is False

    def test_stack_with_invalid_decorator(self, decorator_pattern, sample_component):
        """Test stacking with invalid decorator."""
        decorators = ["logging", "invalid_type"]
        result = decorator_pattern.stack_decorators(sample_component, decorators)
        assert result.stacked is False


class TestDecoratorUnwrapping:
    """Test decorator unwrapping."""

    def test_unwrap_decorator(self, decorator_pattern, sample_component):
        """Test unwrapping a decorator."""
        decorator = LoggingDecorator(sample_component)
        unwrapped = decorator_pattern.unwrap_decorator(decorator)
        assert unwrapped is sample_component

    def test_unwrap_multiple_layers(self, decorator_pattern, sample_component):
        """Test unwrapping multiple layers."""
        decorator1 = LoggingDecorator(sample_component)
        decorator2 = CachingDecorator(decorator1)

        unwrapped = decorator_pattern.unwrap_decorator(decorator2)
        assert unwrapped is decorator1


class TestBaseComponentExtraction:
    """Test base component extraction."""

    def test_get_base_component(self, decorator_pattern, sample_component):
        """Test getting base component."""
        decorator1 = LoggingDecorator(sample_component)
        decorator2 = CachingDecorator(decorator1)
        decorator3 = TimingDecorator(decorator2)

        base = decorator_pattern.get_base_component(decorator3)
        assert base is sample_component

    def test_get_base_from_undecorated(self, decorator_pattern, sample_component):
        """Test getting base from undecorated component."""
        base = decorator_pattern.get_base_component(sample_component)
        assert base is sample_component


class TestDecorationValidation:
    """Test decoration validation."""

    def test_validate_decorated_component(self, decorator_pattern, sample_component):
        """Test validating decorated component."""
        decorator = LoggingDecorator(sample_component)
        validation = decorator_pattern.validate_decoration(decorator)
        assert validation.valid is True
        assert validation.depth == 1
        assert "LoggingDecorator" in validation.decorator_types

    def test_validate_deep_decoration(self, decorator_pattern, sample_component):
        """Test validating deep decoration stack."""
        result = decorator_pattern.stack_decorators(
            sample_component,
            ["logging", "caching", "timing", "validation", "retry", "compression"]
        )
        validation = decorator_pattern.validate_decoration(result.decorated_component)
        assert validation.valid is True
        assert validation.depth == 6
        assert len(validation.warnings) > 0  # Performance warning


class TestDecoratorComposition:
    """Test decorator composition."""

    def test_compose_decorators(self, decorator_pattern):
        """Test composing multiple decorator types."""
        decorators = [LoggingDecorator, CachingDecorator, TimingDecorator]
        composed = decorator_pattern.compose_decorators(decorators)
        assert composed is not None
        assert len(composed.component_types) == 3

    def test_composition_disabled(self, sample_component):
        """Test composition when disabled."""
        config = DecoratorConfig(enable_composition=False)
        pattern = DecoratorPatternFSA(config)

        decorators = [LoggingDecorator, CachingDecorator]
        composed = pattern.compose_decorators(decorators)
        assert composed.decorator_class is None


class TestDecoratorChainApplication:
    """Test decorator chain application."""

    def test_apply_decorator_chain(self, decorator_pattern, sample_component):
        """Test applying decorator chain."""
        chain = DecoratorChain(
            decorators=[LoggingDecorator, CachingDecorator, TimingDecorator]
        )
        result = decorator_pattern.apply_decorator_chain(sample_component, chain)
        assert result.applied is True
        assert result.chain_length == 3
        assert result.decorated_component is not None

    def test_apply_empty_chain(self, decorator_pattern, sample_component):
        """Test applying empty chain."""
        chain = DecoratorChain(decorators=[])
        result = decorator_pattern.apply_decorator_chain(sample_component, chain)
        assert result.applied is True
        assert result.chain_length == 0


class TestChainQueries:
    """Test decorator chain queries."""

    def test_get_decorator_chain(self, decorator_pattern, sample_component):
        """Test getting decorator chain."""
        decorator1 = LoggingDecorator(sample_component)
        decorator2 = CachingDecorator(decorator1)
        decorator3 = TimingDecorator(decorator2)

        chain = decorator_pattern.get_decorator_chain(decorator3)
        assert len(chain) == 3
        assert isinstance(chain[0], TimingDecorator)
        assert isinstance(chain[1], CachingDecorator)
        assert isinstance(chain[2], LoggingDecorator)


class TestDecoratorCounting:
    """Test decorator counting."""

    def test_count_decorators(self, decorator_pattern, sample_component):
        """Test counting decorators."""
        decorator1 = LoggingDecorator(sample_component)
        decorator2 = CachingDecorator(decorator1)

        count = decorator_pattern.count_decorators(decorator2)
        assert count == 2

    def test_count_undecorated(self, decorator_pattern, sample_component):
        """Test counting undecorated component."""
        count = decorator_pattern.count_decorators(sample_component)
        assert count == 0


class TestDecoratorPresenceChecking:
    """Test decorator presence checking."""

    def test_has_decorator(self, decorator_pattern, sample_component):
        """Test checking decorator presence."""
        decorator1 = LoggingDecorator(sample_component)
        decorator2 = CachingDecorator(decorator1)

        assert decorator_pattern.has_decorator(decorator2, CachingDecorator) is True
        assert decorator_pattern.has_decorator(decorator2, LoggingDecorator) is True
        assert decorator_pattern.has_decorator(decorator2, TimingDecorator) is False

    def test_has_decorator_undecorated(self, decorator_pattern, sample_component):
        """Test checking decorator on undecorated component."""
        assert decorator_pattern.has_decorator(sample_component, LoggingDecorator) is False


class TestDecoratorRemoval:
    """Test decorator removal."""

    def test_remove_decorator(self, decorator_pattern, sample_component):
        """Test removing specific decorator."""
        result = decorator_pattern.stack_decorators(
            sample_component,
            ["logging", "caching", "timing"]
        )

        removal = decorator_pattern.remove_decorator(
            result.decorated_component,
            CachingDecorator
        )
        assert removal.removed is True

    def test_remove_nonexistent_decorator(self, decorator_pattern, sample_component):
        """Test removing non-existent decorator."""
        decorator = LoggingDecorator(sample_component)
        removal = decorator_pattern.remove_decorator(decorator, CachingDecorator)
        assert removal.removed is False


class TestDecoratedObjectCloning:
    """Test decorated object cloning."""

    def test_clone_decorated(self, decorator_pattern, sample_component):
        """Test cloning decorated component."""
        decorator = LoggingDecorator(sample_component)
        clone_result = decorator_pattern.clone_decorated(decorator)
        assert clone_result.cloned is True
        assert clone_result.original_id != clone_result.clone_id

    def test_clone_preserves_structure(self, decorator_pattern, sample_component):
        """Test that cloning preserves decorator structure."""
        result = decorator_pattern.stack_decorators(
            sample_component,
            ["logging", "caching"]
        )
        clone_result = decorator_pattern.clone_decorated(result.decorated_component)
        assert clone_result.cloned is True


class TestDecorationMerging:
    """Test decoration merging."""

    def test_merge_decorations(self, decorator_pattern):
        """Test merging two decorated components."""
        comp1 = ConcreteComponent("value1")
        comp2 = ConcreteComponent("value2")

        dec1 = LoggingDecorator(comp1)
        dec2 = CachingDecorator(comp2)

        merge_result = decorator_pattern.merge_decorations(dec1, dec2)
        assert merge_result.merged is True
        assert merge_result.total_decorators >= 2

    def test_merge_removes_duplicates(self, decorator_pattern):
        """Test that merging removes duplicate decorators."""
        comp1 = ConcreteComponent("value1")
        comp2 = ConcreteComponent("value2")

        dec1 = LoggingDecorator(comp1)
        dec2 = LoggingDecorator(comp2)

        merge_result = decorator_pattern.merge_decorations(dec1, dec2)
        assert merge_result.merged is True
        # Should have only 1 logging decorator (duplicates removed)
        assert merge_result.total_decorators == 1


class TestDecorationOrderQueries:
    """Test decoration order queries."""

    def test_get_decoration_order(self, decorator_pattern, sample_component):
        """Test getting decoration order."""
        decorator1 = LoggingDecorator(sample_component)
        decorator2 = CachingDecorator(decorator1)
        decorator3 = TimingDecorator(decorator2)

        order = decorator_pattern.get_decoration_order(decorator3)
        assert order == ["TimingDecorator", "CachingDecorator", "LoggingDecorator"]


class TestDecoratorReordering:
    """Test decorator reordering."""

    def test_reorder_decorators(self, decorator_pattern, sample_component):
        """Test reordering decorators."""
        result = decorator_pattern.stack_decorators(
            sample_component,
            ["logging", "caching", "timing"]
        )

        current_order = decorator_pattern.get_decoration_order(result.decorated_component)
        new_order = list(reversed(current_order))

        reorder_result = decorator_pattern.reorder_decorators(
            result.decorated_component,
            new_order
        )
        assert reorder_result.reordered is True
        assert reorder_result.new_order == new_order

    def test_reorder_with_invalid_order(self, decorator_pattern, sample_component):
        """Test reordering with invalid order."""
        decorator = LoggingDecorator(sample_component)

        # Try to reorder with different decorators
        reorder_result = decorator_pattern.reorder_decorators(
            decorator,
            ["CachingDecorator", "TimingDecorator"]
        )
        assert reorder_result.reordered is False


class TestDecoratorMetrics:
    """Test decorator metrics."""

    def test_get_decorator_metrics(self, decorator_pattern, sample_component):
        """Test getting decorator metrics."""
        result = decorator_pattern.stack_decorators(
            sample_component,
            ["logging", "caching", "timing"]
        )

        metrics = decorator_pattern.get_decorator_metrics(result.decorated_component)
        assert metrics is not None
        assert metrics.decorator_count == 3
        assert len(metrics.decorator_types) == 3

    def test_metrics_track_operations(self, decorator_pattern, sample_component):
        """Test that metrics track operations."""
        decorator = LoggingDecorator(sample_component)

        # Execute some operations
        decorator.operation()
        decorator.operation()

        metrics = decorator_pattern.get_decorator_metrics(decorator)
        assert metrics is not None


class TestConditionalDecoration:
    """Test conditional decoration."""

    def test_create_conditional_decorator(self, decorator_pattern, sample_component):
        """Test creating conditional decorator."""
        decorator = LoggingDecorator(sample_component)
        condition = lambda: True

        conditional = decorator_pattern.create_conditional_decorator(condition, decorator)
        assert conditional is not None
        assert isinstance(conditional, ConditionalDecorator)
        assert conditional.decorator is decorator


class TestCachingBehavior:
    """Test caching decorator behavior."""

    def test_cache_hits_and_misses(self, sample_component):
        """Test cache hit/miss tracking."""
        caching_dec = CachingDecorator(sample_component)

        # First call - cache miss
        result1 = caching_dec.operation()
        assert caching_dec.misses == 1
        assert caching_dec.hits == 0

        # Second call - cache hit
        result2 = caching_dec.operation()
        assert caching_dec.hits == 1
        assert result1 == result2

    def test_cache_clear(self, sample_component):
        """Test clearing cache."""
        caching_dec = CachingDecorator(sample_component)

        caching_dec.operation()
        caching_dec.clear_cache()

        # After clear, next call should be a miss
        caching_dec.operation()
        assert caching_dec.misses == 2


class TestValidationBehavior:
    """Test validation decorator behavior."""

    def test_validation_passes(self, sample_component):
        """Test validation passing."""
        validator = lambda x: x is not None
        validation_dec = ValidationDecorator(sample_component, validator)

        result = validation_dec.operation()
        assert result == "test_value"
        assert validation_dec.validation_count == 1
        assert validation_dec.validation_failures == 0

    def test_validation_fails(self):
        """Test validation failing."""
        component = ConcreteComponent(None)
        validator = lambda x: x is not None
        validation_dec = ValidationDecorator(component, validator)

        with pytest.raises(ValueError):
            validation_dec.operation()

        assert validation_dec.validation_failures == 1


class TestTimingBehavior:
    """Test timing decorator behavior."""

    def test_execution_timing(self, sample_component):
        """Test execution time tracking."""
        timing_dec = TimingDecorator(sample_component)

        timing_dec.operation()
        assert len(timing_dec.execution_times) == 1
        assert timing_dec.execution_times[0] >= 0

    def test_average_time_calculation(self, sample_component):
        """Test average execution time."""
        timing_dec = TimingDecorator(sample_component)

        timing_dec.operation()
        timing_dec.operation()
        timing_dec.operation()

        avg_time = timing_dec.get_average_time()
        assert avg_time > 0
        assert len(timing_dec.execution_times) == 3


class TestRetryBehavior:
    """Test retry decorator behavior."""

    def test_retry_on_failure(self):
        """Test retry on operation failure."""
        class FailingComponent(Component):
            def __init__(self):
                super().__init__()
                self.attempts = 0

            def operation(self):
                self.attempts += 1
                if self.attempts < 3:
                    raise ValueError("Simulated failure")
                return "success"

            def get_description(self):
                return "FailingComponent"

        component = FailingComponent()
        retry_dec = RetryDecorator(component, max_retries=3)

        result = retry_dec.operation()
        assert result == "success"
        assert component.attempts == 3


class TestAuthorizationBehavior:
    """Test authorization decorator behavior."""

    def test_authorization_granted(self, sample_component):
        """Test authorized access."""
        auth_dec = AuthorizationDecorator(sample_component, required_role="user")
        auth_dec.set_role("user")

        result = auth_dec.operation()
        assert result == "test_value"
        assert auth_dec.auth_checks == 1
        assert auth_dec.auth_failures == 0

    def test_authorization_denied(self, sample_component):
        """Test unauthorized access."""
        auth_dec = AuthorizationDecorator(sample_component, required_role="admin")
        auth_dec.set_role("user")

        with pytest.raises(PermissionError):
            auth_dec.operation()

        assert auth_dec.auth_failures == 1


class TestExecuteMethod:
    """Test execute method."""

    def test_execute_operations(self, decorator_pattern):
        """Test executing decorator pattern operations."""
        ops = [
            DecoratorOp(operation="create_component", component_type="concrete", params={"value": "test"}),
        ]

        result = decorator_pattern.execute(ops)
        assert isinstance(result, DecoratorResult)
        assert result.success is True
        assert result.operations_count == 1

    def test_execute_multiple_ops(self, decorator_pattern):
        """Test executing multiple operations."""
        component = decorator_pattern.create_component("concrete", value="test")

        ops = [
            DecoratorOp(
                operation="create_decorator",
                decorator_type="logging",
                component=component
            ),
            DecoratorOp(
                operation="create_decorator",
                decorator_type="caching",
                component=component
            ),
        ]

        result = decorator_pattern.execute(ops)
        assert result.success is True
        assert result.decorations_applied == 2


class TestThreadSafety:
    """Test thread safety."""

    def test_thread_safe_pattern(self):
        """Test thread-safe pattern creation."""
        config = DecoratorConfig(thread_safe=True)
        pattern = DecoratorPatternFSA(config)
        assert pattern._lock is not None

    def test_non_thread_safe_pattern(self):
        """Test non-thread-safe pattern."""
        config = DecoratorConfig(thread_safe=False)
        pattern = DecoratorPatternFSA(config)
        assert pattern._lock is None

    def test_concurrent_decoration(self, decorator_pattern):
        """Test concurrent decoration operations."""
        components = [
            decorator_pattern.create_component("concrete", value=f"test_{i}")
            for i in range(5)
        ]

        def decorate_component(comp):
            decorator_pattern.create_decorator("logging", comp)

        threads = [threading.Thread(target=decorate_component, args=(c,)) for c in components]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # All decorators should be created successfully
        assert decorator_pattern.decoration_count == 5


class TestEdgeCases:
    """Test edge cases and error scenarios."""

    def test_empty_decorator_stack(self, decorator_pattern, sample_component):
        """Test handling empty decorator stack."""
        result = decorator_pattern.stack_decorators(sample_component, [])
        assert result.stacked is True
        assert result.layers == 0

    def test_circular_decoration_prevention(self, decorator_pattern, sample_component):
        """Test preventing circular decoration."""
        # This shouldn't cause issues as we create new decorators
        result = decorator_pattern.stack_decorators(
            sample_component,
            ["logging", "logging", "logging"]
        )
        assert result.stacked is True

    def test_max_depth_enforcement(self):
        """Test maximum depth enforcement."""
        config = DecoratorConfig(max_decorator_depth=3)
        pattern = DecoratorPatternFSA(config)

        component = pattern.create_component("concrete", value="test")
        result = pattern.stack_decorators(
            component,
            ["logging", "caching", "timing", "validation"]
        )
        assert result.stacked is False
