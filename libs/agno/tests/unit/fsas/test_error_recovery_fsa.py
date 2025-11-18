"""
Comprehensive unit tests for Error Recovery FSA.

Tests cover:
- Basic error detection and classification
- Recovery strategy selection
- Retry logic with exponential backoff
- Circuit breaker behavior
- State rollback scenarios
- Multiple error type handling
- Edge cases (unrecoverable errors, timeout scenarios)
- Meta error handling (errors in the error handler itself)
- Analytics and health monitoring
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from agno.fsas.error_recovery_fsa import (
    ErrorRecoveryFSA,
    ErrorCategory,
    RecoveryStrategy,
    RecoveryStrategyType,
    RecoveryResult,
    OperationContext,
    ErrorState,
    ValidationResult,
    StateCheckpoint,
    RollbackResult,
    HealthStatus,
    FailureAnalytics,
    CircuitBreaker,
    FSAState,
)
from agno.exceptions import ModelProviderError, ModelRateLimitError, AgnoError


class TestErrorDetectionAndClassification:
    """Test error detection and classification functionality."""

    def test_detect_rate_limit_error(self):
        """Test detection of rate limit errors."""
        fsa = ErrorRecoveryFSA()

        # Test with ModelRateLimitError
        error = ModelRateLimitError("Rate limit exceeded", model_name="gpt-4")
        category = fsa.detect_error_type(error)
        assert category == ErrorCategory.RATE_LIMIT

        # Test with string-based detection
        error = Exception("429 Too Many Requests - rate limit exceeded")
        category = fsa.detect_error_type(error)
        assert category == ErrorCategory.RATE_LIMIT

    def test_detect_network_error(self):
        """Test detection of network errors."""
        fsa = ErrorRecoveryFSA()

        error = ConnectionError("Network connection failed")
        category = fsa.detect_error_type(error)
        assert category == ErrorCategory.NETWORK

        error = Exception("DNS resolution failed")
        category = fsa.detect_error_type(error)
        assert category == ErrorCategory.NETWORK

    def test_detect_timeout_error(self):
        """Test detection of timeout errors."""
        fsa = ErrorRecoveryFSA()

        error = TimeoutError("Operation timed out")
        category = fsa.detect_error_type(error)
        assert category == ErrorCategory.TIMEOUT

        error = Exception("Request deadline exceeded")
        category = fsa.detect_error_type(error)
        assert category == ErrorCategory.TIMEOUT

    def test_detect_authentication_error(self):
        """Test detection of authentication errors."""
        fsa = ErrorRecoveryFSA()

        error = Exception("401 Unauthorized")
        category = fsa.detect_error_type(error)
        assert category == ErrorCategory.AUTHENTICATION

        error = Exception("Authentication failed")
        category = fsa.detect_error_type(error)
        assert category == ErrorCategory.AUTHENTICATION

    def test_detect_model_provider_error(self):
        """Test detection of model provider errors."""
        fsa = ErrorRecoveryFSA()

        error = ModelProviderError("Model service unavailable", model_name="claude")
        category = fsa.detect_error_type(error)
        assert category == ErrorCategory.MODEL_ERROR

    def test_detect_unrecoverable_error(self):
        """Test detection of unrecoverable errors."""
        fsa = ErrorRecoveryFSA()

        error = SystemExit(1)
        category = fsa.detect_error_type(error)
        assert category == ErrorCategory.UNRECOVERABLE

        error = KeyboardInterrupt()
        category = fsa.detect_error_type(error)
        assert category == ErrorCategory.UNRECOVERABLE

    def test_detect_unknown_error(self):
        """Test handling of unknown error types."""
        fsa = ErrorRecoveryFSA()

        error = Exception("Some random error")
        category = fsa.detect_error_type(error)
        assert category == ErrorCategory.UNKNOWN


class TestRecoveryStrategySelection:
    """Test recovery strategy selection logic."""

    def test_select_retry_for_transient(self):
        """Test that transient errors get retry strategy."""
        fsa = ErrorRecoveryFSA()
        strategy = fsa.select_recovery_strategy(ErrorCategory.TRANSIENT)
        assert strategy.strategy_type == RecoveryStrategyType.RETRY
        assert strategy.max_attempts == fsa.max_retry_attempts

    def test_select_retry_for_rate_limit(self):
        """Test that rate limit errors get retry with longer backoff."""
        fsa = ErrorRecoveryFSA()
        strategy = fsa.select_recovery_strategy(ErrorCategory.RATE_LIMIT)
        assert strategy.strategy_type == RecoveryStrategyType.RETRY
        assert strategy.backoff_multiplier == 2.0  # Longer backoff

    def test_select_fallback_for_model_error(self):
        """Test that model errors get fallback strategy."""
        fsa = ErrorRecoveryFSA()
        strategy = fsa.select_recovery_strategy(ErrorCategory.MODEL_ERROR)
        assert strategy.strategy_type == RecoveryStrategyType.FALLBACK

    def test_select_rollback_for_state_corruption(self):
        """Test that state corruption gets rollback strategy."""
        fsa = ErrorRecoveryFSA()
        strategy = fsa.select_recovery_strategy(ErrorCategory.STATE_CORRUPTION)
        assert strategy.strategy_type == RecoveryStrategyType.ROLLBACK

    def test_select_escalate_for_unrecoverable(self):
        """Test that unrecoverable errors get escalate strategy."""
        fsa = ErrorRecoveryFSA()
        strategy = fsa.select_recovery_strategy(ErrorCategory.UNRECOVERABLE)
        assert strategy.strategy_type == RecoveryStrategyType.ESCALATE
        assert strategy.max_attempts == 0


class TestRetryLogicWithBackoff:
    """Test retry logic with exponential backoff."""

    def test_retry_with_exponential_backoff(self):
        """Test that retry uses exponential backoff."""
        strategy = RecoveryStrategy(
            strategy_type=RecoveryStrategyType.RETRY,
            backoff_base=2.0,
            backoff_multiplier=1.0,
        )

        # Test backoff calculation
        assert strategy.calculate_backoff(0) == 1.0  # 1.0 * (2.0 ** 0)
        assert strategy.calculate_backoff(1) == 2.0  # 1.0 * (2.0 ** 1)
        assert strategy.calculate_backoff(2) == 4.0  # 1.0 * (2.0 ** 2)
        assert strategy.calculate_backoff(3) == 8.0  # 1.0 * (2.0 ** 3)

    def test_retry_success_on_second_attempt(self):
        """Test successful recovery on retry."""
        fsa = ErrorRecoveryFSA(max_retry_attempts=3)

        # Create a mock operation that fails once then succeeds
        attempt_count = {"count": 0}

        def mock_operation():
            attempt_count["count"] += 1
            if attempt_count["count"] == 1:
                raise Exception("Temporary failure")
            return True

        context = OperationContext(
            operation_id="test-op-1",
            operation_name="test_operation",
            start_time=datetime.now(),
            max_retries=3,
        )

        strategy = RecoveryStrategy(
            strategy_type=RecoveryStrategyType.RETRY,
            max_attempts=3,
            backoff_base=1.1,  # Small backoff for test speed
            backoff_multiplier=0.01,
        )

        # Apply retry strategy
        success = fsa.apply_recovery(strategy, context, mock_operation)
        assert success is True
        assert attempt_count["count"] == 2  # Failed once, succeeded on second

    def test_retry_fails_after_max_attempts(self):
        """Test that retry stops after max attempts."""
        fsa = ErrorRecoveryFSA(max_retry_attempts=2)

        # Create a mock operation that always fails
        attempt_count = {"count": 0}

        def failing_operation():
            attempt_count["count"] += 1
            raise Exception("Persistent failure")

        context = OperationContext(
            operation_id="test-op-2",
            operation_name="failing_operation",
            start_time=datetime.now(),
            max_retries=2,
        )

        strategy = RecoveryStrategy(
            strategy_type=RecoveryStrategyType.RETRY,
            max_attempts=2,
            backoff_base=1.1,
            backoff_multiplier=0.01,
        )

        success = fsa.apply_recovery(strategy, context, failing_operation)
        assert success is False
        assert attempt_count["count"] == 2  # Tried max_attempts times


class TestCircuitBreakerBehavior:
    """Test circuit breaker functionality."""

    def test_circuit_breaker_opens_after_threshold(self):
        """Test that circuit breaker opens after failure threshold."""
        cb = CircuitBreaker(failure_threshold=3, success_threshold=2, timeout=1.0)

        assert cb.state == "closed"
        assert cb.can_attempt() is True

        # Record failures
        cb.record_failure()
        assert cb.state == "closed"
        cb.record_failure()
        assert cb.state == "closed"
        cb.record_failure()
        assert cb.state == "open"
        assert cb.can_attempt() is False

    def test_circuit_breaker_half_open_after_timeout(self):
        """Test that circuit breaker enters half-open state after timeout."""
        cb = CircuitBreaker(failure_threshold=2, success_threshold=2, timeout=0.1)

        # Open the circuit
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "open"

        # Wait for timeout
        time.sleep(0.15)
        assert cb.can_attempt() is True
        assert cb.state == "half_open"

    def test_circuit_breaker_closes_after_successes(self):
        """Test that circuit breaker closes after success threshold in half-open."""
        cb = CircuitBreaker(failure_threshold=2, success_threshold=2, timeout=0.1)

        # Open the circuit
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "open"

        # Wait and enter half-open
        time.sleep(0.15)
        cb.can_attempt()
        assert cb.state == "half_open"

        # Record successes
        cb.record_success()
        assert cb.state == "half_open"
        cb.record_success()
        assert cb.state == "closed"

    def test_circuit_breaker_integration_with_fsa(self):
        """Test circuit breaker integration with FSA."""
        fsa = ErrorRecoveryFSA(circuit_breaker_threshold=2)

        context = OperationContext(
            operation_id="circuit-test",
            operation_name="circuit_test",
            start_time=datetime.now(),
            max_retries=5,
        )

        # Trigger multiple failures to open circuit
        for i in range(3):
            error = Exception(f"Failure {i}")
            result = fsa.execute(error, context)

        # Circuit should now be open
        circuit = fsa._get_circuit_breaker("circuit-test")
        assert circuit.is_open() is True

        # Next error should be blocked by circuit breaker
        error = Exception("Should be blocked")
        result = fsa.execute(error, context)
        assert result.success is False
        assert result.strategy_used == RecoveryStrategyType.CIRCUIT_BREAK


class TestStateRollback:
    """Test state checkpoint and rollback functionality."""

    def test_create_checkpoint(self):
        """Test creating a state checkpoint."""
        fsa = ErrorRecoveryFSA()

        state_data = {"step": 1, "data": "test", "values": [1, 2, 3]}
        checkpoint = fsa.create_checkpoint("op-1", state_data)

        assert checkpoint.operation_id == "op-1"
        assert checkpoint.state_data == state_data
        assert checkpoint.checkpoint_id in fsa.checkpoints

    def test_rollback_to_checkpoint(self):
        """Test rolling back to a checkpoint."""
        fsa = ErrorRecoveryFSA()

        state_data = {"step": 1, "counter": 0}
        checkpoint = fsa.create_checkpoint("op-2", state_data)

        rollback_result = fsa.rollback_state(checkpoint)

        assert rollback_result.success is True
        assert rollback_result.checkpoint_id == checkpoint.checkpoint_id
        assert rollback_result.state_restored == state_data

    def test_rollback_with_context(self):
        """Test rollback strategy with operation context."""
        fsa = ErrorRecoveryFSA()

        # Create context with checkpoint
        context = OperationContext(
            operation_id="rollback-op",
            operation_name="rollback_test",
            start_time=datetime.now(),
        )

        checkpoint = fsa.create_checkpoint("rollback-op", {"state": "initial"})
        context.add_checkpoint(checkpoint)

        # Apply rollback strategy
        strategy = RecoveryStrategy(strategy_type=RecoveryStrategyType.ROLLBACK)
        success = fsa.apply_recovery(strategy, context)

        assert success is True

    def test_rollback_fails_without_checkpoint(self):
        """Test that rollback fails when no checkpoint exists."""
        fsa = ErrorRecoveryFSA()

        context = OperationContext(
            operation_id="no-checkpoint",
            operation_name="no_checkpoint_test",
            start_time=datetime.now(),
        )

        strategy = RecoveryStrategy(strategy_type=RecoveryStrategyType.ROLLBACK)
        success = fsa.apply_recovery(strategy, context)

        assert success is False


class TestMultipleErrorTypes:
    """Test handling of multiple different error types."""

    def test_handle_multiple_error_categories(self):
        """Test that different errors get appropriate strategies."""
        fsa = ErrorRecoveryFSA()

        test_cases = [
            (ConnectionError("Network error"), ErrorCategory.NETWORK, RecoveryStrategyType.RETRY),
            (
                ModelRateLimitError("Rate limited", model_name="gpt-4"),
                ErrorCategory.RATE_LIMIT,
                RecoveryStrategyType.RETRY,
            ),
            (
                ModelProviderError("Provider error", model_name="claude"),
                ErrorCategory.MODEL_ERROR,
                RecoveryStrategyType.FALLBACK,
            ),
            (TimeoutError("Timeout"), ErrorCategory.TIMEOUT, RecoveryStrategyType.RETRY),
            (Exception("State corruption detected"), ErrorCategory.STATE_CORRUPTION, RecoveryStrategyType.ROLLBACK),
        ]

        for error, expected_category, expected_strategy in test_cases:
            category = fsa.detect_error_type(error)
            assert category == expected_category

            strategy = fsa.select_recovery_strategy(category)
            assert strategy.strategy_type == expected_strategy

    def test_sequential_different_errors(self):
        """Test handling sequential errors of different types."""
        fsa = ErrorRecoveryFSA()

        errors = [
            ConnectionError("Network blip"),
            TimeoutError("Request timeout"),
            Exception("Temporary unavailable"),
        ]

        context = OperationContext(
            operation_id="multi-error",
            operation_name="multi_error_test",
            start_time=datetime.now(),
        )

        for error in errors:
            result = fsa.execute(error, context)
            # All these are recoverable errors
            assert result.error_category in [ErrorCategory.NETWORK, ErrorCategory.TIMEOUT, ErrorCategory.TRANSIENT]


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_unrecoverable_error_handling(self):
        """Test handling of unrecoverable errors."""
        fsa = ErrorRecoveryFSA()

        context = OperationContext(
            operation_id="unrecoverable",
            operation_name="unrecoverable_test",
            start_time=datetime.now(),
        )

        error = SystemExit(1)
        result = fsa.execute(error, context)

        assert result.success is False
        assert result.error_category == ErrorCategory.UNRECOVERABLE
        assert result.attempts_made == 0

    def test_max_retries_exceeded(self):
        """Test behavior when max retries are exceeded."""
        fsa = ErrorRecoveryFSA(max_retry_attempts=2)

        context = OperationContext(
            operation_id="max-retries",
            operation_name="max_retries_test",
            start_time=datetime.now(),
            max_retries=2,
            retry_count=2,  # Already at max
        )

        error = ConnectionError("Network error")
        result = fsa.execute(error, context)

        assert result.success is False
        assert "Max retries" in result.message or "not recoverable" in result.message

    def test_timeout_scenario(self):
        """Test timeout error scenario."""
        fsa = ErrorRecoveryFSA()

        context = OperationContext(
            operation_id="timeout-test",
            operation_name="timeout_test",
            start_time=datetime.now(),
            timeout_seconds=1.0,
        )

        error = TimeoutError("Operation timed out after 1 second")
        result = fsa.execute(error, context)

        assert result.error_category == ErrorCategory.TIMEOUT
        # Timeout errors should attempt retry
        assert result.strategy_used == RecoveryStrategyType.RETRY

    def test_empty_context(self):
        """Test handling with minimal context."""
        fsa = ErrorRecoveryFSA()

        context = OperationContext(
            operation_id="minimal",
            operation_name="minimal_test",
            start_time=datetime.now(),
        )

        error = Exception("Simple error")
        result = fsa.execute(error, context)

        # Should still work with minimal context
        assert isinstance(result, RecoveryResult)

    def test_validation_with_circuit_open(self):
        """Test validation when circuit breaker is open."""
        fsa = ErrorRecoveryFSA(circuit_breaker_threshold=1)

        context = OperationContext(
            operation_id="circuit-validation",
            operation_name="circuit_validation",
            start_time=datetime.now(),
        )

        # Open the circuit
        circuit = fsa._get_circuit_breaker("circuit-validation")
        circuit.record_failure()
        circuit.record_failure()

        error_state = ErrorState(
            error=Exception("Test error"),
            category=ErrorCategory.TRANSIENT,
            timestamp=datetime.now(),
            context=context,
            stack_trace="",
        )

        validation = fsa.validate(error_state)

        assert validation.is_recoverable is False
        assert validation.recommended_strategy == RecoveryStrategyType.CIRCUIT_BREAK


class TestMetaErrorHandling:
    """Test error handling for the error handler itself."""

    def test_recovery_process_error_handling(self):
        """Test that errors during recovery are handled gracefully."""
        fsa = ErrorRecoveryFSA()

        # Create a context that might cause issues
        context = OperationContext(
            operation_id="meta-error",
            operation_name="meta_error_test",
            start_time=datetime.now(),
        )

        # Use a complex error that might cause issues in processing
        error = Exception("Complex error with \x00 null bytes")
        result = fsa.execute(error, context)

        # Should still return a valid result even if recovery has issues
        assert isinstance(result, RecoveryResult)
        assert result.error_category in ErrorCategory

    def test_strategy_application_failure(self):
        """Test handling when strategy application fails."""
        fsa = ErrorRecoveryFSA()

        context = OperationContext(
            operation_id="strategy-fail",
            operation_name="strategy_fail",
            start_time=datetime.now(),
        )

        # Mock operation that raises during retry
        def problematic_operation():
            raise RuntimeError("Unhandled error in operation")

        strategy = RecoveryStrategy(
            strategy_type=RecoveryStrategyType.RETRY,
            max_attempts=2,
            backoff_base=1.1,
            backoff_multiplier=0.01,
        )

        # Should handle the failure gracefully
        success = fsa.apply_recovery(strategy, context, problematic_operation)
        assert success is False

    def test_fsa_state_consistency_after_errors(self):
        """Test that FSA maintains consistent state after errors."""
        fsa = ErrorRecoveryFSA()

        initial_state = fsa.current_state
        assert initial_state == FSAState.IDLE

        context = OperationContext(
            operation_id="state-test",
            operation_name="state_consistency",
            start_time=datetime.now(),
        )

        # Process an error
        error = Exception("Test error")
        result = fsa.execute(error, context)

        # FSA should be in a valid state
        assert fsa.current_state in [FSAState.RECOVERED, FSAState.FAILED, FSAState.MONITORING]

        # State history should be recorded
        assert len(fsa.state_history) > 0


class TestHealthMonitoring:
    """Test health monitoring and status tracking."""

    def test_monitor_health_new_operation(self):
        """Test health monitoring for a new operation."""
        fsa = ErrorRecoveryFSA()

        health = fsa.monitor_health("new-operation")

        assert health.operation_id == "new-operation"
        assert health.is_healthy is True
        assert health.error_rate == 0.0
        assert health.success_rate == 1.0

    def test_health_degrades_with_failures(self):
        """Test that health status degrades with failures."""
        fsa = ErrorRecoveryFSA()

        context = OperationContext(
            operation_id="health-test",
            operation_name="health_test",
            start_time=datetime.now(),
        )

        # Cause some failures
        for _ in range(3):
            error = Exception("Failure")
            fsa.execute(error, context)

        health = fsa.monitor_health("health-test")

        assert health.error_rate > 0.0
        # May or may not be healthy depending on success rate

    def test_health_improves_with_success(self):
        """Test that health improves with successful recoveries."""
        fsa = ErrorRecoveryFSA()

        context = OperationContext(
            operation_id="health-improve",
            operation_name="health_improve",
            start_time=datetime.now(),
        )

        # Create a recoverable scenario (simulated by not actually failing)
        # Track manually for this test
        fsa._update_health_status("health-improve", True, 0.1)
        fsa._update_health_status("health-improve", True, 0.1)

        health = fsa.monitor_health("health-improve")

        assert health.is_healthy is True
        assert health.success_rate > 0.0


class TestAnalyticsAndReporting:
    """Test analytics and failure reporting."""

    def test_analyze_failures_empty_window(self):
        """Test failure analysis with no errors."""
        fsa = ErrorRecoveryFSA(enable_analytics=True)

        analytics = fsa.analyze_failures("1h")

        assert analytics.total_errors == 0
        assert analytics.recovery_success_rate == 1.0
        assert len(analytics.errors_by_category) == 0

    def test_analyze_failures_with_errors(self):
        """Test failure analysis with recorded errors."""
        fsa = ErrorRecoveryFSA(enable_analytics=True)

        context = OperationContext(
            operation_id="analytics-test",
            operation_name="analytics_test",
            start_time=datetime.now(),
        )

        # Generate some errors
        errors = [
            ConnectionError("Network error 1"),
            ConnectionError("Network error 2"),
            TimeoutError("Timeout error"),
            ModelRateLimitError("Rate limit", model_name="gpt-4"),
        ]

        for error in errors:
            fsa.execute(error, context)

        analytics = fsa.analyze_failures("1h")

        assert analytics.total_errors == len(errors)
        assert ErrorCategory.NETWORK in analytics.errors_by_category
        assert ErrorCategory.TIMEOUT in analytics.errors_by_category
        assert ErrorCategory.RATE_LIMIT in analytics.errors_by_category

    def test_parse_time_window(self):
        """Test time window parsing."""
        fsa = ErrorRecoveryFSA()

        assert fsa._parse_time_window("60s") == 60.0
        assert fsa._parse_time_window("5m") == 300.0
        assert fsa._parse_time_window("1h") == 3600.0
        assert fsa._parse_time_window("2d") == 172800.0

    def test_most_common_errors_tracking(self):
        """Test tracking of most common errors."""
        fsa = ErrorRecoveryFSA(enable_analytics=True)

        context = OperationContext(
            operation_id="common-errors",
            operation_name="common_errors",
            start_time=datetime.now(),
        )

        # Generate repeated errors
        for _ in range(5):
            fsa.execute(ConnectionError("Same network error"), context)

        for _ in range(2):
            fsa.execute(TimeoutError("Timeout"), context)

        analytics = fsa.analyze_failures("1h")

        assert len(analytics.most_common_errors) > 0
        # Most common should be the network error (5 occurrences)
        most_common_msg, count = analytics.most_common_errors[0]
        assert "network error" in most_common_msg.lower() or count == 5


class TestFallbackStrategy:
    """Test fallback strategy functionality."""

    def test_fallback_with_operations(self):
        """Test fallback strategy with fallback operations."""
        fsa = ErrorRecoveryFSA()

        fallback_called = {"primary": False, "secondary": False}

        def primary_fallback():
            fallback_called["primary"] = True

        def secondary_fallback():
            fallback_called["secondary"] = True

        context = OperationContext(
            operation_id="fallback-test",
            operation_name="fallback_test",
            start_time=datetime.now(),
            fallback_operations=[primary_fallback, secondary_fallback],
        )

        strategy = RecoveryStrategy(strategy_type=RecoveryStrategyType.FALLBACK)
        success = fsa.apply_recovery(strategy, context)

        assert success is True
        assert fallback_called["primary"] is True

    def test_fallback_tries_all_operations(self):
        """Test that fallback tries all operations until one succeeds."""
        fsa = ErrorRecoveryFSA()

        attempt_count = {"count": 0}

        def failing_fallback():
            attempt_count["count"] += 1
            raise Exception("Fallback failed")

        def succeeding_fallback():
            attempt_count["count"] += 1

        context = OperationContext(
            operation_id="fallback-multi",
            operation_name="fallback_multi",
            start_time=datetime.now(),
            fallback_operations=[failing_fallback, succeeding_fallback],
        )

        strategy = RecoveryStrategy(strategy_type=RecoveryStrategyType.FALLBACK)
        success = fsa.apply_recovery(strategy, context)

        assert success is True
        assert attempt_count["count"] == 2  # Both were tried


class TestFSAStateManagement:
    """Test FSA state transitions and management."""

    def test_state_transitions_during_recovery(self):
        """Test that FSA transitions through states correctly."""
        fsa = ErrorRecoveryFSA()

        context = OperationContext(
            operation_id="state-transition",
            operation_name="state_transition",
            start_time=datetime.now(),
        )

        initial_state = fsa.current_state
        assert initial_state == FSAState.IDLE

        # Execute recovery
        error = Exception("Test error")
        result = fsa.execute(error, context)

        # Check state history
        history = fsa.get_state_history()
        assert len(history) > 0

        # Verify state progression
        states_visited = [state_tuple[2] for state_tuple in history]
        assert FSAState.DETECTING in states_visited
        assert FSAState.ANALYZING in states_visited

    def test_reset_fsa(self):
        """Test FSA reset functionality."""
        fsa = ErrorRecoveryFSA(enable_analytics=True)

        # Add some data
        context = OperationContext(
            operation_id="reset-test",
            operation_name="reset_test",
            start_time=datetime.now(),
        )
        fsa.execute(Exception("Error"), context)

        # Verify data exists
        assert len(fsa.error_history) > 0

        # Reset
        fsa.reset()

        # Verify clean state
        assert fsa.current_state == FSAState.IDLE
        assert len(fsa.error_history) == 0
        assert len(fsa.circuit_breakers) == 0
        assert len(fsa.checkpoints) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
