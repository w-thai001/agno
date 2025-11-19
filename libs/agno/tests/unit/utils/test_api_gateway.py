"""Tests for API Gateway FSA"""

import time

import pytest

from agno.utils.api_gateway import APIGateway, GatewayState


class TestAPIGateway:
    """Test APIGateway class"""

    def test_init(self):
        """Test gateway initialization"""
        gateway = APIGateway(rate_limit=100, refill_rate=10.0)
        assert gateway.state == GatewayState.READY

    def test_successful_request(self):
        """Test successful request processing"""
        gateway = APIGateway(rate_limit=10, refill_rate=1.0)
        success, result, msg = gateway.request("user1", lambda: "test_result")
        assert success is True
        assert result == "test_result"
        assert msg == "Success"
        assert gateway.state == GatewayState.READY

    def test_rate_limiting(self):
        """Test rate limiting behavior"""
        gateway = APIGateway(rate_limit=5, refill_rate=1.0)

        # Consume all tokens
        for i in range(5):
            success, _, _ = gateway.request("user1", lambda: i)
            assert success is True

        # Next request should be rate limited
        success, result, msg = gateway.request("user1", lambda: "should_fail")
        assert success is False
        assert result is None
        assert "Rate limited" in msg
        assert gateway.state == GatewayState.RATE_LIMITED

    def test_error_handling(self):
        """Test error handling in request"""
        gateway = APIGateway(rate_limit=10, refill_rate=1.0, failure_threshold=3)

        def failing_handler():
            raise ValueError("Test error")

        success, result, msg = gateway.request("user1", failing_handler)
        assert success is False
        assert result is None
        assert "Error: Test error" in msg
        assert gateway.state == GatewayState.ERROR

    def test_circuit_breaker_opens(self):
        """Test circuit breaker opens after threshold failures"""
        gateway = APIGateway(rate_limit=100, refill_rate=10.0, failure_threshold=3)

        def failing_handler():
            raise RuntimeError("Persistent failure")

        # Fail 3 times to trigger circuit breaker
        for i in range(3):
            success, _, msg = gateway.request("user1", failing_handler)
            if i < 2:
                assert gateway.state == GatewayState.ERROR
            else:
                assert success is False
                assert "Circuit breaker opened" in msg
                assert gateway.state == GatewayState.CIRCUIT_OPEN

    def test_circuit_breaker_blocks_requests(self):
        """Test circuit breaker blocks requests when open"""
        gateway = APIGateway(rate_limit=100, refill_rate=10.0, failure_threshold=2)

        # Open circuit breaker
        for _ in range(2):
            gateway.request("user1", lambda: 1 / 0)

        # Circuit should be open, blocking even successful handlers
        success, result, msg = gateway.request("user1", lambda: "success")
        assert success is False
        assert result is None
        assert "Circuit breaker open" in msg
        assert gateway.state == GatewayState.CIRCUIT_OPEN

    def test_circuit_breaker_recovery(self):
        """Test circuit breaker recovers after timeout"""
        gateway = APIGateway(
            rate_limit=100,
            refill_rate=10.0,
            failure_threshold=2,
            recovery_timeout=0.5,
        )

        # Open circuit breaker
        for _ in range(2):
            gateway.request("user1", lambda: 1 / 0)

        # Should be blocked
        success, _, _ = gateway.request("user1", lambda: "test")
        assert success is False

        # Wait for recovery
        time.sleep(0.6)

        # Should work now
        success, result, msg = gateway.request("user1", lambda: "recovered")
        assert success is True
        assert result == "recovered"
        assert msg == "Success"

    def test_multiple_keys_independent(self):
        """Test multiple keys have independent limits and circuit breakers"""
        gateway = APIGateway(rate_limit=5, refill_rate=1.0, failure_threshold=2)

        # Fail user1's circuit breaker
        for _ in range(2):
            gateway.request("user1", lambda: 1 / 0)

        # user1 should be blocked
        success, _, _ = gateway.request("user1", lambda: "test")
        assert success is False

        # user2 should work fine
        success, result, _ = gateway.request("user2", lambda: "user2_ok")
        assert success is True
        assert result == "user2_ok"

    def test_reset_clears_failures_and_circuit(self):
        """Test reset clears failures and circuit breaker"""
        gateway = APIGateway(rate_limit=10, refill_rate=1.0, failure_threshold=2)

        # Open circuit breaker
        for _ in range(2):
            gateway.request("user1", lambda: 1 / 0)

        # Should be blocked
        success, _, _ = gateway.request("user1", lambda: "test")
        assert success is False

        # Reset
        gateway.reset("user1")

        # Should work now
        success, result, _ = gateway.request("user1", lambda: "reset_ok")
        assert success is True
        assert result == "reset_ok"
        assert gateway.state == GatewayState.READY

    def test_reset_restores_rate_limit(self):
        """Test reset restores rate limit"""
        gateway = APIGateway(rate_limit=3, refill_rate=1.0)

        # Consume all tokens
        for _ in range(3):
            gateway.request("user1", lambda: "ok")

        # Should be rate limited
        success, _, _ = gateway.request("user1", lambda: "fail")
        assert success is False

        # Reset
        gateway.reset("user1")

        # Should have full tokens again
        success, _, _ = gateway.request("user1", lambda: "ok")
        assert success is True

    def test_request_with_custom_tokens(self):
        """Test request with custom token consumption"""
        gateway = APIGateway(rate_limit=10, refill_rate=1.0)

        # Consume 8 tokens
        success, _, _ = gateway.request("user1", lambda: "ok", tokens=8.0)
        assert success is True

        # Only 2 tokens left, should fail with 5
        success, _, msg = gateway.request("user1", lambda: "fail", tokens=5.0)
        assert success is False
        assert "Rate limited" in msg

    def test_state_transitions(self):
        """Test FSA state transitions"""
        gateway = APIGateway(rate_limit=100, refill_rate=10.0)

        # Initial state
        assert gateway.state == GatewayState.READY

        # During processing (we can't directly observe this in sync code easily)
        # but after successful request should be READY
        gateway.request("user1", lambda: "ok")
        assert gateway.state == GatewayState.READY

        # After error
        gateway.request("user2", lambda: 1 / 0)
        assert gateway.state == GatewayState.ERROR

    def test_successful_request_resets_failure_count(self):
        """Test successful request resets failure count"""
        gateway = APIGateway(rate_limit=100, refill_rate=10.0, failure_threshold=3)

        # Fail once
        gateway.request("user1", lambda: 1 / 0)

        # Succeed
        success, _, _ = gateway.request("user1", lambda: "ok")
        assert success is True

        # Fail twice more - should not open circuit (count was reset)
        gateway.request("user1", lambda: 1 / 0)
        gateway.request("user1", lambda: 1 / 0)

        # Circuit should still be closed (need one more failure)
        success, _, _ = gateway.request("user1", lambda: "test")
        assert success is True
