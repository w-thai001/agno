"""
Sliding Window Rate Limiter FSA

The sliding window algorithm tracks requests in a time window that slides continuously.
It provides more accurate rate limiting than fixed windows by avoiding boundary issues.

FSA States:
- AVAILABLE: Under rate limit, requests can proceed
- WARNING: Approaching rate limit (>80% of limit)
- LIMITED: Rate limit reached, requests blocked
- RECOVERING: Old requests expiring, capacity recovering

State Transitions:
[AVAILABLE] ──add request──> [WARNING] ──add request──> [LIMITED]
     ↑                           ↑                          ↑
     └──expire old requests──────┴──expire old requests────┘

Implementation:
Uses a sliding log of timestamps. Requests outside the window are automatically expired.
"""

from collections import deque
from time import time
from typing import Deque, Optional

from agno.rate_limit.base import RateLimitExceeded, RateLimiter, RateLimitState
from agno.utils.log import logger


class SlidingWindowRateLimiter(RateLimiter):
    """
    Sliding Window Rate Limiter FSA

    Example:
        # Allow 100 requests per minute
        limiter = SlidingWindowRateLimiter(
            rate_limit_id="user_123",
            max_requests=100,
            window_size=60,  # seconds
        )

        if limiter.allow_request():
            # Process request
            pass
        else:
            retry_after = limiter.get_retry_after()
            print(f"Rate limited, retry after {retry_after}s")
    """

    rate_limit_id: str
    max_requests: int  # Maximum requests allowed in window
    window_size: float  # Window size in seconds
    request_timestamps: Deque[float] = deque()  # Sliding log of request times
    raise_on_limit: bool = False

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, **data):
        # Initialize deque if not provided
        if "request_timestamps" not in data or data["request_timestamps"] is None:
            data["request_timestamps"] = deque()

        super().__init__(**data)

        # Initialize metrics
        self.metrics.max_capacity = float(self.max_requests)
        self._update_current_capacity()

    def allow_request(self, tokens: float = 1.0) -> bool:
        """
        Check if request is allowed and record timestamp

        Args:
            tokens: Number of requests to count (default 1.0, typically 1)

        Returns:
            True if request allowed, False otherwise

        Raises:
            RateLimitExceeded: If rate limit exceeded and raise_on_limit=True
        """
        # Remove expired requests
        self._expire_old_requests()

        # Check if under limit
        current_count = len(self.request_timestamps)
        tokens_int = int(tokens)  # Sliding window typically uses whole requests

        if current_count + tokens_int <= self.max_requests:
            # Add request timestamp(s)
            now = time()
            for _ in range(tokens_int):
                self.request_timestamps.append(now)

            self._update_metrics(allowed=True)
            self._update_current_capacity()
            self._update_state()

            logger.debug(
                f"SlidingWindow[{self.rate_limit_id}]: Request allowed, "
                f"count: {current_count + tokens_int}/{self.max_requests}"
            )
            return True
        else:
            # Rate limit exceeded
            self._update_metrics(allowed=False)
            self.current_state = RateLimitState.LIMITED

            logger.warning(
                f"SlidingWindow[{self.rate_limit_id}]: Rate limit exceeded, "
                f"count: {current_count}/{self.max_requests}"
            )

            if self.raise_on_limit:
                raise RateLimitExceeded(
                    message=f"Sliding window rate limit exceeded for {self.rate_limit_id}",
                    retry_after=self.get_retry_after(),
                    current_state=self.current_state,
                )

            return False

    def _expire_old_requests(self) -> None:
        """Remove requests outside the sliding window"""
        now = time()
        window_start = now - self.window_size

        # Remove timestamps older than window_start
        while self.request_timestamps and self.request_timestamps[0] < window_start:
            self.request_timestamps.popleft()

    def _update_current_capacity(self) -> None:
        """Update current capacity metric"""
        current_count = len(self.request_timestamps)
        # Capacity represents available requests
        self.metrics.current_capacity = float(self.max_requests - current_count)

    def get_retry_after(self) -> Optional[float]:
        """
        Calculate time until next request can be made

        Returns:
            Seconds until retry, or None if requests can proceed
        """
        self._expire_old_requests()
        current_count = len(self.request_timestamps)

        if current_count < self.max_requests:
            return None

        # Calculate when oldest request will expire
        oldest_timestamp = self.request_timestamps[0]
        now = time()
        time_since_oldest = now - oldest_timestamp

        # Time until oldest request exits the window
        return max(0.0, self.window_size - time_since_oldest)

    def reset(self) -> None:
        """Reset the sliding window"""
        self.request_timestamps.clear()
        self.current_state = RateLimitState.AVAILABLE
        self.metrics = type(self.metrics)()
        self.metrics.max_capacity = float(self.max_requests)
        self.metrics.current_capacity = float(self.max_requests)
        logger.debug(f"SlidingWindow[{self.rate_limit_id}]: Reset")

    def get_current_count(self) -> int:
        """Get current number of requests in window"""
        self._expire_old_requests()
        return len(self.request_timestamps)

    def get_requests_per_second(self) -> float:
        """Calculate current requests per second rate"""
        self._expire_old_requests()
        count = len(self.request_timestamps)

        if count == 0:
            return 0.0

        return count / self.window_size

    def set_max_requests(self, new_max: int) -> None:
        """Dynamically adjust maximum requests"""
        old_max = self.max_requests
        self.max_requests = new_max
        self.metrics.max_capacity = float(new_max)
        self._update_current_capacity()
        self._update_state()

        logger.debug(
            f"SlidingWindow[{self.rate_limit_id}]: Max requests adjusted " f"from {old_max} to {new_max}"
        )

    def set_window_size(self, new_window_size: float) -> None:
        """Dynamically adjust window size"""
        old_size = self.window_size
        self.window_size = new_window_size
        # Expire requests based on new window size
        self._expire_old_requests()
        self._update_current_capacity()

        logger.debug(
            f"SlidingWindow[{self.rate_limit_id}]: Window size adjusted "
            f"from {old_size}s to {new_window_size}s"
        )
