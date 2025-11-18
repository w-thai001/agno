"""
Rate Limiter FSA: Advanced rate limiting and throttling for FSA operations.

This module provides comprehensive rate limiting with support for:
- Multiple rate limiting algorithms (Token Bucket, Leaky Bucket, Fixed Window, Sliding Window)
- Per-client quota management
- Burst traffic handling
- Distributed rate limiting with Redis support
- Rate limit analytics and metrics
- Dynamic configuration updates
- Event notifications
- Thread-safe operations
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional, Set, Tuple
from uuid import uuid4

try:
    from agno.utils.log import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


# ==================== Enums and Constants ====================

class RateLimitAlgorithm(Enum):
    """Rate limiting algorithms."""
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"


class RateLimitEvent(Enum):
    """Rate limit event types."""
    LIMIT_EXCEEDED = "limit_exceeded"
    QUOTA_CONSUMED = "quota_consumed"
    QUOTA_RESET = "quota_reset"
    BURST_ALLOWED = "burst_allowed"
    REQUEST_ALLOWED = "request_allowed"
    REQUEST_REJECTED = "request_rejected"


class RequestPriority(Enum):
    """Request priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


# ==================== Data Classes ====================

@dataclass
class Request:
    """Represents a rate-limited request."""
    request_id: str = field(default_factory=lambda: str(uuid4()))
    client_id: str = ""
    resource: str = ""
    priority: RequestPriority = RequestPriority.NORMAL
    tokens: int = 1
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    algorithm: RateLimitAlgorithm = RateLimitAlgorithm.TOKEN_BUCKET
    capacity: int = 100  # Maximum tokens/requests
    refill_rate: float = 10.0  # Tokens per second
    window: timedelta = timedelta(minutes=1)
    burst_capacity: int = 20  # Additional burst capacity
    enable_burst: bool = True
    distributed: bool = False
    redis_key_prefix: str = "rate_limit"


@dataclass
class RateLimitStatus:
    """Status of rate limit check."""
    allowed: bool
    client_id: str
    resource: str
    remaining: int = 0
    limit: int = 0
    retry_after: Optional[timedelta] = None
    reset_at: Optional[datetime] = None


@dataclass
class ValidationResult:
    """Result of configuration validation."""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class ConsumeResult:
    """Result of quota consumption."""
    success: bool
    client_id: str
    tokens_consumed: int = 0
    remaining_tokens: int = 0
    error: Optional[str] = None


@dataclass
class AllowedStatus:
    """Result of rate limit algorithm check."""
    allowed: bool
    remaining: int = 0
    retry_after: Optional[timedelta] = None


@dataclass
class BurstResult:
    """Result of burst handling."""
    allowed: bool
    burst_used: int = 0
    burst_remaining: int = 0


@dataclass
class EnforcementResult:
    """Result of rate limit enforcement."""
    allowed: bool
    action: str = "allow"  # allow, reject, throttle
    retry_after: Optional[timedelta] = None


@dataclass
class QuotaStatus:
    """Quota tracking status."""
    client_id: str
    current_quota: int = 0
    max_quota: int = 0
    quota_percentage: float = 0.0
    reset_at: Optional[datetime] = None


@dataclass
class ResetResult:
    """Result of quota reset."""
    success: bool
    client_id: str
    previous_quota: int = 0
    new_quota: int = 0


@dataclass
class DistributedResult:
    """Result of distributed rate limiting."""
    success: bool
    allowed: bool
    client_id: str
    error: Optional[str] = None


@dataclass
class RateMetrics:
    """Rate limiting metrics."""
    client_id: str
    total_requests: int = 0
    allowed_requests: int = 0
    rejected_requests: int = 0
    avg_tokens_per_request: float = 0.0
    peak_request_rate: float = 0.0
    burst_events: int = 0
    time_window: timedelta = timedelta(minutes=1)


@dataclass
class ConfigResult:
    """Result of configuration update."""
    success: bool
    resource: str
    previous_limit: Optional[int] = None
    new_limit: int = 0
    error: Optional[str] = None


@dataclass
class RateLimitResult:
    """Result of main rate limiting pipeline."""
    success: bool
    allowed: bool
    request_id: str
    client_id: str
    remaining: int = 0
    retry_after: Optional[timedelta] = None
    error: Optional[str] = None


# ==================== Token Bucket ====================

class TokenBucket:
    """Token bucket rate limiting algorithm."""

    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize token bucket.

        Args:
            capacity: Maximum number of tokens
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = float(capacity)
        self.last_refill = time.time()
        self.lock = threading.Lock()

    def consume(self, tokens: int = 1) -> AllowedStatus:
        """
        Consume tokens from bucket.

        Args:
            tokens: Number of tokens to consume

        Returns:
            AllowedStatus indicating if request is allowed
        """
        with self.lock:
            self._refill()

            if self.tokens >= tokens:
                self.tokens -= tokens
                return AllowedStatus(
                    allowed=True,
                    remaining=int(self.tokens)
                )
            else:
                # Calculate retry after
                tokens_needed = tokens - self.tokens
                wait_time = tokens_needed / self.refill_rate
                return AllowedStatus(
                    allowed=False,
                    remaining=int(self.tokens),
                    retry_after=timedelta(seconds=wait_time)
                )

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        tokens_to_add = elapsed * self.refill_rate

        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now

    def get_remaining(self) -> int:
        """Get remaining tokens."""
        with self.lock:
            self._refill()
            return int(self.tokens)


# ==================== Leaky Bucket ====================

class LeakyBucket:
    """Leaky bucket rate limiting algorithm."""

    def __init__(self, capacity: int, leak_rate: float):
        """
        Initialize leaky bucket.

        Args:
            capacity: Maximum bucket capacity
            leak_rate: Requests leaked per second
        """
        self.capacity = capacity
        self.leak_rate = leak_rate
        self.level = 0.0
        self.last_leak = time.time()
        self.lock = threading.Lock()

    def add(self, amount: int = 1) -> AllowedStatus:
        """
        Add requests to bucket.

        Args:
            amount: Number of requests to add

        Returns:
            AllowedStatus indicating if request is allowed
        """
        with self.lock:
            self._leak()

            if self.level + amount <= self.capacity:
                self.level += amount
                return AllowedStatus(
                    allowed=True,
                    remaining=int(self.capacity - self.level)
                )
            else:
                # Calculate retry after
                overflow = (self.level + amount) - self.capacity
                wait_time = overflow / self.leak_rate
                return AllowedStatus(
                    allowed=False,
                    remaining=int(self.capacity - self.level),
                    retry_after=timedelta(seconds=wait_time)
                )

    def _leak(self) -> None:
        """Leak requests based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_leak
        leaked = elapsed * self.leak_rate

        self.level = max(0, self.level - leaked)
        self.last_leak = now

    def get_remaining(self) -> int:
        """Get remaining capacity."""
        with self.lock:
            self._leak()
            return int(self.capacity - self.level)


# ==================== Fixed Window ====================

class FixedWindow:
    """Fixed window counter rate limiting."""

    def __init__(self, limit: int, window: timedelta):
        """
        Initialize fixed window counter.

        Args:
            limit: Maximum requests per window
            window: Time window duration
        """
        self.limit = limit
        self.window = window
        self.counter = 0
        self.window_start = datetime.utcnow()
        self.lock = threading.Lock()

    def check(self, tokens: int = 1) -> AllowedStatus:
        """
        Check if request is allowed.

        Args:
            tokens: Number of tokens to consume

        Returns:
            AllowedStatus indicating if request is allowed
        """
        with self.lock:
            self._reset_if_needed()

            if self.counter + tokens <= self.limit:
                self.counter += tokens
                return AllowedStatus(
                    allowed=True,
                    remaining=self.limit - self.counter
                )
            else:
                # Calculate retry after (time until window resets)
                window_end = self.window_start + self.window
                retry_after = window_end - datetime.utcnow()
                return AllowedStatus(
                    allowed=False,
                    remaining=self.limit - self.counter,
                    retry_after=max(retry_after, timedelta(0))
                )

    def _reset_if_needed(self) -> None:
        """Reset counter if window has elapsed."""
        now = datetime.utcnow()
        if now >= self.window_start + self.window:
            self.counter = 0
            self.window_start = now

    def get_remaining(self) -> int:
        """Get remaining requests in current window."""
        with self.lock:
            self._reset_if_needed()
            return self.limit - self.counter


# ==================== Sliding Window ====================

class SlidingWindow:
    """Sliding window log rate limiting."""

    def __init__(self, limit: int, window: timedelta):
        """
        Initialize sliding window log.

        Args:
            limit: Maximum requests per window
            window: Time window duration
        """
        self.limit = limit
        self.window = window
        self.requests: Deque[datetime] = deque()
        self.lock = threading.Lock()

    def check(self, tokens: int = 1) -> AllowedStatus:
        """
        Check if request is allowed.

        Args:
            tokens: Number of tokens to consume

        Returns:
            AllowedStatus indicating if request is allowed
        """
        with self.lock:
            now = datetime.utcnow()
            self._remove_old_requests(now)

            if len(self.requests) + tokens <= self.limit:
                # Add tokens as separate requests
                for _ in range(tokens):
                    self.requests.append(now)
                return AllowedStatus(
                    allowed=True,
                    remaining=self.limit - len(self.requests)
                )
            else:
                # Calculate retry after (time until oldest request expires)
                if self.requests:
                    oldest = self.requests[0]
                    retry_after = (oldest + self.window) - now
                else:
                    retry_after = timedelta(0)

                return AllowedStatus(
                    allowed=False,
                    remaining=self.limit - len(self.requests),
                    retry_after=max(retry_after, timedelta(0))
                )

    def _remove_old_requests(self, now: datetime) -> None:
        """Remove requests outside the time window."""
        cutoff = now - self.window
        while self.requests and self.requests[0] < cutoff:
            self.requests.popleft()

    def get_remaining(self) -> int:
        """Get remaining requests in current window."""
        with self.lock:
            self._remove_old_requests(datetime.utcnow())
            return self.limit - len(self.requests)


# ==================== Main FSA Class ====================

class RateLimiterFSA:
    """
    Rate Limiter Finite State Automaton.

    Provides advanced rate limiting with multiple algorithms, quota management,
    burst handling, and distributed support.
    """

    def __init__(
        self,
        name: str = "RateLimiterFSA",
        default_config: Optional[RateLimitConfig] = None,
    ):
        """
        Initialize Rate Limiter FSA.

        Args:
            name: Name of the FSA instance
            default_config: Default rate limit configuration
        """
        self.name = name
        self.fsa_id = str(uuid4())
        self.default_config = default_config or RateLimitConfig()

        # Client tracking
        self.token_buckets: Dict[str, TokenBucket] = {}
        self.leaky_buckets: Dict[str, LeakyBucket] = {}
        self.fixed_windows: Dict[str, FixedWindow] = {}
        self.sliding_windows: Dict[str, SlidingWindow] = {}

        # Quota management
        self.quotas: Dict[str, int] = defaultdict(int)
        self.quota_limits: Dict[str, int] = defaultdict(lambda: self.default_config.capacity)
        self.quota_reset_times: Dict[str, datetime] = {}

        # Burst tracking
        self.burst_usage: Dict[str, int] = defaultdict(int)

        # Resource configurations
        self.resource_configs: Dict[str, RateLimitConfig] = {}

        # Metrics
        self.request_counts: Dict[str, int] = defaultdict(int)
        self.allowed_counts: Dict[str, int] = defaultdict(int)
        self.rejected_counts: Dict[str, int] = defaultdict(int)
        self.burst_events: Dict[str, int] = defaultdict(int)
        self.request_history: Dict[str, List[Tuple[datetime, int]]] = defaultdict(list)

        # Event listeners
        self.event_listeners: Dict[RateLimitEvent, List[Callable]] = defaultdict(list)

        # Distributed support
        self.redis_client: Optional[Any] = None

        # Thread safety
        self.lock = threading.RLock()

        logger.info(f"Initialized {self.name} with ID {self.fsa_id}")

    # ==================== Main Execution ====================

    def execute(self, request: Request, client_id: Optional[str] = None) -> RateLimitResult:
        """
        Main rate limiting pipeline.

        Args:
            request: Request to rate limit
            client_id: Optional client ID override

        Returns:
            RateLimitResult with rate limiting decision
        """
        client = client_id or request.client_id
        if not client:
            return RateLimitResult(
                success=False,
                allowed=False,
                request_id=request.request_id,
                client_id="",
                error="Client ID is required"
            )

        try:
            # Check rate limit
            status = self.check_rate_limit(client, request.resource)

            if status.allowed:
                # Consume quota
                consume_result = self.consume_quota(client, request.tokens)

                if consume_result.success:
                    # Track metrics
                    self._track_request(client, request.tokens, allowed=True)

                    # Emit event
                    self.emit_rate_limit_event(client, RateLimitEvent.REQUEST_ALLOWED)

                    return RateLimitResult(
                        success=True,
                        allowed=True,
                        request_id=request.request_id,
                        client_id=client,
                        remaining=consume_result.remaining_tokens
                    )
                else:
                    return RateLimitResult(
                        success=False,
                        allowed=False,
                        request_id=request.request_id,
                        client_id=client,
                        error=consume_result.error
                    )
            else:
                # Track rejection
                self._track_request(client, request.tokens, allowed=False)

                # Emit event
                self.emit_rate_limit_event(client, RateLimitEvent.REQUEST_REJECTED)

                return RateLimitResult(
                    success=True,
                    allowed=False,
                    request_id=request.request_id,
                    client_id=client,
                    remaining=status.remaining,
                    retry_after=status.retry_after
                )

        except Exception as e:
            logger.error(f"Error in rate limit execution: {e}")
            return RateLimitResult(
                success=False,
                allowed=False,
                request_id=request.request_id,
                client_id=client,
                error=str(e)
            )

    # ==================== Validation ====================

    def validate(self, rate_limit_config: RateLimitConfig) -> ValidationResult:
        """
        Validate rate limit configuration.

        Args:
            rate_limit_config: Configuration to validate

        Returns:
            ValidationResult with validation status
        """
        errors = []
        warnings = []

        # Check capacity
        if rate_limit_config.capacity <= 0:
            errors.append("Capacity must be positive")

        # Check refill rate
        if rate_limit_config.refill_rate <= 0:
            errors.append("Refill rate must be positive")

        # Check window
        if rate_limit_config.window <= timedelta(0):
            errors.append("Window duration must be positive")

        # Check burst capacity
        if rate_limit_config.burst_capacity < 0:
            warnings.append("Burst capacity is negative")

        # Check distributed config
        if rate_limit_config.distributed and not self.redis_client:
            warnings.append("Distributed mode enabled but Redis client not configured")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    # ==================== Rate Limit Checking ====================

    def check_rate_limit(self, client_id: str, resource: str) -> RateLimitStatus:
        """
        Check if request is allowed under rate limit.

        Args:
            client_id: Client identifier
            resource: Resource being accessed

        Returns:
            RateLimitStatus with rate limit decision
        """
        config = self._get_config(resource)
        key = f"{client_id}:{resource}"

        # Use appropriate algorithm
        if config.algorithm == RateLimitAlgorithm.TOKEN_BUCKET:
            status = self._check_token_bucket(key, config)
        elif config.algorithm == RateLimitAlgorithm.LEAKY_BUCKET:
            status = self._check_leaky_bucket(key, config)
        elif config.algorithm == RateLimitAlgorithm.FIXED_WINDOW:
            status = self._check_fixed_window(key, config)
        elif config.algorithm == RateLimitAlgorithm.SLIDING_WINDOW:
            status = self._check_sliding_window(key, config)
        else:
            status = AllowedStatus(allowed=True)

        return RateLimitStatus(
            allowed=status.allowed,
            client_id=client_id,
            resource=resource,
            remaining=status.remaining,
            limit=config.capacity,
            retry_after=status.retry_after
        )

    def _check_token_bucket(self, key: str, config: RateLimitConfig) -> AllowedStatus:
        """Check using token bucket algorithm."""
        with self.lock:
            if key not in self.token_buckets:
                self.token_buckets[key] = TokenBucket(
                    config.capacity,
                    config.refill_rate
                )
            return self.token_buckets[key].consume(1)

    def _check_leaky_bucket(self, key: str, config: RateLimitConfig) -> AllowedStatus:
        """Check using leaky bucket algorithm."""
        with self.lock:
            if key not in self.leaky_buckets:
                self.leaky_buckets[key] = LeakyBucket(
                    config.capacity,
                    config.refill_rate
                )
            return self.leaky_buckets[key].add(1)

    def _check_fixed_window(self, key: str, config: RateLimitConfig) -> AllowedStatus:
        """Check using fixed window algorithm."""
        with self.lock:
            if key not in self.fixed_windows:
                self.fixed_windows[key] = FixedWindow(
                    config.capacity,
                    config.window
                )
            return self.fixed_windows[key].check(1)

    def _check_sliding_window(self, key: str, config: RateLimitConfig) -> AllowedStatus:
        """Check using sliding window algorithm."""
        with self.lock:
            if key not in self.sliding_windows:
                self.sliding_windows[key] = SlidingWindow(
                    config.capacity,
                    config.window
                )
            return self.sliding_windows[key].check(1)

    # ==================== Quota Management ====================

    def consume_quota(self, client_id: str, tokens: int) -> ConsumeResult:
        """
        Consume tokens from client quota.

        Args:
            client_id: Client identifier
            tokens: Number of tokens to consume

        Returns:
            ConsumeResult with consumption status
        """
        with self.lock:
            current = self.quotas[client_id]
            limit = self.quota_limits[client_id]

            if current + tokens <= limit:
                self.quotas[client_id] += tokens

                # Emit event
                self.emit_rate_limit_event(client_id, RateLimitEvent.QUOTA_CONSUMED)

                return ConsumeResult(
                    success=True,
                    client_id=client_id,
                    tokens_consumed=tokens,
                    remaining_tokens=limit - self.quotas[client_id]
                )
            else:
                return ConsumeResult(
                    success=False,
                    client_id=client_id,
                    tokens_consumed=0,
                    remaining_tokens=limit - current,
                    error="Insufficient quota"
                )

    def track_quota(self, client_id: str) -> QuotaStatus:
        """
        Monitor quota usage.

        Args:
            client_id: Client identifier

        Returns:
            QuotaStatus with current quota information
        """
        with self.lock:
            current = self.quotas[client_id]
            limit = self.quota_limits[client_id]
            percentage = (current / limit * 100) if limit > 0 else 0

            return QuotaStatus(
                client_id=client_id,
                current_quota=current,
                max_quota=limit,
                quota_percentage=percentage,
                reset_at=self.quota_reset_times.get(client_id)
            )

    def reset_quota(self, client_id: str) -> ResetResult:
        """
        Reset client quota.

        Args:
            client_id: Client identifier

        Returns:
            ResetResult with reset status
        """
        with self.lock:
            previous = self.quotas[client_id]
            limit = self.quota_limits[client_id]

            self.quotas[client_id] = 0
            self.quota_reset_times[client_id] = datetime.utcnow()

            # Emit event
            self.emit_rate_limit_event(client_id, RateLimitEvent.QUOTA_RESET)

            logger.info(f"Reset quota for {client_id}: {previous} -> 0")
            return ResetResult(
                success=True,
                client_id=client_id,
                previous_quota=previous,
                new_quota=0
            )

    # ==================== Algorithm Implementations ====================

    def token_bucket_algorithm(
        self,
        client_id: str,
        capacity: int,
        refill_rate: float
    ) -> AllowedStatus:
        """
        Token bucket rate limiting.

        Args:
            client_id: Client identifier
            capacity: Maximum tokens
            refill_rate: Tokens per second

        Returns:
            AllowedStatus indicating if request is allowed
        """
        key = f"tb:{client_id}"
        with self.lock:
            if key not in self.token_buckets:
                self.token_buckets[key] = TokenBucket(capacity, refill_rate)
            return self.token_buckets[key].consume(1)

    def leaky_bucket_algorithm(
        self,
        client_id: str,
        capacity: int,
        leak_rate: float
    ) -> AllowedStatus:
        """
        Leaky bucket rate limiting.

        Args:
            client_id: Client identifier
            capacity: Bucket capacity
            leak_rate: Requests leaked per second

        Returns:
            AllowedStatus indicating if request is allowed
        """
        key = f"lb:{client_id}"
        with self.lock:
            if key not in self.leaky_buckets:
                self.leaky_buckets[key] = LeakyBucket(capacity, leak_rate)
            return self.leaky_buckets[key].add(1)

    def fixed_window_algorithm(
        self,
        client_id: str,
        limit: int,
        window: timedelta
    ) -> AllowedStatus:
        """
        Fixed window counting.

        Args:
            client_id: Client identifier
            limit: Requests per window
            window: Time window

        Returns:
            AllowedStatus indicating if request is allowed
        """
        key = f"fw:{client_id}"
        with self.lock:
            if key not in self.fixed_windows:
                self.fixed_windows[key] = FixedWindow(limit, window)
            return self.fixed_windows[key].check(1)

    def sliding_window_algorithm(
        self,
        client_id: str,
        limit: int,
        window: timedelta
    ) -> AllowedStatus:
        """
        Sliding window log.

        Args:
            client_id: Client identifier
            limit: Requests per window
            window: Time window

        Returns:
            AllowedStatus indicating if request is allowed
        """
        key = f"sw:{client_id}"
        with self.lock:
            if key not in self.sliding_windows:
                self.sliding_windows[key] = SlidingWindow(limit, window)
            return self.sliding_windows[key].check(1)

    # ==================== Burst Handling ====================

    def handle_burst(self, client_id: str, burst_capacity: int) -> BurstResult:
        """
        Allow traffic bursts.

        Args:
            client_id: Client identifier
            burst_capacity: Maximum burst capacity

        Returns:
            BurstResult with burst handling status
        """
        with self.lock:
            current_burst = self.burst_usage[client_id]

            if current_burst < burst_capacity:
                self.burst_usage[client_id] += 1
                self.burst_events[client_id] += 1

                # Emit event
                self.emit_rate_limit_event(client_id, RateLimitEvent.BURST_ALLOWED)

                logger.debug(f"Burst allowed for {client_id}: {current_burst + 1}/{burst_capacity}")
                return BurstResult(
                    allowed=True,
                    burst_used=current_burst + 1,
                    burst_remaining=burst_capacity - (current_burst + 1)
                )
            else:
                return BurstResult(
                    allowed=False,
                    burst_used=current_burst,
                    burst_remaining=0
                )

    # ==================== Enforcement ====================

    def enforce_limit(self, client_id: str, limit_exceeded: bool) -> EnforcementResult:
        """
        Reject or throttle request.

        Args:
            client_id: Client identifier
            limit_exceeded: Whether limit was exceeded

        Returns:
            EnforcementResult with enforcement decision
        """
        if not limit_exceeded:
            return EnforcementResult(
                allowed=True,
                action="allow"
            )

        # Check if burst is available
        config = self._get_config("")
        if config.enable_burst:
            burst_result = self.handle_burst(client_id, config.burst_capacity)
            if burst_result.allowed:
                return EnforcementResult(
                    allowed=True,
                    action="burst"
                )

        # Calculate retry after
        retry_after = self.calculate_retry_after(client_id)

        # Emit limit exceeded event
        self.emit_rate_limit_event(client_id, RateLimitEvent.LIMIT_EXCEEDED)

        logger.warning(f"Rate limit exceeded for {client_id}")
        return EnforcementResult(
            allowed=False,
            action="reject",
            retry_after=retry_after
        )

    # ==================== Distributed Rate Limiting ====================

    def distributed_rate_limit(
        self,
        client_id: str,
        redis_client: Optional[Any] = None
    ) -> DistributedResult:
        """
        Rate limit across servers using Redis.

        Args:
            client_id: Client identifier
            redis_client: Redis client instance

        Returns:
            DistributedResult with distributed rate limit status
        """
        redis = redis_client or self.redis_client

        if not redis:
            return DistributedResult(
                success=False,
                allowed=False,
                client_id=client_id,
                error="Redis client not configured"
            )

        try:
            # Mock implementation (actual Redis implementation would use Redis commands)
            config = self.default_config
            key = f"{config.redis_key_prefix}:{client_id}"

            # This is a simplified mock - real implementation would use Redis INCR, EXPIRE, etc.
            # For now, fall back to local rate limiting
            status = self.check_rate_limit(client_id, "")

            return DistributedResult(
                success=True,
                allowed=status.allowed,
                client_id=client_id
            )

        except Exception as e:
            logger.error(f"Distributed rate limit error: {e}")
            return DistributedResult(
                success=False,
                allowed=False,
                client_id=client_id,
                error=str(e)
            )

    # ==================== Metrics ====================

    def collect_rate_metrics(
        self,
        client_id: str,
        time_window: timedelta = timedelta(minutes=1)
    ) -> RateMetrics:
        """
        Generate rate analytics.

        Args:
            client_id: Client identifier
            time_window: Time window for metrics

        Returns:
            RateMetrics with analytics data
        """
        with self.lock:
            total = self.request_counts[client_id]
            allowed = self.allowed_counts[client_id]
            rejected = self.rejected_counts[client_id]

            # Calculate average tokens per request
            history = self.request_history[client_id]
            if history:
                total_tokens = sum(tokens for _, tokens in history)
                avg_tokens = total_tokens / len(history)
            else:
                avg_tokens = 0.0

            # Calculate peak request rate
            if history:
                cutoff = datetime.utcnow() - time_window
                recent_requests = [t for t, _ in history if t > cutoff]
                if recent_requests and time_window.total_seconds() > 0:
                    peak_rate = len(recent_requests) / time_window.total_seconds()
                else:
                    peak_rate = 0.0
            else:
                peak_rate = 0.0

            return RateMetrics(
                client_id=client_id,
                total_requests=total,
                allowed_requests=allowed,
                rejected_requests=rejected,
                avg_tokens_per_request=avg_tokens,
                peak_request_rate=peak_rate,
                burst_events=self.burst_events[client_id],
                time_window=time_window
            )

    # ==================== Configuration ====================

    def configure_limit(
        self,
        resource: str,
        limit: int,
        period: timedelta,
        algorithm: Optional[RateLimitAlgorithm] = None
    ) -> ConfigResult:
        """
        Set rate limits for resource.

        Args:
            resource: Resource identifier
            limit: Request limit
            period: Time period
            algorithm: Optional algorithm override

        Returns:
            ConfigResult with configuration status
        """
        with self.lock:
            previous_limit = None
            if resource in self.resource_configs:
                previous_limit = self.resource_configs[resource].capacity

            config = RateLimitConfig(
                algorithm=algorithm or self.default_config.algorithm,
                capacity=limit,
                window=period,
                refill_rate=limit / period.total_seconds(),
                burst_capacity=self.default_config.burst_capacity,
                enable_burst=self.default_config.enable_burst
            )

            self.resource_configs[resource] = config

            logger.info(f"Configured rate limit for {resource}: {limit} per {period}")
            return ConfigResult(
                success=True,
                resource=resource,
                previous_limit=previous_limit,
                new_limit=limit
            )

    # ==================== Event Handling ====================

    def emit_rate_limit_event(
        self,
        client_id: str,
        event_type: RateLimitEvent
    ) -> None:
        """
        Notify rate limit events.

        Args:
            client_id: Client identifier
            event_type: Type of event
        """
        if event_type in self.event_listeners:
            for listener in self.event_listeners[event_type]:
                try:
                    listener(client_id, event_type)
                except Exception as e:
                    logger.error(f"Error in event listener: {e}")

    def add_event_listener(
        self,
        event_type: RateLimitEvent,
        listener: Callable
    ) -> None:
        """
        Add event listener.

        Args:
            event_type: Type of event to listen for
            listener: Callback function
        """
        self.event_listeners[event_type].append(listener)

    # ==================== Utility Methods ====================

    def calculate_retry_after(self, client_id: str) -> timedelta:
        """
        Calculate wait time before retry.

        Args:
            client_id: Client identifier

        Returns:
            Time to wait before retry
        """
        config = self._get_config("")
        key = f"{client_id}:"

        # Get retry time from appropriate algorithm
        if config.algorithm == RateLimitAlgorithm.TOKEN_BUCKET:
            if key in self.token_buckets:
                status = self.token_buckets[key].consume(0)
                return status.retry_after or timedelta(seconds=1)

        # Default retry after
        return timedelta(seconds=1)

    def get_remaining_quota(self, client_id: str) -> int:
        """
        Get remaining tokens for client.

        Args:
            client_id: Client identifier

        Returns:
            Number of remaining tokens
        """
        with self.lock:
            limit = self.quota_limits[client_id]
            used = self.quotas[client_id]
            return max(0, limit - used)

    def _get_config(self, resource: str) -> RateLimitConfig:
        """Get configuration for resource."""
        return self.resource_configs.get(resource, self.default_config)

    def _track_request(self, client_id: str, tokens: int, allowed: bool) -> None:
        """Track request for metrics."""
        with self.lock:
            self.request_counts[client_id] += 1
            if allowed:
                self.allowed_counts[client_id] += 1
            else:
                self.rejected_counts[client_id] += 1

            self.request_history[client_id].append((datetime.utcnow(), tokens))

            # Limit history size
            if len(self.request_history[client_id]) > 1000:
                self.request_history[client_id] = self.request_history[client_id][-1000:]
