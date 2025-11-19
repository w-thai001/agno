# FSA-3.1 Specification

## Overview

The FSA-3.1 (Finite State Automaton v3.1) specification defines a simple, fast, and functional workflow engine for agno. It provides core execution logic with step runner, state tracker, and error handler.

## Design Principles

1. **Simplicity**: Core execution logic in ~600 lines
2. **Performance**: Fast state transitions and minimal overhead
3. **Determinism**: Predictable state transitions based on conditions
4. **Composability**: States and transitions are composable building blocks
5. **Error Resilience**: Built-in error handling and recovery strategies

## Core Components

### 1. State

A **State** represents a node in the workflow FSA.

**Properties:**
- `name` (str): Unique identifier
- `state_type` (StateType): Classification (START, INTERMEDIATE, END, ERROR, RECOVERY)
- `action` (Callable): Function to execute when entering the state
- `timeout` (float, optional): Maximum execution time in seconds
- `metadata` (dict): Custom configuration

**State Types:**
- `START`: Initial state(s) of the workflow
- `INTERMEDIATE`: Processing states in the workflow
- `END`: Terminal states indicating successful completion
- `ERROR`: Terminal states indicating failure
- `RECOVERY`: States for error recovery logic

### 2. Transition

A **Transition** defines an edge between states.

**Properties:**
- `from_state` (str): Source state name
- `to_state` (str): Target state name
- `condition` (TransitionCondition): When the transition fires
- `guard` (Callable, optional): Custom logic to evaluate transition
- `priority` (int): Higher priority transitions evaluated first
- `metadata` (dict): Custom configuration

**Standard Conditions:**
- `SUCCESS`: Transition on successful state execution
- `FAILURE`: Transition on error or exception
- `TIMEOUT`: Transition on timeout
- `CONDITION_MET`: Transition when result is truthy
- `ALWAYS`: Always transition (catch-all)
- `CUSTOM`: Use guard function for evaluation

### 3. StateContext

The **StateContext** carries data between states during execution.

**Properties:**
- `data` (dict): Workflow data and results
- `metadata` (dict): Execution metadata
- `errors` (list): Error history
- `history` (list): State visit history

### 4. StateTracker

The **StateTracker** manages current state and execution progress.

**Responsibilities:**
- Track current state
- Record state transition history
- Count state visits
- Measure execution time
- Provide state snapshots for persistence

### 5. StepRunner

The **StepRunner** executes individual state steps.

**Responsibilities:**
- Execute state actions
- Evaluate transition conditions
- Find next state based on transitions
- Record execution metrics

### 6. ErrorHandler

The **ErrorHandler** manages errors and recovery.

**Strategies:**
- **Retry**: Retry failed state up to N times
- **Recover**: Transition to recovery state
- **Fail**: Stop execution and raise error

**Configuration:**
- `max_retries` (int): Maximum retry attempts per state
- `retry_states` (list): States that support retry
- `recovery_state` (str): Name of recovery state

### 7. FSAEngine

The **FSAEngine** orchestrates workflow execution.

**Key Methods:**
- `add_state(state)`: Add state to FSA
- `add_transition(transition)`: Add transition to FSA
- `run(initial_context)`: Execute workflow synchronously
- `run_async(initial_context)`: Execute workflow with step-by-step yielding

## Execution Model

### Synchronous Execution

```python
engine = FSAEngine(states={...}, transitions=[...])
context = engine.run()
```

1. Start from initial state
2. Execute state action
3. Evaluate transitions
4. Move to next state
5. Repeat until END/ERROR state or no valid transition

### Asynchronous Execution

```python
for state_name, context in engine.run_async():
    print(f"Currently in state: {state_name}")
    # Process intermediate results
```

Yields `(state_name, context)` after each state execution.

## Error Handling

### Error Flow

1. **Exception Raised**: State action raises exception
2. **Error Recorded**: Added to context.errors
3. **Handler Invoked**: ErrorHandler.handle_error() called
4. **Strategy Applied**:
   - Retry: Return same state name
   - Recover: Return recovery state name
   - Fail: Return None (stops execution)

### Retry Logic

```python
error_handler = ErrorHandler(
    max_retries=3,
    retry_states=["fetch_data", "process_data"]
)
```

- States in `retry_states` are retried up to `max_retries` times
- Retry count resets on successful execution
- After max retries, falls back to recovery or fail

### Recovery States

```python
error_handler = ErrorHandler(recovery_state="handle_error")

engine.add_state(State(
    name="handle_error",
    state_type=StateType.RECOVERY,
    action=lambda ctx: log_and_cleanup(ctx)
))
```

- Recovery states handle errors gracefully
- Can inspect `context.errors` for error details
- Can transition to END state or retry failed states

## State Persistence

### State Snapshot

```python
tracker = StateTracker(initial_state)
snapshot = tracker.get_snapshot()
# Returns:
# {
#     "current_state": "processing",
#     "total_transitions": 5,
#     "state_visit_count": {...},
#     "duration_ms": 1234.56,
#     ...
# }
```

### Context Serialization

```python
# StateContext is serializable
import json
context_dict = {
    "data": context.data,
    "metadata": context.metadata,
    "errors": context.errors,
    "history": context.history
}
json.dumps(context_dict)
```

## Best Practices

### 1. State Design

- **Single Responsibility**: Each state should do one thing well
- **Idempotency**: States should be safe to retry
- **Timeouts**: Set timeouts for potentially long-running states

### 2. Transition Design

- **Explicit**: Prefer explicit conditions over ALWAYS
- **Priority**: Use priority to resolve ambiguous transitions
- **Guards**: Use guard functions for complex logic

### 3. Error Handling

- **Retry Wisely**: Only retry idempotent operations
- **Log Errors**: Always log errors for debugging
- **Graceful Degradation**: Use recovery states for graceful failure

### 4. Context Management

- **Minimal Data**: Only store necessary data in context
- **Type Safety**: Validate data types in state actions
- **Error Context**: Preserve error information for debugging

## Example Workflow

```python
from agno.workflow.fsa import (
    FSAEngine, State, Transition, StateContext,
    StateType, TransitionCondition, ErrorHandler
)

# Define states
start = State(
    name="start",
    state_type=StateType.START,
    action=lambda ctx: ctx.data.update({"initialized": True})
)

process = State(
    name="process",
    state_type=StateType.INTERMEDIATE,
    action=lambda ctx: ctx.data.update({"result": "processed"})
)

end = State(
    name="end",
    state_type=StateType.END,
    action=lambda ctx: print(f"Done: {ctx.data}")
)

# Define transitions
transitions = [
    Transition("start", "process", TransitionCondition.SUCCESS),
    Transition("process", "end", TransitionCondition.SUCCESS)
]

# Create and run engine
engine = FSAEngine(
    states={"start": start, "process": process, "end": end},
    transitions=transitions,
    initial_state="start"
)

context = engine.run()
```

## Performance Characteristics

- **Transition Overhead**: O(T) where T is number of transitions from current state
- **State Execution**: O(1) lookup, execution time depends on action
- **Memory**: O(S + H) where S is number of states, H is history length
- **Max Steps**: Configurable limit (default: 1000) prevents infinite loops

## Version History

- **FSA-3.1** (2025): Initial specification
  - Core execution logic
  - Step runner, state tracker, error handler
  - Synchronous and asynchronous execution
  - Retry and recovery strategies
