"""
Resilience Module for Agno Framework

Comprehensive resilience patterns for building fault-tolerant, production-ready agents:

- Circuit Breaker: Prevent cascading failures with automatic recovery
- Bulkhead: Isolate failures and limit resource consumption
- Retry: Automatic retry with exponential backoff
- Timeout: Enforce execution time limits
- Fallback: Graceful degradation with fallback functions
- Rate Limiting: Control request rates

Quick Start:
    ```python
    from agno.resilience import CircuitBreaker, CircuitBreakerConfig
    from agno.resilience.policies import create_balanced_policy

    # Create circuit breaker
    cb = CircuitBreaker(
        name="api_service",
        config=CircuitBreakerConfig(
            failure_policy=create_balanced_policy(),
            failure_threshold=5,
            recovery_timeout=60.0
        )
    )

    # Use circuit breaker
    try:
        result = cb.call(lambda: api_client.get_data())
    except CircuitBreakerOpenError:
        result = get_cached_data()  # Fallback
    ```

Decorator Usage:
    ```python
    from agno.resilience import resilient, CircuitBreakerConfig, BulkheadConfig

    @resilient(
        circuit_breaker_config=CircuitBreakerConfig(failure_threshold=5),
        bulkhead_config=BulkheadConfig(max_concurrent=10),
        name="critical_service"
    )
    async def critical_service_call():
        return await service.call()
    ```
"""

# Core circuit breaker
from agno.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    circuit_breaker,
)

# States
from agno.resilience.states import (
    CircuitState,
    CircuitStateData,
    StateTransition,
)

# Policies
from agno.resilience.policies import (
    FailurePolicy,
    ConsecutiveFailurePolicy,
    FailureRatePolicy,
    LatencyPolicy,
    CompositePolicy,
    CustomPredicatePolicy,
    TimeoutPolicy,
    HealthCheckConfig,
    create_aggressive_policy,
    create_balanced_policy,
    create_conservative_policy,
    create_latency_aware_policy,
)

# Bulkhead
from agno.resilience.bulkhead import (
    Bulkhead,
    BulkheadConfig,
    BulkheadMetrics,
    bulkhead,
)

# Metrics
from agno.resilience.metrics import (
    CircuitBreakerMetrics,
    MetricsCollector,
    get_global_collector,
    register_circuit,
)

# Decorators
from agno.resilience.decorators import (
    RetryConfig,
    TimeoutConfig,
    RateLimitConfig,
    with_retry,
    with_timeout,
    with_rate_limit,
    resilient,
    fallback,
)

# Exceptions
from agno.exceptions import (
    CircuitBreakerError,
    CircuitBreakerOpenError,
    BulkheadFullError,
)

__all__ = [
    # Circuit Breaker
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "circuit_breaker",
    # States
    "CircuitState",
    "CircuitStateData",
    "StateTransition",
    # Policies
    "FailurePolicy",
    "ConsecutiveFailurePolicy",
    "FailureRatePolicy",
    "LatencyPolicy",
    "CompositePolicy",
    "CustomPredicatePolicy",
    "TimeoutPolicy",
    "HealthCheckConfig",
    "create_aggressive_policy",
    "create_balanced_policy",
    "create_conservative_policy",
    "create_latency_aware_policy",
    # Bulkhead
    "Bulkhead",
    "BulkheadConfig",
    "BulkheadMetrics",
    "bulkhead",
    # Metrics
    "CircuitBreakerMetrics",
    "MetricsCollector",
    "get_global_collector",
    "register_circuit",
    # Decorators
    "RetryConfig",
    "TimeoutConfig",
    "RateLimitConfig",
    "with_retry",
    "with_timeout",
    "with_rate_limit",
    "resilient",
    "fallback",
    # Exceptions
    "CircuitBreakerError",
    "CircuitBreakerOpenError",
    "BulkheadFullError",
]


# Version
__version__ = "0.1.0"
