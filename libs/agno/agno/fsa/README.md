## Circuit Breaker FSA - Advanced Resilience Patterns for MLA Framework

A comprehensive Circuit Breaker Finite State Automaton (FSA) implementation with advanced resilience patterns including multi-strategy failure detection, automatic recovery, flexible fallback mechanisms, and comprehensive monitoring.

### Features

- **Three-State FSA**: CLOSED, OPEN, HALF_OPEN with intelligent transitions
- **Multiple Failure Detection Strategies**: Count-based, percentage-based, consecutive, latency-based, anomaly detection, and more
- **Advanced Recovery Mechanisms**: Exponential backoff, adaptive, health check-based, gradual traffic ramping
- **Flexible Fallback Strategies**: Cache, default values, alternative services, degraded mode, request queuing
- **Comprehensive Monitoring**: Real-time metrics, Prometheus integration, alerting
- **Integration Patterns**: Retry logic, timeouts, bulkheads, rate limiting, caching
- **Thread-Safe**: Concurrent request handling with proper synchronization
- **Async Support**: Full async/await support for modern Python applications

### Quick Start

#### Basic Usage

```python
from agno.fsa import CircuitBreakerFSA, CircuitBreakerConfig

# Create configuration
config = CircuitBreakerConfig(
    failure_threshold=5,
    timeout=60.0,
    failure_rate_threshold=0.5
)

# Initialize circuit breaker
circuit_breaker = CircuitBreakerFSA(config=config, name="api_service")

# Execute function through circuit breaker
def api_call():
    return requests.get("https://api.example.com/data")

try:
    result = circuit_breaker.execute(api_call)
    print(f"Success: {result}")
except CircuitOpenError:
    print("Circuit is open, using fallback...")
    result = get_cached_data()
```

#### Using Decorator

```python
from agno.fsa import circuit_breaker, CircuitBreakerConfig

@circuit_breaker(
    config=CircuitBreakerConfig(failure_threshold=5, timeout=60.0),
    name="user_service"
)
def get_user_data(user_id):
    return requests.get(f"https://api.example.com/users/{user_id}")

# Use the decorated function normally
user = get_user_data(123)
```

### Advanced Usage

#### 1. Custom Failure Detection

```python
from agno.fsa import CircuitBreakerFSA, PercentageBasedDetector, SlidingWindowDetector

# Percentage-based detection
detector = PercentageBasedDetector(
    failure_rate_threshold=0.5,  # 50% failure rate
    minimum_requests=10,
    window_size=100
)

cb = CircuitBreakerFSA(
    failure_detector=detector,
    name="payment_service"
)

# Sliding window detection (time-based)
detector = SlidingWindowDetector(
    time_window_seconds=60.0,  # Last 60 seconds
    failure_rate_threshold=0.3,
    minimum_requests=5
)
```

#### 2. Latency-Based Detection

```python
from agno.fsa import LatencyBasedDetector

# Open circuit if too many slow requests
detector = LatencyBasedDetector(
    slow_call_duration_threshold=5000.0,  # 5 seconds in ms
    slow_call_rate_threshold=0.5,  # 50% slow calls
    minimum_requests=10
)

cb = CircuitBreakerFSA(
    failure_detector=detector,
    name="slow_service"
)
```

#### 3. Composite Detection (Multiple Strategies)

```python
from agno.fsa import CompositeDetector, CountBasedDetector, PercentageBasedDetector

# Combine multiple detectors
detector = CompositeDetector(
    detectors=[
        CountBasedDetector(failure_threshold=10),
        PercentageBasedDetector(failure_rate_threshold=0.5, minimum_requests=20),
    ],
    require_all=False  # OR logic (any detector can trigger)
)

cb = CircuitBreakerFSA(failure_detector=detector, name="critical_service")
```

#### 4. Anomaly Detection

```python
from agno.fsa import AnomalyDetector

# ML-based anomaly detection using statistical methods
detector = AnomalyDetector(
    zscore_threshold=3.0,  # 3 standard deviations
    minimum_samples=20,
    lookback_window=100
)

cb = CircuitBreakerFSA(failure_detector=detector, name="ml_service")
```

### Recovery Strategies

#### 1. Exponential Backoff

```python
from agno.fsa import ExponentialBackoffRecovery

strategy = ExponentialBackoffRecovery(
    initial_delay_seconds=1.0,
    max_delay_seconds=300.0,
    multiplier=2.0,
    jitter=True  # Add random jitter to prevent thundering herd
)

cb = CircuitBreakerFSA(recovery_strategy=strategy, name="service")
```

#### 2. Health Check-Based Recovery

```python
from agno.fsa import HealthCheckRecovery

def health_check():
    try:
        response = requests.get("https://api.example.com/health", timeout=2)
        return response.status_code == 200
    except:
        return False

strategy = HealthCheckRecovery(
    health_check=health_check,
    check_interval_seconds=10.0,
    consecutive_successes_required=2
)

cb = CircuitBreakerFSA(recovery_strategy=strategy, name="service")
```

#### 3. Gradual Traffic Ramping

```python
from agno.fsa import GradualRecovery

# Slowly increase traffic during recovery
strategy = GradualRecovery(
    initial_traffic_percentage=0.1,  # Start with 10%
    increment_percentage=0.1,  # Increase by 10%
    increment_interval_seconds=30.0,  # Every 30 seconds
    success_threshold_percentage=0.8  # Need 80% success to increment
)

cb = CircuitBreakerFSA(recovery_strategy=strategy, name="service")
```

### Fallback Strategies

#### 1. Cache Fallback

```python
from agno.fsa import CacheFallback

# Return cached responses when circuit is open
cache = CacheFallback(
    ttl_seconds=300.0,  # 5 minutes
    max_cache_size=1000,
    allow_stale=True,  # Allow stale cache entries
    stale_ttl_seconds=3600.0  # 1 hour for stale
)

cb = CircuitBreakerFSA(fallback_strategy=cache, name="service")

# Store values in cache manually
cache.store("user:123", {"id": 123, "name": "John"})
```

#### 2. Alternative Service Fallback

```python
from agno.fsa import AlternativeServiceFallback

def backup_service(*args, **kwargs):
    return requests.get("https://backup-api.example.com/data")

fallback = AlternativeServiceFallback(
    alternative_func=backup_service,
    timeout_seconds=5.0,
    retry_on_failure=True,
    max_retries=2
)

cb = CircuitBreakerFSA(fallback_strategy=fallback, name="service")
```

#### 3. Degraded Mode Fallback

```python
from agno.fsa import DegradedModeFallback

def degraded_handler(func, *args, **kwargs):
    # Return partial data in degraded mode
    return {
        "status": "degraded",
        "data": None,
        "message": "Service operating in degraded mode",
        "timestamp": datetime.now().isoformat()
    }

fallback = DegradedModeFallback(
    degraded_func=degraded_handler,
    include_error_info=True
)

cb = CircuitBreakerFSA(fallback_strategy=fallback, name="service")
```

#### 4. Queued Request Fallback

```python
from agno.fsa import QueuedRequestFallback

# Queue requests for later processing
fallback = QueuedRequestFallback(
    max_queue_size=1000,
    ttl_seconds=3600.0,  # Keep requests for 1 hour
    persist_to_disk=True
)

cb = CircuitBreakerFSA(fallback_strategy=fallback, name="service")

# Process queue when service recovers
stats = fallback.process_queue()
print(f"Processed {stats['total_processed']} queued requests")
```

#### 5. Composite Fallback (Try Multiple Strategies)

```python
from agno.fsa import CompositeFallback, CacheFallback, AlternativeServiceFallback, DefaultValueFallback

# Try multiple fallback strategies in order
fallback = CompositeFallback(
    strategies=[
        CacheFallback(ttl_seconds=300.0),
        AlternativeServiceFallback(alternative_func=backup_service),
        DefaultValueFallback(default_value={"error": "All services unavailable"})
    ]
)

cb = CircuitBreakerFSA(fallback_strategy=fallback, name="service")
```

### Integration Patterns

#### 1. Retry Integration

```python
from agno.fsa import RetryIntegration

# Combine circuit breaker with retry logic
retry = RetryIntegration(
    max_retries=3,
    exponential_backoff=True,
    backoff_multiplier=2.0,
    jitter=True
)

result = retry.wrap_execute(cb, api_call)
```

#### 2. Timeout Integration

```python
from agno.fsa import TimeoutIntegration

# Enforce timeouts on requests
timeout = TimeoutIntegration(
    timeout_seconds=5.0,
    raise_on_timeout=True
)

result = timeout.wrap_execute(cb, slow_api_call)
```

#### 3. Bulkhead Integration

```python
from agno.fsa import BulkheadIntegration

# Limit concurrent requests (resource isolation)
bulkhead = BulkheadIntegration(
    max_concurrent=10,
    max_queue_size=100,
    queue_timeout_seconds=30.0
)

result = bulkhead.wrap_execute(cb, api_call)
```

#### 4. Rate Limiting Integration

```python
from agno.fsa import RateLimiterIntegration

# Limit request rate
limiter = RateLimiterIntegration(
    requests_per_second=10.0,
    burst_size=20
)

result = limiter.wrap_execute(cb, api_call)
```

#### 5. Combined Integrations

```python
# Stack multiple integrations
retry = RetryIntegration(max_retries=3)
timeout = TimeoutIntegration(timeout_seconds=5.0)
limiter = RateLimiterIntegration(requests_per_second=10.0)

# Apply in order
def protected_call():
    return limiter.wrap_execute(
        cb,
        lambda: timeout.wrap_execute(
            cb,
            lambda: retry.wrap_execute(cb, api_call)
        )
    )
```

### Monitoring and Metrics

#### Get Metrics

```python
# Get current metrics
metrics = cb.get_metrics()

print(f"State: {metrics.state}")
print(f"Total Requests: {metrics.total_requests}")
print(f"Failures: {metrics.failed_requests}")
print(f"Failure Rate: {metrics.failure_rate:.1%}")
print(f"Average Latency: {metrics.average_latency_ms:.2f}ms")
print(f"State Transitions: {metrics.state_transitions}")
```

#### Export Prometheus Metrics

```python
from agno.fsa import MetricsExporter

exporter = MetricsExporter(cb)

# Prometheus format
prometheus_metrics = exporter.export_prometheus()
print(prometheus_metrics)

# JSON format
json_metrics = exporter.export_json()
print(json_metrics)
```

#### Set Up Alerts

```python
from agno.fsa import AlertManager

def email_alert_handler(alert):
    send_email(
        to="ops@example.com",
        subject=f"[{alert.level.value}] Circuit Breaker Alert",
        body=f"{alert.circuit_name}: {alert.message}"
    )

def slack_alert_handler(alert):
    send_slack_message(
        channel="#alerts",
        text=f":warning: {alert.circuit_name}: {alert.message}"
    )

# Register alert handlers
alert_manager = AlertManager(
    cb,
    alert_handlers=[email_alert_handler, slack_alert_handler]
)

# Alerts will be sent automatically on state changes
```

#### Custom Monitoring

```python
from agno.fsa import StateTransitionTracker, FailureRateCalculator, LatencyMonitor

# Track state transitions
tracker = StateTransitionTracker()

# Get transition history
transitions = tracker.get_transitions(limit=10)
for t in transitions:
    print(f"{t.timestamp}: {t.from_state} -> {t.to_state} ({t.reason})")

# Calculate time in each state
time_in_open = tracker.get_time_in_state(CircuitState.OPEN)
print(f"Time in OPEN state: {time_in_open:.2f}s")

# Check flapping rate (rapid state changes)
flapping_rate = tracker.get_flapping_rate(time_window_seconds=300.0)
print(f"Flapping rate: {flapping_rate:.2f} transitions/minute")
```

### Event Listeners

```python
# State change listener
def on_state_change(old_state, new_state):
    logger.info(f"Circuit state changed: {old_state} -> {new_state}")
    if new_state == CircuitState.OPEN:
        send_alert("Circuit breaker opened!")

cb.add_state_change_listener(on_state_change)

# Failure listener
def on_failure(error):
    logger.error(f"Request failed: {error}")

cb.add_failure_listener(on_failure)

# Success listener
def on_success():
    logger.debug("Request succeeded")

cb.add_success_listener(on_success)
```

### Async Support

```python
import asyncio

async def async_api_call():
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.example.com/data") as response:
            return await response.json()

# Execute async function through circuit breaker
result = await cb.execute_async(async_api_call)

# Async retry integration
result = await retry.wrap_execute_async(cb, async_api_call)
```

### Configuration Reference

```python
config = CircuitBreakerConfig(
    # Failure Thresholds
    failure_threshold=5,  # Number of failures to open circuit
    failure_rate_threshold=0.5,  # Percentage threshold (0.0-1.0)
    consecutive_failure_threshold=3,  # Consecutive failures

    # Timing
    timeout=60.0,  # Seconds before OPEN -> HALF_OPEN
    half_open_timeout=30.0,  # Timeout in HALF_OPEN state

    # Half-Open Probing
    half_open_max_calls=3,  # Number of probe calls
    half_open_success_threshold=2,  # Successes needed to close

    # Windows
    rolling_window_size=100,  # Size of rolling window
    time_window_seconds=60.0,  # Time window for calculations

    # Latency
    slow_call_duration_threshold=5.0,  # Slow call threshold (seconds)
    slow_call_rate_threshold=0.5,  # Percentage of slow calls

    # Recovery
    enable_exponential_backoff=True,
    max_backoff_time=300.0,  # Maximum backoff (seconds)
    backoff_multiplier=2.0,

    # Monitoring
    enable_metrics=True,
    enable_health_checks=True,
    health_check_interval=10.0,  # Health check interval (seconds)

    # Bulkhead
    enable_bulkhead=False,
    max_concurrent_calls=10,
    queue_size=100
)
```

### Best Practices

1. **Choose Appropriate Thresholds**: Set thresholds based on your service's characteristics and SLA requirements.

2. **Use Multiple Detection Strategies**: Combine count-based and percentage-based detection for robust failure detection.

3. **Implement Proper Fallbacks**: Always provide fallback strategies to ensure graceful degradation.

4. **Monitor and Alert**: Set up monitoring and alerting to track circuit breaker behavior.

5. **Test Recovery**: Regularly test recovery mechanisms to ensure they work as expected.

6. **Use Gradual Recovery**: For critical services, use gradual traffic ramping to avoid overwhelming recovering services.

7. **Cache Aggressively**: Use cache fallback to reduce load on backend services and improve response times.

8. **Combine Patterns**: Stack multiple resilience patterns (retry + timeout + circuit breaker) for comprehensive protection.

9. **Tune for Your Workload**: Adjust configuration based on observed traffic patterns and failure modes.

10. **Document Behavior**: Document circuit breaker configuration and expected behavior for your team.

### Examples

See the `examples/` directory for complete working examples:

- `basic_usage.py` - Basic circuit breaker usage
- `advanced_detection.py` - Advanced failure detection strategies
- `fallback_patterns.py` - Various fallback strategies
- `monitoring_setup.py` - Monitoring and alerting setup
- `async_example.py` - Async/await usage
- `microservices.py` - Microservices integration
- `chaos_engineering.py` - Chaos engineering scenarios

### Performance

Benchmarks on a modern laptop (M1 Pro, 16GB RAM):

- **Throughput**: ~50,000 requests/second with circuit breaker overhead
- **Latency Overhead**: <0.1ms per request in CLOSED state
- **Memory**: ~100KB base + ~50 bytes per request in rolling window
- **State Transition**: <1ms for state changes

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Circuit Breaker FSA                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐             │
│  │  CLOSED  │───▶│   OPEN   │───▶│HALF_OPEN │             │
│  │          │◀───│          │◀───│          │             │
│  └──────────┘    └──────────┘    └──────────┘             │
│                                                              │
│  Components:                                                 │
│  • Failure Detectors (7+ strategies)                        │
│  • Recovery Strategies (7+ mechanisms)                      │
│  • Fallback Strategies (6+ options)                         │
│  • Monitoring & Metrics                                     │
│  • Integration Patterns                                     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### License

See LICENSE file in the repository root.

### Contributing

Contributions are welcome! Please see CONTRIBUTING.md for guidelines.

### Support

For issues, questions, or contributions, please visit:
https://github.com/your-org/agno
