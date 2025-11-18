"""
Comprehensive test suite for RateLimiterFSA.

Tests cover:
- Configuration validation
- Token bucket algorithm
- Leaky bucket algorithm
- Fixed window counting
- Sliding window log
- Quota consumption and tracking
- Quota reset
- Burst handling
- Rate limit enforcement
- Distributed rate limiting
- Retry-After calculation
- Remaining quota retrieval
- Rate metrics collection
- Dynamic limit configuration
- Event emission
- Edge cases and error handling
- Multi-client scenarios
"""

import time
from datetime import datetime, timedelta
from typing import List
from unittest.mock import Mock

import pytest

from agno.fsas.rate_limiter_fsa import (
    AllowedStatus,
    BurstResult,
    ConfigResult,
    ConsumeResult,
    DistributedResult,
    EnforcementResult,
    FixedWindow,
    LeakyBucket,
    QuotaStatus,
    RateLimit Algorithm,
    RateLimitConfig,
    RateLimitEvent,
    RateLimiterFSA,
    RateLimitResult,
    RateLimitStatus,
    RateMetrics,
    Request,
    RequestPriority,
    ResetResult,
    SlidingWindow,
    TokenBucket,
    ValidationResult,
)


# ==================== Fixtures ====================

@pytest.fixture
def rate_limiter_fsa():
    """Create RateLimiterFSA instance for testing."""
    return RateLimiterFSA(
        name="TestRateLimiter",
        default_config=RateLimitConfig(
            algorithm=RateLimitAlgorithm.TOKEN_BUCKET,
            capacity=100,
            refill_rate=10.0,
            burst_capacity=20
        )
    )


@pytest.fixture
def sample_request():
    """Create sample request for testing."""
    return Request(
        client_id="test_client",
        resource="api/endpoint",
        priority=RequestPriority.NORMAL,
        tokens=1
    )


@pytest.fixture
def sample_requests():
    """Create list of sample requests."""
    return [
        Request(client_id=f"client_{i}", resource="api/endpoint", tokens=1)
        for i in range(10)
    ]


# ==================== Test Configuration Validation ====================

def test_validate_valid_config(rate_limiter_fsa):
    """Test validation of a valid configuration."""
    config = RateLimitConfig(
        capacity=100,
        refill_rate=10.0,
        window=timedelta(minutes=1)
    )

    result = rate_limiter_fsa.validate(config)

    assert isinstance(result, ValidationResult)
    assert result.valid is True
    assert len(result.errors) == 0


def test_validate_config_with_invalid_capacity(rate_limiter_fsa):
    """Test validation fails for invalid capacity."""
    config = RateLimitConfig(
        capacity=0,
        refill_rate=10.0
    )

    result = rate_limiter_fsa.validate(config)

    assert result.valid is False
    assert any("capacity" in err.lower() for err in result.errors)


def test_validate_config_with_invalid_refill_rate(rate_limiter_fsa):
    """Test validation fails for invalid refill rate."""
    config = RateLimitConfig(
        capacity=100,
        refill_rate=-5.0
    )

    result = rate_limiter_fsa.validate(config)

    assert result.valid is False
    assert any("refill rate" in err.lower() for err in result.errors)


def test_validate_config_with_invalid_window(rate_limiter_fsa):
    """Test validation fails for invalid window."""
    config = RateLimitConfig(
        capacity=100,
        refill_rate=10.0,
        window=timedelta(seconds=-1)
    )

    result = rate_limiter_fsa.validate(config)

    assert result.valid is False
    assert any("window" in err.lower() for err in result.errors)


# ==================== Test Token Bucket Algorithm ====================

def test_token_bucket_allows_request():
    """Test token bucket allows request when tokens available."""
    bucket = TokenBucket(capacity=10, refill_rate=5.0)

    result = bucket.consume(1)

    assert isinstance(result, AllowedStatus)
    assert result.allowed is True
    assert result.remaining >= 0


def test_token_bucket_rejects_when_empty():
    """Test token bucket rejects when no tokens available."""
    bucket = TokenBucket(capacity=5, refill_rate=1.0)

    # Consume all tokens
    for _ in range(5):
        bucket.consume(1)

    # Next request should be rejected
    result = bucket.consume(1)

    assert result.allowed is False
    assert result.retry_after is not None


def test_token_bucket_refills_over_time():
    """Test token bucket refills tokens over time."""
    bucket = TokenBucket(capacity=10, refill_rate=10.0)

    # Consume all tokens
    for _ in range(10):
        bucket.consume(1)

    # Wait for refill
    time.sleep(0.5)  # Should refill ~5 tokens

    result = bucket.consume(1)
    assert result.allowed is True


def test_token_bucket_get_remaining():
    """Test getting remaining tokens."""
    bucket = TokenBucket(capacity=10, refill_rate=5.0)

    remaining = bucket.get_remaining()

    assert remaining == 10

    bucket.consume(3)
    remaining = bucket.get_remaining()

    assert remaining == 7


def test_rate_limiter_token_bucket_algorithm(rate_limiter_fsa):
    """Test token bucket algorithm through FSA."""
    result = rate_limiter_fsa.token_bucket_algorithm(
        client_id="test_client",
        capacity=10,
        refill_rate=5.0
    )

    assert isinstance(result, AllowedStatus)
    assert result.allowed is True


# ==================== Test Leaky Bucket Algorithm ====================

def test_leaky_bucket_allows_request():
    """Test leaky bucket allows request when capacity available."""
    bucket = LeakyBucket(capacity=10, leak_rate=5.0)

    result = bucket.add(1)

    assert isinstance(result, AllowedStatus)
    assert result.allowed is True


def test_leaky_bucket_rejects_when_full():
    """Test leaky bucket rejects when full."""
    bucket = LeakyBucket(capacity=5, leak_rate=1.0)

    # Fill bucket
    for _ in range(5):
        bucket.add(1)

    # Next request should be rejected
    result = bucket.add(1)

    assert result.allowed is False
    assert result.retry_after is not None


def test_leaky_bucket_leaks_over_time():
    """Test leaky bucket leaks requests over time."""
    bucket = LeakyBucket(capacity=10, leak_rate=10.0)

    # Fill bucket
    for _ in range(10):
        bucket.add(1)

    # Wait for leak
    time.sleep(0.5)  # Should leak ~5 requests

    result = bucket.add(1)
    assert result.allowed is True


def test_rate_limiter_leaky_bucket_algorithm(rate_limiter_fsa):
    """Test leaky bucket algorithm through FSA."""
    result = rate_limiter_fsa.leaky_bucket_algorithm(
        client_id="test_client",
        capacity=10,
        leak_rate=5.0
    )

    assert isinstance(result, AllowedStatus)
    assert result.allowed is True


# ==================== Test Fixed Window Algorithm ====================

def test_fixed_window_allows_request():
    """Test fixed window allows request within limit."""
    window = FixedWindow(limit=10, window=timedelta(minutes=1))

    result = window.check(1)

    assert isinstance(result, AllowedStatus)
    assert result.allowed is True
    assert result.remaining == 9


def test_fixed_window_rejects_when_limit_exceeded():
    """Test fixed window rejects when limit exceeded."""
    window = FixedWindow(limit=5, window=timedelta(minutes=1))

    # Consume all requests
    for _ in range(5):
        window.check(1)

    # Next request should be rejected
    result = window.check(1)

    assert result.allowed is False
    assert result.retry_after is not None


def test_fixed_window_resets_after_window():
    """Test fixed window resets after time window."""
    window = FixedWindow(limit=5, window=timedelta(seconds=1))

    # Consume all requests
    for _ in range(5):
        window.check(1)

    # Wait for window to reset
    time.sleep(1.1)

    result = window.check(1)
    assert result.allowed is True


def test_rate_limiter_fixed_window_algorithm(rate_limiter_fsa):
    """Test fixed window algorithm through FSA."""
    result = rate_limiter_fsa.fixed_window_algorithm(
        client_id="test_client",
        limit=10,
        window=timedelta(minutes=1)
    )

    assert isinstance(result, AllowedStatus)
    assert result.allowed is True


# ==================== Test Sliding Window Algorithm ====================

def test_sliding_window_allows_request():
    """Test sliding window allows request within limit."""
    window = SlidingWindow(limit=10, window=timedelta(minutes=1))

    result = window.check(1)

    assert isinstance(result, AllowedStatus)
    assert result.allowed is True
    assert result.remaining == 9


def test_sliding_window_rejects_when_limit_exceeded():
    """Test sliding window rejects when limit exceeded."""
    window = SlidingWindow(limit=5, window=timedelta(minutes=1))

    # Consume all requests
    for _ in range(5):
        window.check(1)

    # Next request should be rejected
    result = window.check(1)

    assert result.allowed is False


def test_sliding_window_removes_old_requests():
    """Test sliding window removes old requests."""
    window = SlidingWindow(limit=5, window=timedelta(seconds=1))

    # Add requests
    for _ in range(5):
        window.check(1)

    # Wait for requests to expire
    time.sleep(1.1)

    result = window.check(1)
    assert result.allowed is True


def test_rate_limiter_sliding_window_algorithm(rate_limiter_fsa):
    """Test sliding window algorithm through FSA."""
    result = rate_limiter_fsa.sliding_window_algorithm(
        client_id="test_client",
        limit=10,
        window=timedelta(minutes=1)
    )

    assert isinstance(result, AllowedStatus)
    assert result.allowed is True


# ==================== Test Quota Management ====================

def test_consume_quota_success(rate_limiter_fsa):
    """Test successful quota consumption."""
    result = rate_limiter_fsa.consume_quota("test_client", tokens=10)

    assert isinstance(result, ConsumeResult)
    assert result.success is True
    assert result.tokens_consumed == 10
    assert result.remaining_tokens >= 0


def test_consume_quota_insufficient(rate_limiter_fsa):
    """Test quota consumption fails when insufficient."""
    # Set low quota limit
    rate_limiter_fsa.quota_limits["test_client"] = 5

    # Try to consume more than available
    result = rate_limiter_fsa.consume_quota("test_client", tokens=10)

    assert result.success is False
    assert "insufficient" in result.error.lower()


def test_track_quota(rate_limiter_fsa):
    """Test quota tracking."""
    # Consume some quota
    rate_limiter_fsa.consume_quota("test_client", tokens=30)

    # Track quota
    status = rate_limiter_fsa.track_quota("test_client")

    assert isinstance(status, QuotaStatus)
    assert status.client_id == "test_client"
    assert status.current_quota == 30
    assert 0 <= status.quota_percentage <= 100


def test_reset_quota(rate_limiter_fsa):
    """Test quota reset."""
    # Consume quota
    rate_limiter_fsa.consume_quota("test_client", tokens=50)

    # Reset quota
    result = rate_limiter_fsa.reset_quota("test_client")

    assert isinstance(result, ResetResult)
    assert result.success is True
    assert result.previous_quota == 50
    assert result.new_quota == 0

    # Verify quota is reset
    status = rate_limiter_fsa.track_quota("test_client")
    assert status.current_quota == 0


def test_get_remaining_quota(rate_limiter_fsa):
    """Test getting remaining quota."""
    # Set quota limit
    rate_limiter_fsa.quota_limits["test_client"] = 100

    # Consume some quota
    rate_limiter_fsa.consume_quota("test_client", tokens=30)

    # Get remaining
    remaining = rate_limiter_fsa.get_remaining_quota("test_client")

    assert remaining == 70


# ==================== Test Rate Limit Checking ====================

def test_check_rate_limit_allowed(rate_limiter_fsa):
    """Test rate limit check allows request."""
    status = rate_limiter_fsa.check_rate_limit("test_client", "api/endpoint")

    assert isinstance(status, RateLimitStatus)
    assert status.allowed is True
    assert status.client_id == "test_client"
    assert status.resource == "api/endpoint"


def test_check_rate_limit_with_different_algorithms(rate_limiter_fsa):
    """Test rate limit check with different algorithms."""
    algorithms = [
        RateLimitAlgorithm.TOKEN_BUCKET,
        RateLimitAlgorithm.LEAKY_BUCKET,
        RateLimitAlgorithm.FIXED_WINDOW,
        RateLimitAlgorithm.SLIDING_WINDOW
    ]

    for algo in algorithms:
        # Configure resource with algorithm
        rate_limiter_fsa.configure_limit(
            resource=f"test_{algo.value}",
            limit=10,
            period=timedelta(minutes=1),
            algorithm=algo
        )

        # Check rate limit
        status = rate_limiter_fsa.check_rate_limit("test_client", f"test_{algo.value}")

        assert status.allowed is True


# ==================== Test Burst Handling ====================

def test_handle_burst_allowed(rate_limiter_fsa):
    """Test burst handling allows burst."""
    result = rate_limiter_fsa.handle_burst("test_client", burst_capacity=10)

    assert isinstance(result, BurstResult)
    assert result.allowed is True
    assert result.burst_used == 1
    assert result.burst_remaining == 9


def test_handle_burst_exceeded(rate_limiter_fsa):
    """Test burst handling rejects when capacity exceeded."""
    # Use all burst capacity
    for _ in range(10):
        rate_limiter_fsa.handle_burst("test_client", burst_capacity=10)

    # Next burst should be rejected
    result = rate_limiter_fsa.handle_burst("test_client", burst_capacity=10)

    assert result.allowed is False
    assert result.burst_remaining == 0


# ==================== Test Enforcement ====================

def test_enforce_limit_allowed(rate_limiter_fsa):
    """Test enforcement allows request when limit not exceeded."""
    result = rate_limiter_fsa.enforce_limit("test_client", limit_exceeded=False)

    assert isinstance(result, EnforcementResult)
    assert result.allowed is True
    assert result.action == "allow"


def test_enforce_limit_with_burst(rate_limiter_fsa):
    """Test enforcement uses burst when limit exceeded."""
    result = rate_limiter_fsa.enforce_limit("test_client", limit_exceeded=True)

    # Should use burst capacity
    assert result.action in ["burst", "reject"]


def test_enforce_limit_rejected(rate_limiter_fsa):
    """Test enforcement rejects when limit exceeded and no burst."""
    # Disable burst
    rate_limiter_fsa.default_config.enable_burst = False

    result = rate_limiter_fsa.enforce_limit("test_client", limit_exceeded=True)

    assert result.allowed is False
    assert result.action == "reject"
    assert result.retry_after is not None


# ==================== Test Distributed Rate Limiting ====================

def test_distributed_rate_limit_without_redis(rate_limiter_fsa):
    """Test distributed rate limiting without Redis client."""
    result = rate_limiter_fsa.distributed_rate_limit("test_client")

    assert isinstance(result, DistributedResult)
    assert result.success is False
    assert "not configured" in result.error.lower()


def test_distributed_rate_limit_with_mock_redis(rate_limiter_fsa):
    """Test distributed rate limiting with mock Redis client."""
    # Create mock Redis client
    mock_redis = Mock()

    result = rate_limiter_fsa.distributed_rate_limit("test_client", mock_redis)

    assert isinstance(result, DistributedResult)
    # Should fall back to local rate limiting
    assert result.success is True


# ==================== Test Metrics ====================

def test_collect_rate_metrics(rate_limiter_fsa, sample_request):
    """Test rate metrics collection."""
    # Execute some requests
    for _ in range(5):
        rate_limiter_fsa.execute(sample_request)

    # Collect metrics
    metrics = rate_limiter_fsa.collect_rate_metrics(
        "test_client",
        time_window=timedelta(minutes=1)
    )

    assert isinstance(metrics, RateMetrics)
    assert metrics.client_id == "test_client"
    assert metrics.total_requests >= 5


def test_metrics_with_rejections(rate_limiter_fsa):
    """Test metrics track rejections correctly."""
    # Configure strict limit
    rate_limiter_fsa.configure_limit(
        resource="strict",
        limit=3,
        period=timedelta(minutes=1)
    )

    # Make requests (some will be rejected)
    for i in range(10):
        request = Request(client_id="test_client", resource="strict", tokens=1)
        rate_limiter_fsa.execute(request)

    # Collect metrics
    metrics = rate_limiter_fsa.collect_rate_metrics("test_client")

    assert metrics.rejected_requests > 0


# ==================== Test Configuration ====================

def test_configure_limit(rate_limiter_fsa):
    """Test configuring rate limits."""
    result = rate_limiter_fsa.configure_limit(
        resource="api/v1",
        limit=100,
        period=timedelta(minutes=1)
    )

    assert isinstance(result, ConfigResult)
    assert result.success is True
    assert result.resource == "api/v1"
    assert result.new_limit == 100


def test_configure_limit_updates_existing(rate_limiter_fsa):
    """Test configuring limit updates existing configuration."""
    # Set initial limit
    rate_limiter_fsa.configure_limit("api/v1", limit=50, period=timedelta(minutes=1))

    # Update limit
    result = rate_limiter_fsa.configure_limit("api/v1", limit=100, period=timedelta(minutes=1))

    assert result.success is True
    assert result.previous_limit == 50
    assert result.new_limit == 100


# ==================== Test Event Handling ====================

def test_emit_rate_limit_event(rate_limiter_fsa):
    """Test event emission."""
    events_received = []

    def event_listener(client_id, event_type):
        events_received.append((client_id, event_type))

    # Add listener
    rate_limiter_fsa.add_event_listener(
        RateLimitEvent.REQUEST_ALLOWED,
        event_listener
    )

    # Emit event
    rate_limiter_fsa.emit_rate_limit_event(
        "test_client",
        RateLimitEvent.REQUEST_ALLOWED
    )

    assert len(events_received) == 1
    assert events_received[0] == ("test_client", RateLimitEvent.REQUEST_ALLOWED)


def test_event_on_quota_consumed(rate_limiter_fsa):
    """Test event emitted on quota consumption."""
    events_received = []

    def event_listener(client_id, event_type):
        events_received.append(event_type)

    rate_limiter_fsa.add_event_listener(
        RateLimitEvent.QUOTA_CONSUMED,
        event_listener
    )

    # Consume quota
    rate_limiter_fsa.consume_quota("test_client", tokens=10)

    assert RateLimitEvent.QUOTA_CONSUMED in events_received


def test_event_on_limit_exceeded(rate_limiter_fsa):
    """Test event emitted when limit exceeded."""
    events_received = []

    def event_listener(client_id, event_type):
        events_received.append(event_type)

    rate_limiter_fsa.add_event_listener(
        RateLimitEvent.LIMIT_EXCEEDED,
        event_listener
    )

    # Disable burst to force limit exceeded
    rate_limiter_fsa.default_config.enable_burst = False

    # Force limit exceeded
    rate_limiter_fsa.enforce_limit("test_client", limit_exceeded=True)

    assert RateLimitEvent.LIMIT_EXCEEDED in events_received


# ==================== Test Main Execute Pipeline ====================

def test_execute_allows_request(rate_limiter_fsa, sample_request):
    """Test execute pipeline allows valid request."""
    result = rate_limiter_fsa.execute(sample_request)

    assert isinstance(result, RateLimitResult)
    assert result.success is True
    assert result.allowed is True
    assert result.client_id == "test_client"


def test_execute_rejects_request_without_client_id(rate_limiter_fsa):
    """Test execute rejects request without client ID."""
    request = Request(client_id="", resource="api/endpoint")

    result = rate_limiter_fsa.execute(request)

    assert result.success is False
    assert result.allowed is False
    assert "required" in result.error.lower()


def test_execute_with_rate_limit_exceeded(rate_limiter_fsa):
    """Test execute rejects when rate limit exceeded."""
    # Configure strict limit
    rate_limiter_fsa.configure_limit(
        resource="strict",
        limit=5,
        period=timedelta(minutes=1),
        algorithm=RateLimitAlgorithm.FIXED_WINDOW
    )

    # Make requests until limit exceeded
    results = []
    for i in range(10):
        request = Request(client_id="test_client", resource="strict", tokens=1)
        result = rate_limiter_fsa.execute(request)
        results.append(result)

    # Some requests should be rejected
    rejected = [r for r in results if not r.allowed]
    assert len(rejected) > 0


# ==================== Test Retry After Calculation ====================

def test_calculate_retry_after(rate_limiter_fsa):
    """Test retry-after calculation."""
    retry_after = rate_limiter_fsa.calculate_retry_after("test_client")

    assert isinstance(retry_after, timedelta)
    assert retry_after >= timedelta(0)


# ==================== Test Edge Cases ====================

def test_zero_quota_consumption(rate_limiter_fsa):
    """Test consuming zero tokens."""
    result = rate_limiter_fsa.consume_quota("test_client", tokens=0)

    assert result.success is True
    assert result.tokens_consumed == 0


def test_multiple_clients_independent_limits(rate_limiter_fsa):
    """Test multiple clients have independent rate limits."""
    # Make requests from different clients
    client1_requests = [
        rate_limiter_fsa.execute(Request(client_id="client1", resource="api", tokens=1))
        for _ in range(5)
    ]

    client2_requests = [
        rate_limiter_fsa.execute(Request(client_id="client2", resource="api", tokens=1))
        for _ in range(5)
    ]

    # Both clients should have successful requests
    assert all(r.success for r in client1_requests)
    assert all(r.success for r in client2_requests)

    # Metrics should be separate
    metrics1 = rate_limiter_fsa.collect_rate_metrics("client1")
    metrics2 = rate_limiter_fsa.collect_rate_metrics("client2")

    assert metrics1.total_requests == 5
    assert metrics2.total_requests == 5


def test_concurrent_requests(rate_limiter_fsa):
    """Test thread safety with concurrent requests."""
    import threading

    results = []
    lock = threading.Lock()

    def make_request():
        request = Request(client_id="concurrent_client", resource="api", tokens=1)
        result = rate_limiter_fsa.execute(request)
        with lock:
            results.append(result)

    # Create multiple threads
    threads = [threading.Thread(target=make_request) for _ in range(20)]

    # Start all threads
    for t in threads:
        t.start()

    # Wait for completion
    for t in threads:
        t.join()

    # Verify all requests were processed
    assert len(results) == 20


def test_high_priority_request(rate_limiter_fsa):
    """Test high priority requests."""
    request = Request(
        client_id="test_client",
        resource="api/endpoint",
        priority=RequestPriority.HIGH,
        tokens=1
    )

    result = rate_limiter_fsa.execute(request)

    assert result.success is True
    assert result.allowed is True


def test_burst_event_counting(rate_limiter_fsa):
    """Test burst events are counted correctly."""
    # Trigger multiple bursts
    for _ in range(5):
        rate_limiter_fsa.handle_burst("test_client", burst_capacity=10)

    # Check metrics
    metrics = rate_limiter_fsa.collect_rate_metrics("test_client")

    assert metrics.burst_events == 5
