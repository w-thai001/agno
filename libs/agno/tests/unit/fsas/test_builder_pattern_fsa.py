"""Unit tests for BuilderPatternFSA."""

import pytest
import time

from agno.fsas.builder_pattern_fsa import (
    BuilderPatternFSA,
    Builder,
    Product,
    Director,
    BuilderConfig,
    BuildState,
    StepStatus,
    House,
    Car,
    Computer,
    HouseBuilder,
    CarBuilder,
    ComputerBuilder,
    HouseDirector,
    CarDirector,
    LazyBuilder,
    BuildStep,
    BuilderOp,
    BuilderResult,
    ValidationResult,
    RegisterResult,
    StepResult,
    StepValidation,
    ResetResult,
    DirectorResult,
    FluentResult,
    ChainResult,
    BuildContext,
    BuildStateSnapshot,
    RestoreResult,
    BuildHistory,
    ImmutableProduct,
    CloneResult,
    MergeResult,
    ProductValidation,
    BuilderMetrics,
)


# ==================== Fixtures ====================

@pytest.fixture
def builder_pattern():
    """Create builder pattern instance."""
    config = BuilderConfig()
    return BuilderPatternFSA(config)


@pytest.fixture
def configured_pattern():
    """Create pre-configured builder pattern."""
    config = BuilderConfig(
        enable_validation=True,
        enable_history=True,
        enable_immutability=True,
        enable_state_snapshots=True,
        thread_safe=True,
    )
    pattern = BuilderPatternFSA(config)

    # Register a builder
    builder = HouseBuilder()
    pattern.register_builder("test_builder", builder)

    return pattern


# ==================== Test Classes ====================

class TestBuilderPatternBasics:
    """Test basic builder pattern functionality."""

    def test_initialization(self):
        """Test builder pattern initialization."""
        config = BuilderConfig()
        pattern = BuilderPatternFSA(config)
        assert pattern.config == config
        assert pattern.fsa_id is not None

    def test_initialization_with_custom_config(self):
        """Test initialization with custom configuration."""
        config = BuilderConfig(
            enable_validation=False,
            enable_history=False,
        )
        pattern = BuilderPatternFSA(config)
        assert pattern.config.enable_validation is False
        assert pattern.config.enable_history is False

    def test_validation_success(self, builder_pattern):
        """Test successful configuration validation."""
        config = BuilderConfig(max_builders=500)
        result = builder_pattern.validate(config)
        assert result.valid is True

    def test_validation_failure(self, builder_pattern):
        """Test configuration validation failure."""
        config = BuilderConfig(max_builders=-1)
        result = builder_pattern.validate(config)
        assert result.valid is False
        assert len(result.errors) > 0


class TestBuilderCreation:
    """Test builder creation."""

    def test_create_builder(self, builder_pattern):
        """Test creating a builder."""
        builder = builder_pattern.create_builder("house")
        assert builder is not None
        assert isinstance(builder, HouseBuilder)

    def test_create_car_builder(self, builder_pattern):
        """Test creating car builder."""
        builder = builder_pattern.create_builder("car")
        assert builder is not None
        assert isinstance(builder, CarBuilder)

    def test_create_unknown_builder(self, builder_pattern):
        """Test creating unknown builder type."""
        builder = builder_pattern.create_builder("unknown")
        assert builder is None


class TestBuilderRegistration:
    """Test builder registration."""

    def test_register_builder(self, builder_pattern):
        """Test registering a builder."""
        builder = HouseBuilder()
        result = builder_pattern.register_builder("my_builder", builder)
        assert result.registered is True
        assert result.builder_name == "my_builder"

    def test_register_duplicate_builder(self):
        """Test registering duplicate builder."""
        config = BuilderConfig(allow_override=False)
        pattern = BuilderPatternFSA(config)

        builder1 = HouseBuilder()
        pattern.register_builder("dup_builder", builder1)

        builder2 = HouseBuilder()
        result = pattern.register_builder("dup_builder", builder2)
        assert result.registered is False

    def test_register_with_override(self):
        """Test registering builder with override allowed."""
        config = BuilderConfig(allow_override=True)
        pattern = BuilderPatternFSA(config)

        builder1 = HouseBuilder()
        pattern.register_builder("builder", builder1)

        builder2 = HouseBuilder()
        result = pattern.register_builder("builder", builder2)
        assert result.registered is True


class TestBuilderRetrieval:
    """Test builder retrieval."""

    def test_get_builder(self, configured_pattern):
        """Test getting a builder."""
        builder = configured_pattern.get_builder("test_builder")
        assert builder is not None
        assert isinstance(builder, HouseBuilder)

    def test_get_nonexistent_builder(self, builder_pattern):
        """Test getting non-existent builder."""
        builder = builder_pattern.get_builder("nonexistent")
        assert builder is None


class TestBuildStepExecution:
    """Test build step execution."""

    def test_build_step(self, configured_pattern):
        """Test executing a build step."""
        builder = configured_pattern.get_builder("test_builder")
        result = configured_pattern.build_step(
            builder,
            "build_foundation",
            {"material": "concrete"}
        )
        assert result.executed is True

    def test_build_step_unknown_method(self, configured_pattern):
        """Test executing unknown build step."""
        builder = configured_pattern.get_builder("test_builder")
        result = configured_pattern.build_step(builder, "unknown_step", {})
        assert result.executed is False

    def test_build_step_multiple(self, configured_pattern):
        """Test executing multiple build steps."""
        builder = configured_pattern.get_builder("test_builder")

        result1 = configured_pattern.build_step(builder, "build_foundation", {})
        result2 = configured_pattern.build_step(builder, "build_walls", {})

        assert result1.executed is True
        assert result2.executed is True
        assert len(builder.build_steps) == 2


class TestStepValidation:
    """Test step validation."""

    def test_validate_step(self, configured_pattern):
        """Test validating a step."""
        builder = configured_pattern.get_builder("test_builder")
        result = configured_pattern.validate_step(builder, "build_foundation")
        assert result.valid is True

    def test_validate_invalid_step(self, configured_pattern):
        """Test validating invalid step."""
        builder = configured_pattern.get_builder("test_builder")
        result = configured_pattern.validate_step(builder, "unknown_method")
        assert result.valid is False

    def test_validate_step_disabled(self):
        """Test validation when disabled."""
        config = BuilderConfig(enable_validation=False)
        pattern = BuilderPatternFSA(config)

        builder = HouseBuilder()
        result = pattern.validate_step(builder, "build_foundation")
        assert len(result.warnings) > 0


class TestBuilderReset:
    """Test builder reset."""

    def test_reset_builder(self, configured_pattern):
        """Test resetting a builder."""
        builder = configured_pattern.get_builder("test_builder")

        # Execute some steps
        configured_pattern.build_step(builder, "build_foundation", {})

        # Reset
        result = configured_pattern.reset_builder(builder)
        assert result.reset is True
        assert builder.state == BuildState.INITIALIZED


class TestProductRetrieval:
    """Test product retrieval."""

    def test_get_result(self, configured_pattern):
        """Test getting constructed product."""
        builder = configured_pattern.get_builder("test_builder")

        # Complete construction
        builder.build_foundation()
        builder.build_walls()
        builder.build_roof()

        product = configured_pattern.get_result(builder)
        assert product is not None
        assert isinstance(product, House)

    def test_get_result_incomplete(self, configured_pattern):
        """Test getting result from incomplete builder."""
        builder = configured_pattern.get_builder("test_builder")

        # Don't complete construction
        product = configured_pattern.get_result(builder)
        assert product is None


class TestDirectorCreation:
    """Test director creation."""

    def test_create_director(self, builder_pattern):
        """Test creating a director."""
        builder = HouseBuilder()
        director = builder_pattern.create_director("house", builder)
        assert director is not None
        assert isinstance(director, HouseDirector)

    def test_create_car_director(self, builder_pattern):
        """Test creating car director."""
        builder = CarBuilder()
        director = builder_pattern.create_director("car", builder)
        assert director is not None
        assert isinstance(director, CarDirector)

    def test_create_director_disabled(self):
        """Test creating director when disabled."""
        config = BuilderConfig(enable_directors=False)
        pattern = BuilderPatternFSA(config)

        builder = HouseBuilder()
        director = pattern.create_director("house", builder)
        assert director is None


class TestDirectorConstruction:
    """Test director-based construction."""

    def test_construct_with_director(self, builder_pattern):
        """Test using director for construction."""
        builder = HouseBuilder()
        director = builder_pattern.create_director("house", builder)

        result = builder_pattern.construct_with_director(
            director,
            "construct_simple_house"
        )
        assert result.constructed is True
        # Check that construction actually happened via history
        assert len(builder.build_history) > 0

    def test_construct_luxury_house(self, builder_pattern):
        """Test constructing luxury house with director."""
        builder = HouseBuilder()
        director = HouseDirector(builder)

        result = builder_pattern.construct_with_director(
            director,
            "construct_luxury_house"
        )
        assert result.constructed is True


class TestFluentMethodAddition:
    """Test fluent method addition."""

    def test_add_fluent_method(self, builder_pattern):
        """Test adding a fluent method."""
        builder = HouseBuilder()

        def custom_method(self):
            return self

        result = builder_pattern.add_fluent_method(
            builder,
            "custom_step",
            custom_method
        )
        assert result.added is True

    def test_add_fluent_disabled(self):
        """Test adding fluent method when disabled."""
        config = BuilderConfig(enable_fluent_interface=False)
        pattern = BuilderPatternFSA(config)

        builder = HouseBuilder()
        result = pattern.add_fluent_method(builder, "custom", lambda: None)
        assert result.added is False


class TestBuildStepChaining:
    """Test build step chaining."""

    def test_chain_build_steps(self, builder_pattern):
        """Test chaining build steps."""
        builder = HouseBuilder()

        steps = [
            BuildStep(name="build_foundation", params={"material": "concrete"}),
            BuildStep(name="build_walls", params={"material": "brick"}),
            BuildStep(name="build_roof", params={"material": "tile"}),
        ]

        result = builder_pattern.chain_build_steps(builder, steps)
        assert result.executed is True
        assert result.steps_completed == 3

    def test_chain_with_failure(self, builder_pattern):
        """Test chaining with step failure."""
        builder = HouseBuilder()

        steps = [
            BuildStep(name="build_foundation"),
            BuildStep(name="unknown_step"),
        ]

        result = builder_pattern.chain_build_steps(builder, steps)
        assert result.executed is False
        assert len(result.errors) > 0


class TestBuildContextCreation:
    """Test build context creation."""

    def test_create_build_context(self, builder_pattern):
        """Test creating a build context."""
        context = builder_pattern.create_build_context({"key": "value"})
        assert context is not None
        assert context.params["key"] == "value"


class TestBuildStateSave:
    """Test build state save."""

    def test_save_build_state(self, builder_pattern):
        """Test saving builder state."""
        builder = HouseBuilder()
        builder.build_foundation()

        snapshot = builder_pattern.save_build_state(builder)
        assert snapshot is not None
        assert snapshot.state == BuildState.IN_PROGRESS

    def test_save_state_disabled(self):
        """Test saving state when disabled."""
        config = BuilderConfig(enable_state_snapshots=False)
        pattern = BuilderPatternFSA(config)

        builder = HouseBuilder()
        snapshot = pattern.save_build_state(builder)
        assert snapshot is None


class TestBuildStateRestore:
    """Test build state restore."""

    def test_restore_build_state(self, builder_pattern):
        """Test restoring builder state."""
        builder = HouseBuilder()
        builder.build_foundation()

        # Save state
        snapshot = builder_pattern.save_build_state(builder)

        # Modify builder
        builder.build_walls()

        # Restore
        result = builder_pattern.restore_build_state(builder, snapshot)
        assert result.restored is True


class TestBuildHistoryQueries:
    """Test build history queries."""

    def test_get_build_history(self, builder_pattern):
        """Test getting build history."""
        builder = HouseBuilder()
        builder.build_foundation()
        builder.build_walls()

        history = builder_pattern.get_build_history(builder)
        assert history is not None
        assert len(history.history_entries) > 0

    def test_get_history_disabled(self):
        """Test getting history when disabled."""
        config = BuilderConfig(enable_history=False)
        pattern = BuilderPatternFSA(config)

        builder = HouseBuilder()
        history = pattern.get_build_history(builder)
        assert len(history.steps) == 0


class TestImmutabilityEnforcement:
    """Test immutability enforcement."""

    def test_make_immutable(self, builder_pattern):
        """Test making product immutable."""
        builder = HouseBuilder()
        builder.build_foundation()
        builder.build_walls()
        builder.build_roof()

        product = builder.get_result()
        immutable = builder_pattern.make_immutable(product)

        assert immutable is not None
        assert product.is_immutable is True

    def test_immutable_cannot_modify(self, builder_pattern):
        """Test that immutable product cannot be modified."""
        builder = HouseBuilder()
        builder.build_foundation()
        builder.build_walls()
        builder.build_roof()

        product = builder.get_result()
        builder_pattern.make_immutable(product)

        with pytest.raises(ValueError):
            product.set_property("new_property", "value")

    def test_immutability_disabled(self):
        """Test immutability when disabled."""
        config = BuilderConfig(enable_immutability=False)
        pattern = BuilderPatternFSA(config)

        product = House()
        immutable = pattern.make_immutable(product)
        assert immutable is None


class TestBuilderCloning:
    """Test builder cloning."""

    def test_clone_builder(self, builder_pattern):
        """Test cloning a builder."""
        builder = HouseBuilder()
        builder.build_foundation()

        result = builder_pattern.clone_builder(builder)
        assert result.cloned is True
        assert result.original_id != result.clone_id

    def test_clone_car_builder(self, builder_pattern):
        """Test cloning car builder."""
        builder = CarBuilder()
        builder.build_engine()

        result = builder_pattern.clone_builder(builder)
        assert result.cloned is True


class TestBuilderMerging:
    """Test builder merging."""

    def test_merge_builders(self, builder_pattern):
        """Test merging multiple builders."""
        builder1 = HouseBuilder()
        builder1.build_foundation("concrete")

        builder2 = HouseBuilder()
        builder2.build_walls("brick")

        result = builder_pattern.merge_builders([builder1, builder2])
        assert result.merged is True
        assert result.source_count == 2

    def test_merge_empty_list(self, builder_pattern):
        """Test merging empty builder list."""
        result = builder_pattern.merge_builders([])
        assert result.merged is False


class TestProductValidation:
    """Test product validation."""

    def test_validate_product(self, builder_pattern):
        """Test validating a product."""
        builder = HouseBuilder()
        builder.build_foundation("concrete")
        builder.build_walls("brick")
        builder.build_roof("tile")

        product = builder.get_result()
        schema = {
            "required": ["foundation", "walls", "roof"],
        }

        result = builder_pattern.validate_product(product, schema)
        assert result.valid is True

    def test_validate_incomplete_product(self, builder_pattern):
        """Test validating incomplete product."""
        builder = HouseBuilder()
        builder.build_foundation()

        # Don't complete
        builder.state = BuildState.COMPLETED
        product = builder.get_result()

        schema = {
            "required": ["foundation", "walls", "roof"],
        }

        result = builder_pattern.validate_product(product, schema)
        assert result.valid is False


class TestBuilderMetrics:
    """Test builder metrics."""

    def test_get_builder_metrics(self, builder_pattern):
        """Test getting builder metrics."""
        builder = HouseBuilder()
        builder_pattern.build_step(builder, "build_foundation", {})
        builder_pattern.build_step(builder, "build_walls", {})

        metrics = builder_pattern.get_builder_metrics(builder)
        assert metrics is not None
        assert metrics.steps_completed == 2


class TestLazyBuilder:
    """Test lazy builder."""

    def test_create_lazy_builder(self, builder_pattern):
        """Test creating a lazy builder."""
        lazy_builder = builder_pattern.create_lazy_builder("house")
        assert lazy_builder is not None
        assert isinstance(lazy_builder, LazyBuilder)

    def test_lazy_builder_deferred_construction(self, builder_pattern):
        """Test lazy builder defers construction."""
        lazy_builder = builder_pattern.create_lazy_builder("house")

        # Defer operations
        lazy_builder.defer_operation("build_foundation", material="concrete")
        lazy_builder.defer_operation("build_walls", material="brick")
        lazy_builder.defer_operation("build_roof", material="tile")

        # Get result triggers construction
        product = lazy_builder.get_result()
        assert product is not None


class TestExecuteMethod:
    """Test execute method."""

    def test_execute_operations(self, builder_pattern):
        """Test executing builder pattern operations."""
        ops = [
            BuilderOp(operation="create", builder_type="house"),
        ]

        result = builder_pattern.execute(ops)
        assert isinstance(result, BuilderResult)
        assert result.success is True

    def test_execute_multiple_ops(self, builder_pattern):
        """Test executing multiple operations."""
        builder = HouseBuilder()
        ops = [
            BuilderOp(operation="register", builder_name="builder", builder=builder),
            BuilderOp(
                operation="build_step",
                builder=builder,
                step_name="build_foundation",
                params={},
            ),
        ]

        result = builder_pattern.execute(ops)
        assert result.success is True


class TestEdgeCases:
    """Test edge cases and error scenarios."""

    def test_incomplete_build(self, builder_pattern):
        """Test handling incomplete build."""
        builder = HouseBuilder()
        builder.build_foundation()

        # Try to get result without completing
        product = builder_pattern.get_result(builder)
        assert product is None

    def test_invalid_step(self, builder_pattern):
        """Test handling invalid step."""
        builder = HouseBuilder()
        result = builder_pattern.build_step(builder, "nonexistent_step", {})
        assert result.executed is False

    def test_register_max_limit(self):
        """Test registering builders up to max limit."""
        config = BuilderConfig(max_builders=2)
        pattern = BuilderPatternFSA(config)

        builder1 = HouseBuilder()
        builder2 = CarBuilder()
        builder3 = ComputerBuilder()

        pattern.register_builder("b1", builder1)
        pattern.register_builder("b2", builder2)

        result = pattern.register_builder("b3", builder3)
        assert result.registered is False


class TestThreadSafety:
    """Test thread safety."""

    def test_thread_safe_pattern(self):
        """Test thread-safe pattern creation."""
        config = BuilderConfig(thread_safe=True)
        pattern = BuilderPatternFSA(config)
        assert pattern._lock is not None

    def test_non_thread_safe_pattern(self):
        """Test non-thread-safe pattern."""
        config = BuilderConfig(thread_safe=False)
        pattern = BuilderPatternFSA(config)
        assert pattern._lock is None


class TestComplexMultiStepConstruction:
    """Test complex multi-step construction."""

    def test_complex_house_construction(self, builder_pattern):
        """Test complex house construction."""
        builder = HouseBuilder()

        steps = [
            BuildStep(name="build_foundation", params={"material": "reinforced_concrete"}),
            BuildStep(name="build_walls", params={"material": "brick"}),
            BuildStep(name="build_roof", params={"material": "tile"}),
        ]

        result = builder_pattern.chain_build_steps(builder, steps)
        assert result.executed is True

        product = builder.get_result()
        assert product.get_property("foundation") == "reinforced_concrete"
        assert product.get_property("walls") == "brick"
        assert product.get_property("roof") == "tile"


class TestDirectorAlgorithmVariations:
    """Test director algorithm variations."""

    def test_simple_house_algorithm(self, builder_pattern):
        """Test simple house construction algorithm."""
        builder = HouseBuilder()
        director = HouseDirector(builder)

        result = builder_pattern.construct_with_director(
            director,
            "construct_simple_house"
        )
        assert result.constructed is True

    def test_luxury_house_algorithm(self, builder_pattern):
        """Test luxury house construction algorithm."""
        builder = HouseBuilder()
        director = HouseDirector(builder)

        result = builder_pattern.construct_with_director(
            director,
            "construct_luxury_house"
        )
        assert result.constructed is True

        product = builder.get_result()
        assert product.get_property("foundation") == "reinforced_concrete"


class TestFluentInterfaceScenarios:
    """Test fluent interface scenarios."""

    def test_fluent_interface_chaining(self, builder_pattern):
        """Test fluent interface method chaining."""
        builder = HouseBuilder()

        # Use fluent interface
        builder.build_foundation("concrete") \
               .build_walls("brick") \
               .build_roof("tile")

        product = builder.get_result()
        assert product.get_property("foundation") == "concrete"
        assert product.get_property("walls") == "brick"
        assert product.get_property("roof") == "tile"

    def test_car_fluent_interface(self, builder_pattern):
        """Test car builder fluent interface."""
        builder = CarBuilder()

        builder.build_engine("V8") \
               .build_wheels(4) \
               .build_body("red")

        product = builder.get_result()
        assert product.get_property("engine") == "V8"
        assert product.get_property("wheels") == 4
        assert product.get_property("body_color") == "red"
