"""
Tests for pipeline and schema functionality.
"""

import pytest

from ..pipeline import (
    BatchPipelineExecutor,
    ConditionalBranching,
    PipelineBuilder,
    PipelineComposer,
    PipelineOptimizer,
    PipelineValidator,
    StreamPipelineExecutor,
    TransformationPipeline,
)
from ..schema import (
    CompatibilityChecker,
    SchemaInferrer,
    SchemaMigrator,
    SchemaMapper,
    SchemaRegistry,
    SchemaValidator,
)
from ..types import (
    ErrorStrategy,
    FieldDefinition,
    Pipeline,
    Schema,
    Transformation,
)


class TestPipelineBuilder:
    """Tests for PipelineBuilder."""

    def test_build_pipeline(self):
        """Test building a pipeline."""
        builder = PipelineBuilder("test_pipeline")
        builder.add_transformation("step1", lambda x: x)

        pipeline = builder.build()
        assert pipeline.name == "test_pipeline"
        assert len(pipeline.transformations) == 1

    def test_add_multiple_transformations(self):
        """Test adding multiple transformations."""
        builder = PipelineBuilder("multi_step")
        builder.add_transformation("step1", lambda x: x)
        builder.add_transformation("step2", lambda x: x)

        pipeline = builder.build()
        assert len(pipeline.transformations) == 2

    def test_with_error_strategy(self):
        """Test setting error strategy."""
        builder = PipelineBuilder("error_test")
        builder.with_error_strategy(ErrorStrategy.SKIP)

        pipeline = builder.build()
        assert pipeline.error_strategy == ErrorStrategy.SKIP

    def test_with_parallel_execution(self):
        """Test enabling parallel execution."""
        builder = PipelineBuilder("parallel")
        builder.with_parallel_execution(max_workers=8)

        pipeline = builder.build()
        assert pipeline.parallel_execution is True
        assert pipeline.max_workers == 8

    def test_with_metadata(self):
        """Test adding metadata."""
        builder = PipelineBuilder("meta_test")
        builder.with_metadata(author="test", version="1.0")

        pipeline = builder.build()
        assert pipeline.metadata["author"] == "test"

    def test_fluent_api(self):
        """Test fluent API chaining."""
        pipeline = (
            PipelineBuilder("fluent")
            .add_transformation("step1", lambda x: x)
            .with_error_strategy(ErrorStrategy.LOG)
            .with_metadata(test=True)
            .build()
        )

        assert pipeline.name == "fluent"
        assert pipeline.error_strategy == ErrorStrategy.LOG


class TestTransformationPipeline:
    """Tests for TransformationPipeline."""

    def test_execute_pipeline(self):
        """Test executing a pipeline."""

        def double(data):
            return {"value": data.get("value", 0) * 2}

        transformation = Transformation(name="double", function=double)
        pipeline = Pipeline(name="test", transformations=[transformation])

        executor = TransformationPipeline(pipeline)
        result = executor.execute({"value": 5})

        assert result.success is True
        assert result.data["value"] == 10

    def test_pipeline_with_multiple_steps(self):
        """Test pipeline with multiple steps."""

        def add_one(data):
            return {"value": data.get("value", 0) + 1}

        def multiply_two(data):
            return {"value": data.get("value", 0) * 2}

        pipeline = Pipeline(
            name="multi",
            transformations=[
                Transformation(name="add", function=add_one),
                Transformation(name="multiply", function=multiply_two),
            ],
        )

        executor = TransformationPipeline(pipeline)
        result = executor.execute({"value": 5})

        # (5 + 1) * 2 = 12
        assert result.data["value"] == 12

    def test_pipeline_with_condition(self):
        """Test pipeline with conditional transformation."""

        def process(data):
            return {"processed": True}

        transformation = Transformation(
            name="conditional",
            function=process,
            condition=lambda x: x.get("value", 0) > 10,
        )

        pipeline = Pipeline(name="cond", transformations=[transformation])
        executor = TransformationPipeline(pipeline)

        # Should skip
        result1 = executor.execute({"value": 5})
        assert "processed" not in result1.data

        # Should execute
        result2 = executor.execute({"value": 15})
        assert result2.data.get("processed") is True

    def test_pipeline_error_handling(self):
        """Test pipeline error handling."""

        def failing_transform(data):
            raise ValueError("Intentional error")

        transformation = Transformation(
            name="fail", function=failing_transform, error_strategy=ErrorStrategy.SKIP
        )

        pipeline = Pipeline(name="error_test", transformations=[transformation])
        executor = TransformationPipeline(pipeline)

        result = executor.execute({"value": 5})
        assert len(result.errors) > 0


class TestPipelineValidator:
    """Tests for PipelineValidator."""

    def test_validate_valid_pipeline(self):
        """Test validating a valid pipeline."""
        transformation = Transformation(name="test", function=lambda x: x)
        pipeline = Pipeline(name="valid", transformations=[transformation])

        is_valid, errors = PipelineValidator.validate(pipeline)
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_empty_pipeline(self):
        """Test validating an empty pipeline."""
        pipeline = Pipeline(name="empty", transformations=[])

        is_valid, errors = PipelineValidator.validate(pipeline)
        assert is_valid is False

    def test_validate_invalid_transformation(self):
        """Test validating pipeline with invalid transformation."""
        transformation = Transformation(name="invalid", function="not_callable")
        pipeline = Pipeline(name="invalid", transformations=[transformation])

        is_valid, errors = PipelineValidator.validate(pipeline)
        assert is_valid is False


class TestPipelineOptimizer:
    """Tests for PipelineOptimizer."""

    def test_optimize_pipeline(self):
        """Test optimizing a pipeline."""
        transformation = Transformation(name="test", function=lambda x: x)
        pipeline = Pipeline(name="optimize_me", transformations=[transformation])

        optimized = PipelineOptimizer.optimize(pipeline)
        assert optimized is not None

    def test_remove_redundant_transformations(self):
        """Test removing redundant transformations."""
        pipeline = Pipeline(
            name="redundant",
            transformations=[
                Transformation(name="step1", function=lambda x: x),
                Transformation(name="step1", function=lambda x: x),  # Duplicate
                Transformation(name="step2", function=lambda x: x),
            ],
        )

        optimized = PipelineOptimizer.remove_redundant_transformations(pipeline)
        assert len(optimized.transformations) == 2


class TestConditionalBranching:
    """Tests for ConditionalBranching."""

    def test_create_conditional_transformation(self):
        """Test creating conditional transformation."""

        def is_positive(data):
            return data.get("value", 0) > 0

        def make_negative(data):
            return {"value": -abs(data.get("value", 0))}

        def make_positive(data):
            return {"value": abs(data.get("value", 0))}

        transformation = ConditionalBranching.create_conditional_transformation(
            "sign_transform",
            condition=is_positive,
            true_function=make_positive,
            false_function=make_negative,
        )

        result1 = transformation.function({"value": 5})
        assert result1["value"] == 5

        result2 = transformation.function({"value": -5})
        assert result2["value"] == 5

    def test_create_switch_transformation(self):
        """Test creating switch transformation."""

        def get_type(data):
            return data.get("type", "default")

        def process_a(data):
            return {"result": "A"}

        def process_b(data):
            return {"result": "B"}

        transformation = ConditionalBranching.create_switch_transformation(
            "switch_transform",
            key_function=get_type,
            case_functions={"type_a": process_a, "type_b": process_b},
        )

        result = transformation.function({"type": "type_a"})
        assert result["result"] == "A"


class TestBatchPipelineExecutor:
    """Tests for BatchPipelineExecutor."""

    def test_execute_batch(self):
        """Test batch execution."""

        def increment(data):
            return {"value": data.get("value", 0) + 1}

        transformation = Transformation(name="inc", function=increment)
        pipeline = Pipeline(name="batch", transformations=[transformation])

        executor = BatchPipelineExecutor(pipeline)
        data_list = [{"value": i} for i in range(5)]

        results = executor.execute_batch(data_list)
        assert len(results) == 5
        assert results[0]["value"] == 1

    def test_execute_batch_parallel(self):
        """Test parallel batch execution."""

        def double(data):
            return {"value": data.get("value", 0) * 2}

        transformation = Transformation(name="double", function=double)
        pipeline = Pipeline(name="parallel", transformations=[transformation])

        executor = BatchPipelineExecutor(pipeline)
        data_list = [{"value": i} for i in range(10)]

        results = executor.execute_batch_parallel(data_list, max_workers=2)
        assert len(results) == 10


class TestStreamPipelineExecutor:
    """Tests for StreamPipelineExecutor."""

    def test_execute_stream(self):
        """Test stream execution."""

        def square(data):
            return {"value": data.get("value", 0) ** 2}

        transformation = Transformation(name="square", function=square)
        pipeline = Pipeline(name="stream", transformations=[transformation])

        executor = StreamPipelineExecutor(pipeline)

        def data_generator():
            for i in range(5):
                yield {"value": i}

        results = list(executor.execute_stream(data_generator()))
        assert len(results) == 5
        assert results[2]["value"] == 4  # 2^2


class TestSchemaRegistry:
    """Tests for SchemaRegistry."""

    def test_register_schema(self):
        """Test registering a schema."""
        registry = SchemaRegistry()
        schema = Schema(name="user", version="1.0.0")

        registry.register(schema)
        retrieved = registry.get("user")

        assert retrieved is not None
        assert retrieved.name == "user"

    def test_get_specific_version(self):
        """Test getting specific schema version."""
        registry = SchemaRegistry()
        schema_v1 = Schema(name="user", version="1.0.0")
        schema_v2 = Schema(name="user", version="2.0.0")

        registry.register(schema_v1)
        registry.register(schema_v2)

        retrieved = registry.get("user", "1.0.0")
        assert retrieved.version == "1.0.0"

    def test_list_schemas(self):
        """Test listing schemas."""
        registry = SchemaRegistry()
        registry.register(Schema(name="user"))
        registry.register(Schema(name="product"))

        schemas = registry.list_schemas()
        assert "user" in schemas
        assert "product" in schemas


class TestSchemaInferrer:
    """Tests for SchemaInferrer."""

    def test_infer_from_dict(self):
        """Test inferring schema from dict."""
        data = {"name": "Alice", "age": 30, "active": True}

        schema = SchemaInferrer.infer_from_data(data, "user")
        assert "name" in schema.fields
        assert "age" in schema.fields
        assert schema.fields["age"].type == "integer"

    def test_infer_from_list(self):
        """Test inferring schema from list."""
        data = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]

        schema = SchemaInferrer.infer_from_data(data, "users")
        assert len(schema.fields) == 2
        assert schema.fields["name"].type == "string"

    def test_infer_required_fields(self):
        """Test inferring required fields."""
        data = [{"name": "Alice", "age": 30}, {"name": "Bob"}]  # age is optional

        schema = SchemaInferrer.infer_from_data(data, "users")
        assert schema.fields["name"].required is True
        assert schema.fields["age"].required is False


class TestSchemaValidator:
    """Tests for SchemaValidator."""

    def test_validate_valid_data(self):
        """Test validating valid data."""
        schema = Schema(
            name="user",
            fields={
                "name": FieldDefinition(name="name", type="string", required=True),
                "age": FieldDefinition(name="age", type="integer"),
            },
        )

        data = {"name": "Alice", "age": 30}
        result = SchemaValidator.validate(data, schema)

        assert result.is_valid is True

    def test_validate_missing_required(self):
        """Test validating data with missing required field."""
        schema = Schema(
            name="user",
            fields={"name": FieldDefinition(name="name", type="string", required=True)},
        )

        data = {"age": 30}
        result = SchemaValidator.validate(data, schema)

        assert result.is_valid is False
        assert len(result.errors) > 0

    def test_validate_wrong_type(self):
        """Test validating data with wrong type."""
        schema = Schema(
            name="user",
            fields={"age": FieldDefinition(name="age", type="integer", required=True)},
        )

        data = {"age": "not a number"}
        result = SchemaValidator.validate(data, schema)

        assert result.is_valid is False


class TestSchemaMapper:
    """Tests for SchemaMapper."""

    def test_create_mapping(self):
        """Test creating schema mapping."""
        source = Schema(name="source", fields={"old_field": FieldDefinition(name="old_field", type="string")})

        target = Schema(name="target", fields={"new_field": FieldDefinition(name="new_field", type="string")})

        mapping = SchemaMapper.create_mapping(source, target, auto_map=False)
        assert mapping is not None

    def test_apply_mapping(self):
        """Test applying schema mapping."""
        source = Schema(name="source", fields={"name": FieldDefinition(name="name", type="string")})

        target = Schema(name="target", fields={"fullName": FieldDefinition(name="fullName", type="string")})

        mapping = SchemaMapper.create_mapping(source, target, auto_map=False)
        mapping.add_field_mapping("name", "fullName")

        data = {"name": "Alice"}
        result = SchemaMapper.apply_mapping(data, mapping)

        assert "fullName" in result


class TestCompatibilityChecker:
    """Tests for CompatibilityChecker."""

    def test_check_compatible_schemas(self):
        """Test checking compatible schemas."""
        schema1 = Schema(
            name="v1", fields={"name": FieldDefinition(name="name", type="string")}
        )

        schema2 = Schema(
            name="v2",
            fields={
                "name": FieldDefinition(name="name", type="string"),
                "email": FieldDefinition(name="email", type="string", default=""),
            },
        )

        is_compatible, issues = CompatibilityChecker.check_compatibility(schema1, schema2)
        assert is_compatible is True

    def test_check_incompatible_schemas(self):
        """Test checking incompatible schemas."""
        schema1 = Schema(name="v1", fields={})

        schema2 = Schema(
            name="v2",
            fields={"required_field": FieldDefinition(name="required_field", type="string", required=True)},
        )

        is_compatible, issues = CompatibilityChecker.check_compatibility(schema1, schema2)
        assert is_compatible is False

    def test_backward_compatibility(self):
        """Test backward compatibility check."""
        old_schema = Schema(
            name="old", fields={"name": FieldDefinition(name="name", type="string", required=True)}
        )

        new_schema = Schema(
            name="new",
            fields={
                "name": FieldDefinition(name="name", type="string", required=True),
                "email": FieldDefinition(name="email", type="string", default=""),
            },
        )

        is_compatible, issues = CompatibilityChecker.is_backward_compatible(
            old_schema, new_schema
        )
        assert is_compatible is True
