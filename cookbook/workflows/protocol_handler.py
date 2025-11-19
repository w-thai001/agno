"""🌐 Protocol Handler - Universal Communication Protocol Manager!

This advanced workflow demonstrates how to build a sophisticated protocol handler that manages
various communication protocols with a unified interface. The workflow provides:

1. Multi-protocol support (HTTP/HTTPS, WebSocket, gRPC, MQTT, AMQP)
2. Intelligent connection pooling and management
3. Automatic retry with exponential backoff
4. Circuit breaker pattern for fault tolerance
5. Request/response transformation
6. Protocol-specific error handling

Key capabilities:
- Unified interface for multiple protocols
- Connection pooling for improved performance
- Automatic retries with configurable backoff
- Circuit breaker to prevent cascading failures
- TLS/SSL support for secure communication
- Flexible authentication handling
- Performance metrics and monitoring
- Session state management for caching

Supported protocols:
- HTTP/HTTPS: RESTful APIs, webhooks
- WebSocket: Real-time bidirectional communication
- gRPC: High-performance RPC framework
- MQTT: IoT and pub/sub messaging
- AMQP: Enterprise message queuing

Example use cases:
- "Send HTTP GET request to https://api.example.com/users"
- "Connect to WebSocket server at wss://stream.example.com"
- "Publish MQTT message to topic 'sensors/temperature'"
- "Call gRPC service UserService.GetUser"
- "Send AMQP message to queue 'order.processing'"

Run `pip install httpx websockets grpcio paho-mqtt pika agno` to install dependencies.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from enum import Enum
from textwrap import dedent
from typing import Any, Dict, Iterator, Optional, Union
from urllib.parse import urlparse

from agno.utils.log import logger
from agno.workflow import RunEvent, RunResponse, Workflow
from pydantic import BaseModel, Field, HttpUrl


# ============================================================================
# Pydantic Models for Configuration and Responses
# ============================================================================


class ProtocolType(str, Enum):
    """Supported communication protocols."""

    HTTP = "http"
    HTTPS = "https"
    WEBSOCKET = "websocket"
    GRPC = "grpc"
    MQTT = "mqtt"
    AMQP = "amqp"


class AuthType(str, Enum):
    """Supported authentication types."""

    NONE = "none"
    BASIC = "basic"
    BEARER = "bearer"
    API_KEY = "api_key"
    OAUTH2 = "oauth2"
    TLS_CERT = "tls_cert"


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class AuthCredentials(BaseModel):
    """Authentication credentials configuration."""

    auth_type: AuthType = Field(default=AuthType.NONE, description="Authentication type")
    username: Optional[str] = Field(default=None, description="Username for basic auth")
    password: Optional[str] = Field(default=None, description="Password for basic auth")
    token: Optional[str] = Field(default=None, description="Bearer token or API key")
    oauth2_token: Optional[str] = Field(default=None, description="OAuth2 access token")
    cert_path: Optional[str] = Field(default=None, description="Path to TLS certificate")
    key_path: Optional[str] = Field(default=None, description="Path to TLS key")
    headers: Optional[Dict[str, str]] = Field(
        default=None, description="Additional auth headers"
    )


class RetryPolicy(BaseModel):
    """Retry configuration with exponential backoff."""

    max_attempts: int = Field(default=3, description="Maximum retry attempts", ge=1)
    initial_delay: float = Field(default=1.0, description="Initial delay in seconds", ge=0)
    max_delay: float = Field(default=60.0, description="Maximum delay in seconds", ge=0)
    exponential_base: float = Field(default=2.0, description="Exponential backoff base", ge=1)
    jitter: bool = Field(default=True, description="Add random jitter to delays")


class TimeoutConfig(BaseModel):
    """Timeout configuration for various operations."""

    connect_timeout: float = Field(default=10.0, description="Connection timeout in seconds")
    read_timeout: float = Field(default=30.0, description="Read timeout in seconds")
    write_timeout: float = Field(default=30.0, description="Write timeout in seconds")
    pool_timeout: float = Field(default=5.0, description="Pool acquisition timeout in seconds")


class CircuitBreakerConfig(BaseModel):
    """Circuit breaker configuration."""

    failure_threshold: int = Field(
        default=5, description="Number of failures before opening circuit"
    )
    success_threshold: int = Field(
        default=2, description="Number of successes to close circuit from half-open"
    )
    timeout: float = Field(default=60.0, description="Time in seconds before trying half-open")
    enabled: bool = Field(default=True, description="Enable circuit breaker")


class ConnectionPoolConfig(BaseModel):
    """Connection pool configuration."""

    max_connections: int = Field(default=10, description="Maximum pool connections", ge=1)
    max_keepalive_connections: int = Field(
        default=5, description="Maximum keepalive connections", ge=0
    )
    keepalive_expiry: float = Field(
        default=300.0, description="Keepalive expiry in seconds", ge=0
    )


class ProtocolConfig(BaseModel):
    """Protocol-specific configuration."""

    protocol_type: ProtocolType = Field(..., description="Protocol to use")
    endpoint: str = Field(..., description="Target endpoint/URL")
    auth_credentials: AuthCredentials = Field(
        default_factory=AuthCredentials, description="Authentication details"
    )
    retry_policy: RetryPolicy = Field(
        default_factory=RetryPolicy, description="Retry configuration"
    )
    timeout_config: TimeoutConfig = Field(
        default_factory=TimeoutConfig, description="Timeout settings"
    )
    circuit_breaker: CircuitBreakerConfig = Field(
        default_factory=CircuitBreakerConfig, description="Circuit breaker config"
    )
    pool_config: ConnectionPoolConfig = Field(
        default_factory=ConnectionPoolConfig, description="Connection pool config"
    )
    tls_enabled: bool = Field(default=False, description="Enable TLS/SSL")
    verify_ssl: bool = Field(default=True, description="Verify SSL certificates")
    extra_config: Dict[str, Any] = Field(
        default_factory=dict, description="Protocol-specific extra config"
    )


class ProtocolResponse(BaseModel):
    """Protocol operation response."""

    success: bool = Field(..., description="Operation success status")
    status_code: Optional[int] = Field(default=None, description="Status code if applicable")
    data: Optional[Any] = Field(default=None, description="Response data")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    latency_ms: float = Field(..., description="Operation latency in milliseconds")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")
    retry_count: int = Field(default=0, description="Number of retries performed")
    from_cache: bool = Field(default=False, description="Response from cache")


class ConnectionMetrics(BaseModel):
    """Connection and performance metrics."""

    total_requests: int = Field(default=0, description="Total requests made")
    successful_requests: int = Field(default=0, description="Successful requests")
    failed_requests: int = Field(default=0, description="Failed requests")
    total_retries: int = Field(default=0, description="Total retries performed")
    average_latency_ms: float = Field(default=0.0, description="Average latency")
    circuit_state: CircuitState = Field(
        default=CircuitState.CLOSED, description="Circuit breaker state"
    )
    active_connections: int = Field(default=0, description="Active connections")
    pool_size: int = Field(default=0, description="Current pool size")


# ============================================================================
# Circuit Breaker Implementation
# ============================================================================


class CircuitBreaker:
    """Circuit breaker implementation for fault tolerance."""

    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None

    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if not self.config.enabled:
            return func(*args, **kwargs)

        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker entering HALF_OPEN state")
            else:
                raise Exception(
                    f"Circuit breaker is OPEN. Will retry after "
                    f"{self.config.timeout - (time.time() - self.last_failure_time):.1f}s"
                )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    async def call_async(self, func, *args, **kwargs):
        """Execute async function with circuit breaker protection."""
        if not self.config.enabled:
            return await func(*args, **kwargs)

        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker entering HALF_OPEN state")
            else:
                raise Exception(
                    f"Circuit breaker is OPEN. Will retry after "
                    f"{self.config.timeout - (time.time() - self.last_failure_time):.1f}s"
                )

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        return (
            self.last_failure_time is not None
            and time.time() - self.last_failure_time >= self.config.timeout
        )

    def _on_success(self):
        """Handle successful execution."""
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitState.CLOSED
                self.success_count = 0
                logger.info("Circuit breaker CLOSED")

    def _on_failure(self):
        """Handle failed execution."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        self.success_count = 0

        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            logger.warning("Circuit breaker reopened to OPEN")
        elif self.failure_count >= self.config.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(
                f"Circuit breaker OPEN after {self.failure_count} failures"
            )

    def get_state(self) -> CircuitState:
        """Get current circuit state."""
        return self.state

    def reset(self):
        """Manually reset the circuit breaker."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        logger.info("Circuit breaker manually reset")


# ============================================================================
# Base Protocol Handler
# ============================================================================


class BaseProtocolHandler(ABC):
    """Abstract base class for protocol handlers."""

    def __init__(self, config: ProtocolConfig):
        self.config = config
        self.circuit_breaker = CircuitBreaker(config.circuit_breaker)
        self.metrics = ConnectionMetrics()
        self._connection_pool: Dict[str, Any] = {}

    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to the endpoint."""
        pass

    @abstractmethod
    async def disconnect(self):
        """Close connection and cleanup resources."""
        pass

    @abstractmethod
    async def send(self, data: Any, **kwargs) -> ProtocolResponse:
        """Send data through the protocol."""
        pass

    @abstractmethod
    async def receive(self, **kwargs) -> ProtocolResponse:
        """Receive data from the protocol."""
        pass

    async def execute_with_retry(self, func, *args, **kwargs) -> ProtocolResponse:
        """Execute operation with retry logic and exponential backoff."""
        retry_policy = self.config.retry_policy
        last_exception = None

        for attempt in range(retry_policy.max_attempts):
            try:
                start_time = time.time()
                result = await self.circuit_breaker.call_async(func, *args, **kwargs)
                latency_ms = (time.time() - start_time) * 1000

                self.metrics.total_requests += 1
                self.metrics.successful_requests += 1
                self._update_average_latency(latency_ms)

                return ProtocolResponse(
                    success=True,
                    data=result,
                    latency_ms=latency_ms,
                    retry_count=attempt,
                )

            except Exception as e:
                last_exception = e
                self.metrics.total_requests += 1
                self.metrics.failed_requests += 1
                self.metrics.total_retries += 1

                if attempt < retry_policy.max_attempts - 1:
                    delay = self._calculate_retry_delay(attempt, retry_policy)
                    logger.warning(
                        f"Attempt {attempt + 1}/{retry_policy.max_attempts} failed: {str(e)}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"All {retry_policy.max_attempts} attempts failed. Last error: {str(e)}"
                    )

        return ProtocolResponse(
            success=False,
            error=str(last_exception),
            latency_ms=0.0,
            retry_count=retry_policy.max_attempts - 1,
        )

    def _calculate_retry_delay(self, attempt: int, policy: RetryPolicy) -> float:
        """Calculate retry delay with exponential backoff and jitter."""
        delay = min(
            policy.initial_delay * (policy.exponential_base**attempt),
            policy.max_delay,
        )

        if policy.jitter:
            import random

            delay = delay * (0.5 + random.random() * 0.5)

        return delay

    def _update_average_latency(self, new_latency: float):
        """Update rolling average latency."""
        total = self.metrics.successful_requests
        if total == 1:
            self.metrics.average_latency_ms = new_latency
        else:
            current_avg = self.metrics.average_latency_ms
            self.metrics.average_latency_ms = (
                (current_avg * (total - 1)) + new_latency
            ) / total

    def get_metrics(self) -> ConnectionMetrics:
        """Get current connection metrics."""
        self.metrics.circuit_state = self.circuit_breaker.get_state()
        self.metrics.pool_size = len(self._connection_pool)
        return self.metrics

    def _apply_auth(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Apply authentication to headers."""
        auth = self.config.auth_credentials

        if auth.auth_type == AuthType.BEARER and auth.token:
            headers["Authorization"] = f"Bearer {auth.token}"
        elif auth.auth_type == AuthType.API_KEY and auth.token:
            headers["X-API-Key"] = auth.token
        elif auth.auth_type == AuthType.BASIC and auth.username and auth.password:
            import base64

            credentials = f"{auth.username}:{auth.password}"
            encoded = base64.b64encode(credentials.encode()).decode()
            headers["Authorization"] = f"Basic {encoded}"

        if auth.headers:
            headers.update(auth.headers)

        return headers


# ============================================================================
# HTTP/HTTPS Protocol Handler
# ============================================================================


class HTTPHandler(BaseProtocolHandler):
    """HTTP/HTTPS protocol handler with connection pooling."""

    def __init__(self, config: ProtocolConfig):
        super().__init__(config)
        self.client = None

    async def connect(self) -> bool:
        """Initialize HTTP client with connection pooling."""
        try:
            import httpx

            limits = httpx.Limits(
                max_connections=self.config.pool_config.max_connections,
                max_keepalive_connections=self.config.pool_config.max_keepalive_connections,
                keepalive_expiry=self.config.pool_config.keepalive_expiry,
            )

            timeout = httpx.Timeout(
                connect=self.config.timeout_config.connect_timeout,
                read=self.config.timeout_config.read_timeout,
                write=self.config.timeout_config.write_timeout,
                pool=self.config.timeout_config.pool_timeout,
            )

            self.client = httpx.AsyncClient(
                limits=limits,
                timeout=timeout,
                verify=self.config.verify_ssl,
                http2=self.config.extra_config.get("http2", False),
            )

            logger.info(f"HTTP client initialized for {self.config.endpoint}")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize HTTP client: {str(e)}")
            return False

    async def disconnect(self):
        """Close HTTP client and cleanup."""
        if self.client:
            await self.client.aclose()
            logger.info("HTTP client closed")

    async def send(
        self,
        data: Any = None,
        method: str = "GET",
        path: str = "",
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> ProtocolResponse:
        """Send HTTP request."""
        if not self.client:
            await self.connect()

        async def _request():
            request_headers = headers or {}
            request_headers = self._apply_auth(request_headers)

            url = f"{self.config.endpoint.rstrip('/')}/{path.lstrip('/')}"

            if method.upper() in ["GET", "DELETE"]:
                response = await self.client.request(
                    method, url, headers=request_headers, params=data, **kwargs
                )
            else:
                response = await self.client.request(
                    method, url, headers=request_headers, json=data, **kwargs
                )

            response.raise_for_status()
            return {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": response.json() if response.content else None,
            }

        return await self.execute_with_retry(_request)

    async def receive(self, **kwargs) -> ProtocolResponse:
        """Receive is not applicable for HTTP (use send with GET)."""
        return await self.send(method="GET", **kwargs)


# ============================================================================
# WebSocket Protocol Handler
# ============================================================================


class WebSocketHandler(BaseProtocolHandler):
    """WebSocket protocol handler for real-time communication."""

    def __init__(self, config: ProtocolConfig):
        super().__init__(config)
        self.websocket = None

    async def connect(self) -> bool:
        """Establish WebSocket connection."""
        try:
            import websockets

            extra_headers = {}
            self._apply_auth(extra_headers)

            self.websocket = await websockets.connect(
                self.config.endpoint,
                extra_headers=extra_headers,
                ping_interval=self.config.extra_config.get("ping_interval", 20),
                ping_timeout=self.config.extra_config.get("ping_timeout", 10),
            )

            logger.info(f"WebSocket connected to {self.config.endpoint}")
            return True

        except Exception as e:
            logger.error(f"WebSocket connection failed: {str(e)}")
            return False

    async def disconnect(self):
        """Close WebSocket connection."""
        if self.websocket:
            await self.websocket.close()
            logger.info("WebSocket connection closed")

    async def send(self, data: Any, **kwargs) -> ProtocolResponse:
        """Send message through WebSocket."""
        if not self.websocket:
            await self.connect()

        async def _send():
            import json

            message = json.dumps(data) if isinstance(data, dict) else str(data)
            await self.websocket.send(message)
            return {"sent": True, "message": message}

        return await self.execute_with_retry(_send)

    async def receive(self, timeout: Optional[float] = None, **kwargs) -> ProtocolResponse:
        """Receive message from WebSocket."""
        if not self.websocket:
            await self.connect()

        async def _receive():
            import json

            timeout_val = timeout or self.config.timeout_config.read_timeout
            message = await asyncio.wait_for(
                self.websocket.recv(), timeout=timeout_val
            )

            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                data = message

            return {"received": True, "message": data}

        return await self.execute_with_retry(_receive)


# ============================================================================
# MQTT Protocol Handler
# ============================================================================


class MQTTHandler(BaseProtocolHandler):
    """MQTT protocol handler for pub/sub messaging."""

    def __init__(self, config: ProtocolConfig):
        super().__init__(config)
        self.client = None
        self.connected = False
        self.received_messages = []

    async def connect(self) -> bool:
        """Connect to MQTT broker."""
        try:
            import paho.mqtt.client as mqtt

            parsed = urlparse(self.config.endpoint)
            host = parsed.hostname or "localhost"
            port = parsed.port or 1883

            self.client = mqtt.Client(
                client_id=self.config.extra_config.get("client_id", ""),
                protocol=mqtt.MQTTv311,
            )

            # Set authentication
            auth = self.config.auth_credentials
            if auth.username and auth.password:
                self.client.username_pw_set(auth.username, auth.password)

            # Set TLS if enabled
            if self.config.tls_enabled:
                self.client.tls_set()

            # Set callbacks
            def on_connect(client, userdata, flags, rc):
                self.connected = rc == 0
                if rc == 0:
                    logger.info(f"MQTT connected to {host}:{port}")
                else:
                    logger.error(f"MQTT connection failed with code {rc}")

            def on_message(client, userdata, msg):
                self.received_messages.append(
                    {"topic": msg.topic, "payload": msg.payload.decode(), "qos": msg.qos}
                )

            self.client.on_connect = on_connect
            self.client.on_message = on_message

            # Connect
            self.client.connect(host, port, keepalive=60)
            self.client.loop_start()

            # Wait for connection
            max_wait = 5
            waited = 0
            while not self.connected and waited < max_wait:
                await asyncio.sleep(0.1)
                waited += 0.1

            return self.connected

        except Exception as e:
            logger.error(f"MQTT connection failed: {str(e)}")
            return False

    async def disconnect(self):
        """Disconnect from MQTT broker."""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            logger.info("MQTT disconnected")

    async def send(
        self, data: Any, topic: str = "default", qos: int = 1, **kwargs
    ) -> ProtocolResponse:
        """Publish message to MQTT topic."""
        if not self.connected:
            await self.connect()

        async def _publish():
            import json

            payload = json.dumps(data) if isinstance(data, dict) else str(data)
            result = self.client.publish(topic, payload, qos=qos)
            result.wait_for_publish()

            return {
                "published": True,
                "topic": topic,
                "payload": payload,
                "qos": qos,
            }

        return await self.execute_with_retry(_publish)

    async def receive(
        self, topic: str = "#", timeout: float = 5.0, **kwargs
    ) -> ProtocolResponse:
        """Subscribe and receive messages from MQTT topic."""
        if not self.connected:
            await self.connect()

        async def _subscribe():
            # Clear previous messages
            self.received_messages = []

            # Subscribe to topic
            self.client.subscribe(topic)
            logger.info(f"Subscribed to MQTT topic: {topic}")

            # Wait for messages
            await asyncio.sleep(timeout)

            messages = self.received_messages.copy()
            return {"received": True, "topic": topic, "messages": messages}

        return await self.execute_with_retry(_subscribe)


# ============================================================================
# gRPC Protocol Handler (Placeholder)
# ============================================================================


class GRPCHandler(BaseProtocolHandler):
    """gRPC protocol handler."""

    async def connect(self) -> bool:
        """Establish gRPC channel."""
        logger.info("gRPC handler - connect not yet fully implemented")
        return True

    async def disconnect(self):
        """Close gRPC channel."""
        logger.info("gRPC handler - disconnect not yet fully implemented")

    async def send(self, data: Any, **kwargs) -> ProtocolResponse:
        """Call gRPC method."""
        return ProtocolResponse(
            success=False,
            error="gRPC handler not yet fully implemented",
            latency_ms=0.0,
        )

    async def receive(self, **kwargs) -> ProtocolResponse:
        """Receive gRPC stream."""
        return ProtocolResponse(
            success=False,
            error="gRPC handler not yet fully implemented",
            latency_ms=0.0,
        )


# ============================================================================
# AMQP Protocol Handler (Placeholder)
# ============================================================================


class AMQPHandler(BaseProtocolHandler):
    """AMQP protocol handler."""

    async def connect(self) -> bool:
        """Connect to AMQP broker."""
        logger.info("AMQP handler - connect not yet fully implemented")
        return True

    async def disconnect(self):
        """Disconnect from AMQP broker."""
        logger.info("AMQP handler - disconnect not yet fully implemented")

    async def send(self, data: Any, **kwargs) -> ProtocolResponse:
        """Send message to AMQP queue."""
        return ProtocolResponse(
            success=False,
            error="AMQP handler not yet fully implemented",
            latency_ms=0.0,
        )

    async def receive(self, **kwargs) -> ProtocolResponse:
        """Receive message from AMQP queue."""
        return ProtocolResponse(
            success=False,
            error="AMQP handler not yet fully implemented",
            latency_ms=0.0,
        )


# ============================================================================
# Protocol Handler Workflow
# ============================================================================


class ProtocolHandler(Workflow):
    """
    Advanced protocol handler workflow for managing various communication protocols.

    This workflow provides a unified interface for:
    - HTTP/HTTPS requests with connection pooling
    - WebSocket real-time communication
    - MQTT pub/sub messaging
    - gRPC high-performance RPC (placeholder)
    - AMQP message queuing (placeholder)

    Features:
    - Automatic retry with exponential backoff
    - Circuit breaker pattern for fault tolerance
    - Connection pooling and management
    - TLS/SSL support
    - Authentication handling
    - Performance metrics and monitoring
    """

    description: str = dedent("""\
    A sophisticated protocol handler that provides unified access to multiple
    communication protocols with built-in reliability patterns. Handles connection
    management, retries, circuit breaking, and performance monitoring automatically.
    """)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._handlers: Dict[str, BaseProtocolHandler] = {}

    def run(
        self,
        config: ProtocolConfig,
        operation: str = "send",
        data: Any = None,
        use_cache: bool = True,
        **operation_kwargs,
    ) -> Iterator[RunResponse]:
        """
        Execute protocol operation.

        Args:
            config: Protocol configuration
            operation: Operation to perform ('send', 'receive', 'connect', 'disconnect')
            data: Data to send (for send operation)
            use_cache: Use cached responses when available
            **operation_kwargs: Additional operation-specific arguments

        Yields:
            RunResponse: Operation results
        """
        logger.info(
            f"Executing {operation} operation for {config.protocol_type.value} "
            f"protocol on {config.endpoint}"
        )

        # Check cache for repeated requests
        if use_cache and operation == "send":
            cached_response = self._get_cached_response(config, data)
            if cached_response:
                yield RunResponse(
                    content=f"Retrieved from cache:\n{cached_response.model_dump_json(indent=2)}",
                    event=RunEvent.workflow_completed,
                )
                return

        # Get or create protocol handler
        handler = self._get_handler(config)

        # Execute operation asynchronously
        try:
            response = asyncio.run(self._execute_operation(handler, operation, data, operation_kwargs))

            # Cache successful responses
            if response.success and operation == "send":
                self._cache_response(config, data, response)

            # Get metrics
            metrics = handler.get_metrics()

            # Prepare output
            output = dedent(f"""\
            ✅ Protocol Operation Completed

            **Protocol**: {config.protocol_type.value.upper()}
            **Endpoint**: {config.endpoint}
            **Operation**: {operation}

            **Response**:
            {response.model_dump_json(indent=2)}

            **Metrics**:
            - Total Requests: {metrics.total_requests}
            - Successful: {metrics.successful_requests}
            - Failed: {metrics.failed_requests}
            - Average Latency: {metrics.average_latency_ms:.2f}ms
            - Circuit State: {metrics.circuit_state.value}
            - Retries: {metrics.total_retries}
            """)

            yield RunResponse(content=output, event=RunEvent.workflow_completed)

        except Exception as e:
            error_msg = f"❌ Protocol operation failed: {str(e)}"
            logger.error(error_msg)
            yield RunResponse(content=error_msg, event=RunEvent.workflow_completed)

    def _get_handler(self, config: ProtocolConfig) -> BaseProtocolHandler:
        """Get or create protocol handler."""
        cache_key = f"{config.protocol_type.value}:{config.endpoint}"

        if cache_key not in self._handlers:
            if config.protocol_type in [ProtocolType.HTTP, ProtocolType.HTTPS]:
                self._handlers[cache_key] = HTTPHandler(config)
            elif config.protocol_type == ProtocolType.WEBSOCKET:
                self._handlers[cache_key] = WebSocketHandler(config)
            elif config.protocol_type == ProtocolType.MQTT:
                self._handlers[cache_key] = MQTTHandler(config)
            elif config.protocol_type == ProtocolType.GRPC:
                self._handlers[cache_key] = GRPCHandler(config)
            elif config.protocol_type == ProtocolType.AMQP:
                self._handlers[cache_key] = AMQPHandler(config)
            else:
                raise ValueError(f"Unsupported protocol: {config.protocol_type}")

        return self._handlers[cache_key]

    async def _execute_operation(
        self, handler: BaseProtocolHandler, operation: str, data: Any, kwargs: Dict
    ) -> ProtocolResponse:
        """Execute protocol operation."""
        if operation == "connect":
            success = await handler.connect()
            return ProtocolResponse(
                success=success,
                data={"connected": success},
                latency_ms=0.0,
            )
        elif operation == "disconnect":
            await handler.disconnect()
            return ProtocolResponse(
                success=True,
                data={"disconnected": True},
                latency_ms=0.0,
            )
        elif operation == "send":
            return await handler.send(data, **kwargs)
        elif operation == "receive":
            return await handler.receive(**kwargs)
        else:
            raise ValueError(f"Unknown operation: {operation}")

    def _get_cached_response(
        self, config: ProtocolConfig, data: Any
    ) -> Optional[ProtocolResponse]:
        """Get cached response if available."""
        import hashlib
        import json

        cache_key = hashlib.md5(
            f"{config.endpoint}:{json.dumps(data, sort_keys=True)}".encode()
        ).hexdigest()

        cached = self.session_state.get("responses", {}).get(cache_key)
        if cached:
            logger.info(f"Found cached response for {config.endpoint}")
            cached["from_cache"] = True
            return ProtocolResponse(**cached)
        return None

    def _cache_response(self, config: ProtocolConfig, data: Any, response: ProtocolResponse):
        """Cache successful response."""
        import hashlib
        import json

        cache_key = hashlib.md5(
            f"{config.endpoint}:{json.dumps(data, sort_keys=True)}".encode()
        ).hexdigest()

        self.session_state.setdefault("responses", {})
        self.session_state["responses"][cache_key] = response.model_dump()
        logger.info(f"Cached response for {config.endpoint}")

    def cleanup(self):
        """Cleanup all handlers."""
        for handler in self._handlers.values():
            try:
                asyncio.run(handler.disconnect())
            except Exception as e:
                logger.warning(f"Error during cleanup: {str(e)}")


# ============================================================================
# Example Usage
# ============================================================================


if __name__ == "__main__":
    from agno.storage.sqlite import SqliteStorage
    from agno.utils.pprint import pprint_run_response

    # Example 1: HTTP GET Request
    print("\n" + "=" * 80)
    print("Example 1: HTTP GET Request")
    print("=" * 80 + "\n")

    http_config = ProtocolConfig(
        protocol_type=ProtocolType.HTTP,
        endpoint="https://jsonplaceholder.typicode.com",
        retry_policy=RetryPolicy(max_attempts=3, initial_delay=1.0),
        circuit_breaker=CircuitBreakerConfig(failure_threshold=5),
    )

    protocol_handler = ProtocolHandler(
        session_id="http-example",
        storage=SqliteStorage(
            table_name="protocol_handler_workflows",
            db_file="tmp/agno_workflows.db",
        ),
        debug_mode=True,
    )

    # GET request to fetch a user
    response = protocol_handler.run(
        config=http_config,
        operation="send",
        method="GET",
        path="/users/1",
        use_cache=True,
    )

    pprint_run_response(response, markdown=True)

    # Example 2: HTTP POST Request
    print("\n" + "=" * 80)
    print("Example 2: HTTP POST Request")
    print("=" * 80 + "\n")

    post_data = {
        "title": "Protocol Handler Test",
        "body": "Testing the Agno Protocol Handler",
        "userId": 1,
    }

    response = protocol_handler.run(
        config=http_config,
        operation="send",
        method="POST",
        path="/posts",
        data=post_data,
        use_cache=False,
    )

    pprint_run_response(response, markdown=True)

    # Example 3: WebSocket Communication (requires a WebSocket server)
    print("\n" + "=" * 80)
    print("Example 3: WebSocket Communication")
    print("=" * 80 + "\n")

    # Note: This example requires a running WebSocket server
    # Uncomment to test with your WebSocket server
    """
    ws_config = ProtocolConfig(
        protocol_type=ProtocolType.WEBSOCKET,
        endpoint="wss://echo.websocket.org",
        timeout_config=TimeoutConfig(connect_timeout=5.0, read_timeout=10.0),
    )

    ws_handler = ProtocolHandler(
        session_id="websocket-example",
        debug_mode=True,
    )

    # Send a message
    response = ws_handler.run(
        config=ws_config,
        operation="send",
        data={"message": "Hello from Agno Protocol Handler!"},
    )
    pprint_run_response(response, markdown=True)

    # Receive a message
    response = ws_handler.run(
        config=ws_config,
        operation="receive",
        timeout=5.0,
    )
    pprint_run_response(response, markdown=True)
    """

    # Example 4: MQTT Pub/Sub (requires MQTT broker)
    print("\n" + "=" * 80)
    print("Example 4: MQTT Pub/Sub")
    print("=" * 80 + "\n")

    # Note: This example requires a running MQTT broker
    # You can use a public broker like mqtt://test.mosquitto.org
    """
    mqtt_config = ProtocolConfig(
        protocol_type=ProtocolType.MQTT,
        endpoint="mqtt://test.mosquitto.org:1883",
        extra_config={"client_id": "agno-protocol-handler-test"},
    )

    mqtt_handler = ProtocolHandler(
        session_id="mqtt-example",
        debug_mode=True,
    )

    # Publish a message
    response = mqtt_handler.run(
        config=mqtt_config,
        operation="send",
        data={"temperature": 22.5, "humidity": 65},
        topic="agno/sensors/room1",
        qos=1,
    )
    pprint_run_response(response, markdown=True)

    # Subscribe and receive messages
    response = mqtt_handler.run(
        config=mqtt_config,
        operation="receive",
        topic="agno/sensors/#",
        timeout=10.0,
    )
    pprint_run_response(response, markdown=True)
    """

    # Example 5: Authentication with Bearer Token
    print("\n" + "=" * 80)
    print("Example 5: HTTP with Bearer Token Authentication")
    print("=" * 80 + "\n")

    auth_config = ProtocolConfig(
        protocol_type=ProtocolType.HTTP,
        endpoint="https://api.example.com",
        auth_credentials=AuthCredentials(
            auth_type=AuthType.BEARER,
            token="your-api-token-here",
        ),
    )

    # This would make an authenticated request
    # response = protocol_handler.run(
    #     config=auth_config,
    #     operation="send",
    #     method="GET",
    #     path="/protected/resource",
    # )

    print("\n✨ Protocol Handler examples completed!")
    print("Uncomment the WebSocket and MQTT examples to test with live servers.")
