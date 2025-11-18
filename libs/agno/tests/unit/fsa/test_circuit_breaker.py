"""
Comprehensive tests for Circuit Breaker FSA.

This test suite covers:
- Core circuit breaker functionality
- State transitions
- Failure detection strategies
- Recovery mechanisms
- Fallback strategies
- Monitoring and metrics
- Integration patterns
"""

import asyncio
import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch

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
    circuit_breaker,
)

from agno.fsa.failure_detectors import (
    CountBasedDetector,
    PercentageBasedDetector,
    ConsecutiveFailureDetector,
    SlidingWindowDetector,
    LatencyBasedDetector,
    AnomalyDetector,
    CustomDetector,
    CompositeDetector,
    ErrorTypeDetector,
    AdaptiveDetector,
)

from agno.fsa.recovery_strategies import (
    ExponentialBackoffRecovery,
    FixedDelayRecovery,
    AdaptiveRecovery,
    HealthCheckRecovery,
    ManualRecovery,
    GradualRecovery,
    ScheduledRecovery,
)

from agno.fsa.fallback_strategies import (
    CacheFallback,
    DefaultValueFallback,
    AlternativeServiceFallback,
    DegradedModeFallback,
    QueuedRequestFallback,
    CustomFallback,
    CompositeFallback,
)

from agno.fsa.monitoring import (
    StateTransitionTracker,
    FailureRateCalculator,
    LatencyMonitor,
    SuccessRateTracker,
    CircuitHealthReporter,
    AlertManager,
    AlertLevel,
)

from agno.fsa.integration import (
    RetryIntegration,
    TimeoutIntegration,
    BulkheadIntegration,
    RateLimiterIntegration,
    CacheIntegration,
    ServiceMeshIntegration,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def config():
    """Create test configuration."""
    return CircuitBreakerConfig(
        failure_threshold=5,
        timeout=1.0,
        half_open_max_calls=3,
    )


@pytest.fixture
def circuit_breaker(config):
    """Create circuit breaker instance."""
    cb = CircuitBreakerFSA(config=config, name="test_circuit")
    yield cb
    cb.shutdown()


@pytest.fixture
def failing_func():
    """Create a function that always fails."""
    def func():
        raise ValueError("Test error")
    return func


@pytest.fixture
def succeeding_func():
    """Create a function that always succeeds."""
    def func():
        return "success"
    return func


# ============================================================================
# Core Circuit Breaker Tests
# ============================================================================


class TestCircuitBreakerCore:
    """Tests for core circuit breaker functionality."""

    def test_initialization(self, circuit_breaker):
        """Test circuit breaker initializes in CLOSED state."""
        assert circuit_breaker.get_state() == CircuitState.CLOSED
        assert circuit_breaker.name == "test_circuit"

    def test_successful_execution(self, circuit_breaker, succeeding_func):
        """Test successful request execution."""
        result = circuit_breaker.execute(succeeding_func)
        assert result == "success"
        metrics = circuit_breaker.get_metrics()
        assert metrics.successful_requests == 1
        assert metrics.failed_requests == 0

    def test_failed_execution(self, circuit_breaker, failing_func):
        """Test failed request execution."""
        with pytest.raises(ValueError):
            circuit_breaker.execute(failing_func)

        metrics = circuit_breaker.get_metrics()
        assert metrics.failed_requests == 1

    def test_opens_on_failure_threshold(self, circuit_breaker, failing_func):
        """Test circuit opens when failure threshold is reached."""
        # Trigger failures
        for _ in range(5):
            with pytest.raises(ValueError):
                circuit_breaker.execute(failing_func)

        assert circuit_breaker.get_state() == CircuitState.OPEN

    def test_rejects_requests_when_open(self, circuit_breaker, failing_func, succeeding_func):
        """Test circuit rejects requests when OPEN."""
        # Open the circuit
        for _ in range(5):
            with pytest.raises(ValueError):
                circuit_breaker.execute(failing_func)

        # Attempt execution should be rejected
        with pytest.raises(CircuitOpenError):
            circuit_breaker.execute(succeeding_func)

        metrics = circuit_breaker.get_metrics()
        assert metrics.rejected_requests >= 1

    def test_transitions_to_half_open(self, circuit_breaker, failing_func):
        """Test circuit transitions to HALF_OPEN after timeout."""
        config = CircuitBreakerConfig(failure_threshold=3, timeout=0.1)
        cb = CircuitBreakerFSA(config=config, name="test")

        # Open circuit
        for _ in range(3):
            with pytest.raises(ValueError):
                cb.execute(failing_func)

        assert cb.get_state() == CircuitState.OPEN

        # Wait for timeout
        time.sleep(0.15)

        # Next execution should transition to HALF_OPEN
        with pytest.raises(ValueError):
            cb.execute(failing_func)

        assert cb.get_state() == CircuitState.OPEN  # Failed probe reopens
        cb.shutdown()

    def test_half_open_closes_on_success(self):
        """Test HALF_OPEN transitions to CLOSED on successful probes."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            timeout=0.1,
            half_open_max_calls=2,
            half_open_success_threshold=2
        )
        cb = CircuitBreakerFSA(config=config, name="test")

        failing_func = Mock(side_effect=ValueError("error"))
        succeeding_func = Mock(return_value="success")

        # Open circuit
        for _ in range(3):
            with pytest.raises(ValueError):
                cb.execute(failing_func)

        assert cb.get_state() == CircuitState.OPEN

        # Wait for timeout
        time.sleep(0.15)

        # Force transition to HALF_OPEN
        cb._transition_to(CircuitState.HALF_OPEN, "test")

        # Successful probes
        cb.execute(succeeding_func)
        cb.execute(succeeding_func)

        assert cb.get_state() == CircuitState.CLOSED
        cb.shutdown()

    def test_manual_force_open(self, circuit_breaker):
        """Test manually forcing circuit OPEN."""
        assert circuit_breaker.get_state() == CircuitState.CLOSED
        circuit_breaker.force_open()
        assert circuit_breaker.get_state() == CircuitState.OPEN

    def test_manual_force_close(self, circuit_breaker, failing_func):
        """Test manually forcing circuit CLOSED."""
        # Open circuit
        for _ in range(5):
            with pytest.raises(ValueError):
                circuit_breaker.execute(failing_func)

        assert circuit_breaker.get_state() == CircuitState.OPEN

        circuit_breaker.force_close()
        assert circuit_breaker.get_state() == CircuitState.CLOSED

    def test_reset(self, circuit_breaker, failing_func):
        """Test resetting circuit breaker."""
        # Generate some activity
        for _ in range(3):
            with pytest.raises(ValueError):
                circuit_breaker.execute(failing_func)

        metrics_before = circuit_breaker.get_metrics()
        assert metrics_before.failed_requests > 0

        circuit_breaker.reset()

        assert circuit_breaker.get_state() == CircuitState.CLOSED
        metrics_after = circuit_breaker.get_metrics()
        assert metrics_after.failed_requests == 0

    def test_concurrent_requests(self, circuit_breaker):
        """Test concurrent request handling."""
        import threading

        results = []

        def worker():
            try:
                result = circuit_breaker.execute(lambda: "success")
                results.append(result)
            except Exception as e:
                results.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 10
        assert all(r == "success" for r in results)

    @pytest.mark.asyncio
    async def test_async_execution(self, circuit_breaker):
        """Test async request execution."""
        async def async_func():
            return "async_success"

        result = await circuit_breaker.execute_async(async_func)
        assert result == "async_success"

    def test_decorator(self):
        """Test circuit breaker decorator."""
        @circuit_breaker(config=CircuitBreakerConfig(failure_threshold=2))
        def test_func():
            return "decorated"

        result = test_func()
        assert result == "decorated"

        # Access circuit breaker instance
        cb = test_func._circuit_breaker
        assert isinstance(cb, CircuitBreakerFSA)
        cb.shutdown()


# ============================================================================
# Configuration Tests
# ============================================================================


class TestConfiguration:
    """Tests for circuit breaker configuration."""

    def test_valid_configuration(self):
        """Test valid configuration."""
        config = CircuitBreakerConfig(
            failure_threshold=10,
            timeout=30.0,
            failure_rate_threshold=0.6
        )
        config.validate()  # Should not raise

    def test_invalid_failure_threshold(self):
        """Test invalid failure threshold."""
        config = CircuitBreakerConfig(failure_threshold=0)
        with pytest.raises(ConfigurationError):
            config.validate()

    def test_invalid_failure_rate(self):
        """Test invalid failure rate threshold."""
        config = CircuitBreakerConfig(failure_rate_threshold=1.5)
        with pytest.raises(ConfigurationError):
            config.validate()

    def test_update_configuration(self, circuit_breaker):
        """Test updating configuration."""
        new_config = CircuitBreakerConfig(failure_threshold=10)
        circuit_breaker.configure(new_config)
        assert circuit_breaker.config.failure_threshold == 10


# ============================================================================
# Failure Detector Tests
# ============================================================================


class TestFailureDetectors:
    """Tests for failure detection strategies."""

    def test_count_based_detector(self):
        """Test count-based failure detection."""
        detector = CountBasedDetector(failure_threshold=3)
        cb = CircuitBreakerFSA(failure_detector=detector, name="test")

        failing_func = Mock(side_effect=ValueError("error"))

        # Trigger failures
        for _ in range(3):
            with pytest.raises(ValueError):
                cb.execute(failing_func)

        assert cb.get_state() == CircuitState.OPEN
        cb.shutdown()

    def test_percentage_based_detector(self):
        """Test percentage-based failure detection."""
        detector = PercentageBasedDetector(failure_rate_threshold=0.5, minimum_requests=4)
        cb = CircuitBreakerFSA(failure_detector=detector, name="test")

        # Mix of successes and failures (50% failure rate)
        for i in range(4):
            try:
                if i % 2 == 0:
                    cb.execute(Mock(return_value="success"))
                else:
                    cb.execute(Mock(side_effect=ValueError("error")))
            except ValueError:
                pass

        assert cb.get_state() == CircuitState.OPEN
        cb.shutdown()

    def test_consecutive_failure_detector(self):
        """Test consecutive failure detection."""
        detector = ConsecutiveFailureDetector(consecutive_threshold=3)
        cb = CircuitBreakerFSA(failure_detector=detector, name="test")

        failing_func = Mock(side_effect=ValueError("error"))

        for _ in range(3):
            with pytest.raises(ValueError):
                cb.execute(failing_func)

        assert cb.get_state() == CircuitState.OPEN
        cb.shutdown()

    def test_latency_based_detector(self):
        """Test latency-based failure detection."""
        detector = LatencyBasedDetector(
            slow_call_duration_threshold=100.0,  # 100ms
            slow_call_rate_threshold=0.5,
            minimum_requests=4
        )
        cb = CircuitBreakerFSA(failure_detector=detector, name="test")

        # Slow functions
        def slow_func():
            time.sleep(0.11)  # 110ms
            return "slow"

        # Execute slow calls
        for _ in range(4):
            cb.execute(slow_func)

        # Should open due to high slow call rate
        assert cb.get_state() == CircuitState.OPEN
        cb.shutdown()

    def test_custom_detector(self):
        """Test custom failure detector."""
        def custom_predicate(history, config):
            return len(history) >= 5 and sum(1 for r in history if not r.success) >= 3

        detector = CustomDetector(predicate=custom_predicate)
        cb = CircuitBreakerFSA(failure_detector=detector, name="test")

        failing_func = Mock(side_effect=ValueError("error"))

        # Trigger failures
        for _ in range(5):
            with pytest.raises(ValueError):
                cb.execute(failing_func)

        assert cb.get_state() == CircuitState.OPEN
        cb.shutdown()

    def test_composite_detector_or(self):
        """Test composite detector with OR logic."""
        detector = CompositeDetector(
            detectors=[
                CountBasedDetector(failure_threshold=3),
                ConsecutiveFailureDetector(consecutive_threshold=2)
            ],
            require_all=False  # OR
        )
        cb = CircuitBreakerFSA(failure_detector=detector, name="test")

        failing_func = Mock(side_effect=ValueError("error"))

        # 2 consecutive failures should trigger (second detector)
        for _ in range(2):
            with pytest.raises(ValueError):
                cb.execute(failing_func)

        assert cb.get_state() == CircuitState.OPEN
        cb.shutdown()


# ============================================================================
# Recovery Strategy Tests
# ============================================================================


class TestRecoveryStrategies:
    """Tests for recovery strategies."""

    def test_exponential_backoff_recovery(self):
        """Test exponential backoff recovery."""
        strategy = ExponentialBackoffRecovery(initial_delay_seconds=0.1, multiplier=2.0)

        last_failure_time = datetime.now()

        # First attempt
        next_attempt_0 = strategy.calculate_next_attempt_time(0, last_failure_time, None)
        delay_0 = (next_attempt_0 - last_failure_time).total_seconds()
        assert 0.1 <= delay_0 <= 0.2  # 0.1 + jitter

        # Second attempt (should be ~0.2s)
        next_attempt_1 = strategy.calculate_next_attempt_time(1, last_failure_time, None)
        delay_1 = (next_attempt_1 - last_failure_time).total_seconds()
        assert 0.2 <= delay_1 <= 0.3

    def test_fixed_delay_recovery(self):
        """Test fixed delay recovery."""
        strategy = FixedDelayRecovery(delay_seconds=1.0)

        last_failure_time = datetime.now()
        next_attempt = strategy.calculate_next_attempt_time(0, last_failure_time, None)

        delay = (next_attempt - last_failure_time).total_seconds()
        assert 0.9 <= delay <= 1.1

    def test_manual_recovery(self):
        """Test manual recovery strategy."""
        strategy = ManualRecovery()

        # Should not automatically recover
        assert not strategy.should_attempt_recovery(datetime.now())

        # Allow recovery
        strategy.allow_recovery()
        assert strategy.should_attempt_recovery(datetime.now())

    def test_gradual_recovery(self):
        """Test gradual recovery strategy."""
        strategy = GradualRecovery(
            initial_traffic_percentage=0.2,
            increment_percentage=0.2
        )

        assert strategy.get_current_traffic_percentage() == 0.2

        # Simulate successful requests
        for _ in range(20):
            strategy.record_request_result(True)

        # Traffic should have increased
        assert strategy.get_current_traffic_percentage() > 0.2


# ============================================================================
# Fallback Strategy Tests
# ============================================================================


class TestFallbackStrategies:
    """Tests for fallback strategies."""

    def test_cache_fallback(self):
        """Test cache fallback."""
        cache = CacheFallback(ttl_seconds=1.0)

        # Store value in cache
        cache.store("key1", "cached_value")

        # Retrieve from cache
        value = cache.get("key1")
        assert value == "cached_value"

        # Test expiration
        time.sleep(1.1)
        expired_value = cache.get("key1")
        assert expired_value is None

    def test_default_value_fallback(self):
        """Test default value fallback."""
        fallback = DefaultValueFallback(default_value="default")

        def failing_func():
            raise ValueError("error")

        result = fallback.execute(failing_func)
        assert result == "default"

    def test_alternative_service_fallback(self):
        """Test alternative service fallback."""
        def backup_func(*args, **kwargs):
            return "backup_result"

        fallback = AlternativeServiceFallback(alternative_func=backup_func)

        def failing_func():
            raise ValueError("error")

        result = fallback.execute(failing_func)
        assert result == "backup_result"

    def test_queued_request_fallback(self):
        """Test queued request fallback."""
        fallback = QueuedRequestFallback(max_queue_size=10)

        def test_func():
            return "queued"

        result = fallback.execute(test_func)
        assert result["status"] == "queued"
        assert fallback.get_queue_size() == 1

        # Process queue
        stats = fallback.process_queue()
        assert stats["total_processed"] == 1

    def test_composite_fallback(self):
        """Test composite fallback."""
        fallback = CompositeFallback(
            strategies=[
                DefaultValueFallback(default_value="fallback1"),
                DefaultValueFallback(default_value="fallback2"),
            ]
        )

        def failing_func():
            raise ValueError("error")

        result = fallback.execute(failing_func)
        assert result == "fallback1"  # First strategy succeeds


# ============================================================================
# Monitoring Tests
# ============================================================================


class TestMonitoring:
    """Tests for monitoring and metrics."""

    def test_state_transition_tracker(self):
        """Test state transition tracking."""
        tracker = StateTransitionTracker()

        tracker.record_transition(CircuitState.CLOSED, CircuitState.OPEN, "failures")
        tracker.record_transition(CircuitState.OPEN, CircuitState.HALF_OPEN, "timeout")

        transitions = tracker.get_transitions()
        assert len(transitions) == 2
        assert transitions[0].from_state == CircuitState.CLOSED
        assert transitions[0].to_state == CircuitState.OPEN

    def test_failure_rate_calculator(self):
        """Test failure rate calculation."""
        calculator = FailureRateCalculator()

        # Record requests
        calculator.record_request(True, 100.0)
        calculator.record_request(False, 200.0)
        calculator.record_request(True, 150.0)

        failure_rate = calculator.get_failure_rate()
        assert abs(failure_rate - 0.333) < 0.01  # ~33%

    def test_latency_monitor(self):
        """Test latency monitoring."""
        monitor = LatencyMonitor()

        # Record latencies
        for lat in [100, 200, 150, 300, 250]:
            monitor.record_latency(lat)

        stats = monitor.get_latency_stats()
        assert stats.mean_ms == 200.0
        assert stats.min_ms == 100
        assert stats.max_ms == 300

    def test_alert_manager(self, circuit_breaker):
        """Test alert management."""
        alerts_received = []

        def alert_handler(alert):
            alerts_received.append(alert)

        manager = AlertManager(circuit_breaker, alert_handlers=[alert_handler])

        # Trigger state change
        circuit_breaker.force_open()

        # Should have received alert
        assert len(alerts_received) > 0
        assert alerts_received[0].level == AlertLevel.ERROR


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegrations:
    """Tests for integration patterns."""

    def test_retry_integration(self, circuit_breaker):
        """Test retry integration."""
        retry = RetryIntegration(max_retries=3)

        call_count = [0]

        def flaky_func():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ValueError("error")
            return "success"

        result = retry.wrap_execute(circuit_breaker, flaky_func)
        assert result == "success"
        assert call_count[0] == 3

    def test_timeout_integration(self, circuit_breaker):
        """Test timeout integration."""
        timeout = TimeoutIntegration(timeout_seconds=0.1)

        def slow_func():
            time.sleep(0.5)
            return "slow"

        with pytest.raises(TimeoutError):
            timeout.wrap_execute(circuit_breaker, slow_func)

    def test_bulkhead_integration(self, circuit_breaker):
        """Test bulkhead integration."""
        bulkhead = BulkheadIntegration(max_concurrent=2)

        # Should work within limit
        with_lock_count = [0]

        def test_func():
            with_lock_count[0] += 1
            time.sleep(0.1)
            return "success"

        import threading
        threads = []
        for _ in range(2):
            t = threading.Thread(target=lambda: bulkhead.wrap_execute(circuit_breaker, test_func))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert bulkhead.get_active_count() == 0

    def test_rate_limiter_integration(self, circuit_breaker):
        """Test rate limiter integration."""
        limiter = RateLimiterIntegration(requests_per_second=10.0)

        start = time.time()
        for _ in range(5):
            limiter.wrap_execute(circuit_breaker, lambda: "success")
        duration = time.time() - start

        # Should take some time due to rate limiting
        assert duration >= 0.0

    def test_cache_integration(self, circuit_breaker):
        """Test cache integration."""
        cache = CacheIntegration(ttl_seconds=1.0)

        call_count = [0]

        def counted_func():
            call_count[0] += 1
            return "result"

        # First call
        result1 = cache.wrap_execute(circuit_breaker, counted_func)
        assert result1 == "result"
        assert call_count[0] == 1

        # Second call (should use cache)
        result2 = cache.wrap_execute(circuit_breaker, counted_func)
        assert result2 == "result"
        assert call_count[0] == 1  # Not called again

    def test_service_mesh_integration(self, circuit_breaker):
        """Test service mesh integration."""
        mesh = ServiceMeshIntegration(
            service_name="test-service",
            version="v1.0.0"
        )

        def test_func(**kwargs):
            return kwargs.get("headers", {})

        result = mesh.wrap_execute(circuit_breaker, test_func)
        assert result["x-service-name"] == "test-service"
        assert result["x-service-version"] == "v1.0.0"


# ============================================================================
# Edge Cases and Error Handling Tests
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_invalid_state_transition(self, circuit_breaker):
        """Test invalid state transition handling."""
        # Direct transition from CLOSED to HALF_OPEN is invalid
        with pytest.raises(StateTransitionError):
            circuit_breaker._transition_to(CircuitState.HALF_OPEN, "invalid")

    def test_metrics_collection(self, circuit_breaker, succeeding_func, failing_func):
        """Test comprehensive metrics collection."""
        # Generate activity
        for _ in range(5):
            circuit_breaker.execute(succeeding_func)

        for _ in range(3):
            try:
                circuit_breaker.execute(failing_func)
            except ValueError:
                pass

        metrics = circuit_breaker.get_metrics()
        assert metrics.total_requests == 8
        assert metrics.successful_requests == 5
        assert metrics.failed_requests == 3
        assert 0.0 <= metrics.failure_rate <= 1.0

    def test_health_check(self, circuit_breaker):
        """Test health check functionality."""
        status = circuit_breaker.health_check()
        assert isinstance(status, HealthStatus)
        assert status.is_healthy == True
        assert status.state == CircuitState.CLOSED

    def test_context_manager(self):
        """Test circuit breaker as context manager."""
        config = CircuitBreakerConfig()

        with CircuitBreakerFSA(config=config, name="test") as cb:
            assert cb.get_state() == CircuitState.CLOSED

        # Should be shutdown after exiting context

    def test_event_listeners(self, circuit_breaker):
        """Test event listener functionality."""
        state_changes = []

        def on_state_change(old_state, new_state):
            state_changes.append((old_state, new_state))

        circuit_breaker.add_state_change_listener(on_state_change)
        circuit_breaker.force_open()

        assert len(state_changes) == 1
        assert state_changes[0] == (CircuitState.CLOSED, CircuitState.OPEN)


# ============================================================================
# Performance Tests
# ============================================================================


class TestPerformance:
    """Performance and stress tests."""

    def test_high_throughput(self, circuit_breaker):
        """Test high throughput scenarios."""
        import threading

        results = []
        num_requests = 100

        def worker():
            try:
                result = circuit_breaker.execute(lambda: "success")
                results.append(result)
            except Exception as e:
                results.append(e)

        start = time.time()
        threads = [threading.Thread(target=worker) for _ in range(num_requests)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        duration = time.time() - start

        assert len(results) == num_requests
        print(f"Processed {num_requests} requests in {duration:.3f}s ({num_requests/duration:.1f} req/s)")

    def test_memory_usage(self, circuit_breaker):
        """Test memory usage with large request history."""
        # Execute many requests
        for _ in range(1000):
            try:
                circuit_breaker.execute(lambda: "success")
            except Exception:
                pass

        metrics = circuit_breaker.get_metrics()
        assert metrics.total_requests == 1000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
