"""
API Integrator FSA (Function-Specific Agent) for Agno Framework.

A production-ready FSA for comprehensive API integration operations.

Features:
- REST/GraphQL/SOAP endpoint management
- Request builder with method/headers/body configuration
- Response parsing and transformation
- Authentication integration (Bearer/API Key/OAuth/Basic)
- Retry logic with exponential backoff
- Rate limiting with token bucket algorithm
- Request/response caching with LRU eviction
- Circuit breaker pattern for fault tolerance
- Request validation
- Timeout management
- Comprehensive logging and metrics

Example Usage:
    ```python
    from agno.agent import Agent
    from agno.models.openai import OpenAIChat
    from cookbook.fsa.api_integrator import APIIntegratorToolkit, APIIntegratorConfig

    # Configure the integrator
    config = APIIntegratorConfig(
        default_timeout=30,
        verify_ssl=True,
    )

    # Create the toolkit
    toolkit = APIIntegratorToolkit(config=config)

    # Create an agent with the toolkit
    api_agent = Agent(
        name="API Integration Agent",
        model=OpenAIChat(id="gpt-4o"),
        tools=[toolkit],
        instructions=[
            "You are an expert at integrating with external APIs.",
            "Help users make API requests, handle authentication, and process responses.",
            "Monitor API health using circuit breakers and metrics.",
        ],
        markdown=True,
    )

    # Use the agent
    api_agent.print_response(
        "Register an endpoint for GitHub API at https://api.github.com/users/{username}"
    )
    ```
"""

from .cache_manager import CacheManager
from .circuit_breaker import CircuitBreaker
from .manager import APIIntegratorManager
from .models import (
    APIEndpoint,
    APIIntegratorConfig,
    APIMetrics,
    APIRequest,
    APIResponse,
    APIType,
    AuthConfig,
    AuthType,
    CacheConfig,
    CircuitBreakerConfig,
    GraphQLRequest,
    HTTPMethod,
    RateLimitConfig,
    RetryConfig,
    SOAPRequest,
)
from .rate_limiter import GlobalRateLimiter, RateLimiter
from .retry_strategy import RetryStrategy
from .toolkit import APIIntegratorToolkit

__all__ = [
    # Main components
    "APIIntegratorToolkit",
    "APIIntegratorManager",
    # Models
    "APIIntegratorConfig",
    "APIEndpoint",
    "APIRequest",
    "APIResponse",
    "GraphQLRequest",
    "SOAPRequest",
    "AuthConfig",
    "RetryConfig",
    "RateLimitConfig",
    "CacheConfig",
    "CircuitBreakerConfig",
    "APIMetrics",
    # Enums
    "APIType",
    "HTTPMethod",
    "AuthType",
    # Supporting classes
    "CircuitBreaker",
    "RateLimiter",
    "GlobalRateLimiter",
    "CacheManager",
    "RetryStrategy",
]

__version__ = "1.0.0"
