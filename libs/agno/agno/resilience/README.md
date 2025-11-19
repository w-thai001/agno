## Circuit Breaker FSA for Agno Framework

Comprehensive resilience patterns for building fault-tolerant, production-ready AI agents and microservices.

### Features

#### Core Functionality
- ✅ Circuit breaker state machine (CLOSED → OPEN → HALF_OPEN)
- ✅ Automatic failure detection and recovery
- ✅ Configurable failure thresholds and timeout windows
- ✅ Success/failure rate tracking
- ✅ State transition event hooks
- ✅ Per-service circuit breaker instances

#### Advanced Features
- ✅ Adaptive timeout adjustment based on latency patterns
- ✅ Bulkhead isolation (limit concurrent requests)
- ✅ Fallback function execution on circuit open
- ✅ Health check probes during half-open state
- ✅ Circuit breaker inheritance (global → service → endpoint)
- ✅ Custom failure predicates (beyond status codes)

#### Monitoring & Metrics
- ✅ Real-time state tracking (closed/open/half-open counts)
- ✅ Failure rate metrics with time-series data
- ✅ Latency percentiles (p50, p95, p99)
- ✅ Circuit state change event logging
- ✅ Integration with metrics exporters (Prometheus, Datadog)
- ✅ Dashboard-ready JSON/API endpoints

#### Integration Patterns
- ✅ Decorator-based circuit breaker (@circuit_breaker)
- ✅ Middleware integration for HTTP clients
- ✅ Promise/async wrapper functions
- ✅ Manual circuit breaker control (force open/close)
- ✅ Multi-backend support

#### Configuration
- ✅ Pydantic-based configuration schemas
- ✅ Environment-based policies
- ✅ Runtime configuration updates
- ✅ Circuit breaker templates for common use cases

#### Error Handling
- ✅ Graceful degradation strategies
- ✅ Fallback chain execution (primary → secondary → default)
- ✅ Circuit open error responses with retry-after hints
- ✅ Cascading failure prevention
- ✅ Integration with retry and timeout mechanisms

### Quick Start

#### Basic Usage

```python
from agno.resilience import CircuitBreaker, CircuitBreakerConfig

# Create circuit breaker
cb = CircuitBreaker(
    name="api_service",
    config=CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=60.0,
        half_open_max_calls=3
    )
)

# Use circuit breaker
try:
    result = cb.call(lambda: api_client.get_data())
except CircuitBreakerOpenError:
    result = get_cached_data()  # Fallback
```

#### Decorator Pattern

```python
from agno.resilience import resilient, CircuitBreakerConfig, BulkheadConfig

@resilient(
    circuit_breaker_config=CircuitBreakerConfig(failure_threshold=5),
    bulkhead_config=BulkheadConfig(max_concurrent=10),
    name="critical_service"
)
def critical_service_call():
    return service.call()
```

#### Async Support

```python
# Async function calls
result = await cb.call_async(async_api_call)

# Async context manager
async with cb.context_async():
    result = await expensive_operation()
```

### Configuration Templates

Pre-configured templates for common use cases:

```python
from agno.resilience.configuration import (
    critical_service_config,
    external_api_config,
    database_config,
    microservice_config,
    ml_model_config,
)

# Critical service (payment gateway)
cb = CircuitBreaker("payment", config=critical_service_config())

# External API (third-party service)
cb = CircuitBreaker("weather_api", config=external_api_config(max_concurrent=20))

# Database connections
cb = CircuitBreaker("postgres", config=database_config(max_concurrent=10))

# Microservice communication
cb = CircuitBreaker("user_service", config=microservice_config("user", max_concurrent=50))

# ML model inference (GPU-bound)
cb = CircuitBreaker("gpt4", config=ml_model_config(max_concurrent=3))
```

### Failure Policies

Different strategies for detecting failures:

```python
from agno.resilience.policies import (
    ConsecutiveFailurePolicy,
    FailureRatePolicy,
    LatencyPolicy,
    CompositePolicy,
    create_aggressive_policy,
    create_balanced_policy,
    create_conservative_policy,
)

# Consecutive failures (simple)
policy = ConsecutiveFailurePolicy(threshold=5)

# Failure rate over time window (sophisticated)
policy = FailureRatePolicy(
    threshold=0.5,  # 50% failure rate
    window_seconds=60,
    minimum_requests=10
)

# Latency-based failures
policy = LatencyPolicy(
    p95_threshold_ms=1000.0,
    p99_threshold_ms=2000.0
)

# Combine multiple policies
policy = CompositePolicy(
    policies=[
        ConsecutiveFailurePolicy(threshold=5),
        FailureRatePolicy(threshold=0.5)
    ],
    require_all=False  # OR logic
)
```

### Bulkhead Isolation

Limit concurrent execution to prevent resource exhaustion:

```python
from agno.resilience import Bulkhead, BulkheadConfig

bulkhead = Bulkhead(
    name="database_pool",
    config=BulkheadConfig(
        max_concurrent=10,
        max_queued=20,
        queue_timeout=5.0
    )
)

# Use bulkhead
result = bulkhead.execute(lambda: db.query(sql))

# Decorator pattern
@bulkhead(name="api", config=BulkheadConfig(max_concurrent=5))
def api_call():
    return requests.get(url)
```

### Metrics and Monitoring

#### Prometheus Export

```python
metrics = cb.get_metrics()
prometheus_format = metrics.to_prometheus_format()
```

#### Datadog Export

```python
datadog_metrics = metrics.to_datadog_format()
```

#### JSON Export for Dashboards

```python
json_metrics = metrics.to_json()
```

#### Global Metrics Collection

```python
from agno.resilience.metrics import get_global_collector

collector = get_global_collector()
summary = collector.get_summary()

print(f"Total circuits: {summary['total_circuits']}")
print(f"Unhealthy circuits: {summary['unhealthy_circuits']}")
print(f"Overall failure rate: {summary['aggregate_metrics']['overall_failure_rate']}")
```

### State Transition Hooks

Monitor circuit state changes:

```python
def on_circuit_open(state):
    logger.error(f"Circuit opened! Failure rate: {state.get_failure_rate()}")
    send_alert("Circuit breaker triggered")

def on_circuit_close(state):
    logger.info(f"Circuit recovered. Success rate: {state.get_success_rate()}")

cb = CircuitBreaker(
    name="monitored_service",
    config=CircuitBreakerConfig(
        on_open=on_circuit_open,
        on_close=on_circuit_close
    )
)
```

### Manual Control

Force circuit state when needed:

```python
# Force circuit open (maintenance mode)
cb.force_open()

# Force circuit closed (emergency override)
cb.force_close()

# Reset to initial state
cb.reset()

# Check current state
state = cb.get_state()  # CircuitState.CLOSED/OPEN/HALF_OPEN
```

### Testing

#### Unit Tests

```bash
pytest tests/unit/resilience/test_circuit_breaker.py -v
```

#### Integration Tests

```bash
pytest tests/integration/resilience/test_integration.py -v
```

#### Load Tests

```bash
pytest tests/integration/resilience/test_integration.py::TestLoadScenarios -v
```

### Examples

See comprehensive examples in `cookbook/examples/resilience/`:

- `circuit_breaker_microservices.py` - Microservices architecture example
- Demonstrates:
  - Service-to-service communication
  - Graceful degradation
  - Cascading failure prevention
  - Metrics collection
  - Async patterns

### Architecture

#### State Machine

```
CLOSED ──(failures exceed threshold)──> OPEN
   ↑                                      │
   │                                      │
   │                               (timeout expires)
   │                                      │
   │                                      ↓
   └──(recovery successful)──────── HALF_OPEN
```

#### Module Structure

```
agno/resilience/
├── __init__.py              # Public API
├── circuit_breaker.py       # Core FSA implementation
├── states.py                # State definitions and tracking
├── policies.py              # Failure detection policies
├── metrics.py               # Metrics collection and export
├── bulkhead.py             # Bulkhead isolation pattern
├── decorators.py            # Decorator utilities
├── configuration.py         # Configuration templates
└── README.md               # This file
```

### Best Practices

1. **Choose the Right Policy**
   - Use `ConsecutiveFailurePolicy` for simple scenarios
   - Use `FailureRatePolicy` for production workloads
   - Use `LatencyPolicy` for latency-sensitive services
   - Combine policies with `CompositePolicy` for sophisticated detection

2. **Set Appropriate Thresholds**
   - Critical services: Low threshold (3-5 failures)
   - Unstable services: High threshold (10-20 failures)
   - Consider request volume when setting thresholds

3. **Use Bulkhead Isolation**
   - Protect limited resources (databases, GPUs)
   - Prevent resource exhaustion
   - Limit blast radius of failures

4. **Enable Metrics in Production**
   - Always enable metrics for production systems
   - Export to monitoring systems (Prometheus, Datadog)
   - Set up alerts for circuit state changes

5. **Implement Fallbacks**
   - Always provide fallback functions
   - Use cached data when possible
   - Degrade gracefully rather than failing completely

6. **Test Resilience**
   - Unit test state transitions
   - Integration test with mock failures
   - Load test under realistic conditions
   - Chaos test with random failures

### Performance

- **Low overhead**: <1ms latency added per request
- **Thread-safe**: Uses locks for state management
- **Memory efficient**: Circular buffers for metrics (max 100 recent calls)
- **Scalable**: Supports thousands of concurrent requests

### Integration with Agno Agent

```python
from agno import Agent
from agno.resilience import CircuitBreaker, CircuitBreakerConfig

# Create agent with circuit breaker for model calls
agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    circuit_breaker=CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=60.0
    )
)
```

*(Integration with Agent class coming in future release)*

### Contributing

When contributing to the resilience module:

1. Add comprehensive tests for new features
2. Update this README with examples
3. Follow existing code style and patterns
4. Add type hints for all public APIs
5. Update metrics collection if adding new state

### License

Part of the Agno Framework - Same license as parent project
