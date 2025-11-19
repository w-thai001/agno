"""Token Bucket Rate Limiter - Simple FSA implementation with check, consume, refill"""

from enum import Enum
from threading import Lock
from time import monotonic
from typing import Dict, Optional, Tuple


class RateLimitState(Enum):
    """Rate limiter FSA states"""
    IDLE = "idle"
    THROTTLED = "throttled"
    REFILLING = "refilling"


class TokenBucket:
    """Thread-safe token bucket rate limiter with check, consume, and refill operations"""

    def __init__(self, capacity: float, refill_rate: float, initial_tokens: Optional[float] = None):
        if capacity <= 0 or refill_rate <= 0:
            raise ValueError("Capacity and refill rate must be positive")
        self._capacity = float(capacity)
        self._refill_rate = float(refill_rate)
        self._tokens = float(initial_tokens if initial_tokens is not None else capacity)
        self._last_refill_time = monotonic()
        self._lock = Lock()
        if self._tokens < 0 or self._tokens > self._capacity:
            raise ValueError("Initial tokens must be between 0 and capacity")

    @property
    def state(self) -> RateLimitState:
        """Get current FSA state"""
        with self._lock:
            self._refill()
            if self._tokens >= 1:
                return RateLimitState.IDLE
            return RateLimitState.REFILLING if self._refill_rate > 0 else RateLimitState.THROTTLED

    def available(self) -> float:
        """Get number of available tokens"""
        with self._lock:
            self._refill()
            return self._tokens

    def check(self, tokens: float = 1.0) -> bool:
        """Check if tokens are available without consuming"""
        if tokens <= 0:
            raise ValueError("Token count must be positive")
        with self._lock:
            self._refill()
            return self._tokens >= tokens

    def consume(self, tokens: float = 1.0) -> bool:
        """Attempt to consume tokens from the bucket"""
        if tokens <= 0:
            raise ValueError("Token count must be positive")
        with self._lock:
            self._refill()
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False

    def try_consume(self, tokens: float = 1.0) -> Tuple[bool, float]:
        """Try to consume tokens and return (success, wait_time_seconds)"""
        if tokens <= 0:
            raise ValueError("Token count must be positive")
        with self._lock:
            self._refill()
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True, 0.0
            needed = tokens - self._tokens
            return False, needed / self._refill_rate

    def refill(self, tokens: Optional[float] = None) -> float:
        """Manually refill tokens"""
        with self._lock:
            if tokens is not None:
                if tokens < 0:
                    raise ValueError("Token count cannot be negative")
                self._tokens = min(self._capacity, self._tokens + tokens)
            else:
                self._refill()
            return self._tokens

    def reset(self, tokens: Optional[float] = None) -> None:
        """Reset bucket to initial or specified state"""
        with self._lock:
            self._tokens = float(tokens if tokens is not None else self._capacity)
            self._last_refill_time = monotonic()
            if self._tokens < 0 or self._tokens > self._capacity:
                raise ValueError("Reset tokens must be between 0 and capacity")

    def _refill(self) -> None:
        """Internal refill based on elapsed time"""
        now = monotonic()
        elapsed = now - self._last_refill_time
        if elapsed > 0:
            self._tokens = min(self._capacity, self._tokens + elapsed * self._refill_rate)
            self._last_refill_time = now

    @property
    def capacity(self) -> float:
        return self._capacity

    @property
    def refill_rate(self) -> float:
        return self._refill_rate

    def __repr__(self) -> str:
        return f"TokenBucket(capacity={self._capacity}, refill_rate={self._refill_rate}, tokens={self.available():.2f})"


class RateLimiter:
    """Multi-key rate limiter with per-key token buckets (LRU eviction)"""

    def __init__(self, capacity: float, refill_rate: float, max_buckets: int = 10000):
        self._capacity = capacity
        self._refill_rate = refill_rate
        self._max_buckets = max_buckets
        self._buckets: Dict[str, TokenBucket] = {}
        self._lock = Lock()

    def _get_bucket(self, key: str) -> TokenBucket:
        """Get or create bucket for key"""
        if key not in self._buckets:
            if len(self._buckets) >= self._max_buckets:
                oldest_key = next(iter(self._buckets))
                del self._buckets[oldest_key]
            self._buckets[key] = TokenBucket(capacity=self._capacity, refill_rate=self._refill_rate)
        return self._buckets[key]

    def check(self, key: str, tokens: float = 1.0) -> bool:
        """Check if tokens are available for key"""
        with self._lock:
            bucket = self._get_bucket(key)
        return bucket.check(tokens)

    def consume(self, key: str, tokens: float = 1.0) -> bool:
        """Consume tokens for key"""
        with self._lock:
            bucket = self._get_bucket(key)
        return bucket.consume(tokens)

    def try_consume(self, key: str, tokens: float = 1.0) -> Tuple[bool, float]:
        """Try to consume tokens and get (success, wait_time_seconds)"""
        with self._lock:
            bucket = self._get_bucket(key)
        return bucket.try_consume(tokens)

    def available(self, key: str) -> float:
        """Get available tokens for key"""
        with self._lock:
            bucket = self._get_bucket(key)
        return bucket.available()

    def reset(self, key: str, tokens: Optional[float] = None) -> None:
        """Reset bucket for key"""
        with self._lock:
            bucket = self._get_bucket(key)
        bucket.reset(tokens)

    def clear(self) -> None:
        """Clear all buckets"""
        with self._lock:
            self._buckets.clear()

    def __repr__(self) -> str:
        return f"RateLimiter(capacity={self._capacity}, refill_rate={self._refill_rate}, buckets={len(self._buckets)})"
