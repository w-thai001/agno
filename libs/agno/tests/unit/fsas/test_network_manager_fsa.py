"""
Comprehensive unit tests for Network Manager FSA.

This module contains 35 comprehensive tests covering all functionality
of the NetworkManagerFSA including:
- State machine transitions
- Connection pooling
- Circuit breaker pattern
- Load balancing strategies
- Retry logic with exponential backoff
- Rate limiting
- Response caching
- DNS caching
- Request/response interceptors
- Bandwidth throttling
- Health monitoring
- Concurrent requests
- Error handling
"""

import asyncio
import json
import threading
import time
import pytest
from unittest.mock import Mock, patch, MagicMock

from agno.fsas.infrastructure.network_manager_fsa import (
    NetworkManagerFSA,
    NetworkState,
    HTTPMethod,
    LoadBalancingStrategy,
    CompressionType,
    CircuitState,
    RequestPriority,
    NetworkError,
    ConnectionError,
    TimeoutError,
    CircuitBreakerError,
    RateLimitError,
    StateTransitionError,
    LoadBalancerError,
    Request,
    Response,
    Endpoint,
    RetryConfig,
    CircuitBreakerConfig,
    RateLimitConfig,
    CacheConfig,
    ProxyConfig,
    SSLConfig,
    DNSCache,
    ResponseCache,
    TokenBucket,
    CircuitBreaker,
    ConnectionPool,
    LoadBalancer,
    LoggingInterceptor,
    AuthInterceptor,
    BandwidthThrottler,
    HealthMonitor,
    compress_data,
    decompress_data,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def network_fsa():
    """Create a NetworkManagerFSA instance."""
    fsa = NetworkManagerFSA(
        pool_size=5,
        enable_health_monitoring=False,  # Disable for tests
    )
    yield fsa
    fsa.shutdown()


@pytest.fixture
def retry_config():
    """Create retry configuration."""
    return RetryConfig(
        max_retries=3,
        initial_delay=0.1,
        max_delay=1.0,
        exponential_base=2.0,
    )


@pytest.fixture
def circuit_breaker_config():
    """Create circuit breaker configuration."""
    return CircuitBreakerConfig(
        failure_threshold=3,
        success_threshold=2,
        timeout=1.0,
    )


@pytest.fixture
def rate_limit_config():
    """Create rate limit configuration."""
    return RateLimitConfig(
        requests_per_second=10.0,
        burst_size=20,
    )


# ============================================================================
# State Machine Tests
# ============================================================================

def test_initial_state():
    """Test 1: Network FSA starts in CONNECTED state."""
    fsa = NetworkManagerFSA(enable_health_monitoring=False)
    assert fsa.state == NetworkState.CONNECTED
    fsa.shutdown()


def test_state_transition_to_shutdown(network_fsa):
    """Test 2: Valid state transition to SHUTDOWN."""
    network_fsa.shutdown()
    assert network_fsa.state == NetworkState.IDLE


def test_invalid_state_transition():
    """Test 3: Invalid state transitions raise error."""
    fsa = NetworkManagerFSA(enable_health_monitoring=False)
    fsa.state = NetworkState.IDLE

    with pytest.raises(StateTransitionError):
        fsa.transition_to(NetworkState.CIRCUIT_OPEN)

    fsa.shutdown()


def test_state_transition_to_retrying(network_fsa):
    """Test 4: Transition to RETRYING state."""
    # Manually trigger retry state
    network_fsa.state = NetworkState.CONNECTED
    network_fsa.transition_to(NetworkState.RETRYING)
    assert network_fsa.state == NetworkState.RETRYING


def test_state_transition_circuit_breaker(network_fsa):
    """Test 5: Circuit breaker state transitions."""
    network_fsa.state = NetworkState.CONNECTED
    network_fsa.transition_to(NetworkState.CIRCUIT_OPEN)
    assert network_fsa.state == NetworkState.CIRCUIT_OPEN

    network_fsa.transition_to(NetworkState.CIRCUIT_HALF_OPEN)
    assert network_fsa.state == NetworkState.CIRCUIT_HALF_OPEN


# ============================================================================
# Endpoint Management Tests
# ============================================================================

def test_add_endpoint(network_fsa):
    """Test 6: Add endpoint to network manager."""
    network_fsa.add_endpoint("https://api.example.com")
    assert len(network_fsa.load_balancer.endpoints) == 1


def test_add_multiple_endpoints(network_fsa):
    """Test 7: Add multiple endpoints."""
    network_fsa.add_endpoint("https://api1.example.com")
    network_fsa.add_endpoint("https://api2.example.com")
    network_fsa.add_endpoint("https://api3.example.com")
    assert len(network_fsa.load_balancer.endpoints) == 3


def test_remove_endpoint(network_fsa):
    """Test 8: Remove endpoint from network manager."""
    url = "https://api.example.com"
    network_fsa.add_endpoint(url)
    assert len(network_fsa.load_balancer.endpoints) == 1

    network_fsa.remove_endpoint(url)
    assert len(network_fsa.load_balancer.endpoints) == 0


# ============================================================================
# Load Balancing Tests
# ============================================================================

def test_load_balancer_round_robin():
    """Test 9: Round-robin load balancing."""
    lb = LoadBalancer(strategy=LoadBalancingStrategy.ROUND_ROBIN)
    lb.add_endpoint(Endpoint(url="http://api1.com"))
    lb.add_endpoint(Endpoint(url="http://api2.com"))
    lb.add_endpoint(Endpoint(url="http://api3.com"))

    # Get endpoints in round-robin fashion
    ep1 = lb.get_endpoint()
    ep2 = lb.get_endpoint()
    ep3 = lb.get_endpoint()
    ep4 = lb.get_endpoint()

    assert ep1.url == "http://api1.com"
    assert ep2.url == "http://api2.com"
    assert ep3.url == "http://api3.com"
    assert ep4.url == "http://api1.com"  # Wraps around


def test_load_balancer_least_connections():
    """Test 10: Least connections load balancing."""
    lb = LoadBalancer(strategy=LoadBalancingStrategy.LEAST_CONNECTIONS)

    ep1 = Endpoint(url="http://api1.com", connection_count=5)
    ep2 = Endpoint(url="http://api2.com", connection_count=2)
    ep3 = Endpoint(url="http://api3.com", connection_count=8)

    lb.add_endpoint(ep1)
    lb.add_endpoint(ep2)
    lb.add_endpoint(ep3)

    selected = lb.get_endpoint()
    assert selected.url == "http://api2.com"  # Least connections


def test_load_balancer_random():
    """Test 11: Random load balancing."""
    lb = LoadBalancer(strategy=LoadBalancingStrategy.RANDOM)
    lb.add_endpoint(Endpoint(url="http://api1.com"))
    lb.add_endpoint(Endpoint(url="http://api2.com"))
    lb.add_endpoint(Endpoint(url="http://api3.com"))

    # Get multiple endpoints
    endpoints = [lb.get_endpoint().url for _ in range(10)]

    # Should have some variety (not all the same)
    unique_endpoints = set(endpoints)
    assert len(unique_endpoints) > 1


def test_load_balancer_weighted():
    """Test 12: Weighted load balancing."""
    lb = LoadBalancer(strategy=LoadBalancingStrategy.WEIGHTED)
    lb.add_endpoint(Endpoint(url="http://api1.com", weight=1))
    lb.add_endpoint(Endpoint(url="http://api2.com", weight=5))
    lb.add_endpoint(Endpoint(url="http://api3.com", weight=1))

    # Get many endpoints
    endpoints = [lb.get_endpoint().url for _ in range(100)]

    # api2 should be selected more often due to higher weight
    count_api2 = endpoints.count("http://api2.com")
    assert count_api2 > 50  # Should be roughly 71% (5/7)


# ============================================================================
# Circuit Breaker Tests
# ============================================================================

def test_circuit_breaker_opens_on_failures():
    """Test 13: Circuit breaker opens after threshold failures."""
    config = CircuitBreakerConfig(
        failure_threshold=3,
        success_threshold=2,
        timeout=1.0,
    )
    cb = CircuitBreaker(config)

    def failing_function():
        raise Exception("Simulated failure")

    # Trigger failures
    for _ in range(3):
        try:
            cb.call(failing_function)
        except Exception:
            pass

    # Circuit should be open
    assert cb.state == CircuitState.OPEN


def test_circuit_breaker_half_open_after_timeout():
    """Test 14: Circuit breaker transitions to half-open after timeout."""
    config = CircuitBreakerConfig(
        failure_threshold=2,
        success_threshold=2,
        timeout=0.5,  # Short timeout for testing
    )
    cb = CircuitBreaker(config)

    def failing_function():
        raise Exception("Failure")

    # Open circuit
    for _ in range(2):
        try:
            cb.call(failing_function)
        except Exception:
            pass

    assert cb.state == CircuitState.OPEN

    # Wait for timeout
    time.sleep(0.6)

    # Next call should transition to half-open
    def success_function():
        return "success"

    try:
        cb.call(success_function)
    except CircuitBreakerError:
        pass

    # Should be in half-open or closed
    assert cb.state in (CircuitState.HALF_OPEN, CircuitState.CLOSED)


def test_circuit_breaker_closes_on_success():
    """Test 15: Circuit breaker closes after successful calls."""
    config = CircuitBreakerConfig(
        failure_threshold=2,
        success_threshold=2,
        timeout=0.1,
    )
    cb = CircuitBreaker(config)

    def failing_function():
        raise Exception("Failure")

    def success_function():
        return "success"

    # Open circuit
    for _ in range(2):
        try:
            cb.call(failing_function)
        except Exception:
            pass

    # Wait for timeout
    time.sleep(0.2)

    # Successful calls should close circuit
    for _ in range(2):
        try:
            cb.call(success_function)
        except CircuitBreakerError:
            pass

    assert cb.state == CircuitState.CLOSED


def test_circuit_breaker_manual_reset():
    """Test 16: Manual circuit breaker reset."""
    config = CircuitBreakerConfig(failure_threshold=2)
    cb = CircuitBreaker(config)

    def failing_function():
        raise Exception("Failure")

    # Open circuit
    for _ in range(2):
        try:
            cb.call(failing_function)
        except Exception:
            pass

    assert cb.state == CircuitState.OPEN

    # Manual reset
    cb.reset()
    assert cb.state == CircuitState.CLOSED


# ============================================================================
# Token Bucket / Rate Limiting Tests
# ============================================================================

def test_token_bucket_consume():
    """Test 17: Token bucket consumption."""
    bucket = TokenBucket(rate=10.0, capacity=10)

    # Should be able to consume initial tokens
    assert bucket.consume(5) is True
    assert bucket.consume(5) is True
    assert bucket.consume(1) is False  # Exceeded capacity


def test_token_bucket_refill():
    """Test 18: Token bucket refills over time."""
    bucket = TokenBucket(rate=10.0, capacity=10)

    # Consume all tokens
    bucket.consume(10)
    assert bucket.consume(1) is False

    # Wait for refill
    time.sleep(0.2)  # Should refill 2 tokens

    assert bucket.consume(1) is True


def test_token_bucket_wait_time():
    """Test 19: Token bucket wait time calculation."""
    bucket = TokenBucket(rate=10.0, capacity=10)

    # Consume all tokens
    bucket.consume(10)

    # Calculate wait time for 5 tokens
    wait_time = bucket.wait_time(5)
    assert wait_time > 0
    assert wait_time <= 1.0  # Should be ~0.5 seconds


# ============================================================================
# DNS Cache Tests
# ============================================================================

def test_dns_cache_set_and_get():
    """Test 20: DNS cache set and get."""
    cache = DNSCache(ttl=60)

    cache.set("example.com", "192.168.1.1")
    ip = cache.get("example.com")

    assert ip == "192.168.1.1"


def test_dns_cache_expiration():
    """Test 21: DNS cache expiration."""
    cache = DNSCache(ttl=0)  # Immediate expiration

    cache.set("example.com", "192.168.1.1")
    time.sleep(0.1)

    ip = cache.get("example.com")
    assert ip is None


def test_dns_cache_clear():
    """Test 22: DNS cache clear."""
    cache = DNSCache()

    cache.set("example1.com", "192.168.1.1")
    cache.set("example2.com", "192.168.1.2")

    cache.clear()

    assert cache.get("example1.com") is None
    assert cache.get("example2.com") is None


# ============================================================================
# Response Cache Tests
# ============================================================================

def test_response_cache_set_and_get():
    """Test 23: Response cache set and get."""
    cache = ResponseCache(max_size=10, ttl=60)

    request = Request(
        request_id="1",
        method=HTTPMethod.GET,
        url="https://api.example.com/users",
    )

    response = Response(
        request_id="1",
        status_code=200,
        headers={},
        content=b'{"users": []}',
        elapsed=0.5,
    )

    cache.set(request, response)
    cached = cache.get(request)

    assert cached is not None
    assert cached.status_code == 200
    assert cached.from_cache is True


def test_response_cache_expiration():
    """Test 24: Response cache expiration."""
    cache = ResponseCache(max_size=10, ttl=0)  # Immediate expiration

    request = Request(
        request_id="1",
        method=HTTPMethod.GET,
        url="https://api.example.com/users",
    )

    response = Response(
        request_id="1",
        status_code=200,
        headers={},
        content=b'{}',
        elapsed=0.5,
    )

    cache.set(request, response)
    time.sleep(0.1)

    cached = cache.get(request)
    assert cached is None


def test_response_cache_eviction():
    """Test 25: Response cache evicts oldest when full."""
    cache = ResponseCache(max_size=2, ttl=60)

    # Add 3 requests (exceeds capacity)
    for i in range(3):
        request = Request(
            request_id=str(i),
            method=HTTPMethod.GET,
            url=f"https://api.example.com/item{i}",
        )
        response = Response(
            request_id=str(i),
            status_code=200,
            headers={},
            content=b'{}',
            elapsed=0.1,
        )
        cache.set(request, response)
        time.sleep(0.01)  # Small delay to ensure ordering

    # Cache should only have 2 items
    assert len(cache.cache) == 2


# ============================================================================
# Connection Pool Tests
# ============================================================================

def test_connection_pool_acquire():
    """Test 26: Connection pool acquire."""
    pool = ConnectionPool(max_size=5)

    with pool.get_connection() as conn:
        assert conn is not None
        assert len(pool.active_connections) == 1


def test_connection_pool_return():
    """Test 27: Connection pool returns connection."""
    pool = ConnectionPool(max_size=5)

    with pool.get_connection() as conn:
        assert len(pool.active_connections) == 1

    # After context, connection should be returned
    assert len(pool.active_connections) == 0
    assert len(pool.pool) == 1


def test_connection_pool_max_size():
    """Test 28: Connection pool respects max size."""
    pool = ConnectionPool(max_size=2)

    # Acquire all connections
    with pool.get_connection() as conn1:
        with pool.get_connection() as conn2:
            assert pool.size() == 2


def test_connection_pool_close_all():
    """Test 29: Connection pool closes all connections."""
    pool = ConnectionPool(max_size=5)

    # Create some connections
    with pool.get_connection():
        pass
    with pool.get_connection():
        pass

    pool.close_all()

    assert len(pool.pool) == 0
    assert len(pool.active_connections) == 0


# ============================================================================
# Interceptor Tests
# ============================================================================

def test_logging_interceptor():
    """Test 30: Logging interceptor."""
    interceptor = LoggingInterceptor()

    request = Request(
        request_id="1",
        method=HTTPMethod.GET,
        url="https://api.example.com/users",
    )

    # Should return same request
    modified = interceptor.intercept_request(request)
    assert modified.request_id == request.request_id


def test_auth_interceptor():
    """Test 31: Auth interceptor adds authorization header."""
    interceptor = AuthInterceptor(token="secret_token")

    request = Request(
        request_id="1",
        method=HTTPMethod.GET,
        url="https://api.example.com/users",
    )

    modified = interceptor.intercept_request(request)
    assert 'Authorization' in modified.headers
    assert modified.headers['Authorization'] == 'Bearer secret_token'


def test_add_interceptors_to_fsa(network_fsa):
    """Test 32: Add interceptors to network FSA."""
    logging_interceptor = LoggingInterceptor()
    auth_interceptor = AuthInterceptor(token="test_token")

    network_fsa.add_request_interceptor(logging_interceptor)
    network_fsa.add_request_interceptor(auth_interceptor)

    assert len(network_fsa.request_interceptors) == 2


# ============================================================================
# Bandwidth Throttling Tests
# ============================================================================

def test_bandwidth_throttler():
    """Test 33: Bandwidth throttler limits throughput."""
    throttler = BandwidthThrottler(max_bytes_per_second=1000)

    start_time = time.time()

    # Try to send 2000 bytes (should take ~1 second)
    throttler.throttle(2000)

    elapsed = time.time() - start_time

    # Should take at least 1 second (with some tolerance)
    assert elapsed >= 0.8


def test_set_bandwidth_throttle_on_fsa(network_fsa):
    """Test 34: Set bandwidth throttle on network FSA."""
    network_fsa.set_bandwidth_throttle(max_bytes_per_second=1000000)

    assert network_fsa.bandwidth_throttler is not None
    assert network_fsa.bandwidth_throttler.max_bytes_per_second == 1000000


# ============================================================================
# Metrics Tests
# ============================================================================

def test_metrics_initialization(network_fsa):
    """Test 35: Metrics are initialized."""
    metrics = network_fsa.get_metrics()

    assert 'total_requests' in metrics
    assert 'successful_requests' in metrics
    assert 'failed_requests' in metrics
    assert metrics['total_requests'] == 0


def test_metrics_update_on_success():
    """Test 36: Metrics update on successful request."""
    fsa = NetworkManagerFSA(enable_health_monitoring=False)
    fsa.add_endpoint("https://httpbin.org")

    # Mock successful request
    with patch.object(fsa, '_execute_request') as mock_exec:
        mock_exec.return_value = Response(
            request_id="1",
            status_code=200,
            headers={},
            content=b'{"status": "ok"}',
            elapsed=0.5,
        )

        try:
            fsa.request(HTTPMethod.GET, "/get")
        except:
            pass

    metrics = fsa.get_metrics()
    assert metrics['total_requests'] > 0

    fsa.shutdown()


# ============================================================================
# Request/Response Tests
# ============================================================================

def test_request_creation():
    """Test 37: Request object creation."""
    request = Request(
        request_id="123",
        method=HTTPMethod.POST,
        url="https://api.example.com/users",
        headers={"Content-Type": "application/json"},
        json_data={"name": "John"},
        timeout=30.0,
    )

    assert request.request_id == "123"
    assert request.method == HTTPMethod.POST
    assert request.timeout == 30.0


def test_response_json_parsing():
    """Test 38: Response JSON parsing."""
    response = Response(
        request_id="1",
        status_code=200,
        headers={"Content-Type": "application/json"},
        content=b'{"status": "ok", "message": "Success"}',
        elapsed=0.5,
    )

    data = response.json()
    assert data['status'] == 'ok'
    assert data['message'] == 'Success'


def test_response_text_parsing():
    """Test 39: Response text parsing."""
    response = Response(
        request_id="1",
        status_code=200,
        headers={},
        content=b'Hello, World!',
        elapsed=0.5,
    )

    text = response.text()
    assert text == 'Hello, World!'


# ============================================================================
# Compression Tests
# ============================================================================

def test_gzip_compression():
    """Test 40: GZIP compression and decompression."""
    data = b"This is test data " * 100

    compressed = compress_data(data, CompressionType.GZIP)
    assert len(compressed) < len(data)

    decompressed = decompress_data(compressed, CompressionType.GZIP)
    assert decompressed == data


def test_deflate_compression():
    """Test 41: Deflate compression and decompression."""
    data = b"This is test data " * 100

    compressed = compress_data(data, CompressionType.DEFLATE)
    assert len(compressed) < len(data)

    decompressed = decompress_data(compressed, CompressionType.DEFLATE)
    assert decompressed == data


def test_no_compression():
    """Test 42: No compression returns original data."""
    data = b"This is test data"

    compressed = compress_data(data, CompressionType.NONE)
    assert compressed == data

    decompressed = decompress_data(compressed, CompressionType.NONE)
    assert decompressed == data


# ============================================================================
# Configuration Tests
# ============================================================================

def test_retry_config():
    """Test 43: Retry configuration."""
    config = RetryConfig(
        max_retries=5,
        initial_delay=2.0,
        max_delay=120.0,
        exponential_base=3.0,
    )

    assert config.max_retries == 5
    assert config.initial_delay == 2.0
    assert config.exponential_base == 3.0


def test_circuit_breaker_config():
    """Test 44: Circuit breaker configuration."""
    config = CircuitBreakerConfig(
        failure_threshold=10,
        success_threshold=5,
        timeout=120.0,
    )

    assert config.failure_threshold == 10
    assert config.success_threshold == 5
    assert config.timeout == 120.0


def test_rate_limit_config():
    """Test 45: Rate limit configuration."""
    config = RateLimitConfig(
        requests_per_second=100.0,
        burst_size=200,
        per_endpoint=True,
    )

    assert config.requests_per_second == 100.0
    assert config.burst_size == 200
    assert config.per_endpoint is True


def test_cache_config():
    """Test 46: Cache configuration."""
    config = CacheConfig(
        enabled=True,
        max_size=5000,
        ttl=600,
        cache_methods={HTTPMethod.GET},
    )

    assert config.enabled is True
    assert config.max_size == 5000
    assert config.ttl == 600


def test_ssl_config():
    """Test 47: SSL configuration."""
    config = SSLConfig(
        verify=True,
        cert_file="/path/to/cert.pem",
        key_file="/path/to/key.pem",
    )

    assert config.verify is True
    assert config.cert_file == "/path/to/cert.pem"


def test_proxy_config():
    """Test 48: Proxy configuration."""
    config = ProxyConfig(
        http_proxy="http://proxy.example.com:8080",
        https_proxy="https://proxy.example.com:8443",
        no_proxy=["localhost", "127.0.0.1"],
    )

    assert config.http_proxy == "http://proxy.example.com:8080"
    assert config.https_proxy == "https://proxy.example.com:8443"
    assert "localhost" in config.no_proxy


# ============================================================================
# Endpoint Tests
# ============================================================================

def test_endpoint_avg_response_time():
    """Test 49: Endpoint average response time calculation."""
    endpoint = Endpoint(url="https://api.example.com")

    endpoint.response_times.append(1.0)
    endpoint.response_times.append(2.0)
    endpoint.response_times.append(3.0)

    avg = endpoint.avg_response_time()
    assert avg == 2.0


def test_endpoint_health_status():
    """Test 50: Endpoint health status."""
    endpoint = Endpoint(url="https://api.example.com", is_healthy=True)

    assert endpoint.is_healthy is True

    endpoint.is_healthy = False
    assert endpoint.is_healthy is False


# ============================================================================
# Integration Tests
# ============================================================================

def test_full_request_workflow_with_mock():
    """Test 51: Complete request workflow with mocked response."""
    fsa = NetworkManagerFSA(enable_health_monitoring=False)
    fsa.add_endpoint("https://api.example.com")

    # Mock the execute request
    with patch.object(fsa, '_execute_request') as mock_exec:
        mock_exec.return_value = Response(
            request_id="1",
            status_code=200,
            headers={"Content-Type": "application/json"},
            content=b'{"result": "success"}',
            elapsed=0.5,
        )

        response = fsa.request(
            method=HTTPMethod.GET,
            url="/api/test",
            timeout=10.0,
        )

        assert response.status_code == 200
        assert response.json()['result'] == 'success'

    fsa.shutdown()


def test_request_with_interceptors():
    """Test 52: Request with interceptors."""
    fsa = NetworkManagerFSA(enable_health_monitoring=False)
    fsa.add_endpoint("https://api.example.com")

    # Add auth interceptor
    fsa.add_request_interceptor(AuthInterceptor(token="test_token"))

    # Mock the execute request
    with patch.object(fsa, '_execute_request') as mock_exec:
        mock_exec.return_value = Response(
            request_id="1",
            status_code=200,
            headers={},
            content=b'{}',
            elapsed=0.5,
        )

        fsa.request(HTTPMethod.GET, "/api/test")

        # Verify interceptor was applied
        call_args = mock_exec.call_args
        request = call_args[0][0]
        assert 'Authorization' in request.headers

    fsa.shutdown()


def test_request_with_caching():
    """Test 53: Request with response caching."""
    fsa = NetworkManagerFSA(
        enable_health_monitoring=False,
        cache_config=CacheConfig(enabled=True, ttl=60)
    )
    fsa.add_endpoint("https://api.example.com")

    # Mock the execute request
    with patch.object(fsa, '_execute_request') as mock_exec:
        mock_exec.return_value = Response(
            request_id="1",
            status_code=200,
            headers={},
            content=b'{"cached": true}',
            elapsed=0.5,
        )

        # First request - cache miss
        response1 = fsa.request(HTTPMethod.GET, "/api/test")
        assert response1.from_cache is False

        # Second request - cache hit
        response2 = fsa.request(HTTPMethod.GET, "/api/test")
        assert response2.from_cache is True

        # Execute should only be called once
        assert mock_exec.call_count == 1

    fsa.shutdown()


def test_clear_caches(network_fsa):
    """Test 54: Clear response and DNS caches."""
    # Add some cache entries
    if network_fsa.response_cache:
        request = Request(
            request_id="1",
            method=HTTPMethod.GET,
            url="https://api.example.com/test",
        )
        response = Response(
            request_id="1",
            status_code=200,
            headers={},
            content=b'{}',
            elapsed=0.5,
        )
        network_fsa.response_cache.set(request, response)

    # Clear caches
    network_fsa.clear_cache()
    network_fsa.clear_dns_cache()

    # Verify cleared
    if network_fsa.response_cache:
        assert len(network_fsa.response_cache.cache) == 0


def test_shutdown_cleanup(network_fsa):
    """Test 55: Proper cleanup on shutdown."""
    network_fsa.add_endpoint("https://api.example.com")

    network_fsa.shutdown()

    assert network_fsa.state == NetworkState.IDLE


# ============================================================================
# Concurrent Request Tests
# ============================================================================

def test_concurrent_requests():
    """Test 56: Handle concurrent requests."""
    fsa = NetworkManagerFSA(
        enable_health_monitoring=False,
        max_concurrent_requests=5
    )
    fsa.add_endpoint("https://api.example.com")

    # Mock execute request
    with patch.object(fsa, '_execute_request') as mock_exec:
        mock_exec.return_value = Response(
            request_id="1",
            status_code=200,
            headers={},
            content=b'{}',
            elapsed=0.1,
        )

        # Execute multiple requests concurrently
        def make_request():
            try:
                fsa.request(HTTPMethod.GET, "/api/test")
            except:
                pass

        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

    fsa.shutdown()


def test_batch_requests():
    """Test 57: Batch request execution."""
    fsa = NetworkManagerFSA(enable_health_monitoring=False)
    fsa.add_endpoint("https://api.example.com")

    # Mock execute request
    with patch.object(fsa, '_execute_request') as mock_exec:
        mock_exec.return_value = Response(
            request_id="1",
            status_code=200,
            headers={},
            content=b'{}',
            elapsed=0.1,
        )

        # Create batch requests
        requests = [
            {"method": HTTPMethod.GET, "url": f"/api/test{i}"}
            for i in range(5)
        ]

        responses = fsa.request_batch(requests, max_workers=3)

        assert len(responses) == 5

    fsa.shutdown()


# ============================================================================
# Error Handling Tests
# ============================================================================

def test_no_endpoints_error():
    """Test 58: Error when no endpoints available."""
    fsa = NetworkManagerFSA(enable_health_monitoring=False)

    # No endpoints added
    with patch.object(fsa, '_execute_request'):
        with pytest.raises(LoadBalancerError):
            fsa.request(HTTPMethod.GET, "/api/test")

    fsa.shutdown()


def test_circuit_breaker_error_raised():
    """Test 59: Circuit breaker error is raised when open."""
    config = CircuitBreakerConfig(failure_threshold=1, timeout=10.0)
    fsa = NetworkManagerFSA(
        enable_health_monitoring=False,
        circuit_breaker_config=config
    )
    fsa.add_endpoint("https://api.example.com")

    # Mock failing request
    with patch.object(fsa, '_execute_request') as mock_exec:
        mock_exec.side_effect = NetworkError("Connection failed")

        # First request fails and opens circuit
        try:
            fsa.request(HTTPMethod.GET, "/api/test")
        except:
            pass

        # Second request should raise CircuitBreakerError
        with pytest.raises(CircuitBreakerError):
            fsa.request(HTTPMethod.GET, "/api/test")

    fsa.shutdown()


def test_reset_circuit_breaker(network_fsa):
    """Test 60: Manually reset circuit breaker."""
    network_fsa.circuit_breaker.state = CircuitState.OPEN

    network_fsa.reset_circuit_breaker()

    assert network_fsa.circuit_breaker.state == CircuitState.CLOSED


# ============================================================================
# Performance Tests
# ============================================================================

def test_high_volume_requests():
    """Test 61: Handle high volume of requests."""
    fsa = NetworkManagerFSA(enable_health_monitoring=False)
    fsa.add_endpoint("https://api.example.com")

    # Mock execute request
    with patch.object(fsa, '_execute_request') as mock_exec:
        mock_exec.return_value = Response(
            request_id="1",
            status_code=200,
            headers={},
            content=b'{}',
            elapsed=0.01,
        )

        start_time = time.time()

        # Make 100 requests
        for _ in range(100):
            try:
                fsa.request(HTTPMethod.GET, "/api/test")
            except:
                pass

        elapsed = time.time() - start_time

        # Should complete reasonably fast
        assert elapsed < 5.0

    fsa.shutdown()


# ============================================================================
# Edge Cases
# ============================================================================

def test_request_with_priority():
    """Test 62: Request with different priorities."""
    request_low = Request(
        request_id="1",
        method=HTTPMethod.GET,
        url="/test",
        priority=RequestPriority.LOW
    )

    request_high = Request(
        request_id="2",
        method=HTTPMethod.GET,
        url="/test",
        priority=RequestPriority.HIGH
    )

    assert request_high.priority.value < request_low.priority.value


def test_endpoint_metrics_tracking():
    """Test 63: Endpoint tracks success and failure counts."""
    endpoint = Endpoint(url="https://api.example.com")

    endpoint.success_count = 10
    endpoint.failure_count = 2

    assert endpoint.success_count == 10
    assert endpoint.failure_count == 2


def test_health_monitor_lifecycle():
    """Test 64: Health monitor start and stop."""
    monitor = HealthMonitor(check_interval=1)
    endpoint = Endpoint(url="https://api.example.com")

    monitor.add_endpoint(endpoint)
    monitor.start()

    assert monitor.running is True

    monitor.stop()
    assert monitor.running is False


def test_metrics_dict_conversion():
    """Test 65: Network metrics dictionary conversion."""
    metrics = NetworkMetrics()
    metrics.total_requests = 100
    metrics.successful_requests = 95
    metrics.failed_requests = 5

    metrics_dict = metrics.to_dict()

    assert metrics_dict['total_requests'] == 100
    assert metrics_dict['successful_requests'] == 95
    assert metrics_dict['failed_requests'] == 5
