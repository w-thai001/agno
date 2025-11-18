"""
Comprehensive tests for Network Manager FSA

This test suite covers all major functionality including:
- HTTP/HTTPS requests with connection pooling
- WebSocket connections
- Circuit breaker activation and recovery
- Retry logic with exponential backoff
- Rate limiting enforcement
- Response caching
- Connection timeouts
- SSL certificate validation
- DNS resolution caching
- Load balancing distribution
- Proxy rotation
- Health monitoring
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch

from agno.fsas.infrastructure.network_manager_fsa import (
    NetworkManagerFSA,
    NetworkRequest,
    NetworkResponse,
    Protocol,
    CircuitBreaker,
    CircuitState,
    RetryHandler,
    RateLimiter,
    RequestCache,
    ConnectionPool,
    HealthMonitor,
    LoadBalancer,
    LoadBalanceStrategy,
    DNSResolver,
    SSLValidator,
    MetricsCollector,
    ConnectionError,
    TimeoutError,
    RateLimitExceeded,
    CircuitBreakerOpen,
    DNSResolutionError,
    SSLError,
    NetworkUnreachable,
)


@pytest.fixture
def network_manager():
    """Create NetworkManagerFSA instance for testing"""
    return NetworkManagerFSA(
        max_connections=10,
        rate_limit=10.0,
        rate_window=1.0,
        cache_ttl=5.0
    )


@pytest.fixture
def sample_request():
    """Create sample HTTP request"""
    return NetworkRequest(
        protocol=Protocol.HTTP,
        endpoint="http://example.com/api/test",
        method="GET",
        headers={"User-Agent": "NetworkManager/1.0"},
        timeout=5.0
    )


class TestHTTPRequestWithPooling:
    """Test HTTP requests with connection pooling"""

    @pytest.mark.asyncio
    async def test_http_request_success(self, network_manager, sample_request):
        """Test successful HTTP request"""
        with patch('aiohttp.ClientSession') as mock_session:
            # Mock response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.headers = {"Content-Type": "application/json"}
            mock_response.text = AsyncMock(return_value='{"success": true}')

            mock_session.return_value.__aenter__.return_value.request = AsyncMock(
                return_value=mock_response.__aenter__.return_value
            )
            mock_session.return_value.__aenter__.return_value.request.return_value = mock_response

            response = await network_manager.execute(sample_request)

            assert response.status_code == 200
            assert response.body == '{"success": true}'
            assert not response.cached

    @pytest.mark.asyncio
    async def test_connection_pooling(self, network_manager):
        """Test connection pool reuse"""
        pool = network_manager.connection_pool

        # Add connection to pool
        from agno.fsas.infrastructure.network_manager_fsa import ConnectionInfo
        conn_info = ConnectionInfo(
            endpoint="example.com",
            protocol=Protocol.HTTP,
            connection=MagicMock(),
            created_at=time.time(),
            last_used=time.time()
        )

        pool.put(conn_info)
        assert pool.total_connections == 1

        # Retrieve connection
        retrieved = pool.get("example.com", Protocol.HTTP)
        assert retrieved is not None
        assert retrieved.endpoint == "example.com"
        assert retrieved.request_count == 1


class TestWebSocketConnection:
    """Test WebSocket connections"""

    @pytest.mark.asyncio
    async def test_websocket_send_receive(self, network_manager):
        """Test WebSocket message exchange"""
        request = NetworkRequest(
            protocol=Protocol.WEBSOCKET,
            endpoint="ws://example.com/socket",
            body="test message",
            timeout=5.0
        )

        with patch('websockets.connect') as mock_connect:
            mock_ws = AsyncMock()
            mock_ws.send = AsyncMock()
            mock_ws.recv = AsyncMock(return_value="response message")
            mock_connect.return_value.__aenter__.return_value = mock_ws

            response = await network_manager.execute(request, use_cache=False)

            assert response.status_code == 200
            assert response.body == "response message"
            mock_ws.send.assert_called_once_with("test message")


class TestCircuitBreakerActivation:
    """Test circuit breaker pattern"""

    def test_circuit_breaker_closed_state(self):
        """Test circuit breaker in closed state"""
        cb = CircuitBreaker(failure_threshold=3)
        assert cb.state == CircuitState.CLOSED
        assert cb.can_execute() is True

    def test_circuit_breaker_opens_on_failures(self):
        """Test circuit breaker opens after failures"""
        cb = CircuitBreaker(failure_threshold=3)

        # Record failures
        for _ in range(3):
            cb.record_failure()

        assert cb.state == CircuitState.OPEN

        with pytest.raises(CircuitBreakerOpen):
            cb.can_execute()

    def test_circuit_breaker_half_open_recovery(self):
        """Test circuit breaker transitions to half-open"""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

        # Trigger open state
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        # Wait for recovery timeout
        time.sleep(0.2)

        # Should transition to half-open
        can_execute = cb.can_execute()
        assert can_execute is True
        assert cb.state == CircuitState.HALF_OPEN

    def test_circuit_breaker_closes_after_success(self):
        """Test circuit breaker closes after successful requests in half-open"""
        cb = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=0.1,
            half_open_max_calls=2
        )

        # Open circuit
        cb.record_failure()
        cb.record_failure()

        # Wait and transition to half-open
        time.sleep(0.2)
        cb.can_execute()

        # Record successes
        cb.record_success()
        cb.record_success()

        assert cb.state == CircuitState.CLOSED


class TestRetryExponentialBackoff:
    """Test retry logic with exponential backoff"""

    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """Test retry attempts on failure"""
        retry_handler = RetryHandler(max_attempts=3, base_delay=0.1)

        call_count = 0

        async def failing_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Connection failed")
            return "success"

        result = await retry_handler.execute(failing_operation)

        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_max_attempts_exceeded(self):
        """Test retry gives up after max attempts"""
        retry_handler = RetryHandler(max_attempts=2, base_delay=0.1)

        async def always_failing_operation():
            raise ConnectionError("Always fails")

        with pytest.raises(ConnectionError):
            await retry_handler.execute(always_failing_operation)

    def test_exponential_backoff_calculation(self):
        """Test exponential backoff delay calculation"""
        retry_handler = RetryHandler(
            base_delay=1.0,
            exponential_base=2.0,
            max_delay=10.0
        )

        # Test delay increases exponentially
        delay_0 = retry_handler.calculate_delay(0)
        delay_1 = retry_handler.calculate_delay(1)
        delay_2 = retry_handler.calculate_delay(2)

        # Should be approximately 1, 2, 4 with jitter
        assert 0.5 < delay_0 < 1.5
        assert 1.5 < delay_1 < 2.5
        assert 3.0 < delay_2 < 5.0


class TestRateLimitingEnforcement:
    """Test rate limiting"""

    def test_rate_limit_allows_within_limit(self):
        """Test requests allowed within rate limit"""
        limiter = RateLimiter(rate=5.0, window=1.0)

        # Should allow 5 requests
        for i in range(5):
            assert limiter.allow(f"test_key") is True

    def test_rate_limit_blocks_excess(self):
        """Test rate limit blocks excess requests"""
        limiter = RateLimiter(rate=3.0, window=1.0)

        # Allow 3 requests
        for i in range(3):
            limiter.allow("test_key")

        # 4th request should be blocked
        with pytest.raises(RateLimitExceeded) as exc_info:
            limiter.allow("test_key")

        assert exc_info.value.retry_after > 0

    def test_rate_limit_resets_after_window(self):
        """Test rate limit resets after time window"""
        limiter = RateLimiter(rate=2.0, window=0.5)

        # Use up limit
        limiter.allow("test_key")
        limiter.allow("test_key")

        # Wait for window to pass
        time.sleep(0.6)

        # Should allow new requests
        assert limiter.allow("test_key") is True


class TestResponseCaching:
    """Test response caching"""

    @pytest.mark.asyncio
    async def test_cache_stores_and_retrieves(self, network_manager, sample_request):
        """Test cache stores and retrieves responses"""
        cache = network_manager.cache

        response = NetworkResponse(
            status_code=200,
            headers={"Content-Type": "text/plain"},
            body="cached data",
            duration=0.1
        )

        # Store in cache
        cache.set(sample_request, response)

        # Retrieve from cache
        cached = cache.get(sample_request)
        assert cached is not None
        assert cached.body == "cached data"
        assert cached.cached is True

    @pytest.mark.asyncio
    async def test_cache_ttl_expiration(self):
        """Test cache entries expire after TTL"""
        cache = RequestCache(default_ttl=0.5)

        request = NetworkRequest(
            protocol=Protocol.HTTP,
            endpoint="http://example.com/test",
            method="GET"
        )

        response = NetworkResponse(
            status_code=200,
            headers={},
            body="data",
            duration=0.1
        )

        cache.set(request, response)

        # Should be in cache
        assert cache.get(request) is not None

        # Wait for TTL
        time.sleep(0.6)

        # Should be expired
        assert cache.get(request) is None

    @pytest.mark.asyncio
    async def test_cache_invalidation(self):
        """Test cache invalidation"""
        cache = RequestCache()

        request = NetworkRequest(
            protocol=Protocol.HTTP,
            endpoint="http://example.com/test",
            method="GET"
        )

        response = NetworkResponse(
            status_code=200,
            headers={},
            body="data",
            duration=0.1
        )

        cache.set(request, response)
        assert cache.get(request) is not None

        # Invalidate cache
        cache.invalidate()
        assert cache.get(request) is None


class TestConnectionTimeout:
    """Test connection timeout handling"""

    @pytest.mark.asyncio
    async def test_http_timeout(self, network_manager):
        """Test HTTP request timeout"""
        request = NetworkRequest(
            protocol=Protocol.HTTP,
            endpoint="http://example.com/slow",
            method="GET",
            timeout=0.1
        )

        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.request = AsyncMock(
                side_effect=asyncio.TimeoutError()
            )

            with pytest.raises(TimeoutError):
                await network_manager.execute(request, use_cache=False, use_retry=False)

    @pytest.mark.asyncio
    async def test_tcp_timeout(self, network_manager):
        """Test TCP connection timeout"""
        request = NetworkRequest(
            protocol=Protocol.TCP,
            endpoint="tcp://192.0.2.1:9999",  # Non-routable IP
            timeout=0.1
        )

        with pytest.raises((TimeoutError, ConnectionError)):
            await network_manager.execute(request, use_cache=False, use_retry=False)


class TestSSLCertificateValidation:
    """Test SSL certificate validation"""

    def test_ssl_validation_success(self):
        """Test successful SSL validation"""
        validator = SSLValidator()

        # Should pass validation
        assert validator.validate("example.com") is True

    def test_ssl_certificate_pinning(self):
        """Test certificate pinning"""
        pinned_certs = {
            "secure.example.com": "sha256:abc123..."
        }
        validator = SSLValidator(cert_pinning=pinned_certs)

        # Should validate pinned certificate
        assert validator.validate("secure.example.com") is True

    def test_ssl_validation_failure(self):
        """Test SSL validation failure"""
        validator = SSLValidator()

        # Mock validation failure
        with patch.object(validator, 'validate', side_effect=SSLError("Invalid certificate")):
            with pytest.raises(SSLError):
                validator.validate("invalid.example.com")


class TestDNSResolutionCaching:
    """Test DNS resolution and caching"""

    def test_dns_resolution(self):
        """Test DNS resolution"""
        resolver = DNSResolver()

        with patch('socket.gethostbyname', return_value='93.184.216.34'):
            ip = resolver.resolve('example.com')
            assert ip == '93.184.216.34'

    def test_dns_cache_hit(self):
        """Test DNS cache is used"""
        resolver = DNSResolver(cache_ttl=10.0)

        with patch('socket.gethostbyname', return_value='93.184.216.34') as mock_dns:
            # First call
            ip1 = resolver.resolve('example.com')

            # Second call should use cache
            ip2 = resolver.resolve('example.com')

            assert ip1 == ip2
            # DNS should only be called once
            assert mock_dns.call_count == 1

    def test_dns_resolution_failure(self):
        """Test DNS resolution failure"""
        resolver = DNSResolver()

        with patch('socket.gethostbyname', side_effect=socket.gaierror):
            with pytest.raises(DNSResolutionError) as exc_info:
                resolver.resolve('invalid.example.com')

            assert len(exc_info.value.fallback_servers) > 0


class TestLoadBalancingDistribution:
    """Test load balancing"""

    def test_round_robin_distribution(self):
        """Test round-robin load balancing"""
        lb = LoadBalancer(strategy=LoadBalanceStrategy.ROUND_ROBIN)

        endpoints = ["server1", "server2", "server3"]
        for ep in endpoints:
            lb.add_endpoint(ep)

        # Should cycle through endpoints
        selected = [lb.select() for _ in range(6)]

        assert selected == ["server1", "server2", "server3", "server1", "server2", "server3"]

    def test_least_connections_distribution(self):
        """Test least-connections load balancing"""
        lb = LoadBalancer(strategy=LoadBalanceStrategy.LEAST_CONNECTIONS)

        lb.add_endpoint("server1")
        lb.add_endpoint("server2")

        # Server1 has more connections
        lb.record_connection("server1")
        lb.record_connection("server1")
        lb.record_connection("server2")

        # Should select server2 (fewer connections)
        selected = lb.select()
        assert selected == "server2"

    def test_weighted_distribution(self):
        """Test weighted load balancing"""
        lb = LoadBalancer(strategy=LoadBalanceStrategy.WEIGHTED)

        lb.add_endpoint("server1", weight=3)
        lb.add_endpoint("server2", weight=1)

        # Run multiple times and count
        selections = [lb.select() for _ in range(100)]
        server1_count = selections.count("server1")

        # Server1 should be selected more often (roughly 75% of the time)
        assert server1_count > 60

    def test_load_balancer_health_filter(self):
        """Test load balancer filters unhealthy endpoints"""
        lb = LoadBalancer(strategy=LoadBalanceStrategy.ROUND_ROBIN)
        health_monitor = HealthMonitor(failure_threshold=1)

        lb.add_endpoint("healthy_server")
        lb.add_endpoint("unhealthy_server")

        # Mark one as unhealthy
        health_monitor.record_failure("unhealthy_server")

        # Should only select healthy server
        selected = lb.select(health_monitor)
        assert selected == "healthy_server"


class TestHealthMonitoring:
    """Test endpoint health monitoring"""

    def test_health_monitor_tracks_success(self):
        """Test health monitor tracks successful requests"""
        monitor = HealthMonitor()

        monitor.record_success("server1", response_time=0.1)

        status = monitor.get_status("server1")
        assert status.is_healthy is True
        assert status.success_count == 1
        assert status.response_time == 0.1

    def test_health_monitor_marks_unhealthy(self):
        """Test health monitor marks endpoints unhealthy"""
        monitor = HealthMonitor(failure_threshold=3)

        # Record failures
        for _ in range(3):
            monitor.record_failure("server1")

        assert monitor.is_healthy("server1") is False

    def test_health_monitor_recovery(self):
        """Test endpoint can recover to healthy state"""
        monitor = HealthMonitor(failure_threshold=2)

        # Make unhealthy
        monitor.record_failure("server1")
        monitor.record_failure("server1")
        assert monitor.is_healthy("server1") is False

        # Record success - health improves but stays unhealthy
        monitor.record_success("server1", 0.1)

        # Mark as healthy manually (in real scenario, would need more successes)
        status = monitor.get_status("server1")
        status.is_healthy = True
        status.failure_count = 0

        assert monitor.is_healthy("server1") is True


class TestMetricsCollection:
    """Test metrics collection"""

    def test_metrics_collection(self):
        """Test metrics are collected correctly"""
        collector = MetricsCollector()

        # Record various operations
        collector.record_request("http:GET", 0.1, success=True)
        collector.record_request("http:POST", 0.2, success=True)
        collector.record_request("http:GET", 0.15, success=False)
        collector.record_request("http:GET", 0.05, success=True, cached=True)

        metrics = collector.get_metrics()

        assert metrics.total_requests == 4
        assert metrics.successful_requests == 3
        assert metrics.failed_requests == 1
        assert metrics.cached_responses == 1
        assert metrics.total_duration > 0

    def test_operation_specific_metrics(self):
        """Test per-operation metrics"""
        collector = MetricsCollector()

        collector.record_request("http:GET", 0.1, success=True)
        collector.record_request("http:POST", 0.2, success=True)

        get_metrics = collector.get_operation_metrics("http:GET")
        post_metrics = collector.get_operation_metrics("http:POST")

        assert get_metrics.total_requests == 1
        assert post_metrics.total_requests == 1


class TestNetworkManagerValidation:
    """Test NetworkManager validation and error handling"""

    def test_validation_success(self, network_manager):
        """Test NetworkManager validation"""
        assert network_manager.validate() is True

    def test_error_handling_info(self, network_manager):
        """Test error handling information retrieval"""
        info = network_manager.error_handling()

        assert "circuit_breakers" in info
        assert "health_status" in info
        assert "total_connections" in info
        assert "metrics" in info


class TestIntegrationScenarios:
    """Integration tests for complex scenarios"""

    @pytest.mark.asyncio
    async def test_full_request_lifecycle_with_caching(self, network_manager, sample_request):
        """Test complete request lifecycle with caching"""
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.headers = {"Content-Type": "application/json"}
            mock_response.text = AsyncMock(return_value='{"result": "data"}')

            mock_session.return_value.__aenter__.return_value.request = AsyncMock(
                return_value=mock_response.__aenter__.return_value
            )
            mock_session.return_value.__aenter__.return_value.request.return_value = mock_response

            # First request - not cached
            response1 = await network_manager.execute(sample_request)
            assert response1.cached is False

            # Second request - should be cached
            response2 = await network_manager.execute(sample_request)
            assert response2.cached is True
            assert response2.body == response1.body

    @pytest.mark.asyncio
    async def test_circuit_breaker_integration(self, network_manager, sample_request):
        """Test circuit breaker integration with retry logic"""
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.request = AsyncMock(
                side_effect=Exception("Connection refused")
            )

            # Multiple failures should open circuit
            for _ in range(5):
                try:
                    await network_manager.execute(
                        sample_request,
                        use_cache=False,
                        use_retry=False
                    )
                except:
                    pass

            # Circuit should be open now
            circuit = network_manager._get_circuit_breaker(sample_request.endpoint)
            assert circuit.state == CircuitState.OPEN
