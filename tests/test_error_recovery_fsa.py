"""
Unit tests for Error Recovery FSA

Tests cover:
- Error detection and classification
- Recovery strategy execution
- Exponential backoff retry logic
- Graceful degradation
- State transitions
- Incident logging
"""

import pytest
import time
from unittest.mock import Mock, patch
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.fsas.error_recovery_fsa import (
    ErrorRecoveryFSA,
    ErrorType,
    RecoveryState,
    ErrorContext,
    RecoveryStrategy
)


class TestErrorDetection:
    """Test error detection functionality."""

    def test_detect_error_creates_context(self):
        """Test that detect_error creates proper ErrorContext."""
        fsa = ErrorRecoveryFSA()
        error = ValueError("Test error")

        context = fsa.detect_error(error)

        assert context.error == error
        assert context.error_type == ErrorType.UNKNOWN
        assert context.retry_count == 0
        assert isinstance(context.timestamp, datetime)

    def test_detect_error_with_metadata(self):
        """Test error detection with metadata."""
        fsa = ErrorRecoveryFSA()
        error = Exception("Test")
        metadata = {"operation": "api_call", "endpoint": "/users"}

        context = fsa.detect_error(error, metadata=metadata)

        assert context.metadata == metadata
        assert context.metadata["operation"] == "api_call"

    def test_detect_error_state_transition(self):
        """Test that error detection transitions to ERROR_DETECTED state."""
        fsa = ErrorRecoveryFSA()
        error = Exception("Test")

        fsa.detect_error(error)

        assert fsa.state == RecoveryState.ERROR_DETECTED

    def test_error_history_tracking(self):
        """Test that errors are added to history."""
        fsa = ErrorRecoveryFSA()

        fsa.detect_error(ValueError("Error 1"))
        fsa.detect_error(TypeError("Error 2"))

        assert len(fsa.error_history) == 2
        assert isinstance(fsa.error_history[0].error, ValueError)
        assert isinstance(fsa.error_history[1].error, TypeError)


class TestErrorClassification:
    """Test error classification functionality."""

    def test_classify_api_error(self):
        """Test classification of API-related errors."""
        fsa = ErrorRecoveryFSA()
        error = Exception("HTTP request failed with status 500")
        context = ErrorContext(error=error)

        error_type = fsa.classify_failure(context)

        assert error_type == ErrorType.API
        assert context.error_type == ErrorType.API

    def test_classify_timeout_error(self):
        """Test classification of timeout errors."""
        fsa = ErrorRecoveryFSA()
        error = TimeoutError("Request timeout exceeded")
        context = ErrorContext(error=error)

        error_type = fsa.classify_failure(context)

        assert error_type == ErrorType.TIMEOUT

    def test_classify_validation_error(self):
        """Test classification of validation errors."""
        fsa = ErrorRecoveryFSA()
        error = ValueError("Invalid schema format")
        context = ErrorContext(error=error)

        error_type = fsa.classify_failure(context)

        assert error_type == ErrorType.VALIDATION

    def test_classify_resource_error(self):
        """Test classification of resource errors."""
        fsa = ErrorRecoveryFSA()
        error = MemoryError("Out of memory")
        context = ErrorContext(error=error)

        error_type = fsa.classify_failure(context)

        assert error_type == ErrorType.RESOURCE

    def test_classify_unknown_error(self):
        """Test classification of unknown errors."""
        fsa = ErrorRecoveryFSA()
        error = Exception("Random unknown error")
        context = ErrorContext(error=error)

        error_type = fsa.classify_failure(context)

        assert error_type == ErrorType.UNKNOWN

    def test_classify_state_transition(self):
        """Test state transition during classification."""
        fsa = ErrorRecoveryFSA()
        context = ErrorContext(error=Exception("Test"))

        fsa.classify_failure(context)

        assert fsa.state == RecoveryState.ERROR_CLASSIFIED


class TestRecoveryExecution:
    """Test recovery execution and retry logic."""

    def test_execute_recovery_success_first_try(self):
        """Test successful recovery on first attempt."""
        fsa = ErrorRecoveryFSA()
        context = ErrorContext(error=Exception("Test"), max_retries=3)

        def successful_action():
            return "success"

        result = fsa.execute_recovery(context, successful_action)

        assert result['success'] is True
        assert result['result'] == "success"
        assert result['attempts'] == 1
        assert result['recovered'] is True
        assert fsa.state == RecoveryState.RECOVERY_SUCCESS

    def test_execute_recovery_success_after_retries(self):
        """Test successful recovery after multiple retries."""
        fsa = ErrorRecoveryFSA(strategy=RecoveryStrategy(base_delay=0.01))
        context = ErrorContext(error=Exception("Test"), max_retries=3)

        attempt_count = 0

        def flaky_action():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise Exception("Temporary failure")
            return "success"

        result = fsa.execute_recovery(context, flaky_action)

        assert result['success'] is True
        assert result['attempts'] == 3
        assert result['recovered'] is True

    def test_execute_recovery_all_retries_exhausted(self):
        """Test recovery failure after all retries exhausted."""
        fsa = ErrorRecoveryFSA(strategy=RecoveryStrategy(base_delay=0.01, enable_degraded_mode=False))
        context = ErrorContext(error=Exception("Test"), max_retries=2)

        def failing_action():
            raise Exception("Persistent failure")

        result = fsa.execute_recovery(context, failing_action)

        assert result['success'] is False
        assert result['attempts'] == 3  # max_retries + 1
        assert result['recovered'] is False
        assert fsa.state == RecoveryState.RECOVERY_FAILED

    def test_execute_recovery_with_arguments(self):
        """Test recovery execution with function arguments."""
        fsa = ErrorRecoveryFSA()
        context = ErrorContext(error=Exception("Test"))

        def action_with_args(x, y, z=None):
            return x + y + (z or 0)

        result = fsa.execute_recovery(context, action_with_args, 1, 2, z=3)

        assert result['success'] is True
        assert result['result'] == 6

    def test_exponential_backoff_delay_calculation(self):
        """Test exponential backoff delay calculation."""
        strategy = RecoveryStrategy(base_delay=1.0, exponential_base=2.0, max_delay=10.0)
        fsa = ErrorRecoveryFSA(strategy=strategy)

        delay_0 = fsa._calculate_backoff_delay(0)
        delay_1 = fsa._calculate_backoff_delay(1)
        delay_2 = fsa._calculate_backoff_delay(2)
        delay_5 = fsa._calculate_backoff_delay(5)

        assert delay_0 == 1.0  # 1 * 2^0
        assert delay_1 == 2.0  # 1 * 2^1
        assert delay_2 == 4.0  # 1 * 2^2
        assert delay_5 == 10.0  # Capped at max_delay

    def test_recovery_actions_tracking(self):
        """Test that recovery actions are tracked in context."""
        fsa = ErrorRecoveryFSA(strategy=RecoveryStrategy(base_delay=0.01))
        context = ErrorContext(error=Exception("Test"), max_retries=2)

        def action():
            return "success"

        fsa.execute_recovery(context, action)

        assert len(context.recovery_actions) > 0
        assert any("Success" in action for action in context.recovery_actions)


class TestDegradedMode:
    """Test graceful degradation functionality."""

    def test_degraded_mode_fallback_success(self):
        """Test successful fallback to degraded mode."""
        def fallback():
            return "fallback_result"

        strategy = RecoveryStrategy(
            max_retries=1,
            base_delay=0.01,
            enable_degraded_mode=True,
            fallback_action=fallback
        )
        fsa = ErrorRecoveryFSA(strategy=strategy)
        context = ErrorContext(error=Exception("Test"), max_retries=1)

        def failing_action():
            raise Exception("Always fails")

        result = fsa.execute_recovery(context, failing_action)

        assert result['success'] is True
        assert result['result'] == "fallback_result"
        assert result['degraded_mode'] is True
        assert result['recovered'] is True
        assert fsa.state == RecoveryState.DEGRADED_MODE

    def test_degraded_mode_disabled(self):
        """Test that degraded mode can be disabled."""
        strategy = RecoveryStrategy(
            max_retries=1,
            base_delay=0.01,
            enable_degraded_mode=False
        )
        fsa = ErrorRecoveryFSA(strategy=strategy)
        context = ErrorContext(error=Exception("Test"), max_retries=1)

        def failing_action():
            raise Exception("Always fails")

        result = fsa.execute_recovery(context, failing_action)

        assert result['success'] is False
        assert 'degraded_mode' not in result or not result.get('degraded_mode')
        assert fsa.state == RecoveryState.RECOVERY_FAILED

    def test_degraded_mode_fallback_also_fails(self):
        """Test handling when degraded mode fallback also fails."""
        def failing_fallback():
            raise Exception("Fallback also fails")

        strategy = RecoveryStrategy(
            max_retries=1,
            base_delay=0.01,
            enable_degraded_mode=True,
            fallback_action=failing_fallback
        )
        fsa = ErrorRecoveryFSA(strategy=strategy)
        context = ErrorContext(error=Exception("Test"), max_retries=1)

        def failing_action():
            raise Exception("Always fails")

        result = fsa.execute_recovery(context, failing_action)

        assert result['success'] is False
        assert result['degraded_mode'] is True
        assert result['recovered'] is False


class TestIncidentLogging:
    """Test incident logging functionality."""

    def test_log_incident_default_handler(self):
        """Test incident logging with default handler."""
        fsa = ErrorRecoveryFSA()
        context = ErrorContext(
            error=ValueError("Test error"),
            error_type=ErrorType.VALIDATION,
            retry_count=2
        )
        context.recovery_actions.append("Retry attempt 1")

        # Should not raise any exceptions
        fsa.log_incident(context)

    def test_log_incident_custom_handler(self):
        """Test incident logging with custom handler."""
        logged_incidents = []

        def custom_handler(incident):
            logged_incidents.append(incident)

        fsa = ErrorRecoveryFSA(log_handler=custom_handler)
        context = ErrorContext(
            error=ValueError("Test error"),
            error_type=ErrorType.API
        )

        fsa.log_incident(context, additional_info={"severity": "high"})

        assert len(logged_incidents) == 1
        assert logged_incidents[0]['error_type'] == 'api'
        assert logged_incidents[0]['error'] == 'Test error'
        assert logged_incidents[0]['additional_info']['severity'] == 'high'

    def test_log_incident_includes_all_context(self):
        """Test that logged incident includes all relevant context."""
        logged_incidents = []

        def custom_handler(incident):
            logged_incidents.append(incident)

        fsa = ErrorRecoveryFSA(log_handler=custom_handler)
        context = ErrorContext(
            error=Exception("Test"),
            error_type=ErrorType.TIMEOUT,
            retry_count=3,
            metadata={"endpoint": "/api/test"}
        )
        context.recovery_actions.append("Action 1")

        fsa.log_incident(context)

        incident = logged_incidents[0]
        assert 'timestamp' in incident
        assert incident['error_type'] == 'timeout'
        assert incident['retry_count'] == 3
        assert incident['metadata']['endpoint'] == '/api/test'
        assert 'Action 1' in incident['recovery_actions']


class TestCompleteWorkflow:
    """Test complete error handling workflow."""

    def test_handle_error_complete_workflow(self):
        """Test the complete handle_error workflow."""
        fsa = ErrorRecoveryFSA(strategy=RecoveryStrategy(base_delay=0.01))

        error = Exception("API request failed")

        def recovery():
            return "recovered"

        result = fsa.handle_error(
            error,
            recovery_action=recovery,
            context={"operation": "fetch_data"}
        )

        assert result['recovered'] is True
        assert result['success'] is True
        assert 'error_type' in result
        assert fsa.state == RecoveryState.IDLE

    def test_handle_error_without_recovery_action(self):
        """Test handle_error without providing recovery action."""
        fsa = ErrorRecoveryFSA()
        error = ValueError("Invalid input")

        result = fsa.handle_error(error, context={"field": "email"})

        assert result['recovered'] is False
        assert 'error_type' in result
        assert len(fsa.error_history) == 1

    def test_handle_error_with_retry_and_success(self):
        """Test complete workflow with retries leading to success."""
        fsa = ErrorRecoveryFSA(strategy=RecoveryStrategy(base_delay=0.01, max_retries=3))

        attempt_count = 0

        def flaky_recovery():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise Exception("Not yet")
            return "success"

        error = Exception("Initial failure")
        result = fsa.handle_error(error, recovery_action=flaky_recovery)

        assert result['recovered'] is True
        assert result['attempts'] == 2
        assert fsa.state == RecoveryState.IDLE


class TestStateManagement:
    """Test FSA state management."""

    def test_initial_state(self):
        """Test that FSA starts in IDLE state."""
        fsa = ErrorRecoveryFSA()
        assert fsa.state == RecoveryState.IDLE

    def test_state_transitions_recorded(self):
        """Test that state transitions are recorded."""
        fsa = ErrorRecoveryFSA()
        error = Exception("Test")

        fsa.detect_error(error)
        context = ErrorContext(error=error)
        fsa.classify_failure(context)

        assert len(fsa.state_transitions) >= 2
        assert fsa.state_transitions[0][0] == RecoveryState.IDLE
        assert fsa.state_transitions[0][1] == RecoveryState.ERROR_DETECTED

    def test_reset_clears_state(self):
        """Test that reset clears all state."""
        fsa = ErrorRecoveryFSA()

        fsa.detect_error(Exception("Test 1"))
        fsa.detect_error(Exception("Test 2"))

        fsa.reset()

        assert fsa.state == RecoveryState.IDLE
        assert len(fsa.error_history) == 0
        assert len(fsa.state_transitions) == 0


class TestStatistics:
    """Test error statistics functionality."""

    def test_get_error_statistics_empty(self):
        """Test statistics when no errors have occurred."""
        fsa = ErrorRecoveryFSA()
        stats = fsa.get_error_statistics()

        assert stats['total_errors'] == 0
        assert stats['by_type'] == {}
        assert stats['average_retries'] == 0

    def test_get_error_statistics_with_errors(self):
        """Test statistics with multiple errors."""
        fsa = ErrorRecoveryFSA()

        # Create some errors
        ctx1 = fsa.detect_error(Exception("API error"))
        ctx1.error_type = ErrorType.API
        ctx1.retry_count = 2

        ctx2 = fsa.detect_error(Exception("Timeout"))
        ctx2.error_type = ErrorType.TIMEOUT
        ctx2.retry_count = 1

        ctx3 = fsa.detect_error(Exception("Another API error"))
        ctx3.error_type = ErrorType.API
        ctx3.retry_count = 3

        stats = fsa.get_error_statistics()

        assert stats['total_errors'] == 3
        assert stats['by_type']['api'] == 2
        assert stats['by_type']['timeout'] == 1
        assert stats['average_retries'] == 2.0  # (2 + 1 + 3) / 3

    def test_statistics_tracks_state_transitions(self):
        """Test that statistics track state transitions."""
        fsa = ErrorRecoveryFSA()

        fsa.detect_error(Exception("Test"))
        stats = fsa.get_error_statistics()

        assert stats['state_transitions'] > 0


class TestIntegrationScenarios:
    """Integration tests for real-world scenarios."""

    def test_api_retry_scenario(self):
        """Test realistic API retry scenario."""
        call_count = 0

        def simulated_api_call():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("API connection failed")
            return {"status": "success", "data": [1, 2, 3]}

        fsa = ErrorRecoveryFSA(strategy=RecoveryStrategy(base_delay=0.01, max_retries=5))

        try:
            simulated_api_call()
        except Exception as e:
            result = fsa.handle_error(
                e,
                recovery_action=simulated_api_call,
                context={"endpoint": "/api/data"}
            )

            assert result['recovered'] is True
            assert result['result']['status'] == 'success'
            assert call_count == 3

    def test_timeout_with_degraded_mode(self):
        """Test timeout scenario with graceful degradation."""
        def timeout_action():
            raise TimeoutError("Request timed out")

        def cached_fallback():
            return {"cached": True, "data": []}

        strategy = RecoveryStrategy(
            max_retries=2,
            base_delay=0.01,
            enable_degraded_mode=True,
            fallback_action=cached_fallback
        )
        fsa = ErrorRecoveryFSA(strategy=strategy)

        error = TimeoutError("Initial timeout")
        result = fsa.handle_error(error, recovery_action=timeout_action)

        assert result['recovered'] is True
        assert result['degraded_mode'] is True
        assert result['result']['cached'] is True

    def test_validation_error_no_retry(self):
        """Test that validation errors can be handled without retries."""
        fsa = ErrorRecoveryFSA()
        error = ValueError("Invalid email format")

        result = fsa.handle_error(error, context={"field": "email"})

        assert result['error_type'] == 'validation'
        assert len(fsa.error_history) == 1
        assert fsa.error_history[0].error_type == ErrorType.VALIDATION


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
