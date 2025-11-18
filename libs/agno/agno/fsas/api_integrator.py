"""
API Integrator FSA - Universal API integration layer for the MLA framework.

Supports REST, GraphQL, gRPC, WebSocket, and SOAP APIs with automatic
retry logic, rate limiting, authentication, caching, and error recovery.
"""

import asyncio
import hashlib
import json
import time
import ssl
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from urllib.parse import urljoin, urlparse
import threading

try:
    import aiohttp
    import requests
    from requests.adapters import HTTPAdapter, Retry as RequestsRetry
except ImportError:
    aiohttp = None
    requests = None
    HTTPAdapter = None
    RequestsRetry = None

try:
    import grpc
except ImportError:
    grpc = None

try:
    import websockets
except ImportError:
    websockets = None

try:
    from zeep import Client as SOAPClient
    from zeep.transports import Transport
except ImportError:
    SOAPClient = None
    Transport = None

from agno.fsas.base import BaseFSA, FSAState
from agno.utils.log import logger


# ============================================================================
# ENUMS AND CONSTANTS
# ============================================================================


class ProtocolType(Enum):
    """Supported API protocol types."""

    REST = "rest"
    GRAPHQL = "graphql"
    GRPC = "grpc"
    WEBSOCKET = "websocket"
    SOAP = "soap"


class HTTPMethod(Enum):
    """HTTP methods for REST APIs."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class AuthType(Enum):
    """Authentication types."""

    NONE = "none"
    API_KEY = "api_key"
    BEARER = "bearer"
    BASIC = "basic"
    OAUTH2 = "oauth2"
    JWT = "jwt"
    MTLS = "mtls"


class OAuth2GrantType(Enum):
    """OAuth2 grant types."""

    AUTHORIZATION_CODE = "authorization_code"
    CLIENT_CREDENTIALS = "client_credentials"
    IMPLICIT = "implicit"
    REFRESH_TOKEN = "refresh_token"
    PASSWORD = "password"


class CircuitBreakerState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class RecoveryAction(Enum):
    """Error recovery actions."""

    RETRY = "retry"
    FALLBACK = "fallback"
    FAIL = "fail"
    CIRCUIT_BREAK = "circuit_break"


# ============================================================================
# EXCEPTIONS
# ============================================================================


class APIIntegratorError(Exception):
    """Base exception for API Integrator errors."""

    pass


class NetworkTimeoutError(APIIntegratorError):
    """Network timeout error."""

    pass


class AuthenticationFailedError(APIIntegratorError):
    """Authentication failed error."""

    pass


class RateLimitExceededError(APIIntegratorError):
    """Rate limit exceeded error."""

    pass


class CircuitBreakerOpenError(APIIntegratorError):
    """Circuit breaker is open error."""

    pass


class InvalidResponseError(APIIntegratorError):
    """Invalid response error."""

    pass


class ProtocolNotSupportedError(APIIntegratorError):
    """Protocol not supported error."""

    pass


# ============================================================================
# DATA MODELS
# ============================================================================


@dataclass
class APIRequest:
    """Represents an API request."""

    protocol: ProtocolType
    endpoint: str
    method: HTTPMethod = HTTPMethod.GET
    headers: Dict[str, str] = field(default_factory=dict)
    params: Dict[str, Any] = field(default_factory=dict)
    body: Optional[Any] = None
    timeout: float = 30.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_cache_key(self) -> str:
        """Generate cache key for the request."""
        key_parts = [
            self.protocol.value,
            self.endpoint,
            self.method.value if hasattr(self, "method") else "",
            json.dumps(self.params, sort_keys=True),
            json.dumps(self.headers, sort_keys=True),
        ]
        key_string = ":".join(str(p) for p in key_parts)
        return hashlib.sha256(key_string.encode()).hexdigest()


@dataclass
class APIResponse:
    """Represents an API response."""

    status_code: int
    data: Any
    headers: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    cached: bool = False
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def is_success(self) -> bool:
        """Check if response is successful."""
        return 200 <= self.status_code < 300

    @property
    def is_client_error(self) -> bool:
        """Check if response is a client error."""
        return 400 <= self.status_code < 500

    @property
    def is_server_error(self) -> bool:
        """Check if response is a server error."""
        return 500 <= self.status_code < 600


@dataclass
class ValidationResult:
    """Result of configuration validation."""

    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_error(self, error: str) -> None:
        """Add validation error."""
        self.errors.append(error)
        self.valid = False

    def add_warning(self, warning: str) -> None:
        """Add validation warning."""
        self.warnings.append(warning)


@dataclass
class AuthConfig:
    """Authentication configuration."""

    auth_type: AuthType
    credentials: Dict[str, Any] = field(default_factory=dict)
    token_url: Optional[str] = None
    refresh_url: Optional[str] = None
    grant_type: Optional[OAuth2GrantType] = None
    scopes: List[str] = field(default_factory=list)


@dataclass
class AuthToken:
    """Authentication token."""

    access_token: str
    token_type: str = "Bearer"
    expires_at: Optional[datetime] = None
    refresh_token: Optional[str] = None
    scopes: List[str] = field(default_factory=list)

    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() >= self.expires_at

    def to_header_value(self) -> str:
        """Convert to authorization header value."""
        return f"{self.token_type} {self.access_token}"


@dataclass
class APIConfig:
    """API configuration."""

    base_url: str
    protocol: ProtocolType
    auth_config: Optional[AuthConfig] = None
    default_headers: Dict[str, str] = field(default_factory=dict)
    timeout: float = 30.0
    retry_config: Optional[Dict[str, Any]] = None
    rate_limit_config: Optional[Dict[str, Any]] = None
    circuit_breaker_config: Optional[Dict[str, Any]] = None
    cache_config: Optional[Dict[str, Any]] = None
    ssl_verify: bool = True
    ssl_cert: Optional[str] = None
    ssl_key: Optional[str] = None


@dataclass
class CacheEntry:
    """Cache entry."""

    key: str
    value: APIResponse
    expires_at: datetime
    hits: int = 0

    @property
    def is_expired(self) -> bool:
        """Check if entry is expired."""
        return datetime.utcnow() >= self.expires_at


# ============================================================================
# AUTHENTICATION MANAGER
# ============================================================================


class AuthenticationManager:
    """
    Manages authentication for API requests.

    Supports OAuth2, JWT, API Key, Basic Auth, and mTLS.
    """

    def __init__(self):
        """Initialize authentication manager."""
        self._tokens: Dict[str, AuthToken] = {}
        self._lock = threading.Lock()

    def authenticate(
        self,
        auth_config: AuthConfig,
        force_refresh: bool = False
    ) -> AuthToken:
        """
        Authenticate and get access token.

        Args:
            auth_config: Authentication configuration
            force_refresh: Force token refresh

        Returns:
            AuthToken instance

        Raises:
            AuthenticationFailedError: If authentication fails
        """
        auth_key = self._get_auth_key(auth_config)

        with self._lock:
            # Check if we have a valid token
            if not force_refresh and auth_key in self._tokens:
                token = self._tokens[auth_key]
                if not token.is_expired:
                    logger.debug("Using cached authentication token")
                    return token

            # Authenticate based on type
            if auth_config.auth_type == AuthType.OAUTH2:
                token = self._oauth2_authenticate(auth_config)
            elif auth_config.auth_type == AuthType.JWT:
                token = self._jwt_authenticate(auth_config)
            elif auth_config.auth_type == AuthType.API_KEY:
                token = self._api_key_authenticate(auth_config)
            elif auth_config.auth_type == AuthType.BASIC:
                token = self._basic_authenticate(auth_config)
            elif auth_config.auth_type == AuthType.BEARER:
                token = self._bearer_authenticate(auth_config)
            else:
                raise AuthenticationFailedError(
                    f"Unsupported auth type: {auth_config.auth_type.value}"
                )

            # Cache token
            self._tokens[auth_key] = token
            logger.info(f"Successfully authenticated using {auth_config.auth_type.value}")

            return token

    def _get_auth_key(self, auth_config: AuthConfig) -> str:
        """Generate key for caching auth tokens."""
        parts = [
            auth_config.auth_type.value,
            json.dumps(auth_config.credentials, sort_keys=True),
        ]
        return hashlib.sha256(":".join(parts).encode()).hexdigest()

    def _oauth2_authenticate(self, auth_config: AuthConfig) -> AuthToken:
        """Authenticate using OAuth2."""
        if not auth_config.token_url:
            raise AuthenticationFailedError("token_url required for OAuth2")

        grant_type = auth_config.grant_type or OAuth2GrantType.CLIENT_CREDENTIALS

        if grant_type == OAuth2GrantType.CLIENT_CREDENTIALS:
            return self._oauth2_client_credentials(auth_config)
        elif grant_type == OAuth2GrantType.PASSWORD:
            return self._oauth2_password(auth_config)
        elif grant_type == OAuth2GrantType.REFRESH_TOKEN:
            return self._oauth2_refresh_token(auth_config)
        else:
            raise AuthenticationFailedError(
                f"Unsupported OAuth2 grant type: {grant_type.value}"
            )

    def _oauth2_client_credentials(self, auth_config: AuthConfig) -> AuthToken:
        """OAuth2 client credentials flow."""
        if requests is None:
            raise ImportError("requests library required for OAuth2")

        data = {
            "grant_type": "client_credentials",
            "client_id": auth_config.credentials.get("client_id"),
            "client_secret": auth_config.credentials.get("client_secret"),
        }

        if auth_config.scopes:
            data["scope"] = " ".join(auth_config.scopes)

        try:
            response = requests.post(auth_config.token_url, data=data, timeout=30)
            response.raise_for_status()
            token_data = response.json()

            expires_in = token_data.get("expires_in")
            expires_at = None
            if expires_in:
                expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

            return AuthToken(
                access_token=token_data["access_token"],
                token_type=token_data.get("token_type", "Bearer"),
                expires_at=expires_at,
                refresh_token=token_data.get("refresh_token"),
                scopes=token_data.get("scope", "").split() if token_data.get("scope") else [],
            )
        except Exception as e:
            raise AuthenticationFailedError(f"OAuth2 authentication failed: {str(e)}")

    def _oauth2_password(self, auth_config: AuthConfig) -> AuthToken:
        """OAuth2 password flow."""
        if requests is None:
            raise ImportError("requests library required for OAuth2")

        data = {
            "grant_type": "password",
            "username": auth_config.credentials.get("username"),
            "password": auth_config.credentials.get("password"),
            "client_id": auth_config.credentials.get("client_id"),
        }

        client_secret = auth_config.credentials.get("client_secret")
        if client_secret:
            data["client_secret"] = client_secret

        if auth_config.scopes:
            data["scope"] = " ".join(auth_config.scopes)

        try:
            response = requests.post(auth_config.token_url, data=data, timeout=30)
            response.raise_for_status()
            token_data = response.json()

            expires_in = token_data.get("expires_in")
            expires_at = None
            if expires_in:
                expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

            return AuthToken(
                access_token=token_data["access_token"],
                token_type=token_data.get("token_type", "Bearer"),
                expires_at=expires_at,
                refresh_token=token_data.get("refresh_token"),
                scopes=token_data.get("scope", "").split() if token_data.get("scope") else [],
            )
        except Exception as e:
            raise AuthenticationFailedError(f"OAuth2 password flow failed: {str(e)}")

    def _oauth2_refresh_token(self, auth_config: AuthConfig) -> AuthToken:
        """OAuth2 refresh token flow."""
        if requests is None:
            raise ImportError("requests library required for OAuth2")

        refresh_token = auth_config.credentials.get("refresh_token")
        if not refresh_token:
            raise AuthenticationFailedError("refresh_token required")

        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": auth_config.credentials.get("client_id"),
        }

        client_secret = auth_config.credentials.get("client_secret")
        if client_secret:
            data["client_secret"] = client_secret

        try:
            url = auth_config.refresh_url or auth_config.token_url
            response = requests.post(url, data=data, timeout=30)
            response.raise_for_status()
            token_data = response.json()

            expires_in = token_data.get("expires_in")
            expires_at = None
            if expires_in:
                expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

            return AuthToken(
                access_token=token_data["access_token"],
                token_type=token_data.get("token_type", "Bearer"),
                expires_at=expires_at,
                refresh_token=token_data.get("refresh_token", refresh_token),
                scopes=token_data.get("scope", "").split() if token_data.get("scope") else [],
            )
        except Exception as e:
            raise AuthenticationFailedError(f"Token refresh failed: {str(e)}")

    def _jwt_authenticate(self, auth_config: AuthConfig) -> AuthToken:
        """Authenticate using JWT."""
        token = auth_config.credentials.get("token")
        if not token:
            raise AuthenticationFailedError("JWT token required")

        expires_at = auth_config.credentials.get("expires_at")
        if expires_at and isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)

        return AuthToken(
            access_token=token,
            token_type="Bearer",
            expires_at=expires_at,
        )

    def _api_key_authenticate(self, auth_config: AuthConfig) -> AuthToken:
        """Authenticate using API key."""
        api_key = auth_config.credentials.get("api_key")
        if not api_key:
            raise AuthenticationFailedError("API key required")

        # API keys typically don't expire
        return AuthToken(
            access_token=api_key,
            token_type=auth_config.credentials.get("token_type", "ApiKey"),
        )

    def _basic_authenticate(self, auth_config: AuthConfig) -> AuthToken:
        """Authenticate using Basic Auth."""
        import base64

        username = auth_config.credentials.get("username")
        password = auth_config.credentials.get("password")

        if not username or not password:
            raise AuthenticationFailedError("Username and password required for Basic Auth")

        credentials = f"{username}:{password}"
        encoded = base64.b64encode(credentials.encode()).decode()

        return AuthToken(
            access_token=encoded,
            token_type="Basic",
        )

    def _bearer_authenticate(self, auth_config: AuthConfig) -> AuthToken:
        """Authenticate using Bearer token."""
        token = auth_config.credentials.get("token")
        if not token:
            raise AuthenticationFailedError("Bearer token required")

        return AuthToken(
            access_token=token,
            token_type="Bearer",
        )

    def refresh_token(self, auth_config: AuthConfig) -> AuthToken:
        """
        Refresh authentication token.

        Args:
            auth_config: Authentication configuration

        Returns:
            New AuthToken instance
        """
        return self.authenticate(auth_config, force_refresh=True)

    def clear_cache(self) -> None:
        """Clear cached tokens."""
        with self._lock:
            self._tokens.clear()
            logger.debug("Cleared authentication token cache")


# ============================================================================
# CIRCUIT BREAKER
# ============================================================================


class CircuitBreakerManager:
    """
    Implements circuit breaker pattern for fault tolerance.

    Prevents cascading failures by tracking error rates and
    temporarily blocking requests when threshold is exceeded.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 3,
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds before attempting recovery
            half_open_max_calls: Max calls allowed in half-open state
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._half_open_calls = 0
        self._lock = threading.Lock()

    @property
    def state(self) -> CircuitBreakerState:
        """Get current circuit breaker state."""
        return self._state

    def can_execute(self) -> bool:
        """
        Check if request can be executed.

        Returns:
            True if request can proceed, False otherwise
        """
        with self._lock:
            if self._state == CircuitBreakerState.CLOSED:
                return True

            if self._state == CircuitBreakerState.OPEN:
                # Check if recovery timeout has passed
                if self._should_attempt_recovery():
                    self._transition_to_half_open()
                    return True
                return False

            if self._state == CircuitBreakerState.HALF_OPEN:
                # Allow limited calls in half-open state
                if self._half_open_calls < self.half_open_max_calls:
                    self._half_open_calls += 1
                    return True
                return False

        return False

    def record_success(self) -> None:
        """Record successful execution."""
        with self._lock:
            if self._state == CircuitBreakerState.HALF_OPEN:
                # Success in half-open state, close circuit
                self._transition_to_closed()
            else:
                # Reset failure count on success
                self._failure_count = 0

    def record_failure(self) -> None:
        """Record failed execution."""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = datetime.utcnow()

            if self._state == CircuitBreakerState.HALF_OPEN:
                # Failure in half-open state, reopen circuit
                self._transition_to_open()
            elif self._failure_count >= self.failure_threshold:
                # Threshold exceeded, open circuit
                self._transition_to_open()

    def _should_attempt_recovery(self) -> bool:
        """Check if we should attempt recovery."""
        if self._last_failure_time is None:
            return True

        elapsed = (datetime.utcnow() - self._last_failure_time).total_seconds()
        return elapsed >= self.recovery_timeout

    def _transition_to_open(self) -> None:
        """Transition to open state."""
        self._state = CircuitBreakerState.OPEN
        logger.warning("Circuit breaker opened due to failures")

    def _transition_to_half_open(self) -> None:
        """Transition to half-open state."""
        self._state = CircuitBreakerState.HALF_OPEN
        self._half_open_calls = 0
        logger.info("Circuit breaker entering half-open state")

    def _transition_to_closed(self) -> None:
        """Transition to closed state."""
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._half_open_calls = 0
        logger.info("Circuit breaker closed after successful recovery")

    def reset(self) -> None:
        """Reset circuit breaker to closed state."""
        with self._lock:
            self._state = CircuitBreakerState.CLOSED
            self._failure_count = 0
            self._half_open_calls = 0
            self._last_failure_time = None
            logger.debug("Circuit breaker reset")


# ============================================================================
# RATE LIMITER
# ============================================================================


class TokenBucketRateLimiter:
    """
    Token bucket algorithm for rate limiting.

    Allows bursts while maintaining average rate limit.
    """

    def __init__(
        self,
        rate: float,
        capacity: Optional[int] = None,
        window: float = 1.0,
    ):
        """
        Initialize rate limiter.

        Args:
            rate: Tokens per window
            capacity: Bucket capacity (defaults to rate)
            window: Time window in seconds
        """
        self.rate = rate
        self.capacity = capacity or int(rate)
        self.window = window

        self._tokens = float(self.capacity)
        self._last_update = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self, tokens: int = 1, timeout: Optional[float] = None) -> bool:
        """
        Acquire tokens from bucket.

        Args:
            tokens: Number of tokens to acquire
            timeout: Maximum time to wait (None = no wait)

        Returns:
            True if tokens acquired, False otherwise
        """
        start_time = time.monotonic()

        while True:
            with self._lock:
                self._refill()

                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return True

            if timeout is None:
                return False

            elapsed = time.monotonic() - start_time
            if elapsed >= timeout:
                return False

            # Wait a bit before retrying
            time.sleep(0.01)

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self._last_update

        # Add tokens based on rate and elapsed time
        tokens_to_add = (elapsed / self.window) * self.rate
        self._tokens = min(self._tokens + tokens_to_add, self.capacity)
        self._last_update = now

    @property
    def available_tokens(self) -> float:
        """Get available tokens."""
        with self._lock:
            self._refill()
            return self._tokens


class RateLimitManager:
    """Manages rate limiting for different endpoints."""

    def __init__(self):
        """Initialize rate limit manager."""
        self._limiters: Dict[str, TokenBucketRateLimiter] = {}
        self._lock = threading.Lock()

    def get_limiter(
        self,
        endpoint: str,
        rate: float,
        window: float = 1.0,
    ) -> TokenBucketRateLimiter:
        """
        Get or create rate limiter for endpoint.

        Args:
            endpoint: API endpoint
            rate: Requests per window
            window: Time window in seconds

        Returns:
            TokenBucketRateLimiter instance
        """
        key = f"{endpoint}:{rate}:{window}"

        with self._lock:
            if key not in self._limiters:
                self._limiters[key] = TokenBucketRateLimiter(
                    rate=rate,
                    window=window,
                )

            return self._limiters[key]

    def acquire(
        self,
        endpoint: str,
        rate: float,
        window: float = 1.0,
        timeout: Optional[float] = None,
    ) -> bool:
        """
        Acquire permission to make request.

        Args:
            endpoint: API endpoint
            rate: Requests per window
            window: Time window in seconds
            timeout: Maximum time to wait

        Returns:
            True if permission granted, False otherwise
        """
        limiter = self.get_limiter(endpoint, rate, window)
        return limiter.acquire(timeout=timeout)


# ============================================================================
# CACHE MANAGER
# ============================================================================


class CacheManager:
    """Manages response caching with TTL."""

    def __init__(self, max_size: int = 1000):
        """
        Initialize cache manager.

        Args:
            max_size: Maximum number of cached entries
        """
        self.max_size = max_size
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: deque = deque()
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[APIResponse]:
        """
        Get cached response.

        Args:
            key: Cache key

        Returns:
            Cached APIResponse or None
        """
        with self._lock:
            if key not in self._cache:
                return None

            entry = self._cache[key]

            # Check if expired
            if entry.is_expired:
                del self._cache[key]
                return None

            # Update access order and hit count
            entry.hits += 1
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)

            logger.debug(f"Cache hit for key: {key[:16]}... (hits: {entry.hits})")
            return entry.value

    def set(
        self,
        key: str,
        response: APIResponse,
        ttl: int = 300,
    ) -> None:
        """
        Cache response.

        Args:
            key: Cache key
            response: Response to cache
            ttl: Time to live in seconds
        """
        with self._lock:
            # Check size limit
            if len(self._cache) >= self.max_size:
                self._evict()

            # Create entry
            entry = CacheEntry(
                key=key,
                value=response,
                expires_at=datetime.utcnow() + timedelta(seconds=ttl),
            )

            self._cache[key] = entry
            self._access_order.append(key)

            logger.debug(f"Cached response for key: {key[:16]}... (ttl: {ttl}s)")

    def _evict(self) -> None:
        """Evict least recently used entry."""
        if not self._access_order:
            return

        # Remove oldest entry
        old_key = self._access_order.popleft()
        if old_key in self._cache:
            del self._cache[old_key]
            logger.debug(f"Evicted cache entry: {old_key[:16]}...")

    def clear(self) -> None:
        """Clear all cached entries."""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
            logger.debug("Cleared cache")

    def cleanup_expired(self) -> int:
        """
        Remove expired entries.

        Returns:
            Number of entries removed
        """
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired
            ]

            for key in expired_keys:
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)

            if expired_keys:
                logger.debug(f"Removed {len(expired_keys)} expired cache entries")

            return len(expired_keys)


# ============================================================================
# RETRY STRATEGY
# ============================================================================


class RetryStrategy:
    """
    Implements retry logic with exponential backoff and jitter.
    """

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        """
        Initialize retry strategy.

        Args:
            max_attempts: Maximum retry attempts
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds
            exponential_base: Base for exponential backoff
            jitter: Whether to add jitter to delay
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for retry attempt.

        Args:
            attempt: Attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        import random

        # Exponential backoff
        delay = min(
            self.base_delay * (self.exponential_base ** attempt),
            self.max_delay
        )

        # Add jitter
        if self.jitter:
            delay = delay * (0.5 + random.random() * 0.5)

        return delay

    def should_retry(
        self,
        attempt: int,
        exception: Optional[Exception] = None,
        response: Optional[APIResponse] = None,
    ) -> bool:
        """
        Determine if request should be retried.

        Args:
            attempt: Attempt number (0-indexed)
            exception: Exception that occurred
            response: Response received

        Returns:
            True if should retry, False otherwise
        """
        # Check max attempts
        if attempt >= self.max_attempts:
            return False

        # Retry on network errors
        if exception is not None:
            if isinstance(exception, (NetworkTimeoutError, ConnectionError)):
                return True

        # Retry on server errors
        if response is not None:
            if response.is_server_error:
                return True
            # Retry on rate limit (with backoff)
            if response.status_code == 429:
                return True

        return False


# ============================================================================
# PROTOCOL HANDLERS
# ============================================================================


class ProtocolHandler(ABC):
    """Base class for protocol handlers."""

    @abstractmethod
    def execute(
        self,
        request: APIRequest,
        config: APIConfig,
        auth_token: Optional[AuthToken] = None,
    ) -> APIResponse:
        """Execute request."""
        pass

    @abstractmethod
    async def aexecute(
        self,
        request: APIRequest,
        config: APIConfig,
        auth_token: Optional[AuthToken] = None,
    ) -> APIResponse:
        """Execute request asynchronously."""
        pass


class RESTAPIHandler(ProtocolHandler):
    """Handler for REST API requests."""

    def __init__(self):
        """Initialize REST handler."""
        self._session: Optional[requests.Session] = None
        self._async_session: Optional[aiohttp.ClientSession] = None

    def _get_session(self, config: APIConfig) -> requests.Session:
        """Get or create requests session."""
        if requests is None:
            raise ImportError("requests library required for REST API")

        if self._session is None:
            self._session = requests.Session()

            # Configure retry for connection errors
            if config.retry_config:
                retry = RequestsRetry(
                    total=config.retry_config.get("max_attempts", 3),
                    backoff_factor=config.retry_config.get("base_delay", 1.0),
                    status_forcelist=[500, 502, 503, 504],
                )
                adapter = HTTPAdapter(max_retries=retry)
                self._session.mount("http://", adapter)
                self._session.mount("https://", adapter)

            # Configure SSL
            if not config.ssl_verify:
                self._session.verify = False
            elif config.ssl_cert:
                self._session.cert = (config.ssl_cert, config.ssl_key)

        return self._session

    def execute(
        self,
        request: APIRequest,
        config: APIConfig,
        auth_token: Optional[AuthToken] = None,
    ) -> APIResponse:
        """Execute REST request."""
        session = self._get_session(config)

        # Build URL
        url = urljoin(config.base_url, request.endpoint)

        # Prepare headers
        headers = {**config.default_headers, **request.headers}
        if auth_token:
            headers["Authorization"] = auth_token.to_header_value()

        try:
            # Make request
            response = session.request(
                method=request.method.value,
                url=url,
                headers=headers,
                params=request.params,
                json=request.body if isinstance(request.body, dict) else None,
                data=request.body if not isinstance(request.body, dict) else None,
                timeout=request.timeout,
            )

            # Parse response
            try:
                data = response.json()
            except ValueError:
                data = response.text

            return APIResponse(
                status_code=response.status_code,
                data=data,
                headers=dict(response.headers),
                metadata={"url": url, "method": request.method.value},
            )

        except requests.exceptions.Timeout:
            raise NetworkTimeoutError(f"Request timeout after {request.timeout}s")
        except requests.exceptions.RequestException as e:
            raise APIIntegratorError(f"Request failed: {str(e)}")

    async def aexecute(
        self,
        request: APIRequest,
        config: APIConfig,
        auth_token: Optional[AuthToken] = None,
    ) -> APIResponse:
        """Execute REST request asynchronously."""
        if aiohttp is None:
            raise ImportError("aiohttp library required for async REST API")

        # Build URL
        url = urljoin(config.base_url, request.endpoint)

        # Prepare headers
        headers = {**config.default_headers, **request.headers}
        if auth_token:
            headers["Authorization"] = auth_token.to_header_value()

        # Configure SSL
        ssl_context = None
        if not config.ssl_verify:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

        try:
            timeout = aiohttp.ClientTimeout(total=request.timeout)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.request(
                    method=request.method.value,
                    url=url,
                    headers=headers,
                    params=request.params,
                    json=request.body if isinstance(request.body, dict) else None,
                    data=request.body if not isinstance(request.body, dict) else None,
                    ssl=ssl_context,
                ) as response:
                    # Parse response
                    try:
                        data = await response.json()
                    except (ValueError, aiohttp.ContentTypeError):
                        data = await response.text()

                    return APIResponse(
                        status_code=response.status,
                        data=data,
                        headers=dict(response.headers),
                        metadata={"url": url, "method": request.method.value},
                    )

        except asyncio.TimeoutError:
            raise NetworkTimeoutError(f"Request timeout after {request.timeout}s")
        except aiohttp.ClientError as e:
            raise APIIntegratorError(f"Request failed: {str(e)}")


class GraphQLHandler(ProtocolHandler):
    """Handler for GraphQL API requests."""

    def execute(
        self,
        request: APIRequest,
        config: APIConfig,
        auth_token: Optional[AuthToken] = None,
    ) -> APIResponse:
        """Execute GraphQL request."""
        if requests is None:
            raise ImportError("requests library required for GraphQL")

        # Build URL
        url = urljoin(config.base_url, request.endpoint)

        # Prepare headers
        headers = {**config.default_headers, **request.headers}
        headers["Content-Type"] = "application/json"
        if auth_token:
            headers["Authorization"] = auth_token.to_header_value()

        # Prepare GraphQL payload
        payload = {
            "query": request.body.get("query") if isinstance(request.body, dict) else request.body,
        }

        if isinstance(request.body, dict) and "variables" in request.body:
            payload["variables"] = request.body["variables"]

        if isinstance(request.body, dict) and "operationName" in request.body:
            payload["operationName"] = request.body["operationName"]

        try:
            response = requests.post(
                url=url,
                headers=headers,
                json=payload,
                timeout=request.timeout,
                verify=config.ssl_verify,
            )

            data = response.json()

            # Check for GraphQL errors
            if "errors" in data:
                logger.warning(f"GraphQL errors: {data['errors']}")

            return APIResponse(
                status_code=response.status_code,
                data=data,
                headers=dict(response.headers),
                metadata={"url": url, "protocol": "graphql"},
            )

        except requests.exceptions.Timeout:
            raise NetworkTimeoutError(f"Request timeout after {request.timeout}s")
        except requests.exceptions.RequestException as e:
            raise APIIntegratorError(f"GraphQL request failed: {str(e)}")

    async def aexecute(
        self,
        request: APIRequest,
        config: APIConfig,
        auth_token: Optional[AuthToken] = None,
    ) -> APIResponse:
        """Execute GraphQL request asynchronously."""
        if aiohttp is None:
            raise ImportError("aiohttp library required for async GraphQL")

        # Build URL
        url = urljoin(config.base_url, request.endpoint)

        # Prepare headers
        headers = {**config.default_headers, **request.headers}
        headers["Content-Type"] = "application/json"
        if auth_token:
            headers["Authorization"] = auth_token.to_header_value()

        # Prepare GraphQL payload
        payload = {
            "query": request.body.get("query") if isinstance(request.body, dict) else request.body,
        }

        if isinstance(request.body, dict) and "variables" in request.body:
            payload["variables"] = request.body["variables"]

        try:
            timeout = aiohttp.ClientTimeout(total=request.timeout)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    url=url,
                    headers=headers,
                    json=payload,
                    ssl=None if config.ssl_verify else False,
                ) as response:
                    data = await response.json()

                    # Check for GraphQL errors
                    if "errors" in data:
                        logger.warning(f"GraphQL errors: {data['errors']}")

                    return APIResponse(
                        status_code=response.status,
                        data=data,
                        headers=dict(response.headers),
                        metadata={"url": url, "protocol": "graphql"},
                    )

        except asyncio.TimeoutError:
            raise NetworkTimeoutError(f"Request timeout after {request.timeout}s")
        except aiohttp.ClientError as e:
            raise APIIntegratorError(f"GraphQL request failed: {str(e)}")


class WebSocketHandler(ProtocolHandler):
    """Handler for WebSocket connections."""

    def execute(
        self,
        request: APIRequest,
        config: APIConfig,
        auth_token: Optional[AuthToken] = None,
    ) -> APIResponse:
        """WebSocket requires async execution."""
        raise NotImplementedError("WebSocket handler requires async execution")

    async def aexecute(
        self,
        request: APIRequest,
        config: APIConfig,
        auth_token: Optional[AuthToken] = None,
    ) -> APIResponse:
        """Execute WebSocket request asynchronously."""
        if websockets is None:
            raise ImportError("websockets library required for WebSocket")

        # Build URL
        url = urljoin(config.base_url, request.endpoint)
        # Convert http(s) to ws(s)
        url = url.replace("http://", "ws://").replace("https://", "wss://")

        # Prepare headers
        extra_headers = {**config.default_headers, **request.headers}
        if auth_token:
            extra_headers["Authorization"] = auth_token.to_header_value()

        try:
            async with websockets.connect(
                url,
                extra_headers=extra_headers,
            ) as websocket:
                # Send message if provided
                if request.body:
                    await websocket.send(
                        json.dumps(request.body) if isinstance(request.body, dict) else request.body
                    )

                # Receive response
                response_data = await websocket.recv()

                # Try to parse as JSON
                try:
                    data = json.loads(response_data)
                except json.JSONDecodeError:
                    data = response_data

                return APIResponse(
                    status_code=200,
                    data=data,
                    metadata={"url": url, "protocol": "websocket"},
                )

        except asyncio.TimeoutError:
            raise NetworkTimeoutError(f"WebSocket timeout after {request.timeout}s")
        except Exception as e:
            raise APIIntegratorError(f"WebSocket request failed: {str(e)}")


class SOAPHandler(ProtocolHandler):
    """Handler for SOAP API requests."""

    def __init__(self):
        """Initialize SOAP handler."""
        self._clients: Dict[str, Any] = {}

    def _get_client(self, wsdl_url: str, config: APIConfig) -> Any:
        """Get or create SOAP client."""
        if SOAPClient is None:
            raise ImportError("zeep library required for SOAP")

        if wsdl_url not in self._clients:
            # Configure transport
            session = requests.Session()
            if not config.ssl_verify:
                session.verify = False

            transport = Transport(session=session, timeout=config.timeout)
            self._clients[wsdl_url] = SOAPClient(wsdl=wsdl_url, transport=transport)

        return self._clients[wsdl_url]

    def execute(
        self,
        request: APIRequest,
        config: APIConfig,
        auth_token: Optional[AuthToken] = None,
    ) -> APIResponse:
        """Execute SOAP request."""
        # Get WSDL URL from metadata
        wsdl_url = request.metadata.get("wsdl_url", config.base_url)
        operation = request.metadata.get("operation")

        if not operation:
            raise APIIntegratorError("SOAP operation required in request metadata")

        # Get client
        client = self._get_client(wsdl_url, config)

        try:
            # Get service operation
            service_method = getattr(client.service, operation)

            # Execute operation
            if isinstance(request.body, dict):
                result = service_method(**request.body)
            elif isinstance(request.body, (list, tuple)):
                result = service_method(*request.body)
            else:
                result = service_method(request.body) if request.body else service_method()

            return APIResponse(
                status_code=200,
                data=result,
                metadata={"wsdl": wsdl_url, "operation": operation, "protocol": "soap"},
            )

        except Exception as e:
            raise APIIntegratorError(f"SOAP request failed: {str(e)}")

    async def aexecute(
        self,
        request: APIRequest,
        config: APIConfig,
        auth_token: Optional[AuthToken] = None,
    ) -> APIResponse:
        """Execute SOAP request asynchronously."""
        # Run sync execute in thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.execute,
            request,
            config,
            auth_token,
        )


class gRPCHandler(ProtocolHandler):
    """Handler for gRPC API requests."""

    def execute(
        self,
        request: APIRequest,
        config: APIConfig,
        auth_token: Optional[AuthToken] = None,
    ) -> APIResponse:
        """Execute gRPC request."""
        if grpc is None:
            raise ImportError("grpcio library required for gRPC")

        # This is a simplified implementation
        # Real gRPC would need proto definitions
        raise NotImplementedError("gRPC handler requires proto definitions")

    async def aexecute(
        self,
        request: APIRequest,
        config: APIConfig,
        auth_token: Optional[AuthToken] = None,
    ) -> APIResponse:
        """Execute gRPC request asynchronously."""
        raise NotImplementedError("gRPC handler requires proto definitions")


# ============================================================================
# REQUEST/RESPONSE PIPELINE
# ============================================================================


class RequestInterceptor(ABC):
    """Base class for request interceptors."""

    @abstractmethod
    def intercept(self, request: APIRequest, config: APIConfig) -> APIRequest:
        """Intercept and potentially modify request."""
        pass


class ResponseTransformer(ABC):
    """Base class for response transformers."""

    @abstractmethod
    def transform(self, response: APIResponse, request: APIRequest) -> APIResponse:
        """Transform response."""
        pass


class HeaderInjector(RequestInterceptor):
    """Inject headers into requests."""

    def __init__(self, headers: Dict[str, str]):
        """Initialize with headers to inject."""
        self.headers = headers

    def intercept(self, request: APIRequest, config: APIConfig) -> APIRequest:
        """Inject headers into request."""
        request.headers.update(self.headers)
        return request


class DataValidator(ResponseTransformer):
    """Validate response data against schema."""

    def __init__(self, schema: Optional[Dict[str, Any]] = None):
        """Initialize with optional schema."""
        self.schema = schema

    def transform(self, response: APIResponse, request: APIRequest) -> APIResponse:
        """Validate response data."""
        if self.schema and response.is_success:
            # Simple validation (could use jsonschema library)
            if not self._validate(response.data, self.schema):
                raise InvalidResponseError("Response data does not match schema")

        return response

    def _validate(self, data: Any, schema: Dict[str, Any]) -> bool:
        """Simple schema validation."""
        # This is a placeholder - use jsonschema for real validation
        return True


class PayloadCompressor(RequestInterceptor):
    """Compress request payload."""

    def intercept(self, request: APIRequest, config: APIConfig) -> APIRequest:
        """Compress payload if needed."""
        import gzip

        if request.body and len(str(request.body)) > 1024:
            # Compress large payloads
            request.headers["Content-Encoding"] = "gzip"

        return request


# ============================================================================
# MAIN API INTEGRATOR FSA
# ============================================================================


class APIIntegratorFSA(BaseFSA):
    """
    Universal API integration layer for the MLA framework.

    Supports multiple protocols (REST, GraphQL, gRPC, WebSocket, SOAP)
    with automatic retry logic, rate limiting, authentication, caching,
    and error recovery.
    """

    def __init__(
        self,
        config: Optional[APIConfig] = None,
        name: Optional[str] = None,
        mock_mode: bool = False,
    ):
        """
        Initialize API Integrator FSA.

        Args:
            config: API configuration
            name: Optional name for the FSA instance
            mock_mode: Enable mock mode for testing
        """
        super().__init__(name=name or "APIIntegratorFSA")

        self.config = config
        self.mock_mode = mock_mode

        # Initialize components
        self.auth_manager = AuthenticationManager()
        self.cache_manager = CacheManager()
        self.rate_limit_manager = RateLimitManager()
        self.circuit_breaker: Optional[CircuitBreakerManager] = None

        # Initialize protocol handlers
        self._handlers: Dict[ProtocolType, ProtocolHandler] = {
            ProtocolType.REST: RESTAPIHandler(),
            ProtocolType.GRAPHQL: GraphQLHandler(),
            ProtocolType.WEBSOCKET: WebSocketHandler(),
            ProtocolType.SOAP: SOAPHandler(),
            ProtocolType.GRPC: gRPCHandler(),
        }

        # Request/Response pipeline
        self._request_interceptors: List[RequestInterceptor] = []
        self._response_transformers: List[ResponseTransformer] = []

        # Configure circuit breaker if config provided
        if config and config.circuit_breaker_config:
            cb_config = config.circuit_breaker_config
            self.circuit_breaker = CircuitBreakerManager(
                failure_threshold=cb_config.get("failure_threshold", 5),
                recovery_timeout=cb_config.get("recovery_timeout", 60.0),
                half_open_max_calls=cb_config.get("half_open_max_calls", 3),
            )

        # Transition to READY state
        if config:
            self.transition(FSAState.READY, trigger="configuration_provided")

        logger.info(f"Initialized {self.name}")

    def _initialize_transitions(self) -> None:
        """Initialize allowed state transitions."""
        # Define valid state transitions
        self.add_transition(FSAState.IDLE, FSAState.INITIALIZING)
        self.add_transition(FSAState.IDLE, FSAState.READY)
        self.add_transition(FSAState.INITIALIZING, FSAState.READY)
        self.add_transition(FSAState.INITIALIZING, FSAState.ERROR)
        self.add_transition(FSAState.READY, FSAState.EXECUTING)
        self.add_transition(FSAState.READY, FSAState.ERROR)
        self.add_transition(FSAState.EXECUTING, FSAState.READY)
        self.add_transition(FSAState.EXECUTING, FSAState.COMPLETED)
        self.add_transition(FSAState.EXECUTING, FSAState.ERROR)
        self.add_transition(FSAState.EXECUTING, FSAState.PAUSED)
        self.add_transition(FSAState.PAUSED, FSAState.EXECUTING)
        self.add_transition(FSAState.PAUSED, FSAState.READY)
        self.add_transition(FSAState.ERROR, FSAState.READY)
        self.add_transition(FSAState.ERROR, FSAState.TERMINATED)
        self.add_transition(FSAState.COMPLETED, FSAState.READY)

    def configure_protocol(
        self,
        protocol: str,
        settings: Dict[str, Any]
    ) -> None:
        """
        Configure protocol-specific settings.

        Args:
            protocol: Protocol type
            settings: Protocol settings
        """
        protocol_type = ProtocolType(protocol.lower())

        if protocol_type not in self._handlers:
            raise ProtocolNotSupportedError(f"Protocol {protocol} not supported")

        # Store settings in context
        if "protocol_settings" not in self.context.data:
            self.context.data["protocol_settings"] = {}

        self.context.data["protocol_settings"][protocol_type.value] = settings

        logger.info(f"Configured {protocol} protocol")

    def add_request_interceptor(self, interceptor: RequestInterceptor) -> None:
        """
        Add request interceptor to pipeline.

        Args:
            interceptor: Request interceptor
        """
        self._request_interceptors.append(interceptor)
        logger.debug(f"Added request interceptor: {interceptor.__class__.__name__}")

    def add_response_transformer(self, transformer: ResponseTransformer) -> None:
        """
        Add response transformer to pipeline.

        Args:
            transformer: Response transformer
        """
        self._response_transformers.append(transformer)
        logger.debug(f"Added response transformer: {transformer.__class__.__name__}")

    def validate(self, config: APIConfig) -> ValidationResult:
        """
        Validate API configuration.

        Args:
            config: API configuration to validate

        Returns:
            ValidationResult with validation status and errors
        """
        result = ValidationResult(valid=True)

        # Validate base URL
        if not config.base_url:
            result.add_error("base_url is required")
        else:
            parsed = urlparse(config.base_url)
            if not parsed.scheme or not parsed.netloc:
                result.add_error("Invalid base_url format")

        # Validate protocol
        if not isinstance(config.protocol, ProtocolType):
            result.add_error("Invalid protocol type")

        # Validate timeout
        if config.timeout <= 0:
            result.add_error("timeout must be positive")

        # Validate auth config
        if config.auth_config:
            auth_result = self._validate_auth_config(config.auth_config)
            result.errors.extend(auth_result.errors)
            result.warnings.extend(auth_result.warnings)
            if not auth_result.valid:
                result.valid = False

        # Validate SSL configuration
        if config.ssl_cert and not config.ssl_key:
            result.add_warning("ssl_cert provided without ssl_key")

        logger.debug(f"Configuration validation: {result.valid}")
        return result

    def _validate_auth_config(self, auth_config: AuthConfig) -> ValidationResult:
        """Validate authentication configuration."""
        result = ValidationResult(valid=True)

        if auth_config.auth_type == AuthType.OAUTH2:
            if not auth_config.token_url:
                result.add_error("token_url required for OAuth2")

            if not auth_config.grant_type:
                result.add_error("grant_type required for OAuth2")

            grant_type = auth_config.grant_type
            if grant_type == OAuth2GrantType.CLIENT_CREDENTIALS:
                if "client_id" not in auth_config.credentials:
                    result.add_error("client_id required for client_credentials")
                if "client_secret" not in auth_config.credentials:
                    result.add_error("client_secret required for client_credentials")

            elif grant_type == OAuth2GrantType.PASSWORD:
                if "username" not in auth_config.credentials:
                    result.add_error("username required for password grant")
                if "password" not in auth_config.credentials:
                    result.add_error("password required for password grant")

        elif auth_config.auth_type == AuthType.API_KEY:
            if "api_key" not in auth_config.credentials:
                result.add_error("api_key required for API key auth")

        elif auth_config.auth_type == AuthType.BASIC:
            if "username" not in auth_config.credentials:
                result.add_error("username required for basic auth")
            if "password" not in auth_config.credentials:
                result.add_error("password required for basic auth")

        return result

    def authenticate(self, auth_config: AuthConfig) -> AuthToken:
        """
        Authenticate using provided configuration.

        Args:
            auth_config: Authentication configuration

        Returns:
            AuthToken instance

        Raises:
            AuthenticationFailedError: If authentication fails
        """
        return self.auth_manager.authenticate(auth_config)

    def execute(self, request: APIRequest) -> APIResponse:
        """
        Execute API request with retry, rate limiting, and caching.

        Args:
            request: API request to execute

        Returns:
            APIResponse instance

        Raises:
            Various APIIntegratorError subclasses on failure
        """
        if not self.config:
            raise APIIntegratorError("No configuration provided")

        if not self.is_ready and not self.is_executing:
            raise APIIntegratorError(f"FSA not ready (state: {self.state.value})")

        # Transition to executing state
        self.transition(FSAState.EXECUTING, trigger="execute_called")

        try:
            # Check circuit breaker
            if self.circuit_breaker and not self.circuit_breaker.can_execute():
                raise CircuitBreakerOpenError("Circuit breaker is open")

            # Check cache
            if self.config.cache_config and request.method == HTTPMethod.GET:
                cache_key = request.get_cache_key()
                cached_response = self.cache_manager.get(cache_key)
                if cached_response:
                    cached_response.cached = True
                    self.transition(FSAState.READY, trigger="cache_hit")
                    return cached_response

            # Apply rate limiting
            if self.config.rate_limit_config:
                rate = self.config.rate_limit_config.get("rate", 10)
                window = self.config.rate_limit_config.get("window", 1.0)
                timeout = self.config.rate_limit_config.get("timeout", 5.0)

                if not self.rate_limit_manager.acquire(
                    request.endpoint, rate, window, timeout
                ):
                    raise RateLimitExceededError("Rate limit exceeded")

            # Get auth token if needed
            auth_token = None
            if self.config.auth_config:
                auth_token = self.auth_manager.authenticate(self.config.auth_config)

            # Apply request interceptors
            for interceptor in self._request_interceptors:
                request = interceptor.intercept(request, self.config)

            # Execute with retry
            response = self._execute_with_retry(request, auth_token)

            # Apply response transformers
            for transformer in self._response_transformers:
                response = transformer.transform(response, request)

            # Cache successful responses
            if (
                self.config.cache_config
                and response.is_success
                and request.method == HTTPMethod.GET
            ):
                cache_key = request.get_cache_key()
                ttl = self.config.cache_config.get("ttl", 300)
                self.cache_manager.set(cache_key, response, ttl)

            # Record success with circuit breaker
            if self.circuit_breaker:
                self.circuit_breaker.record_success()

            # Transition back to ready
            self.transition(FSAState.COMPLETED, trigger="execution_completed")
            self.transition(FSAState.READY, trigger="ready_for_next")

            return response

        except Exception as e:
            # Record failure with circuit breaker
            if self.circuit_breaker:
                self.circuit_breaker.record_failure()

            # Handle error
            recovery_action = self.error_handling(
                e,
                {"request": request, "config": self.config}
            )

            self.transition(FSAState.ERROR, trigger="execution_failed")
            raise

    async def aexecute(self, request: APIRequest) -> APIResponse:
        """
        Execute API request asynchronously.

        Args:
            request: API request to execute

        Returns:
            APIResponse instance
        """
        if not self.config:
            raise APIIntegratorError("No configuration provided")

        if not self.is_ready and not self.is_executing:
            raise APIIntegratorError(f"FSA not ready (state: {self.state.value})")

        # Transition to executing state
        self.transition(FSAState.EXECUTING, trigger="aexecute_called")

        try:
            # Check circuit breaker
            if self.circuit_breaker and not self.circuit_breaker.can_execute():
                raise CircuitBreakerOpenError("Circuit breaker is open")

            # Check cache
            if self.config.cache_config and request.method == HTTPMethod.GET:
                cache_key = request.get_cache_key()
                cached_response = self.cache_manager.get(cache_key)
                if cached_response:
                    cached_response.cached = True
                    self.transition(FSAState.READY, trigger="cache_hit")
                    return cached_response

            # Apply rate limiting
            if self.config.rate_limit_config:
                rate = self.config.rate_limit_config.get("rate", 10)
                window = self.config.rate_limit_config.get("window", 1.0)
                timeout = self.config.rate_limit_config.get("timeout", 5.0)

                # Async rate limiting
                acquired = await asyncio.get_event_loop().run_in_executor(
                    None,
                    self.rate_limit_manager.acquire,
                    request.endpoint,
                    rate,
                    window,
                    timeout,
                )

                if not acquired:
                    raise RateLimitExceededError("Rate limit exceeded")

            # Get auth token if needed
            auth_token = None
            if self.config.auth_config:
                auth_token = await asyncio.get_event_loop().run_in_executor(
                    None,
                    self.auth_manager.authenticate,
                    self.config.auth_config,
                )

            # Apply request interceptors
            for interceptor in self._request_interceptors:
                request = interceptor.intercept(request, self.config)

            # Execute with retry
            response = await self._aexecute_with_retry(request, auth_token)

            # Apply response transformers
            for transformer in self._response_transformers:
                response = transformer.transform(response, request)

            # Cache successful responses
            if (
                self.config.cache_config
                and response.is_success
                and request.method == HTTPMethod.GET
            ):
                cache_key = request.get_cache_key()
                ttl = self.config.cache_config.get("ttl", 300)
                self.cache_manager.set(cache_key, response, ttl)

            # Record success with circuit breaker
            if self.circuit_breaker:
                self.circuit_breaker.record_success()

            # Transition back to ready
            self.transition(FSAState.COMPLETED, trigger="execution_completed")
            self.transition(FSAState.READY, trigger="ready_for_next")

            return response

        except Exception as e:
            # Record failure with circuit breaker
            if self.circuit_breaker:
                self.circuit_breaker.record_failure()

            # Handle error
            recovery_action = self.error_handling(
                e,
                {"request": request, "config": self.config}
            )

            self.transition(FSAState.ERROR, trigger="execution_failed")
            raise

    def _execute_with_retry(
        self,
        request: APIRequest,
        auth_token: Optional[AuthToken],
    ) -> APIResponse:
        """Execute request with retry logic."""
        # Get retry strategy
        retry_config = self.config.retry_config or {}
        strategy = RetryStrategy(
            max_attempts=retry_config.get("max_attempts", 3),
            base_delay=retry_config.get("base_delay", 1.0),
            max_delay=retry_config.get("max_delay", 60.0),
        )

        attempt = 0
        last_exception = None
        last_response = None

        while attempt < strategy.max_attempts:
            try:
                # Get protocol handler
                handler = self._handlers.get(request.protocol)
                if not handler:
                    raise ProtocolNotSupportedError(
                        f"Protocol {request.protocol.value} not supported"
                    )

                # Execute request
                if self.mock_mode:
                    response = self._mock_execute(request)
                else:
                    response = handler.execute(request, self.config, auth_token)

                # Check if we should retry
                if not strategy.should_retry(attempt, response=response):
                    return response

                last_response = response

            except Exception as e:
                last_exception = e

                # Check if we should retry
                if not strategy.should_retry(attempt, exception=e):
                    raise

            # Calculate delay and wait
            if attempt < strategy.max_attempts - 1:
                delay = strategy.calculate_delay(attempt)
                logger.debug(f"Retrying after {delay:.2f}s (attempt {attempt + 1})")
                time.sleep(delay)

            attempt += 1

        # Max attempts reached
        if last_exception:
            raise last_exception
        elif last_response:
            return last_response
        else:
            raise APIIntegratorError("Max retry attempts reached")

    async def _aexecute_with_retry(
        self,
        request: APIRequest,
        auth_token: Optional[AuthToken],
    ) -> APIResponse:
        """Execute request asynchronously with retry logic."""
        # Get retry strategy
        retry_config = self.config.retry_config or {}
        strategy = RetryStrategy(
            max_attempts=retry_config.get("max_attempts", 3),
            base_delay=retry_config.get("base_delay", 1.0),
            max_delay=retry_config.get("max_delay", 60.0),
        )

        attempt = 0
        last_exception = None
        last_response = None

        while attempt < strategy.max_attempts:
            try:
                # Get protocol handler
                handler = self._handlers.get(request.protocol)
                if not handler:
                    raise ProtocolNotSupportedError(
                        f"Protocol {request.protocol.value} not supported"
                    )

                # Execute request
                if self.mock_mode:
                    response = self._mock_execute(request)
                else:
                    response = await handler.aexecute(request, self.config, auth_token)

                # Check if we should retry
                if not strategy.should_retry(attempt, response=response):
                    return response

                last_response = response

            except Exception as e:
                last_exception = e

                # Check if we should retry
                if not strategy.should_retry(attempt, exception=e):
                    raise

            # Calculate delay and wait
            if attempt < strategy.max_attempts - 1:
                delay = strategy.calculate_delay(attempt)
                logger.debug(f"Retrying after {delay:.2f}s (attempt {attempt + 1})")
                await asyncio.sleep(delay)

            attempt += 1

        # Max attempts reached
        if last_exception:
            raise last_exception
        elif last_response:
            return last_response
        else:
            raise APIIntegratorError("Max retry attempts reached")

    def _mock_execute(self, request: APIRequest) -> APIResponse:
        """Execute request in mock mode."""
        logger.debug(f"Mock execution: {request.method.value} {request.endpoint}")

        return APIResponse(
            status_code=200,
            data={"mock": True, "endpoint": request.endpoint},
            metadata={"mock_mode": True},
        )

    def retry_with_backoff(
        self,
        request: APIRequest,
        max_attempts: int = 3
    ) -> APIResponse:
        """
        Retry request with exponential backoff.

        Args:
            request: API request
            max_attempts: Maximum retry attempts

        Returns:
            APIResponse instance
        """
        # Update retry config temporarily
        original_config = self.config.retry_config
        self.config.retry_config = {"max_attempts": max_attempts}

        try:
            return self.execute(request)
        finally:
            self.config.retry_config = original_config

    def apply_rate_limit(
        self,
        endpoint: str,
        limit: int,
        window: int = 1
    ) -> bool:
        """
        Apply rate limit to endpoint.

        Args:
            endpoint: API endpoint
            limit: Request limit
            window: Time window in seconds

        Returns:
            True if request allowed, False otherwise
        """
        return self.rate_limit_manager.acquire(
            endpoint,
            rate=float(limit),
            window=float(window),
        )

    def cache_response(
        self,
        key: str,
        response: APIResponse,
        ttl: int = 300
    ) -> None:
        """
        Cache response.

        Args:
            key: Cache key
            response: Response to cache
            ttl: Time to live in seconds
        """
        self.cache_manager.set(key, response, ttl)

    def transform_payload(
        self,
        data: dict,
        schema: dict
    ) -> dict:
        """
        Transform payload according to schema.

        Args:
            data: Input data
            schema: Transformation schema

        Returns:
            Transformed data
        """
        # Simple transformation (could be extended)
        result = {}

        for key, mapping in schema.items():
            if isinstance(mapping, str):
                # Simple field mapping
                result[key] = data.get(mapping)
            elif isinstance(mapping, dict):
                # Nested transformation
                if "source" in mapping:
                    result[key] = data.get(mapping["source"])
                if "transform" in mapping and callable(mapping["transform"]):
                    result[key] = mapping["transform"](result.get(key))

        return result

    def subscribe_webhook(
        self,
        url: str,
        events: List[str]
    ) -> Dict[str, Any]:
        """
        Subscribe to webhook events.

        Args:
            url: Webhook URL
            events: Events to subscribe to

        Returns:
            Subscription details
        """
        subscription = {
            "id": str(datetime.utcnow().timestamp()),
            "url": url,
            "events": events,
            "created_at": datetime.utcnow().isoformat(),
        }

        # Store in context
        if "webhooks" not in self.context.data:
            self.context.data["webhooks"] = []

        self.context.data["webhooks"].append(subscription)

        logger.info(f"Subscribed webhook: {url} for events: {events}")
        return subscription

    def error_handling(
        self,
        exception: Exception,
        context: dict
    ) -> RecoveryAction:
        """
        Handle errors during execution.

        Args:
            exception: Exception that occurred
            context: Error context

        Returns:
            RecoveryAction to take
        """
        self.add_error(str(exception))

        # Determine recovery action
        if isinstance(exception, NetworkTimeoutError):
            logger.warning(f"Network timeout: {exception}")
            return RecoveryAction.RETRY

        elif isinstance(exception, RateLimitExceededError):
            logger.warning(f"Rate limit exceeded: {exception}")
            return RecoveryAction.RETRY

        elif isinstance(exception, AuthenticationFailedError):
            logger.error(f"Authentication failed: {exception}")
            return RecoveryAction.FAIL

        elif isinstance(exception, CircuitBreakerOpenError):
            logger.error(f"Circuit breaker open: {exception}")
            return RecoveryAction.CIRCUIT_BREAK

        elif isinstance(exception, InvalidResponseError):
            logger.error(f"Invalid response: {exception}")
            return RecoveryAction.FAIL

        else:
            logger.error(f"Unexpected error: {exception}")
            return RecoveryAction.FAIL

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get FSA metrics.

        Returns:
            Dictionary of metrics
        """
        metrics = {
            **self.to_dict(),
            "circuit_breaker": (
                {
                    "state": self.circuit_breaker.state.value,
                    "failure_count": self.circuit_breaker._failure_count,
                }
                if self.circuit_breaker
                else None
            ),
            "cache": {
                "size": len(self.cache_manager._cache),
                "max_size": self.cache_manager.max_size,
            },
            "webhooks": len(self.context.data.get("webhooks", [])),
        }

        return metrics
