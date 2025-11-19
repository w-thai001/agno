"""
Distributed Rate Limiter FSA (Redis-backed)

Implements rate limiting across multiple servers/processes using Redis as a shared state store.
Supports multiple algorithms: token bucket, sliding window, and fixed window.

FSA States:
- AVAILABLE: Under rate limit, requests can proceed
- WARNING: Approaching rate limit
- LIMITED: Rate limit reached
- RECOVERING: Capacity recovering
- ERROR: Redis connection error

State Transitions:
[AVAILABLE] ──consume tokens──> [WARNING] ──consume tokens──> [LIMITED]
     ↑                              ↑                              ↑
     └──refill/expire───────────────┴──refill/expire──────────────┘
     ↓
[ERROR] (Redis unavailable)
     ↓
[AVAILABLE] (fallback to local, or block)
"""

from enum import Enum
from time import time
from typing import Any, Dict, Optional

from pydantic import BaseModel

from agno.rate_limit.base import RateLimitExceeded, RateLimiter, RateLimitState
from agno.utils.log import logger


class DistributedAlgorithm(str, Enum):
    """Algorithm to use for distributed rate limiting"""

    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"


class FallbackStrategy(str, Enum):
    """Strategy when Redis is unavailable"""

    ALLOW_ALL = "allow_all"  # Allow all requests
    DENY_ALL = "deny_all"  # Deny all requests
    LOCAL_ONLY = "local_only"  # Fall back to local rate limiting (not distributed)


class DistributedRateLimiter(RateLimiter):
    """
    Distributed Rate Limiter FSA (Redis-backed)

    Example:
        import redis

        # Initialize Redis client
        redis_client = redis.Redis(host='localhost', port=6379, db=0)

        # Create distributed rate limiter
        limiter = DistributedRateLimiter(
            rate_limit_id="global_api",
            redis_client=redis_client,
            algorithm=DistributedAlgorithm.TOKEN_BUCKET,
            capacity=1000,
            refill_rate=1000/60,  # 1000 per minute
        )

        if limiter.allow_request():
            # Process request
            pass
        else:
            retry_after = limiter.get_retry_after()
            print(f"Rate limited, retry after {retry_after}s")
    """

    rate_limit_id: str
    redis_client: Optional[Any] = None  # Redis client instance
    algorithm: DistributedAlgorithm = DistributedAlgorithm.TOKEN_BUCKET
    fallback_strategy: FallbackStrategy = FallbackStrategy.LOCAL_ONLY
    raise_on_limit: bool = False

    # Token Bucket parameters
    capacity: Optional[float] = None
    refill_rate: Optional[float] = None

    # Sliding/Fixed Window parameters
    max_requests: Optional[int] = None
    window_size: Optional[float] = None

    # Redis key configuration
    redis_key_prefix: str = "agno:ratelimit"
    redis_key_ttl: int = 86400  # 24 hours

    # Fallback local limiter
    _local_limiter: Optional[RateLimiter] = None

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, **data):
        super().__init__(**data)

        # Validate algorithm-specific parameters
        if self.algorithm == DistributedAlgorithm.TOKEN_BUCKET:
            if self.capacity is None or self.refill_rate is None:
                raise ValueError("Token bucket requires 'capacity' and 'refill_rate' parameters")
        else:  # SLIDING_WINDOW or FIXED_WINDOW
            if self.max_requests is None or self.window_size is None:
                raise ValueError("Window algorithms require 'max_requests' and 'window_size' parameters")

        # Initialize local fallback limiter
        if self.fallback_strategy == FallbackStrategy.LOCAL_ONLY:
            self._initialize_local_limiter()

        # Initialize metrics
        if self.algorithm == DistributedAlgorithm.TOKEN_BUCKET:
            self.metrics.max_capacity = self.capacity or 0.0
        else:
            self.metrics.max_capacity = float(self.max_requests or 0)

    def _initialize_local_limiter(self) -> None:
        """Initialize local fallback rate limiter"""
        if self.algorithm == DistributedAlgorithm.TOKEN_BUCKET:
            from agno.rate_limit.token_bucket import TokenBucketRateLimiter

            self._local_limiter = TokenBucketRateLimiter(
                rate_limit_id=f"{self.rate_limit_id}_local",
                capacity=self.capacity or 100,
                refill_rate=self.refill_rate or 1.0,
            )
        elif self.algorithm == DistributedAlgorithm.SLIDING_WINDOW:
            from agno.rate_limit.sliding_window import SlidingWindowRateLimiter

            self._local_limiter = SlidingWindowRateLimiter(
                rate_limit_id=f"{self.rate_limit_id}_local",
                max_requests=self.max_requests or 100,
                window_size=self.window_size or 60,
            )
        else:  # FIXED_WINDOW
            from agno.rate_limit.fixed_window import FixedWindowRateLimiter

            self._local_limiter = FixedWindowRateLimiter(
                rate_limit_id=f"{self.rate_limit_id}_local",
                max_requests=self.max_requests or 100,
                window_size=self.window_size or 60,
            )

    def allow_request(self, tokens: float = 1.0) -> bool:
        """
        Check if request is allowed using distributed rate limiting

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if request allowed, False otherwise

        Raises:
            RateLimitExceeded: If rate limit exceeded and raise_on_limit=True
        """
        if self.redis_client is None:
            return self._fallback_allow_request(tokens)

        try:
            # Execute algorithm-specific logic
            if self.algorithm == DistributedAlgorithm.TOKEN_BUCKET:
                allowed = self._token_bucket_allow(tokens)
            elif self.algorithm == DistributedAlgorithm.SLIDING_WINDOW:
                allowed = self._sliding_window_allow(tokens)
            else:  # FIXED_WINDOW
                allowed = self._fixed_window_allow(tokens)

            self._update_metrics(allowed=allowed)

            if allowed:
                self._update_state()
                logger.debug(f"Distributed[{self.rate_limit_id}]: Request allowed")
                return True
            else:
                self.current_state = RateLimitState.LIMITED
                logger.warning(f"Distributed[{self.rate_limit_id}]: Rate limit exceeded")

                if self.raise_on_limit:
                    raise RateLimitExceeded(
                        message=f"Distributed rate limit exceeded for {self.rate_limit_id}",
                        retry_after=self.get_retry_after(),
                        current_state=self.current_state,
                    )

                return False

        except Exception as e:
            logger.error(f"Distributed[{self.rate_limit_id}]: Redis error: {e}")
            self.current_state = RateLimitState.ERROR
            return self._fallback_allow_request(tokens)

    def _token_bucket_allow(self, tokens: float) -> bool:
        """Token bucket algorithm using Redis + Lua script"""
        # Lua script for atomic token bucket operation
        lua_script = """
        local key = KEYS[1]
        local capacity = tonumber(ARGV[1])
        local refill_rate = tonumber(ARGV[2])
        local tokens_requested = tonumber(ARGV[3])
        local now = tonumber(ARGV[4])
        local ttl = tonumber(ARGV[5])

        -- Get current state
        local state = redis.call('HMGET', key, 'tokens', 'last_refill')
        local tokens = tonumber(state[1]) or capacity
        local last_refill = tonumber(state[2]) or now

        -- Refill tokens
        local time_elapsed = now - last_refill
        local tokens_to_add = time_elapsed * refill_rate
        tokens = math.min(capacity, tokens + tokens_to_add)

        -- Check if enough tokens
        if tokens >= tokens_requested then
            tokens = tokens - tokens_requested
            redis.call('HMSET', key, 'tokens', tokens, 'last_refill', now)
            redis.call('EXPIRE', key, ttl)
            return {1, tokens}  -- allowed, remaining tokens
        else
            redis.call('HMSET', key, 'tokens', tokens, 'last_refill', now)
            redis.call('EXPIRE', key, ttl)
            return {0, tokens}  -- denied, remaining tokens
        end
        """

        key = f"{self.redis_key_prefix}:tb:{self.rate_limit_id}"
        result = self.redis_client.eval(
            lua_script, 1, key, self.capacity, self.refill_rate, tokens, time(), self.redis_key_ttl
        )

        allowed = bool(result[0])
        self.metrics.current_capacity = float(result[1])
        return allowed

    def _sliding_window_allow(self, tokens: float) -> bool:
        """Sliding window algorithm using Redis sorted set"""
        key = f"{self.redis_key_prefix}:sw:{self.rate_limit_id}"
        now = time()
        window_start = now - (self.window_size or 60)

        # Remove expired entries
        self.redis_client.zremrangebyscore(key, 0, window_start)

        # Count current requests
        current_count = self.redis_client.zcard(key)

        if current_count + int(tokens) <= (self.max_requests or 100):
            # Add new request(s)
            for i in range(int(tokens)):
                self.redis_client.zadd(key, {f"{now}:{i}": now})

            self.redis_client.expire(key, self.redis_key_ttl)

            # Update metrics
            self.metrics.current_capacity = float((self.max_requests or 100) - current_count - int(tokens))
            return True
        else:
            self.metrics.current_capacity = float((self.max_requests or 100) - current_count)
            return False

    def _fixed_window_allow(self, tokens: float) -> bool:
        """Fixed window algorithm using Redis counter"""
        from math import floor

        # Calculate current window
        now = time()
        window_size = self.window_size or 60
        window_number = floor(now / window_size)
        key = f"{self.redis_key_prefix}:fw:{self.rate_limit_id}:{window_number}"

        # Increment counter
        current_count = self.redis_client.incr(key)

        # Set TTL on first request in window
        if current_count == 1:
            self.redis_client.expire(key, int(window_size) + 1)

        max_req = self.max_requests or 100

        if current_count <= max_req:
            self.metrics.current_capacity = float(max_req - current_count)
            return True
        else:
            # Decrement back since we exceeded
            self.redis_client.decr(key)
            self.metrics.current_capacity = 0.0
            return False

    def _fallback_allow_request(self, tokens: float) -> bool:
        """Handle request when Redis is unavailable"""
        if self.fallback_strategy == FallbackStrategy.ALLOW_ALL:
            logger.warning(f"Distributed[{self.rate_limit_id}]: Fallback ALLOW_ALL")
            return True
        elif self.fallback_strategy == FallbackStrategy.DENY_ALL:
            logger.warning(f"Distributed[{self.rate_limit_id}]: Fallback DENY_ALL")
            return False
        else:  # LOCAL_ONLY
            logger.warning(f"Distributed[{self.rate_limit_id}]: Fallback to local limiter")
            if self._local_limiter:
                return self._local_limiter.allow_request(tokens)
            return True

    def get_retry_after(self) -> Optional[float]:
        """Calculate time until next request can be made"""
        # This is algorithm-specific and would require querying Redis
        # For simplicity, return a default
        return 1.0

    def reset(self) -> None:
        """Reset the distributed rate limiter"""
        if self.redis_client is None:
            return

        try:
            # Delete all keys for this rate limiter
            pattern = f"{self.redis_key_prefix}:*:{self.rate_limit_id}*"
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)

            self.current_state = RateLimitState.AVAILABLE
            self.metrics = type(self.metrics)()

            logger.debug(f"Distributed[{self.rate_limit_id}]: Reset")
        except Exception as e:
            logger.error(f"Distributed[{self.rate_limit_id}]: Reset error: {e}")

    def get_distributed_stats(self) -> Dict[str, Any]:
        """Get statistics from Redis"""
        if self.redis_client is None:
            return {}

        try:
            if self.algorithm == DistributedAlgorithm.TOKEN_BUCKET:
                key = f"{self.redis_key_prefix}:tb:{self.rate_limit_id}"
                state = self.redis_client.hmget(key, "tokens", "last_refill")
                return {
                    "tokens": float(state[0]) if state[0] else self.capacity,
                    "last_refill": float(state[1]) if state[1] else time(),
                }
            elif self.algorithm == DistributedAlgorithm.SLIDING_WINDOW:
                key = f"{self.redis_key_prefix}:sw:{self.rate_limit_id}"
                count = self.redis_client.zcard(key)
                return {"current_count": count, "max_requests": self.max_requests}
            else:  # FIXED_WINDOW
                # Get current window key
                from math import floor

                now = time()
                window_size = self.window_size or 60
                window_number = floor(now / window_size)
                key = f"{self.redis_key_prefix}:fw:{self.rate_limit_id}:{window_number}"
                count = int(self.redis_client.get(key) or 0)
                return {"current_count": count, "max_requests": self.max_requests}
        except Exception as e:
            logger.error(f"Distributed[{self.rate_limit_id}]: Stats error: {e}")
            return {}
