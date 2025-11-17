# State Manager FSA (Finite State Automaton)

A comprehensive state management system for task persistence and recovery in the Agno framework.

## Overview

The State Manager FSA provides robust task state management with the following features:

- **Task State Tracking**: Manage tasks through defined states (pending, in-progress, completed, failed, suspended, recovering)
- **State Persistence**: Save and load task state to/from disk in JSON format
- **Checkpoint Management**: Create checkpoints with timestamps for point-in-time recovery
- **Recovery Mechanisms**: Recover tasks from interruptions and failures
- **State Versioning**: Handle state schema migrations across versions
- **FSA Rules**: Enforce valid state transitions based on finite state automaton rules

## Installation

The State Manager FSA is part of the Agno library:

```bash
pip install agno
```

## Quick Start

```python
from agno.state_manager_fsa import StateManagerFSA, TaskState, CheckpointConfig

# Create a state manager
config = CheckpointConfig(auto_checkpoint=True, checkpoint_interval=300)
fsm = StateManagerFSA(storage_path="/tmp/states", checkpoint_config=config)

# Create a task
task = fsm.create_task(
    task_id="task_1",
    data={"name": "Process data", "progress": 0}
)

# Transition through states
fsm.transition_state("task_1", TaskState.IN_PROGRESS)
fsm.transition_state("task_1", TaskState.COMPLETED)

# Save state
fsm.save_state("task_1")
```

## Core Components

### Task States

The FSA defines the following task states:

- **PENDING**: Task is created and waiting to start
- **IN_PROGRESS**: Task is actively being processed
- **COMPLETED**: Task has finished successfully (terminal state)
- **FAILED**: Task encountered an error
- **SUSPENDED**: Task is temporarily paused
- **RECOVERING**: Task is in recovery mode after interruption

### State Transitions

Valid state transitions are enforced by the FSA:

```
PENDING → [IN_PROGRESS, SUSPENDED, FAILED]
IN_PROGRESS → [COMPLETED, FAILED, SUSPENDED]
COMPLETED → [] (terminal state)
FAILED → [PENDING, RECOVERING]
SUSPENDED → [IN_PROGRESS, FAILED]
RECOVERING → [IN_PROGRESS, FAILED]
```

### Data Structures

#### TaskStateData

Represents the complete state of a task:

```python
@dataclass
class TaskStateData:
    task_id: str
    current_state: TaskState
    data: Dict[str, Any]
    previous_state: Optional[TaskState]
    created_at: float
    updated_at: float
    checkpoints: List[Checkpoint]
    metadata: Optional[Dict[str, Any]]
    retry_count: int
    max_retries: int
    error_message: Optional[str]
```

#### Checkpoint

Represents a point-in-time snapshot of task state:

```python
@dataclass
class Checkpoint:
    checkpoint_id: str
    task_id: str
    state: TaskState
    timestamp: float
    data: Dict[str, Any]
    metadata: Optional[Dict[str, Any]]
```

#### CheckpointConfig

Configuration for checkpoint management:

```python
@dataclass
class CheckpointConfig:
    auto_checkpoint: bool = True
    checkpoint_interval: float = 300.0  # seconds
    max_checkpoints: int = 10
    compress_checkpoints: bool = False
    checkpoint_dir: Optional[str] = None
```

## Usage Examples

### Basic Task Management

```python
from agno.state_manager_fsa import StateManagerFSA, TaskState

# Initialize
fsm = StateManagerFSA(storage_path="/tmp/app_states")

# Create task
task = fsm.create_task(
    task_id="data_processing",
    data={"source": "file.csv", "rows_processed": 0},
    metadata={"priority": "high"}
)

# Process task
fsm.transition_state("data_processing", TaskState.IN_PROGRESS)

# Update progress
task = fsm.get_task("data_processing")
task.data["rows_processed"] = 1000

# Complete
fsm.transition_state("data_processing", TaskState.COMPLETED)
```

### Checkpoint Management

```python
# Create checkpoints during long-running tasks
fsm.create_task("model_training", data={"epoch": 0, "loss": 1.0})
fsm.transition_state("model_training", TaskState.IN_PROGRESS)

for epoch in range(10):
    task = fsm.get_task("model_training")
    task.data["epoch"] = epoch
    task.data["loss"] = train_epoch()

    # Checkpoint after each epoch
    fsm.create_checkpoint(
        "model_training",
        checkpoint_id=f"epoch_{epoch}",
        metadata={"epoch": epoch}
    )

# Restore to specific checkpoint if needed
fsm.restore_checkpoint("model_training", "epoch_5")
```

### State Persistence and Recovery

```python
# Save state before shutdown
fsm.save_state("long_running_task")

# ... application restarts ...

# Recover in new instance
new_fsm = StateManagerFSA(storage_path="/tmp/app_states")
success = new_fsm.recover_task("long_running_task")

if success:
    task = new_fsm.get_task("long_running_task")
    print(f"Recovered task in state: {task.current_state}")
    # Continue processing...
```

### Error Handling with Retries

```python
task = fsm.create_task(
    "api_call",
    data={"endpoint": "/api/data"},
    max_retries=3
)

fsm.transition_state("api_call", TaskState.IN_PROGRESS)

try:
    # Attempt API call
    result = call_api()
except Exception as e:
    # Mark as failed
    fsm.transition_state(
        "api_call",
        TaskState.FAILED,
        error_message=str(e)
    )

    task = fsm.get_task("api_call")
    if task.retry_count < task.max_retries:
        # Retry
        fsm.transition_state("api_call", TaskState.RECOVERING)
        fsm.transition_state("api_call", TaskState.IN_PROGRESS)
        # ... retry logic ...
```

### Batch Task Management

```python
# Create multiple tasks
for i in range(100):
    fsm.create_task(f"batch_{i}", data={"item_id": i})

# Process pending tasks
pending = fsm.get_all_tasks(state_filter=TaskState.PENDING)

for task in pending:
    fsm.transition_state(task.task_id, TaskState.IN_PROGRESS)
    process_task(task)
    fsm.transition_state(task.task_id, TaskState.COMPLETED)

# Get statistics
stats = fsm.get_statistics()
print(f"Completed: {stats['state_counts']['completed']}")
```

## API Reference

### StateManagerFSA

Main class for state management.

#### Methods

##### `__init__(storage_path, checkpoint_config, version)`

Initialize the state manager.

**Parameters:**
- `storage_path` (str, optional): Directory for storing state files
- `checkpoint_config` (CheckpointConfig, optional): Checkpoint configuration
- `version` (StateVersion, optional): State version

##### `create_task(task_id, data, metadata, max_retries)`

Create a new task in PENDING state.

**Parameters:**
- `task_id` (str): Unique task identifier
- `data` (Dict[str, Any]): Task data payload
- `metadata` (Dict[str, Any], optional): Task metadata
- `max_retries` (int): Maximum retry attempts (default: 3)

**Returns:** TaskStateData

##### `get_task(task_id)`

Get task state by ID.

**Parameters:**
- `task_id` (str): Task identifier

**Returns:** TaskStateData or None

##### `transition_state(task_id, new_state, error_message)`

Transition task to a new state.

**Parameters:**
- `task_id` (str): Task identifier
- `new_state` (TaskState): Target state
- `error_message` (str, optional): Error message for FAILED state

**Returns:** bool

##### `create_checkpoint(task_id, checkpoint_id, metadata)`

Create a checkpoint for current task state.

**Parameters:**
- `task_id` (str): Task identifier
- `checkpoint_id` (str, optional): Checkpoint ID (auto-generated if not provided)
- `metadata` (Dict[str, Any], optional): Checkpoint metadata

**Returns:** Checkpoint

##### `restore_checkpoint(task_id, checkpoint_id)`

Restore task state from a checkpoint.

**Parameters:**
- `task_id` (str): Task identifier
- `checkpoint_id` (str, optional): Checkpoint ID (uses latest if not provided)

**Returns:** bool

##### `save_state(task_id)`

Save task state to disk.

**Parameters:**
- `task_id` (str): Task identifier

**Returns:** str (file path)

##### `load_state(task_id, auto_migrate)`

Load task state from disk.

**Parameters:**
- `task_id` (str): Task identifier
- `auto_migrate` (bool): Auto-migrate if version mismatch (default: True)

**Returns:** TaskStateData or None

##### `recover_task(task_id)`

Recover a task from saved state.

**Parameters:**
- `task_id` (str): Task identifier

**Returns:** bool

##### `get_all_tasks(state_filter)`

Get all tasks, optionally filtered by state.

**Parameters:**
- `state_filter` (TaskState, optional): Filter by state

**Returns:** List[TaskStateData]

##### `delete_task(task_id, delete_from_disk)`

Delete a task.

**Parameters:**
- `task_id` (str): Task identifier
- `delete_from_disk` (bool): Delete state file (default: True)

**Returns:** bool

##### `get_statistics()`

Get statistics about the state manager.

**Returns:** Dict[str, Any]

## State File Format

Task state is persisted in JSON format:

```json
{
  "version": {
    "major": 1,
    "minor": 0,
    "patch": 0
  },
  "task": {
    "task_id": "task_1",
    "current_state": "in_progress",
    "data": {"key": "value"},
    "previous_state": "pending",
    "created_at": 1234567890.123,
    "updated_at": 1234567891.456,
    "checkpoints": [...],
    "metadata": {},
    "retry_count": 0,
    "max_retries": 3,
    "error_message": null
  },
  "saved_at": 1234567891.456
}
```

## Best Practices

1. **Regular Checkpointing**: Enable auto-checkpointing for long-running tasks
2. **Error Messages**: Always provide descriptive error messages when transitioning to FAILED
3. **Retry Logic**: Set appropriate max_retries based on task criticality
4. **State Persistence**: Call save_state() before application shutdown
5. **Recovery Testing**: Test recovery scenarios in your application
6. **Metadata Usage**: Use metadata for filtering and organization
7. **Cleanup**: Delete completed tasks to manage disk space

## Testing

Comprehensive tests are available in `tests/unit/test_state_manager_fsa.py`:

```bash
pytest libs/agno/tests/unit/test_state_manager_fsa.py -v
```

Test coverage includes:
- Task creation and state transitions
- State save/load functionality
- Checkpoint management
- Recovery mechanisms
- Version migration
- Data structure conversions

## Examples

See `libs/agno/agno/state_manager_fsa_example.py` for complete working examples.

## Contributing

Contributions are welcome! Please ensure:
- All tests pass
- New features include tests
- Code follows existing patterns
- Documentation is updated

## License

This module is part of the Agno framework and follows the same license.

## Support

For issues and questions:
- GitHub Issues: https://github.com/agno-ai/agno
- Documentation: https://docs.agno.com

## Version History

### 1.0.0 (Initial Release)
- Task state management with FSA rules
- State persistence and recovery
- Checkpoint management
- Version migration support
- Comprehensive test coverage
