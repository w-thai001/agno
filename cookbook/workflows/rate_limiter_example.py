"""
Rate Limiter Example Usage

This script demonstrates various use cases for the RateLimiter workflow:
1. API endpoint protection
2. User quota management
3. Service-to-service rate limiting
4. Dynamic rate limit configuration

Run this example:
    python cookbook/workflows/rate_limiter_example.py

Prerequisites:
    - Redis running on localhost:6379
    - Install dependencies: pip install redis agno
"""

import time
from rate_limiter import RateLimiter, RateLimitRequest, RateLimitResponse


def example_1_api_endpoint_protection():
    """
    Example 1: Protecting an API endpoint from abuse

    Scenario: REST API with 100 requests per minute per user
    """
    print("\n" + "=" * 70)
    print("Example 1: API Endpoint Protection")
    print("=" * 70)
    print("Scenario: REST API with 100 requests/minute per user\n")

    limiter = RateLimiter(redis_url="redis://localhost:6379/0")

    # Simulate API requests from a user
    user_id = "api_user_12345"

    def handle_api_request(endpoint: str, user_id: str) -> dict:
        """Simulate handling an API request with rate limiting"""

        # Check rate limit
        request = RateLimitRequest(
            client_id=user_id,
            max_requests=100,
            time_window_seconds=60,
            tokens_requested=1
        )

        response = limiter.check_rate_limit(request)

        if response.allow_request:
            # Process the request
            return {
                "status": "success",
                "endpoint": endpoint,
                "data": {"message": "Request processed successfully"},
                "rate_limit": {
                    "remaining": int(response.remaining_tokens),
                    "reset": int(response.window_reset_time)
                }
            }
        else:
            # Return 429 Too Many Requests
            return {
                "status": "error",
                "error": "Rate limit exceeded",
                "retry_after": response.retry_after_seconds,
                "rate_limit": {
                    "remaining": 0,
                    "reset": int(response.window_reset_time)
                }
            }

    # Simulate 5 API requests
    for i in range(5):
        result = handle_api_request("/api/v1/users", user_id)
        print(f"Request {i+1}: {result['status']:8s} | "
              f"Remaining: {result['rate_limit']['remaining']:3d}")

    print("\n✓ Example 1 completed")


def example_2_tiered_rate_limits():
    """
    Example 2: Tiered rate limits for different user plans

    Scenario: Free, Pro, and Enterprise users with different limits
    """
    print("\n" + "=" * 70)
    print("Example 2: Tiered Rate Limits (User Plans)")
    print("=" * 70)
    print("Scenario: Different limits for Free, Pro, and Enterprise users\n")

    limiter = RateLimiter(redis_url="redis://localhost:6379/0")

    # Define rate limits for each tier
    rate_limits = {
        "free": {"max_requests": 10, "time_window": 60},
        "pro": {"max_requests": 100, "time_window": 60},
        "enterprise": {"max_requests": 1000, "time_window": 60}
    }

    def check_user_rate_limit(user_id: str, plan: str) -> RateLimitResponse:
        """Check rate limit based on user plan"""
        limits = rate_limits[plan]

        request = RateLimitRequest(
            client_id=f"{plan}:{user_id}",  # Include plan in client_id
            max_requests=limits["max_requests"],
            time_window_seconds=limits["time_window"]
        )

        return limiter.check_rate_limit(request)

    # Test each plan
    users = [
        ("user_001", "free"),
        ("user_002", "pro"),
        ("user_003", "enterprise")
    ]

    for user_id, plan in users:
        response = check_user_rate_limit(user_id, plan)
        print(f"{plan:12s} user '{user_id}': "
              f"Allowed={response.allow_request} | "
              f"Limit={rate_limits[plan]['max_requests']:4d} | "
              f"Remaining={response.remaining_tokens:7.2f}")

    print("\n✓ Example 2 completed")


def example_3_weighted_operations():
    """
    Example 3: Different costs for different operations

    Scenario: Heavy operations consume more tokens
    """
    print("\n" + "=" * 70)
    print("Example 3: Weighted Operations (Different Token Costs)")
    print("=" * 70)
    print("Scenario: Heavy operations consume more tokens\n")

    limiter = RateLimiter(redis_url="redis://localhost:6379/0")

    # Define operation costs
    operation_costs = {
        "read": 1,
        "write": 5,
        "delete": 10,
        "bulk_export": 50,
        "analytics_query": 20
    }

    user_id = "power_user_789"

    # Reset to start fresh
    limiter.reset_client_limit(user_id, 100, 60)

    print(f"Starting with 100 tokens for user '{user_id}'\n")

    # Simulate various operations
    operations = [
        "read",
        "read",
        "write",
        "read",
        "analytics_query",
        "write",
        "bulk_export",
        "delete"
    ]

    for op in operations:
        tokens_needed = operation_costs[op]

        request = RateLimitRequest(
            client_id=user_id,
            max_requests=100,
            time_window_seconds=60,
            tokens_requested=tokens_needed
        )

        response = limiter.check_rate_limit(request)

        status = "✓" if response.allow_request else "✗"
        print(f"{status} {op:20s} (cost: {tokens_needed:2d} tokens) | "
              f"Remaining: {response.remaining_tokens:6.2f}")

    print("\n✓ Example 3 completed")


def example_4_burst_handling():
    """
    Example 4: Handling burst traffic with burst multiplier

    Scenario: Allow temporary bursts but maintain average rate
    """
    print("\n" + "=" * 70)
    print("Example 4: Burst Traffic Handling")
    print("=" * 70)
    print("Scenario: Allow bursts up to 2x normal rate\n")

    limiter = RateLimiter(redis_url="redis://localhost:6379/0")

    user_id = "bursty_user_456"

    # Reset to start fresh
    limiter.reset_client_limit(user_id, 10, 10)

    print("Normal limit: 10 requests / 10 seconds")
    print("Burst capacity: 20 requests (2x multiplier)\n")

    # Send burst of requests
    print("Sending burst of 15 requests immediately:")
    for i in range(15):
        request = RateLimitRequest(
            client_id=user_id,
            max_requests=10,
            time_window_seconds=10,
            burst_multiplier=2.0  # Allow bursts up to 20 requests
        )

        response = limiter.check_rate_limit(request)

        status = "✓ ALLOWED" if response.allow_request else "✗ DENIED"
        print(f"  Request {i+1:2d}: {status} | Remaining: {response.remaining_tokens:5.2f}")

    print("\n✓ Example 4 completed")


def example_5_distributed_rate_limiting():
    """
    Example 5: Distributed rate limiting across multiple servers

    Scenario: Multiple API servers sharing the same rate limit state
    """
    print("\n" + "=" * 70)
    print("Example 5: Distributed Rate Limiting")
    print("=" * 70)
    print("Scenario: Multiple servers sharing rate limit state via Redis\n")

    # Create multiple limiter instances (simulating different servers)
    limiter_server1 = RateLimiter(redis_url="redis://localhost:6379/0")
    limiter_server2 = RateLimiter(redis_url="redis://localhost:6379/0")
    limiter_server3 = RateLimiter(redis_url="redis://localhost:6379/0")

    user_id = "distributed_user_999"

    # Reset to start fresh
    limiter_server1.reset_client_limit(user_id, 10, 60)

    print("Simulating requests across 3 servers (shared limit: 10 req/60s)\n")

    servers = [
        ("Server 1", limiter_server1),
        ("Server 2", limiter_server2),
        ("Server 3", limiter_server3),
        ("Server 1", limiter_server1),
        ("Server 2", limiter_server2),
        ("Server 3", limiter_server3),
        ("Server 1", limiter_server1),
        ("Server 2", limiter_server2),
        ("Server 3", limiter_server3),
        ("Server 1", limiter_server1),
        ("Server 2", limiter_server2),
        ("Server 3", limiter_server3),
    ]

    for server_name, limiter in servers:
        request = RateLimitRequest(
            client_id=user_id,
            max_requests=10,
            time_window_seconds=60
        )

        response = limiter.check_rate_limit(request)

        status = "✓" if response.allow_request else "✗"
        print(f"{status} {server_name}: Remaining = {response.remaining_tokens:5.2f}")

    print("\n✓ Example 5 completed - All servers see consistent state")


def example_6_monitoring_and_stats():
    """
    Example 6: Monitoring rate limit usage and statistics

    Scenario: Track usage patterns and get statistics
    """
    print("\n" + "=" * 70)
    print("Example 6: Monitoring and Statistics")
    print("=" * 70)
    print("Scenario: Track usage patterns for analytics\n")

    limiter = RateLimiter(redis_url="redis://localhost:6379/0")

    # Create some activity
    users = ["user_001", "user_002", "user_003"]

    for user in users:
        limiter.reset_client_limit(user, 100, 60)

        # Simulate different usage patterns
        if user == "user_001":
            num_requests = 25
        elif user == "user_002":
            num_requests = 75
        else:
            num_requests = 95

        for _ in range(num_requests):
            request = RateLimitRequest(
                client_id=user,
                max_requests=100,
                time_window_seconds=60
            )
            limiter.check_rate_limit(request)

    # Get statistics for each user
    print("User Statistics:\n")
    for user in users:
        stats = limiter.get_client_stats(user, 100, 60)

        usage_percent = ((100 - stats['tokens']) / 100) * 100

        print(f"{user}:")
        print(f"  Total requests: {stats['total_requests']}")
        print(f"  Remaining tokens: {stats['tokens']:.2f}")
        print(f"  Usage: {usage_percent:.1f}%")
        print(f"  TTL: {stats['ttl']}s")
        print()

    print("✓ Example 6 completed")


def example_7_graceful_degradation():
    """
    Example 7: Graceful degradation when Redis is unavailable

    Scenario: System continues to function when Redis fails
    """
    print("\n" + "=" * 70)
    print("Example 7: Graceful Degradation")
    print("=" * 70)
    print("Scenario: Handle Redis failures gracefully\n")

    # Try to connect to non-existent Redis instance
    try:
        limiter = RateLimiter(redis_url="redis://localhost:9999/0")
    except ConnectionError as e:
        print(f"Expected error: {e}\n")
        print("✓ Example 7 completed - System properly handles Redis failures")


def example_8_workflow_interface():
    """
    Example 8: Using the Workflow run() interface

    Scenario: Use the high-level workflow interface
    """
    print("\n" + "=" * 70)
    print("Example 8: Workflow Interface")
    print("=" * 70)
    print("Scenario: Using the workflow run() method\n")

    limiter = RateLimiter(redis_url="redis://localhost:6379/0")

    # Check rate limit
    print("1. Check rate limit:")
    for response in limiter.run(
        client_id="workflow_user",
        max_requests=5,
        time_window_seconds=60,
        operation="check"
    ):
        print(f"   {response.content}\n")

    # Get statistics
    print("2. Get statistics:")
    for response in limiter.run(
        client_id="workflow_user",
        operation="stats"
    ):
        print(f"   {response.content}\n")

    # Reset limit
    print("3. Reset limit:")
    for response in limiter.run(
        client_id="workflow_user",
        operation="reset"
    ):
        print(f"   {response.content}\n")

    print("✓ Example 8 completed")


def main():
    """Run all examples"""
    print("\n" + "=" * 70)
    print("RATE LIMITER WORKFLOW - COMPREHENSIVE EXAMPLES")
    print("=" * 70)

    try:
        example_1_api_endpoint_protection()
        example_2_tiered_rate_limits()
        example_3_weighted_operations()
        example_4_burst_handling()
        example_5_distributed_rate_limiting()
        example_6_monitoring_and_stats()
        example_7_graceful_degradation()
        example_8_workflow_interface()

        print("\n" + "=" * 70)
        print("ALL EXAMPLES COMPLETED SUCCESSFULLY!")
        print("=" * 70)

    except ConnectionError as e:
        print(f"\n✗ Error: {e}")
        print("\nMake sure Redis is running:")
        print("  docker run -d -p 6379:6379 redis:7.2.1")
        print("  OR")
        print("  redis-server")

    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
