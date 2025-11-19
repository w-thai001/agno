"""
Rate limiter implementation using token bucket algorithm.

Prevents overwhelming APIs with too many requests by controlling
the rate at which requests can be made.
"""

import time
from threading import Lock
from typing import Optional

from agno.utils.log import logger

from .models import RateLimitConfig


class RateLimiter:
    """
    Token bucket rate limiter.

    The token bucket algorithm allows for burst traffic while maintaining
    an average rate limit. Tokens are added to the bucket at a fixed rate,
    and each request consumes one token.
    """

    def __init__(self, endpoint_name: str, config: RateLimitConfig):
        """
        Initialize rate limiter.

        Args:
            endpoint_name: Name of the endpoint this rate limiter protects
            config: Rate limit configuration
        """
        self.endpoint_name = endpoint_name
        self.config = config
        self.tokens = float(config.burst_size)  # Start with full bucket
        self.last_update = time.time()
        self.lock = Lock()

        logger.debug(
            f"RateLimiter initialized for {endpoint_name}: "
            f"{config.requests_per_second} req/s, burst={config.burst_size}"
        )

    def acquire(self, tokens: int = 1, blocking: bool = True, timeout: Optional[float] = None) -> bool:
        """
        Acquire tokens from the bucket.

        Args:
            tokens: Number of tokens to acquire (default: 1)
            blocking: If True, wait until tokens are available
            timeout: Maximum time to wait in seconds (only if blocking=True)

        Returns:
            True if tokens were acquired, False otherwise

        Raises:
            TimeoutError: If blocking=True and timeout is reached
        """
        if not self.config.enabled:
            return True

        start_time = time.time()

        while True:
            with self.lock:
                self._refill_tokens()

                if self.tokens >= tokens:
                    self.tokens -= tokens
                    logger.debug(
                        f"RateLimiter for {self.endpoint_name}: "
                        f"Acquired {tokens} token(s), {self.tokens:.2f} remaining"
                    )
                    return True

                if not blocking:
                    logger.warning(
                        f"RateLimiter for {self.endpoint_name}: "
                        f"Rate limit hit, need {tokens} tokens but only {self.tokens:.2f} available"
                    )
                    return False

                # Calculate wait time for next token
                tokens_needed = tokens - self.tokens
                wait_time = tokens_needed / self.config.requests_per_second

            # Check timeout
            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed + wait_time > timeout:
                    raise TimeoutError(
                        f"RateLimiter timeout for {self.endpoint_name}: "
                        f"Could not acquire {tokens} tokens within {timeout}s"
                    )

            logger.debug(
                f"RateLimiter for {self.endpoint_name}: Waiting {wait_time:.2f}s for tokens"
            )
            time.sleep(wait_time)

    def _refill_tokens(self):
        """Refill tokens based on time elapsed since last update."""
        now = time.time()
        time_elapsed = now - self.last_update

        # Calculate tokens to add
        tokens_to_add = time_elapsed * self.config.requests_per_second

        # Cap at burst size
        self.tokens = min(self.tokens + tokens_to_add, float(self.config.burst_size))
        self.last_update = now

    def get_available_tokens(self) -> float:
        """Get the current number of available tokens."""
        with self.lock:
            self._refill_tokens()
            return self.tokens

    def reset(self):
        """Reset the rate limiter to full capacity."""
        with self.lock:
            self.tokens = float(self.config.burst_size)
            self.last_update = time.time()
            logger.info(f"RateLimiter for {self.endpoint_name}: Reset to full capacity")

    def get_metrics(self) -> dict:
        """Get rate limiter metrics."""
        with self.lock:
            self._refill_tokens()
            return {
                "endpoint_name": self.endpoint_name,
                "available_tokens": self.tokens,
                "max_tokens": self.config.burst_size,
                "tokens_per_second": self.config.requests_per_second,
                "utilization_percent": (
                    (1 - (self.tokens / self.config.burst_size)) * 100
                    if self.config.burst_size > 0
                    else 0
                ),
            }


class GlobalRateLimiter:
    """
    Global rate limiter that manages rate limits across all endpoints.

    This is useful when you have an overall API quota that applies
    to all endpoints combined.
    """

    def __init__(self, config: RateLimitConfig):
        """
        Initialize global rate limiter.

        Args:
            config: Rate limit configuration
        """
        self.limiter = RateLimiter("global", config)
        logger.info(
            f"GlobalRateLimiter initialized: {config.requests_per_second} req/s, "
            f"burst={config.burst_size}"
        )

    def acquire(self, tokens: int = 1, blocking: bool = True, timeout: Optional[float] = None) -> bool:
        """Acquire tokens from the global bucket."""
        return self.limiter.acquire(tokens=tokens, blocking=blocking, timeout=timeout)

    def get_available_tokens(self) -> float:
        """Get available tokens."""
        return self.limiter.get_available_tokens()

    def reset(self):
        """Reset the global rate limiter."""
        self.limiter.reset()

    def get_metrics(self) -> dict:
        """Get global rate limiter metrics."""
        return self.limiter.get_metrics()
