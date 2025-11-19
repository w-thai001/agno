"""
Token Bucket Rate Limiter FSA

The token bucket algorithm maintains a bucket of tokens that refills at a constant rate.
Each request consumes tokens from the bucket. If the bucket is empty, requests are denied.

FSA States:
- AVAILABLE: Bucket has tokens, requests can proceed
- WARNING: Bucket below 20% capacity
- RECOVERING: Tokens being added back to bucket
- LIMITED: Bucket empty, requests blocked

State Transitions:
[AVAILABLE] ──consume tokens──> [WARNING] ──consume tokens──> [LIMITED]
     ↑                              ↑                              ↑
     └──refill──────────────────────┴──refill────────────────────┘
"""

from time import time
from typing import Optional

from agno.rate_limit.base import RateLimitExceeded, RateLimiter, RateLimitState
from agno.utils.log import logger


class TokenBucketRateLimiter(RateLimiter):
    """
    Token Bucket Rate Limiter FSA

    Example:
        # Allow 100 requests per minute
        limiter = TokenBucketRateLimiter(
            rate_limit_id="api_key_123",
            capacity=100,
            refill_rate=100/60,  # tokens per second
        )

        # Check if request is allowed
        if limiter.allow_request():
            # Process request
            pass
        else:
            retry_after = limiter.get_retry_after()
            print(f"Rate limited, retry after {retry_after}s")
    """

    rate_limit_id: str
    capacity: float  # Maximum tokens in bucket
    refill_rate: float  # Tokens added per second
    tokens: float = 0.0  # Current tokens in bucket
    last_refill_time: float = 0.0  # Last time bucket was refilled
    raise_on_limit: bool = False  # Whether to raise exception when limited

    def __init__(self, **data):
        super().__init__(**data)
        # Initialize bucket to full capacity
        if self.tokens == 0.0:
            self.tokens = self.capacity
        if self.last_refill_time == 0.0:
            self.last_refill_time = time()

        # Initialize metrics
        self.metrics.current_capacity = self.tokens
        self.metrics.max_capacity = self.capacity

    def allow_request(self, tokens: float = 1.0) -> bool:
        """
        Check if request is allowed and consume tokens

        Args:
            tokens: Number of tokens to consume (default 1.0)

        Returns:
            True if request allowed, False otherwise

        Raises:
            RateLimitExceeded: If rate limit exceeded and raise_on_limit=True
        """
        # Refill bucket based on time elapsed
        self._refill()

        # Check if enough tokens available
        if self.tokens >= tokens:
            # Consume tokens
            self.tokens -= tokens
            self.metrics.current_capacity = self.tokens
            self._update_metrics(allowed=True)
            self._update_state()

            logger.debug(
                f"TokenBucket[{self.rate_limit_id}]: Request allowed, "
                f"tokens remaining: {self.tokens:.2f}/{self.capacity}"
            )
            return True
        else:
            # Not enough tokens
            self._update_metrics(allowed=False)
            self.current_state = RateLimitState.LIMITED

            logger.warning(
                f"TokenBucket[{self.rate_limit_id}]: Rate limit exceeded, "
                f"tokens: {self.tokens:.2f}/{self.capacity}"
            )

            if self.raise_on_limit:
                raise RateLimitExceeded(
                    message=f"Token bucket rate limit exceeded for {self.rate_limit_id}",
                    retry_after=self.get_retry_after(),
                    current_state=self.current_state,
                )

            return False

    def _refill(self) -> None:
        """Refill bucket with tokens based on elapsed time"""
        now = time()
        time_elapsed = now - self.last_refill_time

        # Calculate tokens to add
        tokens_to_add = time_elapsed * self.refill_rate

        # Add tokens (capped at capacity)
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill_time = now

        # Update metrics
        self.metrics.current_capacity = self.tokens

    def get_retry_after(self) -> Optional[float]:
        """
        Calculate time until next request can be made

        Returns:
            Seconds until retry, or None if requests can proceed
        """
        self._refill()

        if self.tokens >= 1.0:
            return None

        # Calculate time needed to accumulate 1 token
        tokens_needed = 1.0 - self.tokens
        return tokens_needed / self.refill_rate if self.refill_rate > 0 else None

    def reset(self) -> None:
        """Reset the token bucket to full capacity"""
        self.tokens = self.capacity
        self.last_refill_time = time()
        self.current_state = RateLimitState.AVAILABLE
        self.metrics = type(self.metrics)()  # Reset metrics
        self.metrics.current_capacity = self.tokens
        self.metrics.max_capacity = self.capacity
        logger.debug(f"TokenBucket[{self.rate_limit_id}]: Reset to full capacity")

    def get_available_tokens(self) -> float:
        """Get current number of available tokens after refill"""
        self._refill()
        return self.tokens

    def set_capacity(self, new_capacity: float) -> None:
        """Dynamically adjust bucket capacity"""
        old_capacity = self.capacity
        self.capacity = new_capacity
        self.metrics.max_capacity = new_capacity

        # Adjust current tokens proportionally
        if old_capacity > 0:
            ratio = new_capacity / old_capacity
            self.tokens = min(new_capacity, self.tokens * ratio)
        else:
            self.tokens = new_capacity

        self.metrics.current_capacity = self.tokens
        logger.debug(
            f"TokenBucket[{self.rate_limit_id}]: Capacity adjusted "
            f"from {old_capacity} to {new_capacity}, tokens: {self.tokens:.2f}"
        )

    def set_refill_rate(self, new_rate: float) -> None:
        """Dynamically adjust refill rate"""
        old_rate = self.refill_rate
        self.refill_rate = new_rate
        logger.debug(
            f"TokenBucket[{self.rate_limit_id}]: Refill rate adjusted " f"from {old_rate} to {new_rate} tokens/sec"
        )
