"""
Circuit Breaker FSA - Advanced Resilience Patterns for MLA Framework

This module provides a comprehensive Circuit Breaker Finite State Automaton (FSA)
implementation with advanced resilience patterns including:
- Multi-strategy failure detection
- Automatic recovery with multiple strategies
- Flexible fallback mechanisms
- Comprehensive monitoring and metrics
- Integration with retry, timeout, and rate limiting
"""

from agno.fsa.circuit_breaker import (
    CircuitBreakerFSA,
    CircuitState,
    CircuitBreakerConfig,
    CircuitMetrics,
    HealthStatus,
    CircuitOpenError,
    FallbackFailedError,
    ConfigurationError,
    StateTransitionError,
)

from agno.fsa.failure_detectors import (
    FailureDetector,
    CountBasedDetector,
    PercentageBasedDetector,
    ConsecutiveFailureDetector,
    SlidingWindowDetector,
    AnomalyDetector,
    LatencyBasedDetector,
    CustomDetector,
)

from agno.fsa.recovery_strategies import (
    RecoveryStrategy,
    ExponentialBackoffRecovery,
    FixedDelayRecovery,
    AdaptiveRecovery,
    HealthCheckRecovery,
    ManualRecovery,
    GradualRecovery,
)

from agno.fsa.fallback_strategies import (
    FallbackStrategy,
    CacheFallback,
    DefaultValueFallback,
    AlternativeServiceFallback,
    DegradedModeFallback,
    QueuedRequestFallback,
    CustomFallback,
)

from agno.fsa.monitoring import (
    StateTransitionTracker,
    FailureRateCalculator,
    LatencyMonitor,
    SuccessRateTracker,
    CircuitHealthReporter,
    MetricsExporter,
    AlertManager,
)

from agno.fsa.integration import (
    RetryIntegration,
    TimeoutIntegration,
    BulkheadIntegration,
    RateLimiterIntegration,
    CacheIntegration,
    ServiceMeshIntegration,
)

__all__ = [
    # Core
    "CircuitBreakerFSA",
    "CircuitState",
    "CircuitBreakerConfig",
    "CircuitMetrics",
    "HealthStatus",
    "CircuitOpenError",
    "FallbackFailedError",
    "ConfigurationError",
    "StateTransitionError",
    # Failure Detectors
    "FailureDetector",
    "CountBasedDetector",
    "PercentageBasedDetector",
    "ConsecutiveFailureDetector",
    "SlidingWindowDetector",
    "AnomalyDetector",
    "LatencyBasedDetector",
    "CustomDetector",
    # Recovery Strategies
    "RecoveryStrategy",
    "ExponentialBackoffRecovery",
    "FixedDelayRecovery",
    "AdaptiveRecovery",
    "HealthCheckRecovery",
    "ManualRecovery",
    "GradualRecovery",
    # Fallback Strategies
    "FallbackStrategy",
    "CacheFallback",
    "DefaultValueFallback",
    "AlternativeServiceFallback",
    "DegradedModeFallback",
    "QueuedRequestFallback",
    "CustomFallback",
    # Monitoring
    "StateTransitionTracker",
    "FailureRateCalculator",
    "LatencyMonitor",
    "SuccessRateTracker",
    "CircuitHealthReporter",
    "MetricsExporter",
    "AlertManager",
    # Integration
    "RetryIntegration",
    "TimeoutIntegration",
    "BulkheadIntegration",
    "RateLimiterIntegration",
    "CacheIntegration",
    "ServiceMeshIntegration",
]
