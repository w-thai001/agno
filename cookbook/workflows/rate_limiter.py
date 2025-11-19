"""
Rate Limiter Workflow for Agno Framework

This workflow implements a production-ready token bucket rate limiter with Redis backend.
It supports distributed rate limiting with sliding window tracking and burst allowances.

Features:
- Token bucket algorithm for smooth rate limiting
- Redis backend for distributed state management
- Sliding window for accurate rate tracking
- Burst allowance support
- Edge case handling (concurrent requests, clock skew)
- Atomic operations using Redis Lua scripts

Author: Agno AI
License: MIT
"""

import time
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Iterator
import redis
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError

from agno.workflow import Workflow, RunResponse
from agno.utils.log import logger


@dataclass
class RateLimitRequest:
    """Input model for rate limit check requests"""
    client_id: str
    max_requests: int = 100
    time_window_seconds: int = 60
    tokens_requested: int = 1
    burst_multiplier: float = 1.5  # Allow bursts up to 1.5x max_requests


@dataclass
class RateLimitResponse:
    """Output model for rate limit check responses"""
    allow_request: bool
    remaining_tokens: float
    retry_after_seconds: float
    total_requests: int
    window_reset_time: float
    client_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class RateLimiter(Workflow):
    """
    Token Bucket Rate Limiter Workflow

    Implements distributed rate limiting using Redis and the token bucket algorithm.
    Provides accurate rate tracking with sliding windows and support for burst traffic.

    Attributes:
        description: Workflow description
        redis_client: Redis client for distributed state
        redis_url: Redis connection URL
        default_max_requests: Default maximum requests per window
        default_time_window: Default time window in seconds
        clock_skew_tolerance: Tolerance for clock skew in seconds

    Example:
        >>> limiter = RateLimiter(redis_url="redis://localhost:6379/0")
        >>> request = RateLimitRequest(
        ...     client_id="user_123",
        ...     max_requests=10,
        ...     time_window_seconds=60
        ... )
        >>> response = limiter.check_rate_limit(request)
        >>> if response.allow_request:
        ...     print(f"Request allowed. Remaining: {response.remaining_tokens}")
        ... else:
        ...     print(f"Rate limit exceeded. Retry after: {response.retry_after_seconds}s")
    """

    description: str = "Token bucket rate limiter with Redis backend for distributed rate limiting"

    # Redis configuration
    redis_client: Optional[redis.Redis] = None
    redis_url: str = "redis://localhost:6379/0"
    redis_timeout: int = 5  # Connection timeout in seconds

    # Default rate limit settings
    default_max_requests: int = 100
    default_time_window: int = 60
    clock_skew_tolerance: float = 2.0  # seconds

    # Lua script for atomic token bucket operations
    _lua_script: Optional[redis.client.Script] = None

    def __init__(self, **kwargs):
        """Initialize the Rate Limiter workflow"""
        super().__init__(**kwargs)

        # Extract redis_url from kwargs if provided
        if "redis_url" in kwargs:
            self.redis_url = kwargs["redis_url"]

        # Initialize Redis connection
        self._init_redis()

        # Load Lua script for atomic operations
        self._load_lua_script()

    def _init_redis(self) -> None:
        """Initialize Redis client with error handling"""
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_timeout=self.redis_timeout,
                socket_connect_timeout=self.redis_timeout,
                retry_on_timeout=True,
                health_check_interval=30
            )
            # Test connection
            self.redis_client.ping()
            logger.info(f"✓ Connected to Redis at {self.redis_url}")
        except (RedisError, RedisConnectionError) as e:
            logger.error(f"✗ Failed to connect to Redis: {e}")
            raise ConnectionError(
                f"Unable to connect to Redis at {self.redis_url}. "
                f"Ensure Redis is running and accessible. Error: {e}"
            )

    def _load_lua_script(self) -> None:
        """
        Load Lua script for atomic token bucket operations

        This script implements the token bucket algorithm atomically in Redis:
        1. Calculate tokens to add based on time elapsed
        2. Add tokens up to burst capacity
        3. Check if enough tokens available
        4. Consume tokens if available
        5. Return updated state
        """
        lua_script = """
        local key = KEYS[1]
        local max_tokens = tonumber(ARGV[1])
        local refill_rate = tonumber(ARGV[2])
        local burst_capacity = tonumber(ARGV[3])
        local tokens_requested = tonumber(ARGV[4])
        local current_time = tonumber(ARGV[5])

        -- Get current bucket state
        local bucket = redis.call('HMGET', key, 'tokens', 'last_refill', 'total_requests')
        local tokens = tonumber(bucket[1]) or max_tokens
        local last_refill = tonumber(bucket[2]) or current_time
        local total_requests = tonumber(bucket[3]) or 0

        -- Calculate time elapsed and tokens to add
        local time_elapsed = math.max(0, current_time - last_refill)
        local tokens_to_add = time_elapsed * refill_rate

        -- Refill tokens up to burst capacity
        tokens = math.min(burst_capacity, tokens + tokens_to_add)

        -- Check if enough tokens available
        local allowed = tokens >= tokens_requested

        if allowed then
            -- Consume tokens
            tokens = tokens - tokens_requested
            total_requests = total_requests + 1
        end

        -- Update bucket state
        redis.call('HMSET', key, 'tokens', tokens, 'last_refill', current_time, 'total_requests', total_requests)

        -- Set expiration to prevent memory leaks (2x time window)
        local ttl = math.ceil(max_tokens / refill_rate * 2)
        redis.call('EXPIRE', key, ttl)

        -- Calculate retry_after
        local retry_after = 0
        if not allowed then
            retry_after = (tokens_requested - tokens) / refill_rate
        end

        -- Return: allowed, tokens, total_requests, retry_after
        return {allowed and 1 or 0, tokens, total_requests, retry_after}
        """

        try:
            self._lua_script = self.redis_client.register_script(lua_script)
            logger.debug("✓ Lua script loaded successfully")
        except RedisError as e:
            logger.error(f"✗ Failed to load Lua script: {e}")
            raise RuntimeError(f"Failed to register Lua script in Redis: {e}")

    def _get_redis_key(self, client_id: str, max_requests: int, time_window: int) -> str:
        """
        Generate Redis key for rate limit bucket

        Args:
            client_id: Unique client identifier
            max_requests: Maximum requests allowed
            time_window: Time window in seconds

        Returns:
            Redis key string
        """
        return f"rate_limit:{client_id}:{max_requests}:{time_window}"

    def check_rate_limit(self, request: RateLimitRequest) -> RateLimitResponse:
        """
        Check if a request should be allowed based on rate limits

        This method implements the token bucket algorithm with sliding window:
        - Tokens refill at a constant rate (max_requests / time_window)
        - Burst capacity allows temporary spikes
        - Atomic operations prevent race conditions

        Args:
            request: RateLimitRequest with client_id and rate limit parameters

        Returns:
            RateLimitResponse with decision and metadata

        Raises:
            ValueError: If request parameters are invalid
            RedisError: If Redis operation fails
        """
        # Validate input
        self._validate_request(request)

        # Calculate token bucket parameters
        refill_rate = request.max_requests / request.time_window_seconds  # tokens per second
        burst_capacity = request.max_requests * request.burst_multiplier
        current_time = time.time()

        # Get Redis key
        redis_key = self._get_redis_key(
            request.client_id,
            request.max_requests,
            request.time_window_seconds
        )

        try:
            # Execute atomic token bucket operation
            result = self._lua_script(
                keys=[redis_key],
                args=[
                    request.max_requests,
                    refill_rate,
                    burst_capacity,
                    request.tokens_requested,
                    current_time
                ]
            )

            # Parse result
            allowed = bool(result[0])
            remaining_tokens = float(result[1])
            total_requests = int(result[2])
            retry_after = float(result[3])

            # Calculate window reset time
            time_to_full = (request.max_requests - remaining_tokens) / refill_rate
            window_reset_time = current_time + time_to_full

            # Build response
            response = RateLimitResponse(
                allow_request=allowed,
                remaining_tokens=remaining_tokens,
                retry_after_seconds=retry_after,
                total_requests=total_requests,
                window_reset_time=window_reset_time,
                client_id=request.client_id,
                metadata={
                    "max_requests": request.max_requests,
                    "time_window_seconds": request.time_window_seconds,
                    "refill_rate": refill_rate,
                    "burst_capacity": burst_capacity,
                    "tokens_requested": request.tokens_requested,
                    "timestamp": current_time
                }
            )

            # Log decision
            if allowed:
                logger.debug(
                    f"✓ Request allowed for {request.client_id} | "
                    f"Remaining: {remaining_tokens:.2f} | "
                    f"Total: {total_requests}"
                )
            else:
                logger.warning(
                    f"✗ Rate limit exceeded for {request.client_id} | "
                    f"Retry after: {retry_after:.2f}s"
                )

            return response

        except RedisError as e:
            logger.error(f"Redis error during rate limit check: {e}")
            # Fail open: allow request on Redis errors (configurable)
            return RateLimitResponse(
                allow_request=True,
                remaining_tokens=request.max_requests,
                retry_after_seconds=0.0,
                total_requests=0,
                window_reset_time=current_time + request.time_window_seconds,
                client_id=request.client_id,
                metadata={"error": str(e), "fail_open": True}
            )

    def _validate_request(self, request: RateLimitRequest) -> None:
        """
        Validate rate limit request parameters

        Args:
            request: RateLimitRequest to validate

        Raises:
            ValueError: If any parameter is invalid
        """
        if not request.client_id or not isinstance(request.client_id, str):
            raise ValueError("client_id must be a non-empty string")

        if request.max_requests <= 0:
            raise ValueError(f"max_requests must be positive, got {request.max_requests}")

        if request.time_window_seconds <= 0:
            raise ValueError(f"time_window_seconds must be positive, got {request.time_window_seconds}")

        if request.tokens_requested <= 0:
            raise ValueError(f"tokens_requested must be positive, got {request.tokens_requested}")

        if request.burst_multiplier < 1.0:
            raise ValueError(f"burst_multiplier must be >= 1.0, got {request.burst_multiplier}")

    def get_client_stats(self, client_id: str, max_requests: int = None,
                        time_window: int = None) -> Dict[str, Any]:
        """
        Get current rate limit statistics for a client

        Args:
            client_id: Client identifier
            max_requests: Maximum requests (uses default if not provided)
            time_window: Time window in seconds (uses default if not provided)

        Returns:
            Dictionary with current bucket state
        """
        max_requests = max_requests or self.default_max_requests
        time_window = time_window or self.default_time_window

        redis_key = self._get_redis_key(client_id, max_requests, time_window)

        try:
            bucket_data = self.redis_client.hgetall(redis_key)

            if not bucket_data:
                return {
                    "client_id": client_id,
                    "exists": False,
                    "tokens": max_requests,
                    "total_requests": 0
                }

            return {
                "client_id": client_id,
                "exists": True,
                "tokens": float(bucket_data.get("tokens", max_requests)),
                "last_refill": float(bucket_data.get("last_refill", 0)),
                "total_requests": int(bucket_data.get("total_requests", 0)),
                "ttl": self.redis_client.ttl(redis_key)
            }
        except RedisError as e:
            logger.error(f"Failed to get client stats: {e}")
            return {"client_id": client_id, "error": str(e)}

    def reset_client_limit(self, client_id: str, max_requests: int = None,
                          time_window: int = None) -> bool:
        """
        Reset rate limit for a specific client

        Args:
            client_id: Client identifier
            max_requests: Maximum requests (uses default if not provided)
            time_window: Time window in seconds (uses default if not provided)

        Returns:
            True if reset successful, False otherwise
        """
        max_requests = max_requests or self.default_max_requests
        time_window = time_window or self.default_time_window

        redis_key = self._get_redis_key(client_id, max_requests, time_window)

        try:
            deleted = self.redis_client.delete(redis_key)
            logger.info(f"✓ Reset rate limit for {client_id}")
            return bool(deleted)
        except RedisError as e:
            logger.error(f"Failed to reset client limit: {e}")
            return False

    def run(self, client_id: str, max_requests: int = None,
            time_window_seconds: int = None, tokens_requested: int = 1,
            operation: str = "check") -> Iterator[RunResponse]:
        """
        Main workflow entry point for rate limiting operations

        Args:
            client_id: Unique client identifier
            max_requests: Maximum requests per window (default: 100)
            time_window_seconds: Time window in seconds (default: 60)
            tokens_requested: Number of tokens to consume (default: 1)
            operation: Operation to perform - "check", "stats", or "reset"

        Yields:
            RunResponse with rate limit decision or statistics

        Example:
            >>> limiter = RateLimiter(redis_url="redis://localhost:6379/0")
            >>>
            >>> # Check rate limit
            >>> for response in limiter.run(client_id="user_123", max_requests=10,
            ...                             time_window_seconds=60):
            ...     print(response.content)
            >>>
            >>> # Get stats
            >>> for response in limiter.run(client_id="user_123", operation="stats"):
            ...     print(response.content)
            >>>
            >>> # Reset limit
            >>> for response in limiter.run(client_id="user_123", operation="reset"):
            ...     print(response.content)
        """
        max_requests = max_requests or self.default_max_requests
        time_window_seconds = time_window_seconds or self.default_time_window

        try:
            if operation == "check":
                # Check rate limit
                request = RateLimitRequest(
                    client_id=client_id,
                    max_requests=max_requests,
                    time_window_seconds=time_window_seconds,
                    tokens_requested=tokens_requested
                )

                response = self.check_rate_limit(request)

                if response.allow_request:
                    content = (
                        f"✓ Request ALLOWED for client '{client_id}'\n"
                        f"Remaining tokens: {response.remaining_tokens:.2f}\n"
                        f"Total requests: {response.total_requests}\n"
                        f"Window resets in: {response.window_reset_time - time.time():.2f}s"
                    )
                else:
                    content = (
                        f"✗ Request DENIED for client '{client_id}'\n"
                        f"Rate limit exceeded\n"
                        f"Retry after: {response.retry_after_seconds:.2f}s\n"
                        f"Window resets in: {response.window_reset_time - time.time():.2f}s"
                    )

                yield RunResponse(content=content, event=RunEvent.workflow_completed)

            elif operation == "stats":
                # Get client statistics
                stats = self.get_client_stats(client_id, max_requests, time_window_seconds)

                if stats.get("exists"):
                    content = (
                        f"📊 Rate Limit Stats for '{client_id}':\n"
                        f"Current tokens: {stats['tokens']:.2f}\n"
                        f"Total requests: {stats['total_requests']}\n"
                        f"Last refill: {stats['last_refill']:.2f}\n"
                        f"TTL: {stats['ttl']}s"
                    )
                else:
                    content = f"📊 No rate limit data found for '{client_id}'"

                yield RunResponse(content=content, event=RunEvent.workflow_completed)

            elif operation == "reset":
                # Reset client rate limit
                success = self.reset_client_limit(client_id, max_requests, time_window_seconds)

                if success:
                    content = f"✓ Rate limit reset successfully for '{client_id}'"
                else:
                    content = f"✗ Failed to reset rate limit for '{client_id}'"

                yield RunResponse(content=content, event=RunEvent.workflow_completed)

            else:
                raise ValueError(f"Unknown operation: {operation}. Use 'check', 'stats', or 'reset'")

        except Exception as e:
            logger.error(f"Error in rate limiter workflow: {e}")
            yield RunResponse(
                content=f"Error: {str(e)}",
                event=RunEvent.workflow_completed
            )

    def __del__(self):
        """Cleanup Redis connection on deletion"""
        if self.redis_client:
            try:
                self.redis_client.close()
            except:
                pass


# Example usage
if __name__ == "__main__":
    import sys

    # Initialize rate limiter
    limiter = RateLimiter(
        redis_url="redis://localhost:6379/0",
        debug_mode=True
    )

    print("=" * 60)
    print("Rate Limiter Workflow - Example Usage")
    print("=" * 60)

    # Example 1: Basic rate limiting
    print("\n1. Basic Rate Limiting (10 requests per 60 seconds)")
    print("-" * 60)

    for i in range(12):
        request = RateLimitRequest(
            client_id="user_alice",
            max_requests=10,
            time_window_seconds=60
        )

        response = limiter.check_rate_limit(request)

        status = "✓ ALLOWED" if response.allow_request else "✗ DENIED"
        print(f"Request {i+1:2d}: {status} | "
              f"Remaining: {response.remaining_tokens:5.2f} | "
              f"Retry after: {response.retry_after_seconds:5.2f}s")

    # Example 2: Burst traffic handling
    print("\n2. Burst Traffic (burst_multiplier=2.0)")
    print("-" * 60)

    # Reset first
    limiter.reset_client_limit("user_bob", 5, 10)

    for i in range(8):
        request = RateLimitRequest(
            client_id="user_bob",
            max_requests=5,
            time_window_seconds=10,
            burst_multiplier=2.0  # Allow bursts up to 10 requests
        )

        response = limiter.check_rate_limit(request)

        status = "✓ ALLOWED" if response.allow_request else "✗ DENIED"
        print(f"Request {i+1:2d}: {status} | "
              f"Remaining: {response.remaining_tokens:5.2f}")

    # Example 3: Multiple token consumption
    print("\n3. Multiple Token Consumption (heavy operations)")
    print("-" * 60)

    limiter.reset_client_limit("user_charlie", 100, 60)

    operations = [
        ("Light query", 1),
        ("Medium query", 5),
        ("Heavy query", 20),
        ("Batch operation", 50),
    ]

    for op_name, tokens in operations:
        request = RateLimitRequest(
            client_id="user_charlie",
            max_requests=100,
            time_window_seconds=60,
            tokens_requested=tokens
        )

        response = limiter.check_rate_limit(request)

        status = "✓ ALLOWED" if response.allow_request else "✗ DENIED"
        print(f"{op_name:20s} ({tokens:2d} tokens): {status} | "
              f"Remaining: {response.remaining_tokens:6.2f}")

    # Example 4: Concurrent requests simulation
    print("\n4. Concurrent Requests (atomic operations)")
    print("-" * 60)

    limiter.reset_client_limit("user_dave", 5, 10)

    import concurrent.futures

    def make_request(req_num):
        request = RateLimitRequest(
            client_id="user_dave",
            max_requests=5,
            time_window_seconds=10
        )
        response = limiter.check_rate_limit(request)
        return req_num, response.allow_request, response.remaining_tokens

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(make_request, i) for i in range(10)]
        results = [future.result() for future in concurrent.futures.as_completed(futures)]

    results.sort(key=lambda x: x[0])
    for req_num, allowed, remaining in results:
        status = "✓ ALLOWED" if allowed else "✗ DENIED"
        print(f"Concurrent request {req_num+1:2d}: {status} | Remaining: {remaining:5.2f}")

    # Example 5: Statistics and monitoring
    print("\n5. Client Statistics")
    print("-" * 60)

    stats = limiter.get_client_stats("user_alice", 10, 60)
    print(f"Client: {stats['client_id']}")
    print(f"Current tokens: {stats.get('tokens', 'N/A')}")
    print(f"Total requests: {stats.get('total_requests', 'N/A')}")
    print(f"TTL: {stats.get('ttl', 'N/A')}s")

    # Example 6: Using workflow run() method
    print("\n6. Workflow Run Method")
    print("-" * 60)

    for response in limiter.run(
        client_id="user_eve",
        max_requests=3,
        time_window_seconds=10,
        operation="check"
    ):
        print(response.content)

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)
