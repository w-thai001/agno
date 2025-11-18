"""
Tests for the DataTransformerFSA core functionality.
"""

import pytest

from ..core import DataTransformerFSA
from ..exceptions import InvalidFormatError, UnsupportedFormatError
from ..types import (
    AggregationConfig,
    DataFormat,
    Enricher,
    ErrorStrategy,
    FieldDefinition,
    Pipeline,
    Schema,
    Transformation,
    TransformationRule,
    TransformationRules,
    TransformationType,
)


class TestDataTransformerFSAInitialization:
    """Tests for FSA initialization."""

    def test_initialization(self):
        """Test FSA initializes correctly."""
        fsa = DataTransformerFSA()
        assert fsa is not None
        assert fsa.format_registry is not None
        assert fsa.schema_registry is not None

    def test_supported_formats(self):
        """Test getting supported formats."""
        fsa = DataTransformerFSA()
        formats = fsa.get_supported_formats()
        assert "json" in formats
        assert "csv" in formats
        assert "yaml" in formats


class TestFormatConversion:
    """Tests for format conversion."""

    def test_json_to_csv_conversion(self):
        """Test converting JSON to CSV."""
        fsa = DataTransformerFSA()
        json_data = '[{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]'

        result = fsa.convert_format(json_data, "json", "csv")
        assert isinstance(result, str)
        assert "name" in result
        assert "Alice" in result

    def test_csv_to_json_conversion(self):
        """Test converting CSV to JSON."""
        fsa = DataTransformerFSA()
        csv_data = "name,age\nAlice,30\nBob,25"

        result = fsa.convert_format(csv_data, "csv", "json")
        assert isinstance(result, str)
        assert "Alice" in result

    def test_json_to_yaml_conversion(self):
        """Test converting JSON to YAML."""
        fsa = DataTransformerFSA()
        json_data = '{"name": "Alice", "age": 30}'

        result = fsa.convert_format(json_data, "json", "yaml")
        assert isinstance(result, str)
        assert "name:" in result or "Alice" in result

    def test_yaml_to_json_conversion(self):
        """Test converting YAML to JSON."""
        fsa = DataTransformerFSA()
        yaml_data = "name: Alice\nage: 30"

        result = fsa.convert_format(yaml_data, "yaml", "json")
        assert isinstance(result, str)
        assert "Alice" in result

    def test_invalid_format_error(self):
        """Test error on invalid format."""
        fsa = DataTransformerFSA()
        invalid_json = '{"name": "Alice"'

        with pytest.raises(InvalidFormatError):
            fsa.convert_format(invalid_json, "json", "csv")

    def test_unsupported_format(self):
        """Test error on unsupported format."""
        fsa = DataTransformerFSA()
        with pytest.raises((UnsupportedFormatError, ValueError)):
            fsa.convert_format('{"test": 1}', "json", "unknown_format")


class TestTransformation:
    """Tests for data transformation."""

    def test_basic_transformation(self):
        """Test basic data transformation."""
        fsa = DataTransformerFSA()
        data = {"name": "alice", "age": 30}

        rules = TransformationRules()
        rules.add_rule(
            TransformationRule(
                name="uppercase_name",
                type=TransformationType.VALUE_TRANSFORMATION,
                source_field="name",
                parameters={"normalizer": "uppercase"},
            )
        )

        result = fsa.transform(data, "json", rules)
        assert result.data is not None
        assert result.errors == []

    def test_transformation_with_field_mapping(self):
        """Test transformation with field mapping."""
        fsa = DataTransformerFSA()
        data = {"old_name": "value"}

        rules = TransformationRules()
        rules.add_rule(
            TransformationRule(
                name="rename_field",
                type=TransformationType.FIELD_MAPPING,
                source_field="old_name",
                target_field="new_name",
                parameters={"operation": "rename"},
            )
        )

        result = fsa.transform(data, "json", rules)
        assert result.errors == []

    def test_transformation_with_type_conversion(self):
        """Test transformation with type conversion."""
        fsa = DataTransformerFSA()
        data = {"age": "30"}

        rules = TransformationRules()
        rules.add_rule(
            TransformationRule(
                name="convert_age",
                type=TransformationType.TYPE_CONVERSION,
                source_field="age",
                parameters={"target_type": "int"},
            )
        )

        result = fsa.transform(data, "json", rules)
        assert result.errors == []

    def test_transformation_error_handling(self):
        """Test transformation error handling."""
        fsa = DataTransformerFSA()
        data = {"value": "test"}

        rules = TransformationRules()
        rules.add_rule(
            TransformationRule(
                name="failing_rule",
                type=TransformationType.TYPE_CONVERSION,
                source_field="nonexistent",
                error_strategy=ErrorStrategy.LOG,
                parameters={"target_type": "int"},
            )
        )

        result = fsa.transform(data, "json", rules)
        # Should not raise, just log error
        assert result is not None


class TestPipelineOperations:
    """Tests for pipeline operations."""

    def test_create_pipeline(self):
        """Test creating a pipeline."""
        fsa = DataTransformerFSA()
        pipeline = fsa.create_pipeline("test_pipeline")

        assert pipeline is not None
        assert pipeline.name == "test_pipeline"
        assert "test_pipeline" in fsa.list_pipelines()

    def test_execute_pipeline(self):
        """Test executing a pipeline."""
        fsa = DataTransformerFSA()

        def uppercase_transform(data):
            if isinstance(data, dict):
                return {k: v.upper() if isinstance(v, str) else v for k, v in data.items()}
            return data

        transformation = Transformation(name="uppercase", function=uppercase_transform)

        pipeline = fsa.create_pipeline("test", [transformation])
        result = fsa.execute_pipeline({"name": "alice"}, pipeline)

        assert result is not None

    def test_batch_transform(self):
        """Test batch transformation."""
        fsa = DataTransformerFSA()

        def increment(data):
            return {"value": data.get("value", 0) + 1}

        transformation = Transformation(name="increment", function=increment)
        pipeline = fsa.create_pipeline("batch_test", [transformation])

        data_list = [{"value": 1}, {"value": 2}, {"value": 3}]
        results = fsa.batch_transform(data_list, pipeline)

        assert len(results) == 3

    def test_batch_transform_parallel(self):
        """Test parallel batch transformation."""
        fsa = DataTransformerFSA()

        def double(data):
            return {"value": data.get("value", 0) * 2}

        transformation = Transformation(name="double", function=double)
        pipeline = fsa.create_pipeline("parallel_test", [transformation])

        data_list = [{"value": i} for i in range(10)]
        results = fsa.batch_transform(data_list, pipeline, parallel=True, max_workers=2)

        assert len(results) == 10

    def test_stream_transform(self):
        """Test stream transformation."""
        fsa = DataTransformerFSA()

        def add_one(data):
            return {"value": data.get("value", 0) + 1}

        transformation = Transformation(name="add_one", function=add_one)
        pipeline = fsa.create_pipeline("stream_test", [transformation])

        def data_generator():
            for i in range(5):
                yield {"value": i}

        results = list(fsa.stream_transform(data_generator(), pipeline))
        assert len(results) == 5

    def test_optimize_pipeline(self):
        """Test pipeline optimization."""
        fsa = DataTransformerFSA()
        pipeline = fsa.create_pipeline("optimize_test")

        optimized = fsa.optimize_pipeline(pipeline)
        assert optimized is not None


class TestSchemaManagement:
    """Tests for schema management."""

    def test_register_schema(self):
        """Test registering a schema."""
        fsa = DataTransformerFSA()
        schema = Schema(
            name="user",
            version="1.0.0",
            fields={
                "name": FieldDefinition(name="name", type="string", required=True),
                "age": FieldDefinition(name="age", type="integer"),
            },
        )

        fsa.register_schema(schema)
        assert "user" in fsa.list_schemas()

    def test_infer_schema(self):
        """Test schema inference."""
        fsa = DataTransformerFSA()
        data = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]

        schema = fsa.infer_schema(data, "users")
        assert schema is not None
        assert schema.name == "users"
        assert "name" in schema.fields
        assert "age" in schema.fields

    def test_validate_data(self):
        """Test data validation."""
        fsa = DataTransformerFSA()
        schema = Schema(
            name="user",
            fields={
                "name": FieldDefinition(name="name", type="string", required=True),
                "age": FieldDefinition(name="age", type="integer"),
            },
        )
        fsa.register_schema(schema)

        valid_data = {"name": "Alice", "age": 30}
        result = fsa.validate_data(valid_data, schema)
        assert result.is_valid

    def test_validate_data_invalid(self):
        """Test data validation with invalid data."""
        fsa = DataTransformerFSA()
        schema = Schema(
            name="user",
            fields={"name": FieldDefinition(name="name", type="string", required=True)},
        )
        fsa.register_schema(schema)

        invalid_data = {"age": 30}  # Missing required 'name'
        result = fsa.validate_data(invalid_data, schema)
        assert not result.is_valid
        assert len(result.errors) > 0

    def test_map_schema(self):
        """Test schema mapping."""
        fsa = DataTransformerFSA()

        schema_v1 = Schema(
            name="user_v1",
            fields={"first_name": FieldDefinition(name="first_name", type="string")},
        )

        schema_v2 = Schema(
            name="user_v2",
            fields={"firstName": FieldDefinition(name="firstName", type="string")},
        )

        fsa.register_schema(schema_v1)
        fsa.register_schema(schema_v2)

        mapping = fsa.map_schema(schema_v1, schema_v2, auto_map=False)
        assert mapping is not None

    def test_migrate_schema(self):
        """Test schema migration."""
        fsa = DataTransformerFSA()

        schema_v1 = Schema(
            name="user",
            version="1.0.0",
            fields={"name": FieldDefinition(name="name", type="string")},
        )

        schema_v2 = Schema(
            name="user",
            version="2.0.0",
            fields={
                "name": FieldDefinition(name="name", type="string"),
                "email": FieldDefinition(name="email", type="string", default=""),
            },
        )

        fsa.register_schema(schema_v1)
        fsa.register_schema(schema_v2)

        data = {"name": "Alice"}
        migrated = fsa.migrate_schema(data, "user", "user", "1.0.0", "2.0.0")

        assert migrated is not None
        assert "name" in migrated


class TestDataEnrichment:
    """Tests for data enrichment."""

    def test_add_lookup_table(self):
        """Test adding a lookup table."""
        fsa = DataTransformerFSA()
        fsa.add_lookup_table("countries", {"US": "United States", "UK": "United Kingdom"})
        # No assertion needed, just ensure no error

    def test_enrich_data(self):
        """Test data enrichment."""
        fsa = DataTransformerFSA()

        def add_full_name(source_fields):
            return {"full_name": f"{source_fields['first']} {source_fields['last']}"}

        enricher = Enricher(
            name="full_name",
            enricher_function=add_full_name,
            source_fields=["first", "last"],
            target_fields=["full_name"],
        )

        data = {"first": "John", "last": "Doe"}
        enriched = fsa.enrich_data(data, [enricher])

        assert "full_name" in enriched

    def test_enrich_data_list(self):
        """Test enriching a list of data."""
        fsa = DataTransformerFSA()

        def add_suffix(source_fields):
            return {"name_with_suffix": source_fields["name"] + "_enriched"}

        enricher = Enricher(
            name="suffix",
            enricher_function=add_suffix,
            source_fields=["name"],
            target_fields=["name_with_suffix"],
        )

        data_list = [{"name": "Alice"}, {"name": "Bob"}]
        enriched = fsa.enrich_data(data_list, [enricher])

        assert len(enriched) == 2
        assert all("name_with_suffix" in item for item in enriched)


class TestAggregationAndFiltering:
    """Tests for aggregation and filtering."""

    def test_aggregate_data(self):
        """Test data aggregation."""
        fsa = DataTransformerFSA()
        data = [
            {"category": "A", "amount": 100},
            {"category": "A", "amount": 200},
            {"category": "B", "amount": 150},
        ]

        config = AggregationConfig(
            group_by=["category"], aggregations={"amount": ["sum", "count"]}
        )

        result = fsa.aggregate_data(data, config)
        assert len(result) == 2

    def test_filter_data(self):
        """Test data filtering."""
        fsa = DataTransformerFSA()
        data = [{"age": 25}, {"age": 30}, {"age": 18}]

        filtered = fsa.filter_data(data, lambda x: x.get("age", 0) >= 21)
        assert len(filtered) == 2


class TestCustomTransformers:
    """Tests for custom transformers."""

    def test_register_custom_transformer(self):
        """Test registering a custom transformer."""
        fsa = DataTransformerFSA()

        def custom_transform(data):
            return {"transformed": True}

        fsa.register_custom_transformer("my_transform", custom_transform)
        transformer = fsa.get_custom_transformer("my_transform")

        assert transformer is not None
        result = transformer({})
        assert result["transformed"] is True

    def test_get_nonexistent_transformer(self):
        """Test getting a non-existent transformer."""
        fsa = DataTransformerFSA()
        transformer = fsa.get_custom_transformer("nonexistent")
        assert transformer is None


class TestUtilityMethods:
    """Tests for utility methods."""

    def test_get_pipeline(self):
        """Test getting a pipeline."""
        fsa = DataTransformerFSA()
        fsa.create_pipeline("test_pipeline")

        pipeline = fsa.get_pipeline("test_pipeline")
        assert pipeline is not None
        assert pipeline.name == "test_pipeline"

    def test_list_pipelines(self):
        """Test listing pipelines."""
        fsa = DataTransformerFSA()
        fsa.create_pipeline("pipeline1")
        fsa.create_pipeline("pipeline2")

        pipelines = fsa.list_pipelines()
        assert "pipeline1" in pipelines
        assert "pipeline2" in pipelines

    def test_transformation_history(self):
        """Test transformation history."""
        fsa = DataTransformerFSA()
        json_data = '{"name": "Alice"}'

        fsa.convert_format(json_data, "json", "yaml")

        history = fsa.get_transformation_history()
        assert len(history) > 0

    def test_clear_history(self):
        """Test clearing transformation history."""
        fsa = DataTransformerFSA()
        json_data = '{"name": "Alice"}'

        fsa.convert_format(json_data, "json", "yaml")
        fsa.clear_history()

        history = fsa.get_transformation_history()
        assert len(history) == 0
