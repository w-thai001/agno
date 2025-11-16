"""
FSA Rate Limiter

Control FSA execution rate and resource usage:
- Token bucket algorithm
- Sliding window rate limiting
- Fixed window rate limiting
- Concurrent execution limiting
- Burst handling
- Rate quota management
- Adaptive rate limiting

Prevents resource exhaustion and ensures fair usage.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from datetime import datetime, timedelta
import time
from collections import deque

from pydantic import BaseModel

from agno.agent import Agent
from agno.fsa.base import FSA, FSAState, FSATransition, FSAExecutionResult
from agno.utils.log import logger


class RateLimitAlgorithm(str, Enum):
    """Rate limiting algorithms"""
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"
    CONCURRENT_LIMIT = "concurrent_limit"


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded"""
    pass


class RateLimitStatus(BaseModel):
    """Rate limit status"""
    allowed: bool
    remaining_quota: int
    reset_time: str
    retry_after_seconds: float


class RateLimitMetrics(BaseModel):
    """Rate limiter metrics"""
    total_requests: int
    allowed_requests: int
    rejected_requests: int
    current_rate: float  # requests per second
    quota_remaining: int
    algorithm: RateLimitAlgorithm


class RateLimiterState(str, Enum):
    """States for Rate Limiter FSA"""
    INITIAL = "initial"
    CHECKING = "checking"
    ALLOWING = "allowing"
    THROTTLING = "throttling"
    EXECUTING = "executing"
    REPLENISHING = "replenishing"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class FSARateLimiter(FSA):
    """
    FSA Rate Limiter

    Controls FSA execution rate using various algorithms:
    - Token Bucket: Allows bursts up to bucket size
    - Sliding Window: Smooth rate limiting over time window
    - Fixed Window: Resets quota at fixed intervals
    - Concurrent Limit: Limits simultaneous executions

    Example:
        ```python
        # Create rate limiter (100 requests per minute)
        limiter = FSARateLimiter(
            name="RateLimiter",
            requests_per_second=100/60,
            algorithm="token_bucket",
            burst_size=10
        )

        # Execute with rate limiting
        result = limiter.execute_limited(
            my_fsa,
            context={"task": "test"}
        )

        # Check rate limit status
        status = limiter.get_status()
        print(f"Remaining: {status.remaining_quota}")
        print(f"Retry after: {status.retry_after_seconds}s")
        ```
    """

    # Configuration
    requests_per_second: float = 10.0  # Max requests per second
    algorithm: str = "token_bucket"
    burst_size: int = 20  # Max burst for token bucket
    window_size_seconds: float = 60.0  # Window size for sliding/fixed window
    max_concurrent: int = 10  # Max concurrent executions

    # Token Bucket state
    tokens: float = 0.0
    max_tokens: float = 20.0
    last_refill_time: Optional[datetime] = None

    # Sliding Window state
    request_timestamps: deque = field(default_factory=deque)

    # Fixed Window state
    window_start: Optional[datetime] = None
    window_requests: int = 0

    # Concurrent execution state
    current_concurrent: int = 0

    # Metrics
    total_requests: int = 0
    allowed_requests: int = 0
    rejected_requests: int = 0

    # Callback for rate limit exceeded
    on_rate_limit_exceeded: Optional[Callable] = None

    def __post_init__(self):
        """Initialize rate limiter"""
        self.initial_state = RateLimiterState.INITIAL
        self.current_state = self.initial_state
        self.final_states = {RateLimiterState.SUCCESS, RateLimiterState.FAILED}
        self.state_history = [self.current_state]

        # Initialize algorithm-specific state
        self.max_tokens = self.burst_size
        self.tokens = self.max_tokens
        self.last_refill_time = datetime.now()
        self.window_start = datetime.now()

        self._setup_transitions()

        if self.debug_mode:
            logger.debug(f"FSARateLimiter {self.name} initialized")
            logger.debug(f"Algorithm: {self.algorithm}")
            logger.debug(f"Rate: {self.requests_per_second} req/s")

    def _setup_transitions(self) -> None:
        """Setup rate limiter workflow"""
        # INITIAL -> CHECKING
        self.add_transition(
            RateLimiterState.INITIAL,
            RateLimiterState.CHECKING,
            action=self._check_rate_limit,
            description="Check rate limit"
        )

        # CHECKING -> ALLOWING (quota available)
        self.add_transition(
            RateLimiterState.CHECKING,
            RateLimiterState.ALLOWING,
            condition=lambda ctx: ctx.get("allowed", False),
            action=self._allow_request,
            description="Allow request"
        )

        # CHECKING -> THROTTLING (quota exceeded)
        self.add_transition(
            RateLimiterState.CHECKING,
            RateLimiterState.THROTTLING,
            condition=lambda ctx: not ctx.get("allowed", False),
            action=self._throttle_request,
            description="Throttle request"
        )

        # ALLOWING -> EXECUTING
        self.add_transition(
            RateLimiterState.ALLOWING,
            RateLimiterState.EXECUTING,
            action=self._execute_request,
            description="Execute request"
        )

        # THROTTLING -> REPLENISHING
        self.add_transition(
            RateLimiterState.THROTTLING,
            RateLimiterState.REPLENISHING,
            condition=lambda ctx: ctx.get("should_wait", False),
            action=self._replenish_quota,
            description="Wait and replenish quota"
        )

        # REPLENISHING -> CHECKING
        self.add_transition(
            RateLimiterState.REPLENISHING,
            RateLimiterState.CHECKING,
            condition=lambda ctx: ctx.get("replenished", False),
            description="Retry after replenishment"
        )

        # THROTTLING -> FAILED (no wait)
        self.add_transition(
            RateLimiterState.THROTTLING,
            RateLimiterState.FAILED,
            condition=lambda ctx: not ctx.get("should_wait", False),
            description="Rate limit exceeded"
        )

        # EXECUTING -> SUCCESS
        self.add_transition(
            RateLimiterState.EXECUTING,
            RateLimiterState.SUCCESS,
            condition=lambda ctx: ctx.get("execution_complete", False),
            description="Execution complete"
        )

        # Error handling
        for state in RateLimiterState:
            if state not in [RateLimiterState.SUCCESS, RateLimiterState.FAILED]:
                self.add_transition(
                    state,
                    RateLimiterState.FAILED,
                    condition=lambda ctx: ctx.get("critical_error", False),
                    description="Critical error"
                )

    def _check_rate_limit(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Check if request is allowed under rate limit"""
        self.total_requests += 1

        algorithm = RateLimitAlgorithm(self.algorithm)

        if algorithm == RateLimitAlgorithm.TOKEN_BUCKET:
            allowed = self._check_token_bucket()
        elif algorithm == RateLimitAlgorithm.SLIDING_WINDOW:
            allowed = self._check_sliding_window()
        elif algorithm == RateLimitAlgorithm.FIXED_WINDOW:
            allowed = self._check_fixed_window()
        elif algorithm == RateLimitAlgorithm.CONCURRENT_LIMIT:
            allowed = self._check_concurrent_limit()
        else:
            allowed = True

        context["allowed"] = allowed

        if not allowed:
            self.rejected_requests += 1
            if self.debug_mode:
                logger.warning(f"Rate limit exceeded ({self.algorithm})")
        else:
            self.allowed_requests += 1

        return context

    def _check_token_bucket(self) -> bool:
        """Check token bucket rate limit"""
        # Refill tokens based on time elapsed
        now = datetime.now()
        if self.last_refill_time:
            elapsed = (now - self.last_refill_time).total_seconds()
            tokens_to_add = elapsed * self.requests_per_second
            self.tokens = min(self.max_tokens, self.tokens + tokens_to_add)

        self.last_refill_time = now

        # Check if token available
        if self.tokens >= 1.0:
            return True
        return False

    def _check_sliding_window(self) -> bool:
        """Check sliding window rate limit"""
        now = datetime.now()
        window_start = now - timedelta(seconds=self.window_size_seconds)

        # Remove old timestamps
        while self.request_timestamps and self.request_timestamps[0] < window_start:
            self.request_timestamps.popleft()

        # Check if under limit
        max_requests = int(self.requests_per_second * self.window_size_seconds)
        return len(self.request_timestamps) < max_requests

    def _check_fixed_window(self) -> bool:
        """Check fixed window rate limit"""
        now = datetime.now()

        # Check if window has reset
        if self.window_start and (now - self.window_start).total_seconds() >= self.window_size_seconds:
            self.window_start = now
            self.window_requests = 0

        # Check if under limit
        max_requests = int(self.requests_per_second * self.window_size_seconds)
        return self.window_requests < max_requests

    def _check_concurrent_limit(self) -> bool:
        """Check concurrent execution limit"""
        return self.current_concurrent < self.max_concurrent

    def _allow_request(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Allow request and consume quota"""
        algorithm = RateLimitAlgorithm(self.algorithm)

        if algorithm == RateLimitAlgorithm.TOKEN_BUCKET:
            self.tokens -= 1.0
        elif algorithm == RateLimitAlgorithm.SLIDING_WINDOW:
            self.request_timestamps.append(datetime.now())
        elif algorithm == RateLimitAlgorithm.FIXED_WINDOW:
            self.window_requests += 1
        elif algorithm == RateLimitAlgorithm.CONCURRENT_LIMIT:
            self.current_concurrent += 1

        if self.debug_mode:
            logger.debug(f"Request allowed. Remaining quota: {self._get_remaining_quota()}")

        return context

    def _throttle_request(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Throttle request that exceeds rate limit"""
        # Calculate retry after time
        retry_after = self._calculate_retry_after()

        context["retry_after_seconds"] = retry_after
        context["should_wait"] = context.get("wait_if_limited", False)

        # Call callback if set
        if self.on_rate_limit_exceeded:
            self.on_rate_limit_exceeded(retry_after)

        if self.debug_mode:
            logger.warning(f"Request throttled. Retry after: {retry_after:.2f}s")

        return context

    def _replenish_quota(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Wait for quota replenishment"""
        retry_after = context.get("retry_after_seconds", 1.0)

        if self.debug_mode:
            logger.info(f"Waiting {retry_after:.2f}s for quota replenishment")

        time.sleep(retry_after)

        context["replenished"] = True

        return context

    def _execute_request(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the rate-limited request"""
        fsa = context.get("target_fsa")
        fsa_context = context.get("fsa_context", {})

        if not fsa:
            context["critical_error"] = True
            raise ValueError("No FSA provided for rate limiting")

        try:
            result = fsa.run(initial_context=fsa_context)
            context["result"] = result
            context["execution_complete"] = True

        except Exception as e:
            context["error"] = str(e)
            context["execution_complete"] = False

            if self.debug_mode:
                logger.error(f"Execution failed: {e}")

        finally:
            # Release concurrent slot if using concurrent limit
            if RateLimitAlgorithm(self.algorithm) == RateLimitAlgorithm.CONCURRENT_LIMIT:
                self.current_concurrent -= 1

        return context

    def _calculate_retry_after(self) -> float:
        """Calculate time until next request is allowed"""
        algorithm = RateLimitAlgorithm(self.algorithm)

        if algorithm == RateLimitAlgorithm.TOKEN_BUCKET:
            # Time to get 1 token
            return 1.0 / self.requests_per_second

        elif algorithm == RateLimitAlgorithm.SLIDING_WINDOW:
            if self.request_timestamps:
                # Time until oldest request falls out of window
                oldest = self.request_timestamps[0]
                window_end = oldest + timedelta(seconds=self.window_size_seconds)
                now = datetime.now()
                return max(0, (window_end - now).total_seconds())
            return 0.0

        elif algorithm == RateLimitAlgorithm.FIXED_WINDOW:
            # Time until window resets
            if self.window_start:
                window_end = self.window_start + timedelta(seconds=self.window_size_seconds)
                now = datetime.now()
                return max(0, (window_end - now).total_seconds())
            return 0.0

        elif algorithm == RateLimitAlgorithm.CONCURRENT_LIMIT:
            # Estimate based on average execution time
            return 0.1  # Default wait time

        return 1.0

    def _get_remaining_quota(self) -> int:
        """Get remaining quota"""
        algorithm = RateLimitAlgorithm(self.algorithm)

        if algorithm == RateLimitAlgorithm.TOKEN_BUCKET:
            return int(self.tokens)

        elif algorithm == RateLimitAlgorithm.SLIDING_WINDOW:
            max_requests = int(self.requests_per_second * self.window_size_seconds)
            return max(0, max_requests - len(self.request_timestamps))

        elif algorithm == RateLimitAlgorithm.FIXED_WINDOW:
            max_requests = int(self.requests_per_second * self.window_size_seconds)
            return max(0, max_requests - self.window_requests)

        elif algorithm == RateLimitAlgorithm.CONCURRENT_LIMIT:
            return max(0, self.max_concurrent - self.current_concurrent)

        return 0

    def execute_limited(
        self,
        fsa: FSA,
        context: Optional[Dict[str, Any]] = None,
        wait_if_limited: bool = False
    ) -> Any:
        """
        Execute FSA with rate limiting

        Args:
            fsa: FSA to execute
            context: Execution context
            wait_if_limited: If True, wait when rate limited. If False, raise exception.

        Returns:
            Execution result

        Raises:
            RateLimitExceeded: If rate limit exceeded and wait_if_limited=False
        """
        self.reset()

        exec_context = {
            "target_fsa": fsa,
            "fsa_context": context or {},
            "wait_if_limited": wait_if_limited
        }

        result = self.run(exec_context)

        if self.current_state == RateLimiterState.FAILED:
            raise RateLimitExceeded(
                f"Rate limit exceeded. Retry after {self._calculate_retry_after():.2f}s"
            )

        return result.context.get("result")

    def get_status(self) -> RateLimitStatus:
        """Get current rate limit status"""
        now = datetime.now()
        retry_after = self._calculate_retry_after()

        reset_time = now + timedelta(seconds=retry_after)

        return RateLimitStatus(
            allowed=self._check_rate_limit_allowed(),
            remaining_quota=self._get_remaining_quota(),
            reset_time=reset_time.isoformat(),
            retry_after_seconds=retry_after
        )

    def get_metrics(self) -> RateLimitMetrics:
        """Get rate limiter metrics"""
        current_rate = 0.0
        if self.total_requests > 0 and self.last_refill_time:
            elapsed = (datetime.now() - self.last_refill_time).total_seconds()
            if elapsed > 0:
                current_rate = self.allowed_requests / elapsed

        return RateLimitMetrics(
            total_requests=self.total_requests,
            allowed_requests=self.allowed_requests,
            rejected_requests=self.rejected_requests,
            current_rate=current_rate,
            quota_remaining=self._get_remaining_quota(),
            algorithm=RateLimitAlgorithm(self.algorithm)
        )

    def _check_rate_limit_allowed(self) -> bool:
        """Check if a request would be allowed (without consuming quota)"""
        algorithm = RateLimitAlgorithm(self.algorithm)

        if algorithm == RateLimitAlgorithm.TOKEN_BUCKET:
            # Refill tokens (without modifying state)
            now = datetime.now()
            if self.last_refill_time:
                elapsed = (now - self.last_refill_time).total_seconds()
                tokens_to_add = elapsed * self.requests_per_second
                virtual_tokens = min(self.max_tokens, self.tokens + tokens_to_add)
                return virtual_tokens >= 1.0
            return self.tokens >= 1.0

        elif algorithm == RateLimitAlgorithm.SLIDING_WINDOW:
            now = datetime.now()
            window_start = now - timedelta(seconds=self.window_size_seconds)
            active_requests = sum(1 for ts in self.request_timestamps if ts >= window_start)
            max_requests = int(self.requests_per_second * self.window_size_seconds)
            return active_requests < max_requests

        elif algorithm == RateLimitAlgorithm.FIXED_WINDOW:
            max_requests = int(self.requests_per_second * self.window_size_seconds)
            return self.window_requests < max_requests

        elif algorithm == RateLimitAlgorithm.CONCURRENT_LIMIT:
            return self.current_concurrent < self.max_concurrent

        return True

    def reset_quota(self) -> None:
        """Reset rate limit quota"""
        self.tokens = self.max_tokens
        self.request_timestamps.clear()
        self.window_requests = 0
        self.window_start = datetime.now()
        self.current_concurrent = 0
        self.last_refill_time = datetime.now()

        if self.debug_mode:
            logger.info("Rate limit quota reset")
