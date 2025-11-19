# Workflow Orchestrator FSA

A comprehensive workflow orchestration engine with Finite State Automaton (FSA) based task execution for the Agno framework.

## Features

- **DAG Execution**: Directed Acyclic Graph-based task dependency management
- **Parallel Task Support**: Execute independent tasks concurrently with configurable parallelism
- **Dependency Resolution**: Automatic resolution of task dependencies with topological sorting
- **Error Recovery**: Retry mechanisms with configurable backoff and failure callbacks
- **State Persistence**: Save and restore workflow state for recovery from failures
- **Execution Monitoring**: Real-time metrics and progress tracking
- **Task Cancellation**: Cancel workflows and pause/resume execution
- **Flexible Task Definition**: Support for both synchronous and asynchronous task functions

## Architecture

### Core Components

1. **Task**: Individual unit of work with dependencies and execution logic
2. **TaskState**: FSA states for task execution lifecycle
3. **WorkflowOrchestrator**: Main orchestration engine
4. **DAG**: Directed Acyclic Graph for dependency management
5. **StateManager**: Handles workflow state persistence
6. **ExecutionMetrics**: Tracks execution statistics and progress

### Task States (FSA)

```
PENDING → WAITING → READY → RUNNING → COMPLETED
                              ↓
                          RETRYING → FAILED → SKIPPED
                              ↑         ↓
                              └─────────┘
```

- **PENDING**: Initial state when task is created
- **WAITING**: Task is waiting for dependencies to complete
- **READY**: All dependencies satisfied, ready to execute
- **RUNNING**: Task is currently executing
- **COMPLETED**: Task completed successfully
- **FAILED**: Task failed after all retries
- **RETRYING**: Task failed and is being retried
- **SKIPPED**: Task skipped due to failed dependency
- **CANCELLED**: Task cancelled by user

## Installation

The orchestrator is part of the agno workflow module:

```python
from agno.workflow import (
    WorkflowOrchestrator,
    Task,
    TaskState,
    WorkflowState,
)
```

## Quick Start

### Simple Linear Workflow

```python
from agno.workflow import WorkflowOrchestrator, Task

def extract_data(context):
    # Extract data from source
    return {"data": [...]}

def transform_data(context):
    # Transform the data
    return {"transformed": [...]}

def load_data(context):
    # Load to destination
    return "Success"

# Create orchestrator
orchestrator = WorkflowOrchestrator(workflow_id="etl_pipeline")

# Define tasks with dependencies
orchestrator.add_task(
    Task(task_id="extract", name="Extract Data", func=extract_data)
)
orchestrator.add_task(
    Task(
        task_id="transform",
        name="Transform Data",
        func=transform_data,
        dependencies=["extract"]
    )
)
orchestrator.add_task(
    Task(
        task_id="load",
        name="Load Data",
        func=load_data,
        dependencies=["transform"]
    )
)

# Execute workflow
results = orchestrator.execute()
```

### Parallel Task Execution

```python
orchestrator = WorkflowOrchestrator(
    workflow_id="parallel_workflow",
    max_parallel_tasks=4  # Run up to 4 tasks in parallel
)

# Create fan-out pattern
orchestrator.add_task(Task(task_id="split", func=split_data))
orchestrator.add_task(Task(task_id="p1", func=process_1, dependencies=["split"]))
orchestrator.add_task(Task(task_id="p2", func=process_2, dependencies=["split"]))
orchestrator.add_task(Task(task_id="p3", func=process_3, dependencies=["split"]))
orchestrator.add_task(Task(task_id="merge", func=merge_data, dependencies=["p1", "p2", "p3"]))

results = orchestrator.execute()
# p1, p2, p3 will run in parallel after split completes
```

## Advanced Features

### Error Handling and Retry

```python
def flaky_task(context):
    # Task that might fail
    if random.random() < 0.5:
        raise Exception("Random failure")
    return "Success"

def on_task_failure(task, error):
    logger.error(f"Task {task.name} failed: {error}")
    # Send alert, etc.

orchestrator.add_task(
    Task(
        task_id="flaky",
        name="Flaky Task",
        func=flaky_task,
        retry_count=3,           # Retry up to 3 times
        retry_delay=2.0,         # Wait 2 seconds between retries
        timeout=30.0,            # Task timeout in seconds
        on_failure=on_task_failure
    )
)
```

### State Persistence and Recovery

```python
from pathlib import Path

# Enable auto-persistence
orchestrator = WorkflowOrchestrator(
    workflow_id="persistent_workflow",
    auto_persist=True,
    state_dir=Path(".workflow_state")
)

# First execution (may fail)
try:
    orchestrator.execute()
except Exception as e:
    print(f"Workflow failed: {e}")

# Resume from saved state
orchestrator2 = WorkflowOrchestrator(
    workflow_id="persistent_workflow",
    auto_persist=True,
    state_dir=Path(".workflow_state")
)

# Re-register tasks (functions can't be persisted)
orchestrator2.add_tasks([...])

# Resume execution
results = orchestrator2.execute(resume=True)
# Only incomplete tasks will be executed
```

### Real-time Monitoring

```python
import asyncio

async def execute_with_monitoring():
    orchestrator = WorkflowOrchestrator(workflow_id="monitored")
    orchestrator.add_tasks([...])

    # Start execution in background
    execution_task = asyncio.create_task(orchestrator.execute_async())

    # Monitor progress
    while orchestrator.workflow_state.value == "running":
        await asyncio.sleep(1)
        metrics = orchestrator.get_metrics()

        print(f"Progress: {metrics.get_progress_percentage():.0f}%")
        print(f"Completed: {metrics.completed_tasks}/{metrics.total_tasks}")
        print(f"Running: {metrics.running_tasks}")

    await execution_task

asyncio.run(execute_with_monitoring())
```

### Complex DAG Workflows

```python
# Build a complex deployment pipeline
orchestrator = WorkflowOrchestrator(
    workflow_id="deployment",
    max_parallel_tasks=3
)

tasks = [
    # Initialize
    Task(task_id="init", func=init_deployment),

    # Parallel infrastructure setup
    Task(task_id="db", func=setup_database, dependencies=["init"]),
    Task(task_id="cache", func=setup_cache, dependencies=["init"]),
    Task(task_id="queue", func=setup_queue, dependencies=["init"]),

    # Migrations
    Task(task_id="migrate", func=run_migrations, dependencies=["db"]),

    # Parallel service deployment
    Task(task_id="api", func=deploy_api, dependencies=["migrate", "cache"]),
    Task(task_id="workers", func=deploy_workers, dependencies=["migrate", "queue"]),

    # Testing and validation
    Task(task_id="tests", func=run_tests, dependencies=["api", "workers"]),
    Task(task_id="healthcheck", func=health_check, dependencies=["api", "workers"]),

    # Finalization
    Task(task_id="notify", func=send_notifications, dependencies=["tests", "healthcheck"]),
]

orchestrator.add_tasks(tasks)
results = orchestrator.execute()
```

## API Reference

### WorkflowOrchestrator

```python
WorkflowOrchestrator(
    workflow_id: Optional[str] = None,
    max_parallel_tasks: int = 4,
    state_dir: Optional[Path] = None,
    auto_persist: bool = True
)
```

**Methods:**

- `add_task(task: Task)`: Add a task to the workflow
- `add_tasks(tasks: List[Task])`: Add multiple tasks
- `execute(context: Dict = None, resume: bool = False)`: Execute workflow synchronously
- `execute_async(context: Dict = None, resume: bool = False)`: Execute workflow asynchronously
- `get_metrics()`: Get current execution metrics
- `get_status()`: Get comprehensive workflow status
- `pause()`: Pause workflow execution
- `cancel()`: Cancel workflow execution
- `reset()`: Reset workflow to initial state
- `persist_state()`: Manually persist state to disk

### Task

```python
Task(
    task_id: str,
    name: str,
    func: Callable,
    dependencies: List[str] = [],
    retry_count: int = 0,
    retry_delay: float = 1.0,
    timeout: Optional[float] = None,
    on_failure: Optional[Callable] = None,
    on_success: Optional[Callable] = None,
    metadata: Dict[str, Any] = {}
)
```

**Attributes:**

- `task_id`: Unique identifier for the task
- `name`: Human-readable task name
- `func`: Callable to execute (sync or async)
- `dependencies`: List of task_ids this task depends on
- `retry_count`: Number of retries on failure
- `retry_delay`: Delay between retries in seconds
- `timeout`: Maximum execution time in seconds
- `on_failure`: Callback when task fails
- `on_success`: Callback when task succeeds
- `metadata`: Additional task metadata

### TaskResult

```python
@dataclass
class TaskResult:
    task_id: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    retry_count: int = 0
```

### ExecutionMetrics

```python
@dataclass
class ExecutionMetrics:
    workflow_id: str
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    skipped_tasks: int
    running_tasks: int
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    duration: Optional[float]

    def get_progress_percentage() -> float
    def to_dict() -> Dict[str, Any]
```

## Examples

The `examples/` directory contains comprehensive examples:

1. **Simple Linear Workflow**: Basic sequential task execution
2. **Parallel Execution**: Fan-out/fan-in pattern
3. **Error Handling**: Retry mechanisms and failure callbacks
4. **Complex DAG**: Multi-level dependency graphs
5. **State Persistence**: Recovery from failures
6. **Monitoring**: Real-time progress tracking
7. **Data Pipeline**: Real-world ETL pipeline

Run examples:

```bash
# Run all examples
python -m agno.workflow.examples.orchestrator_examples

# Run specific example
python -m agno.workflow.examples.orchestrator_examples 3  # Error handling example
```

## Best Practices

### 1. Task Design

- Keep tasks focused and single-purpose
- Make tasks idempotent when possible
- Use context for sharing data between tasks
- Avoid side effects in task functions

### 2. Dependency Management

- Declare all dependencies explicitly
- Avoid circular dependencies
- Use the DAG validator before execution
- Group related tasks logically

### 3. Error Handling

- Set appropriate retry counts for transient failures
- Use on_failure callbacks for alerting
- Consider task timeouts for long-running operations
- Handle partial failures gracefully

### 4. Performance

- Tune max_parallel_tasks based on system resources
- Profile task execution times
- Use async tasks for I/O-bound operations
- Monitor memory usage for large workflows

### 5. State Management

- Enable auto_persist for long-running workflows
- Version your workflow definitions
- Test recovery scenarios
- Clean up old state files periodically

## Technical Details

### DAG Validation

The orchestrator uses Kahn's algorithm for topological sorting and DFS for cycle detection:

```python
# Validate DAG structure
is_valid, error = orchestrator.dag.validate()
if not is_valid:
    raise ValueError(f"Invalid DAG: {error}")

# Get execution order
execution_order = orchestrator.dag.topological_sort()
```

### Task Execution

Tasks are executed using asyncio for efficient parallelism:

1. Identify ready tasks (all dependencies satisfied)
2. Acquire semaphore for concurrency control
3. Execute task with timeout if specified
4. Update task state based on result
5. Trigger dependent tasks
6. Persist state if auto_persist is enabled

### State Persistence

State is persisted as JSON:

```json
{
  "workflow_id": "my_workflow",
  "workflow_state": "running",
  "completed_tasks": ["task1", "task2"],
  "failed_tasks": [],
  "tasks": {
    "task1": {
      "task_id": "task1",
      "state": "completed",
      "result": {...}
    }
  },
  "metrics": {...}
}
```

## Limitations

- Task functions cannot be persisted (must be re-registered on resume)
- Maximum recommended tasks per workflow: 1000
- State files grow with workflow size
- Async tasks require asyncio-compatible functions

## Troubleshooting

### Common Issues

**1. Circular Dependencies**
```python
# This will fail validation
orchestrator.add_task(Task("a", func=f1, dependencies=["b"]))
orchestrator.add_task(Task("b", func=f2, dependencies=["a"]))
# Error: DAG contains cycles
```

**2. Missing Dependencies**
```python
# Task depends on non-existent task
orchestrator.add_task(Task("a", func=f1, dependencies=["nonexistent"]))
# Error: Task a depends on non-existent task nonexistent
```

**3. Task Timeouts**
```python
# Set appropriate timeouts
Task("slow", func=slow_func, timeout=300)  # 5 minutes
```

## Contributing

Contributions are welcome! Please ensure:

- All tests pass
- Code follows the existing style
- Documentation is updated
- Examples are provided for new features

## License

This is part of the Agno framework and follows the same license (MPL 2.0).

## Support

For issues and questions:
- GitHub Issues: https://github.com/agnohq/agno/issues
- Documentation: https://docs.agno.com
- Examples: See `examples/orchestrator_examples.py`
