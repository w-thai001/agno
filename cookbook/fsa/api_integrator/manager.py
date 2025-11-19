"""
API Integrator Manager - Core orchestration class for API integration FSA.

This manager coordinates all API integration operations including request
execution, authentication, retry logic, rate limiting, caching, and circuit breaking.
"""

import base64
import json
import time
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import requests
from pydantic import BaseModel

from agno.utils.log import logger

from .cache_manager import CacheManager
from .circuit_breaker import CircuitBreaker
from .models import (
    APIEndpoint,
    APIIntegratorConfig,
    APIMetrics,
    APIRequest,
    APIResponse,
    APIType,
    AuthConfig,
    AuthType,
    GraphQLRequest,
    HTTPMethod,
    SOAPRequest,
)
from .rate_limiter import GlobalRateLimiter, RateLimiter
from .retry_strategy import RetryStrategy


class APIIntegratorManager(BaseModel):
    """
    Manager for API integration operations.

    This class provides a production-ready API integration solution with:
    - REST/GraphQL/SOAP support
    - Authentication (Bearer, API Key, OAuth, Basic)
    - Retry logic with exponential backoff
    - Rate limiting with token bucket algorithm
    - Request/response caching
    - Circuit breaker pattern
    - Comprehensive metrics and logging
    """

    config: APIIntegratorConfig = APIIntegratorConfig()
    endpoints: Dict[str, APIEndpoint] = {}
    _cache_manager: Optional[CacheManager] = None
    _retry_strategy: Optional[RetryStrategy] = None
    _global_rate_limiter: Optional[GlobalRateLimiter] = None
    _rate_limiters: Dict[str, RateLimiter] = {}
    _circuit_breakers: Dict[str, CircuitBreaker] = {}
    _metrics: Dict[str, APIMetrics] = {}

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, **data):
        """Initialize the API Integrator Manager."""
        super().__init__(**data)
        self._initialize_components()

    def _initialize_components(self):
        """Initialize all manager components."""
        # Initialize cache manager
        self._cache_manager = CacheManager(self.config.cache_config)

        # Initialize retry strategy
        self._retry_strategy = RetryStrategy(self.config.retry_config)

        # Initialize global rate limiter
        self._global_rate_limiter = GlobalRateLimiter(self.config.rate_limit_config)

        logger.info("APIIntegratorManager initialized successfully")

    def register_endpoint(self, endpoint: APIEndpoint) -> None:
        """
        Register an API endpoint.

        Args:
            endpoint: Endpoint configuration to register
        """
        if endpoint.name in self.endpoints:
            logger.warning(f"Endpoint {endpoint.name} already exists, overwriting")

        self.endpoints[endpoint.name] = endpoint

        # Initialize endpoint-specific components
        self._rate_limiters[endpoint.name] = RateLimiter(
            endpoint.name, self.config.rate_limit_config
        )
        self._circuit_breakers[endpoint.name] = CircuitBreaker(
            endpoint.name, self.config.circuit_breaker_config
        )
        self._metrics[endpoint.name] = APIMetrics(endpoint_name=endpoint.name)

        logger.info(f"Registered endpoint: {endpoint.name} ({endpoint.api_type.value})")

    def make_request(
        self, request: APIRequest, skip_cache: bool = False, cache_ttl: Optional[int] = None
    ) -> APIResponse:
        """
        Make an API request with full feature support.

        Args:
            request: API request specification
            skip_cache: Skip cache lookup and storage
            cache_ttl: Custom cache TTL (overrides default)

        Returns:
            APIResponse with results

        Raises:
            Exception: If endpoint not found or request fails
        """
        # Validate endpoint exists
        if request.endpoint_name not in self.endpoints:
            raise ValueError(f"Endpoint {request.endpoint_name} not registered")

        endpoint = self.endpoints[request.endpoint_name]
        start_time = time.time()

        # Update metrics
        metrics = self._metrics[request.endpoint_name]
        metrics.total_requests += 1

        # Determine HTTP method
        method = request.method or endpoint.method

        # Build full URL with path parameters
        url = endpoint.url
        if request.path_params:
            for key, value in request.path_params.items():
                url = url.replace(f"{{{key}}}", str(value))

        # Check cache first
        cached_response = None
        if not skip_cache:
            cached_response = self._cache_manager.get(
                endpoint_name=request.endpoint_name,
                method=method,
                url=url,
                headers=request.headers,
                params=request.params,
                body=request.body,
            )

        if cached_response:
            metrics.cache_hits += 1
            duration_ms = (time.time() - start_time) * 1000
            logger.info(f"Request to {request.endpoint_name} served from cache ({duration_ms:.2f}ms)")
            return cached_response

        metrics.cache_misses += 1

        # Acquire rate limit tokens
        rate_limiter = self._rate_limiters[request.endpoint_name]
        if not rate_limiter.acquire(blocking=True, timeout=30.0):
            metrics.rate_limit_hits += 1
            raise Exception(f"Rate limit exceeded for {request.endpoint_name}")

        # Acquire global rate limit
        if not self._global_rate_limiter.acquire(blocking=True, timeout=30.0):
            metrics.rate_limit_hits += 1
            raise Exception("Global rate limit exceeded")

        # Execute through circuit breaker and retry logic
        circuit_breaker = self._circuit_breakers[request.endpoint_name]

        try:
            response = self._retry_strategy.execute_with_status_check(
                func=lambda: circuit_breaker.call(
                    self._execute_http_request,
                    endpoint=endpoint,
                    request=request,
                    method=method,
                    url=url,
                ),
                endpoint_name=request.endpoint_name,
                get_status_code=lambda r: r.status_code,
                retry_on_exceptions=[requests.exceptions.RequestException, TimeoutError],
            )

            # Update metrics
            metrics.successful_requests += 1
            duration_ms = (time.time() - start_time) * 1000
            metrics.total_duration_ms += duration_ms
            metrics.avg_duration_ms = metrics.total_duration_ms / metrics.total_requests

            # Cache successful responses
            if not skip_cache and response.success:
                self._cache_manager.put(
                    endpoint_name=request.endpoint_name,
                    method=method,
                    url=url,
                    response=response,
                    headers=request.headers,
                    params=request.params,
                    body=request.body,
                    ttl=cache_ttl,
                )

            return response

        except Exception as e:
            metrics.failed_requests += 1
            duration_ms = (time.time() - start_time) * 1000

            logger.error(f"Request to {request.endpoint_name} failed after retries: {e}")

            return APIResponse(
                status_code=0,
                headers={},
                body=None,
                success=False,
                error=str(e),
                from_cache=False,
                retry_count=self.config.retry_config.max_retries,
                duration_ms=duration_ms,
                endpoint_name=request.endpoint_name,
            )

    def _execute_http_request(
        self, endpoint: APIEndpoint, request: APIRequest, method: HTTPMethod, url: str
    ) -> APIResponse:
        """
        Execute the actual HTTP request.

        Args:
            endpoint: Endpoint configuration
            request: Request specification
            method: HTTP method
            url: Full URL

        Returns:
            APIResponse

        Raises:
            requests.exceptions.RequestException: On request failure
        """
        start_time = time.time()

        # Build headers
        headers = {
            "User-Agent": self.config.user_agent,
            **endpoint.headers,
            **request.headers,
        }

        # Add authentication
        auth_config = request.auth or self.config.default_auth
        if auth_config:
            self._apply_authentication(headers, auth_config)

        # Prepare request kwargs
        request_kwargs = {
            "method": method.value,
            "url": url,
            "headers": headers,
            "params": request.params,
            "timeout": request.timeout or endpoint.timeout,
            "verify": self.config.verify_ssl,
            "allow_redirects": self.config.follow_redirects,
        }

        # Add body if present
        if request.body:
            if isinstance(request.body, dict):
                if headers.get("Content-Type", "").startswith("application/json"):
                    request_kwargs["json"] = request.body
                else:
                    request_kwargs["data"] = request.body
            else:
                request_kwargs["data"] = request.body

        # Execute request
        logger.debug(f"Executing {method.value} request to {url}")

        try:
            response = requests.request(**request_kwargs)
            duration_ms = (time.time() - start_time) * 1000

            # Parse response body
            body = None
            raw_text = response.text

            try:
                if response.headers.get("Content-Type", "").startswith("application/json"):
                    body = response.json()
                else:
                    body = raw_text
            except Exception:
                body = raw_text

            api_response = APIResponse(
                status_code=response.status_code,
                headers=dict(response.headers),
                body=body,
                raw_text=raw_text,
                success=200 <= response.status_code < 300,
                error=None if 200 <= response.status_code < 300 else f"HTTP {response.status_code}",
                from_cache=False,
                retry_count=0,
                duration_ms=duration_ms,
                endpoint_name=request.endpoint_name,
            )

            logger.info(
                f"{method.value} {url} -> {response.status_code} ({duration_ms:.2f}ms)"
            )

            return api_response

        except requests.exceptions.RequestException as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Request failed: {e}")
            raise

    def _apply_authentication(self, headers: Dict[str, str], auth: AuthConfig) -> None:
        """
        Apply authentication to request headers.

        Args:
            headers: Headers dictionary to modify
            auth: Authentication configuration
        """
        if auth.auth_type == AuthType.BEARER:
            if auth.token:
                headers["Authorization"] = f"Bearer {auth.token}"

        elif auth.auth_type == AuthType.API_KEY:
            if auth.token and auth.api_key_header:
                headers[auth.api_key_header] = auth.token

        elif auth.auth_type == AuthType.BASIC:
            if auth.username and auth.password:
                credentials = f"{auth.username}:{auth.password}"
                encoded = base64.b64encode(credentials.encode()).decode()
                headers["Authorization"] = f"Basic {encoded}"

        elif auth.auth_type == AuthType.OAUTH2:
            # For OAuth2, assume token is already obtained
            if auth.token:
                headers["Authorization"] = f"Bearer {auth.token}"

    def make_graphql_request(self, request: GraphQLRequest) -> APIResponse:
        """
        Make a GraphQL request.

        Args:
            request: GraphQL request specification

        Returns:
            APIResponse with GraphQL results
        """
        # Convert to standard API request
        api_request = APIRequest(
            endpoint_name=request.endpoint_name,
            method=HTTPMethod.POST,
            headers={
                "Content-Type": "application/json",
                **request.headers,
            },
            body={
                "query": request.query,
                "variables": request.variables,
                "operationName": request.operation_name,
            },
        )

        return self.make_request(api_request)

    def make_soap_request(self, request: SOAPRequest) -> APIResponse:
        """
        Make a SOAP request.

        Args:
            request: SOAP request specification

        Returns:
            APIResponse with SOAP results
        """
        # Convert to standard API request
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": request.action,
            **request.headers,
        }

        api_request = APIRequest(
            endpoint_name=request.endpoint_name,
            method=HTTPMethod.POST,
            headers=headers,
            body=request.body,
        )

        return self.make_request(api_request)

    def get_endpoint(self, name: str) -> Optional[APIEndpoint]:
        """Get endpoint configuration by name."""
        return self.endpoints.get(name)

    def list_endpoints(self) -> list[str]:
        """List all registered endpoint names."""
        return list(self.endpoints.keys())

    def get_metrics(self, endpoint_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get metrics for endpoints.

        Args:
            endpoint_name: Specific endpoint name, or None for all endpoints

        Returns:
            Dictionary of metrics
        """
        if endpoint_name:
            if endpoint_name not in self._metrics:
                return {}
            return self._metrics[endpoint_name].model_dump()

        return {name: metrics.model_dump() for name, metrics in self._metrics.items()}

    def get_cache_metrics(self) -> dict:
        """Get cache metrics."""
        return self._cache_manager.get_metrics()

    def get_circuit_breaker_status(self, endpoint_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get circuit breaker status.

        Args:
            endpoint_name: Specific endpoint name, or None for all endpoints

        Returns:
            Circuit breaker status information
        """
        if endpoint_name:
            if endpoint_name not in self._circuit_breakers:
                return {}
            return self._circuit_breakers[endpoint_name].get_metrics()

        return {
            name: breaker.get_metrics() for name, breaker in self._circuit_breakers.items()
        }

    def reset_circuit_breaker(self, endpoint_name: str) -> None:
        """
        Manually reset a circuit breaker.

        Args:
            endpoint_name: Endpoint name
        """
        if endpoint_name in self._circuit_breakers:
            self._circuit_breakers[endpoint_name].reset()
            logger.info(f"Circuit breaker reset for {endpoint_name}")

    def invalidate_cache(self, endpoint_name: Optional[str] = None) -> int:
        """
        Invalidate cache entries.

        Args:
            endpoint_name: Specific endpoint name, or None for all

        Returns:
            Number of entries invalidated
        """
        return self._cache_manager.invalidate(endpoint_name=endpoint_name)

    def cleanup_expired_cache(self) -> int:
        """Clean up expired cache entries."""
        return self._cache_manager.cleanup_expired()
