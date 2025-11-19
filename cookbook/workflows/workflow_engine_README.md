# Workflow Engine FSA - Production-Ready Workflow Orchestration

A production-ready workflow orchestration system built on Finite State Automaton (FSA) principles, providing robust step execution, state management, conditional branching, parallel execution, error handling, and progress tracking.

## Features

- **FSA-Based State Management**: Clean, predictable state transitions following FSA-3.1 specification
- **Conditional Branching**: Dynamic workflow paths based on runtime conditions
- **Parallel Execution**: Execute multiple tasks concurrently with configurable parallelism
- **Comprehensive Error Handling**: Automatic retries, timeouts, and error recovery
- **Progress Tracking**: Real-time workflow execution monitoring with detailed events
- **Type Safety**: Full type hints and Pydantic models for validation
- **Production Ready**: Tested, documented, and integrated with Agno's workflow infrastructure

## Architecture

### Core Components

1. **State**: Represents a workflow state with handlers, transitions, and execution tracking
2. **StateTransition**: Defines allowed transitions between states with optional conditions
3. **StateGraph**: Manages the complete state machine topology
4. **ExecutionContext**: Tracks runtime variables, history, and statistics
5. **WorkflowEngine**: Main orchestrator that executes the state machine

### State Lifecycle

```
PENDING → RUNNING → COMPLETED/FAILED
                  ↓
              (retry if configured)
```

## Quick Start

### Basic Linear Workflow

```python
from agno.workflow.engine import WorkflowEngine, State

# Create engine
engine = WorkflowEngine(name="simple_workflow")

# Define states
start = State(name="start", is_initial=True)
process = State(name="process")
end = State(name="end", is_final=True)

# Define transitions
start.add_transition("process")
process.add_transition("end")

# Add handlers
def start_handler(ctx):
    ctx.set("data", "initialized")
    print("Workflow started")

def process_handler(ctx):
    data = ctx.get("data")
    ctx.set("result", f"Processed: {data}")
    print("Processing data")

engine.add_state(start, handler=start_handler)
engine.add_state(process, handler=process_handler)
engine.add_state(end)

# Execute
for response in engine.run(input_param="value"):
    print(response.content)
```

### Conditional Branching

```python
from agno.workflow.engine import State, TransitionCondition

# Create state with conditional transitions
check = State(name="check", is_initial=True)
path_a = State(name="path_a")
path_b = State(name="path_b")
end = State(name="end", is_final=True)

# Define conditions
high_value = TransitionCondition(
    condition="amount > 1000",
    target_state="path_a",
    description="High value orders"
)

# Add conditional transition
check.add_transition("path_a", conditions=[high_value])
check.add_transition("path_b")  # Default path

path_a.add_transition("end")
path_b.add_transition("end")
```

### Error Handling with Retries

```python
# State with automatic retries
risky_state = State(
    name="api_call",
    retry_count=3,  # Retry up to 3 times
    timeout_seconds=30,  # 30 second timeout
)

def api_handler(ctx):
    # Your code that might fail
    response = call_external_api()
    ctx.set("api_result", response)
    return response

engine.add_state(risky_state, handler=api_handler)
```

### Parallel Execution

```python
# Execute tasks in parallel
def parallel_processing_handler(ctx):
    engine = ctx.get("_engine")  # Access to engine instance

    tasks = [task1, task2, task3]
    results = engine.execute_parallel(tasks, ctx)

    ctx.set("parallel_results", results)
    return results
```

### State Callbacks

```python
def on_enter_callback(ctx):
    print(f"Entering state at {datetime.now()}")
    ctx.set("entered_at", datetime.now())

def on_exit_callback(ctx):
    print(f"Exiting state at {datetime.now()}")
    ctx.set("exited_at", datetime.now())

state = State(name="monitored_state")
engine.add_state(
    state,
    handler=main_handler,
    on_enter=on_enter_callback,
    on_exit=on_exit_callback
)
```

## Configuration

```python
from agno.workflow.engine import WorkflowEngineConfig

config = WorkflowEngineConfig(
    name="my_engine",
    max_parallel_tasks=5,  # Max concurrent tasks
    default_timeout_seconds=300,  # Default state timeout
    enable_progress_tracking=True,  # Emit progress events
    retry_delay_seconds=2.0,  # Delay between retries
    max_execution_time_seconds=3600,  # Total workflow timeout
)

engine = WorkflowEngine(name="my_workflow", config=config)
```

## Condition Expressions

Transition conditions support Python expressions with safe evaluation:

```python
# Numeric comparisons
TransitionCondition(condition="value > 100", target_state="high")
TransitionCondition(condition="value >= 50 and value < 100", target_state="medium")

# String comparisons
TransitionCondition(condition="status == 'approved'", target_state="next")

# Boolean logic
TransitionCondition(condition="is_valid and not is_processed", target_state="process")

# Membership tests
TransitionCondition(condition="'error' in tags", target_state="error_handler")

# Complex expressions
TransitionCondition(
    condition="amount > 1000 and user_level == 'premium' and in_stock == True",
    target_state="express_shipping"
)
```

## Execution Context

The execution context provides runtime state management:

```python
# Set/get variables
ctx.set("key", "value")
value = ctx.get("key", default="default_value")

# Check existence
if ctx.has("key"):
    # ...

# Update multiple
ctx.update({"key1": "value1", "key2": "value2"})

# Access execution history
path = ctx.get_execution_path()  # ['state1', 'state2', 'state3']
stats = ctx.get_state_statistics()  # Detailed performance metrics

# Check state visits
if ctx.has_visited_state("validation"):
    # ...
```

## Progress Tracking

When `enable_progress_tracking=True`, the engine emits detailed events:

```python
for response in engine.run(param="value"):
    if response.event == "run_started":
        print("Workflow started")

    elif response.content.get("status") == "state_started":
        print(f"State {response.content['state']} started")

    elif response.content.get("status") == "state_completed":
        print(f"State completed: {response.content['result']}")

    elif response.content.get("status") == "transition":
        print(f"Transitioning: {response.content['from_state']} → {response.content['to_state']}")

    elif response.event == "run_completed":
        print(f"Workflow completed in {response.content['duration_ms']}ms")
```

## Real-World Examples

### 1. Order Processing Workflow

See: `workflow_engine_order_processing.py`

Features demonstrated:
- Conditional branching (standard vs premium orders)
- Inventory checks with error handling
- Customer notifications
- Backorder management

```bash
python cookbook/workflows/workflow_engine_order_processing.py
```

### 2. Multi-Level Approval Pipeline

See: `workflow_engine_approval_pipeline.py`

Features demonstrated:
- Multi-level approval chains
- Amount-based routing
- Parallel compliance reviews
- Rejection handling with reasons

```bash
python cookbook/workflows/workflow_engine_approval_pipeline.py
```

## Testing

Comprehensive test suite with 20+ test cases covering:

- State creation and validation
- Transition conditions
- State graph validation
- Execution context management
- Workflow execution (linear and branching)
- Error handling and retries
- Parallel execution
- Progress tracking
- Callbacks

Run tests:

```bash
pytest libs/agno/tests/unit/workflow/test_fsm_engine.py -v
```

## Performance Metrics

The engine automatically tracks:

- **Per-State Metrics**:
  - Total executions
  - Success/failure counts
  - Average duration
  - Total duration

- **Workflow Metrics**:
  - Total duration
  - Execution path
  - State transition count

Access metrics from execution context:

```python
ctx = engine.get_execution_context()
stats = ctx.get_state_statistics()

for state_name, metrics in stats.items():
    print(f"{state_name}:")
    print(f"  Executions: {metrics['total_executions']}")
    print(f"  Success Rate: {metrics['successful'] / metrics['total_executions'] * 100}%")
    print(f"  Avg Duration: {metrics['avg_duration_ms']}ms")
```

## Best Practices

### 1. State Design

- Keep states focused on single responsibilities
- Use descriptive state names
- Mark initial and final states explicitly
- Set appropriate timeouts based on expected duration

### 2. Error Handling

- Configure retries for transient failures
- Use timeouts to prevent hanging
- Provide meaningful error messages
- Log errors with context

### 3. Condition Design

- Keep conditions simple and readable
- Test edge cases
- Provide default transitions for fallback paths
- Document complex conditions

### 4. Context Management

- Use consistent variable naming
- Clean up unnecessary variables
- Avoid storing large objects
- Use metadata for auxiliary information

### 5. Testing

- Test both happy paths and error scenarios
- Verify all conditional branches
- Test timeout and retry behavior
- Mock external dependencies

## Integration with Agno Workflows

The Workflow Engine extends `agno.workflow.Workflow`, providing seamless integration:

```python
from agno.workflow.engine import WorkflowEngine
from agno.storage import SqliteStorage

# Use Agno's storage and session management
engine = WorkflowEngine(
    name="my_workflow",
    storage=SqliteStorage(db_path="workflows.db"),
    session_id="session-123",
)

# Access workflow features
engine.load_session()
engine.write_to_storage()
```

## API Reference

### WorkflowEngine

**Methods:**
- `add_state(state, handler, on_enter, on_exit)`: Add state to workflow
- `validate()`: Validate workflow configuration
- `run(**kwargs)`: Execute workflow
- `execute_parallel(tasks, context)`: Run tasks in parallel
- `get_execution_context()`: Get current context
- `reset()`: Reset all states

### State

**Attributes:**
- `name`: Unique state identifier
- `is_initial`: Mark as initial state
- `is_final`: Mark as final state
- `retry_count`: Number of retries on failure
- `timeout_seconds`: Execution timeout
- `handler`: Execution function
- `on_enter`: Entry callback
- `on_exit`: Exit callback

**Methods:**
- `add_transition(to_state, conditions)`: Add transition
- `get_next_state(context)`: Determine next state
- `reset()`: Reset execution tracking

### ExecutionContext

**Methods:**
- `set(key, value)`: Set variable
- `get(key, default)`: Get variable
- `has(key)`: Check variable existence
- `update(dict)`: Update multiple variables
- `get_execution_path()`: Get state execution order
- `get_state_statistics()`: Get performance metrics
- `has_visited_state(name)`: Check if state was executed

## FSA-3.1 Specification Compliance

This implementation follows FSA-3.1 principles:

1. **Deterministic Transitions**: Each state transition is well-defined
2. **State Isolation**: States are independent and composable
3. **Input Processing**: Context-based condition evaluation
4. **Accept States**: Explicit final state marking
5. **Error States**: Proper error handling and recovery
6. **Observability**: Complete execution tracking and metrics

## Line Count Summary

- **Implementation**: ~600 lines
  - `state.py`: ~230 lines
  - `context.py`: ~180 lines
  - `fsm_engine.py`: ~190 lines

- **Tests**: ~400 lines
  - `test_fsm_engine.py`: ~400 lines

- **Examples**: ~250 lines
  - Order processing: ~130 lines
  - Approval pipeline: ~120 lines

- **Documentation**: ~150 lines

**Total**: ~1400 lines (with documentation)

## License

Part of the Agno framework. See main repository license.

## Contributing

Contributions welcome! Please:
1. Add tests for new features
2. Update documentation
3. Follow existing code style
4. Ensure all tests pass

## Support

For issues or questions:
- GitHub Issues: https://github.com/agno-framework/agno/issues
- Documentation: https://docs.agno.com
