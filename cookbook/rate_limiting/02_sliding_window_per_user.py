"""
Sliding Window Per-User Rate Limiting Example

This example demonstrates how to use the SlidingWindowRateLimiter
to implement per-user rate limiting for an API.
"""

from time import sleep
from typing import Dict

from agno.rate_limit import SlidingWindowRateLimiter


class UserRateLimiter:
    """Manages per-user rate limits using sliding window"""

    def __init__(self, max_requests: int = 5, window_size: float = 10):
        self.max_requests = max_requests
        self.window_size = window_size
        self.limiters: Dict[str, SlidingWindowRateLimiter] = {}

    def allow_request(self, user_id: str) -> bool:
        """Check if user can make a request"""
        if user_id not in self.limiters:
            self.limiters[user_id] = SlidingWindowRateLimiter(
                rate_limit_id=user_id,
                max_requests=self.max_requests,
                window_size=self.window_size,
            )

        return self.limiters[user_id].allow_request()

    def get_user_stats(self, user_id: str) -> dict:
        """Get user's current rate limit stats"""
        if user_id not in self.limiters:
            return {
                "user_id": user_id,
                "requests": 0,
                "limit": self.max_requests,
                "retry_after": None,
            }

        limiter = self.limiters[user_id]
        return {
            "user_id": user_id,
            "requests": limiter.get_current_count(),
            "limit": self.max_requests,
            "requests_per_second": limiter.get_requests_per_second(),
            "retry_after": limiter.get_retry_after(),
            "state": limiter.current_state.value,
        }


def simulate_user_requests(user_limiter: UserRateLimiter, user_id: str, num_requests: int):
    """Simulate requests from a user"""
    print(f"\n{'='*60}")
    print(f"User: {user_id} - Making {num_requests} requests")
    print(f"{'='*60}")

    for i in range(1, num_requests + 1):
        allowed = user_limiter.allow_request(user_id)
        stats = user_limiter.get_user_stats(user_id)

        print(
            f"Request {i:2d}: {'✓ ALLOWED' if allowed else '✗ DENIED '} | "
            f"Count: {stats['requests']}/{stats['limit']} | "
            f"Rate: {stats['requests_per_second']:.2f} req/s | "
            f"State: {stats['state']}"
        )

        if not allowed and stats["retry_after"]:
            print(f"           → Rate limited! Retry after {stats['retry_after']:.2f}s")

        # Small delay between requests
        sleep(0.5)


def main():
    print("=" * 60)
    print("Sliding Window Per-User Rate Limiting Example")
    print("=" * 60)
    print("\nConfiguration:")
    print("  - Max Requests: 5 per user")
    print("  - Window Size: 10 seconds")
    print("  - Algorithm: Sliding Window")

    # Create user rate limiter (5 requests per 10 seconds)
    user_limiter = UserRateLimiter(max_requests=5, window_size=10)

    # Simulate requests from User A
    simulate_user_requests(user_limiter, "user_alice", num_requests=8)

    # Show that User B has independent limit
    print("\n" + "=" * 60)
    print("Switching to different user...")
    print("=" * 60)

    simulate_user_requests(user_limiter, "user_bob", num_requests=3)

    # Wait for User A's window to partially expire
    print("\n" + "=" * 60)
    print("Waiting 6 seconds for User A's old requests to expire...")
    print("=" * 60)
    sleep(6)

    # User A should now be able to make more requests
    print("\n" + "=" * 60)
    print("User A tries again after 6 seconds")
    print("=" * 60)

    stats = user_limiter.get_user_stats("user_alice")
    print(f"\nUser Alice Stats:")
    print(f"  - Current requests in window: {stats['requests']}/{stats['limit']}")
    print(f"  - Requests per second: {stats['requests_per_second']:.2f}")
    print(f"  - State: {stats['state']}")

    simulate_user_requests(user_limiter, "user_alice", num_requests=3)

    # Show final stats for all users
    print("\n" + "=" * 60)
    print("Final Statistics:")
    print("=" * 60)

    for user_id in ["user_alice", "user_bob"]:
        stats = user_limiter.get_user_stats(user_id)
        print(f"\n{user_id}:")
        print(f"  - Requests in window: {stats['requests']}/{stats['limit']}")
        print(f"  - Rate: {stats['requests_per_second']:.2f} req/s")
        print(f"  - State: {stats['state']}")
        if stats["retry_after"]:
            print(f"  - Retry after: {stats['retry_after']:.2f}s")


if __name__ == "__main__":
    main()
