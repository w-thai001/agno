"""
Circuit Breaker Configuration Templates

Provides pre-configured circuit breaker templates for common use cases
and environments. These templates can be used as-is or customized.
"""

from dataclasses import dataclass
from typing import Optional

from agno.resilience.circuit_breaker import CircuitBreakerConfig
from agno.resilience.bulkhead import BulkheadConfig
from agno.resilience.policies import (
    create_aggressive_policy,
    create_balanced_policy,
    create_conservative_policy,
    create_latency_aware_policy,
    TimeoutPolicy,
    HealthCheckConfig,
)


# ====================
# Circuit Breaker Templates
# ====================

def critical_service_config() -> CircuitBreakerConfig:
    """
    Configuration for critical services that must fail fast.

    Use for: Payment gateways, authentication services, core APIs

    Characteristics:
    - Aggressive failure detection (3 consecutive failures)
    - Short recovery timeout (30s)
    - Limited half-open attempts (2)
    - No bulkhead (unlimited concurrent requests)

    Example:
        ```python
        from agno.resilience import CircuitBreaker
        from agno.resilience.configuration import critical_service_config

        cb = CircuitBreaker(name="payment_api", config=critical_service_config())
        ```
    """
    return CircuitBreakerConfig(
        failure_policy=create_aggressive_policy(),
        failure_threshold=3,
        success_threshold=2,
        recovery_timeout=30.0,
        half_open_max_calls=2,
        timeout_policy=TimeoutPolicy(
            open_timeout_seconds=30.0,
            adaptive_multiplier=1.5,
            max_timeout_seconds=180.0
        ),
        enable_metrics=True,
        verbose=True
    )


def external_api_config(max_concurrent: int = 50) -> CircuitBreakerConfig:
    """
    Configuration for external API calls with rate limiting.

    Use for: Third-party APIs, external services

    Characteristics:
    - Balanced failure detection
    - Medium recovery timeout (60s)
    - Bulkhead for rate limiting
    - Latency-aware failure detection

    Args:
        max_concurrent: Maximum concurrent requests allowed

    Example:
        ```python
        cb = CircuitBreaker(
            name="external_api",
            config=external_api_config(max_concurrent=20)
        )
        ```
    """
    return CircuitBreakerConfig(
        failure_policy=create_latency_aware_policy(p95_threshold_ms=2000.0),
        failure_threshold=5,
        success_threshold=3,
        recovery_timeout=60.0,
        half_open_max_calls=3,
        max_concurrent_calls=max_concurrent,
        timeout_policy=TimeoutPolicy(
            open_timeout_seconds=60.0,
            adaptive_multiplier=2.0,
            max_timeout_seconds=300.0
        ),
        enable_metrics=True,
        verbose=False
    )


def database_config(max_concurrent: int = 20) -> CircuitBreakerConfig:
    """
    Configuration for database connections.

    Use for: Database queries, connection pools

    Characteristics:
    - Conservative failure detection (tolerant of transient failures)
    - Strict bulkhead isolation
    - Health check probes
    - Longer recovery timeout

    Args:
        max_concurrent: Maximum concurrent database connections

    Example:
        ```python
        cb = CircuitBreaker(
            name="postgres_db",
            config=database_config(max_concurrent=10)
        )
        ```
    """
    return CircuitBreakerConfig(
        failure_policy=create_conservative_policy(),
        failure_threshold=10,
        success_threshold=5,
        recovery_timeout=120.0,
        half_open_max_calls=5,
        max_concurrent_calls=max_concurrent,
        health_check_config=HealthCheckConfig(
            enabled=True,
            probe_requests=5,
            required_success_rate=0.8,
            probe_timeout_seconds=10.0
        ),
        timeout_policy=TimeoutPolicy(
            open_timeout_seconds=120.0,
            adaptive_multiplier=1.5,
            max_timeout_seconds=600.0
        ),
        enable_metrics=True,
        verbose=False
    )


def microservice_config(
    service_name: str,
    max_concurrent: int = 100,
    failure_threshold: int = 5
) -> CircuitBreakerConfig:
    """
    Configuration for microservice-to-microservice communication.

    Use for: Internal service mesh, microservices architecture

    Characteristics:
    - Balanced failure detection
    - Generous bulkhead for high throughput
    - Adaptive timeout
    - Comprehensive metrics

    Args:
        service_name: Name of the target service
        max_concurrent: Maximum concurrent requests
        failure_threshold: Number of failures before opening

    Example:
        ```python
        cb = CircuitBreaker(
            name=f"user_service",
            config=microservice_config("user-service", max_concurrent=50)
        )
        ```
    """
    return CircuitBreakerConfig(
        failure_policy=create_balanced_policy(),
        failure_threshold=failure_threshold,
        success_threshold=3,
        recovery_timeout=60.0,
        half_open_max_calls=5,
        max_concurrent_calls=max_concurrent,
        timeout_policy=TimeoutPolicy(
            open_timeout_seconds=60.0,
            adaptive_multiplier=2.0,
            max_timeout_seconds=300.0
        ),
        enable_metrics=True,
        verbose=False
    )


def unstable_service_config() -> CircuitBreakerConfig:
    """
    Configuration for known unstable services.

    Use for: Beta services, experimental endpoints, flaky third-party APIs

    Characteristics:
    - Very conservative failure detection
    - Long recovery timeout
    - Many retry attempts in half-open
    - Relaxed thresholds

    Example:
        ```python
        cb = CircuitBreaker(
            name="beta_api",
            config=unstable_service_config()
        )
        ```
    """
    return CircuitBreakerConfig(
        failure_policy=create_conservative_policy(),
        failure_threshold=20,  # Very high threshold
        success_threshold=10,  # Require many successes to close
        recovery_timeout=180.0,  # 3 minutes
        half_open_max_calls=10,
        max_concurrent_calls=10,  # Limit blast radius
        timeout_policy=TimeoutPolicy(
            open_timeout_seconds=180.0,
            adaptive_multiplier=1.2,  # Slow backoff
            max_timeout_seconds=600.0
        ),
        enable_metrics=True,
        verbose=True
    )


def ml_model_config(max_concurrent: int = 5) -> CircuitBreakerConfig:
    """
    Configuration for ML model inference endpoints.

    Use for: ML/AI model APIs, GPU-intensive operations

    Characteristics:
    - Very strict bulkhead (expensive resources)
    - Latency-aware failure detection
    - Long timeouts (inference can be slow)
    - Conservative failure thresholds

    Args:
        max_concurrent: Maximum concurrent inference requests

    Example:
        ```python
        cb = CircuitBreaker(
            name="gpt4_inference",
            config=ml_model_config(max_concurrent=3)
        )
        ```
    """
    return CircuitBreakerConfig(
        failure_policy=create_latency_aware_policy(p95_threshold_ms=5000.0),
        failure_threshold=3,
        success_threshold=2,
        recovery_timeout=120.0,
        half_open_max_calls=2,
        max_concurrent_calls=max_concurrent,  # Strict limit for GPU resources
        timeout_policy=TimeoutPolicy(
            open_timeout_seconds=120.0,
            adaptive_multiplier=1.5,
            max_timeout_seconds=600.0
        ),
        enable_metrics=True,
        verbose=True
    )


# ====================
# Bulkhead Templates
# ====================

def io_bound_bulkhead() -> BulkheadConfig:
    """
    Bulkhead configuration for I/O-bound operations.

    Use for: File I/O, network requests, database queries
    """
    return BulkheadConfig(
        max_concurrent=50,
        max_queued=100,
        queue_timeout=10.0,
        enable_metrics=True
    )


def cpu_bound_bulkhead() -> BulkheadConfig:
    """
    Bulkhead configuration for CPU-bound operations.

    Use for: Data processing, computations, compression
    """
    import os
    cpu_count = os.cpu_count() or 4

    return BulkheadConfig(
        max_concurrent=cpu_count,
        max_queued=cpu_count * 2,
        queue_timeout=30.0,
        enable_metrics=True
    )


def gpu_bound_bulkhead() -> BulkheadConfig:
    """
    Bulkhead configuration for GPU-bound operations.

    Use for: ML inference, video processing, rendering
    """
    return BulkheadConfig(
        max_concurrent=2,  # Most systems have 1-2 GPUs
        max_queued=10,
        queue_timeout=60.0,
        enable_metrics=True
    )


# ====================
# Environment-based Configuration
# ====================

@dataclass
class EnvironmentConfig:
    """Environment-specific circuit breaker settings"""
    failure_threshold_multiplier: float = 1.0
    timeout_multiplier: float = 1.0
    enable_verbose: bool = False
    enable_metrics: bool = True


def development_env() -> EnvironmentConfig:
    """Development environment settings (more verbose, tolerant)"""
    return EnvironmentConfig(
        failure_threshold_multiplier=2.0,  # More tolerant
        timeout_multiplier=2.0,  # Longer timeouts
        enable_verbose=True,
        enable_metrics=True
    )


def staging_env() -> EnvironmentConfig:
    """Staging environment settings (production-like but verbose)"""
    return EnvironmentConfig(
        failure_threshold_multiplier=1.2,
        timeout_multiplier=1.5,
        enable_verbose=True,
        enable_metrics=True
    )


def production_env() -> EnvironmentConfig:
    """Production environment settings (strict, quiet)"""
    return EnvironmentConfig(
        failure_threshold_multiplier=1.0,
        timeout_multiplier=1.0,
        enable_verbose=False,
        enable_metrics=True
    )


def apply_environment(
    config: CircuitBreakerConfig,
    env: EnvironmentConfig
) -> CircuitBreakerConfig:
    """
    Apply environment-specific settings to a configuration.

    Example:
        ```python
        base_config = external_api_config()
        prod_config = apply_environment(base_config, production_env())
        ```
    """
    config.failure_threshold = int(config.failure_threshold * env.failure_threshold_multiplier)
    config.recovery_timeout = config.recovery_timeout * env.timeout_multiplier
    config.verbose = env.enable_verbose
    config.enable_metrics = env.enable_metrics

    if config.timeout_policy:
        config.timeout_policy.open_timeout_seconds *= env.timeout_multiplier
        config.timeout_policy.max_timeout_seconds *= env.timeout_multiplier

    return config
