"""
Basic Data Transformations

This example demonstrates basic data transformation capabilities of the
Data Transformer FSA.
"""

from agno.fsa import DataTransformerFSA
from agno.fsa.data_transformer import (
    FieldDefinition,
    Schema,
    TransformationRule,
    TransformationRules,
    TransformationType,
)


def main():
    # Initialize the transformer
    transformer = DataTransformerFSA()

    print("=" * 80)
    print("Data Transformer FSA - Basic Transformations")
    print("=" * 80)

    # Example 1: Format Conversion
    print("\n1. Format Conversion: JSON to CSV")
    print("-" * 80)

    json_data = '[{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]'
    csv_result = transformer.convert_format(json_data, "json", "csv")

    print("Input (JSON):")
    print(json_data)
    print("\nOutput (CSV):")
    print(csv_result)

    # Example 2: Field Mapping
    print("\n\n2. Field Mapping: Rename Fields")
    print("-" * 80)

    rules = TransformationRules()
    rules.add_rule(
        TransformationRule(
            name="rename_first_name",
            type=TransformationType.FIELD_MAPPING,
            source_field="first_name",
            target_field="firstName",
            parameters={"operation": "rename"},
        )
    )

    data = {"first_name": "Alice", "last_name": "Doe"}
    result = transformer.transform(data, "json", rules)

    print("Input:")
    print(data)
    print("\nOutput:")
    print(result.data)

    # Example 3: Type Conversion
    print("\n\n3. Type Conversion: String to Integer")
    print("-" * 80)

    rules = TransformationRules()
    rules.add_rule(
        TransformationRule(
            name="convert_age",
            type=TransformationType.TYPE_CONVERSION,
            source_field="age",
            parameters={"target_type": "int"},
        )
    )

    data = {"name": "Alice", "age": "30"}
    result = transformer.transform(data, "json", rules)

    print("Input:")
    print(data)
    print("\nOutput:")
    print(result.data)

    # Example 4: Schema Definition and Validation
    print("\n\n4. Schema Validation")
    print("-" * 80)

    user_schema = Schema(
        name="user",
        version="1.0.0",
        fields={
            "name": FieldDefinition(name="name", type="string", required=True),
            "age": FieldDefinition(name="age", type="integer", required=False),
            "email": FieldDefinition(name="email", type="string", required=True),
        },
    )

    transformer.register_schema(user_schema)

    # Valid data
    valid_data = {"name": "Alice", "age": 30, "email": "alice@example.com"}
    validation_result = transformer.validate_data(valid_data, user_schema)

    print("Valid Data:")
    print(valid_data)
    print(f"Is Valid: {validation_result.is_valid}")

    # Invalid data (missing required field)
    invalid_data = {"name": "Bob", "age": 25}  # Missing email
    validation_result = transformer.validate_data(invalid_data, user_schema)

    print("\nInvalid Data:")
    print(invalid_data)
    print(f"Is Valid: {validation_result.is_valid}")
    print(f"Errors: {validation_result.errors}")

    # Example 5: Schema Inference
    print("\n\n5. Schema Inference from Data")
    print("-" * 80)

    sample_data = [
        {"name": "Alice", "age": 30, "active": True},
        {"name": "Bob", "age": 25, "active": False},
    ]

    inferred_schema = transformer.infer_schema(sample_data, "users")

    print("Sample Data:")
    print(sample_data)
    print(f"\nInferred Schema: {inferred_schema.name}")
    print("Fields:")
    for field_name, field_def in inferred_schema.fields.items():
        print(f"  - {field_name}: {field_def.type} (required={field_def.required})")

    # Example 6: Data Filtering
    print("\n\n6. Data Filtering")
    print("-" * 80)

    users = [
        {"name": "Alice", "age": 30, "status": "active"},
        {"name": "Bob", "age": 17, "status": "inactive"},
        {"name": "Charlie", "age": 25, "status": "active"},
    ]

    filtered = transformer.filter_data(users, lambda x: x.get("age", 0) >= 18 and x.get("status") == "active")

    print("Original Data:")
    for user in users:
        print(f"  {user}")

    print("\nFiltered Data (age >= 18 and status = active):")
    for user in filtered:
        print(f"  {user}")

    # Example 7: Data Aggregation
    print("\n\n7. Data Aggregation")
    print("-" * 80)

    from agno.fsa.data_transformer import AggregationConfig

    sales_data = [
        {"product": "Widget", "category": "A", "amount": 100},
        {"product": "Gadget", "category": "A", "amount": 200},
        {"product": "Tool", "category": "B", "amount": 150},
    ]

    config = AggregationConfig(group_by=["category"], aggregations={"amount": ["sum", "avg", "count"]})

    result = transformer.aggregate_data(sales_data, config)

    print("Sales Data:")
    for sale in sales_data:
        print(f"  {sale}")

    print("\nAggregated by Category:")
    for agg in result:
        print(f"  {agg}")

    print("\n" + "=" * 80)
    print("Examples completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    main()
