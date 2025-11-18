"""
Pipeline Transformation Examples

This example demonstrates pipeline creation and execution with the
Data Transformer FSA.
"""

from agno.fsa import DataTransformerFSA
from agno.fsa.data_transformer import (
    ConditionalBranching,
    ErrorStrategy,
    Pipeline,
    PipelineBuilder,
    Transformation,
)


def main():
    transformer = DataTransformerFSA()

    print("=" * 80)
    print("Data Transformer FSA - Pipeline Examples")
    print("=" * 80)

    # Example 1: Simple Pipeline
    print("\n1. Simple Sequential Pipeline")
    print("-" * 80)

    def normalize_email(data):
        if "email" in data:
            data["email"] = data["email"].lower().strip()
        return data

    def add_full_name(data):
        first = data.get("first_name", "")
        last = data.get("last_name", "")
        data["full_name"] = f"{first} {last}".strip()
        return data

    pipeline = (
        PipelineBuilder("user_cleanup")
        .add_transformation("normalize_email", normalize_email)
        .add_transformation("add_full_name", add_full_name)
        .build()
    )

    user_data = {"first_name": "Alice", "last_name": "Doe", "email": " ALICE@EXAMPLE.COM "}

    result = transformer.execute_pipeline(user_data, pipeline)

    print("Input:")
    print(user_data)
    print("\nOutput:")
    print(result.data)

    # Example 2: Pipeline with Error Handling
    print("\n\n2. Pipeline with Error Handling")
    print("-" * 80)

    def safe_divide(data):
        if "value" in data and "divisor" in data:
            data["result"] = data["value"] / data["divisor"]
        return data

    def add_metadata(data):
        data["processed"] = True
        return data

    pipeline = (
        PipelineBuilder("safe_calculation")
        .add_transformation("divide", safe_divide, error_strategy=ErrorStrategy.LOG)
        .add_transformation("add_metadata", add_metadata)
        .with_error_strategy(ErrorStrategy.LOG)
        .build()
    )

    # Test with valid data
    valid_data = {"value": 100, "divisor": 5}
    result = transformer.execute_pipeline(valid_data, pipeline)
    print("Valid Data Result:")
    print(result.data)

    # Test with invalid data (division by zero)
    invalid_data = {"value": 100, "divisor": 0}
    result = transformer.execute_pipeline(invalid_data, pipeline)
    print("\nInvalid Data Result:")
    print(f"Data: {result.data}")
    print(f"Errors: {result.errors}")

    # Example 3: Conditional Pipeline
    print("\n\n3. Conditional Pipeline Branching")
    print("-" * 80)

    def process_premium(data):
        return {**data, "discount": 0.2, "tier": "premium"}

    def process_regular(data):
        return {**data, "discount": 0.05, "tier": "regular"}

    conditional_transform = ConditionalBranching.create_conditional_transformation(
        name="apply_tier",
        condition=lambda x: x.get("purchases", 0) > 100,
        true_function=process_premium,
        false_function=process_regular,
    )

    pipeline = Pipeline(name="user_tier", transformations=[conditional_transform])

    user1 = {"name": "Alice", "purchases": 150}
    user2 = {"name": "Bob", "purchases": 50}

    from agno.fsa.data_transformer import TransformationPipeline

    executor = TransformationPipeline(pipeline)

    result1 = executor.execute(user1)
    result2 = executor.execute(user2)

    print("User 1 (150 purchases):")
    print(result1.data)
    print("\nUser 2 (50 purchases):")
    print(result2.data)

    # Example 4: Batch Processing Pipeline
    print("\n\n4. Batch Processing")
    print("-" * 80)

    def clean_record(data):
        return {
            "name": data.get("name", "").title(),
            "email": data.get("email", "").lower(),
            "status": data.get("status", "active"),
        }

    transformation = Transformation(name="clean", function=clean_record)
    pipeline = transformer.create_pipeline("batch_clean", [transformation])

    records = [
        {"name": "alice smith", "email": "ALICE@EXAMPLE.COM"},
        {"name": "bob jones", "email": "BOB@EXAMPLE.COM"},
        {"name": "charlie brown", "email": "CHARLIE@EXAMPLE.COM"},
    ]

    print("Processing 3 records in batch...")
    results = transformer.batch_transform(records, pipeline)

    print("\nResults:")
    for i, result in enumerate(results, 1):
        print(f"{i}. {result.data}")

    # Example 5: Parallel Batch Processing
    print("\n\n5. Parallel Batch Processing")
    print("-" * 80)

    def expensive_operation(data):
        # Simulate expensive operation
        import time

        time.sleep(0.1)
        return {"id": data["id"], "processed": True, "value": data["id"] * 2}

    transformation = Transformation(name="expensive", function=expensive_operation)
    pipeline = transformer.create_pipeline("parallel_test", [transformation])

    large_batch = [{"id": i} for i in range(10)]

    print("Processing 10 records in parallel...")
    import time

    start = time.time()
    results = transformer.batch_transform(large_batch, pipeline, parallel=True, max_workers=4)
    duration = time.time() - start

    print(f"Processed {len(results)} records in {duration:.2f} seconds")
    print(f"First result: {results[0].data}")
    print(f"Last result: {results[-1].data}")

    # Example 6: Streaming Pipeline
    print("\n\n6. Streaming Data Processing")
    print("-" * 80)

    def data_generator():
        """Simulate streaming data source."""
        for i in range(5):
            yield {"id": i, "value": i * 10}

    def categorize(data):
        value = data.get("value", 0)
        if value > 20:
            return {**data, "category": "high"}
        else:
            return {**data, "category": "low"}

    transformation = Transformation(name="categorize", function=categorize)
    pipeline = transformer.create_pipeline("stream_process", [transformation])

    print("Processing stream...")
    for result in transformer.stream_transform(data_generator(), pipeline):
        print(f"  {result}")

    # Example 7: Complex Multi-Step Pipeline
    print("\n\n7. Complex Multi-Step Pipeline")
    print("-" * 80)

    def validate_email(data):
        import re

        email = data.get("email", "")
        pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        data["email_valid"] = bool(re.match(pattern, email))
        return data

    def compute_age_group(data):
        age = data.get("age", 0)
        if age < 18:
            data["age_group"] = "minor"
        elif age < 65:
            data["age_group"] = "adult"
        else:
            data["age_group"] = "senior"
        return data

    def add_timestamp(data):
        from datetime import datetime

        data["processed_at"] = datetime.now().isoformat()
        return data

    pipeline = (
        PipelineBuilder("comprehensive_processing")
        .add_transformation("validate_email", validate_email)
        .add_transformation("compute_age_group", compute_age_group)
        .add_transformation("add_timestamp", add_timestamp)
        .with_metadata(version="1.0", author="Data Team")
        .build()
    )

    user = {"name": "Alice", "age": 30, "email": "alice@example.com"}

    result = transformer.execute_pipeline(user, pipeline)

    print("Input:")
    print(user)
    print("\nOutput:")
    print(result.data)
    print(f"\nPipeline Metadata: {pipeline.metadata}")

    print("\n" + "=" * 80)
    print("Pipeline examples completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    main()
