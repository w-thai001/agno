"""
Unit tests for rate limiter implementations.

These tests use a mock Redis client for unit testing without requiring
a live Redis instance. For integration tests with real Redis, see
tests/integration/utils/test_rate_limiter_integration.py
"""

import time
from unittest.mock import Mock, patch

import pytest


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    mock = Mock()
    mock.script_load = Mock(return_value="test_sha")
    mock.evalsha = Mock()
    mock.delete = Mock(return_value=1)
    mock.hmget = Mock(return_value=["10.0", str(time.time())])
    return mock


class TestTokenBucketRateLimiter:
    """Test TokenBucketRateLimiter class."""

    def test_import_without_redis_raises_error(self):
        """Test that importing without redis-py raises ImportError."""
        with patch("agno.utils.rate_limiter.REDIS_AVAILABLE", False):
            from agno.utils.rate_limiter import TokenBucketRateLimiter

            with pytest.raises(ImportError, match="redis-py is required"):
                TokenBucketRateLimiter()

    def test_initialization_with_url(self, mock_redis):
        """Test initialization with Redis URL."""
        with patch("redis.from_url", return_value=mock_redis):
            from agno.utils.rate_limiter import TokenBucketRateLimiter

            limiter = TokenBucketRateLimiter(
                redis_client="redis://localhost:6379/0",
                default_max_requests=100,
                default_time_window_seconds=60,
            )

            assert limiter.default_max_requests == 100
            assert limiter.default_time_window_seconds == 60
            assert limiter.key_prefix == "rate_limit"

    def test_initialization_with_client(self, mock_redis):
        """Test initialization with Redis client instance."""
        from agno.utils.rate_limiter import TokenBucketRateLimiter

        limiter = TokenBucketRateLimiter(
            redis_client=mock_redis,
            key_prefix="custom_prefix",
        )

        assert limiter.key_prefix == "custom_prefix"
        assert limiter._redis == mock_redis

    def test_allow_request_success(self, mock_redis):
        """Test successful request allowance."""
        # Mock Redis to return: allowed=1, remaining=99, retry_after=0
        mock_redis.evalsha.return_value = [1, 99, 0.0]

        from agno.utils.rate_limiter import TokenBucketRateLimiter

        limiter = TokenBucketRateLimiter(redis_client=mock_redis)
        result = limiter.allow_request("client_123")

        assert result.allow_request is True
        assert result.remaining_tokens == 99
        assert result.retry_after_seconds == 0.0

    def test_allow_request_rate_limited(self, mock_redis):
        """Test rate limited request."""
        # Mock Redis to return: allowed=0, remaining=0, retry_after=5.5
        mock_redis.evalsha.return_value = [0, 0, 5.5]

        from agno.utils.rate_limiter import TokenBucketRateLimiter

        limiter = TokenBucketRateLimiter(redis_client=mock_redis)
        result = limiter.allow_request("client_123")

        assert result.allow_request is False
        assert result.remaining_tokens == 0
        assert result.retry_after_seconds == 5.5

    def test_allow_request_with_custom_limits(self, mock_redis):
        """Test request with custom limits."""
        mock_redis.evalsha.return_value = [1, 49, 0.0]

        from agno.utils.rate_limiter import TokenBucketRateLimiter

        limiter = TokenBucketRateLimiter(redis_client=mock_redis)
        result = limiter.allow_request(
            "client_123", max_requests=50, time_window_seconds=30
        )

        assert result.allow_request is True
        # Verify the evalsha was called with correct refill rate
        # refill_rate = 50 / 30 = 1.666...
        args = mock_redis.evalsha.call_args
        assert args[0][2] == 50  # max_requests
        assert abs(args[0][3] - 1.6666666666666667) < 0.0001  # refill_rate

    def test_allow_request_multiple_tokens(self, mock_redis):
        """Test requesting multiple tokens at once."""
        mock_redis.evalsha.return_value = [1, 95, 0.0]

        from agno.utils.rate_limiter import TokenBucketRateLimiter

        limiter = TokenBucketRateLimiter(redis_client=mock_redis)
        result = limiter.allow_request("client_123", tokens_requested=5)

        # Verify tokens_requested was passed
        args = mock_redis.evalsha.call_args
        assert args[0][5] == 5  # tokens_requested

    def test_key_generation(self, mock_redis):
        """Test Redis key generation."""
        from agno.utils.rate_limiter import TokenBucketRateLimiter

        limiter = TokenBucketRateLimiter(
            redis_client=mock_redis, key_prefix="test_prefix"
        )

        key = limiter._get_key("client_123")
        assert key == "test_prefix:client_123"

    def test_reset_client(self, mock_redis):
        """Test resetting a client's rate limit."""
        from agno.utils.rate_limiter import TokenBucketRateLimiter

        limiter = TokenBucketRateLimiter(redis_client=mock_redis)
        result = limiter.reset_client("client_123")

        assert result is True
        mock_redis.delete.assert_called_once()

    def test_get_client_info(self, mock_redis):
        """Test getting client information."""
        current_time = time.time()
        mock_redis.hmget.return_value = ["42.5", str(current_time)]

        from agno.utils.rate_limiter import TokenBucketRateLimiter

        limiter = TokenBucketRateLimiter(redis_client=mock_redis)
        info = limiter.get_client_info("client_123")

        assert info is not None
        tokens, last_refill = info
        assert tokens == 42.5
        assert abs(last_refill - current_time) < 0.001

    def test_get_client_info_nonexistent(self, mock_redis):
        """Test getting info for non-existent client."""
        mock_redis.hmget.return_value = [None, None]

        from agno.utils.rate_limiter import TokenBucketRateLimiter

        limiter = TokenBucketRateLimiter(redis_client=mock_redis)
        info = limiter.get_client_info("nonexistent")

        assert info is None

    def test_context_manager(self, mock_redis):
        """Test using rate limiter as context manager."""
        from agno.utils.rate_limiter import TokenBucketRateLimiter

        with TokenBucketRateLimiter(redis_client=mock_redis) as limiter:
            assert limiter is not None

        # close() should be called
        if hasattr(mock_redis, "close"):
            mock_redis.close.assert_called_once()

    def test_redis_error_fails_open(self, mock_redis):
        """Test that Redis errors cause the limiter to fail open."""
        import redis

        mock_redis.evalsha.side_effect = redis.RedisError("Connection failed")

        from agno.utils.rate_limiter import TokenBucketRateLimiter

        limiter = TokenBucketRateLimiter(redis_client=mock_redis)
        result = limiter.allow_request("client_123")

        # Should fail open (allow the request)
        assert result.allow_request is True
        assert result.remaining_tokens == limiter.default_max_requests


class TestSlidingWindowRateLimiter:
    """Test SlidingWindowRateLimiter class."""

    def test_import_without_redis_raises_error(self):
        """Test that importing without redis-py raises ImportError."""
        with patch("agno.utils.rate_limiter.REDIS_AVAILABLE", False):
            from agno.utils.rate_limiter import SlidingWindowRateLimiter

            with pytest.raises(ImportError, match="redis-py is required"):
                SlidingWindowRateLimiter()

    def test_initialization(self, mock_redis):
        """Test initialization."""
        from agno.utils.rate_limiter import SlidingWindowRateLimiter

        limiter = SlidingWindowRateLimiter(
            redis_client=mock_redis,
            default_max_requests=50,
            default_time_window_seconds=30,
        )

        assert limiter.default_max_requests == 50
        assert limiter.default_time_window_seconds == 30
        assert limiter.key_prefix == "sliding_window"

    def test_allow_request_success(self, mock_redis):
        """Test successful request with sliding window."""
        # Mock Redis to return: allowed=1, remaining=49, retry_after=0
        mock_redis.evalsha.return_value = [1, 49, 0.0]

        from agno.utils.rate_limiter import SlidingWindowRateLimiter

        limiter = SlidingWindowRateLimiter(redis_client=mock_redis)
        result = limiter.allow_request("client_456")

        assert result.allow_request is True
        assert result.remaining_tokens == 49
        assert result.retry_after_seconds == 0.0

    def test_allow_request_rate_limited(self, mock_redis):
        """Test rate limited request with sliding window."""
        # Mock Redis to return: allowed=0, remaining=0, retry_after=10.0
        mock_redis.evalsha.return_value = [0, 0, 10.0]

        from agno.utils.rate_limiter import SlidingWindowRateLimiter

        limiter = SlidingWindowRateLimiter(redis_client=mock_redis)
        result = limiter.allow_request("client_456")

        assert result.allow_request is False
        assert result.remaining_tokens == 0
        assert result.retry_after_seconds == 10.0

    def test_reset_client(self, mock_redis):
        """Test resetting client in sliding window."""
        from agno.utils.rate_limiter import SlidingWindowRateLimiter

        limiter = SlidingWindowRateLimiter(redis_client=mock_redis)
        result = limiter.reset_client("client_456")

        assert result is True
        mock_redis.delete.assert_called_once()

    def test_context_manager(self, mock_redis):
        """Test using sliding window as context manager."""
        from agno.utils.rate_limiter import SlidingWindowRateLimiter

        with SlidingWindowRateLimiter(redis_client=mock_redis) as limiter:
            assert limiter is not None


class TestRateLimitResult:
    """Test RateLimitResult dataclass."""

    def test_rate_limit_result_creation(self):
        """Test creating RateLimitResult."""
        from agno.utils.rate_limiter import RateLimitResult

        result = RateLimitResult(
            allow_request=True, remaining_tokens=50, retry_after_seconds=0.0
        )

        assert result.allow_request is True
        assert result.remaining_tokens == 50
        assert result.retry_after_seconds == 0.0

    def test_rate_limit_result_equality(self):
        """Test RateLimitResult equality."""
        from agno.utils.rate_limiter import RateLimitResult

        result1 = RateLimitResult(
            allow_request=True, remaining_tokens=50, retry_after_seconds=0.0
        )
        result2 = RateLimitResult(
            allow_request=True, remaining_tokens=50, retry_after_seconds=0.0
        )

        assert result1 == result2
