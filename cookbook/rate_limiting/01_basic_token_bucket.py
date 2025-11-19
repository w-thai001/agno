"""
Basic Token Bucket Rate Limiting Example

This example demonstrates how to use the TokenBucketRateLimiter
to limit API calls to a model provider.
"""

from time import sleep, time

from agno.rate_limit import TokenBucketRateLimiter


def main():
    print("=" * 60)
    print("Token Bucket Rate Limiting Example")
    print("=" * 60)

    # Create a rate limiter that allows 10 requests per minute
    # with a burst capacity of 10
    limiter = TokenBucketRateLimiter(
        rate_limit_id="demo_api",
        capacity=10,  # Max burst of 10 requests
        refill_rate=10 / 60,  # 10 requests per 60 seconds = 0.1667 tokens/sec
    )

    print(f"\nRate Limiter Configuration:")
    print(f"  - Capacity: {limiter.capacity} tokens")
    print(f"  - Refill Rate: {limiter.refill_rate:.4f} tokens/second")
    print(f"  - Max Rate: {limiter.refill_rate * 60:.1f} requests/minute\n")

    # Simulate making requests
    print("Simulating 15 rapid requests:")
    print("-" * 60)

    for i in range(1, 16):
        allowed = limiter.allow_request()
        tokens_remaining = limiter.get_available_tokens()
        metrics = limiter.get_metrics()

        print(
            f"Request {i:2d}: {'✓ ALLOWED' if allowed else '✗ DENIED '} | "
            f"Tokens: {tokens_remaining:5.2f} | "
            f"State: {limiter.current_state.value:10s} | "
            f"Utilization: {metrics['utilization']:.1%}"
        )

        if not allowed:
            retry_after = limiter.get_retry_after()
            print(f"           → Rate limited! Retry after {retry_after:.2f} seconds")

    # Wait for some tokens to refill
    print("\n" + "=" * 60)
    print("Waiting 5 seconds for tokens to refill...")
    print("=" * 60)
    sleep(5)

    # Try requests again
    print("\nAfter 5 second wait:")
    print("-" * 60)

    for i in range(1, 4):
        allowed = limiter.allow_request()
        tokens_remaining = limiter.get_available_tokens()

        print(f"Request {i}: {'✓ ALLOWED' if allowed else '✗ DENIED'} | " f"Tokens: {tokens_remaining:5.2f}")

    # Show final metrics
    print("\n" + "=" * 60)
    print("Final Metrics:")
    print("=" * 60)

    final_metrics = limiter.get_metrics()
    print(f"  Total Requests: {final_metrics['total_requests']}")
    print(f"  Allowed: {final_metrics['allowed_requests']}")
    print(f"  Denied: {final_metrics['denied_requests']}")
    print(f"  Denial Rate: {final_metrics['denial_rate']:.1%}")
    print(f"  Current Utilization: {final_metrics['utilization']:.1%}")
    print(f"  Available Tokens: {final_metrics['current_capacity']:.2f}")
    print(f"  State: {final_metrics['current_state']}")


if __name__ == "__main__":
    main()
