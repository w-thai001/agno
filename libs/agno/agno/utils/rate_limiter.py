"""
Token Bucket Rate Limiter with Redis Backend

This module provides a production-ready distributed rate limiting implementation
using the token bucket algorithm with Redis as the backend storage.

Features:
- Token bucket algorithm with refill rate
- Redis backend for distributed rate limiting
- Sliding window for accurate rate tracking
- Support for burst allowances
- Thread-safe and distributed-safe
"""

import time
from dataclasses import dataclass
from typing import Optional, Tuple

try:
    import redis
    from redis import Redis, ConnectionPool
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


@dataclass
class RateLimitResult:
    """Result of a rate limit check.

    Attributes:
        allow_request: Whether the request should be allowed
        remaining_tokens: Number of tokens remaining in the bucket
        retry_after_seconds: Time to wait before retrying (0 if allowed)
    """
    allow_request: bool
    remaining_tokens: int
    retry_after_seconds: float


class TokenBucketRateLimiter:
    """
    Distributed token bucket rate limiter using Redis.

    The token bucket algorithm allows for burst traffic while maintaining
    an average rate limit. Tokens are added to the bucket at a constant rate,
    and requests consume tokens. If no tokens are available, the request is denied.

    This implementation uses Redis with Lua scripts for atomic operations,
    making it suitable for distributed systems.

    Args:
        redis_client: Redis client instance or connection URL
        key_prefix: Prefix for Redis keys (default: "rate_limit")
        default_max_requests: Default maximum requests (can be overridden per client)
        default_time_window_seconds: Default time window in seconds (can be overridden per client)

    Example:
        >>> limiter = TokenBucketRateLimiter(
        ...     redis_client="redis://localhost:6379/0",
        ...     default_max_requests=100,
        ...     default_time_window_seconds=60
        ... )
        >>> result = limiter.allow_request("user_123")
        >>> if result.allow_request:
        ...     print(f"Request allowed. Remaining: {result.remaining_tokens}")
        ... else:
        ...     print(f"Rate limited. Retry after: {result.retry_after_seconds}s")
    """

    # Lua script for atomic token bucket check and update
    # This ensures thread-safety and distributed consistency
    LUA_SCRIPT = """
    local key = KEYS[1]
    local max_tokens = tonumber(ARGV[1])
    local refill_rate = tonumber(ARGV[2])
    local current_time = tonumber(ARGV[3])
    local requested_tokens = tonumber(ARGV[4])

    -- Get current bucket state
    local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
    local tokens = tonumber(bucket[1])
    local last_refill = tonumber(bucket[2])

    -- Initialize bucket if it doesn't exist
    if tokens == nil then
        tokens = max_tokens
        last_refill = current_time
    end

    -- Calculate tokens to add based on time elapsed
    local time_elapsed = current_time - last_refill
    local tokens_to_add = time_elapsed * refill_rate

    -- Refill tokens (capped at max_tokens)
    tokens = math.min(max_tokens, tokens + tokens_to_add)

    -- Check if we have enough tokens
    local allowed = 0
    local retry_after = 0

    if tokens >= requested_tokens then
        -- Consume tokens
        tokens = tokens - requested_tokens
        allowed = 1
        last_refill = current_time
    else
        -- Calculate time until enough tokens are available
        local tokens_needed = requested_tokens - tokens
        retry_after = tokens_needed / refill_rate
    end

    -- Update bucket state
    redis.call('HSET', key, 'tokens', tokens, 'last_refill', last_refill)

    -- Set expiration to prevent memory leaks (2x time window)
    local ttl = math.ceil((max_tokens / refill_rate) * 2)
    redis.call('EXPIRE', key, ttl)

    -- Return: allowed (0/1), tokens remaining, retry_after
    return {allowed, math.floor(tokens), retry_after}
    """

    def __init__(
        self,
        redis_client: Optional[str | Redis] = None,
        key_prefix: str = "rate_limit",
        default_max_requests: int = 100,
        default_time_window_seconds: int = 60,
    ):
        """Initialize the rate limiter.

        Args:
            redis_client: Redis client or connection URL. If None, will try localhost.
            key_prefix: Prefix for all Redis keys
            default_max_requests: Default maximum requests allowed
            default_time_window_seconds: Default time window in seconds

        Raises:
            ImportError: If redis-py is not installed
            redis.ConnectionError: If cannot connect to Redis
        """
        if not REDIS_AVAILABLE:
            raise ImportError(
                "redis-py is required for TokenBucketRateLimiter. "
                "Install it with: pip install redis"
            )

        # Initialize Redis client
        if redis_client is None:
            redis_client = "redis://localhost:6379/0"

        if isinstance(redis_client, str):
            # Parse connection URL
            self._redis: Redis = redis.from_url(redis_client, decode_responses=True)
        else:
            self._redis = redis_client

        self.key_prefix = key_prefix
        self.default_max_requests = default_max_requests
        self.default_time_window_seconds = default_time_window_seconds

        # Register Lua script
        try:
            self._script_sha = self._redis.script_load(self.LUA_SCRIPT)
        except redis.RedisError as e:
            raise redis.ConnectionError(f"Failed to connect to Redis: {e}")

    def _get_key(self, client_id: str) -> str:
        """Generate Redis key for a client."""
        return f"{self.key_prefix}:{client_id}"

    def allow_request(
        self,
        client_id: str,
        max_requests: Optional[int] = None,
        time_window_seconds: Optional[int] = None,
        tokens_requested: int = 1,
    ) -> RateLimitResult:
        """
        Check if a request should be allowed for the given client.

        Args:
            client_id: Unique identifier for the client (e.g., user_id, IP address)
            max_requests: Maximum requests allowed (overrides default if provided)
            time_window_seconds: Time window in seconds (overrides default if provided)
            tokens_requested: Number of tokens to consume (default: 1)

        Returns:
            RateLimitResult with allow_request, remaining_tokens, and retry_after_seconds

        Example:
            >>> result = limiter.allow_request("user_123", max_requests=10, time_window_seconds=60)
            >>> if not result.allow_request:
            ...     print(f"Rate limited! Retry after {result.retry_after_seconds:.2f} seconds")
        """
        # Use defaults if not provided
        max_requests = max_requests or self.default_max_requests
        time_window_seconds = time_window_seconds or self.default_time_window_seconds

        # Calculate refill rate (tokens per second)
        refill_rate = max_requests / time_window_seconds

        # Get current time
        current_time = time.time()

        # Execute Lua script
        key = self._get_key(client_id)

        try:
            result = self._redis.evalsha(
                self._script_sha,
                1,  # Number of keys
                key,
                max_requests,
                refill_rate,
                current_time,
                tokens_requested,
            )

            allowed, remaining_tokens, retry_after = result

            return RateLimitResult(
                allow_request=bool(allowed),
                remaining_tokens=int(remaining_tokens),
                retry_after_seconds=float(retry_after),
            )

        except redis.exceptions.NoScriptError:
            # Script not found, reload it
            self._script_sha = self._redis.script_load(self.LUA_SCRIPT)
            return self.allow_request(client_id, max_requests, time_window_seconds, tokens_requested)

        except redis.RedisError as e:
            # On Redis errors, fail open (allow the request) to prevent service disruption
            # In production, you might want to log this error
            return RateLimitResult(
                allow_request=True,
                remaining_tokens=max_requests,
                retry_after_seconds=0.0,
            )

    def reset_client(self, client_id: str) -> bool:
        """
        Reset the rate limit for a specific client.

        Args:
            client_id: Client identifier to reset

        Returns:
            True if the client was reset, False if it didn't exist

        Example:
            >>> limiter.reset_client("user_123")
            True
        """
        key = self._get_key(client_id)
        try:
            deleted = self._redis.delete(key)
            return deleted > 0
        except redis.RedisError:
            return False

    def get_client_info(self, client_id: str) -> Optional[Tuple[float, float]]:
        """
        Get current token count and last refill time for a client.

        Args:
            client_id: Client identifier

        Returns:
            Tuple of (tokens, last_refill_timestamp) or None if client doesn't exist

        Example:
            >>> info = limiter.get_client_info("user_123")
            >>> if info:
            ...     tokens, last_refill = info
            ...     print(f"Tokens: {tokens}, Last refill: {last_refill}")
        """
        key = self._get_key(client_id)
        try:
            result = self._redis.hmget(key, "tokens", "last_refill")
            if result[0] is None:
                return None
            return (float(result[0]), float(result[1]))
        except redis.RedisError:
            return None

    def close(self):
        """Close the Redis connection."""
        if hasattr(self._redis, "close"):
            self._redis.close()

    def __enter__(self):
        """Context manager support."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager support."""
        self.close()


class SlidingWindowRateLimiter:
    """
    Sliding window rate limiter using Redis.

    This implementation uses a sliding window log approach, which provides
    more accurate rate limiting than fixed windows but uses more memory.
    Each request is logged with its timestamp, and old requests are pruned.

    Args:
        redis_client: Redis client instance or connection URL
        key_prefix: Prefix for Redis keys (default: "sliding_window")
        default_max_requests: Default maximum requests per window
        default_time_window_seconds: Default time window in seconds

    Example:
        >>> limiter = SlidingWindowRateLimiter(
        ...     redis_client="redis://localhost:6379/0",
        ...     default_max_requests=100,
        ...     default_time_window_seconds=60
        ... )
        >>> result = limiter.allow_request("user_456")
    """

    # Lua script for atomic sliding window check
    LUA_SCRIPT = """
    local key = KEYS[1]
    local max_requests = tonumber(ARGV[1])
    local window_start = tonumber(ARGV[2])
    local current_time = tonumber(ARGV[3])
    local ttl = tonumber(ARGV[4])

    -- Remove old entries outside the window
    redis.call('ZREMRANGEBYSCORE', key, '-inf', window_start)

    -- Count requests in current window
    local request_count = redis.call('ZCARD', key)

    -- Check if we're under the limit
    local allowed = 0
    local retry_after = 0

    if request_count < max_requests then
        -- Add current request
        redis.call('ZADD', key, current_time, current_time)
        allowed = 1
        request_count = request_count + 1
    else
        -- Get the oldest request in the window
        local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
        if #oldest > 0 then
            retry_after = tonumber(oldest[2]) - window_start
        end
    end

    -- Set expiration
    redis.call('EXPIRE', key, ttl)

    -- Return: allowed (0/1), remaining requests, retry_after
    local remaining = max_requests - request_count
    return {allowed, math.max(0, remaining), retry_after}
    """

    def __init__(
        self,
        redis_client: Optional[str | Redis] = None,
        key_prefix: str = "sliding_window",
        default_max_requests: int = 100,
        default_time_window_seconds: int = 60,
    ):
        """Initialize the sliding window rate limiter."""
        if not REDIS_AVAILABLE:
            raise ImportError(
                "redis-py is required for SlidingWindowRateLimiter. "
                "Install it with: pip install redis"
            )

        if redis_client is None:
            redis_client = "redis://localhost:6379/0"

        if isinstance(redis_client, str):
            self._redis: Redis = redis.from_url(redis_client, decode_responses=True)
        else:
            self._redis = redis_client

        self.key_prefix = key_prefix
        self.default_max_requests = default_max_requests
        self.default_time_window_seconds = default_time_window_seconds

        try:
            self._script_sha = self._redis.script_load(self.LUA_SCRIPT)
        except redis.RedisError as e:
            raise redis.ConnectionError(f"Failed to connect to Redis: {e}")

    def _get_key(self, client_id: str) -> str:
        """Generate Redis key for a client."""
        return f"{self.key_prefix}:{client_id}"

    def allow_request(
        self,
        client_id: str,
        max_requests: Optional[int] = None,
        time_window_seconds: Optional[int] = None,
    ) -> RateLimitResult:
        """
        Check if a request should be allowed using sliding window.

        Args:
            client_id: Unique identifier for the client
            max_requests: Maximum requests allowed (overrides default)
            time_window_seconds: Time window in seconds (overrides default)

        Returns:
            RateLimitResult with allow_request, remaining_tokens, and retry_after_seconds
        """
        max_requests = max_requests or self.default_max_requests
        time_window_seconds = time_window_seconds or self.default_time_window_seconds

        current_time = time.time()
        window_start = current_time - time_window_seconds
        ttl = time_window_seconds * 2  # Keep data for 2x window

        key = self._get_key(client_id)

        try:
            result = self._redis.evalsha(
                self._script_sha,
                1,
                key,
                max_requests,
                window_start,
                current_time,
                ttl,
            )

            allowed, remaining, retry_after = result

            return RateLimitResult(
                allow_request=bool(allowed),
                remaining_tokens=int(remaining),
                retry_after_seconds=float(retry_after),
            )

        except redis.exceptions.NoScriptError:
            self._script_sha = self._redis.script_load(self.LUA_SCRIPT)
            return self.allow_request(client_id, max_requests, time_window_seconds)

        except redis.RedisError:
            # Fail open on Redis errors
            return RateLimitResult(
                allow_request=True,
                remaining_tokens=max_requests,
                retry_after_seconds=0.0,
            )

    def reset_client(self, client_id: str) -> bool:
        """Reset the rate limit for a specific client."""
        key = self._get_key(client_id)
        try:
            deleted = self._redis.delete(key)
            return deleted > 0
        except redis.RedisError:
            return False

    def close(self):
        """Close the Redis connection."""
        if hasattr(self._redis, "close"):
            self._redis.close()

    def __enter__(self):
        """Context manager support."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager support."""
        self.close()
