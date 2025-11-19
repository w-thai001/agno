"""
FSA Workflow Engine Example: Data Processing Pipeline

This example demonstrates the FSA-3.1 workflow engine with:
- State-based execution flow
- Error handling and retry logic
- State transitions with conditions
- Context data passing between states
"""

from agno.workflow.fsa import (
    FSAEngine,
    State,
    StateType,
    Transition,
    TransitionCondition,
    StateContext,
    ErrorHandler,
)
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Define state actions
def initialize_pipeline(context: StateContext) -> dict:
    """Initialize the data pipeline"""
    logger.info("Initializing data pipeline...")
    context.data["status"] = "initialized"
    context.data["records_processed"] = 0
    return {"initialized": True}


def fetch_data(context: StateContext) -> dict:
    """Fetch data from source"""
    logger.info("Fetching data from source...")

    # Simulate data fetching
    sample_data = [
        {"id": 1, "value": 100},
        {"id": 2, "value": 200},
        {"id": 3, "value": 300},
    ]

    context.data["raw_data"] = sample_data
    context.data["fetch_status"] = "success"

    return {"fetched": len(sample_data)}


def validate_data(context: StateContext) -> bool:
    """Validate fetched data"""
    logger.info("Validating data...")

    raw_data = context.data.get("raw_data", [])

    # Validation logic
    if not raw_data:
        logger.error("No data to validate")
        return False

    # Check all records have required fields
    valid = all("id" in record and "value" in record for record in raw_data)

    context.data["validation_passed"] = valid

    if valid:
        logger.info(f"Validation passed for {len(raw_data)} records")
    else:
        logger.error("Validation failed")

    return valid


def transform_data(context: StateContext) -> dict:
    """Transform and enrich data"""
    logger.info("Transforming data...")

    raw_data = context.data.get("raw_data", [])

    # Apply transformations
    transformed = []
    for record in raw_data:
        transformed_record = {
            "id": record["id"],
            "value": record["value"],
            "doubled": record["value"] * 2,
            "category": "high" if record["value"] > 150 else "low"
        }
        transformed.append(transformed_record)

    context.data["transformed_data"] = transformed
    context.data["records_processed"] = len(transformed)

    logger.info(f"Transformed {len(transformed)} records")

    return {"transformed": len(transformed)}


def save_results(context: StateContext) -> dict:
    """Save processed results"""
    logger.info("Saving results...")

    transformed_data = context.data.get("transformed_data", [])

    # Simulate saving to storage
    context.data["saved_count"] = len(transformed_data)
    context.data["save_status"] = "completed"

    logger.info(f"Saved {len(transformed_data)} records")

    return {"saved": len(transformed_data)}


def handle_validation_error(context: StateContext) -> dict:
    """Handle validation errors"""
    logger.warning("Handling validation error...")

    # Log error details
    last_error = context.get_last_error()
    if last_error:
        logger.error(f"Error details: {last_error}")

    # Clean up and prepare for retry
    context.data["retry_attempted"] = True

    return {"error_handled": True}


def finalize_pipeline(context: StateContext) -> dict:
    """Finalize and report results"""
    logger.info("Finalizing pipeline...")

    # Generate summary
    summary = {
        "total_records": len(context.data.get("raw_data", [])),
        "processed_records": context.data.get("records_processed", 0),
        "saved_records": context.data.get("saved_count", 0),
        "status": context.data.get("save_status", "unknown"),
    }

    context.data["summary"] = summary

    logger.info(f"Pipeline complete: {summary}")

    return summary


# Create states
start_state = State(
    name="start",
    state_type=StateType.START,
    action=initialize_pipeline,
)

fetch_state = State(
    name="fetch",
    state_type=StateType.INTERMEDIATE,
    action=fetch_data,
)

validate_state = State(
    name="validate",
    state_type=StateType.INTERMEDIATE,
    action=validate_data,
)

transform_state = State(
    name="transform",
    state_type=StateType.INTERMEDIATE,
    action=transform_data,
)

save_state = State(
    name="save",
    state_type=StateType.INTERMEDIATE,
    action=save_results,
)

error_state = State(
    name="error_handler",
    state_type=StateType.RECOVERY,
    action=handle_validation_error,
)

end_state = State(
    name="end",
    state_type=StateType.END,
    action=finalize_pipeline,
)


# Create transitions
transitions = [
    # Happy path
    Transition(
        from_state="start",
        to_state="fetch",
        condition=TransitionCondition.SUCCESS,
        priority=10,
    ),
    Transition(
        from_state="fetch",
        to_state="validate",
        condition=TransitionCondition.SUCCESS,
        priority=10,
    ),
    Transition(
        from_state="validate",
        to_state="transform",
        condition=TransitionCondition.CONDITION_MET,  # validate_data returns bool
        priority=10,
    ),
    Transition(
        from_state="transform",
        to_state="save",
        condition=TransitionCondition.SUCCESS,
        priority=10,
    ),
    Transition(
        from_state="save",
        to_state="end",
        condition=TransitionCondition.SUCCESS,
        priority=10,
    ),

    # Error handling path
    Transition(
        from_state="validate",
        to_state="error_handler",
        condition=TransitionCondition.FAILURE,
        priority=5,
    ),
    Transition(
        from_state="error_handler",
        to_state="end",
        condition=TransitionCondition.ALWAYS,
        priority=1,
    ),
]


def run_data_pipeline():
    """Run the data processing pipeline using FSA engine"""

    # Configure error handler
    error_handler = ErrorHandler(
        max_retries=2,
        retry_states=["fetch", "save"],
    )

    # Create FSA engine
    engine = FSAEngine(
        states={
            "start": start_state,
            "fetch": fetch_state,
            "validate": validate_state,
            "transform": transform_state,
            "save": save_state,
            "error_handler": error_state,
            "end": end_state,
        },
        transitions=transitions,
        initial_state="start",
        error_handler=error_handler,
    )

    # Run the workflow
    logger.info("=" * 60)
    logger.info("Starting Data Processing Pipeline")
    logger.info("=" * 60)

    context = engine.run()

    # Display results
    logger.info("=" * 60)
    logger.info("Pipeline Execution Complete")
    logger.info("=" * 60)

    print("\n=== Execution Summary ===")
    print(f"Final State: {context.metadata['execution']['current_state']}")
    print(f"Total Steps: {context.metadata['completed_steps']}")
    print(f"Total Transitions: {context.metadata['execution']['total_transitions']}")
    print(f"Duration: {context.metadata['execution']['duration_ms']:.2f}ms")

    print("\n=== State Visit History ===")
    print(" -> ".join(context.history))

    print("\n=== Pipeline Results ===")
    if "summary" in context.data:
        for key, value in context.data["summary"].items():
            print(f"{key}: {value}")

    if context.errors:
        print("\n=== Errors Encountered ===")
        for error in context.errors:
            print(f"State: {error['state']}, Error: {error['error']}")

    return context


def run_async_pipeline():
    """Run pipeline with step-by-step execution"""

    # Configure error handler
    error_handler = ErrorHandler(
        max_retries=2,
        retry_states=["fetch", "save"],
    )

    # Create FSA engine
    engine = FSAEngine(
        states={
            "start": start_state,
            "fetch": fetch_state,
            "validate": validate_state,
            "transform": transform_state,
            "save": save_state,
            "error_handler": error_state,
            "end": end_state,
        },
        transitions=transitions,
        initial_state="start",
        error_handler=error_handler,
    )

    # Run async
    logger.info("=" * 60)
    logger.info("Starting Async Data Processing Pipeline")
    logger.info("=" * 60)

    for step_num, (state_name, context) in enumerate(engine.run_async(), start=1):
        print(f"\nStep {step_num}: Executing state '{state_name}'")
        print(f"  Current data keys: {list(context.data.keys())}")
        print(f"  Records processed: {context.data.get('records_processed', 0)}")

    print("\n" + "=" * 60)
    print("Async Pipeline Complete")
    print("=" * 60)


if __name__ == "__main__":
    # Run synchronous pipeline
    print("\n" + "=" * 60)
    print("SYNCHRONOUS EXECUTION")
    print("=" * 60)
    run_data_pipeline()

    # Run async pipeline
    print("\n\n" + "=" * 60)
    print("ASYNCHRONOUS EXECUTION")
    print("=" * 60)
    run_async_pipeline()
