"""
Data models for API Integrator FSA.

This module defines all the data structures used for API integration operations.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class HTTPMethod(str, Enum):
    """Supported HTTP methods."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class APIType(str, Enum):
    """Supported API types."""

    REST = "REST"
    GRAPHQL = "GRAPHQL"
    SOAP = "SOAP"


class AuthType(str, Enum):
    """Supported authentication types."""

    NONE = "NONE"
    BEARER = "BEARER"
    API_KEY = "API_KEY"
    OAUTH2 = "OAUTH2"
    BASIC = "BASIC"


class CircuitBreakerState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "CLOSED"  # Normal operation
    OPEN = "OPEN"  # Failing, reject requests
    HALF_OPEN = "HALF_OPEN"  # Testing if service recovered


class APIEndpoint(BaseModel):
    """API endpoint configuration."""

    name: str = Field(description="Unique identifier for the endpoint")
    url: str = Field(description="Full URL or URL template")
    api_type: APIType = Field(default=APIType.REST, description="Type of API")
    method: HTTPMethod = Field(default=HTTPMethod.GET, description="HTTP method")
    headers: Dict[str, str] = Field(default_factory=dict, description="Default headers")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    description: Optional[str] = Field(default=None, description="Endpoint description")


class AuthConfig(BaseModel):
    """Authentication configuration."""

    auth_type: AuthType = Field(default=AuthType.NONE, description="Authentication type")
    token: Optional[str] = Field(default=None, description="Bearer token or API key")
    api_key_header: Optional[str] = Field(default="X-API-Key", description="API key header name")
    username: Optional[str] = Field(default=None, description="Basic auth username")
    password: Optional[str] = Field(default=None, description="Basic auth password")
    oauth_token_url: Optional[str] = Field(default=None, description="OAuth token endpoint")
    client_id: Optional[str] = Field(default=None, description="OAuth client ID")
    client_secret: Optional[str] = Field(default=None, description="OAuth client secret")
    scope: Optional[str] = Field(default=None, description="OAuth scope")


class RetryConfig(BaseModel):
    """Retry configuration with exponential backoff."""

    max_retries: int = Field(default=3, description="Maximum number of retry attempts")
    initial_delay: float = Field(default=1.0, description="Initial delay in seconds")
    max_delay: float = Field(default=60.0, description="Maximum delay in seconds")
    exponential_base: float = Field(default=2.0, description="Exponential backoff base")
    retry_on_status_codes: List[int] = Field(
        default_factory=lambda: [408, 429, 500, 502, 503, 504],
        description="HTTP status codes to retry on",
    )


class RateLimitConfig(BaseModel):
    """Rate limiting configuration using token bucket algorithm."""

    requests_per_second: float = Field(default=10.0, description="Requests allowed per second")
    burst_size: int = Field(default=20, description="Maximum burst size")
    enabled: bool = Field(default=True, description="Enable rate limiting")


class CacheConfig(BaseModel):
    """Cache configuration."""

    enabled: bool = Field(default=True, description="Enable caching")
    ttl: int = Field(default=300, description="Cache TTL in seconds")
    max_size: int = Field(default=1000, description="Maximum cache entries")
    cache_methods: List[HTTPMethod] = Field(
        default_factory=lambda: [HTTPMethod.GET, HTTPMethod.HEAD],
        description="HTTP methods to cache",
    )


class CircuitBreakerConfig(BaseModel):
    """Circuit breaker configuration."""

    enabled: bool = Field(default=True, description="Enable circuit breaker")
    failure_threshold: int = Field(default=5, description="Failures before opening circuit")
    success_threshold: int = Field(default=2, description="Successes to close circuit from half-open")
    timeout: int = Field(default=60, description="Timeout before half-open in seconds")
    monitored_exceptions: List[str] = Field(
        default_factory=lambda: ["RequestException", "Timeout", "ConnectionError"],
        description="Exception types to monitor",
    )


class APIRequest(BaseModel):
    """API request specification."""

    endpoint_name: str = Field(description="Name of the registered endpoint")
    method: Optional[HTTPMethod] = Field(default=None, description="Override HTTP method")
    headers: Dict[str, str] = Field(default_factory=dict, description="Additional headers")
    params: Dict[str, Any] = Field(default_factory=dict, description="Query parameters")
    body: Optional[Union[Dict[str, Any], str]] = Field(default=None, description="Request body")
    auth: Optional[AuthConfig] = Field(default=None, description="Authentication override")
    timeout: Optional[int] = Field(default=None, description="Timeout override")
    path_params: Dict[str, str] = Field(default_factory=dict, description="URL path parameters")


class GraphQLRequest(BaseModel):
    """GraphQL-specific request."""

    endpoint_name: str = Field(description="Name of the registered GraphQL endpoint")
    query: str = Field(description="GraphQL query or mutation")
    variables: Dict[str, Any] = Field(default_factory=dict, description="Query variables")
    operation_name: Optional[str] = Field(default=None, description="Operation name")
    headers: Dict[str, str] = Field(default_factory=dict, description="Additional headers")


class SOAPRequest(BaseModel):
    """SOAP-specific request."""

    endpoint_name: str = Field(description="Name of the registered SOAP endpoint")
    action: str = Field(description="SOAP action")
    body: str = Field(description="SOAP envelope XML")
    headers: Dict[str, str] = Field(default_factory=dict, description="Additional headers")


class APIResponse(BaseModel):
    """API response wrapper."""

    status_code: int = Field(description="HTTP status code")
    headers: Dict[str, str] = Field(description="Response headers")
    body: Optional[Union[Dict[str, Any], str, bytes]] = Field(default=None, description="Response body")
    raw_text: Optional[str] = Field(default=None, description="Raw response text")
    success: bool = Field(description="Whether request was successful")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    from_cache: bool = Field(default=False, description="Whether response was served from cache")
    retry_count: int = Field(default=0, description="Number of retries attempted")
    duration_ms: float = Field(description="Request duration in milliseconds")
    endpoint_name: str = Field(description="Endpoint name that was called")

    class Config:
        arbitrary_types_allowed = True


class TransformConfig(BaseModel):
    """Response transformation configuration."""

    enabled: bool = Field(default=False, description="Enable response transformation")
    jmespath_query: Optional[str] = Field(default=None, description="JMESPath query for extraction")
    json_path: Optional[str] = Field(default=None, description="JSONPath for extraction")
    xml_xpath: Optional[str] = Field(default=None, description="XPath for XML extraction")
    custom_transform: Optional[str] = Field(default=None, description="Custom transformation function name")


class RequestValidationRule(BaseModel):
    """Request validation rule."""

    field: str = Field(description="Field to validate")
    required: bool = Field(default=False, description="Whether field is required")
    type: Optional[str] = Field(default=None, description="Expected type (str, int, dict, etc.)")
    pattern: Optional[str] = Field(default=None, description="Regex pattern for validation")
    min_length: Optional[int] = Field(default=None, description="Minimum length")
    max_length: Optional[int] = Field(default=None, description="Maximum length")
    allowed_values: Optional[List[Any]] = Field(default=None, description="Allowed values")


class APIIntegratorConfig(BaseModel):
    """Main configuration for API Integrator."""

    default_auth: Optional[AuthConfig] = Field(default=None, description="Default authentication")
    retry_config: RetryConfig = Field(default_factory=RetryConfig, description="Retry configuration")
    rate_limit_config: RateLimitConfig = Field(
        default_factory=RateLimitConfig, description="Rate limit configuration"
    )
    cache_config: CacheConfig = Field(default_factory=CacheConfig, description="Cache configuration")
    circuit_breaker_config: CircuitBreakerConfig = Field(
        default_factory=CircuitBreakerConfig, description="Circuit breaker configuration"
    )
    default_timeout: int = Field(default=30, description="Default timeout in seconds")
    verify_ssl: bool = Field(default=True, description="Verify SSL certificates")
    follow_redirects: bool = Field(default=True, description="Follow HTTP redirects")
    max_redirects: int = Field(default=10, description="Maximum redirects to follow")
    user_agent: str = Field(
        default="Agno-API-Integrator/1.0", description="User agent for requests"
    )


class APIMetrics(BaseModel):
    """API call metrics."""

    endpoint_name: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_duration_ms: float = 0.0
    avg_duration_ms: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    retries: int = 0
    circuit_breaker_opens: int = 0
    rate_limit_hits: int = 0


class APIIntegratorState(BaseModel):
    """Overall state of the API Integrator."""

    endpoints: Dict[str, APIEndpoint] = Field(default_factory=dict)
    metrics: Dict[str, APIMetrics] = Field(default_factory=dict)
    circuit_breaker_states: Dict[str, CircuitBreakerState] = Field(default_factory=dict)
    is_initialized: bool = False
    total_requests: int = 0
