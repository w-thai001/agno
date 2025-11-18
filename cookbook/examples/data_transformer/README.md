# Data Transformer FSA

Universal data transformation engine for the Agno framework that converts, validates, enriches, and normalizes data between formats, schemas, and protocols with pipeline composition and error recovery.

## Features

- **Multi-Format Support**: JSON, XML, CSV, Parquet, Avro, Protocol Buffers, YAML
- **Schema Management**: Automatic inference, validation, migration, and versioning
- **Data Enrichment**: Lookup tables, API calls, computed fields
- **Transformation Pipelines**: Composable, chainable transformations with error handling
- **Field-Level Operations**: Map, filter, reduce, aggregate, transform
- **Type Conversion**: Automatic type coercion with validation
- **Batch & Streaming**: Support for both batch and streaming data processing
- **Error Recovery**: Multiple strategies (retry, skip, fallback, log)

## Installation

```bash
cd /home/user/agno
pip install -e libs/agno
```

### Dependencies

```bash
pip install pandas pyarrow lxml pyyaml avro-python3
```

## Quick Start

```python
from agno.fsa import DataTransformerFSA

# Initialize the transformer
transformer = DataTransformerFSA()

# Convert JSON to CSV
json_data = '[{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]'
csv_result = transformer.convert_format(json_data, "json", "csv")
print(csv_result)
```

## Core Capabilities

### 1. Format Conversion

Convert between different data formats seamlessly:

```python
# JSON to XML
json_data = '{"user": {"name": "Alice", "age": 30}}'
xml_result = transformer.convert_format(json_data, "json", "xml")

# CSV to JSON
csv_data = "name,age\\nAlice,30\\nBob,25"
json_result = transformer.convert_format(csv_data, "csv", "json")

# JSON to YAML
yaml_result = transformer.convert_format(json_data, "json", "yaml")
```

### 2. Schema Management

Define, infer, and validate data schemas:

```python
from agno.fsa.data_transformer import Schema, FieldDefinition

# Define a schema
user_schema = Schema(
    name="user",
    version="1.0.0",
    fields={
        "name": FieldDefinition(name="name", type="string", required=True),
        "age": FieldDefinition(name="age", type="integer", required=False),
        "email": FieldDefinition(name="email", type="string", required=True)
    }
)

# Register the schema
transformer.register_schema(user_schema)

# Infer schema from data
data = [
    {"name": "Alice", "age": 30, "email": "alice@example.com"},
    {"name": "Bob", "age": 25, "email": "bob@example.com"}
]
inferred_schema = transformer.infer_schema(data, "users")

# Validate data against schema
validation_result = transformer.validate_data(data[0], user_schema)
if not validation_result.is_valid:
    print("Validation errors:", validation_result.errors)
```

### 3. Transformation Pipelines

Create reusable transformation pipelines:

```python
from agno.fsa.data_transformer import PipelineBuilder, Transformation

# Build a pipeline using the fluent API
pipeline = (
    PipelineBuilder("user_data_cleanup")
    .add_transformation(
        "normalize_email",
        lambda data: {
            **data,
            "email": data.get("email", "").lower().strip()
        }
    )
    .add_transformation(
        "add_full_name",
        lambda data: {
            **data,
            "full_name": f"{data.get('first_name', '')} {data.get('last_name', '')}"
        }
    )
    .with_error_strategy(ErrorStrategy.LOG)
    .build()
)

# Execute the pipeline
data = {"first_name": "Alice", "last_name": "Doe", "email": " ALICE@EXAMPLE.COM "}
result = transformer.execute_pipeline(data, pipeline)
print(result.data)
# Output: {'first_name': 'Alice', 'last_name': 'Doe', 'email': 'alice@example.com', 'full_name': 'Alice Doe'}
```

### 4. Data Enrichment

Enrich data with additional information:

```python
from agno.fsa.data_transformer import Enricher

# Add a lookup table
transformer.add_lookup_table("countries", {
    "US": "United States",
    "UK": "United Kingdom",
    "CA": "Canada"
})

# Define an enricher
def geocode_enricher(source_fields):
    # Simulate API call
    city = source_fields.get("city", "")
    return {
        "latitude": 40.7128 if city == "NYC" else 0.0,
        "longitude": -74.0060 if city == "NYC" else 0.0
    }

enricher = Enricher(
    name="geocode",
    enricher_function=geocode_enricher,
    source_fields=["city"],
    target_fields=["latitude", "longitude"]
)

# Enrich data
data = {"name": "Alice", "city": "NYC"}
enriched = transformer.enrich_data(data, [enricher])
print(enriched)
# Output: {'name': 'Alice', 'city': 'NYC', 'latitude': 40.7128, 'longitude': -74.006}
```

### 5. Data Aggregation

Aggregate and group data:

```python
from agno.fsa.data_transformer import AggregationConfig

# Sample sales data
sales_data = [
    {"product": "Widget", "category": "A", "amount": 100, "quantity": 10},
    {"product": "Gadget", "category": "A", "amount": 200, "quantity": 5},
    {"product": "Tool", "category": "B", "amount": 150, "quantity": 8}
]

# Configure aggregation
config = AggregationConfig(
    group_by=["category"],
    aggregations={
        "amount": ["sum", "avg", "count"],
        "quantity": ["sum", "max"]
    }
)

# Aggregate
result = transformer.aggregate_data(sales_data, config)
print(result)
# Output: [
#   {'category': 'A', 'amount_sum': 300, 'amount_avg': 150, 'amount_count': 2, 'quantity_sum': 15, 'quantity_max': 10},
#   {'category': 'B', 'amount_sum': 150, 'amount_avg': 150, 'amount_count': 1, 'quantity_sum': 8, 'quantity_max': 8}
# ]
```

### 6. Data Filtering

Filter data based on conditions:

```python
# Filter data
users = [
    {"name": "Alice", "age": 30, "status": "active"},
    {"name": "Bob", "age": 17, "status": "inactive"},
    {"name": "Charlie", "age": 25, "status": "active"}
]

# Filter adults who are active
filtered = transformer.filter_data(
    users,
    lambda x: x.get("age", 0) >= 18 and x.get("status") == "active"
)
print(filtered)
# Output: [{'name': 'Alice', 'age': 30, 'status': 'active'}, {'name': 'Charlie', 'age': 25, 'status': 'active'}]
```

### 7. Batch Processing

Process multiple records efficiently:

```python
# Create a pipeline
def clean_record(data):
    return {
        "name": data.get("name", "").title(),
        "email": data.get("email", "").lower()
    }

transformation = Transformation(name="clean", function=clean_record)
pipeline = transformer.create_pipeline("batch_clean", [transformation])

# Process batch
records = [
    {"name": "alice", "email": "ALICE@EXAMPLE.COM"},
    {"name": "bob", "email": "BOB@EXAMPLE.COM"}
]

results = transformer.batch_transform(records, pipeline, parallel=True, max_workers=4)
print(results)
```

### 8. Streaming Data

Process streaming data:

```python
def data_generator():
    """Simulate streaming data source."""
    for i in range(100):
        yield {"id": i, "value": i * 2}

# Create transformation pipeline
def validate_and_filter(data):
    if data.get("value", 0) > 50:
        return {"id": data["id"], "value": data["value"], "category": "high"}
    return {"id": data["id"], "value": data["value"], "category": "low"}

transformation = Transformation(name="categorize", function=validate_and_filter)
pipeline = transformer.create_pipeline("stream_process", [transformation])

# Process stream
for result in transformer.stream_transform(data_generator(), pipeline):
    print(result)
```

## Advanced Examples

### Field Mapping and Transformation

```python
from agno.fsa.data_transformer import TransformationRule, TransformationRules, TransformationType

# Define transformation rules
rules = TransformationRules()

# Rename fields
rules.add_rule(TransformationRule(
    name="rename_first_name",
    type=TransformationType.FIELD_MAPPING,
    source_field="first_name",
    target_field="firstName",
    parameters={"operation": "rename"}
))

# Convert types
rules.add_rule(TransformationRule(
    name="convert_age",
    type=TransformationType.TYPE_CONVERSION,
    source_field="age",
    parameters={"target_type": "int"}
))

# Normalize values
rules.add_rule(TransformationRule(
    name="uppercase_email",
    type=TransformationType.VALUE_TRANSFORMATION,
    source_field="email",
    parameters={"normalizer": "lowercase"}
))

# Apply transformations
data = {"first_name": "Alice", "age": "30", "email": "ALICE@EXAMPLE.COM"}
result = transformer.transform(data, "json", rules)
print(result.data)
```

### Schema Migration

```python
# Define version 1 schema
schema_v1 = Schema(
    name="user",
    version="1.0.0",
    fields={
        "name": FieldDefinition(name="name", type="string", required=True)
    }
)

# Define version 2 schema (added email field)
schema_v2 = Schema(
    name="user",
    version="2.0.0",
    fields={
        "name": FieldDefinition(name="name", type="string", required=True),
        "email": FieldDefinition(name="email", type="string", required=False, default="")
    }
)

# Register both versions
transformer.register_schema(schema_v1)
transformer.register_schema(schema_v2)

# Migrate data from v1 to v2
old_data = {"name": "Alice"}
migrated = transformer.migrate_schema(old_data, "user", "user", "1.0.0", "2.0.0")
print(migrated)
# Output: {'name': 'Alice', 'email': ''}
```

### Conditional Pipeline Branching

```python
from agno.fsa.data_transformer import ConditionalBranching

def process_premium_user(data):
    return {**data, "discount": 0.2, "tier": "premium"}

def process_regular_user(data):
    return {**data, "discount": 0.05, "tier": "regular"}

# Create conditional transformation
conditional_transform = ConditionalBranching.create_conditional_transformation(
    name="apply_discount",
    condition=lambda x: x.get("purchases", 0) > 100,
    true_function=process_premium_user,
    false_function=process_regular_user
)

# Use in pipeline
pipeline = Pipeline(name="user_tier", transformations=[conditional_transform])
executor = TransformationPipeline(pipeline)

# Test
user1 = {"name": "Alice", "purchases": 150}
user2 = {"name": "Bob", "purchases": 50}

result1 = executor.execute(user1)
result2 = executor.execute(user2)

print(result1.data)  # {'name': 'Alice', 'purchases': 150, 'discount': 0.2, 'tier': 'premium'}
print(result2.data)  # {'name': 'Bob', 'purchases': 50, 'discount': 0.05, 'tier': 'regular'}
```

### Custom Transformers

```python
# Register a custom transformer
def encrypt_field(data, field_name="password"):
    import hashlib
    if field_name in data:
        data[field_name] = hashlib.sha256(data[field_name].encode()).hexdigest()
    return data

transformer.register_custom_transformer("encrypt", encrypt_field)

# Use the custom transformer
custom_transformer = transformer.get_custom_transformer("encrypt")
sensitive_data = {"username": "alice", "password": "secret123"}
secured = custom_transformer(sensitive_data, field_name="password")
print(secured)
```

## Error Handling

The Data Transformer FSA provides multiple error handling strategies:

```python
from agno.fsa.data_transformer import ErrorStrategy

# RAISE: Raise exception on error (default)
# SKIP: Skip failed records
# RETRY: Retry failed operations
# FALLBACK: Use fallback value
# LOG: Log error and continue

# Example with different strategies
def risky_transform(data):
    if "required_field" not in data:
        raise ValueError("Missing required field")
    return data

# Strategy 1: Skip failed records
transformation_skip = Transformation(
    name="risky",
    function=risky_transform,
    error_strategy=ErrorStrategy.SKIP
)

# Strategy 2: Retry with exponential backoff
transformation_retry = Transformation(
    name="risky",
    function=risky_transform,
    error_strategy=ErrorStrategy.RETRY,
    retry_count=3,
    retry_delay=1.0
)

# Strategy 3: Fallback to original data
transformation_fallback = Transformation(
    name="risky",
    function=risky_transform,
    error_strategy=ErrorStrategy.FALLBACK
)
```

## Performance Optimization

### Parallel Processing

```python
# Enable parallel execution for independent transformations
pipeline = (
    PipelineBuilder("parallel_pipeline")
    .add_transformation("step1", lambda x: x)
    .add_transformation("step2", lambda x: x)
    .with_parallel_execution(max_workers=8)
    .build()
)
```

### Pipeline Optimization

```python
# Optimize pipeline for better performance
pipeline = transformer.create_pipeline("my_pipeline", [...])
optimized_pipeline = transformer.optimize_pipeline(pipeline)
```

### Batch Processing for Large Datasets

```python
# Process large datasets in batches
large_dataset = [{"id": i} for i in range(10000)]

results = transformer.batch_transform(
    large_dataset,
    pipeline,
    parallel=True,
    max_workers=8
)
```

## Testing

Run the comprehensive test suite:

```bash
# Install pytest
pip install pytest pytest-cov

# Run all tests
pytest libs/agno/agno/fsa/data_transformer/tests/ -v

# Run with coverage
pytest libs/agno/agno/fsa/data_transformer/tests/ --cov=agno.fsa.data_transformer --cov-report=html

# Run specific test file
pytest libs/agno/agno/fsa/data_transformer/tests/test_core.py -v
```

## API Reference

### Main Classes

- **DataTransformerFSA**: Main transformation engine
- **PipelineBuilder**: Fluent API for building pipelines
- **Schema**: Data schema definition
- **Enricher**: Data enrichment configuration
- **TransformationRule**: Single transformation rule
- **Pipeline**: Transformation pipeline

### Format Handlers

- **JSONTransformer**: JSON format handler with JSONPath support
- **XMLTransformer**: XML format handler with XPath support
- **CSVTransformer**: CSV format handler with delimiter detection
- **YAMLTransformer**: YAML format handler
- **ParquetTransformer**: Parquet format handler (requires pyarrow)
- **AvroTransformer**: Avro format handler (requires avro-python3)

### Transformation Engines

- **FieldMapper**: Field mapping operations
- **TypeConverter**: Type conversion engine
- **ValueNormalizer**: Value normalization
- **DataValidator**: Data validation
- **DataEnricher**: Data enrichment
- **AggregationEngine**: Data aggregation
- **FilterEngine**: Data filtering

### Schema Management

- **SchemaRegistry**: Schema storage and versioning
- **SchemaInferrer**: Automatic schema inference
- **SchemaMigrator**: Schema migration
- **SchemaValidator**: Schema validation
- **SchemaMapper**: Schema field mapping
- **CompatibilityChecker**: Schema compatibility checking

## Contributing

Contributions are welcome! Please ensure:

1. All tests pass
2. Code coverage remains above 85%
3. Documentation is updated
4. Type hints are included

## License

Part of the Agno framework. See main repository for license information.

## Support

For issues and questions:
- GitHub Issues: https://github.com/anthropics/agno/issues
- Documentation: https://docs.agno.com
