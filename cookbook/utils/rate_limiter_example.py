"""
Production-Ready Rate Limiter Examples

This example demonstrates how to use the TokenBucketRateLimiter and
SlidingWindowRateLimiter for various rate limiting scenarios.

Requirements:
    pip install agno[redis]

Redis Setup:
    # Using Docker:
    docker run -d -p 6379:6379 redis:7.2.1

    # Or install locally:
    # See: https://redis.io/docs/getting-started/
"""

import time
from typing import Optional

from agno.utils.rate_limiter import (
    RateLimitResult,
    SlidingWindowRateLimiter,
    TokenBucketRateLimiter,
)


# ============================================================================
# Example 1: Basic Token Bucket Rate Limiting
# ============================================================================


def example_basic_rate_limiting():
    """
    Basic example: Limit requests to 10 per minute per user.
    """
    print("\n" + "=" * 70)
    print("Example 1: Basic Token Bucket Rate Limiting")
    print("=" * 70)

    # Initialize rate limiter
    # In production, use your Redis connection string
    limiter = TokenBucketRateLimiter(
        redis_client="redis://localhost:6379/0",
        default_max_requests=10,
        default_time_window_seconds=60,
    )

    user_id = "user_123"

    # Simulate 15 requests
    for i in range(15):
        result: RateLimitResult = limiter.allow_request(user_id)

        if result.allow_request:
            print(
                f"Request {i + 1}: ✓ Allowed "
                f"(Remaining: {result.remaining_tokens} tokens)"
            )
            # Process the request here
        else:
            print(
                f"Request {i + 1}: ✗ Rate Limited "
                f"(Retry after: {result.retry_after_seconds:.2f}s)"
            )
            # Return 429 Too Many Requests
            break


# ============================================================================
# Example 2: API Endpoint Protection
# ============================================================================


def rate_limit_decorator(
    max_requests: int = 100, time_window_seconds: int = 60
):
    """
    Decorator for rate limiting API endpoints.

    Usage:
        @rate_limit_decorator(max_requests=10, time_window_seconds=60)
        def my_api_endpoint(user_id: str):
            return {"status": "success"}
    """

    def decorator(func):
        limiter = TokenBucketRateLimiter(
            redis_client="redis://localhost:6379/0",
            default_max_requests=max_requests,
            default_time_window_seconds=time_window_seconds,
        )

        def wrapper(user_id: str, *args, **kwargs):
            result = limiter.allow_request(user_id)

            if not result.allow_request:
                raise Exception(
                    f"Rate limit exceeded. "
                    f"Retry after {result.retry_after_seconds:.2f} seconds"
                )

            # Add rate limit headers (useful for API responses)
            response = func(user_id, *args, **kwargs)
            if isinstance(response, dict):
                response["_rate_limit"] = {
                    "remaining": result.remaining_tokens,
                    "reset_after": result.retry_after_seconds,
                }

            return response

        return wrapper

    return decorator


@rate_limit_decorator(max_requests=5, time_window_seconds=10)
def protected_api_endpoint(user_id: str, data: Optional[str] = None):
    """Example API endpoint with rate limiting."""
    return {
        "user_id": user_id,
        "data": data or "Hello, World!",
        "timestamp": time.time(),
    }


def example_api_protection():
    """
    Demonstrate API endpoint protection with rate limiting.
    """
    print("\n" + "=" * 70)
    print("Example 2: API Endpoint Protection")
    print("=" * 70)

    user_id = "api_user_456"

    # Make 7 requests (limit is 5 per 10 seconds)
    for i in range(7):
        try:
            response = protected_api_endpoint(user_id, f"Request {i + 1}")
            rate_info = response.get("_rate_limit", {})
            print(
                f"Request {i + 1}: ✓ Success "
                f"(Remaining: {rate_info.get('remaining', 'N/A')})"
            )
        except Exception as e:
            print(f"Request {i + 1}: ✗ {e}")
            break

        time.sleep(0.5)  # Small delay between requests


# ============================================================================
# Example 3: Different Rate Limits for Different User Tiers
# ============================================================================


class TieredRateLimiter:
    """
    Rate limiter with different limits for different user tiers.
    """

    TIER_LIMITS = {
        "free": {"max_requests": 10, "time_window": 60},
        "basic": {"max_requests": 100, "time_window": 60},
        "premium": {"max_requests": 1000, "time_window": 60},
        "enterprise": {"max_requests": 10000, "time_window": 60},
    }

    def __init__(self, redis_client: str = "redis://localhost:6379/0"):
        self.limiter = TokenBucketRateLimiter(redis_client=redis_client)

    def check_rate_limit(
        self, user_id: str, tier: str = "free"
    ) -> RateLimitResult:
        """Check rate limit based on user tier."""
        limits = self.TIER_LIMITS.get(tier, self.TIER_LIMITS["free"])

        return self.limiter.allow_request(
            client_id=f"{tier}:{user_id}",
            max_requests=limits["max_requests"],
            time_window_seconds=limits["time_window"],
        )


def example_tiered_rate_limiting():
    """
    Demonstrate different rate limits for different user tiers.
    """
    print("\n" + "=" * 70)
    print("Example 3: Tiered Rate Limiting")
    print("=" * 70)

    limiter = TieredRateLimiter()

    # Test different tiers
    tiers = ["free", "basic", "premium"]
    for tier in tiers:
        result = limiter.check_rate_limit(f"user_{tier}", tier=tier)
        print(
            f"{tier.capitalize():10} tier: {result.remaining_tokens:5} requests remaining"
        )


# ============================================================================
# Example 4: Sliding Window Rate Limiting
# ============================================================================


def example_sliding_window():
    """
    Demonstrate sliding window rate limiting for more accurate tracking.
    """
    print("\n" + "=" * 70)
    print("Example 4: Sliding Window Rate Limiting")
    print("=" * 70)

    # Sliding window provides more accurate rate limiting
    # compared to fixed windows
    limiter = SlidingWindowRateLimiter(
        redis_client="redis://localhost:6379/0",
        default_max_requests=5,
        default_time_window_seconds=10,
    )

    user_id = "sliding_user_789"

    print("Making 5 requests quickly...")
    for i in range(5):
        result = limiter.allow_request(user_id)
        status = "✓" if result.allow_request else "✗"
        print(f"  Request {i + 1}: {status} (Remaining: {result.remaining_tokens})")

    print("\nWaiting 5 seconds...")
    time.sleep(5)

    print("Making 3 more requests...")
    for i in range(3):
        result = limiter.allow_request(user_id)
        status = "✓" if result.allow_request else "✗"
        print(
            f"  Request {i + 6}: {status} "
            f"(Remaining: {result.remaining_tokens}, "
            f"Retry after: {result.retry_after_seconds:.2f}s)"
        )


# ============================================================================
# Example 5: Burst Allowances
# ============================================================================


def example_burst_allowance():
    """
    Demonstrate burst allowances with token bucket.

    Token bucket naturally supports bursts - if tokens accumulate while
    the client is idle, they can be used in a burst later.
    """
    print("\n" + "=" * 70)
    print("Example 5: Burst Allowance")
    print("=" * 70)

    limiter = TokenBucketRateLimiter(
        redis_client="redis://localhost:6379/0",
        default_max_requests=10,  # Bucket capacity
        default_time_window_seconds=10,  # Refill rate: 1 token/second
    )

    user_id = "burst_user"

    # Reset user to start fresh
    limiter.reset_client(user_id)

    print("Waiting 5 seconds to accumulate tokens...")
    time.sleep(5)

    # Now we can burst up to 10 requests (the bucket capacity)
    # even though we're making them faster than 1 per second
    print("Making burst of 8 requests:")
    for i in range(8):
        result = limiter.allow_request(user_id)
        status = "✓" if result.allow_request else "✗"
        print(f"  Burst request {i + 1}: {status} (Remaining: {result.remaining_tokens})")


# ============================================================================
# Example 6: Multi-Token Requests
# ============================================================================


def example_multi_token_requests():
    """
    Demonstrate requesting multiple tokens for expensive operations.

    Some operations may be more expensive and should consume more tokens.
    """
    print("\n" + "=" * 70)
    print("Example 6: Multi-Token Requests")
    print("=" * 70)

    limiter = TokenBucketRateLimiter(
        redis_client="redis://localhost:6379/0",
        default_max_requests=100,
        default_time_window_seconds=60,
    )

    user_id = "multi_token_user"
    limiter.reset_client(user_id)

    operations = [
        ("simple_query", 1),
        ("complex_query", 5),
        ("data_export", 10),
        ("report_generation", 20),
    ]

    for operation, tokens in operations:
        result = limiter.allow_request(user_id, tokens_requested=tokens)

        if result.allow_request:
            print(
                f"{operation:20} (cost: {tokens:2} tokens): ✓ "
                f"(Remaining: {result.remaining_tokens})"
            )
        else:
            print(
                f"{operation:20} (cost: {tokens:2} tokens): ✗ "
                f"(Retry after: {result.retry_after_seconds:.2f}s)"
            )


# ============================================================================
# Example 7: Production Flask/FastAPI Integration
# ============================================================================


def example_production_integration():
    """
    Example of how to integrate rate limiting in a production API.

    This demonstrates best practices for production use.
    """
    print("\n" + "=" * 70)
    print("Example 7: Production Integration Pattern")
    print("=" * 70)

    print("""
# Flask Example:
from flask import Flask, request, jsonify
from agno.utils.rate_limiter import TokenBucketRateLimiter

app = Flask(__name__)
limiter = TokenBucketRateLimiter(
    redis_client="redis://redis-host:6379/0",
    default_max_requests=100,
    default_time_window_seconds=60
)

@app.route('/api/endpoint')
def api_endpoint():
    # Get client identifier (IP, user ID, API key, etc.)
    client_id = request.headers.get('X-API-Key') or request.remote_addr

    # Check rate limit
    result = limiter.allow_request(client_id)

    # Add rate limit headers
    response = jsonify({'data': 'your data'})
    response.headers['X-RateLimit-Remaining'] = str(result.remaining_tokens)
    response.headers['X-RateLimit-Reset'] = str(result.retry_after_seconds)

    if not result.allow_request:
        response.status_code = 429
        response.headers['Retry-After'] = str(int(result.retry_after_seconds))
        return response

    return response


# FastAPI Example:
from fastapi import FastAPI, Request, HTTPException
from agno.utils.rate_limiter import TokenBucketRateLimiter

app = FastAPI()
limiter = TokenBucketRateLimiter(
    redis_client="redis://redis-host:6379/0",
    default_max_requests=100,
    default_time_window_seconds=60
)

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_id = request.headers.get('X-API-Key') or request.client.host

    result = limiter.allow_request(client_id)

    if not result.allow_request:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Retry after {result.retry_after_seconds:.2f}s",
            headers={
                "Retry-After": str(int(result.retry_after_seconds)),
                "X-RateLimit-Remaining": "0"
            }
        )

    response = await call_next(request)
    response.headers['X-RateLimit-Remaining'] = str(result.remaining_tokens)
    return response
    """)


# ============================================================================
# Example 8: Monitoring and Metrics
# ============================================================================


def example_monitoring():
    """
    Demonstrate how to monitor rate limiting metrics.
    """
    print("\n" + "=" * 70)
    print("Example 8: Monitoring and Metrics")
    print("=" * 70)

    limiter = TokenBucketRateLimiter(
        redis_client="redis://localhost:6379/0",
        default_max_requests=100,
        default_time_window_seconds=60,
    )

    user_id = "monitored_user"

    # Get current client info
    info = limiter.get_client_info(user_id)
    if info:
        tokens, last_refill = info
        print(f"User: {user_id}")
        print(f"  Current tokens: {tokens:.2f}")
        print(f"  Last refill: {time.time() - last_refill:.2f}s ago")
    else:
        print(f"User {user_id} has not made any requests yet")

    # Make a request and show updated metrics
    result = limiter.allow_request(user_id)
    print(f"\nAfter request:")
    print(f"  Allowed: {result.allow_request}")
    print(f"  Remaining tokens: {result.remaining_tokens}")


# ============================================================================
# Main
# ============================================================================


def main():
    """Run all examples."""
    print("\n")
    print("=" * 70)
    print("Token Bucket Rate Limiter - Production Examples")
    print("=" * 70)
    print("\nNote: Make sure Redis is running on localhost:6379")
    print("      docker run -d -p 6379:6379 redis:7.2.1")

    try:
        # Run examples
        example_basic_rate_limiting()
        example_api_protection()
        example_tiered_rate_limiting()
        example_sliding_window()
        example_burst_allowance()
        example_multi_token_requests()
        example_production_integration()
        example_monitoring()

        print("\n" + "=" * 70)
        print("All examples completed successfully!")
        print("=" * 70 + "\n")

    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        print(
            "\nMake sure Redis is running: docker run -d -p 6379:6379 redis:7.2.1"
        )
        raise


if __name__ == "__main__":
    main()
