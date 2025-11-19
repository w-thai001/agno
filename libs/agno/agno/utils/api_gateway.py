"""API Gateway FSA with rate limiting and circuit breaker"""

from enum import Enum
from time import monotonic
from typing import Callable, Optional, Tuple, TypeVar

from agno.utils.rate_limiter import RateLimiter

T = TypeVar("T")


class GatewayState(Enum):
    """API Gateway FSA states"""
    READY = "ready"
    PROCESSING = "processing"
    RATE_LIMITED = "rate_limited"
    CIRCUIT_OPEN = "circuit_open"
    ERROR = "error"


class APIGateway:
    """API Gateway with rate limiting and circuit breaker pattern"""

    def __init__(self, rate_limit: float = 100.0, refill_rate: float = 10.0,
                 failure_threshold: int = 5, recovery_timeout: float = 60.0):
        self._limiter = RateLimiter(capacity=rate_limit, refill_rate=refill_rate)
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._failures: dict[str, int] = {}
        self._circuit_open_time: dict[str, float] = {}
        self._state = GatewayState.READY

    @property
    def state(self) -> GatewayState:
        return self._state

    def request(self, key: str, handler: Callable[[], T], tokens: float = 1.0) -> Tuple[bool, Optional[T], str]:
        """Process API request with rate limiting and circuit breaker. Returns: (success, result, message)"""
        # Check circuit breaker
        if key in self._circuit_open_time:
            if monotonic() - self._circuit_open_time[key] < self._recovery_timeout:
                self._state = GatewayState.CIRCUIT_OPEN
                return False, None, "Circuit breaker open"
            del self._circuit_open_time[key]
            self._failures[key] = 0

        # Check rate limit
        success, wait_time = self._limiter.try_consume(key, tokens)
        if not success:
            self._state = GatewayState.RATE_LIMITED
            return False, None, f"Rate limited. Retry in {wait_time:.2f}s"

        # Process request
        self._state = GatewayState.PROCESSING
        try:
            result = handler()
            self._failures[key] = 0
            self._state = GatewayState.READY
            return True, result, "Success"
        except Exception as e:
            self._failures[key] = self._failures.get(key, 0) + 1
            if self._failures[key] >= self._failure_threshold:
                self._circuit_open_time[key] = monotonic()
                self._state = GatewayState.CIRCUIT_OPEN
                return False, None, f"Circuit breaker opened: {str(e)}"
            self._state = GatewayState.ERROR
            return False, None, f"Error: {str(e)}"

    def reset(self, key: str) -> None:
        """Reset circuit breaker and rate limit for key"""
        self._failures.pop(key, None)
        self._circuit_open_time.pop(key, None)
        self._limiter.reset(key)
        self._state = GatewayState.READY
