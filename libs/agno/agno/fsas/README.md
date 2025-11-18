# API Integrator FSA

Universal API integration layer for the MLA framework with multi-protocol support, automatic retry logic, rate limiting, authentication, caching, and error recovery.

## Features

- **Multi-Protocol Support**: REST, GraphQL, gRPC, WebSocket, and SOAP
- **Authentication**: OAuth2, JWT, API Key, Basic Auth, Bearer Token, mTLS
- **Resilience Patterns**: Circuit breaker, exponential backoff, retry logic
- **Rate Limiting**: Token bucket algorithm with per-endpoint limits
- **Caching**: TTL-based caching with LRU eviction
- **Request/Response Pipeline**: Interceptors and transformers
- **Error Recovery**: Automatic fallback and recovery strategies
- **Mock Mode**: Built-in testing support

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

### Basic REST API Integration

```python
from agno.fsas.api_integrator import (
    APIIntegratorFSA,
    APIConfig,
    APIRequest,
    ProtocolType,
    HTTPMethod,
)

# Configure API
config = APIConfig(
    base_url="https://api.example.com",
    protocol=ProtocolType.REST,
    timeout=30.0,
)

# Create FSA
fsa = APIIntegratorFSA(config=config)

# Create request
request = APIRequest(
    protocol=ProtocolType.REST,
    endpoint="/api/users",
    method=HTTPMethod.GET,
    headers={"Accept": "application/json"},
)

# Execute request
response = fsa.execute(request)

print(f"Status: {response.status_code}")
print(f"Data: {response.data}")
```

### With Authentication

```python
from agno.fsas.api_integrator import AuthConfig, AuthType

# API Key Authentication
auth_config = AuthConfig(
    auth_type=AuthType.API_KEY,
    credentials={"api_key": "your-api-key"},
)

config = APIConfig(
    base_url="https://api.example.com",
    protocol=ProtocolType.REST,
    auth_config=auth_config,
)

fsa = APIIntegratorFSA(config=config)
```

### OAuth2 Authentication

```python
from agno.fsas.api_integrator import OAuth2GrantType

auth_config = AuthConfig(
    auth_type=AuthType.OAUTH2,
    token_url="https://auth.example.com/oauth/token",
    grant_type=OAuth2GrantType.CLIENT_CREDENTIALS,
    credentials={
        "client_id": "your-client-id",
        "client_secret": "your-client-secret",
    },
    scopes=["read", "write"],
)

config = APIConfig(
    base_url="https://api.example.com",
    protocol=ProtocolType.REST,
    auth_config=auth_config,
)

fsa = APIIntegratorFSA(config=config)
```

### With Rate Limiting

```python
config = APIConfig(
    base_url="https://api.example.com",
    protocol=ProtocolType.REST,
    rate_limit_config={
        "rate": 100,        # 100 requests
        "window": 60,       # per 60 seconds
        "timeout": 5.0,     # wait up to 5 seconds
    },
)

fsa = APIIntegratorFSA(config=config)
```

### With Caching

```python
config = APIConfig(
    base_url="https://api.example.com",
    protocol=ProtocolType.REST,
    cache_config={
        "ttl": 300,  # Cache for 5 minutes
    },
)

fsa = APIIntegratorFSA(config=config)

# First request - hits API
response1 = fsa.execute(request)
print(f"Cached: {response1.cached}")  # False

# Second request - from cache
response2 = fsa.execute(request)
print(f"Cached: {response2.cached}")  # True
```

### With Circuit Breaker

```python
config = APIConfig(
    base_url="https://api.example.com",
    protocol=ProtocolType.REST,
    circuit_breaker_config={
        "failure_threshold": 5,      # Open after 5 failures
        "recovery_timeout": 60.0,    # Try recovery after 60s
        "half_open_max_calls": 3,    # Allow 3 test calls
    },
)

fsa = APIIntegratorFSA(config=config)
```

### With Retry Logic

```python
config = APIConfig(
    base_url="https://api.example.com",
    protocol=ProtocolType.REST,
    retry_config={
        "max_attempts": 3,     # Retry up to 3 times
        "base_delay": 1.0,     # Start with 1s delay
        "max_delay": 60.0,     # Max 60s delay
    },
)

fsa = APIIntegratorFSA(config=config)
```

## GraphQL Support

```python
from agno.fsas.api_integrator import ProtocolType

config = APIConfig(
    base_url="https://api.example.com",
    protocol=ProtocolType.GRAPHQL,
)

fsa = APIIntegratorFSA(config=config)

request = APIRequest(
    protocol=ProtocolType.GRAPHQL,
    endpoint="/graphql",
    body={
        "query": """
            query GetUser($id: ID!) {
                user(id: $id) {
                    id
                    name
                    email
                }
            }
        """,
        "variables": {"id": "123"},
    },
)

response = fsa.execute(request)
print(response.data)
```

## WebSocket Support

```python
import asyncio

config = APIConfig(
    base_url="wss://api.example.com",
    protocol=ProtocolType.WEBSOCKET,
)

fsa = APIIntegratorFSA(config=config)

request = APIRequest(
    protocol=ProtocolType.WEBSOCKET,
    endpoint="/ws",
    body={"action": "subscribe", "channel": "updates"},
)

# WebSocket requires async execution
response = await fsa.aexecute(request)
print(response.data)
```

## SOAP Support

```python
config = APIConfig(
    base_url="https://api.example.com/soap",
    protocol=ProtocolType.SOAP,
)

fsa = APIIntegratorFSA(config=config)

request = APIRequest(
    protocol=ProtocolType.SOAP,
    endpoint="",
    body={"param1": "value1", "param2": "value2"},
    metadata={
        "wsdl_url": "https://api.example.com/soap?wsdl",
        "operation": "GetData",
    },
)

response = fsa.execute(request)
```

## Request/Response Pipeline

### Adding Request Interceptors

```python
from agno.fsas.api_integrator import HeaderInjector

# Add custom headers to all requests
fsa.add_request_interceptor(
    HeaderInjector({
        "X-Client-Version": "1.0.0",
        "X-Request-ID": "unique-id",
    })
)

# Create custom interceptor
from agno.fsas.api_integrator import RequestInterceptor

class LoggingInterceptor(RequestInterceptor):
    def intercept(self, request, config):
        print(f"Request: {request.method.value} {request.endpoint}")
        return request

fsa.add_request_interceptor(LoggingInterceptor())
```

### Adding Response Transformers

```python
from agno.fsas.api_integrator import ResponseTransformer

class DataExtractor(ResponseTransformer):
    def transform(self, response, request):
        if response.is_success and isinstance(response.data, dict):
            # Extract nested data
            response.data = response.data.get("data", response.data)
        return response

fsa.add_response_transformer(DataExtractor())
```

## Advanced Features

### Webhook Subscriptions

```python
subscription = fsa.subscribe_webhook(
    url="https://myapp.com/webhooks/callback",
    events=["user.created", "user.updated", "user.deleted"],
)

print(f"Subscription ID: {subscription['id']}")
```

### Payload Transformation

```python
# Source data
user_data = {
    "first_name": "John",
    "last_name": "Doe",
    "user_email": "john@example.com",
}

# Define transformation schema
schema = {
    "name": "first_name",
    "surname": "last_name",
    "email": "user_email",
}

# Transform
transformed = fsa.transform_payload(user_data, schema)
# Result: {"name": "John", "surname": "Doe", "email": "john@example.com"}
```

### Manual Rate Limiting

```python
# Check rate limit before making request
if fsa.apply_rate_limit("/api/users", limit=10, window=1):
    response = fsa.execute(request)
else:
    print("Rate limit exceeded")
```

### Manual Caching

```python
# Cache custom response
response = APIResponse(status_code=200, data={"custom": "data"})
fsa.cache_response("my-cache-key", response, ttl=300)

# Retrieve cached response
cached = fsa.cache_manager.get("my-cache-key")
```

### Metrics and Monitoring

```python
metrics = fsa.get_metrics()

print(f"FSA State: {metrics['state']}")
print(f"Circuit Breaker: {metrics['circuit_breaker']}")
print(f"Cache Size: {metrics['cache']['size']}")
print(f"Webhooks: {metrics['webhooks']}")
```

## Async Support

```python
import asyncio

async def make_requests():
    config = APIConfig(
        base_url="https://api.example.com",
        protocol=ProtocolType.REST,
    )

    fsa = APIIntegratorFSA(config=config)

    request = APIRequest(
        protocol=ProtocolType.REST,
        endpoint="/api/users",
    )

    # Async execution
    response = await fsa.aexecute(request)
    print(response.data)

asyncio.run(make_requests())
```

## Mock Mode for Testing

```python
# Enable mock mode
fsa = APIIntegratorFSA(config=config, mock_mode=True)

# All requests return mock responses
response = fsa.execute(request)
print(response.metadata["mock_mode"])  # True
```

## Error Handling

```python
from agno.fsas.api_integrator import (
    NetworkTimeoutError,
    RateLimitExceededError,
    CircuitBreakerOpenError,
    AuthenticationFailedError,
)

try:
    response = fsa.execute(request)
except NetworkTimeoutError:
    print("Request timed out")
except RateLimitExceededError:
    print("Rate limit exceeded")
except CircuitBreakerOpenError:
    print("Circuit breaker is open")
except AuthenticationFailedError:
    print("Authentication failed")
```

## Configuration Validation

```python
from agno.fsas.api_integrator import ValidationResult

# Validate configuration before use
result = fsa.validate(config)

if result.valid:
    print("Configuration is valid")
else:
    print("Validation errors:")
    for error in result.errors:
        print(f"  - {error}")

    print("Warnings:")
    for warning in result.warnings:
        print(f"  - {warning}")
```

## Complete Example

```python
from agno.fsas.api_integrator import (
    APIIntegratorFSA,
    APIConfig,
    APIRequest,
    AuthConfig,
    AuthType,
    ProtocolType,
    HTTPMethod,
    HeaderInjector,
)

# Configure API with all features
auth_config = AuthConfig(
    auth_type=AuthType.API_KEY,
    credentials={"api_key": "your-api-key"},
)

config = APIConfig(
    base_url="https://api.example.com",
    protocol=ProtocolType.REST,
    auth_config=auth_config,
    timeout=30.0,
    rate_limit_config={
        "rate": 100,
        "window": 60,
    },
    cache_config={
        "ttl": 300,
    },
    circuit_breaker_config={
        "failure_threshold": 5,
        "recovery_timeout": 60.0,
    },
    retry_config={
        "max_attempts": 3,
        "base_delay": 1.0,
    },
)

# Create FSA
fsa = APIIntegratorFSA(config=config, name="MyAPIIntegrator")

# Add request interceptor
fsa.add_request_interceptor(
    HeaderInjector({"X-Client": "MyApp/1.0"})
)

# Validate configuration
validation = fsa.validate(config)
if not validation.valid:
    raise ValueError(f"Invalid config: {validation.errors}")

# Create and execute request
request = APIRequest(
    protocol=ProtocolType.REST,
    endpoint="/api/v1/users",
    method=HTTPMethod.GET,
    params={"page": 1, "limit": 10},
    headers={"Accept": "application/json"},
)

# Execute with automatic retry, rate limiting, caching
response = fsa.execute(request)

if response.is_success:
    print(f"Users: {response.data}")
    print(f"Cached: {response.cached}")
else:
    print(f"Error: {response.status_code}")

# Get metrics
metrics = fsa.get_metrics()
print(f"Metrics: {metrics}")
```

## Testing

Run the test suite:

```bash
# Run all tests
pytest tests/fsas/test_api_integrator.py -v

# Run specific test class
pytest tests/fsas/test_api_integrator.py::TestAPIIntegratorFSA -v

# Run with coverage
pytest tests/fsas/test_api_integrator.py --cov=agno.fsas --cov-report=html
```

## Architecture

### Components

1. **APIIntegratorFSA**: Main FSA class coordinating all components
2. **AuthenticationManager**: Handles all authentication flows
3. **CircuitBreakerManager**: Implements circuit breaker pattern
4. **RateLimitManager**: Token bucket rate limiting
5. **CacheManager**: LRU cache with TTL
6. **RetryStrategy**: Exponential backoff with jitter
7. **Protocol Handlers**: REST, GraphQL, WebSocket, SOAP, gRPC
8. **Pipeline**: Request interceptors and response transformers

### State Machine

```
IDLE -> INITIALIZING -> READY -> EXECUTING -> COMPLETED -> READY
                   |                  |
                   v                  v
                 ERROR            PAUSED
```

## Best Practices

1. **Always validate configuration** before first use
2. **Use rate limiting** to respect API limits
3. **Enable caching** for GET requests
4. **Configure circuit breaker** for unreliable services
5. **Use retry strategy** for transient failures
6. **Add request interceptors** for cross-cutting concerns
7. **Monitor metrics** for performance insights
8. **Use mock mode** for testing

## License

Copyright (c) Agno Framework

## Contributing

Contributions are welcome! Please read the contributing guidelines first.
