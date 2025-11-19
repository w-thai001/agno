"""Unit tests for RetryHandler FSA."""

import asyncio
import time
from typing import List

import pytest

from agno.fsa import (
    CircuitBreakerOpen,
    CircuitState,
    RetryConfig,
    RetryHandler,
    retry,
    retry_async,
)


class CustomError(Exception):
    """Custom exception for testing."""

    pass


class NonRetryableError(Exception):
    """Exception that should not be retried."""

    pass


def test_retry_config_defaults():
    """Test RetryConfig default values."""
    config = RetryConfig()
    assert config.max_retries == 3
    assert config.initial_delay == 1.0
    assert config.max_delay == 60.0
    assert config.exponential_base == 2.0
    assert config.jitter is True
    assert config.retry_on_exceptions == (Exception,)
    assert config.circuit_breaker_enabled is False


def test_retry_handler_initialization():
    """Test RetryHandler initialization."""
    handler = RetryHandler(name="TestHandler")
    assert handler.name == "TestHandler"
    assert handler.circuit_state == CircuitState.CLOSED
    assert handler.stats.total_attempts == 0


def test_successful_execution_first_try():
    """Test successful execution on first attempt."""
    handler = RetryHandler()
    call_count = [0]

    def successful_func():
        call_count[0] += 1
        return "success"

    result = handler.execute(successful_func)
    assert result == "success"
    assert call_count[0] == 1
    assert handler.stats.total_attempts == 1
    assert handler.stats.successful_attempts == 1
    assert handler.stats.failed_attempts == 0


def test_retry_on_failure():
    """Test retry behavior on failures."""
    config = RetryConfig(max_retries=2, initial_delay=0.01, jitter=False)
    handler = RetryHandler(config=config)
    call_count = [0]

    def failing_then_success():
        call_count[0] += 1
        if call_count[0] < 3:
            raise CustomError("Temporary failure")
        return "success"

    result = handler.execute(failing_then_success)
    assert result == "success"
    assert call_count[0] == 3  # Failed twice, succeeded on third
    assert handler.stats.total_attempts == 3
    assert handler.stats.successful_attempts == 1


def test_max_retries_exceeded():
    """Test behavior when max retries is exceeded."""
    config = RetryConfig(max_retries=2, initial_delay=0.01, jitter=False)
    handler = RetryHandler(config=config)
    call_count = [0]

    def always_fails():
        call_count[0] += 1
        raise CustomError("Always fails")

    with pytest.raises(CustomError):
        handler.execute(always_fails)

    assert call_count[0] == 3  # Initial + 2 retries
    assert handler.stats.total_attempts == 3
    assert handler.stats.failed_attempts == 3


def test_exponential_backoff():
    """Test exponential backoff calculation."""
    config = RetryConfig(
        max_retries=3,
        initial_delay=0.1,
        exponential_base=2.0,
        jitter=False
    )
    handler = RetryHandler(config=config)

    # Test delay calculation
    delay0 = handler._calculate_delay(0)
    delay1 = handler._calculate_delay(1)
    delay2 = handler._calculate_delay(2)

    assert delay0 == 0.1  # 0.1 * 2^0
    assert delay1 == 0.2  # 0.1 * 2^1
    assert delay2 == 0.4  # 0.1 * 2^2


def test_max_delay_cap():
    """Test that delay is capped at max_delay."""
    config = RetryConfig(
        initial_delay=10.0,
        max_delay=5.0,
        exponential_base=2.0,
        jitter=False
    )
    handler = RetryHandler(config=config)

    # Large attempt number should still be capped
    delay = handler._calculate_delay(10)
    assert delay == 5.0


def test_jitter_adds_randomness():
    """Test that jitter adds randomness to delays."""
    config = RetryConfig(
        initial_delay=1.0,
        exponential_base=2.0,
        jitter=True
    )
    handler = RetryHandler(config=config)

    # Generate multiple delays and check they vary
    delays = [handler._calculate_delay(1) for _ in range(10)]
    # With jitter, delays should vary (not all the same)
    assert len(set(delays)) > 1
    # All delays should be between 0 and expected max
    assert all(0 <= d <= 2.0 for d in delays)


def test_retry_on_specific_exceptions():
    """Test retrying only on specific exception types."""
    config = RetryConfig(
        max_retries=2,
        initial_delay=0.01,
        retry_on_exceptions=(CustomError,)
    )
    handler = RetryHandler(config=config)
    call_count = [0]

    def raises_non_retryable():
        call_count[0] += 1
        raise NonRetryableError("Should not retry")

    # Should fail immediately without retries
    with pytest.raises(NonRetryableError):
        handler.execute(raises_non_retryable)

    assert call_count[0] == 1  # No retries
    assert handler.stats.total_attempts == 1


@pytest.mark.asyncio
async def test_async_execution_success():
    """Test async execution with success."""
    handler = RetryHandler()
    call_count = [0]

    async def async_successful():
        call_count[0] += 1
        await asyncio.sleep(0.01)
        return "async success"

    result = await handler.execute_async(async_successful)
    assert result == "async success"
    assert call_count[0] == 1


@pytest.mark.asyncio
async def test_async_retry_on_failure():
    """Test async retry behavior."""
    config = RetryConfig(max_retries=2, initial_delay=0.01, jitter=False)
    handler = RetryHandler(config=config)
    call_count = [0]

    async def async_failing_then_success():
        call_count[0] += 1
        await asyncio.sleep(0.01)
        if call_count[0] < 3:
            raise CustomError("Temporary async failure")
        return "async success"

    result = await handler.execute_async(async_failing_then_success)
    assert result == "async success"
    assert call_count[0] == 3


def test_circuit_breaker_opens_after_failures():
    """Test circuit breaker opens after threshold failures."""
    config = RetryConfig(
        max_retries=0,  # Fail immediately
        circuit_breaker_enabled=True,
        failure_threshold=3
    )
    handler = RetryHandler(config=config)

    def always_fails():
        raise CustomError("Fail")

    # Fail 3 times to trigger circuit breaker
    for i in range(3):
        with pytest.raises(CustomError):
            handler.execute(always_fails)

    # Circuit should now be open
    assert handler.circuit_state == CircuitState.OPEN
    assert handler.stats.circuit_opens == 1

    # Next call should fail with CircuitBreakerOpen
    with pytest.raises(CircuitBreakerOpen):
        handler.execute(always_fails)


def test_circuit_breaker_half_open_transition():
    """Test circuit breaker transitions to half-open after timeout."""
    config = RetryConfig(
        max_retries=0,
        circuit_breaker_enabled=True,
        failure_threshold=2,
        timeout=0.1  # Very short timeout for testing
    )
    handler = RetryHandler(config=config)

    def always_fails():
        raise CustomError("Fail")

    # Open the circuit
    for _ in range(2):
        with pytest.raises(CustomError):
            handler.execute(always_fails)

    assert handler.circuit_state == CircuitState.OPEN

    # Wait for timeout
    time.sleep(0.15)

    # Circuit should now be half-open
    assert handler.circuit_state == CircuitState.HALF_OPEN


def test_circuit_breaker_closes_after_success_threshold():
    """Test circuit breaker closes after success threshold in half-open."""
    config = RetryConfig(
        max_retries=0,
        circuit_breaker_enabled=True,
        failure_threshold=2,
        success_threshold=2,
        timeout=0.1
    )
    handler = RetryHandler(config=config)
    call_count = [0]

    def conditional_func():
        call_count[0] += 1
        if call_count[0] <= 2:
            raise CustomError("Initial failures")
        return "success"

    # Open circuit
    for _ in range(2):
        with pytest.raises(CustomError):
            handler.execute(conditional_func)

    assert handler.circuit_state == CircuitState.OPEN

    # Wait for half-open
    time.sleep(0.15)
    assert handler.circuit_state == CircuitState.HALF_OPEN

    # Two successes should close circuit
    handler.execute(conditional_func)
    handler.execute(conditional_func)

    assert handler.circuit_state == CircuitState.CLOSED


def test_circuit_breaker_reopens_on_half_open_failure():
    """Test circuit reopens if failure occurs in half-open state."""
    config = RetryConfig(
        max_retries=0,
        circuit_breaker_enabled=True,
        failure_threshold=2,
        timeout=0.1
    )
    handler = RetryHandler(config=config)

    def always_fails():
        raise CustomError("Fail")

    # Open circuit
    for _ in range(2):
        with pytest.raises(CustomError):
            handler.execute(always_fails)

    # Wait for half-open
    time.sleep(0.15)
    assert handler.circuit_state == CircuitState.HALF_OPEN

    # Failure in half-open should reopen circuit
    with pytest.raises(CustomError):
        handler.execute(always_fails)

    assert handler.circuit_state == CircuitState.OPEN


def test_retry_decorator_sync():
    """Test retry decorator for sync functions."""
    call_count = [0]

    @retry(max_retries=2, initial_delay=0.01, jitter=False)
    def decorated_func():
        call_count[0] += 1
        if call_count[0] < 2:
            raise CustomError("Temporary")
        return "decorated success"

    result = decorated_func()
    assert result == "decorated success"
    assert call_count[0] == 2


@pytest.mark.asyncio
async def test_retry_decorator_async():
    """Test retry decorator for async functions."""
    call_count = [0]

    @retry_async(max_retries=2, initial_delay=0.01, jitter=False)
    async def decorated_async():
        call_count[0] += 1
        await asyncio.sleep(0.01)
        if call_count[0] < 2:
            raise CustomError("Temporary")
        return "async decorated success"

    result = await decorated_async()
    assert result == "async decorated success"
    assert call_count[0] == 2


def test_retry_stats_tracking():
    """Test statistics tracking."""
    config = RetryConfig(max_retries=3, initial_delay=0.01, jitter=False)
    handler = RetryHandler(config=config)
    call_count = [0]

    def mixed_results():
        call_count[0] += 1
        if call_count[0] < 3:
            raise CustomError("Fail")
        return "success"

    handler.execute(mixed_results)

    stats = handler.get_stats()
    assert stats.total_attempts == 3
    assert stats.successful_attempts == 1
    assert stats.failed_attempts == 2
    assert stats.total_delay > 0


def test_reset_handler():
    """Test resetting handler state."""
    config = RetryConfig(max_retries=0, initial_delay=0.01)
    handler = RetryHandler(config=config)

    def fails():
        raise CustomError("Fail")

    # Execute and fail
    with pytest.raises(CustomError):
        handler.execute(fails)

    assert handler.stats.total_attempts == 1
    assert handler.stats.failed_attempts == 1

    # Reset
    handler.reset()

    assert handler.stats.total_attempts == 0
    assert handler.stats.failed_attempts == 0
    assert handler.circuit_state == CircuitState.CLOSED


def test_circuit_breaker_disabled_by_default():
    """Test that circuit breaker is disabled by default."""
    handler = RetryHandler()

    def always_fails():
        raise CustomError("Fail")

    # Should never open circuit with default config
    for _ in range(10):
        with pytest.raises(CustomError):
            handler.execute(always_fails)

    assert handler.circuit_state == CircuitState.CLOSED


def test_sync_function_with_async_execute():
    """Test that sync functions work with execute_async."""
    handler = RetryHandler()
    call_count = [0]

    def sync_func():
        call_count[0] += 1
        return "sync result"

    async def test_wrapper():
        result = await handler.execute_async(sync_func)
        return result

    result = asyncio.run(test_wrapper())
    assert result == "sync result"
    assert call_count[0] == 1


def test_delay_accumulation_in_stats():
    """Test that total delay is tracked in stats."""
    config = RetryConfig(max_retries=2, initial_delay=0.05, jitter=False)
    handler = RetryHandler(config=config)
    call_count = [0]

    def fails_twice():
        call_count[0] += 1
        if call_count[0] < 3:
            raise CustomError("Fail")
        return "success"

    start_time = time.time()
    handler.execute(fails_twice)
    elapsed = time.time() - start_time

    # Should have delayed approximately: 0.05 + 0.1 = 0.15 seconds
    assert handler.stats.total_delay >= 0.1
    assert elapsed >= 0.1


def test_multiple_exception_types():
    """Test retrying on multiple exception types."""
    config = RetryConfig(
        max_retries=2,
        initial_delay=0.01,
        retry_on_exceptions=(CustomError, ValueError)
    )
    handler = RetryHandler(config=config)
    call_count = [0]

    def raises_different_exceptions():
        call_count[0] += 1
        if call_count[0] == 1:
            raise CustomError("First")
        elif call_count[0] == 2:
            raise ValueError("Second")
        return "success"

    result = handler.execute(raises_different_exceptions)
    assert result == "success"
    assert call_count[0] == 3


def test_circuit_breaker_success_resets_failure_count():
    """Test that success in closed state resets failure count."""
    config = RetryConfig(
        max_retries=0,
        circuit_breaker_enabled=True,
        failure_threshold=3
    )
    handler = RetryHandler(config=config)
    call_count = [0]

    def conditional():
        call_count[0] += 1
        if call_count[0] in [1, 2]:
            raise CustomError("Fail")
        return "success"

    # Two failures
    for _ in range(2):
        with pytest.raises(CustomError):
            handler.execute(conditional)

    assert handler._failure_count == 2

    # One success should reset count
    handler.execute(conditional)
    assert handler._failure_count == 0
    assert handler.circuit_state == CircuitState.CLOSED
