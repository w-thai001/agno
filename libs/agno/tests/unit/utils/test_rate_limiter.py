"""Tests for rate limiter token bucket implementation"""

import time
from threading import Thread

import pytest

from agno.utils.rate_limiter import RateLimiter, RateLimitState, TokenBucket


class TestTokenBucket:
    """Test TokenBucket class"""

    def test_init_default_tokens(self):
        """Test initialization with default tokens"""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        assert bucket.capacity == 10
        assert bucket.refill_rate == 1.0
        assert bucket.available() == 10

    def test_init_custom_tokens(self):
        """Test initialization with custom tokens"""
        bucket = TokenBucket(capacity=10, refill_rate=1.0, initial_tokens=5)
        assert bucket.available() == 5

    def test_init_invalid_capacity(self):
        """Test initialization with invalid capacity"""
        with pytest.raises(ValueError):
            TokenBucket(capacity=0, refill_rate=1.0)
        with pytest.raises(ValueError):
            TokenBucket(capacity=-10, refill_rate=1.0)

    def test_init_invalid_refill_rate(self):
        """Test initialization with invalid refill rate"""
        with pytest.raises(ValueError):
            TokenBucket(capacity=10, refill_rate=0)
        with pytest.raises(ValueError):
            TokenBucket(capacity=10, refill_rate=-1)

    def test_init_invalid_initial_tokens(self):
        """Test initialization with invalid initial tokens"""
        with pytest.raises(ValueError):
            TokenBucket(capacity=10, refill_rate=1.0, initial_tokens=-1)
        with pytest.raises(ValueError):
            TokenBucket(capacity=10, refill_rate=1.0, initial_tokens=15)

    def test_check_available(self):
        """Test checking token availability"""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        assert bucket.check(5) is True
        assert bucket.check(10) is True
        assert bucket.check(11) is False

    def test_check_invalid_tokens(self):
        """Test checking with invalid token count"""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        with pytest.raises(ValueError):
            bucket.check(0)
        with pytest.raises(ValueError):
            bucket.check(-5)

    def test_consume_tokens(self):
        """Test consuming tokens"""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        assert bucket.consume(5) is True
        assert bucket.available() == 5
        assert bucket.consume(5) is True
        assert bucket.available() == 0
        assert bucket.consume(1) is False

    def test_consume_insufficient_tokens(self):
        """Test consuming more tokens than available"""
        bucket = TokenBucket(capacity=10, refill_rate=1.0, initial_tokens=3)
        assert bucket.consume(5) is False
        assert bucket.available() == 3  # No tokens should be consumed

    def test_consume_invalid_tokens(self):
        """Test consuming with invalid token count"""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        with pytest.raises(ValueError):
            bucket.consume(0)
        with pytest.raises(ValueError):
            bucket.consume(-5)

    def test_try_consume_success(self):
        """Test try_consume when successful"""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        success, wait_time = bucket.try_consume(5)
        assert success is True
        assert wait_time == 0.0
        assert bucket.available() == 5

    def test_try_consume_failure(self):
        """Test try_consume when insufficient tokens"""
        bucket = TokenBucket(capacity=10, refill_rate=2.0, initial_tokens=3)
        success, wait_time = bucket.try_consume(5)
        assert success is False
        assert wait_time == 1.0  # Need 2 more tokens at 2/sec = 1 second

    def test_refill_automatic(self):
        """Test automatic time-based refill"""
        bucket = TokenBucket(capacity=10, refill_rate=10.0, initial_tokens=0)
        time.sleep(0.5)  # Wait 0.5 seconds
        tokens = bucket.available()
        assert tokens >= 4.0  # Should have ~5 tokens (allowing some variance)
        assert tokens <= 6.0

    def test_refill_manual(self):
        """Test manual refill"""
        bucket = TokenBucket(capacity=10, refill_rate=1.0, initial_tokens=0)
        result = bucket.refill(5)
        assert result == 5
        assert bucket.available() == 5

    def test_refill_exceeds_capacity(self):
        """Test refill doesn't exceed capacity"""
        bucket = TokenBucket(capacity=10, refill_rate=1.0, initial_tokens=8)
        bucket.refill(5)
        assert bucket.available() == 10  # Should cap at capacity

    def test_refill_invalid(self):
        """Test manual refill with invalid tokens"""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        with pytest.raises(ValueError):
            bucket.refill(-5)

    def test_reset_default(self):
        """Test reset to capacity"""
        bucket = TokenBucket(capacity=10, refill_rate=1.0, initial_tokens=0)
        bucket.reset()
        assert bucket.available() == 10

    def test_reset_custom(self):
        """Test reset to custom value"""
        bucket = TokenBucket(capacity=10, refill_rate=1.0, initial_tokens=0)
        bucket.reset(7)
        assert bucket.available() == 7

    def test_reset_invalid(self):
        """Test reset with invalid tokens"""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        with pytest.raises(ValueError):
            bucket.reset(-1)
        with pytest.raises(ValueError):
            bucket.reset(15)

    def test_state_idle(self):
        """Test FSA state when idle"""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        assert bucket.state == RateLimitState.IDLE

    def test_state_refilling(self):
        """Test FSA state when refilling"""
        bucket = TokenBucket(capacity=10, refill_rate=1.0, initial_tokens=0.5)
        assert bucket.state == RateLimitState.REFILLING

    def test_state_throttled(self):
        """Test FSA state when throttled (refill_rate=0)"""
        bucket = TokenBucket(capacity=10, refill_rate=0.1, initial_tokens=0.5)
        # With refill_rate > 0 and tokens < 1, should be REFILLING
        assert bucket.state == RateLimitState.REFILLING

    def test_repr(self):
        """Test string representation"""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        repr_str = repr(bucket)
        assert "TokenBucket" in repr_str
        assert "capacity=10" in repr_str
        assert "refill_rate=1.0" in repr_str

    def test_thread_safety(self):
        """Test thread safety of token bucket"""
        bucket = TokenBucket(capacity=100, refill_rate=10.0)
        results = []

        def consume_tokens():
            for _ in range(10):
                results.append(bucket.consume(1))
                time.sleep(0.01)

        threads = [Thread(target=consume_tokens) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # All 50 consumes should succeed (100 initial tokens)
        assert sum(results) == 50


class TestRateLimiter:
    """Test RateLimiter class"""

    def test_init(self):
        """Test initialization"""
        limiter = RateLimiter(capacity=10, refill_rate=1.0)
        assert limiter._capacity == 10
        assert limiter._refill_rate == 1.0

    def test_check_new_key(self):
        """Test checking tokens for new key"""
        limiter = RateLimiter(capacity=10, refill_rate=1.0)
        assert limiter.check("user1", 5) is True
        assert limiter.check("user1", 15) is False

    def test_consume_new_key(self):
        """Test consuming tokens for new key"""
        limiter = RateLimiter(capacity=10, refill_rate=1.0)
        assert limiter.consume("user1", 5) is True
        assert limiter.available("user1") == 5

    def test_multiple_keys(self):
        """Test multiple independent keys"""
        limiter = RateLimiter(capacity=10, refill_rate=1.0)
        assert limiter.consume("user1", 5) is True
        assert limiter.consume("user2", 3) is True
        assert limiter.available("user1") == 5
        assert limiter.available("user2") == 7

    def test_try_consume(self):
        """Test try_consume for key"""
        limiter = RateLimiter(capacity=10, refill_rate=2.0)
        limiter.consume("user1", 8)
        success, wait_time = limiter.try_consume("user1", 5)
        assert success is False
        assert wait_time == 1.5  # Need 3 more tokens at 2/sec

    def test_reset_key(self):
        """Test resetting a key"""
        limiter = RateLimiter(capacity=10, refill_rate=1.0)
        limiter.consume("user1", 8)
        limiter.reset("user1")
        assert limiter.available("user1") == 10

    def test_clear(self):
        """Test clearing all buckets"""
        limiter = RateLimiter(capacity=10, refill_rate=1.0)
        limiter.consume("user1", 5)
        limiter.consume("user2", 3)
        limiter.clear()
        # After clear, new buckets should be created with full capacity
        assert limiter.available("user1") == 10
        assert limiter.available("user2") == 10

    def test_max_buckets_lru(self):
        """Test LRU eviction when max buckets reached"""
        limiter = RateLimiter(capacity=10, refill_rate=1.0, max_buckets=3)
        limiter.consume("user1", 1)
        limiter.consume("user2", 1)
        limiter.consume("user3", 1)
        limiter.consume("user4", 1)  # Should evict user1
        # user1 should be evicted, so new bucket with full capacity
        assert limiter.available("user1") == 10

    def test_repr(self):
        """Test string representation"""
        limiter = RateLimiter(capacity=10, refill_rate=1.0)
        limiter.consume("user1", 1)
        repr_str = repr(limiter)
        assert "RateLimiter" in repr_str
        assert "capacity=10" in repr_str
        assert "refill_rate=1.0" in repr_str
        assert "buckets=1" in repr_str
