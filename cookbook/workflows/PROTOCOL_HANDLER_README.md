# 🌐 Protocol Handler - Universal Communication Protocol Manager

A production-ready workflow for the Agno Framework that provides a unified interface for managing various communication protocols with built-in reliability patterns.

## 🎯 Overview

The Protocol Handler is a sophisticated workflow that abstracts away the complexity of working with multiple communication protocols. It provides:

- **Unified Interface**: Single API for HTTP, WebSocket, gRPC, MQTT, and AMQP
- **Reliability Patterns**: Automatic retries, circuit breakers, and connection pooling
- **Performance**: Built-in caching, connection reuse, and metrics
- **Security**: TLS/SSL support and flexible authentication
- **Monitoring**: Comprehensive metrics and performance tracking

## 📦 Installation

```bash
# Core dependencies
pip install agno

# Protocol-specific dependencies
pip install httpx          # For HTTP/HTTPS
pip install websockets     # For WebSocket
pip install grpcio         # For gRPC
pip install paho-mqtt      # For MQTT
pip install pika           # For AMQP

# Or install all at once
pip install httpx websockets grpcio paho-mqtt pika agno
```

## 🚀 Quick Start

### Basic HTTP Request

```python
from protocol_handler import ProtocolHandler, ProtocolConfig, ProtocolType

# Create handler instance
handler = ProtocolHandler(
    session_id="my-app",
    debug_mode=True,
)

# Configure HTTP protocol
config = ProtocolConfig(
    protocol_type=ProtocolType.HTTP,
    endpoint="https://api.example.com",
)

# Make a GET request
response = handler.run(
    config=config,
    operation="send",
    method="GET",
    path="/users/1",
)
```

### WebSocket Communication

```python
config = ProtocolConfig(
    protocol_type=ProtocolType.WEBSOCKET,
    endpoint="wss://stream.example.com",
)

# Send a message
handler.run(
    config=config,
    operation="send",
    data={"message": "Hello!"},
)

# Receive a message
handler.run(
    config=config,
    operation="receive",
    timeout=5.0,
)
```

### MQTT Pub/Sub

```python
config = ProtocolConfig(
    protocol_type=ProtocolType.MQTT,
    endpoint="mqtt://broker.example.com:1883",
)

# Publish message
handler.run(
    config=config,
    operation="send",
    data={"temperature": 22.5},
    topic="sensors/room1",
    qos=1,
)

# Subscribe and receive
handler.run(
    config=config,
    operation="receive",
    topic="sensors/#",
    timeout=10.0,
)
```

## 🔧 Configuration

### Protocol Configuration

```python
from protocol_handler import (
    ProtocolConfig,
    ProtocolType,
    RetryPolicy,
    TimeoutConfig,
    CircuitBreakerConfig,
    ConnectionPoolConfig,
    AuthCredentials,
    AuthType,
)

config = ProtocolConfig(
    # Required
    protocol_type=ProtocolType.HTTP,
    endpoint="https://api.example.com",

    # Authentication
    auth_credentials=AuthCredentials(
        auth_type=AuthType.BEARER,
        token="your-token-here",
    ),

    # Retry policy
    retry_policy=RetryPolicy(
        max_attempts=3,
        initial_delay=1.0,
        max_delay=60.0,
        exponential_base=2.0,
        jitter=True,
    ),

    # Timeouts
    timeout_config=TimeoutConfig(
        connect_timeout=10.0,
        read_timeout=30.0,
        write_timeout=30.0,
        pool_timeout=5.0,
    ),

    # Circuit breaker
    circuit_breaker=CircuitBreakerConfig(
        failure_threshold=5,
        success_threshold=2,
        timeout=60.0,
        enabled=True,
    ),

    # Connection pooling
    pool_config=ConnectionPoolConfig(
        max_connections=10,
        max_keepalive_connections=5,
        keepalive_expiry=300.0,
    ),

    # TLS/SSL
    tls_enabled=True,
    verify_ssl=True,

    # Protocol-specific options
    extra_config={"http2": True},
)
```

### Authentication Types

The Protocol Handler supports multiple authentication methods:

#### 1. Bearer Token

```python
auth_credentials=AuthCredentials(
    auth_type=AuthType.BEARER,
    token="your-bearer-token",
)
```

#### 2. API Key

```python
auth_credentials=AuthCredentials(
    auth_type=AuthType.API_KEY,
    token="your-api-key",
)
```

#### 3. Basic Authentication

```python
auth_credentials=AuthCredentials(
    auth_type=AuthType.BASIC,
    username="user",
    password="pass",
)
```

#### 4. OAuth2

```python
auth_credentials=AuthCredentials(
    auth_type=AuthType.OAUTH2,
    oauth2_token="your-oauth2-token",
)
```

#### 5. Custom Headers

```python
auth_credentials=AuthCredentials(
    auth_type=AuthType.NONE,
    headers={
        "X-Custom-Auth": "custom-value",
        "X-API-Version": "v2",
    },
)
```

## 🎯 Features

### 1. Automatic Retry with Exponential Backoff

The handler automatically retries failed requests with intelligent backoff:

```python
retry_policy=RetryPolicy(
    max_attempts=5,           # Try up to 5 times
    initial_delay=1.0,        # Start with 1 second delay
    max_delay=60.0,           # Cap at 60 seconds
    exponential_base=2.0,     # Double delay each time
    jitter=True,              # Add randomness to prevent thundering herd
)
```

**Retry sequence**: 1s → 2s → 4s → 8s → 16s (with jitter)

### 2. Circuit Breaker Pattern

Prevents cascading failures by opening the circuit when errors occur:

```python
circuit_breaker=CircuitBreakerConfig(
    failure_threshold=5,      # Open after 5 failures
    success_threshold=2,      # Close after 2 successes
    timeout=60.0,            # Wait 60s before trying again
    enabled=True,
)
```

**States**:
- **CLOSED**: Normal operation, requests pass through
- **OPEN**: Too many failures, requests are rejected immediately
- **HALF_OPEN**: Testing if service recovered

### 3. Connection Pooling

Reuse connections for better performance:

```python
pool_config=ConnectionPoolConfig(
    max_connections=20,               # Maximum total connections
    max_keepalive_connections=10,     # Keep 10 connections alive
    keepalive_expiry=300.0,          # Expire after 5 minutes
)
```

### 4. Response Caching

Cache successful responses to reduce API calls:

```python
# Enable caching
response = handler.run(
    config=config,
    operation="send",
    method="GET",
    path="/users/1",
    use_cache=True,  # Cache this response
)

# Subsequent calls return cached response
response = handler.run(
    config=config,
    operation="send",
    method="GET",
    path="/users/1",
    use_cache=True,  # Returns from cache
)
```

### 5. Performance Metrics

Track connection performance and health:

```python
# Metrics are automatically tracked
response = handler.run(config=config, operation="send", ...)

# Metrics included in response:
# - Total requests
# - Successful/failed requests
# - Average latency
# - Circuit state
# - Total retries
```

## 📊 Supported Protocols

### HTTP/HTTPS ✅

Full support with connection pooling, retries, and circuit breaking.

**Methods**: GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS

```python
response = handler.run(
    config=http_config,
    operation="send",
    method="POST",
    path="/api/users",
    data={"name": "John", "email": "john@example.com"},
    headers={"Content-Type": "application/json"},
)
```

### WebSocket ✅

Real-time bidirectional communication with automatic reconnection.

```python
# Send
handler.run(
    config=ws_config,
    operation="send",
    data={"type": "message", "content": "Hello!"},
)

# Receive
handler.run(
    config=ws_config,
    operation="receive",
    timeout=10.0,
)
```

### MQTT ✅

IoT messaging with pub/sub pattern.

```python
# Publish
handler.run(
    config=mqtt_config,
    operation="send",
    data={"temperature": 22.5, "humidity": 65},
    topic="sensors/room1",
    qos=1,  # Quality of Service: 0, 1, or 2
)

# Subscribe
handler.run(
    config=mqtt_config,
    operation="receive",
    topic="sensors/#",  # Wildcard subscription
    timeout=10.0,
)
```

### gRPC ⚠️

Placeholder implementation (requires proto definitions).

```python
# Coming soon - requires service-specific implementation
```

### AMQP ⚠️

Placeholder implementation (for RabbitMQ, etc.).

```python
# Coming soon - requires broker-specific configuration
```

## 📝 Examples

See `protocol_handler_examples.py` for comprehensive examples:

1. **REST API CRUD Operations**: Full create, read, update, delete examples
2. **Authentication Methods**: All supported auth types
3. **Retry Logic**: Error handling and automatic retries
4. **Circuit Breaker**: Fault tolerance in action
5. **Connection Pooling**: Performance benefits
6. **WebSocket Communication**: Real-time messaging
7. **MQTT Messaging**: IoT pub/sub patterns
8. **Caching Strategies**: Response caching for performance

Run examples:

```bash
# Run all examples
python protocol_handler_examples.py

# Run specific example
python protocol_handler_examples.py 1  # REST API CRUD
python protocol_handler_examples.py 2  # Authentication
python protocol_handler_examples.py 3  # Retry logic
```

## 🔍 Advanced Usage

### Custom Error Handling

```python
try:
    response = handler.run(config=config, operation="send", ...)
    if response.success:
        print(f"Success! Data: {response.data}")
    else:
        print(f"Failed: {response.error}")
except Exception as e:
    logger.error(f"Unexpected error: {str(e)}")
```

### Streaming Responses

```python
from agno.utils.pprint import pprint_run_response

# The run() method returns an Iterator[RunResponse]
response_iterator = handler.run(config=config, operation="send", ...)

# Print streaming response
pprint_run_response(response_iterator, markdown=True)
```

### Session State Management

```python
# Handler persists state across runs with same session_id
handler = ProtocolHandler(
    session_id="my-persistent-session",
    storage=SqliteStorage(
        table_name="protocol_sessions",
        db_file="data/sessions.db",
    ),
)

# Cached data persists across application restarts
```

### Multiple Handlers

```python
# Use different handlers for different services
api_handler = ProtocolHandler(session_id="api-client")
iot_handler = ProtocolHandler(session_id="iot-client")
realtime_handler = ProtocolHandler(session_id="realtime-client")

# Each maintains separate connection pools and caches
```

## 🛡️ Best Practices

### 1. Reuse Handler Instances

```python
# ✅ Good - Reuse handler for connection pooling
handler = ProtocolHandler(session_id="app")
for i in range(100):
    handler.run(config=config, operation="send", path=f"/items/{i}")

# ❌ Bad - Creates new pools each time
for i in range(100):
    handler = ProtocolHandler(session_id=f"app-{i}")
    handler.run(config=config, operation="send", path=f"/items/{i}")
```

### 2. Configure Appropriate Timeouts

```python
# For fast APIs
TimeoutConfig(connect_timeout=5.0, read_timeout=10.0)

# For slow/batch APIs
TimeoutConfig(connect_timeout=30.0, read_timeout=300.0)
```

### 3. Use Circuit Breakers in Production

```python
# Prevent cascading failures
CircuitBreakerConfig(
    failure_threshold=5,
    success_threshold=2,
    timeout=60.0,
    enabled=True,  # Always enable in production
)
```

### 4. Enable Caching for Immutable Data

```python
# Cache GET requests for reference data
handler.run(
    config=config,
    method="GET",
    path="/countries",
    use_cache=True,  # Countries don't change often
)

# Don't cache mutable data
handler.run(
    config=config,
    method="GET",
    path="/user/notifications",
    use_cache=False,  # Notifications change frequently
)
```

### 5. Monitor Metrics

```python
# Retrieve handler metrics periodically
handler_instance = handler._get_handler(config)
metrics = handler_instance.get_metrics()

print(f"Success rate: {metrics.successful_requests / metrics.total_requests * 100:.2f}%")
print(f"Average latency: {metrics.average_latency_ms:.2f}ms")
print(f"Circuit state: {metrics.circuit_state}")
```

## 🐛 Troubleshooting

### Connection Timeouts

```python
# Increase timeouts
timeout_config=TimeoutConfig(
    connect_timeout=30.0,
    read_timeout=60.0,
)
```

### Too Many Retries

```python
# Reduce retry attempts
retry_policy=RetryPolicy(max_attempts=2)
```

### Circuit Breaker Always Open

```python
# Increase failure threshold or timeout
circuit_breaker=CircuitBreakerConfig(
    failure_threshold=10,  # Allow more failures
    timeout=30.0,         # Try recovery sooner
)
```

### SSL/TLS Errors

```python
# Disable SSL verification (development only!)
config = ProtocolConfig(
    protocol_type=ProtocolType.HTTP,
    endpoint="https://localhost:8000",
    verify_ssl=False,  # ⚠️ Don't use in production
)
```

### Memory Issues with Caching

```python
# Disable caching for large responses
handler.run(config=config, operation="send", use_cache=False)

# Or clear cache periodically
handler.session_state["responses"] = {}
```

## 📚 API Reference

### ProtocolHandler Class

**Methods**:
- `run(config, operation, data, use_cache, **kwargs)`: Execute protocol operation

**Operations**:
- `send`: Send data through protocol
- `receive`: Receive data from protocol
- `connect`: Establish connection
- `disconnect`: Close connection

### Protocol Types

- `ProtocolType.HTTP` / `ProtocolType.HTTPS`
- `ProtocolType.WEBSOCKET`
- `ProtocolType.GRPC`
- `ProtocolType.MQTT`
- `ProtocolType.AMQP`

### Auth Types

- `AuthType.NONE`
- `AuthType.BASIC`
- `AuthType.BEARER`
- `AuthType.API_KEY`
- `AuthType.OAUTH2`
- `AuthType.TLS_CERT`

### Circuit States

- `CircuitState.CLOSED`: Normal operation
- `CircuitState.OPEN`: Blocking requests
- `CircuitState.HALF_OPEN`: Testing recovery

## 🤝 Contributing

To extend the Protocol Handler:

1. **Add New Protocol**: Inherit from `BaseProtocolHandler`
2. **Implement Methods**: `connect()`, `disconnect()`, `send()`, `receive()`
3. **Use Decorators**: Leverage `execute_with_retry()` for reliability
4. **Update Factory**: Add to `_get_handler()` in `ProtocolHandler`

Example:

```python
class MyProtocolHandler(BaseProtocolHandler):
    async def connect(self) -> bool:
        # Establish connection
        return True

    async def disconnect(self):
        # Close connection
        pass

    async def send(self, data: Any, **kwargs) -> ProtocolResponse:
        # Send logic with retry
        async def _send():
            # Your send implementation
            return result

        return await self.execute_with_retry(_send)

    async def receive(self, **kwargs) -> ProtocolResponse:
        # Receive logic
        pass
```

## 📄 License

Part of the Agno Framework. See main repository for license details.

## 🔗 Related

- [Agno Framework Documentation](https://docs.agno.dev)
- [Workflow Guide](https://docs.agno.dev/workflows)
- [API Reference](https://docs.agno.dev/api)

---

**Built with ❤️ for the Agno Framework**
