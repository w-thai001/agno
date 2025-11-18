"""
Comprehensive unit tests for Data Transformer FSA.

This module contains 30 comprehensive tests covering all functionality
of the DataTransformerFSA including:
- State machine transitions
- Format conversions
- Schema validation
- Field mapping
- Aggregations
- Filtering
- Pipeline composition
- Caching
- Metrics
- Versioning
- Error handling
"""

import asyncio
import json
import pytest
from datetime import datetime
from typing import Dict, Any, List
from unittest.mock import Mock, patch

from agno.fsas.infrastructure.data_transformer_fsa import (
    DataTransformerFSA,
    TransformationState,
    TransformationType,
    DataFormat,
    SchemaValidationError,
    TransformationError,
    FormatConversionError,
    StateTransitionError,
    EnrichmentError,
    DataQualityError,
    TransformConfig,
    TransformMetrics,
    TransformPipeline,
    DataSchema,
    SchemaField,
    FieldMapping,
    AggregationFunction,
    DataQualityRule,
    CacheManager,
    create_field_mapping,
    create_simple_schema,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def fsa():
    """Create a DataTransformerFSA instance."""
    return DataTransformerFSA(
        enable_cache=True,
        cache_size=100,
        max_workers=2,
        enable_metrics=True,
    )


@pytest.fixture
def sample_json_data():
    """Sample JSON data for testing."""
    return json.dumps([
        {"id": 1, "name": "Alice", "age": 30, "email": "alice@example.com"},
        {"id": 2, "name": "Bob", "age": 25, "email": "bob@example.com"},
        {"id": 3, "name": "Charlie", "age": 35, "email": "charlie@example.com"},
    ])


@pytest.fixture
def sample_dict_data():
    """Sample dict data for testing."""
    return [
        {"id": 1, "name": "Alice", "age": 30, "email": "alice@example.com"},
        {"id": 2, "name": "Bob", "age": 25, "email": "bob@example.com"},
        {"id": 3, "name": "Charlie", "age": 35, "email": "charlie@example.com"},
    ]


@pytest.fixture
def sample_csv_data():
    """Sample CSV data for testing."""
    return """id,name,age,email
1,Alice,30,alice@example.com
2,Bob,25,bob@example.com
3,Charlie,35,charlie@example.com"""


@pytest.fixture
def sample_xml_data():
    """Sample XML data for testing."""
    return """<?xml version="1.0"?>
<users>
    <user>
        <id>1</id>
        <name>Alice</name>
        <age>30</age>
    </user>
    <user>
        <id>2</id>
        <name>Bob</name>
        <age>25</age>
    </user>
</users>"""


@pytest.fixture
def user_schema():
    """Create a user schema for testing."""
    return DataSchema(
        name="user_schema",
        version="1.0",
        fields=[
            SchemaField(name="id", type="integer", required=True),
            SchemaField(name="name", type="string", required=True),
            SchemaField(name="age", type="integer", required=False),
            SchemaField(name="email", type="string", required=False),
        ],
    )


@pytest.fixture
def transform_config(user_schema):
    """Create a basic transform config."""
    return TransformConfig(
        transform_id="test_transform",
        transform_type=TransformationType.MAP,
        source_format=DataFormat.JSON,
        target_format=DataFormat.DICT,
        schema=user_schema,
        enable_cache=True,
    )


# ============================================================================
# State Machine Tests
# ============================================================================

def test_initial_state(fsa):
    """Test 1: FSA starts in IDLE state."""
    assert fsa.state == TransformationState.IDLE


def test_valid_state_transition(fsa):
    """Test 2: Valid state transitions work correctly."""
    fsa.transition_to(TransformationState.VALIDATING)
    assert fsa.state == TransformationState.VALIDATING

    fsa.transition_to(TransformationState.EXTRACTING)
    assert fsa.state == TransformationState.EXTRACTING

    fsa.transition_to(TransformationState.TRANSFORMING)
    assert fsa.state == TransformationState.TRANSFORMING


def test_invalid_state_transition(fsa):
    """Test 3: Invalid state transitions raise error."""
    with pytest.raises(StateTransitionError):
        fsa.transition_to(TransformationState.LOADING)


def test_state_transition_to_failed(fsa):
    """Test 4: Transition to FAILED state from various states."""
    fsa.transition_to(TransformationState.VALIDATING)
    fsa.transition_to(TransformationState.FAILED)
    assert fsa.state == TransformationState.FAILED


def test_state_transition_to_completed(fsa):
    """Test 5: Complete workflow state transitions."""
    fsa.transition_to(TransformationState.VALIDATING)
    fsa.transition_to(TransformationState.EXTRACTING)
    fsa.transition_to(TransformationState.TRANSFORMING)
    fsa.transition_to(TransformationState.LOADING)
    fsa.transition_to(TransformationState.COMPLETED)
    assert fsa.state == TransformationState.COMPLETED


# ============================================================================
# Format Conversion Tests
# ============================================================================

def test_json_to_dict_conversion(fsa, sample_json_data):
    """Test 6: JSON to dict conversion."""
    result = fsa.json_to_dict(sample_json_data)
    assert isinstance(result, list)
    assert len(result) == 3
    assert result[0]["name"] == "Alice"


def test_dict_to_json_conversion(fsa, sample_dict_data):
    """Test 7: Dict to JSON conversion."""
    result = fsa.dict_to_json(sample_dict_data)
    assert isinstance(result, str)
    parsed = json.loads(result)
    assert len(parsed) == 3


def test_csv_to_dict_conversion(fsa, sample_csv_data):
    """Test 8: CSV to dict conversion."""
    result = fsa.csv_to_dict(sample_csv_data)
    assert isinstance(result, list)
    assert len(result) == 3
    assert result[0]["name"] == "Alice"


def test_dict_to_csv_conversion(fsa, sample_dict_data):
    """Test 9: Dict to CSV conversion."""
    result = fsa.dict_to_csv(sample_dict_data)
    assert isinstance(result, str)
    assert "id,name,age,email" in result
    assert "Alice" in result


def test_xml_to_dict_conversion(fsa, sample_xml_data):
    """Test 10: XML to dict conversion."""
    result = fsa.xml_to_dict(sample_xml_data)
    assert isinstance(result, dict)
    assert "user" in result


def test_dict_to_xml_conversion(fsa):
    """Test 11: Dict to XML conversion."""
    data = {"user": {"id": "1", "name": "Alice"}}
    result = fsa.dict_to_xml(data, root_tag="root")
    assert isinstance(result, str)
    assert "<user>" in result
    assert "<name>Alice</name>" in result


def test_invalid_json_conversion(fsa):
    """Test 12: Invalid JSON raises error."""
    with pytest.raises(FormatConversionError):
        fsa.json_to_dict("invalid json {")


def test_invalid_xml_conversion(fsa):
    """Test 13: Invalid XML raises error."""
    with pytest.raises(FormatConversionError):
        fsa.xml_to_dict("<invalid><xml>")


# ============================================================================
# Schema Validation Tests
# ============================================================================

def test_schema_field_validation(user_schema):
    """Test 14: Schema validates fields correctly."""
    valid_record = {"id": 1, "name": "Alice", "age": 30}
    is_valid, errors = user_schema.validate_record(valid_record)
    assert is_valid
    assert len(errors) == 0


def test_schema_required_field_validation(user_schema):
    """Test 15: Schema validates required fields."""
    invalid_record = {"age": 30}  # Missing required 'id' and 'name'
    is_valid, errors = user_schema.validate_record(invalid_record)
    assert not is_valid
    assert len(errors) > 0


def test_schema_type_validation(user_schema):
    """Test 16: Schema validates field types."""
    invalid_record = {"id": "not_an_integer", "name": "Alice"}
    is_valid, errors = user_schema.validate_record(invalid_record)
    assert not is_valid
    assert any("type" in error.lower() for error in errors)


def test_schema_constraint_validation():
    """Test 17: Schema validates field constraints."""
    schema = DataSchema(
        name="test_schema",
        version="1.0",
        fields=[
            SchemaField(
                name="age",
                type="integer",
                constraints={"min": 0, "max": 150}
            ),
        ],
    )

    invalid_record = {"age": 200}
    is_valid, errors = schema.validate_record(invalid_record)
    assert not is_valid


# ============================================================================
# Field Mapping Tests
# ============================================================================

def test_field_mapping_basic(fsa):
    """Test 18: Basic field mapping."""
    data = {"first_name": "Alice", "last_name": "Smith"}
    mappings = [
        FieldMapping(source_field="first_name", target_field="fname"),
        FieldMapping(source_field="last_name", target_field="lname"),
    ]

    result = fsa.map_fields(data, mappings)
    assert result["fname"] == "Alice"
    assert result["lname"] == "Smith"


def test_field_mapping_with_transformation(fsa):
    """Test 19: Field mapping with transformation function."""
    data = {"name": "alice"}
    mappings = [
        FieldMapping(
            source_field="name",
            target_field="name_upper",
            transformation=lambda x: x.upper()
        ),
    ]

    result = fsa.map_fields(data, mappings)
    assert result["name_upper"] == "ALICE"


def test_field_mapping_with_default(fsa):
    """Test 20: Field mapping with default value."""
    data = {}
    mappings = [
        FieldMapping(
            source_field="missing_field",
            target_field="field",
            default_value="default",
            required=False,
        ),
    ]

    result = fsa.map_fields(data, mappings)
    assert result["field"] == "default"


def test_field_mapping_list(fsa, sample_dict_data):
    """Test 21: Field mapping on list of records."""
    mappings = [
        FieldMapping(source_field="name", target_field="full_name"),
    ]

    result = fsa.map_fields(sample_dict_data, mappings)
    assert len(result) == 3
    assert result[0]["full_name"] == "Alice"


# ============================================================================
# Filtering and Aggregation Tests
# ============================================================================

def test_filter_data(fsa, sample_dict_data):
    """Test 22: Data filtering."""
    filters = [lambda record: record["age"] > 28]
    result = fsa.filter_data(sample_dict_data, filters)

    assert len(result) == 2
    assert all(record["age"] > 28 for record in result)


def test_multiple_filters(fsa, sample_dict_data):
    """Test 23: Multiple filter conditions."""
    filters = [
        lambda record: record["age"] > 20,
        lambda record: record["age"] < 35,
    ]
    result = fsa.filter_data(sample_dict_data, filters)

    assert len(result) == 2


def test_aggregate_sum(fsa, sample_dict_data):
    """Test 24: Aggregation with SUM function."""
    aggregations = {"age": AggregationFunction.SUM}
    result = fsa._apply_aggregations(sample_dict_data, aggregations, None)

    assert result["age"] == 90  # 30 + 25 + 35


def test_aggregate_avg(fsa, sample_dict_data):
    """Test 25: Aggregation with AVG function."""
    aggregations = {"age": AggregationFunction.AVG}
    result = fsa._apply_aggregations(sample_dict_data, aggregations, None)

    assert result["age"] == 30  # (30 + 25 + 35) / 3


def test_aggregate_count(fsa, sample_dict_data):
    """Test 26: Aggregation with COUNT function."""
    aggregations = {"id": AggregationFunction.COUNT}
    result = fsa._apply_aggregations(sample_dict_data, aggregations, None)

    assert result["id"] == 3


# ============================================================================
# Transform Pipeline Tests
# ============================================================================

def test_pipeline_creation(fsa):
    """Test 27: Pipeline creation and execution."""
    pipeline = TransformPipeline(name="test_pipeline")

    # Add transforms
    pipeline.add_transform(lambda x: x * 2)
    pipeline.add_transform(lambda x: x + 10)

    result = pipeline.execute(5)
    assert result == 20  # (5 * 2) + 10


def test_pipeline_chaining(fsa):
    """Test 28: Pipeline chaining."""
    pipeline = TransformPipeline(name="test_pipeline")
    pipeline.add_transform(lambda x: x.upper()).add_transform(lambda x: x + "!")

    result = pipeline.execute("hello")
    assert result == "HELLO!"


@pytest.mark.asyncio
async def test_pipeline_async_execution():
    """Test 29: Async pipeline execution."""
    pipeline = TransformPipeline(name="async_pipeline")

    async def async_transform(x):
        await asyncio.sleep(0.01)
        return x * 2

    pipeline.add_transform(async_transform)

    result = await pipeline.execute_async(5)
    assert result == 10


# ============================================================================
# Caching Tests
# ============================================================================

def test_cache_manager():
    """Test 30: Cache manager functionality."""
    cache = CacheManager(max_size=10, default_ttl=60)

    # Set and get
    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"

    # Cache hit
    assert cache.hits == 1

    # Cache miss
    assert cache.get("nonexistent") is None
    assert cache.misses == 1


def test_cache_expiration():
    """Test 31: Cache expiration."""
    cache = CacheManager(max_size=10, default_ttl=0)  # Immediate expiration

    cache.set("key1", "value1")
    import time
    time.sleep(0.1)

    # Should be expired
    assert cache.get("key1") is None


def test_cache_size_limit():
    """Test 32: Cache size limit."""
    cache = CacheManager(max_size=2, default_ttl=60)

    cache.set("key1", "value1")
    cache.set("key2", "value2")
    cache.set("key3", "value3")  # Should evict oldest

    # Cache should only have 2 items
    assert cache.get("key2") == "value2"
    assert cache.get("key3") == "value3"


# ============================================================================
# Metrics Tests
# ============================================================================

def test_transform_metrics():
    """Test 33: Transform metrics collection."""
    metrics = TransformMetrics(
        transform_id="test_transform",
        operation="test_operation"
    )

    metrics.records_processed = 100
    metrics.records_failed = 5
    metrics.complete()

    assert metrics.duration_seconds is not None
    assert metrics.duration_seconds >= 0


def test_metrics_collection(fsa, sample_dict_data, transform_config):
    """Test 34: Metrics collection during transformation."""
    result = fsa.transform(sample_dict_data, transform_config)

    metrics = fsa.get_metrics("test_transform")
    assert metrics is not None
    assert metrics["records_processed"] > 0


# ============================================================================
# Integration Tests
# ============================================================================

def test_end_to_end_json_to_csv(fsa, sample_json_data, user_schema):
    """Test 35: End-to-end JSON to CSV transformation."""
    config = TransformConfig(
        transform_id="json_to_csv",
        transform_type=TransformationType.CONVERT,
        source_format=DataFormat.JSON,
        target_format=DataFormat.CSV,
        schema=user_schema,
    )

    result = fsa.transform(sample_json_data, config)
    assert isinstance(result, str)
    assert "Alice" in result
    assert "Bob" in result


def test_batch_transformation(fsa, sample_dict_data, transform_config):
    """Test 36: Batch transformation."""
    batch = [sample_dict_data, sample_dict_data]
    results = fsa.transform_batch(batch, transform_config)

    assert len(results) == 2
    assert all(result is not None for result in results)


def test_transformation_with_cache(fsa, sample_dict_data, transform_config):
    """Test 37: Transformation with caching."""
    # First transform - cache miss
    result1 = fsa.transform(sample_dict_data, transform_config)

    # Second transform - cache hit
    result2 = fsa.transform(sample_dict_data, transform_config)

    # Results should be identical
    assert result1 == result2

    # Check cache stats
    stats = fsa.get_cache_stats()
    assert stats["hits"] > 0


def test_transformation_with_filters(fsa, sample_dict_data, user_schema):
    """Test 38: Transformation with filters."""
    config = TransformConfig(
        transform_id="filter_transform",
        transform_type=TransformationType.FILTER,
        source_format=DataFormat.DICT,
        target_format=DataFormat.DICT,
        schema=user_schema,
        filters=[lambda record: record["age"] > 28],
    )

    result = fsa.transform(sample_dict_data, config)
    assert len(result) == 2


def test_transformation_with_aggregation(fsa, sample_dict_data, user_schema):
    """Test 39: Transformation with aggregation."""
    config = TransformConfig(
        transform_id="agg_transform",
        transform_type=TransformationType.AGGREGATE,
        source_format=DataFormat.DICT,
        target_format=DataFormat.DICT,
        schema=user_schema,
        aggregations={"age": AggregationFunction.AVG},
    )

    result = fsa.transform(sample_dict_data, config)
    assert "age" in result
    assert result["age"] == 30


# ============================================================================
# Error Handling Tests
# ============================================================================

def test_schema_validation_error(fsa, user_schema):
    """Test 40: Schema validation error handling."""
    invalid_data = [{"invalid": "data"}]

    config = TransformConfig(
        transform_id="validation_test",
        transform_type=TransformationType.MAP,
        source_format=DataFormat.DICT,
        target_format=DataFormat.DICT,
        schema=user_schema,
    )

    with pytest.raises(SchemaValidationError):
        fsa.transform(invalid_data, config, validate=True)


def test_transformation_error_recovery(fsa):
    """Test 41: FSA recovers from transformation errors."""
    config = TransformConfig(
        transform_id="error_test",
        transform_type=TransformationType.MAP,
        source_format=DataFormat.JSON,
        target_format=DataFormat.DICT,
    )

    # Trigger error with invalid JSON
    try:
        fsa.transform("invalid json", config)
    except TransformationError:
        pass

    # FSA should be back in IDLE state
    assert fsa.state == TransformationState.IDLE


# ============================================================================
# Enrichment Tests
# ============================================================================

def test_enrichment_source_registration(fsa):
    """Test 42: Enrichment source registration."""
    def mock_enrichment(key):
        return {"extra_field": f"enriched_{key}"}

    fsa.register_enrichment_source("test_source", mock_enrichment)
    assert "test_source" in fsa.enrichment_sources


def test_data_enrichment(fsa):
    """Test 43: Data enrichment."""
    def mock_enrichment(key):
        return {"country": "USA"}

    fsa.register_enrichment_source("location", mock_enrichment)

    data = {"id": 1, "name": "Alice"}
    result = fsa.enrich_data(data, "location", "id")

    assert result["country"] == "USA"


def test_enrichment_with_missing_source(fsa):
    """Test 44: Enrichment with missing source raises error."""
    data = {"id": 1, "name": "Alice"}

    with pytest.raises(EnrichmentError):
        fsa.enrich_data(data, "nonexistent_source", "id")


# ============================================================================
# Versioning Tests
# ============================================================================

def test_version_creation(fsa, transform_config):
    """Test 45: Transform version creation."""
    version = fsa.create_version(
        transform_id="test_transform",
        config=transform_config,
        checkpoint_data={"test": "data"},
        created_by="test_user",
    )

    assert version.transform_id == "test_transform"
    assert version.created_by == "test_user"
    assert version.checkpoint_data == {"test": "data"}


def test_version_history(fsa, transform_config):
    """Test 46: Version history tracking."""
    # Create multiple versions
    version1 = fsa.create_version("test_transform", transform_config)
    version2 = fsa.create_version("test_transform", transform_config)

    # Check history
    history = fsa.version_history["test_transform"]
    assert len(history) == 2


def test_rollback_to_version(fsa, transform_config):
    """Test 47: Rollback to previous version."""
    version = fsa.create_version("test_transform", transform_config)

    rollback_version = fsa.rollback_to_version("test_transform", version.version_id)

    assert rollback_version is not None
    assert rollback_version.version_id == version.version_id
    assert fsa.state == TransformationState.IDLE


def test_rollback_to_nonexistent_version(fsa):
    """Test 48: Rollback to nonexistent version returns None."""
    result = fsa.rollback_to_version("test_transform", "nonexistent_id")
    assert result is None


# ============================================================================
# Data Quality Tests
# ============================================================================

def test_data_quality_not_null_rule(fsa, sample_dict_data):
    """Test 49: Data quality NOT_NULL rule."""
    rules = {
        "name": [(DataQualityRule.NOT_NULL, None)],
    }

    is_valid, errors = fsa.validate_data_quality(sample_dict_data, rules)
    assert is_valid


def test_data_quality_unique_rule(fsa):
    """Test 50: Data quality UNIQUE rule."""
    data = [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"},
        {"id": 2, "name": "Charlie"},  # Duplicate ID
    ]

    rules = {
        "id": [(DataQualityRule.UNIQUE, None)],
    }

    is_valid, errors = fsa.validate_data_quality(data, rules)
    assert not is_valid


def test_data_quality_range_rule(fsa, sample_dict_data):
    """Test 51: Data quality RANGE rule."""
    rules = {
        "age": [(DataQualityRule.RANGE, (0, 100))],
    }

    is_valid, errors = fsa.validate_data_quality(sample_dict_data, rules)
    assert is_valid


def test_data_quality_type_check_rule(fsa, sample_dict_data):
    """Test 52: Data quality TYPE_CHECK rule."""
    rules = {
        "name": [(DataQualityRule.TYPE_CHECK, str)],
        "age": [(DataQualityRule.TYPE_CHECK, int)],
    }

    is_valid, errors = fsa.validate_data_quality(sample_dict_data, rules)
    assert is_valid


# ============================================================================
# Utility Function Tests
# ============================================================================

def test_create_field_mapping_utility():
    """Test 53: create_field_mapping utility function."""
    mapping = create_field_mapping(
        source="first_name",
        target="fname",
        transform=lambda x: x.upper(),
        default="Unknown",
        required=True,
    )

    assert mapping.source_field == "first_name"
    assert mapping.target_field == "fname"
    assert mapping.transformation is not None
    assert mapping.default_value == "Unknown"
    assert mapping.required is True


def test_create_simple_schema_utility():
    """Test 54: create_simple_schema utility function."""
    schema = create_simple_schema(
        name="test_schema",
        fields={"id": "integer", "name": "string"},
        required_fields=["id"],
    )

    assert schema.name == "test_schema"
    assert len(schema.fields) == 2
    assert schema.fields[0].required is True


# ============================================================================
# Streaming Tests
# ============================================================================

def test_stream_transformation(fsa, sample_dict_data, transform_config):
    """Test 55: Stream transformation."""
    def data_stream():
        for record in sample_dict_data:
            yield record

    results = list(fsa.transform_stream(data_stream(), transform_config, batch_size=2))
    assert len(results) >= 3


@pytest.mark.asyncio
async def test_async_transformation(fsa, sample_dict_data, transform_config):
    """Test 56: Async transformation."""
    result = await fsa.transform_async(sample_dict_data, transform_config)
    assert result is not None


# ============================================================================
# Edge Cases and Stress Tests
# ============================================================================

def test_empty_data_transformation(fsa, transform_config):
    """Test 57: Transformation with empty data."""
    result = fsa.transform([], transform_config, validate=False)
    assert result == []


def test_single_record_transformation(fsa, transform_config):
    """Test 58: Transformation with single record."""
    data = {"id": 1, "name": "Alice", "age": 30}
    result = fsa.transform(data, transform_config, validate=False)
    assert result is not None


def test_large_batch_transformation(fsa, transform_config):
    """Test 59: Large batch transformation."""
    large_data = [{"id": i, "name": f"User{i}", "age": 20 + i} for i in range(1000)]

    result = fsa.transform(large_data, transform_config, validate=False)
    assert len(result) == 1000


def test_cache_clear(fsa):
    """Test 60: Cache clearing."""
    fsa.cache.set("key1", "value1")
    fsa.clear_cache()

    assert fsa.cache.get("key1") is None
    assert len(fsa.cache.cache) == 0


# ============================================================================
# Integration with Complex Pipelines
# ============================================================================

def test_complex_pipeline_with_multiple_transforms(fsa, sample_dict_data):
    """Test 61: Complex pipeline with multiple transforms."""
    # Create configs for pipeline
    config1 = TransformConfig(
        transform_id="step1",
        transform_type=TransformationType.FILTER,
        source_format=DataFormat.DICT,
        target_format=DataFormat.DICT,
        filters=[lambda r: r["age"] > 20],
    )

    config2 = TransformConfig(
        transform_id="step2",
        transform_type=TransformationType.MAP,
        source_format=DataFormat.DICT,
        target_format=DataFormat.DICT,
        field_mappings=[
            FieldMapping(source_field="name", target_field="full_name"),
        ],
    )

    pipeline = fsa.create_pipeline("complex", [config1, config2])
    result = pipeline.execute(sample_dict_data)

    assert len(result) > 0
    assert "full_name" in result[0]


def test_parallel_batch_processing(fsa, sample_dict_data, transform_config):
    """Test 62: Parallel batch processing."""
    batch = [sample_dict_data] * 5

    results = fsa.transform_batch(batch, transform_config, parallel=True)
    assert len(results) == 5


# ============================================================================
# Performance and Monitoring Tests
# ============================================================================

def test_metrics_store(fsa, sample_dict_data, transform_config):
    """Test 63: Metrics store functionality."""
    fsa.transform(sample_dict_data, transform_config)

    all_metrics = fsa.get_metrics()
    assert "test_transform" in all_metrics


def test_cache_statistics(fsa):
    """Test 64: Cache statistics."""
    fsa.cache.set("key1", "value1")
    fsa.cache.get("key1")  # Hit
    fsa.cache.get("key2")  # Miss

    stats = fsa.get_cache_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["hit_rate"] == 0.5


# ============================================================================
# Additional Coverage Tests
# ============================================================================

def test_transform_config_metadata(transform_config):
    """Test 65: Transform config with metadata."""
    transform_config.metadata = {"author": "test", "version": "1.0"}
    assert transform_config.metadata["author"] == "test"


def test_schema_field_with_description():
    """Test 66: Schema field with description."""
    field = SchemaField(
        name="email",
        type="string",
        required=True,
        description="User email address",
    )
    assert field.description == "User email address"


def test_metrics_to_dict():
    """Test 67: Metrics conversion to dict."""
    metrics = TransformMetrics(
        transform_id="test",
        operation="test_op",
        records_processed=100,
    )
    metrics.complete()

    metrics_dict = metrics.to_dict()
    assert metrics_dict["transform_id"] == "test"
    assert metrics_dict["records_processed"] == 100


def test_field_mapping_missing_required_field(fsa):
    """Test 68: Field mapping with missing required field."""
    data = {}
    mappings = [
        FieldMapping(
            source_field="missing",
            target_field="target",
            required=True,
        ),
    ]

    with pytest.raises(TransformationError):
        fsa.map_fields(data, mappings)


def test_aggregation_with_empty_data(fsa):
    """Test 69: Aggregation with empty data."""
    result = fsa._apply_aggregations([], {"age": AggregationFunction.SUM}, None)
    assert isinstance(result, dict)


def test_enrichment_with_list_data(fsa):
    """Test 70: Enrichment with list of records."""
    def mock_enrichment(key):
        return {"status": "active"}

    fsa.register_enrichment_source("status_lookup", mock_enrichment)

    data = [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"},
    ]

    result = fsa.enrich_data(data, "status_lookup", "id")
    assert all(record.get("status") == "active" for record in result)
