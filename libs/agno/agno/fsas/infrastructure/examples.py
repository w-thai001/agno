"""
Example usage of Network Manager FSA

This module demonstrates various use cases for the NetworkManagerFSA
including HTTP requests, WebSocket connections, circuit breaker patterns,
caching, rate limiting, and more.
"""

import asyncio
from agno.fsas.infrastructure.network_manager_fsa import (
    NetworkManagerFSA,
    NetworkRequest,
    Protocol,
    LoadBalanceStrategy,
)


async def example_http_request():
    """Example: Basic HTTP request with caching"""
    print("\n=== Example 1: HTTP Request with Caching ===")

    # Initialize Network Manager
    nm = NetworkManagerFSA(
        max_connections=100,
        rate_limit=100.0,
        rate_window=60.0,
        cache_ttl=300.0
    )

    # Create HTTP request
    request = NetworkRequest(
        protocol=Protocol.HTTP,
        endpoint="https://api.example.com/data",
        method="GET",
        headers={"Authorization": "Bearer token123"},
        timeout=10.0
    )

    try:
        # First request - will fetch from server
        response = await nm.execute(request)
        print(f"Status: {response.status_code}")
        print(f"Cached: {response.cached}")
        print(f"Duration: {response.duration:.3f}s")

        # Second request - will use cache
        response2 = await nm.execute(request)
        print(f"Second request cached: {response2.cached}")

    except Exception as e:
        print(f"Error: {e}")


async def example_websocket():
    """Example: WebSocket connection"""
    print("\n=== Example 2: WebSocket Connection ===")

    nm = NetworkManagerFSA()

    request = NetworkRequest(
        protocol=Protocol.WEBSOCKET,
        endpoint="wss://echo.websocket.org",
        body="Hello WebSocket!",
        timeout=5.0
    )

    try:
        response = await nm.execute(request, use_cache=False)
        print(f"WebSocket response: {response.body}")
    except Exception as e:
        print(f"WebSocket error: {e}")


async def example_circuit_breaker():
    """Example: Circuit breaker pattern"""
    print("\n=== Example 3: Circuit Breaker Pattern ===")

    nm = NetworkManagerFSA()

    # Simulate multiple failures to trigger circuit breaker
    request = NetworkRequest(
        protocol=Protocol.HTTP,
        endpoint="https://unreliable-api.example.com/data",
        method="GET",
        timeout=1.0
    )

    for i in range(7):
        try:
            response = await nm.execute(request, use_retry=False)
            print(f"Request {i+1}: Success")
        except Exception as e:
            print(f"Request {i+1}: {type(e).__name__}")

    # Check circuit breaker status
    cb = nm._get_circuit_breaker(request.endpoint)
    print(f"Circuit breaker state: {cb.state.value}")


async def example_load_balancing():
    """Example: Load balancing across multiple endpoints"""
    print("\n=== Example 4: Load Balancing ===")

    nm = NetworkManagerFSA()

    # Configure load balancer
    lb = nm.load_balancer
    lb.add_endpoint("server1.example.com", weight=3)
    lb.add_endpoint("server2.example.com", weight=1)
    lb.add_endpoint("server3.example.com", weight=1)

    # Select endpoints
    print("Round-robin selection:")
    for i in range(5):
        selected = lb.select()
        print(f"  Request {i+1} -> {selected}")


async def example_rate_limiting():
    """Example: Rate limiting"""
    print("\n=== Example 5: Rate Limiting ===")

    # Create manager with strict rate limit
    nm = NetworkManagerFSA(rate_limit=3.0, rate_window=2.0)

    request = NetworkRequest(
        protocol=Protocol.HTTP,
        endpoint="https://api.example.com/limited",
        method="GET"
    )

    # Try to make requests
    for i in range(5):
        try:
            response = await nm.execute(request, use_cache=False)
            print(f"Request {i+1}: Allowed")
        except Exception as e:
            print(f"Request {i+1}: {type(e).__name__} - {e}")


async def example_retry_logic():
    """Example: Retry with exponential backoff"""
    print("\n=== Example 6: Retry Logic ===")

    nm = NetworkManagerFSA()

    # Configure retry handler
    nm.retry_handler.max_attempts = 3
    nm.retry_handler.base_delay = 0.5

    request = NetworkRequest(
        protocol=Protocol.HTTP,
        endpoint="https://flaky-api.example.com/data",
        method="GET",
        timeout=5.0
    )

    try:
        print("Attempting request with retry...")
        response = await nm.execute(request, use_retry=True)
        print(f"Success after retries: {response.status_code}")
    except Exception as e:
        print(f"Failed after all retries: {e}")


async def example_health_monitoring():
    """Example: Endpoint health monitoring"""
    print("\n=== Example 7: Health Monitoring ===")

    nm = NetworkManagerFSA()
    monitor = nm.health_monitor

    # Simulate some requests
    monitor.record_success("api1.example.com", response_time=0.15)
    monitor.record_success("api2.example.com", response_time=0.25)
    monitor.record_failure("api2.example.com")
    monitor.record_failure("api2.example.com")
    monitor.record_failure("api2.example.com")

    # Check health status
    print("Health status:")
    for endpoint in ["api1.example.com", "api2.example.com"]:
        status = monitor.get_status(endpoint)
        if status:
            print(f"  {endpoint}: {'Healthy' if status.is_healthy else 'Unhealthy'}")
            print(f"    Success: {status.success_count}, Failures: {status.failure_count}")


async def example_metrics_collection():
    """Example: Metrics collection"""
    print("\n=== Example 8: Metrics Collection ===")

    nm = NetworkManagerFSA()
    collector = nm.metrics_collector

    # Simulate various operations
    collector.record_request("http:GET", 0.15, success=True)
    collector.record_request("http:POST", 0.25, success=True)
    collector.record_request("http:GET", 0.10, success=True, cached=True)
    collector.record_request("http:DELETE", 0.30, success=False)

    # Get metrics
    metrics = collector.get_metrics()
    print(f"Total requests: {metrics.total_requests}")
    print(f"Successful: {metrics.successful_requests}")
    print(f"Failed: {metrics.failed_requests}")
    print(f"Cached: {metrics.cached_responses}")
    print(f"Average duration: {metrics.total_duration / metrics.total_requests:.3f}s")


async def example_tcp_udp():
    """Example: TCP and UDP requests"""
    print("\n=== Example 9: TCP/UDP Requests ===")

    nm = NetworkManagerFSA()

    # TCP request
    tcp_request = NetworkRequest(
        protocol=Protocol.TCP,
        endpoint="tcp://echo-server.example.com:7000",
        body="TCP message",
        timeout=5.0
    )

    # UDP request
    udp_request = NetworkRequest(
        protocol=Protocol.UDP,
        endpoint="udp://dns.example.com:53",
        body=b"\x00\x01",  # DNS query
        timeout=2.0
    )

    print("TCP and UDP examples (requires actual servers)")


def example_validation():
    """Example: Validate configuration"""
    print("\n=== Example 10: Configuration Validation ===")

    nm = NetworkManagerFSA()

    # Validate configuration
    is_valid = nm.validate()
    print(f"Configuration valid: {is_valid}")

    # Get error handling info
    info = nm.error_handling()
    print(f"Total connections: {info['total_connections']}")
    print(f"Active circuit breakers: {len(info['circuit_breakers'])}")


async def main():
    """Run all examples"""
    print("=" * 60)
    print("Network Manager FSA Examples")
    print("=" * 60)

    # Note: Most examples will fail without actual servers
    # This demonstrates the API usage patterns

    await example_http_request()
    # await example_websocket()
    # await example_circuit_breaker()
    await example_load_balancing()
    # await example_rate_limiting()
    # await example_retry_logic()
    await example_health_monitoring()
    await example_metrics_collection()
    await example_tcp_udp()
    example_validation()

    print("\n" + "=" * 60)
    print("Examples completed")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
