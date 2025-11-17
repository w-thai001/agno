"""
Example usage of StateManagerFSA

This file demonstrates how to use the State Manager FSA for task state
persistence and recovery.
"""

from agno.state_manager_fsa import (
    StateManagerFSA,
    TaskState,
    CheckpointConfig,
    StateVersion
)


def example_basic_usage():
    """Basic usage example"""

    # Create a state manager with custom configuration
    config = CheckpointConfig(
        auto_checkpoint=True,
        checkpoint_interval=300,  # 5 minutes
        max_checkpoints=10
    )

    fsm = StateManagerFSA(
        storage_path="/tmp/my_app_states",
        checkpoint_config=config
    )

    # Create a new task
    task = fsm.create_task(
        task_id="data_processing_001",
        data={
            "source": "dataset.csv",
            "rows_processed": 0,
            "total_rows": 1000
        },
        metadata={"priority": "high", "user": "user_123"}
    )

    # Transition task through states
    fsm.transition_state("data_processing_001", TaskState.IN_PROGRESS)

    # Update task data (simulate work)
    task = fsm.get_task("data_processing_001")
    task.data["rows_processed"] = 500

    # Create a checkpoint
    checkpoint = fsm.create_checkpoint(
        "data_processing_001",
        metadata={"note": "halfway done"}
    )

    # Continue processing...
    task.data["rows_processed"] = 1000

    # Complete the task
    fsm.transition_state("data_processing_001", TaskState.COMPLETED)

    # Save final state
    fsm.save_state("data_processing_001")


def example_recovery():
    """Example of recovering from interruption"""

    # Initial run
    fsm1 = StateManagerFSA(storage_path="/tmp/app_states")
    fsm1.create_task("long_running_task", data={"progress": 0})
    fsm1.transition_state("long_running_task", TaskState.IN_PROGRESS)

    task = fsm1.get_task("long_running_task")
    task.data["progress"] = 75

    # Create checkpoint before potential failure
    fsm1.create_checkpoint("long_running_task")
    fsm1.save_state("long_running_task")

    # ... application crashes or is interrupted ...

    # Recovery in new instance
    fsm2 = StateManagerFSA(storage_path="/tmp/app_states")

    # Recover the task
    success = fsm2.recover_task("long_running_task")

    if success:
        task = fsm2.get_task("long_running_task")
        print(f"Recovered task at progress: {task.data['progress']}%")

        # Continue from where we left off
        fsm2.transition_state("long_running_task", TaskState.IN_PROGRESS)
        # ... resume processing ...


def example_error_handling():
    """Example of handling task failures with retry logic"""

    fsm = StateManagerFSA(storage_path="/tmp/app_states")

    task = fsm.create_task(
        "api_call_task",
        data={"endpoint": "/api/data", "attempt": 1},
        max_retries=3
    )

    fsm.transition_state("api_call_task", TaskState.IN_PROGRESS)

    try:
        # Simulate API call
        # api_response = call_external_api()
        raise Exception("Connection timeout")

    except Exception as e:
        # Mark task as failed
        fsm.transition_state(
            "api_call_task",
            TaskState.FAILED,
            error_message=str(e)
        )

        # Check if we can retry
        task = fsm.get_task("api_call_task")
        if task.retry_count < task.max_retries:
            # Transition to recovering state
            fsm.transition_state("api_call_task", TaskState.RECOVERING)
            # ... implement retry logic ...
        else:
            print(f"Task failed after {task.max_retries} retries")


def example_batch_processing():
    """Example of managing multiple tasks"""

    fsm = StateManagerFSA(storage_path="/tmp/batch_states")

    # Create multiple tasks
    for i in range(10):
        fsm.create_task(
            f"batch_item_{i}",
            data={"item_id": i, "status": "pending"}
        )

    # Get all pending tasks
    pending_tasks = fsm.get_all_tasks(state_filter=TaskState.PENDING)

    for task in pending_tasks:
        # Process each task
        fsm.transition_state(task.task_id, TaskState.IN_PROGRESS)

        # ... do work ...

        # Mark as completed
        fsm.transition_state(task.task_id, TaskState.COMPLETED)

    # Get statistics
    stats = fsm.get_statistics()
    print(f"Completed: {stats['state_counts']['completed']} tasks")


def example_checkpoint_restoration():
    """Example of restoring from a specific checkpoint"""

    fsm = StateManagerFSA(storage_path="/tmp/app_states")

    task = fsm.create_task("model_training", data={"epoch": 0, "loss": 1.0})
    fsm.transition_state("model_training", TaskState.IN_PROGRESS)

    # Create checkpoints at different epochs
    for epoch in range(1, 6):
        task = fsm.get_task("model_training")
        task.data["epoch"] = epoch
        task.data["loss"] = 1.0 / (epoch + 1)

        checkpoint = fsm.create_checkpoint(
            "model_training",
            checkpoint_id=f"epoch_{epoch}",
            metadata={"epoch": epoch}
        )

    # Restore to epoch 3
    fsm.restore_checkpoint("model_training", "epoch_3")

    task = fsm.get_task("model_training")
    print(f"Restored to epoch {task.data['epoch']} with loss {task.data['loss']}")


if __name__ == "__main__":
    # Run examples
    print("Running State Manager FSA examples...")

    print("\n1. Basic Usage")
    example_basic_usage()

    print("\n2. Recovery Example")
    example_recovery()

    print("\n3. Error Handling")
    example_error_handling()

    print("\n4. Batch Processing")
    example_batch_processing()

    print("\n5. Checkpoint Restoration")
    example_checkpoint_restoration()

    print("\nAll examples completed!")
