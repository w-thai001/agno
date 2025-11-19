"""
Fixed Window Rate Limiter FSA

The fixed window algorithm divides time into fixed windows (e.g., per minute, per hour).
Each window has a counter that tracks requests. The counter resets at window boundaries.

FSA States:
- AVAILABLE: Under rate limit in current window
- WARNING: Approaching rate limit (>80% of limit)
- LIMITED: Rate limit reached in current window
- RECOVERING: Waiting for window to reset

State Transitions:
[AVAILABLE] ──increment counter──> [WARNING] ──increment counter──> [LIMITED]
     ↑                                                                    ↓
     └─────────────────window reset───────────────────────────────────┘

Note: Fixed windows can have boundary issues where 2x limit can be reached
across window boundaries. Use SlidingWindowRateLimiter for more accuracy.
"""

from math import floor
from time import time
from typing import Optional

from agno.rate_limit.base import RateLimitExceeded, RateLimiter, RateLimitState
from agno.utils.log import logger


class FixedWindowRateLimiter(RateLimiter):
    """
    Fixed Window Rate Limiter FSA

    Example:
        # Allow 100 requests per minute
        limiter = FixedWindowRateLimiter(
            rate_limit_id="api_key_456",
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
    max_requests: int  # Maximum requests allowed per window
    window_size: float  # Window size in seconds
    current_window_start: float = 0.0  # Start time of current window
    current_window_count: int = 0  # Request count in current window
    raise_on_limit: bool = False

    def __init__(self, **data):
        super().__init__(**data)

        # Initialize to current window
        if self.current_window_start == 0.0:
            self.current_window_start = self._get_current_window_start()

        # Initialize metrics
        self.metrics.max_capacity = float(self.max_requests)
        self._update_current_capacity()

    def allow_request(self, tokens: float = 1.0) -> bool:
        """
        Check if request is allowed and increment counter

        Args:
            tokens: Number of requests to count (default 1.0, typically 1)

        Returns:
            True if request allowed, False otherwise

        Raises:
            RateLimitExceeded: If rate limit exceeded and raise_on_limit=True
        """
        # Check if we need to reset window
        self._check_and_reset_window()

        tokens_int = int(tokens)

        # Check if under limit
        if self.current_window_count + tokens_int <= self.max_requests:
            # Increment counter
            self.current_window_count += tokens_int

            self._update_metrics(allowed=True)
            self._update_current_capacity()
            self._update_state()

            logger.debug(
                f"FixedWindow[{self.rate_limit_id}]: Request allowed, "
                f"count: {self.current_window_count}/{self.max_requests}"
            )
            return True
        else:
            # Rate limit exceeded
            self._update_metrics(allowed=False)
            self.current_state = RateLimitState.LIMITED

            logger.warning(
                f"FixedWindow[{self.rate_limit_id}]: Rate limit exceeded, "
                f"count: {self.current_window_count}/{self.max_requests}"
            )

            if self.raise_on_limit:
                raise RateLimitExceeded(
                    message=f"Fixed window rate limit exceeded for {self.rate_limit_id}",
                    retry_after=self.get_retry_after(),
                    current_state=self.current_state,
                )

            return False

    def _get_current_window_start(self) -> float:
        """Calculate start time of current window"""
        now = time()
        # Floor to nearest window boundary
        window_number = floor(now / self.window_size)
        return window_number * self.window_size

    def _check_and_reset_window(self) -> None:
        """Check if window has expired and reset if needed"""
        current_window_start = self._get_current_window_start()

        if current_window_start > self.current_window_start:
            # Window has expired, reset counter
            logger.debug(
                f"FixedWindow[{self.rate_limit_id}]: Window reset, "
                f"previous count: {self.current_window_count}"
            )

            self.current_window_start = current_window_start
            self.current_window_count = 0
            self.current_state = RateLimitState.AVAILABLE

    def _update_current_capacity(self) -> None:
        """Update current capacity metric"""
        # Capacity represents available requests
        self.metrics.current_capacity = float(self.max_requests - self.current_window_count)

    def get_retry_after(self) -> Optional[float]:
        """
        Calculate time until next window starts

        Returns:
            Seconds until retry, or None if requests can proceed
        """
        self._check_and_reset_window()

        if self.current_window_count < self.max_requests:
            return None

        # Calculate time until next window
        now = time()
        next_window_start = self.current_window_start + self.window_size
        return max(0.0, next_window_start - now)

    def reset(self) -> None:
        """Reset the fixed window counter"""
        self.current_window_start = self._get_current_window_start()
        self.current_window_count = 0
        self.current_state = RateLimitState.AVAILABLE
        self.metrics = type(self.metrics)()
        self.metrics.max_capacity = float(self.max_requests)
        self.metrics.current_capacity = float(self.max_requests)
        logger.debug(f"FixedWindow[{self.rate_limit_id}]: Reset")

    def get_current_count(self) -> int:
        """Get current number of requests in window"""
        self._check_and_reset_window()
        return self.current_window_count

    def get_time_until_reset(self) -> float:
        """Get time in seconds until window resets"""
        now = time()
        next_window_start = self.current_window_start + self.window_size
        return max(0.0, next_window_start - now)

    def set_max_requests(self, new_max: int) -> None:
        """Dynamically adjust maximum requests"""
        old_max = self.max_requests
        self.max_requests = new_max
        self.metrics.max_capacity = float(new_max)
        self._update_current_capacity()
        self._update_state()

        logger.debug(f"FixedWindow[{self.rate_limit_id}]: Max requests adjusted from {old_max} to {new_max}")

    def set_window_size(self, new_window_size: float) -> None:
        """Dynamically adjust window size (resets current window)"""
        old_size = self.window_size
        self.window_size = new_window_size
        # Reset to new window
        self.current_window_start = self._get_current_window_start()
        self.current_window_count = 0
        self._update_current_capacity()

        logger.debug(
            f"FixedWindow[{self.rate_limit_id}]: Window size adjusted "
            f"from {old_size}s to {new_window_size}s (window reset)"
        )
