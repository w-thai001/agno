# Error Recovery FSA

A production-ready Finite State Automaton (FSA) for handling failure modes and implementing error recovery strategies in distributed systems.

## Features

- **Error Detection & Classification**: Automatically detects and classifies errors into categories (API, Timeout, Validation, Resource)
- **Retry Strategies**: Implements exponential backoff with configurable retry limits
- **Graceful Degradation**: Supports fallback actions when primary recovery fails
- **State Management**: Full FSA with state transitions tracking
- **Incident Logging**: Comprehensive error logging with customizable handlers
- **Statistics**: Track error patterns and recovery metrics

## Installation

```python
from src.fsas.error_recovery_fsa import ErrorRecoveryFSA, RecoveryStrategy
```

## Quick Start

### Basic Error Handling

```python
from src.fsas.error_recovery_fsa import ErrorRecoveryFSA

# Create FSA instance
fsa = ErrorRecoveryFSA()

# Handle an error
try:
    risky_operation()
except Exception as e:
    result = fsa.handle_error(
        e,
        recovery_action=risky_operation,
        context={"operation": "api_call"}
    )

    if result['recovered']:
        print("Operation recovered successfully!")
```

### Custom Recovery Strategy

```python
from src.fsas.error_recovery_fsa import ErrorRecoveryFSA, RecoveryStrategy

# Configure custom strategy
strategy = RecoveryStrategy(
    max_retries=5,
    base_delay=1.0,
    max_delay=60.0,
    exponential_base=2.0,
    enable_degraded_mode=True
)

fsa = ErrorRecoveryFSA(strategy=strategy)
```

### Graceful Degradation

```python
def fallback_from_cache():
    return {"cached": True, "data": get_cached_data()}

strategy = RecoveryStrategy(
    max_retries=3,
    enable_degraded_mode=True,
    fallback_action=fallback_from_cache
)

fsa = ErrorRecoveryFSA(strategy=strategy)

result = fsa.handle_error(error, recovery_action=api_call)
if result.get('degraded_mode'):
    print("Using cached data")
```

### Custom Logging

```python
def custom_logger(incident):
    # Send to monitoring system
    monitoring.log_error(
        error_type=incident['error_type'],
        timestamp=incident['timestamp'],
        metadata=incident['metadata']
    )

fsa = ErrorRecoveryFSA(log_handler=custom_logger)
```

## Core Functions

### `detect_error(error, metadata=None)`
Detects and creates context for an error occurrence.

**Parameters:**
- `error`: Exception object
- `metadata`: Optional dict with additional context

**Returns:** `ErrorContext` object

### `classify_failure(context)`
Classifies error into one of the predefined types.

**Parameters:**
- `context`: ErrorContext object

**Returns:** `ErrorType` enum value

### `execute_recovery(context, recovery_action, *args, **kwargs)`
Executes recovery strategy with exponential backoff retries.

**Parameters:**
- `context`: ErrorContext object
- `recovery_action`: Callable to retry
- `*args`, `**kwargs`: Arguments for recovery_action

**Returns:** Dict with recovery result

### `log_incident(context, additional_info=None)`
Logs error incident with full context.

**Parameters:**
- `context`: ErrorContext object
- `additional_info`: Optional additional information

## Error Types

- `API`: API-related errors (HTTP, connection, etc.)
- `TIMEOUT`: Timeout and deadline exceeded errors
- `VALIDATION`: Data validation and schema errors
- `RESOURCE`: Resource exhaustion (memory, disk, etc.)
- `UNKNOWN`: Unclassified errors

## FSA States

- `IDLE`: Initial state
- `ERROR_DETECTED`: Error has been detected
- `ERROR_CLASSIFIED`: Error has been classified
- `RECOVERY_IN_PROGRESS`: Recovery action is being executed
- `RECOVERY_SUCCESS`: Recovery succeeded
- `RECOVERY_FAILED`: All recovery attempts failed
- `DEGRADED_MODE`: Operating in degraded mode with fallback

## Configuration

### RecoveryStrategy Parameters

- `max_retries` (int): Maximum number of retry attempts (default: 3)
- `base_delay` (float): Base delay in seconds (default: 1.0)
- `max_delay` (float): Maximum delay in seconds (default: 60.0)
- `exponential_base` (float): Base for exponential backoff (default: 2.0)
- `enable_degraded_mode` (bool): Enable fallback mode (default: True)
- `fallback_action` (Callable): Fallback function for degraded mode

## Statistics

Get comprehensive error statistics:

```python
stats = fsa.get_error_statistics()

print(f"Total errors: {stats['total_errors']}")
print(f"By type: {stats['by_type']}")
print(f"Average retries: {stats['average_retries']}")
```

## Demo

Run the demonstration script to see all features in action:

```bash
python src/fsas/demo_error_recovery.py
```

## Testing

Run the unit tests:

```bash
python -m pytest tests/test_error_recovery_fsa.py -v
```

## Use Cases

1. **API Integration**: Retry failed API calls with exponential backoff
2. **Distributed Systems**: Handle transient failures in microservices
3. **Database Operations**: Recover from connection timeouts
4. **Resource Management**: Gracefully handle resource exhaustion
5. **Service Degradation**: Maintain availability with fallback mechanisms

## Architecture

The FSA follows a clear state machine pattern:

```
IDLE → ERROR_DETECTED → ERROR_CLASSIFIED → RECOVERY_IN_PROGRESS
                                          ↓
                    DEGRADED_MODE ← RECOVERY_FAILED
                                          ↓
                                   RECOVERY_SUCCESS → IDLE
```

## Best Practices

1. **Set appropriate retry limits**: Avoid infinite loops with reasonable max_retries
2. **Configure exponential backoff**: Prevent overwhelming downstream services
3. **Implement fallback actions**: Always have a degraded mode strategy
4. **Monitor error patterns**: Use statistics to identify systemic issues
5. **Custom logging**: Integrate with your monitoring infrastructure

## License

Part of the Agno project.
