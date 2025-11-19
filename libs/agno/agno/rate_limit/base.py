"""
Base classes and utilities for rate limiting FSAs
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from time import time
from typing import Optional

from pydantic import BaseModel


class RateLimitState(str, Enum):
    """FSA states for rate limiting"""

    AVAILABLE = "available"  # Requests can proceed
    LIMITED = "limited"  # Rate limit reached, request blocked
    RECOVERING = "recovering"  # Tokens/capacity recovering
    WARNING = "warning"  # Approaching rate limit threshold


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded"""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[float] = None,
        current_state: Optional[RateLimitState] = None,
    ):
        super().__init__(message)
        self.message = message
        self.retry_after = retry_after  # Seconds until request can be retried
        self.current_state = current_state

    def __str__(self) -> str:
        if self.retry_after:
            return f"{self.message} (retry after {self.retry_after:.2f}s)"
        return self.message


@dataclass
class RateLimitMetrics:
    """Metrics for rate limiting FSA"""

    total_requests: int = 0
    allowed_requests: int = 0
    denied_requests: int = 0
    current_capacity: float = 0.0
    max_capacity: float = 0.0
    last_request_time: float = field(default_factory=time)

    @property
    def utilization(self) -> float:
        """Current utilization as percentage (0.0 - 1.0)"""
        if self.max_capacity == 0:
            return 0.0
        return 1.0 - (self.current_capacity / self.max_capacity)

    @property
    def denial_rate(self) -> float:
        """Percentage of requests denied (0.0 - 1.0)"""
        if self.total_requests == 0:
            return 0.0
        return self.denied_requests / self.total_requests


class RateLimiter(ABC, BaseModel):
    """Abstract base class for rate limiter FSAs"""

    rate_limit_id: str
    current_state: RateLimitState = RateLimitState.AVAILABLE
    metrics: RateLimitMetrics = RateLimitMetrics()

    class Config:
        arbitrary_types_allowed = True

    @abstractmethod
    def allow_request(self, tokens: float = 1.0) -> bool:
        """
        Check if request is allowed and update state

        Args:
            tokens: Number of tokens to consume (default 1.0)

        Returns:
            True if request allowed, False otherwise

        Raises:
            RateLimitExceeded: If rate limit is exceeded (optional behavior)
        """
        pass

    @abstractmethod
    def get_retry_after(self) -> Optional[float]:
        """
        Get time in seconds until next request can be made

        Returns:
            Seconds until retry, or None if requests can proceed
        """
        pass

    @abstractmethod
    def reset(self) -> None:
        """Reset the rate limiter state"""
        pass

    def _update_metrics(self, allowed: bool) -> None:
        """Update metrics after request attempt"""
        self.metrics.total_requests += 1
        self.metrics.last_request_time = time()

        if allowed:
            self.metrics.allowed_requests += 1
        else:
            self.metrics.denied_requests += 1

    def _update_state(self) -> None:
        """Update FSA state based on current utilization"""
        utilization = self.metrics.utilization

        if utilization >= 1.0:
            self.current_state = RateLimitState.LIMITED
        elif utilization >= 0.8:
            self.current_state = RateLimitState.WARNING
        elif utilization > 0:
            self.current_state = RateLimitState.RECOVERING
        else:
            self.current_state = RateLimitState.AVAILABLE

    def get_metrics(self) -> dict:
        """Get current metrics as dictionary"""
        return {
            "total_requests": self.metrics.total_requests,
            "allowed_requests": self.metrics.allowed_requests,
            "denied_requests": self.metrics.denied_requests,
            "current_capacity": self.metrics.current_capacity,
            "max_capacity": self.metrics.max_capacity,
            "utilization": self.metrics.utilization,
            "denial_rate": self.metrics.denial_rate,
            "current_state": self.current_state.value,
            "last_request_time": self.metrics.last_request_time,
        }
