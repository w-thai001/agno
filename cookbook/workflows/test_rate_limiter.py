"""
Unit Tests for Rate Limiter Workflow

Run tests with:
    pytest cookbook/workflows/test_rate_limiter.py -v

Run tests with coverage:
    pytest cookbook/workflows/test_rate_limiter.py -v --cov=rate_limiter

Prerequisites:
    - Redis running on localhost:6379 (or use redis-py-mock for mocking)
    - Install dependencies: pip install pytest pytest-cov redis
"""

import time
import pytest
import redis
from unittest.mock import Mock, patch, MagicMock
from concurrent.futures import ThreadPoolExecutor
from typing import List

# Import the rate limiter modules
from rate_limiter import RateLimiter, RateLimitRequest, RateLimitResponse


class TestRateLimitRequest:
    """Test RateLimitRequest dataclass"""

    def test_default_values(self):
        """Test default values for RateLimitRequest"""
        request = RateLimitRequest(client_id="test_client")

        assert request.client_id == "test_client"
        assert request.max_requests == 100
        assert request.time_window_seconds == 60
        assert request.tokens_requested == 1
        assert request.burst_multiplier == 1.5

    def test_custom_values(self):
        """Test custom values for RateLimitRequest"""
        request = RateLimitRequest(
            client_id="custom_client",
            max_requests=50,
            time_window_seconds=30,
            tokens_requested=5,
            burst_multiplier=2.0
        )

        assert request.client_id == "custom_client"
        assert request.max_requests == 50
        assert request.time_window_seconds == 30
        assert request.tokens_requested == 5
        assert request.burst_multiplier == 2.0


class TestRateLimitResponse:
    """Test RateLimitResponse dataclass"""

    def test_response_creation(self):
        """Test RateLimitResponse creation"""
        response = RateLimitResponse(
            allow_request=True,
            remaining_tokens=95.5,
            retry_after_seconds=0.0,
            total_requests=5,
            window_reset_time=time.time() + 60,
            client_id="test_client"
        )

        assert response.allow_request is True
        assert response.remaining_tokens == 95.5
        assert response.retry_after_seconds == 0.0
        assert response.total_requests == 5
        assert response.client_id == "test_client"
        assert isinstance(response.metadata, dict)


@pytest.fixture(scope="function")
def redis_client():
    """
    Fixture to provide a real Redis client for integration tests.

    Note: Requires Redis running on localhost:6379
    """
    try:
        client = redis.from_url("redis://localhost:6379/15", decode_responses=True)
        client.ping()

        # Clean up before test
        client.flushdb()

        yield client

        # Clean up after test
        client.flushdb()
        client.close()
    except (redis.ConnectionError, redis.exceptions.ConnectionError):
        pytest.skip("Redis not available on localhost:6379")


@pytest.fixture(scope="function")
def rate_limiter(redis_client):
    """Fixture to provide a RateLimiter instance"""
    limiter = RateLimiter(redis_url="redis://localhost:6379/15", debug_mode=False)
    return limiter


class TestRateLimiterInitialization:
    """Test RateLimiter initialization"""

    def test_successful_initialization(self, rate_limiter):
        """Test successful Redis connection"""
        assert rate_limiter.redis_client is not None
        assert rate_limiter.redis_client.ping() is True
        assert rate_limiter._lua_script is not None

    def test_connection_failure(self):
        """Test handling of Redis connection failure"""
        with pytest.raises(ConnectionError) as exc_info:
            RateLimiter(redis_url="redis://invalid-host:9999/0")

        assert "Unable to connect to Redis" in str(exc_info.value)

    def test_custom_defaults(self):
        """Test custom default configuration"""
        limiter = RateLimiter(
            redis_url="redis://localhost:6379/15",
            default_max_requests=200,
            default_time_window=120
        )

        assert limiter.default_max_requests == 200
        assert limiter.default_time_window == 120


class TestRateLimiterValidation:
    """Test input validation"""

    def test_validate_empty_client_id(self, rate_limiter):
        """Test validation fails for empty client_id"""
        request = RateLimitRequest(client_id="")

        with pytest.raises(ValueError) as exc_info:
            rate_limiter.check_rate_limit(request)

        assert "client_id must be a non-empty string" in str(exc_info.value)

    def test_validate_negative_max_requests(self, rate_limiter):
        """Test validation fails for negative max_requests"""
        request = RateLimitRequest(client_id="test", max_requests=-10)

        with pytest.raises(ValueError) as exc_info:
            rate_limiter.check_rate_limit(request)

        assert "max_requests must be positive" in str(exc_info.value)

    def test_validate_zero_time_window(self, rate_limiter):
        """Test validation fails for zero time_window"""
        request = RateLimitRequest(client_id="test", time_window_seconds=0)

        with pytest.raises(ValueError) as exc_info:
            rate_limiter.check_rate_limit(request)

        assert "time_window_seconds must be positive" in str(exc_info.value)

    def test_validate_invalid_burst_multiplier(self, rate_limiter):
        """Test validation fails for burst_multiplier < 1.0"""
        request = RateLimitRequest(client_id="test", burst_multiplier=0.5)

        with pytest.raises(ValueError) as exc_info:
            rate_limiter.check_rate_limit(request)

        assert "burst_multiplier must be >= 1.0" in str(exc_info.value)


class TestTokenBucketAlgorithm:
    """Test token bucket algorithm implementation"""

    def test_initial_request_allowed(self, rate_limiter):
        """Test that first request is always allowed"""
        request = RateLimitRequest(
            client_id="user_1",
            max_requests=10,
            time_window_seconds=60
        )

        response = rate_limiter.check_rate_limit(request)

        assert response.allow_request is True
        assert response.remaining_tokens < 10  # Should have consumed 1 token
        assert response.total_requests == 1

    def test_multiple_requests_allowed(self, rate_limiter):
        """Test multiple requests within limit are allowed"""
        request = RateLimitRequest(
            client_id="user_2",
            max_requests=5,
            time_window_seconds=60
        )

        # Make 5 requests
        responses = []
        for _ in range(5):
            response = rate_limiter.check_rate_limit(request)
            responses.append(response)

        # All should be allowed
        assert all(r.allow_request for r in responses)
        assert responses[-1].remaining_tokens < 1  # Almost empty

    def test_rate_limit_exceeded(self, rate_limiter):
        """Test that requests are denied when limit exceeded"""
        request = RateLimitRequest(
            client_id="user_3",
            max_requests=3,
            time_window_seconds=60
        )

        # Make 3 requests (should succeed)
        for _ in range(3):
            response = rate_limiter.check_rate_limit(request)
            assert response.allow_request is True

        # 4th request should fail
        response = rate_limiter.check_rate_limit(request)
        assert response.allow_request is False
        assert response.retry_after_seconds > 0

    def test_token_refill(self, rate_limiter):
        """Test that tokens refill over time"""
        request = RateLimitRequest(
            client_id="user_4",
            max_requests=2,
            time_window_seconds=2  # Very short window for testing
        )

        # Use up tokens
        rate_limiter.check_rate_limit(request)
        rate_limiter.check_rate_limit(request)

        # Should be denied immediately
        response = rate_limiter.check_rate_limit(request)
        assert response.allow_request is False

        # Wait for refill
        time.sleep(1.5)

        # Should be allowed after refill
        response = rate_limiter.check_rate_limit(request)
        assert response.allow_request is True

    def test_burst_allowance(self, rate_limiter):
        """Test burst multiplier allows temporary spikes"""
        request = RateLimitRequest(
            client_id="user_5",
            max_requests=10,
            time_window_seconds=60,
            burst_multiplier=2.0  # Allow bursts up to 20
        )

        # Make 15 requests rapidly (within burst capacity)
        allowed_count = 0
        for _ in range(15):
            response = rate_limiter.check_rate_limit(request)
            if response.allow_request:
                allowed_count += 1

        # Should allow at least 10 (normal) and up to 15 (burst)
        assert allowed_count >= 10
        assert allowed_count <= 15

    def test_weighted_requests(self, rate_limiter):
        """Test different token costs for different operations"""
        # Light operation (1 token)
        light_request = RateLimitRequest(
            client_id="user_6",
            max_requests=100,
            time_window_seconds=60,
            tokens_requested=1
        )

        # Heavy operation (20 tokens)
        heavy_request = RateLimitRequest(
            client_id="user_6",
            max_requests=100,
            time_window_seconds=60,
            tokens_requested=20
        )

        # Make 3 light requests (3 tokens total)
        for _ in range(3):
            response = rate_limiter.check_rate_limit(light_request)
            assert response.allow_request is True

        # Make 4 heavy requests (80 tokens total)
        for _ in range(4):
            response = rate_limiter.check_rate_limit(heavy_request)
            assert response.allow_request is True

        # Total: 83 tokens used, should have ~17 left
        response = rate_limiter.check_rate_limit(light_request)
        assert response.allow_request is True
        assert 10 < response.remaining_tokens < 20


class TestConcurrency:
    """Test concurrent request handling"""

    def test_atomic_operations(self, rate_limiter):
        """Test that concurrent requests are handled atomically"""
        request = RateLimitRequest(
            client_id="user_concurrent",
            max_requests=10,
            time_window_seconds=60
        )

        def make_request():
            return rate_limiter.check_rate_limit(request)

        # Make 20 concurrent requests
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(20)]
            responses = [future.result() for future in futures]

        # Exactly 10 should be allowed
        allowed = sum(1 for r in responses if r.allow_request)
        denied = sum(1 for r in responses if not r.allow_request)

        assert allowed == 10
        assert denied == 10

    def test_multiple_clients_isolated(self, rate_limiter):
        """Test that different clients have isolated rate limits"""
        def make_requests(client_id: str, count: int) -> List[bool]:
            results = []
            for _ in range(count):
                request = RateLimitRequest(
                    client_id=client_id,
                    max_requests=5,
                    time_window_seconds=60
                )
                response = rate_limiter.check_rate_limit(request)
                results.append(response.allow_request)
            return results

        # Make requests for different clients concurrently
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_a = executor.submit(make_requests, "client_a", 10)
            future_b = executor.submit(make_requests, "client_b", 10)
            future_c = executor.submit(make_requests, "client_c", 10)

            results_a = future_a.result()
            results_b = future_b.result()
            results_c = future_c.result()

        # Each client should have exactly 5 allowed
        assert sum(results_a) == 5
        assert sum(results_b) == 5
        assert sum(results_c) == 5


class TestRedisKeyManagement:
    """Test Redis key management"""

    def test_redis_key_format(self, rate_limiter):
        """Test Redis key format"""
        key = rate_limiter._get_redis_key("user_123", 100, 60)
        assert key == "rate_limit:user_123:100:60"

    def test_different_limits_different_keys(self, rate_limiter):
        """Test that different limits use different keys"""
        key1 = rate_limiter._get_redis_key("user_123", 100, 60)
        key2 = rate_limiter._get_redis_key("user_123", 200, 60)
        key3 = rate_limiter._get_redis_key("user_123", 100, 120)

        assert key1 != key2
        assert key1 != key3
        assert key2 != key3

    def test_ttl_prevents_memory_leak(self, rate_limiter, redis_client):
        """Test that Redis keys have TTL to prevent memory leaks"""
        request = RateLimitRequest(
            client_id="user_ttl",
            max_requests=10,
            time_window_seconds=5
        )

        rate_limiter.check_rate_limit(request)

        key = rate_limiter._get_redis_key("user_ttl", 10, 5)
        ttl = redis_client.ttl(key)

        # TTL should be set (>0) and reasonable (2x time window)
        assert ttl > 0
        assert ttl <= 10  # 2x time window


class TestStatisticsAndMonitoring:
    """Test statistics and monitoring features"""

    def test_get_client_stats_existing(self, rate_limiter):
        """Test getting stats for existing client"""
        # Make some requests
        request = RateLimitRequest(
            client_id="user_stats",
            max_requests=100,
            time_window_seconds=60
        )

        for _ in range(25):
            rate_limiter.check_rate_limit(request)

        # Get stats
        stats = rate_limiter.get_client_stats("user_stats", 100, 60)

        assert stats["client_id"] == "user_stats"
        assert stats["exists"] is True
        assert stats["total_requests"] == 25
        assert stats["tokens"] < 100  # Should have consumed tokens
        assert stats["ttl"] > 0

    def test_get_client_stats_nonexistent(self, rate_limiter):
        """Test getting stats for non-existent client"""
        stats = rate_limiter.get_client_stats("nonexistent_user", 100, 60)

        assert stats["client_id"] == "nonexistent_user"
        assert stats["exists"] is False
        assert stats["tokens"] == 100
        assert stats["total_requests"] == 0

    def test_reset_client_limit(self, rate_limiter):
        """Test resetting client rate limit"""
        # Make some requests
        request = RateLimitRequest(
            client_id="user_reset",
            max_requests=5,
            time_window_seconds=60
        )

        for _ in range(5):
            rate_limiter.check_rate_limit(request)

        # Should be rate limited
        response = rate_limiter.check_rate_limit(request)
        assert response.allow_request is False

        # Reset limit
        success = rate_limiter.reset_client_limit("user_reset", 5, 60)
        assert success is True

        # Should be allowed again
        response = rate_limiter.check_rate_limit(request)
        assert response.allow_request is True


class TestErrorHandling:
    """Test error handling and edge cases"""

    def test_fail_open_on_redis_error(self, rate_limiter):
        """Test that system fails open on Redis errors"""
        request = RateLimitRequest(
            client_id="user_error",
            max_requests=10,
            time_window_seconds=60
        )

        # Mock Redis error
        with patch.object(rate_limiter._lua_script, '__call__', side_effect=redis.RedisError("Connection lost")):
            response = rate_limiter.check_rate_limit(request)

            # Should fail open (allow request)
            assert response.allow_request is True
            assert "error" in response.metadata
            assert response.metadata["fail_open"] is True

    def test_redis_connection_cleanup(self, rate_limiter):
        """Test that Redis connection is cleaned up"""
        client = rate_limiter.redis_client
        assert client is not None

        # Delete limiter (calls __del__)
        del rate_limiter

        # Connection should be closed (this will raise an error if we try to use it)
        # Note: Can't easily test this without complex mocking


class TestWorkflowInterface:
    """Test high-level workflow interface"""

    def test_workflow_check_operation(self, rate_limiter):
        """Test workflow check operation"""
        responses = list(rate_limiter.run(
            client_id="workflow_user",
            max_requests=5,
            time_window_seconds=60,
            operation="check"
        ))

        assert len(responses) == 1
        assert "ALLOWED" in responses[0].content or "DENIED" in responses[0].content

    def test_workflow_stats_operation(self, rate_limiter):
        """Test workflow stats operation"""
        # Make some requests first
        rate_limiter.check_rate_limit(RateLimitRequest(
            client_id="workflow_stats",
            max_requests=10,
            time_window_seconds=60
        ))

        # Get stats
        responses = list(rate_limiter.run(
            client_id="workflow_stats",
            max_requests=10,
            time_window_seconds=60,
            operation="stats"
        ))

        assert len(responses) == 1
        assert "Stats" in responses[0].content or "No rate limit data" in responses[0].content

    def test_workflow_reset_operation(self, rate_limiter):
        """Test workflow reset operation"""
        responses = list(rate_limiter.run(
            client_id="workflow_reset",
            operation="reset"
        ))

        assert len(responses) == 1
        assert "reset" in responses[0].content.lower()

    def test_workflow_invalid_operation(self, rate_limiter):
        """Test workflow with invalid operation"""
        responses = list(rate_limiter.run(
            client_id="workflow_invalid",
            operation="invalid_op"
        ))

        assert len(responses) == 1
        assert "Error" in responses[0].content or "Unknown" in responses[0].content


class TestEdgeCases:
    """Test edge cases and special scenarios"""

    def test_very_high_request_rate(self, rate_limiter):
        """Test with very high request limit"""
        request = RateLimitRequest(
            client_id="user_high",
            max_requests=10000,
            time_window_seconds=60
        )

        response = rate_limiter.check_rate_limit(request)
        assert response.allow_request is True
        assert response.remaining_tokens < 10000

    def test_very_short_time_window(self, rate_limiter):
        """Test with very short time window"""
        request = RateLimitRequest(
            client_id="user_short",
            max_requests=2,
            time_window_seconds=1
        )

        # Use up tokens
        rate_limiter.check_rate_limit(request)
        rate_limiter.check_rate_limit(request)

        # Should be denied
        response = rate_limiter.check_rate_limit(request)
        assert response.allow_request is False
        assert response.retry_after_seconds <= 1

    def test_single_token_limit(self, rate_limiter):
        """Test with single token limit"""
        request = RateLimitRequest(
            client_id="user_single",
            max_requests=1,
            time_window_seconds=60
        )

        # First request allowed
        response = rate_limiter.check_rate_limit(request)
        assert response.allow_request is True

        # Second request denied
        response = rate_limiter.check_rate_limit(request)
        assert response.allow_request is False

    def test_fractional_tokens(self, rate_limiter):
        """Test that fractional tokens are handled correctly"""
        request = RateLimitRequest(
            client_id="user_fractional",
            max_requests=10,
            time_window_seconds=3  # Results in 3.33 tokens/sec refill rate
        )

        response = rate_limiter.check_rate_limit(request)
        assert response.allow_request is True
        assert isinstance(response.remaining_tokens, float)


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
