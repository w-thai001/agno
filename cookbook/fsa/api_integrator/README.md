# API Integrator FSA

A production-ready Function-Specific Agent (FSA) for comprehensive API integration in the Agno Framework.

## Overview

The API Integrator FSA provides enterprise-grade API integration capabilities with built-in resilience, monitoring, and optimization features. It supports REST, GraphQL, and SOAP APIs with sophisticated error handling, caching, rate limiting, and circuit breaker patterns.

## Features

### Core Capabilities
- ✅ **REST/GraphQL/SOAP Support** - Unified interface for different API types
- 🔐 **Multiple Authentication Methods** - Bearer, API Key, OAuth2, Basic Auth
- 🔄 **Retry Logic** - Exponential backoff with jitter
- 🚦 **Rate Limiting** - Token bucket algorithm for request throttling
- 💾 **Response Caching** - LRU cache with TTL support
- ⚡ **Circuit Breaker** - Fault tolerance and cascading failure prevention
- ✔️ **Request Validation** - Schema-based validation
- ⏱️ **Timeout Management** - Configurable per-endpoint timeouts
- 📊 **Comprehensive Metrics** - Request statistics, cache performance, circuit health
- 📝 **Detailed Logging** - Full request/response lifecycle tracking

### Reliability Features
- **Exponential Backoff**: Intelligent retry delays with configurable base and max delay
- **Jitter**: Random variance to prevent thundering herd
- **Circuit Breaker States**: CLOSED → OPEN → HALF_OPEN transitions
- **Rate Limit Bursting**: Token bucket allows burst traffic while maintaining average rate
- **Cache Eviction**: LRU policy ensures optimal memory usage
- **Thread Safety**: All components are thread-safe for concurrent use

## Installation

The API Integrator FSA is included in the Agno Framework cookbook. No additional installation required.

```python
from cookbook.fsa.api_integrator import APIIntegratorToolkit, APIIntegratorConfig
```

## Quick Start

### Example 1: Basic Usage with Agent

```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from cookbook.fsa.api_integrator import APIIntegratorToolkit

# Create toolkit
toolkit = APIIntegratorToolkit()

# Create agent
api_agent = Agent(
    name="API Integration Agent",
    model=OpenAIChat(id="gpt-4o"),
    tools=[toolkit],
    instructions=[
        "You are an expert at integrating with external APIs.",
        "Help users make API requests and process responses.",
    ],
    markdown=True,
)

# Use the agent
api_agent.print_response(
    "Register a GitHub endpoint at https://api.github.com/users/{username} "
    "and get info about user 'octocat'"
)
```

### Example 2: Direct Manager Usage (Programmatic)

```python
from cookbook.fsa.api_integrator import (
    APIIntegratorManager,
    APIEndpoint,
    APIRequest,
    APIType,
    HTTPMethod,
)

# Create manager
manager = APIIntegratorManager()

# Register endpoint
endpoint = APIEndpoint(
    name="github_user",
    url="https://api.github.com/users/{username}",
    api_type=APIType.REST,
    method=HTTPMethod.GET,
)
manager.register_endpoint(endpoint)

# Make request
request = APIRequest(
    endpoint_name="github_user",
    path_params={"username": "octocat"},
)
response = manager.make_request(request)

print(f"Status: {response.status_code}")
print(f"Body: {response.body}")
```

## Configuration

### Custom Configuration

```python
from cookbook.fsa.api_integrator import (
    APIIntegratorConfig,
    RetryConfig,
    RateLimitConfig,
    CacheConfig,
    CircuitBreakerConfig,
    AuthConfig,
    AuthType,
)

config = APIIntegratorConfig(
    # Default settings
    default_timeout=30,
    verify_ssl=True,
    follow_redirects=True,

    # Default authentication
    default_auth=AuthConfig(
        auth_type=AuthType.BEARER,
        token="your_token_here",
    ),

    # Retry configuration
    retry_config=RetryConfig(
        max_retries=3,
        initial_delay=1.0,
        max_delay=60.0,
        exponential_base=2.0,
        retry_on_status_codes=[408, 429, 500, 502, 503, 504],
    ),

    # Rate limiting (token bucket)
    rate_limit_config=RateLimitConfig(
        requests_per_second=10.0,
        burst_size=20,
        enabled=True,
    ),

    # Caching
    cache_config=CacheConfig(
        enabled=True,
        ttl=300,  # 5 minutes
        max_size=1000,
    ),

    # Circuit breaker
    circuit_breaker_config=CircuitBreakerConfig(
        enabled=True,
        failure_threshold=5,
        success_threshold=2,
        timeout=60,
    ),
)

toolkit = APIIntegratorToolkit(config=config)
```

## Architecture

### MLA Framework Components

The API Integrator follows the MLA (Model-Logic-Agent) pattern:

```
┌─────────────────────────────────────────┐
│          Agent (Orchestrator)           │
│  ┌───────────────────────────────────┐  │
│  │   Model (OpenAIChat/Claude)       │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │   Logic (Instructions/Tools)      │  │
│  │   - APIIntegratorToolkit          │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│      APIIntegratorManager               │
│  ┌────────────┬────────────┬─────────┐  │
│  │  Circuit   │   Rate     │ Cache   │  │
│  │  Breaker   │  Limiter   │ Manager │  │
│  └────────────┴────────────┴─────────┘  │
│  ┌────────────┬────────────────────┐    │
│  │   Retry    │   Auth Handler     │    │
│  │  Strategy  │                    │    │
│  └────────────┴────────────────────┘    │
└─────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility |
|-----------|----------------|
| **APIIntegratorManager** | Orchestrates all API operations and manages state |
| **CircuitBreaker** | Prevents cascading failures, manages CLOSED/OPEN/HALF_OPEN states |
| **RateLimiter** | Enforces request rate limits using token bucket algorithm |
| **CacheManager** | LRU cache with TTL for response caching |
| **RetryStrategy** | Implements exponential backoff with jitter |
| **APIIntegratorToolkit** | Provides tools for Agno agents |

## Toolkit Functions

### Endpoint Management

#### `register_endpoint()`
Register a new API endpoint.

```python
register_endpoint(
    name="my_api",
    url="https://api.example.com/resource/{id}",
    api_type="REST",  # REST, GRAPHQL, or SOAP
    method="GET",     # GET, POST, PUT, PATCH, DELETE
    headers={"Accept": "application/json"},
    timeout=30,
    description="My API endpoint"
)
```

#### `list_endpoints()`
List all registered endpoints.

```python
endpoints = list_endpoints()
# Returns: ["my_api", "github_user", ...]
```

#### `get_endpoint_info()`
Get detailed endpoint configuration.

```python
info = get_endpoint_info("my_api")
# Returns endpoint configuration dict
```

### Request Execution

#### `make_rest_request()`
Execute a REST API request.

```python
response = make_rest_request(
    endpoint_name="my_api",
    method="POST",  # Optional override
    headers={"Custom-Header": "value"},
    params={"query": "param"},
    body={"key": "value"},
    path_params={"id": "123"},
    auth_type="BEARER",
    auth_token="token_here",
    skip_cache=False,
    timeout=30,
)
```

#### `make_graphql_request()`
Execute a GraphQL query.

```python
response = make_graphql_request(
    endpoint_name="graphql_api",
    query="""
        query GetUser($id: ID!) {
            user(id: $id) {
                name
                email
            }
        }
    """,
    variables={"id": "123"},
    operation_name="GetUser",
    headers={"Authorization": "Bearer token"},
)
```

#### `make_soap_request()`
Execute a SOAP request.

```python
response = make_soap_request(
    endpoint_name="soap_service",
    action="GetWeather",
    body="""<?xml version="1.0"?>
        <soap:Envelope>
            <soap:Body>
                <GetWeather>
                    <City>New York</City>
                </GetWeather>
            </soap:Body>
        </soap:Envelope>
    """,
    headers={"SOAPAction": "GetWeather"},
)
```

### Monitoring & Metrics

#### `get_metrics()`
Get API call metrics.

```python
# All endpoints
all_metrics = get_metrics()

# Specific endpoint
metrics = get_metrics("my_api")
# Returns:
# {
#     "total_requests": 100,
#     "successful_requests": 95,
#     "failed_requests": 5,
#     "avg_duration_ms": 245.5,
#     "cache_hits": 30,
#     "cache_misses": 70,
#     "retries": 8,
#     "rate_limit_hits": 2
# }
```

#### `get_cache_metrics()`
Get cache performance metrics.

```python
cache_metrics = get_cache_metrics()
# Returns:
# {
#     "size": 150,
#     "max_size": 1000,
#     "hits": 300,
#     "misses": 700,
#     "hit_rate_percent": 30.0,
#     "evictions": 5,
#     "utilization_percent": 15.0
# }
```

#### `get_circuit_breaker_status()`
Get circuit breaker status.

```python
status = get_circuit_breaker_status("my_api")
# Returns:
# {
#     "state": "CLOSED",  # CLOSED, OPEN, or HALF_OPEN
#     "failure_count": 0,
#     "success_count": 0,
#     "last_failure_time": None,
#     "time_since_last_failure": None
# }
```

### Cache Management

#### `invalidate_cache()`
Invalidate cache entries.

```python
# Invalidate specific endpoint
count = invalidate_cache("my_api")

# Clear all cache
count = invalidate_cache()
```

#### `cleanup_cache()`
Remove expired cache entries.

```python
count = cleanup_cache()
# Returns number of expired entries removed
```

### Circuit Breaker Management

#### `reset_circuit_breaker()`
Manually reset a circuit breaker to CLOSED state.

```python
reset_circuit_breaker("my_api")
```

## Authentication

### Bearer Token

```python
# Set default auth in config
config = APIIntegratorConfig(
    default_auth=AuthConfig(
        auth_type=AuthType.BEARER,
        token="your_bearer_token",
    )
)

# Or per-request
make_rest_request(
    endpoint_name="api",
    auth_type="BEARER",
    auth_token="your_bearer_token",
)
```

### API Key

```python
# Custom header name
auth = AuthConfig(
    auth_type=AuthType.API_KEY,
    token="your_api_key",
    api_key_header="X-API-Key",  # Default
)
```

### Basic Authentication

```python
auth = AuthConfig(
    auth_type=AuthType.BASIC,
    username="user",
    password="pass",
)
```

### OAuth2

```python
# Assumes token is already obtained
auth = AuthConfig(
    auth_type=AuthType.OAUTH2,
    token="oauth_access_token",
)
```

## Advanced Features

### Circuit Breaker Pattern

The circuit breaker prevents cascading failures by monitoring request failures and temporarily blocking requests to failing services.

**States:**
- **CLOSED**: Normal operation, requests pass through
- **OPEN**: Too many failures, requests are immediately rejected
- **HALF_OPEN**: Testing if service recovered, limited requests allowed

**Transitions:**
```
CLOSED ──(failures >= threshold)──> OPEN
OPEN ──(timeout expired)──> HALF_OPEN
HALF_OPEN ──(success >= threshold)──> CLOSED
HALF_OPEN ──(any failure)──> OPEN
```

### Retry Strategy

Implements exponential backoff with jitter to intelligently retry failed requests.

**Algorithm:**
```
delay = initial_delay * (base ^ attempt)
delay = min(delay, max_delay)
delay = delay + jitter
```

**Default Configuration:**
- Max retries: 3
- Initial delay: 1.0s
- Max delay: 60.0s
- Exponential base: 2.0
- Retry on: [408, 429, 500, 502, 503, 504]

### Rate Limiting

Uses token bucket algorithm to enforce rate limits.

**How it works:**
1. Bucket starts with `burst_size` tokens
2. Tokens are consumed by requests (1 token per request)
3. Tokens are refilled at `requests_per_second` rate
4. Requests wait if insufficient tokens available

**Benefits:**
- Allows burst traffic up to `burst_size`
- Maintains average rate of `requests_per_second`
- Prevents API quota exhaustion
- Thread-safe for concurrent requests

### Caching

LRU (Least Recently Used) cache with TTL support.

**Features:**
- Automatic cache key generation from request parameters
- TTL-based expiration
- LRU eviction when cache is full
- Selective caching by HTTP method (default: GET, HEAD)
- Cache hit/miss metrics

**Cache Key Components:**
- Endpoint name
- HTTP method
- URL
- Query parameters
- Request body
- Selected headers (Accept, Content-Type, etc.)

## Metrics & Monitoring

### API Metrics

Track per-endpoint performance:
- Total requests
- Success/failure counts
- Average response time
- Cache hit/miss ratio
- Retry counts
- Rate limit hits
- Circuit breaker opens

### Cache Metrics

Monitor cache efficiency:
- Hit rate percentage
- Cache size and utilization
- Eviction count
- Total hits/misses

### Circuit Breaker Metrics

Monitor service health:
- Current state (CLOSED/OPEN/HALF_OPEN)
- Failure count
- Time since last failure
- Success count in HALF_OPEN state

## Error Handling

### Request Failures

```python
response = make_rest_request(endpoint_name="api")

if not response["success"]:
    print(f"Request failed: {response['error']}")
    print(f"Status code: {response['status_code']}")
    print(f"Retries attempted: {response['retry_count']}")
```

### Circuit Breaker Open

When a circuit breaker is OPEN, requests are immediately rejected:

```python
# Check circuit breaker status first
status = get_circuit_breaker_status("api")
if status["state"] == "OPEN":
    print("Circuit is open, waiting for recovery...")
    # Optionally reset manually
    reset_circuit_breaker("api")
```

### Rate Limit Exceeded

```python
# Rate limiter blocks until tokens available (default)
# Or configure non-blocking mode in manager

# Check rate limiter status via metrics
metrics = get_metrics("api")
if metrics["rate_limit_hits"] > 0:
    print("Rate limit was hit during requests")
```

## Best Practices

### 1. Configure Appropriate Timeouts

```python
# Global default
config = APIIntegratorConfig(default_timeout=30)

# Per-endpoint
endpoint = APIEndpoint(
    name="slow_api",
    url="...",
    timeout=120,  # 2 minutes for slow endpoints
)

# Per-request
make_rest_request(endpoint_name="api", timeout=60)
```

### 2. Use Caching for Read-Heavy Workloads

```python
config = APIIntegratorConfig(
    cache_config=CacheConfig(
        enabled=True,
        ttl=600,  # 10 minutes for slowly-changing data
        max_size=1000,
    )
)
```

### 3. Set Conservative Circuit Breaker Thresholds

```python
config = APIIntegratorConfig(
    circuit_breaker_config=CircuitBreakerConfig(
        failure_threshold=5,  # Open after 5 failures
        success_threshold=2,  # Close after 2 successes in HALF_OPEN
        timeout=60,  # Wait 60s before trying again
    )
)
```

### 4. Monitor Metrics Regularly

```python
# Get comprehensive health check
def health_check():
    metrics = get_metrics()
    cache = get_cache_metrics()
    breakers = get_circuit_breaker_status()

    for endpoint, data in metrics.items():
        success_rate = (
            data["successful_requests"] / data["total_requests"] * 100
            if data["total_requests"] > 0 else 0
        )
        print(f"{endpoint}: {success_rate:.1f}% success rate")
```

### 5. Use Path Parameters for RESTful URLs

```python
# Register with template
register_endpoint(
    name="get_user",
    url="https://api.example.com/users/{user_id}/posts/{post_id}",
)

# Use with path_params
make_rest_request(
    endpoint_name="get_user",
    path_params={"user_id": "123", "post_id": "456"},
)
```

### 6. Implement Graceful Degradation

```python
# Primary API with fallback
try:
    response = make_rest_request(endpoint_name="primary_api")
    if not response["success"]:
        response = make_rest_request(endpoint_name="fallback_api")
except Exception:
    # Return cached data or default values
    pass
```

## Examples

See `api_integrator_example.py` for comprehensive examples including:
1. Basic REST API integration
2. Custom configuration
3. Authentication methods
4. GraphQL integration
5. Monitoring and metrics
6. Error handling
7. Advanced workflows
8. Cache management
9. Direct manager usage

## API Reference

### Models

- `APIIntegratorConfig` - Main configuration
- `APIEndpoint` - Endpoint definition
- `APIRequest` - REST request specification
- `GraphQLRequest` - GraphQL request specification
- `SOAPRequest` - SOAP request specification
- `APIResponse` - Response wrapper
- `AuthConfig` - Authentication configuration
- `RetryConfig` - Retry configuration
- `RateLimitConfig` - Rate limit configuration
- `CacheConfig` - Cache configuration
- `CircuitBreakerConfig` - Circuit breaker configuration
- `APIMetrics` - Metrics data

### Enums

- `APIType` - REST, GRAPHQL, SOAP
- `HTTPMethod` - GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS
- `AuthType` - NONE, BEARER, API_KEY, OAUTH2, BASIC
- `CircuitBreakerState` - CLOSED, OPEN, HALF_OPEN

## Performance Considerations

### Thread Safety
All components are thread-safe and can be used in concurrent environments.

### Memory Usage
- Cache size is capped by `max_size` configuration
- LRU eviction prevents unbounded growth
- Expired entries are lazily cleaned up

### Network Efficiency
- Caching reduces redundant API calls
- Rate limiting prevents overwhelming APIs
- Connection pooling (via requests library)
- Automatic retry reduces manual intervention

### Scalability
- Token bucket allows burst traffic
- Circuit breaker prevents cascading failures
- Per-endpoint rate limiters allow fine-grained control
- Metrics help identify bottlenecks

## Troubleshooting

### Issue: Requests Always Cache Miss

**Solution:** Check that the request parameters are identical, including headers and body.

```python
# Verify cache is enabled
cache_metrics = get_cache_metrics()
print(cache_metrics)
```

### Issue: Circuit Breaker Always Open

**Solution:** Lower failure threshold or increase timeout.

```python
# Reset manually
reset_circuit_breaker("api")

# Or adjust config
config.circuit_breaker_config.failure_threshold = 10
```

### Issue: Rate Limit Too Restrictive

**Solution:** Increase requests per second or burst size.

```python
config.rate_limit_config.requests_per_second = 20.0
config.rate_limit_config.burst_size = 50
```

### Issue: Timeouts Occurring Frequently

**Solution:** Increase timeout or check network connectivity.

```python
# Increase timeout
config.default_timeout = 60

# Or per-endpoint
endpoint.timeout = 120
```

## Contributing

This FSA is part of the Agno Framework cookbook. To contribute:
1. Add new features in the appropriate module
2. Update tests
3. Update this README
4. Submit a pull request

## License

Part of the Agno Framework - see main repository for license details.

## Support

For issues and questions:
- Check examples in `api_integrator_example.py`
- Review Agno Framework documentation
- Submit issues to the Agno repository

## Changelog

### Version 1.0.0
- Initial release
- REST/GraphQL/SOAP support
- Authentication (Bearer, API Key, OAuth2, Basic)
- Retry logic with exponential backoff
- Rate limiting with token bucket
- LRU cache with TTL
- Circuit breaker pattern
- Comprehensive metrics
- Full Agno Agent integration
