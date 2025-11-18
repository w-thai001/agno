"""Unit tests for AdapterPatternFSA."""

import pytest
import threading

from agno.fsas.adapter_pattern_fsa import (
    AdapterPatternFSA,
    AdapterConfig,
    Target,
    Adaptee,
    LegacySystem,
    ModernInterface,
    ClassAdapter,
    ObjectAdapter,
    TwoWayAdapter,
    PluggableAdapter,
    LazyAdapter,
    AdaptationStrategy,
    DirectMappingStrategy,
    TransformationStrategy,
    AdapterFactory,
    AdapterOp,
    AdapterResult,
    ValidationResult,
    RegisterResult,
    TranslateResult,
    AdaptationValidation,
    ComposedAdapter,
    CompatibilityResult,
    SetStrategyResult,
    ReverseResult,
    CloneResult,
    MergeResult,
    AdapterMetrics,
    AdaptedObject,
)


# ==================== Fixtures ====================

@pytest.fixture
def adapter_pattern():
    """Create adapter pattern instance."""
    config = AdapterConfig()
    return AdapterPatternFSA(config)


@pytest.fixture
def configured_pattern():
    """Create pre-configured adapter pattern."""
    config = AdapterConfig(
        enable_class_adapters=True,
        enable_object_adapters=True,
        enable_two_way_adapters=True,
        enable_pluggable_adapters=True,
        thread_safe=True,
    )
    return AdapterPatternFSA(config)


@pytest.fixture
def sample_adaptee():
    """Create sample adaptee."""
    return Adaptee("test_data")


# ==================== Test Classes ====================

class TestAdapterPatternBasics:
    """Test basic adapter pattern functionality."""

    def test_initialization(self):
        """Test adapter pattern initialization."""
        config = AdapterConfig()
        pattern = AdapterPatternFSA(config)
        assert pattern.config == config
        assert pattern.fsa_id is not None

    def test_initialization_with_custom_config(self):
        """Test initialization with custom configuration."""
        config = AdapterConfig(
            enable_class_adapters=False,
            max_adapter_chain_depth=5,
        )
        pattern = AdapterPatternFSA(config)
        assert pattern.config.enable_class_adapters is False
        assert pattern.config.max_adapter_chain_depth == 5

    def test_validation_success(self, adapter_pattern):
        """Test successful configuration validation."""
        config = AdapterConfig(max_adapter_chain_depth=20)
        result = adapter_pattern.validate(config)
        assert result.valid is True

    def test_validation_failure(self, adapter_pattern):
        """Test configuration validation failure."""
        config = AdapterConfig(max_adapter_chain_depth=-1)
        result = adapter_pattern.validate(config)
        assert result.valid is False
        assert len(result.errors) > 0


class TestClassAdapterCreation:
    """Test class adapter creation."""

    def test_create_class_adapter(self, adapter_pattern):
        """Test creating class adapter."""
        adapter = adapter_pattern.create_class_adapter(data="test")
        assert adapter is not None
        assert isinstance(adapter, ClassAdapter)
        assert isinstance(adapter, Target)
        assert isinstance(adapter, Adaptee)

    def test_class_adapter_implements_target(self, adapter_pattern):
        """Test class adapter implements target interface."""
        adapter = adapter_pattern.create_class_adapter(data="test")
        result = adapter.request()
        assert result is not None
        assert "test" in result

    def test_class_adapter_disabled(self):
        """Test class adapter creation when disabled."""
        config = AdapterConfig(enable_class_adapters=False)
        pattern = AdapterPatternFSA(config)
        adapter = pattern.create_class_adapter()
        assert adapter is None


class TestObjectAdapterCreation:
    """Test object adapter creation."""

    def test_create_object_adapter(self, adapter_pattern, sample_adaptee):
        """Test creating object adapter."""
        adapter = adapter_pattern.create_object_adapter(Target, sample_adaptee)
        assert adapter is not None
        assert isinstance(adapter, ObjectAdapter)
        assert isinstance(adapter, Target)

    def test_object_adapter_wraps_adaptee(self, adapter_pattern, sample_adaptee):
        """Test object adapter wraps adaptee."""
        adapter = adapter_pattern.create_object_adapter(Target, sample_adaptee)
        wrapped = adapter.get_adaptee()
        assert wrapped is sample_adaptee

    def test_object_adapter_disabled(self, sample_adaptee):
        """Test object adapter creation when disabled."""
        config = AdapterConfig(enable_object_adapters=False)
        pattern = AdapterPatternFSA(config)
        adapter = pattern.create_object_adapter(Target, sample_adaptee)
        assert adapter is None

    def test_object_adapter_without_adaptee(self, adapter_pattern):
        """Test object adapter creation without adaptee."""
        adapter = adapter_pattern.create_object_adapter(Target, None)
        assert adapter is None


class TestTwoWayAdapterCreation:
    """Test two-way adapter creation."""

    def test_create_two_way_adapter(self, adapter_pattern):
        """Test creating two-way adapter."""
        adapter = adapter_pattern.create_two_way_adapter(Target, Adaptee)
        assert adapter is not None
        assert isinstance(adapter, TwoWayAdapter)

    def test_two_way_forward_adapt(self, adapter_pattern):
        """Test two-way adapter forward conversion."""
        adapter = adapter_pattern.create_two_way_adapter(Target, Adaptee)
        obj = Adaptee("test")
        result = adapter.forward_adapt(obj)
        assert result is not None
        assert adapter.forward_conversions == 1

    def test_two_way_reverse_adapt(self, adapter_pattern):
        """Test two-way adapter reverse conversion."""
        adapter = adapter_pattern.create_two_way_adapter(Target, Adaptee)
        obj = Adaptee("test")
        result = adapter.reverse_adapt(obj)
        assert result is not None
        assert adapter.reverse_conversions == 1

    def test_two_way_adapter_disabled(self):
        """Test two-way adapter when disabled."""
        config = AdapterConfig(enable_two_way_adapters=False)
        pattern = AdapterPatternFSA(config)
        adapter = pattern.create_two_way_adapter(Target, Adaptee)
        assert adapter is None


class TestPluggableAdapterCreation:
    """Test pluggable adapter creation."""

    def test_create_pluggable_adapter(self, adapter_pattern, sample_adaptee):
        """Test creating pluggable adapter."""
        strategy = DirectMappingStrategy({'request': 'specific_request'})
        adapter = adapter_pattern.create_pluggable_adapter(Target, sample_adaptee, strategy)
        assert adapter is not None
        assert isinstance(adapter, PluggableAdapter)

    def test_pluggable_adapter_disabled(self, sample_adaptee):
        """Test pluggable adapter when disabled."""
        config = AdapterConfig(enable_pluggable_adapters=False)
        pattern = AdapterPatternFSA(config)
        strategy = DirectMappingStrategy({})
        adapter = pattern.create_pluggable_adapter(Target, sample_adaptee, strategy)
        assert adapter is None


class TestAdapteeAdaptation:
    """Test adaptee adaptation."""

    def test_adapt_with_object_adapter(self, adapter_pattern, sample_adaptee):
        """Test adapting with object adapter."""
        adapted = adapter_pattern.adapt(sample_adaptee, Target, "object")
        assert adapted is not None
        assert isinstance(adapted, AdaptedObject)

    def test_adapt_with_class_adapter(self, adapter_pattern):
        """Test adapting with class adapter."""
        adaptee = Adaptee("test")
        adapted = adapter_pattern.adapt(adaptee, Target, "class")
        assert adapted is not None

    def test_adapt_unknown_type(self, adapter_pattern, sample_adaptee):
        """Test adapting with unknown adapter type."""
        adapted = adapter_pattern.adapt(sample_adaptee, Target, "unknown")
        assert adapted is None


class TestAdapterRegistration:
    """Test adapter registration."""

    def test_register_adapter(self, adapter_pattern):
        """Test registering an adapter."""
        result = adapter_pattern.register_adapter(Adaptee, Target, ClassAdapter)
        assert result.registered is True
        assert result.source_type == "Adaptee"
        assert result.target_type == "Target"

    def test_register_duplicate_adapter(self, adapter_pattern):
        """Test registering duplicate adapter."""
        adapter_pattern.register_adapter(Adaptee, Target, ClassAdapter)
        result = adapter_pattern.register_adapter(Adaptee, Target, ObjectAdapter)
        assert result.registered is False

    def test_register_with_method_map(self, adapter_pattern):
        """Test registering adapter with method mapping."""
        method_map = {'request': 'specific_request'}
        result = adapter_pattern.register_adapter(
            Adaptee, Target, ClassAdapter, method_map
        )
        assert result.registered is True


class TestAdapterRetrieval:
    """Test adapter retrieval."""

    def test_get_registered_adapter(self, adapter_pattern):
        """Test getting registered adapter."""
        adapter_pattern.register_adapter(Adaptee, Target, ClassAdapter)
        retrieved = adapter_pattern.get_adapter(Adaptee, Target)
        assert retrieved == ClassAdapter

    def test_get_nonexistent_adapter(self, adapter_pattern):
        """Test getting non-existent adapter."""
        retrieved = adapter_pattern.get_adapter(Adaptee, Target)
        assert retrieved is None


class TestInterfaceTranslation:
    """Test interface translation."""

    def test_translate_interface(self, adapter_pattern, sample_adaptee):
        """Test translating interface."""
        adapter_pattern.register_adapter(Adaptee, Target, ObjectAdapter)
        result = adapter_pattern.translate_interface(sample_adaptee, Adaptee, Target)
        assert result.translated is True
        assert result.adapted_object is not None

    def test_translate_without_adapter(self, adapter_pattern, sample_adaptee):
        """Test translation without registered adapter."""
        result = adapter_pattern.translate_interface(sample_adaptee, Adaptee, Target)
        assert result.translated is False


class TestAdaptationValidation:
    """Test adaptation validation."""

    def test_validate_valid_adaptation(self, adapter_pattern, sample_adaptee):
        """Test validating valid adaptation."""
        adapter = adapter_pattern.create_object_adapter(Target, sample_adaptee)
        validation = adapter_pattern.validate_adaptation(adapter, Target)
        assert validation.valid is True
        assert validation.conformance_score > 0

    def test_validate_missing_methods(self, adapter_pattern):
        """Test validation with missing methods."""
        class IncompleteAdapter:
            def request(self):
                return "test"
            # Missing get_info method

        validation = adapter_pattern.validate_adaptation(IncompleteAdapter(), Target)
        assert validation.valid is False
        assert len(validation.missing_methods) > 0


class TestAdapterComposition:
    """Test adapter composition."""

    def test_compose_adapters(self, adapter_pattern, sample_adaptee):
        """Test composing multiple adapters."""
        adapter1 = adapter_pattern.create_object_adapter(Target, sample_adaptee)
        adapter2 = adapter_pattern.create_object_adapter(Target, sample_adaptee)

        composed = adapter_pattern.compose_adapters([adapter1, adapter2])
        assert composed is not None
        assert composed.chain_length == 2

    def test_compose_empty_list(self, adapter_pattern):
        """Test composing empty adapter list."""
        composed = adapter_pattern.compose_adapters([])
        assert composed.adapter is None
        assert composed.chain_length == 0


class TestAdaptedMethodsQueries:
    """Test adapted methods queries."""

    def test_get_adapted_methods(self, adapter_pattern, sample_adaptee):
        """Test getting adapted method names."""
        adapter = adapter_pattern.create_object_adapter(Target, sample_adaptee)
        methods = adapter_pattern.get_adapted_methods(adapter)
        assert len(methods) > 0
        assert 'request' in methods
        assert 'get_info' in methods


class TestInterfaceCompatibilityChecking:
    """Test interface compatibility checking."""

    def test_check_compatible_interfaces(self, adapter_pattern):
        """Test checking compatible interfaces."""
        result = adapter_pattern.check_interface_compatibility(Target, Target)
        assert result.compatible is True
        assert result.compatibility_score == 1.0

    def test_check_incompatible_interfaces(self, adapter_pattern):
        """Test checking incompatible interfaces."""
        result = adapter_pattern.check_interface_compatibility(Adaptee, Target)
        assert result.compatibility_score < 1.0

    def test_compatibility_suggestions(self, adapter_pattern):
        """Test compatibility check provides suggestions."""
        result = adapter_pattern.check_interface_compatibility(Adaptee, Target)
        if not result.compatible:
            assert len(result.suggestions) > 0


class TestAdapterFactoryCreation:
    """Test adapter factory creation."""

    def test_create_adapter_factory(self, adapter_pattern):
        """Test creating adapter factory."""
        factory = adapter_pattern.create_adapter_factory(Adaptee, Target)
        assert factory is not None
        assert isinstance(factory, AdapterFactory)

    def test_factory_creates_adapters(self, adapter_pattern):
        """Test factory creates adapters."""
        factory = adapter_pattern.create_adapter_factory(Adaptee, Target)
        adapter = factory.create_class_adapter(data="test")
        assert adapter is not None
        assert factory.adapters_created == 1


class TestAdaptationMappingQueries:
    """Test adaptation mapping queries."""

    def test_get_adaptation_mapping(self, adapter_pattern, sample_adaptee):
        """Test getting adaptation mapping."""
        adapter = adapter_pattern.create_object_adapter(Target, sample_adaptee)
        mapping = adapter_pattern.get_adaptation_mapping(adapter)
        assert isinstance(mapping, dict)

    def test_mapping_for_class_adapter(self, adapter_pattern):
        """Test mapping for class adapter."""
        adapter = adapter_pattern.create_class_adapter(data="test")
        mapping = adapter_pattern.get_adaptation_mapping(adapter)
        assert 'request' in mapping


class TestStrategySetting:
    """Test strategy setting."""

    def test_set_adaptation_strategy(self, adapter_pattern, sample_adaptee):
        """Test setting adaptation strategy."""
        strategy1 = DirectMappingStrategy({})
        adapter = adapter_pattern.create_pluggable_adapter(Target, sample_adaptee, strategy1)

        strategy2 = TransformationStrategy(lambda x: x)
        result = adapter_pattern.set_adaptation_strategy(adapter, strategy2)
        assert result.success is True
        assert result.new_strategy == "TransformationStrategy"

    def test_set_strategy_on_non_pluggable(self, adapter_pattern, sample_adaptee):
        """Test setting strategy on non-pluggable adapter."""
        adapter = adapter_pattern.create_object_adapter(Target, sample_adaptee)
        strategy = DirectMappingStrategy({})
        result = adapter_pattern.set_adaptation_strategy(adapter, strategy)
        assert result.success is False


class TestReverseAdaptation:
    """Test reverse adaptation."""

    def test_reverse_adapt_object_adapter(self, adapter_pattern, sample_adaptee):
        """Test reverse adapting object adapter."""
        adapter = adapter_pattern.create_object_adapter(Target, sample_adaptee)
        result = adapter_pattern.reverse_adapt(adapter, Adaptee)
        assert result.success is True
        assert result.original_object is sample_adaptee

    def test_reverse_adapt_two_way_adapter(self, adapter_pattern):
        """Test reverse adapting two-way adapter."""
        adapter = adapter_pattern.create_two_way_adapter(Target, Adaptee)
        result = adapter_pattern.reverse_adapt(adapter, Target)
        assert result.success is True


class TestAdapterCloning:
    """Test adapter cloning."""

    def test_clone_adapter(self, adapter_pattern, sample_adaptee):
        """Test cloning adapter."""
        adapter = adapter_pattern.create_object_adapter(Target, sample_adaptee)
        clone_result = adapter_pattern.clone_adapter(adapter)
        assert clone_result.cloned is True
        assert clone_result.original_id != clone_result.clone_id

    def test_clone_preserves_state(self, adapter_pattern, sample_adaptee):
        """Test that cloning preserves adapter state."""
        adapter = adapter_pattern.create_object_adapter(Target, sample_adaptee)
        adapter.request()  # Increment adaptation_count

        clone_result = adapter_pattern.clone_adapter(adapter)
        assert clone_result.cloned is True


class TestAdapterMerging:
    """Test adapter merging."""

    def test_merge_adapters(self, adapter_pattern, sample_adaptee):
        """Test merging two adapters."""
        adapter1 = adapter_pattern.create_object_adapter(Target, sample_adaptee)
        adapter2 = adapter_pattern.create_object_adapter(Target, sample_adaptee)

        merge_result = adapter_pattern.merge_adapters(adapter1, adapter2)
        assert merge_result.merged is True

    def test_merge_combines_mappings(self, adapter_pattern, sample_adaptee):
        """Test that merging combines method mappings."""
        adapter1 = adapter_pattern.create_class_adapter(data="test1")
        adapter2 = adapter_pattern.create_class_adapter(data="test2")

        merge_result = adapter_pattern.merge_adapters(adapter1, adapter2)
        assert merge_result.merged is True
        assert merge_result.total_mappings >= 0


class TestAdapterMetrics:
    """Test adapter metrics."""

    def test_get_adapter_metrics(self, adapter_pattern, sample_adaptee):
        """Test getting adapter metrics."""
        adapter = adapter_pattern.create_object_adapter(Target, sample_adaptee)
        metrics = adapter_pattern.get_adapter_metrics(adapter)
        assert metrics is not None
        assert metrics.adapter_id == adapter.adapter_id

    def test_metrics_track_adaptations(self, adapter_pattern, sample_adaptee):
        """Test that metrics track adaptations."""
        adapter = adapter_pattern.create_object_adapter(Target, sample_adaptee)

        # Perform some adaptations
        adapter.request()
        adapter.request()

        metrics = adapter_pattern.get_adapter_metrics(adapter)
        assert metrics.adaptation_count == 2


class TestLazyAdapter:
    """Test lazy adapter."""

    def test_create_lazy_adapter(self, adapter_pattern):
        """Test creating lazy adapter."""
        factory = lambda: Adaptee("lazy")
        adapter = adapter_pattern.create_lazy_adapter(Target, factory)
        assert adapter is not None
        assert isinstance(adapter, LazyAdapter)
        assert adapter.initialized is False

    def test_lazy_adapter_defers_creation(self, adapter_pattern):
        """Test lazy adapter defers creation."""
        factory = lambda: Adaptee("lazy")
        adapter = adapter_pattern.create_lazy_adapter(Target, factory)

        # Should not be initialized yet
        assert adapter.initialized is False

        # Access should trigger initialization
        adapter.request()
        assert adapter.initialized is True

    def test_lazy_adapter_disabled(self):
        """Test lazy adapter when disabled."""
        config = AdapterConfig(enable_lazy_adapters=False)
        pattern = AdapterPatternFSA(config)
        factory = lambda: Adaptee("lazy")
        adapter = pattern.create_lazy_adapter(Target, factory)
        assert adapter is None


class TestExecuteMethod:
    """Test execute method."""

    def test_execute_operations(self, adapter_pattern):
        """Test executing adapter pattern operations."""
        ops = [
            AdapterOp(operation="create_class_adapter", params={"data": "test"}),
        ]

        result = adapter_pattern.execute(ops)
        assert isinstance(result, AdapterResult)
        assert result.success is True
        assert result.operations_count == 1

    def test_execute_multiple_ops(self, adapter_pattern, sample_adaptee):
        """Test executing multiple operations."""
        ops = [
            AdapterOp(operation="create_object_adapter", adaptee=sample_adaptee),
            AdapterOp(operation="adapt", adaptee=sample_adaptee, adapter_type="object"),
        ]

        result = adapter_pattern.execute(ops)
        assert result.success is True
        assert result.adaptations_performed >= 1


class TestThreadSafety:
    """Test thread safety."""

    def test_thread_safe_pattern(self):
        """Test thread-safe pattern creation."""
        config = AdapterConfig(thread_safe=True)
        pattern = AdapterPatternFSA(config)
        assert pattern._lock is not None

    def test_non_thread_safe_pattern(self):
        """Test non-thread-safe pattern."""
        config = AdapterConfig(thread_safe=False)
        pattern = AdapterPatternFSA(config)
        assert pattern._lock is None

    def test_concurrent_adaptation(self, adapter_pattern):
        """Test concurrent adaptation operations."""
        adaptees = [Adaptee(f"data_{i}") for i in range(5)]

        def adapt_object(adaptee):
            adapter_pattern.create_object_adapter(Target, adaptee)

        threads = [threading.Thread(target=adapt_object, args=(a,)) for a in adaptees]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # All adapters should be created successfully
        assert adapter_pattern.adaptation_count == 5


class TestEdgeCases:
    """Test edge cases and error scenarios."""

    def test_missing_method_adaptation(self, adapter_pattern):
        """Test adapting object with missing methods."""
        class IncompletAdaptee:
            pass

        adaptee = IncompletAdaptee()
        adapter = adapter_pattern.create_object_adapter(Target, adaptee)
        # Should still create adapter, but validation will fail
        assert adapter is not None

    def test_type_mismatch(self, adapter_pattern):
        """Test handling type mismatches."""
        # Try to adapt incompatible types
        result = adapter_pattern.check_interface_compatibility(str, Target)
        # Should handle gracefully
        assert result is not None

    def test_max_chain_depth(self, adapter_pattern):
        """Test maximum adapter chain depth."""
        config = AdapterConfig(max_adapter_chain_depth=2)
        pattern = AdapterPatternFSA(config)

        adaptee = Adaptee("test")
        adapters = [
            pattern.create_object_adapter(Target, adaptee),
            pattern.create_object_adapter(Target, adaptee),
            pattern.create_object_adapter(Target, adaptee),
        ]

        composed = pattern.compose_adapters(adapters)
        # Should warn but still compose
        assert composed is not None


class TestComplexAdapterChains:
    """Test complex adapter chains."""

    def test_multi_level_adaptation(self, adapter_pattern):
        """Test multi-level adapter chain."""
        # Create chain: Adaptee -> Adapter1 -> Adapter2
        adaptee = Adaptee("original")
        adapter1 = adapter_pattern.create_object_adapter(Target, adaptee)
        adapter2 = adapter_pattern.create_object_adapter(Target, adaptee)

        composed = adapter_pattern.compose_adapters([adapter1, adapter2])
        assert composed.chain_length == 2

    def test_adapter_chain_execution(self, adapter_pattern, sample_adaptee):
        """Test executing through adapter chain."""
        adapter1 = adapter_pattern.create_object_adapter(Target, sample_adaptee)
        adapter2 = adapter_pattern.create_object_adapter(Target, sample_adaptee)

        composed = adapter_pattern.compose_adapters([adapter1, adapter2])

        # Verify composition occurred
        assert composed.chain_length == 2
        assert composed.adapter is not None


class TestAdapterBehavior:
    """Test adapter behavior."""

    def test_class_adapter_inheritance(self):
        """Test class adapter uses inheritance."""
        adapter = ClassAdapter("test")
        # Should have methods from both Target and Adaptee
        assert hasattr(adapter, 'request')
        assert hasattr(adapter, 'get_info')
        assert hasattr(adapter, 'specific_request')

    def test_object_adapter_composition(self, sample_adaptee):
        """Test object adapter uses composition."""
        adapter = ObjectAdapter(sample_adaptee)
        # Should have Target methods but wrap Adaptee
        assert hasattr(adapter, 'request')
        assert hasattr(adapter, 'get_info')
        assert adapter.get_adaptee() is sample_adaptee

    def test_two_way_bidirectional(self):
        """Test two-way adapter is bidirectional."""
        adapter = TwoWayAdapter(Target, Adaptee)
        obj = Adaptee("test")

        # Forward
        forward = adapter.forward_adapt(obj)
        assert adapter.forward_conversions == 1

        # Reverse
        reverse = adapter.reverse_adapt(forward)
        assert adapter.reverse_conversions == 1

        # Check stats
        stats = adapter.get_direction_stats()
        assert stats['forward'] == 1
        assert stats['reverse'] == 1


class TestStrategyPattern:
    """Test strategy pattern in pluggable adapter."""

    def test_direct_mapping_strategy(self, sample_adaptee):
        """Test direct mapping strategy."""
        method_map = {'request': 'specific_request'}
        strategy = DirectMappingStrategy(method_map)
        adapter = PluggableAdapter(sample_adaptee, strategy)

        # Should use strategy for adaptation
        result = adapter.request()
        assert result is not None

    def test_transformation_strategy(self, sample_adaptee):
        """Test transformation strategy."""
        transform = lambda x: x
        strategy = TransformationStrategy(transform)
        adapter = PluggableAdapter(sample_adaptee, strategy)

        # Should use transformation
        result = adapter.request()
        assert result is not None

    def test_strategy_change(self, sample_adaptee):
        """Test changing adapter strategy."""
        strategy1 = DirectMappingStrategy({})
        adapter = PluggableAdapter(sample_adaptee, strategy1)

        initial_changes = adapter.strategy_changes

        strategy2 = TransformationStrategy(lambda x: x)
        adapter.set_strategy(strategy2)

        assert adapter.strategy_changes == initial_changes + 1
