"""
Unit tests for Circuit Breaker FSA

Tests cover:
- State machine transitions (CLOSED → OPEN → HALF_OPEN → CLOSED)
- Failure detection policies
- Timeout and recovery behavior
- Bulkhead isolation
- Metrics collection
- Thread safety
- Edge cases
"""

import pytest
import asyncio
import time
import threading
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from agno.resilience import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    CircuitBreakerOpenError,
    BulkheadFullError,
    ConsecutiveFailurePolicy,
    FailureRatePolicy,
    TimeoutPolicy,
)


class TestCircuitBreakerStateTransitions:
    """Test state machine transitions"""

    def test_initial_state_is_closed(self):
        """Circuit breaker should start in CLOSED state"""
        cb = CircuitBreaker(name="test", config=CircuitBreakerConfig(failure_threshold=3))
        assert cb.get_state() == CircuitState.CLOSED

    def test_closed_to_open_on_consecutive_failures(self):
        """Should transition to OPEN after consecutive failures"""
        cb = CircuitBreaker(
            name="test",
            config=CircuitBreakerConfig(
                failure_threshold=3,
                failure_policy=ConsecutiveFailurePolicy(threshold=3)
            )
        )

        # Simulate 3 consecutive failures
        for i in range(3):
            try:
                cb.call(lambda: self._failing_function())
            except Exception:
                pass

        assert cb.get_state() == CircuitState.OPEN

    def test_open_rejects_requests(self):
        """OPEN circuit should reject requests immediately"""
        cb = CircuitBreaker(
            name="test",
            config=CircuitBreakerConfig(failure_threshold=2)
        )

        # Cause circuit to open
        for i in range(2):
            try:
                cb.call(lambda: self._failing_function())
            except Exception:
                pass

        # Next request should be rejected
        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            cb.call(lambda: "success")

        assert exc_info.value.circuit_name == "test"

    def test_open_to_half_open_after_timeout(self):
        """Should transition to HALF_OPEN after recovery timeout"""
        cb = CircuitBreaker(
            name="test",
            config=CircuitBreakerConfig(
                failure_threshold=2,
                recovery_timeout=0.1,  # 100ms
                timeout_policy=TimeoutPolicy(open_timeout_seconds=0.1)
            )
        )

        # Open the circuit
        for i in range(2):
            try:
                cb.call(lambda: self._failing_function())
            except Exception:
                pass

        assert cb.get_state() == CircuitState.OPEN

        # Wait for timeout
        time.sleep(0.15)

        # Next request should trigger transition to HALF_OPEN
        try:
            cb.call(lambda: "success")
        except CircuitBreakerOpenError:
            pass  # May still reject first attempt

        # Circuit should now be HALF_OPEN
        assert cb.get_state() == CircuitState.HALF_OPEN

    def test_half_open_to_closed_on_success(self):
        """Should transition to CLOSED after successful requests in HALF_OPEN"""
        cb = CircuitBreaker(
            name="test",
            config=CircuitBreakerConfig(
                failure_threshold=2,
                success_threshold=2,
                recovery_timeout=0.1,
                half_open_max_calls=3,
                timeout_policy=TimeoutPolicy(open_timeout_seconds=0.1)
            )
        )

        # Open the circuit
        for i in range(2):
            try:
                cb.call(lambda: self._failing_function())
            except Exception:
                pass

        # Wait and transition to HALF_OPEN
        time.sleep(0.15)

        # Make successful requests
        for i in range(3):
            result = cb.call(lambda: "success")
            assert result == "success"

        # Should be closed now
        assert cb.get_state() == CircuitState.CLOSED

    def test_half_open_to_open_on_failure(self):
        """Should transition back to OPEN if failure occurs in HALF_OPEN"""
        cb = CircuitBreaker(
            name="test",
            config=CircuitBreakerConfig(
                failure_threshold=2,
                recovery_timeout=0.1,
                half_open_max_calls=3,
                timeout_policy=TimeoutPolicy(open_timeout_seconds=0.1)
            )
        )

        # Open the circuit
        for i in range(2):
            try:
                cb.call(lambda: self._failing_function())
            except Exception:
                pass

        # Wait and transition to HALF_OPEN
        time.sleep(0.15)

        # Make one successful request
        result = cb.call(lambda: "success")

        # Then a failure
        try:
            cb.call(lambda: self._failing_function())
        except Exception:
            pass

        # Should be OPEN again
        assert cb.get_state() == CircuitState.OPEN

    @staticmethod
    def _failing_function():
        raise Exception("Simulated failure")


class TestFailurePolicies:
    """Test different failure detection policies"""

    def test_consecutive_failure_policy(self):
        """Test consecutive failure policy"""
        cb = CircuitBreaker(
            name="test",
            config=CircuitBreakerConfig(
                failure_policy=ConsecutiveFailurePolicy(threshold=5)
            )
        )

        # 4 failures should not open circuit
        for i in range(4):
            try:
                cb.call(lambda: self._fail())
            except Exception:
                pass

        assert cb.get_state() == CircuitState.CLOSED

        # 5th failure should open it
        try:
            cb.call(lambda: self._fail())
        except Exception:
            pass

        assert cb.get_state() == CircuitState.OPEN

    def test_failure_rate_policy(self):
        """Test failure rate policy"""
        cb = CircuitBreaker(
            name="test",
            config=CircuitBreakerConfig(
                failure_policy=FailureRatePolicy(
                    threshold=0.5,  # 50%
                    window_seconds=60,
                    minimum_requests=10
                )
            )
        )

        # Mix of successes and failures (6 failures, 4 successes = 60% failure rate)
        for i in range(10):
            try:
                if i < 6:
                    cb.call(lambda: self._fail())
                else:
                    cb.call(lambda: "success")
            except Exception:
                pass

        # Should be open due to high failure rate
        assert cb.get_state() == CircuitState.OPEN

    @staticmethod
    def _fail():
        raise Exception("Failure")


class TestBulkheadIsolation:
    """Test bulkhead pattern"""

    def test_bulkhead_limits_concurrent_requests(self):
        """Bulkhead should limit concurrent requests"""
        cb = CircuitBreaker(
            name="test",
            config=CircuitBreakerConfig(max_concurrent_calls=2)
        )

        results = []

        def slow_function():
            time.sleep(0.1)
            return "success"

        # Start 3 concurrent requests
        threads = []
        for i in range(3):
            def worker():
                try:
                    result = cb.call(slow_function)
                    results.append(result)
                except BulkheadFullError:
                    results.append("rejected")

            t = threading.Thread(target=worker)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # At least one should be rejected
        assert "rejected" in results

    def test_bulkhead_releases_on_completion(self):
        """Bulkhead should release slots when requests complete"""
        cb = CircuitBreaker(
            name="test",
            config=CircuitBreakerConfig(max_concurrent_calls=1)
        )

        # First request
        result1 = cb.call(lambda: "success1")
        assert result1 == "success1"

        # Second request should succeed (first completed)
        result2 = cb.call(lambda: "success2")
        assert result2 == "success2"


class TestMetrics:
    """Test metrics collection"""

    def test_metrics_track_requests(self):
        """Metrics should track all requests"""
        cb = CircuitBreaker(
            name="test",
            config=CircuitBreakerConfig(enable_metrics=True)
        )

        # Make requests
        for i in range(5):
            try:
                if i < 3:
                    cb.call(lambda: "success")
                else:
                    cb.call(lambda: self._fail())
            except Exception:
                pass

        metrics = cb.get_metrics()
        assert metrics is not None
        assert metrics.total_requests == 5
        assert metrics.successful_requests == 3
        assert metrics.failed_requests == 2

    def test_metrics_track_state_transitions(self):
        """Metrics should track state transitions"""
        cb = CircuitBreaker(
            name="test",
            config=CircuitBreakerConfig(
                failure_threshold=3,
                enable_metrics=True
            )
        )

        # Open the circuit
        for i in range(3):
            try:
                cb.call(lambda: self._fail())
            except Exception:
                pass

        metrics = cb.get_metrics()
        assert metrics.times_opened >= 1
        assert metrics.current_state == CircuitState.OPEN

    @staticmethod
    def _fail():
        raise Exception("Failure")


class TestAsyncSupport:
    """Test async/await support"""

    @pytest.mark.asyncio
    async def test_async_call_success(self):
        """Should support async function calls"""
        cb = CircuitBreaker(name="test")

        async def async_func():
            await asyncio.sleep(0.01)
            return "async_success"

        result = await cb.call_async(async_func)
        assert result == "async_success"

    @pytest.mark.asyncio
    async def test_async_call_failure(self):
        """Should handle async failures"""
        cb = CircuitBreaker(
            name="test",
            config=CircuitBreakerConfig(failure_threshold=2)
        )

        async def async_fail():
            raise Exception("Async failure")

        # Cause failures
        for i in range(2):
            with pytest.raises(Exception):
                await cb.call_async(async_fail)

        # Circuit should be open
        assert cb.get_state() == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_async_circuit_open_rejection(self):
        """Open circuit should reject async requests"""
        cb = CircuitBreaker(
            name="test",
            config=CircuitBreakerConfig(failure_threshold=1)
        )

        async def async_fail():
            raise Exception("Failure")

        # Open the circuit
        with pytest.raises(Exception):
            await cb.call_async(async_fail)

        # Should reject next request
        with pytest.raises(CircuitBreakerOpenError):
            await cb.call_async(async lambda: "success")


class TestFallbackBehavior:
    """Test fallback function execution"""

    def test_fallback_on_circuit_open(self):
        """Should execute fallback when circuit is open"""
        fallback_called = []

        def fallback(*args, **kwargs):
            fallback_called.append(True)
            return "fallback_result"

        cb = CircuitBreaker(
            name="test",
            config=CircuitBreakerConfig(
                failure_threshold=2,
                fallback_function=fallback
            )
        )

        # Open the circuit
        for i in range(2):
            try:
                cb.call(lambda: self._fail())
            except Exception:
                pass

        # Next call should use fallback
        result = cb.call(lambda: "normal")
        assert result == "fallback_result"
        assert fallback_called

    @staticmethod
    def _fail():
        raise Exception("Failure")


class TestManualControl:
    """Test manual circuit control"""

    def test_force_open(self):
        """Should allow manually forcing circuit open"""
        cb = CircuitBreaker(name="test")

        assert cb.get_state() == CircuitState.CLOSED

        cb.force_open()
        assert cb.get_state() == CircuitState.OPEN

    def test_force_close(self):
        """Should allow manually forcing circuit closed"""
        cb = CircuitBreaker(
            name="test",
            config=CircuitBreakerConfig(failure_threshold=2)
        )

        # Open the circuit
        for i in range(2):
            try:
                cb.call(lambda: self._fail())
            except Exception:
                pass

        assert cb.get_state() == CircuitState.OPEN

        cb.force_close()
        assert cb.get_state() == CircuitState.CLOSED

    def test_reset(self):
        """Should reset circuit to initial state"""
        cb = CircuitBreaker(
            name="test",
            config=CircuitBreakerConfig(failure_threshold=2)
        )

        # Open the circuit
        for i in range(2):
            try:
                cb.call(lambda: self._fail())
            except Exception:
                pass

        cb.reset()
        assert cb.get_state() == CircuitState.CLOSED

        state_data = cb.get_state_data()
        assert state_data['failure_count'] == 0
        assert state_data['success_count'] == 0

    @staticmethod
    def _fail():
        raise Exception("Failure")


class TestEdgeCases:
    """Test edge cases and error conditions"""

    def test_zero_threshold(self):
        """Should handle edge case of very low threshold"""
        cb = CircuitBreaker(
            name="test",
            config=CircuitBreakerConfig(failure_threshold=1)
        )

        # Single failure should open circuit
        try:
            cb.call(lambda: self._fail())
        except Exception:
            pass

        assert cb.get_state() == CircuitState.OPEN

    def test_very_high_threshold(self):
        """Should handle very high failure threshold"""
        cb = CircuitBreaker(
            name="test",
            config=CircuitBreakerConfig(failure_threshold=1000)
        )

        # Many failures should not open circuit
        for i in range(100):
            try:
                cb.call(lambda: self._fail())
            except Exception:
                pass

        assert cb.get_state() == CircuitState.CLOSED

    def test_mixed_success_and_failure(self):
        """Should handle intermittent failures correctly"""
        cb = CircuitBreaker(
            name="test",
            config=CircuitBreakerConfig(
                failure_policy=ConsecutiveFailurePolicy(threshold=3)
            )
        )

        # Alternating success and failure
        for i in range(10):
            try:
                if i % 2 == 0:
                    cb.call(lambda: "success")
                else:
                    cb.call(lambda: self._fail())
            except Exception:
                pass

        # Should remain closed (no 3 consecutive failures)
        assert cb.get_state() == CircuitState.CLOSED

    @staticmethod
    def _fail():
        raise Exception("Failure")


class TestStateHooks:
    """Test state transition hooks"""

    def test_on_open_hook(self):
        """Should call hook when circuit opens"""
        hook_called = []

        def on_open(state):
            hook_called.append(True)

        cb = CircuitBreaker(
            name="test",
            config=CircuitBreakerConfig(
                failure_threshold=2,
                on_open=on_open
            )
        )

        # Open the circuit
        for i in range(2):
            try:
                cb.call(lambda: self._fail())
            except Exception:
                pass

        assert hook_called

    def test_on_close_hook(self):
        """Should call hook when circuit closes"""
        hook_called = []

        def on_close(state):
            hook_called.append(True)

        cb = CircuitBreaker(
            name="test",
            config=CircuitBreakerConfig(
                failure_threshold=2,
                recovery_timeout=0.1,
                on_close=on_close,
                timeout_policy=TimeoutPolicy(open_timeout_seconds=0.1)
            )
        )

        # Open the circuit
        for i in range(2):
            try:
                cb.call(lambda: self._fail())
            except Exception:
                pass

        # Wait and make successful requests
        time.sleep(0.15)
        for i in range(3):
            cb.call(lambda: "success")

        assert hook_called

    @staticmethod
    def _fail():
        raise Exception("Failure")
