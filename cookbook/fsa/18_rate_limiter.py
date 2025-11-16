"""🚦 FSA Rate Limiter Example

This example demonstrates rate limiting for FSA execution to prevent resource
exhaustion and ensure fair usage.

Run `pip install agno` to install dependencies.
"""

from agno.fsa.rate_limiter import (
    FSARateLimiter,
    RateLimitAlgorithm,
    RateLimitExceeded
)
from agno.fsa.code_builder import MultiStepCodeBuilder
import time


def main():
    """Demonstrate FSA Rate Limiter"""

    print("\n" + "=" * 70)
    print("FSA RATE LIMITER - RESOURCE CONTROL")
    print("=" * 70)

    # =========================================================================
    # Example 1: Token Bucket Algorithm
    # =========================================================================
    print("\n" + "─" * 70)
    print("EXAMPLE 1: TOKEN BUCKET ALGORITHM")
    print("─" * 70)

    print("\n🪣 Token Bucket Rate Limiter:")
    print("   - 5 requests per second")
    print("   - Burst size: 10 tokens")
    print("   - Allows bursts up to bucket capacity")

    token_limiter = FSARateLimiter(
        name="TokenBucketLimiter",
        requests_per_second=5.0,
        algorithm="token_bucket",
        burst_size=10,
        debug_mode=True
    )

    print(f"\n✓ Rate limiter created")

    # Create test FSA
    test_fsa = MultiStepCodeBuilder(
        name="TestService",
        programming_language="python"
    )

    # Test burst handling
    print(f"\n🔥 Testing burst capacity (sending 10 rapid requests):")

    for i in range(10):
        try:
            result = token_limiter.execute_limited(
                test_fsa,
                context={"task": f"Request {i + 1}"},
                wait_if_limited=False
            )

            status = token_limiter.get_status()
            print(f"  {i + 1}. ✅ Allowed (Remaining: {status.remaining_quota} tokens)")

        except RateLimitExceeded as e:
            print(f"  {i + 1}. ❌ Rate limited: {e}")

    # Check metrics
    metrics = token_limiter.get_metrics()
    print(f"\n📊 Metrics:")
    print(f"  Total Requests: {metrics.total_requests}")
    print(f"  Allowed: {metrics.allowed_requests}")
    print(f"  Rejected: {metrics.rejected_requests}")
    print(f"  Current Rate: {metrics.current_rate:.2f} req/s")

    # =========================================================================
    # Example 2: Sliding Window Algorithm
    # =========================================================================
    print("\n\n" + "=" * 70)
    print("EXAMPLE 2: SLIDING WINDOW ALGORITHM")
    print("=" * 70)

    print("\n📊 Sliding Window Rate Limiter:")
    print("   - 10 requests per 60 seconds")
    print("   - Smooth rate limiting over time window")

    sliding_limiter = FSARateLimiter(
        name="SlidingWindowLimiter",
        requests_per_second=10.0 / 60.0,  # 10 requests per 60 seconds
        algorithm="sliding_window",
        window_size_seconds=60.0,
        debug_mode=False  # Less verbose
    )

    print(f"\n📈 Sending requests over time:")

    for i in range(12):
        try:
            result = sliding_limiter.execute_limited(
                test_fsa,
                context={"task": f"Request {i + 1}"},
                wait_if_limited=False
            )

            status = sliding_limiter.get_status()
            print(f"  {i + 1}. ✅ Allowed (Quota: {status.remaining_quota})")

        except RateLimitExceeded as e:
            status = sliding_limiter.get_status()
            print(f"  {i + 1}. ❌ Rate limited")
            print(f"      Retry after: {status.retry_after_seconds:.1f}s")

        time.sleep(0.1)  # Small delay between requests

    # =========================================================================
    # Example 3: Fixed Window Algorithm
    # =========================================================================
    print("\n\n" + "=" * 70)
    print("EXAMPLE 3: FIXED WINDOW ALGORITHM")
    print("=" * 70)

    print("\n🪟 Fixed Window Rate Limiter:")
    print("   - 5 requests per 10-second window")
    print("   - Quota resets at window boundaries")

    fixed_limiter = FSARateLimiter(
        name="FixedWindowLimiter",
        requests_per_second=5.0 / 10.0,  # 5 requests per 10 seconds
        algorithm="fixed_window",
        window_size_seconds=10.0,
        debug_mode=False
    )

    print(f"\n⏱️  Testing window reset:")

    # Phase 1: Use quota
    print(f"\n  Phase 1 - Using quota:")
    for i in range(7):
        try:
            result = fixed_limiter.execute_limited(
                test_fsa,
                context={"task": f"Request {i + 1}"},
                wait_if_limited=False
            )
            print(f"    {i + 1}. ✅ Allowed")
        except RateLimitExceeded:
            status = fixed_limiter.get_status()
            print(f"    {i + 1}. ❌ Rate limited (wait {status.retry_after_seconds:.1f}s)")

    # Wait for window reset
    print(f"\n  ⏳ Waiting for window to reset...")
    time.sleep(10.5)

    # Phase 2: New window
    print(f"\n  Phase 2 - After window reset:")
    for i in range(3):
        try:
            result = fixed_limiter.execute_limited(
                test_fsa,
                context={"task": f"Request {i + 1}"},
                wait_if_limited=False
            )
            status = fixed_limiter.get_status()
            print(f"    {i + 1}. ✅ Allowed (Quota: {status.remaining_quota})")
        except RateLimitExceeded:
            print(f"    {i + 1}. ❌ Rate limited")

    # =========================================================================
    # Example 4: Concurrent Execution Limit
    # =========================================================================
    print("\n\n" + "=" * 70)
    print("EXAMPLE 4: CONCURRENT EXECUTION LIMIT")
    print("=" * 70)

    print("\n👥 Concurrent Execution Limiter:")
    print("   - Maximum 3 concurrent executions")
    print("   - Prevents resource exhaustion")

    concurrent_limiter = FSARateLimiter(
        name="ConcurrentLimiter",
        algorithm="concurrent_limit",
        max_concurrent=3,
        debug_mode=False
    )

    print(f"\n🔢 Testing concurrent limit:")

    # Simulate concurrent requests
    for i in range(5):
        try:
            status = concurrent_limiter.get_status()
            print(f"  Request {i + 1}: Quota={status.remaining_quota}")

            result = concurrent_limiter.execute_limited(
                test_fsa,
                context={"task": f"Request {i + 1}"},
                wait_if_limited=False
            )
            print(f"    ✅ Executed")

        except RateLimitExceeded as e:
            print(f"    ❌ Concurrent limit reached")

    # =========================================================================
    # Example 5: Wait When Limited
    # =========================================================================
    print("\n\n" + "=" * 70)
    print("EXAMPLE 5: AUTOMATIC WAITING WHEN LIMITED")
    print("=" * 70)

    print("\n⏰ Rate Limiter with Auto-Wait:")
    print("   - Automatically waits when rate limited")
    print("   - Ensures all requests eventually succeed")

    wait_limiter = FSARateLimiter(
        name="WaitLimiter",
        requests_per_second=2.0,  # 2 requests per second
        algorithm="token_bucket",
        burst_size=3,
        debug_mode=False
    )

    print(f"\n📤 Sending 5 requests (auto-wait enabled):")

    start_time = time.time()

    for i in range(5):
        request_start = time.time()

        # This will wait if rate limited
        result = wait_limiter.execute_limited(
            test_fsa,
            context={"task": f"Request {i + 1}"},
            wait_if_limited=True  # Auto-wait
        )

        elapsed = time.time() - request_start
        total_elapsed = time.time() - start_time

        status = wait_limiter.get_status()
        print(f"  {i + 1}. ✅ Completed in {elapsed:.2f}s (Total: {total_elapsed:.2f}s)")
        print(f"      Remaining quota: {status.remaining_quota}")

    # =========================================================================
    # Example 6: Rate Limit Callbacks
    # =========================================================================
    print("\n\n" + "=" * 70)
    print("EXAMPLE 6: RATE LIMIT EXCEEDED CALLBACKS")
    print("=" * 70)

    print("\n🔔 Rate Limiter with Callback:")

    callback_count = [0]  # Use list for mutability

    def on_rate_limit(retry_after):
        callback_count[0] += 1
        print(f"  ⚠️  Callback triggered! Retry after {retry_after:.2f}s")

    callback_limiter = FSARateLimiter(
        name="CallbackLimiter",
        requests_per_second=1.0,
        algorithm="token_bucket",
        burst_size=2,
        debug_mode=False
    )

    callback_limiter.on_rate_limit_exceeded = on_rate_limit

    print(f"\n📞 Sending rapid requests (callback on rate limit):")

    for i in range(5):
        try:
            result = callback_limiter.execute_limited(
                test_fsa,
                context={"task": f"Request {i + 1}"},
                wait_if_limited=False
            )
            print(f"  {i + 1}. ✅ Allowed")
        except RateLimitExceeded:
            print(f"  {i + 1}. ❌ Rate limited")

    print(f"\n📊 Callback invoked: {callback_count[0]} times")

    # =========================================================================
    # Example 7: Rate Limiter Status & Metrics
    # =========================================================================
    print("\n\n" + "=" * 70)
    print("EXAMPLE 7: STATUS & METRICS")
    print("=" * 70)

    status = callback_limiter.get_status()
    metrics = callback_limiter.get_metrics()

    print(f"\n📊 Rate Limit Status:")
    print(f"  Allowed: {status.allowed}")
    print(f"  Remaining Quota: {status.remaining_quota}")
    print(f"  Reset Time: {status.reset_time}")
    print(f"  Retry After: {status.retry_after_seconds:.2f}s")

    print(f"\n📈 Rate Limiter Metrics:")
    print(f"  Algorithm: {metrics.algorithm.value}")
    print(f"  Total Requests: {metrics.total_requests}")
    print(f"  Allowed: {metrics.allowed_requests} ({metrics.allowed_requests / max(metrics.total_requests, 1) * 100:.1f}%)")
    print(f"  Rejected: {metrics.rejected_requests} ({metrics.rejected_requests / max(metrics.total_requests, 1) * 100:.1f}%)")
    print(f"  Current Rate: {metrics.current_rate:.2f} req/s")
    print(f"  Quota Remaining: {metrics.quota_remaining}")

    # =========================================================================
    # Example 8: Production Use Case
    # =========================================================================
    print("\n\n" + "=" * 70)
    print("EXAMPLE 8: PRODUCTION USE CASE")
    print("=" * 70)

    print("\n🏭 Production API Rate Limiting:")
    print("   - Protect external API from overload")
    print("   - 100 requests per minute limit")
    print("   - Burst capacity: 20 requests")

    api_limiter = FSARateLimiter(
        name="APIRateLimiter",
        requests_per_second=100.0 / 60.0,  # 100 per minute
        algorithm="token_bucket",
        burst_size=20,
        debug_mode=False
    )

    api_service = MultiStepCodeBuilder(
        name="ExternalAPI",
        programming_language="python"
    )

    print(f"\n🌐 Simulating API calls:")

    successful = 0
    rate_limited = 0

    for i in range(25):
        try:
            result = api_limiter.execute_limited(
                api_service,
                context={"endpoint": "/api/data", "request_id": i + 1},
                wait_if_limited=False
            )
            successful += 1

            if i < 5 or i >= 20:  # Show first 5 and last 5
                print(f"  Request {i + 1}: ✅ Success")
            elif i == 5:
                print(f"  ...")

        except RateLimitExceeded:
            rate_limited += 1
            if i >= 20:  # Show limited requests
                print(f"  Request {i + 1}: ❌ Rate limited")

    print(f"\n📊 API Call Summary:")
    print(f"  Successful: {successful}")
    print(f"  Rate Limited: {rate_limited}")
    print(f"  Success Rate: {successful / 25 * 100:.1f}%")

    # =========================================================================
    # Best Practices
    # =========================================================================
    print("\n\n" + "=" * 70)
    print("RATE LIMITING BEST PRACTICES")
    print("=" * 70)

    practices = [
        "1. Choose algorithm based on use case:",
        "   - Token Bucket: Best for burstable workloads",
        "   - Sliding Window: Smooth, consistent rate limiting",
        "   - Fixed Window: Simple, predictable quota resets",
        "   - Concurrent Limit: Prevent resource exhaustion",
        "2. Set appropriate burst sizes for token bucket",
        "3. Use wait_if_limited=True for background jobs",
        "4. Use wait_if_limited=False for user-facing APIs",
        "5. Monitor rejected_requests to tune limits",
        "6. Implement callbacks for rate limit alerts",
        "7. Consider distributed rate limiting for multi-instance deployments",
        "8. Reset quotas periodically for long-running systems",
        "9. Log rate limit events for analysis",
        "10. Combine with circuit breaker for comprehensive protection"
    ]

    for practice in practices:
        print(f"   {practice}")

    print("\n" + "=" * 70)
    print("✅ Rate limiter demonstration complete!")
    print("=" * 70)

    print("\n💡 Key Takeaway: Rate limiting prevents resource exhaustion")
    print("   and ensures fair usage across all consumers!")


if __name__ == "__main__":
    main()
