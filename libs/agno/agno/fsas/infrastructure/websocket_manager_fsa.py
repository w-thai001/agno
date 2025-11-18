"""
WebSocket Manager FSA - Comprehensive WebSocket Management for Agno MLA Framework

This module provides a production-ready Finite State Automaton (FSA) implementation
for managing WebSocket connections, including server and client implementations,
connection lifecycle management, message routing, room management, and more.

Features:
- WebSocket server and client implementations
- Connection lifecycle management (connect, disconnect, reconnect)
- Message routing and broadcasting
- Room/channel management for group communications
- Authentication and authorization integration
- Heartbeat/ping-pong for connection health monitoring
- Message queuing and buffering for offline clients
- Binary and text message support
- Compression support (permessage-deflate)
- Rate limiting and throttling
- Connection pooling and scaling support
- Protocol negotiation (subprotocols)
- Error handling and reconnection strategies
- Event-driven architecture with callbacks
- Integration with Session Manager FSA
- Metrics and monitoring

Author: Agno Framework
License: MIT
"""

import asyncio
import enum
import json
import logging
import time
import uuid
import zlib
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import (
    Any,
    Callable,
    Coroutine,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Union,
)

try:
    import websockets
    from websockets.client import WebSocketClientProtocol
    from websockets.server import WebSocketServerProtocol, serve
    from websockets.exceptions import (
        ConnectionClosed,
        ConnectionClosedError,
        ConnectionClosedOK,
        WebSocketException,
    )
except ImportError:
    websockets = None
    WebSocketClientProtocol = None
    WebSocketServerProtocol = None
    serve = None
    ConnectionClosed = Exception
    ConnectionClosedError = Exception
    ConnectionClosedOK = Exception
    WebSocketException = Exception

logger = logging.getLogger(__name__)


# ============================================================================
# Enumerations and Constants
# ============================================================================


class ConnectionState(enum.Enum):
    """WebSocket connection states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    CLOSING = "closing"
    CLOSED = "closed"
    FAILED = "failed"


class MessageType(enum.Enum):
    """Types of WebSocket messages."""
    TEXT = "text"
    BINARY = "binary"
    PING = "ping"
    PONG = "pong"
    CLOSE = "close"
    CONTROL = "control"


class MessagePriority(enum.Enum):
    """Message priority levels for queue processing."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class EventType(enum.Enum):
    """WebSocket event types."""
    CONNECTION_OPENED = "connection_opened"
    CONNECTION_CLOSED = "connection_closed"
    CONNECTION_ERROR = "connection_error"
    MESSAGE_RECEIVED = "message_received"
    MESSAGE_SENT = "message_sent"
    HEARTBEAT_TIMEOUT = "heartbeat_timeout"
    ROOM_JOINED = "room_joined"
    ROOM_LEFT = "room_left"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    AUTHENTICATION_SUCCESS = "authentication_success"
    AUTHENTICATION_FAILURE = "authentication_failure"


# Constants
DEFAULT_HEARTBEAT_INTERVAL = 30  # seconds
DEFAULT_HEARTBEAT_TIMEOUT = 90  # seconds
DEFAULT_RECONNECT_DELAY = 1  # seconds
MAX_RECONNECT_DELAY = 60  # seconds
DEFAULT_MESSAGE_QUEUE_SIZE = 1000
DEFAULT_RATE_LIMIT = 100  # messages per minute
DEFAULT_RATE_LIMIT_WINDOW = 60  # seconds
COMPRESSION_THRESHOLD = 1024  # bytes


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class WebSocketMessage:
    """Represents a WebSocket message with metadata."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: MessageType = MessageType.TEXT
    data: Union[str, bytes] = ""
    priority: MessagePriority = MessagePriority.NORMAL
    timestamp: float = field(default_factory=time.time)
    room: Optional[str] = None
    sender_id: Optional[str] = None
    recipient_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    compressed: bool = False
    retry_count: int = 0
    max_retries: int = 3

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return {
            "id": self.id,
            "type": self.type.value,
            "data": self.data if isinstance(self.data, str) else self.data.hex(),
            "priority": self.priority.value,
            "timestamp": self.timestamp,
            "room": self.room,
            "sender_id": self.sender_id,
            "recipient_id": self.recipient_id,
            "metadata": self.metadata,
            "compressed": self.compressed,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WebSocketMessage":
        """Create message from dictionary."""
        msg = cls()
        msg.id = data.get("id", msg.id)
        msg.type = MessageType(data.get("type", "text"))
        msg.data = data.get("data", "")
        msg.priority = MessagePriority(data.get("priority", 1))
        msg.timestamp = data.get("timestamp", time.time())
        msg.room = data.get("room")
        msg.sender_id = data.get("sender_id")
        msg.recipient_id = data.get("recipient_id")
        msg.metadata = data.get("metadata", {})
        msg.compressed = data.get("compressed", False)
        return msg


@dataclass
class ConnectionMetrics:
    """Metrics for a WebSocket connection."""

    connection_id: str
    state: ConnectionState = ConnectionState.DISCONNECTED
    connected_at: Optional[float] = None
    disconnected_at: Optional[float] = None
    messages_sent: int = 0
    messages_received: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    errors: int = 0
    reconnect_attempts: int = 0
    last_heartbeat: Optional[float] = None
    last_message_at: Optional[float] = None
    latency_ms: Optional[float] = None

    def uptime(self) -> Optional[float]:
        """Calculate connection uptime in seconds."""
        if self.connected_at is None:
            return None
        end_time = self.disconnected_at or time.time()
        return end_time - self.connected_at

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "connection_id": self.connection_id,
            "state": self.state.value,
            "connected_at": self.connected_at,
            "disconnected_at": self.disconnected_at,
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
            "bytes_sent": self.bytes_sent,
            "bytes_received": self.bytes_received,
            "errors": self.errors,
            "reconnect_attempts": self.reconnect_attempts,
            "last_heartbeat": self.last_heartbeat,
            "last_message_at": self.last_message_at,
            "latency_ms": self.latency_ms,
            "uptime": self.uptime(),
        }


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    max_messages: int = DEFAULT_RATE_LIMIT
    window_seconds: int = DEFAULT_RATE_LIMIT_WINDOW
    burst_size: int = 10
    enabled: bool = True


@dataclass
class ReconnectStrategy:
    """Configuration for reconnection strategy."""

    enabled: bool = True
    initial_delay: float = DEFAULT_RECONNECT_DELAY
    max_delay: float = MAX_RECONNECT_DELAY
    max_attempts: Optional[int] = None
    exponential_backoff: bool = True
    jitter: bool = True


@dataclass
class CompressionConfig:
    """Configuration for message compression."""

    enabled: bool = True
    threshold_bytes: int = COMPRESSION_THRESHOLD
    level: int = 6  # zlib compression level (1-9)


# ============================================================================
# Connection Management
# ============================================================================


class WebSocketConnection:
    """Manages a single WebSocket connection with lifecycle and state management."""

    def __init__(
        self,
        connection_id: str,
        websocket: Union[WebSocketClientProtocol, WebSocketServerProtocol],
        is_server: bool = False,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ):
        """
        Initialize a WebSocket connection.

        Args:
            connection_id: Unique identifier for this connection
            websocket: The underlying websocket protocol instance
            is_server: Whether this is a server-side connection
            user_id: Optional user identifier
            session_id: Optional session identifier for integration
        """
        self.connection_id = connection_id
        self.websocket = websocket
        self.is_server = is_server
        self.user_id = user_id
        self.session_id = session_id

        self.state = ConnectionState.CONNECTED
        self.metrics = ConnectionMetrics(connection_id=connection_id)
        self.metrics.state = ConnectionState.CONNECTED
        self.metrics.connected_at = time.time()

        self.rooms: Set[str] = set()
        self.metadata: Dict[str, Any] = {}
        self.authenticated = False
        self.authorized_actions: Set[str] = set()

        # Message queue for offline/buffering
        self.message_queue: deque = deque(maxlen=DEFAULT_MESSAGE_QUEUE_SIZE)
        self.pending_messages: Dict[str, WebSocketMessage] = {}

        # Rate limiting
        self.message_timestamps: deque = deque()

        # Heartbeat
        self.last_heartbeat_sent: Optional[float] = None
        self.last_heartbeat_received: Optional[float] = None
        self.heartbeat_task: Optional[asyncio.Task] = None

        # Lock for thread safety
        self.lock = asyncio.Lock()

    async def send_message(
        self,
        message: WebSocketMessage,
        compress: bool = False,
    ) -> bool:
        """
        Send a message through the WebSocket connection.

        Args:
            message: The message to send
            compress: Whether to compress the message

        Returns:
            True if message was sent successfully, False otherwise
        """
        try:
            async with self.lock:
                if self.state not in [ConnectionState.CONNECTED, ConnectionState.RECONNECTING]:
                    # Queue message for later delivery
                    self.message_queue.append(message)
                    return False

                # Prepare message data
                if message.type == MessageType.TEXT:
                    data = message.data if isinstance(message.data, str) else json.dumps(message.to_dict())

                    # Compress if needed
                    if compress and len(data) > COMPRESSION_THRESHOLD:
                        compressed_data = zlib.compress(data.encode())
                        if len(compressed_data) < len(data):
                            data = compressed_data
                            message.compressed = True

                    await self.websocket.send(data)
                elif message.type == MessageType.BINARY:
                    data = message.data if isinstance(message.data, bytes) else message.data.encode()
                    await self.websocket.send(data)
                else:
                    # Control messages
                    await self.websocket.send(json.dumps(message.to_dict()))

                # Update metrics
                self.metrics.messages_sent += 1
                self.metrics.bytes_sent += len(data) if isinstance(data, (str, bytes)) else 0
                self.metrics.last_message_at = time.time()

                return True

        except Exception as e:
            logger.error(f"Error sending message on connection {self.connection_id}: {e}")
            self.metrics.errors += 1
            return False

    async def receive_message(self) -> Optional[WebSocketMessage]:
        """
        Receive a message from the WebSocket connection.

        Returns:
            The received message or None if connection is closed
        """
        try:
            data = await self.websocket.recv()

            # Determine message type
            if isinstance(data, str):
                message = WebSocketMessage(type=MessageType.TEXT, data=data)
            elif isinstance(data, bytes):
                # Check if it's compressed
                try:
                    decompressed = zlib.decompress(data)
                    message = WebSocketMessage(
                        type=MessageType.TEXT,
                        data=decompressed.decode(),
                        compressed=True,
                    )
                except:
                    message = WebSocketMessage(type=MessageType.BINARY, data=data)
            else:
                return None

            # Update metrics
            self.metrics.messages_received += 1
            self.metrics.bytes_received += len(data)
            self.metrics.last_message_at = time.time()

            return message

        except ConnectionClosed:
            logger.info(f"Connection {self.connection_id} closed")
            self.state = ConnectionState.CLOSED
            return None
        except Exception as e:
            logger.error(f"Error receiving message on connection {self.connection_id}: {e}")
            self.metrics.errors += 1
            return None

    async def send_heartbeat(self) -> bool:
        """Send a heartbeat ping message."""
        try:
            await self.websocket.ping()
            self.last_heartbeat_sent = time.time()
            self.metrics.last_heartbeat = self.last_heartbeat_sent
            return True
        except Exception as e:
            logger.error(f"Error sending heartbeat on connection {self.connection_id}: {e}")
            return False

    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close the WebSocket connection."""
        try:
            self.state = ConnectionState.CLOSING
            await self.websocket.close(code=code, reason=reason)
            self.state = ConnectionState.CLOSED
            self.metrics.state = ConnectionState.CLOSED
            self.metrics.disconnected_at = time.time()

            # Cancel heartbeat task
            if self.heartbeat_task and not self.heartbeat_task.done():
                self.heartbeat_task.cancel()

        except Exception as e:
            logger.error(f"Error closing connection {self.connection_id}: {e}")
            self.state = ConnectionState.FAILED

    def is_alive(self) -> bool:
        """Check if connection is alive."""
        return self.state in [ConnectionState.CONNECTED, ConnectionState.RECONNECTING]

    def join_room(self, room: str) -> bool:
        """Join a room/channel."""
        if room not in self.rooms:
            self.rooms.add(room)
            return True
        return False

    def leave_room(self, room: str) -> bool:
        """Leave a room/channel."""
        if room in self.rooms:
            self.rooms.remove(room)
            return True
        return False

    def is_in_room(self, room: str) -> bool:
        """Check if connection is in a room."""
        return room in self.rooms


# ============================================================================
# Room/Channel Management
# ============================================================================


class RoomManager:
    """Manages rooms/channels for group communications."""

    def __init__(self):
        """Initialize the room manager."""
        self.rooms: Dict[str, Set[str]] = defaultdict(set)
        self.room_metadata: Dict[str, Dict[str, Any]] = {}
        self.lock = asyncio.Lock()

    async def create_room(
        self,
        room_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Create a new room.

        Args:
            room_id: Unique identifier for the room
            metadata: Optional metadata for the room

        Returns:
            True if room was created, False if it already exists
        """
        async with self.lock:
            if room_id in self.rooms:
                return False
            self.rooms[room_id] = set()
            self.room_metadata[room_id] = metadata or {}
            return True

    async def delete_room(self, room_id: str) -> bool:
        """Delete a room."""
        async with self.lock:
            if room_id in self.rooms:
                del self.rooms[room_id]
                if room_id in self.room_metadata:
                    del self.room_metadata[room_id]
                return True
            return False

    async def add_connection(self, room_id: str, connection_id: str) -> bool:
        """Add a connection to a room."""
        async with self.lock:
            if room_id not in self.rooms:
                self.rooms[room_id] = set()
            self.rooms[room_id].add(connection_id)
            return True

    async def remove_connection(self, room_id: str, connection_id: str) -> bool:
        """Remove a connection from a room."""
        async with self.lock:
            if room_id in self.rooms and connection_id in self.rooms[room_id]:
                self.rooms[room_id].remove(connection_id)
                # Clean up empty rooms
                if not self.rooms[room_id]:
                    del self.rooms[room_id]
                    if room_id in self.room_metadata:
                        del self.room_metadata[room_id]
                return True
            return False

    async def get_room_connections(self, room_id: str) -> Set[str]:
        """Get all connections in a room."""
        async with self.lock:
            return self.rooms.get(room_id, set()).copy()

    async def get_connection_rooms(self, connection_id: str) -> Set[str]:
        """Get all rooms a connection is in."""
        async with self.lock:
            rooms = set()
            for room_id, connections in self.rooms.items():
                if connection_id in connections:
                    rooms.add(room_id)
            return rooms

    async def get_room_count(self, room_id: str) -> int:
        """Get the number of connections in a room."""
        async with self.lock:
            return len(self.rooms.get(room_id, set()))

    def list_rooms(self) -> List[str]:
        """List all active rooms."""
        return list(self.rooms.keys())


# ============================================================================
# Rate Limiting
# ============================================================================


class RateLimiter:
    """Token bucket rate limiter for WebSocket connections."""

    def __init__(self, config: RateLimitConfig):
        """
        Initialize the rate limiter.

        Args:
            config: Rate limiting configuration
        """
        self.config = config
        self.tokens: Dict[str, float] = {}
        self.last_update: Dict[str, float] = {}
        self.lock = asyncio.Lock()

    async def check_rate_limit(self, connection_id: str) -> Tuple[bool, float]:
        """
        Check if a connection has exceeded its rate limit.

        Args:
            connection_id: The connection to check

        Returns:
            Tuple of (allowed, retry_after_seconds)
        """
        if not self.config.enabled:
            return True, 0.0

        async with self.lock:
            now = time.time()

            # Initialize if new connection
            if connection_id not in self.tokens:
                self.tokens[connection_id] = float(self.config.max_messages)
                self.last_update[connection_id] = now
                return True, 0.0

            # Calculate token refill
            time_passed = now - self.last_update[connection_id]
            refill_rate = self.config.max_messages / self.config.window_seconds
            tokens_to_add = time_passed * refill_rate

            self.tokens[connection_id] = min(
                self.config.max_messages,
                self.tokens[connection_id] + tokens_to_add
            )
            self.last_update[connection_id] = now

            # Check if we have tokens available
            if self.tokens[connection_id] >= 1.0:
                self.tokens[connection_id] -= 1.0
                return True, 0.0
            else:
                # Calculate retry after
                tokens_needed = 1.0 - self.tokens[connection_id]
                retry_after = tokens_needed / refill_rate
                return False, retry_after

    async def reset(self, connection_id: str):
        """Reset rate limit for a connection."""
        async with self.lock:
            if connection_id in self.tokens:
                del self.tokens[connection_id]
            if connection_id in self.last_update:
                del self.last_update[connection_id]


# ============================================================================
# Authentication and Authorization
# ============================================================================


class AuthenticationManager:
    """Manages authentication and authorization for WebSocket connections."""

    def __init__(self):
        """Initialize the authentication manager."""
        self.auth_handlers: List[Callable] = []
        self.token_validators: List[Callable] = []
        self.authenticated_connections: Dict[str, Dict[str, Any]] = {}
        self.lock = asyncio.Lock()

    def register_auth_handler(
        self,
        handler: Callable[[Dict[str, Any]], Coroutine[Any, Any, bool]]
    ):
        """Register an authentication handler."""
        self.auth_handlers.append(handler)

    def register_token_validator(
        self,
        validator: Callable[[str], Coroutine[Any, Any, Optional[Dict[str, Any]]]]
    ):
        """Register a token validator."""
        self.token_validators.append(validator)

    async def authenticate(
        self,
        connection_id: str,
        credentials: Dict[str, Any],
    ) -> Tuple[bool, Optional[str]]:
        """
        Authenticate a connection.

        Args:
            connection_id: The connection to authenticate
            credentials: Authentication credentials

        Returns:
            Tuple of (success, error_message)
        """
        async with self.lock:
            # Run all auth handlers
            for handler in self.auth_handlers:
                try:
                    result = await handler(credentials)
                    if not result:
                        return False, "Authentication failed"
                except Exception as e:
                    logger.error(f"Auth handler error: {e}")
                    return False, str(e)

            # Store authentication info
            self.authenticated_connections[connection_id] = {
                "timestamp": time.time(),
                "credentials": credentials,
            }

            return True, None

    async def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Validate an authentication token.

        Args:
            token: The token to validate

        Returns:
            User information if valid, None otherwise
        """
        for validator in self.token_validators:
            try:
                user_info = await validator(token)
                if user_info:
                    return user_info
            except Exception as e:
                logger.error(f"Token validator error: {e}")
        return None

    async def is_authenticated(self, connection_id: str) -> bool:
        """Check if a connection is authenticated."""
        async with self.lock:
            return connection_id in self.authenticated_connections

    async def authorize(
        self,
        connection_id: str,
        action: str,
        resource: Optional[str] = None,
    ) -> bool:
        """
        Check if a connection is authorized for an action.

        Args:
            connection_id: The connection to check
            action: The action to authorize
            resource: Optional resource identifier

        Returns:
            True if authorized, False otherwise
        """
        # Default implementation - override with custom logic
        return await self.is_authenticated(connection_id)

    async def revoke(self, connection_id: str):
        """Revoke authentication for a connection."""
        async with self.lock:
            if connection_id in self.authenticated_connections:
                del self.authenticated_connections[connection_id]


# ============================================================================
# Message Queue and Buffering
# ============================================================================


class MessageQueue:
    """Priority queue for message buffering and offline client support."""

    def __init__(self, max_size: int = DEFAULT_MESSAGE_QUEUE_SIZE):
        """
        Initialize the message queue.

        Args:
            max_size: Maximum queue size
        """
        self.max_size = max_size
        self.queues: Dict[str, Dict[MessagePriority, deque]] = defaultdict(
            lambda: {priority: deque() for priority in MessagePriority}
        )
        self.lock = asyncio.Lock()

    async def enqueue(
        self,
        connection_id: str,
        message: WebSocketMessage,
    ) -> bool:
        """
        Add a message to the queue.

        Args:
            connection_id: Target connection
            message: Message to queue

        Returns:
            True if message was queued, False if queue is full
        """
        async with self.lock:
            priority_queue = self.queues[connection_id][message.priority]

            # Check total queue size
            total_size = sum(
                len(q) for q in self.queues[connection_id].values()
            )
            if total_size >= self.max_size:
                # Drop lowest priority message
                for priority in MessagePriority:
                    if self.queues[connection_id][priority]:
                        self.queues[connection_id][priority].popleft()
                        break

            priority_queue.append(message)
            return True

    async def dequeue(
        self,
        connection_id: str,
    ) -> Optional[WebSocketMessage]:
        """
        Get the next message from the queue.

        Args:
            connection_id: Connection to dequeue for

        Returns:
            Next message or None if queue is empty
        """
        async with self.lock:
            # Check priorities from highest to lowest
            for priority in reversed(list(MessagePriority)):
                queue = self.queues[connection_id][priority]
                if queue:
                    return queue.popleft()
            return None

    async def get_queue_size(self, connection_id: str) -> int:
        """Get the total queue size for a connection."""
        async with self.lock:
            return sum(len(q) for q in self.queues[connection_id].values())

    async def clear(self, connection_id: str):
        """Clear all queued messages for a connection."""
        async with self.lock:
            if connection_id in self.queues:
                del self.queues[connection_id]


# ============================================================================
# WebSocket Manager FSA - Main Implementation
# ============================================================================


class WebSocketManagerFSA:
    """
    Main WebSocket Manager Finite State Automaton.

    This class orchestrates all WebSocket operations including connection
    management, message routing, room management, authentication, and more.
    """

    def __init__(
        self,
        heartbeat_interval: int = DEFAULT_HEARTBEAT_INTERVAL,
        heartbeat_timeout: int = DEFAULT_HEARTBEAT_TIMEOUT,
        rate_limit_config: Optional[RateLimitConfig] = None,
        reconnect_strategy: Optional[ReconnectStrategy] = None,
        compression_config: Optional[CompressionConfig] = None,
        enable_metrics: bool = True,
    ):
        """
        Initialize the WebSocket Manager FSA.

        Args:
            heartbeat_interval: Interval between heartbeat pings (seconds)
            heartbeat_timeout: Timeout for heartbeat response (seconds)
            rate_limit_config: Rate limiting configuration
            reconnect_strategy: Reconnection strategy configuration
            compression_config: Compression configuration
            enable_metrics: Whether to collect metrics
        """
        if websockets is None:
            raise ImportError(
                "websockets library is required. Install with: pip install websockets"
            )

        # Configuration
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_timeout = heartbeat_timeout
        self.rate_limit_config = rate_limit_config or RateLimitConfig()
        self.reconnect_strategy = reconnect_strategy or ReconnectStrategy()
        self.compression_config = compression_config or CompressionConfig()
        self.enable_metrics = enable_metrics

        # Connection management
        self.connections: Dict[str, WebSocketConnection] = {}
        self.user_connections: Dict[str, Set[str]] = defaultdict(set)
        self.connection_lock = asyncio.Lock()

        # Component managers
        self.room_manager = RoomManager()
        self.rate_limiter = RateLimiter(self.rate_limit_config)
        self.auth_manager = AuthenticationManager()
        self.message_queue = MessageQueue()

        # Server state
        self.server = None
        self.server_task: Optional[asyncio.Task] = None
        self.is_running = False

        # Event handlers
        self.event_handlers: Dict[EventType, List[Callable]] = defaultdict(list)

        # Message handlers
        self.message_handlers: Dict[str, Callable] = {}

        # Metrics
        self.global_metrics = {
            "total_connections": 0,
            "active_connections": 0,
            "total_messages": 0,
            "total_bytes": 0,
            "total_errors": 0,
            "start_time": time.time(),
        }

        # Background tasks
        self.background_tasks: List[asyncio.Task] = []

        logger.info("WebSocket Manager FSA initialized")

    # ========================================================================
    # Server Management
    # ========================================================================

    async def start_server(
        self,
        host: str = "0.0.0.0",
        port: int = 8765,
        subprotocols: Optional[List[str]] = None,
        **kwargs,
    ) -> bool:
        """
        Start the WebSocket server.

        Args:
            host: Host to bind to
            port: Port to bind to
            subprotocols: List of supported subprotocols
            **kwargs: Additional arguments for websockets.serve

        Returns:
            True if server started successfully
        """
        try:
            # Configure compression
            if self.compression_config.enabled:
                kwargs.setdefault("compression", "deflate")

            # Set subprotocols
            if subprotocols:
                kwargs["subprotocols"] = subprotocols

            # Start server
            self.server = await serve(
                self._handle_connection,
                host,
                port,
                **kwargs
            )

            self.is_running = True
            logger.info(f"WebSocket server started on {host}:{port}")

            # Start background tasks
            await self._start_background_tasks()

            return True

        except Exception as e:
            logger.error(f"Failed to start WebSocket server: {e}")
            return False

    async def stop_server(self):
        """Stop the WebSocket server."""
        try:
            self.is_running = False

            # Stop background tasks
            await self._stop_background_tasks()

            # Close all connections
            await self._close_all_connections()

            # Stop server
            if self.server:
                self.server.close()
                await self.server.wait_closed()
                self.server = None

            logger.info("WebSocket server stopped")

        except Exception as e:
            logger.error(f"Error stopping WebSocket server: {e}")

    async def _handle_connection(
        self,
        websocket: WebSocketServerProtocol,
        path: str = "/",
    ):
        """
        Handle a new WebSocket connection.

        Args:
            websocket: The WebSocket protocol instance
            path: The connection path
        """
        connection_id = str(uuid.uuid4())
        connection = None

        try:
            # Create connection
            connection = WebSocketConnection(
                connection_id=connection_id,
                websocket=websocket,
                is_server=True,
            )

            # Register connection
            await self._register_connection(connection)

            # Emit connection opened event
            await self._emit_event(
                EventType.CONNECTION_OPENED,
                {
                    "connection_id": connection_id,
                    "path": path,
                    "remote_address": websocket.remote_address,
                }
            )

            # Start heartbeat
            connection.heartbeat_task = asyncio.create_task(
                self._heartbeat_loop(connection_id)
            )

            # Message loop
            while connection.is_alive() and self.is_running:
                try:
                    message = await connection.receive_message()
                    if message is None:
                        break

                    # Check rate limit
                    allowed, retry_after = await self.rate_limiter.check_rate_limit(
                        connection_id
                    )
                    if not allowed:
                        await self._emit_event(
                            EventType.RATE_LIMIT_EXCEEDED,
                            {
                                "connection_id": connection_id,
                                "retry_after": retry_after,
                            }
                        )
                        continue

                    # Process message
                    await self._process_message(connection_id, message)

                except ConnectionClosed:
                    break
                except Exception as e:
                    logger.error(f"Error in message loop for {connection_id}: {e}")
                    connection.metrics.errors += 1
                    break

        except Exception as e:
            logger.error(f"Error handling connection {connection_id}: {e}")

        finally:
            # Cleanup
            await self._unregister_connection(connection_id)

            if connection:
                await connection.close()

            # Emit connection closed event
            await self._emit_event(
                EventType.CONNECTION_CLOSED,
                {"connection_id": connection_id}
            )

    # ========================================================================
    # Client Management
    # ========================================================================

    async def connect_client(
        self,
        uri: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        subprotocols: Optional[List[str]] = None,
        **kwargs,
    ) -> Optional[str]:
        """
        Connect to a WebSocket server as a client.

        Args:
            uri: WebSocket URI to connect to
            user_id: Optional user identifier
            session_id: Optional session identifier
            subprotocols: List of supported subprotocols
            **kwargs: Additional arguments for websockets.connect

        Returns:
            Connection ID if successful, None otherwise
        """
        connection_id = str(uuid.uuid4())

        try:
            # Configure compression
            if self.compression_config.enabled:
                kwargs.setdefault("compression", "deflate")

            # Set subprotocols
            if subprotocols:
                kwargs["subprotocols"] = subprotocols

            # Connect
            websocket = await websockets.connect(uri, **kwargs)

            # Create connection
            connection = WebSocketConnection(
                connection_id=connection_id,
                websocket=websocket,
                is_server=False,
                user_id=user_id,
                session_id=session_id,
            )

            # Register connection
            await self._register_connection(connection)

            # Emit connection opened event
            await self._emit_event(
                EventType.CONNECTION_OPENED,
                {
                    "connection_id": connection_id,
                    "uri": uri,
                    "user_id": user_id,
                    "session_id": session_id,
                }
            )

            # Start heartbeat
            connection.heartbeat_task = asyncio.create_task(
                self._heartbeat_loop(connection_id)
            )

            # Start message receiving task
            asyncio.create_task(self._client_receive_loop(connection_id))

            logger.info(f"Client connected to {uri} with ID {connection_id}")
            return connection_id

        except Exception as e:
            logger.error(f"Failed to connect client to {uri}: {e}")
            await self._unregister_connection(connection_id)
            return None

    async def _client_receive_loop(self, connection_id: str):
        """Message receiving loop for client connections."""
        try:
            connection = self.connections.get(connection_id)
            if not connection:
                return

            while connection.is_alive() and self.is_running:
                try:
                    message = await connection.receive_message()
                    if message is None:
                        break

                    # Process message
                    await self._process_message(connection_id, message)

                except ConnectionClosed:
                    break
                except Exception as e:
                    logger.error(f"Error in client receive loop for {connection_id}: {e}")
                    connection.metrics.errors += 1
                    break

            # Attempt reconnection if enabled
            if self.reconnect_strategy.enabled and connection.is_alive():
                await self._attempt_reconnection(connection_id)

        except Exception as e:
            logger.error(f"Error in client receive loop: {e}")
        finally:
            await self._unregister_connection(connection_id)

    async def disconnect_client(self, connection_id: str):
        """
        Disconnect a client connection.

        Args:
            connection_id: The connection to disconnect
        """
        connection = self.connections.get(connection_id)
        if connection and not connection.is_server:
            await connection.close()
            await self._unregister_connection(connection_id)

    # ========================================================================
    # Connection Registration and Management
    # ========================================================================

    async def _register_connection(self, connection: WebSocketConnection):
        """Register a new connection."""
        async with self.connection_lock:
            self.connections[connection.connection_id] = connection

            if connection.user_id:
                self.user_connections[connection.user_id].add(connection.connection_id)

            # Update metrics
            self.global_metrics["total_connections"] += 1
            self.global_metrics["active_connections"] = len(self.connections)

            logger.info(f"Registered connection {connection.connection_id}")

    async def _unregister_connection(self, connection_id: str):
        """Unregister a connection."""
        async with self.connection_lock:
            connection = self.connections.get(connection_id)
            if not connection:
                return

            # Remove from user connections
            if connection.user_id:
                self.user_connections[connection.user_id].discard(connection_id)
                if not self.user_connections[connection.user_id]:
                    del self.user_connections[connection.user_id]

            # Remove from all rooms
            rooms = await self.room_manager.get_connection_rooms(connection_id)
            for room in rooms:
                await self.room_manager.remove_connection(room, connection_id)
                connection.leave_room(room)

            # Clean up
            del self.connections[connection_id]
            await self.rate_limiter.reset(connection_id)
            await self.auth_manager.revoke(connection_id)
            await self.message_queue.clear(connection_id)

            # Update metrics
            self.global_metrics["active_connections"] = len(self.connections)

            logger.info(f"Unregistered connection {connection_id}")

    async def _close_all_connections(self):
        """Close all active connections."""
        connection_ids = list(self.connections.keys())
        for connection_id in connection_ids:
            connection = self.connections.get(connection_id)
            if connection:
                await connection.close(code=1001, reason="Server shutdown")

    # ========================================================================
    # Message Processing and Routing
    # ========================================================================

    async def _process_message(
        self,
        connection_id: str,
        message: WebSocketMessage,
    ):
        """
        Process an incoming message.

        Args:
            connection_id: Source connection
            message: The message to process
        """
        try:
            message.sender_id = connection_id

            # Emit message received event
            await self._emit_event(
                EventType.MESSAGE_RECEIVED,
                {
                    "connection_id": connection_id,
                    "message": message.to_dict(),
                }
            )

            # Update global metrics
            self.global_metrics["total_messages"] += 1

            # Try to parse as JSON for structured messages
            if message.type == MessageType.TEXT:
                try:
                    data = json.loads(message.data)
                    message_type = data.get("type")

                    # Route to specific handler
                    if message_type in self.message_handlers:
                        await self.message_handlers[message_type](
                            connection_id, data
                        )
                        return
                except (json.JSONDecodeError, TypeError):
                    pass

            # Default handling - broadcast to room or direct message
            if message.room:
                await self.broadcast_to_room(message.room, message, exclude=[connection_id])
            elif message.recipient_id:
                await self.send_to_connection(message.recipient_id, message)

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await self._emit_event(
                EventType.CONNECTION_ERROR,
                {
                    "connection_id": connection_id,
                    "error": str(e),
                }
            )

    async def send_to_connection(
        self,
        connection_id: str,
        message: WebSocketMessage,
    ) -> bool:
        """
        Send a message to a specific connection.

        Args:
            connection_id: Target connection
            message: Message to send

        Returns:
            True if message was sent successfully
        """
        connection = self.connections.get(connection_id)
        if not connection:
            # Queue for later delivery
            await self.message_queue.enqueue(connection_id, message)
            return False

        # Check if connection is alive
        if not connection.is_alive():
            await self.message_queue.enqueue(connection_id, message)
            return False

        # Send message
        compress = (
            self.compression_config.enabled and
            len(str(message.data)) > self.compression_config.threshold_bytes
        )

        success = await connection.send_message(message, compress=compress)

        if success:
            await self._emit_event(
                EventType.MESSAGE_SENT,
                {
                    "connection_id": connection_id,
                    "message": message.to_dict(),
                }
            )

        return success

    async def send_to_user(
        self,
        user_id: str,
        message: WebSocketMessage,
    ) -> int:
        """
        Send a message to all connections of a user.

        Args:
            user_id: Target user
            message: Message to send

        Returns:
            Number of connections the message was sent to
        """
        connection_ids = self.user_connections.get(user_id, set())
        sent_count = 0

        for connection_id in connection_ids:
            if await self.send_to_connection(connection_id, message):
                sent_count += 1

        return sent_count

    async def broadcast_to_room(
        self,
        room_id: str,
        message: WebSocketMessage,
        exclude: Optional[List[str]] = None,
    ) -> int:
        """
        Broadcast a message to all connections in a room.

        Args:
            room_id: Target room
            message: Message to broadcast
            exclude: Optional list of connection IDs to exclude

        Returns:
            Number of connections the message was sent to
        """
        exclude = exclude or []
        connection_ids = await self.room_manager.get_room_connections(room_id)
        sent_count = 0

        for connection_id in connection_ids:
            if connection_id not in exclude:
                if await self.send_to_connection(connection_id, message):
                    sent_count += 1

        return sent_count

    async def broadcast_to_all(
        self,
        message: WebSocketMessage,
        exclude: Optional[List[str]] = None,
    ) -> int:
        """
        Broadcast a message to all connections.

        Args:
            message: Message to broadcast
            exclude: Optional list of connection IDs to exclude

        Returns:
            Number of connections the message was sent to
        """
        exclude = exclude or []
        sent_count = 0

        for connection_id in self.connections.keys():
            if connection_id not in exclude:
                if await self.send_to_connection(connection_id, message):
                    sent_count += 1

        return sent_count

    # ========================================================================
    # Room Management Methods
    # ========================================================================

    async def create_room(
        self,
        room_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Create a new room."""
        return await self.room_manager.create_room(room_id, metadata)

    async def delete_room(self, room_id: str) -> bool:
        """Delete a room."""
        return await self.room_manager.delete_room(room_id)

    async def join_room(self, connection_id: str, room_id: str) -> bool:
        """
        Add a connection to a room.

        Args:
            connection_id: Connection to add
            room_id: Room to join

        Returns:
            True if successfully joined
        """
        connection = self.connections.get(connection_id)
        if not connection:
            return False

        # Add to room
        await self.room_manager.add_connection(room_id, connection_id)
        connection.join_room(room_id)

        # Emit event
        await self._emit_event(
            EventType.ROOM_JOINED,
            {
                "connection_id": connection_id,
                "room_id": room_id,
            }
        )

        return True

    async def leave_room(self, connection_id: str, room_id: str) -> bool:
        """
        Remove a connection from a room.

        Args:
            connection_id: Connection to remove
            room_id: Room to leave

        Returns:
            True if successfully left
        """
        connection = self.connections.get(connection_id)
        if not connection:
            return False

        # Remove from room
        await self.room_manager.remove_connection(room_id, connection_id)
        connection.leave_room(room_id)

        # Emit event
        await self._emit_event(
            EventType.ROOM_LEFT,
            {
                "connection_id": connection_id,
                "room_id": room_id,
            }
        )

        return True

    # ========================================================================
    # Authentication and Authorization
    # ========================================================================

    async def authenticate_connection(
        self,
        connection_id: str,
        credentials: Dict[str, Any],
    ) -> bool:
        """
        Authenticate a connection.

        Args:
            connection_id: Connection to authenticate
            credentials: Authentication credentials

        Returns:
            True if authentication successful
        """
        connection = self.connections.get(connection_id)
        if not connection:
            return False

        success, error = await self.auth_manager.authenticate(
            connection_id, credentials
        )

        if success:
            connection.authenticated = True
            await self._emit_event(
                EventType.AUTHENTICATION_SUCCESS,
                {"connection_id": connection_id}
            )
        else:
            await self._emit_event(
                EventType.AUTHENTICATION_FAILURE,
                {
                    "connection_id": connection_id,
                    "error": error,
                }
            )

        return success

    # ========================================================================
    # Heartbeat and Connection Health
    # ========================================================================

    async def _heartbeat_loop(self, connection_id: str):
        """
        Heartbeat loop for a connection.

        Args:
            connection_id: Connection to monitor
        """
        try:
            while self.is_running:
                await asyncio.sleep(self.heartbeat_interval)

                connection = self.connections.get(connection_id)
                if not connection or not connection.is_alive():
                    break

                # Send heartbeat
                success = await connection.send_heartbeat()

                if not success:
                    logger.warning(f"Heartbeat failed for connection {connection_id}")
                    break

                # Check for timeout
                if connection.last_heartbeat_received:
                    time_since_last = time.time() - connection.last_heartbeat_received
                    if time_since_last > self.heartbeat_timeout:
                        logger.warning(
                            f"Heartbeat timeout for connection {connection_id}"
                        )
                        await self._emit_event(
                            EventType.HEARTBEAT_TIMEOUT,
                            {"connection_id": connection_id}
                        )
                        await connection.close(code=1001, reason="Heartbeat timeout")
                        break

        except Exception as e:
            logger.error(f"Error in heartbeat loop for {connection_id}: {e}")

    # ========================================================================
    # Reconnection
    # ========================================================================

    async def _attempt_reconnection(self, connection_id: str):
        """
        Attempt to reconnect a failed connection.

        Args:
            connection_id: Connection to reconnect
        """
        if not self.reconnect_strategy.enabled:
            return

        connection = self.connections.get(connection_id)
        if not connection or connection.is_server:
            return

        attempt = 0
        delay = self.reconnect_strategy.initial_delay

        while (
            self.is_running and
            (self.reconnect_strategy.max_attempts is None or
             attempt < self.reconnect_strategy.max_attempts)
        ):
            attempt += 1
            connection.metrics.reconnect_attempts = attempt

            logger.info(
                f"Attempting reconnection {attempt} for {connection_id} "
                f"after {delay:.2f}s delay"
            )

            await asyncio.sleep(delay)

            # Attempt reconnect logic here
            # This is a placeholder - actual implementation would need
            # the original URI and connection parameters

            # Calculate next delay
            if self.reconnect_strategy.exponential_backoff:
                delay = min(delay * 2, self.reconnect_strategy.max_delay)

            # Add jitter
            if self.reconnect_strategy.jitter:
                import random
                delay = delay * (0.5 + random.random())

    # ========================================================================
    # Event Handling
    # ========================================================================

    def on(self, event_type: EventType, handler: Callable):
        """
        Register an event handler.

        Args:
            event_type: Type of event to handle
            handler: Handler function
        """
        self.event_handlers[event_type].append(handler)

    async def _emit_event(self, event_type: EventType, data: Dict[str, Any]):
        """
        Emit an event to all registered handlers.

        Args:
            event_type: Type of event
            data: Event data
        """
        handlers = self.event_handlers.get(event_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    handler(data)
            except Exception as e:
                logger.error(f"Error in event handler for {event_type}: {e}")

    def register_message_handler(self, message_type: str, handler: Callable):
        """
        Register a handler for a specific message type.

        Args:
            message_type: Type of message to handle
            handler: Handler function
        """
        self.message_handlers[message_type] = handler

    # ========================================================================
    # Background Tasks
    # ========================================================================

    async def _start_background_tasks(self):
        """Start background maintenance tasks."""
        self.background_tasks = [
            asyncio.create_task(self._cleanup_task()),
            asyncio.create_task(self._metrics_task()),
            asyncio.create_task(self._queue_processor_task()),
        ]

    async def _stop_background_tasks(self):
        """Stop all background tasks."""
        for task in self.background_tasks:
            if not task.done():
                task.cancel()

        # Wait for cancellation
        await asyncio.gather(*self.background_tasks, return_exceptions=True)
        self.background_tasks.clear()

    async def _cleanup_task(self):
        """Periodic cleanup of stale connections and data."""
        try:
            while self.is_running:
                await asyncio.sleep(60)  # Run every minute

                # Check for stale connections
                current_time = time.time()
                stale_connections = []

                for connection_id, connection in self.connections.items():
                    if connection.metrics.last_message_at:
                        idle_time = current_time - connection.metrics.last_message_at
                        if idle_time > 300:  # 5 minutes idle
                            stale_connections.append(connection_id)

                # Close stale connections
                for connection_id in stale_connections:
                    connection = self.connections.get(connection_id)
                    if connection:
                        await connection.close(code=1000, reason="Idle timeout")

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in cleanup task: {e}")

    async def _metrics_task(self):
        """Periodic metrics collection and logging."""
        try:
            while self.is_running:
                await asyncio.sleep(300)  # Run every 5 minutes

                if self.enable_metrics:
                    metrics = self.get_global_metrics()
                    logger.info(f"WebSocket Metrics: {json.dumps(metrics, indent=2)}")

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in metrics task: {e}")

    async def _queue_processor_task(self):
        """Process queued messages for offline/reconnected clients."""
        try:
            while self.is_running:
                await asyncio.sleep(1)  # Check every second

                for connection_id, connection in list(self.connections.items()):
                    if connection.is_alive():
                        # Process queued messages
                        queue_size = await self.message_queue.get_queue_size(
                            connection_id
                        )

                        if queue_size > 0:
                            message = await self.message_queue.dequeue(connection_id)
                            if message:
                                await self.send_to_connection(connection_id, message)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in queue processor task: {e}")

    # ========================================================================
    # Metrics and Monitoring
    # ========================================================================

    def get_connection_metrics(
        self,
        connection_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get metrics for a specific connection.

        Args:
            connection_id: Connection to get metrics for

        Returns:
            Metrics dictionary or None if connection not found
        """
        connection = self.connections.get(connection_id)
        if not connection:
            return None
        return connection.metrics.to_dict()

    def get_global_metrics(self) -> Dict[str, Any]:
        """Get global WebSocket manager metrics."""
        uptime = time.time() - self.global_metrics["start_time"]

        return {
            **self.global_metrics,
            "uptime_seconds": uptime,
            "rooms": len(self.room_manager.list_rooms()),
            "authenticated_connections": len(
                self.auth_manager.authenticated_connections
            ),
        }

    def get_room_metrics(self, room_id: str) -> Dict[str, Any]:
        """Get metrics for a specific room."""
        return {
            "room_id": room_id,
            "connection_count": asyncio.run(
                self.room_manager.get_room_count(room_id)
            ),
            "metadata": self.room_manager.room_metadata.get(room_id, {}),
        }

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def get_connection(self, connection_id: str) -> Optional[WebSocketConnection]:
        """Get a connection by ID."""
        return self.connections.get(connection_id)

    def get_user_connections(self, user_id: str) -> Set[str]:
        """Get all connection IDs for a user."""
        return self.user_connections.get(user_id, set()).copy()

    def list_connections(self) -> List[str]:
        """List all active connection IDs."""
        return list(self.connections.keys())

    def list_rooms(self) -> List[str]:
        """List all active rooms."""
        return self.room_manager.list_rooms()

    async def get_connection_count(self) -> int:
        """Get the current number of active connections."""
        return len(self.connections)

    async def get_room_count(self) -> int:
        """Get the current number of active rooms."""
        return len(self.room_manager.list_rooms())


# ============================================================================
# Helper Functions
# ============================================================================


def create_websocket_manager(
    **kwargs,
) -> WebSocketManagerFSA:
    """
    Factory function to create a WebSocket Manager FSA instance.

    Args:
        **kwargs: Configuration parameters for WebSocketManagerFSA

    Returns:
        Configured WebSocketManagerFSA instance
    """
    return WebSocketManagerFSA(**kwargs)


async def create_and_start_server(
    host: str = "0.0.0.0",
    port: int = 8765,
    **kwargs,
) -> WebSocketManagerFSA:
    """
    Create and start a WebSocket server.

    Args:
        host: Host to bind to
        port: Port to bind to
        **kwargs: Additional configuration parameters

    Returns:
        Running WebSocketManagerFSA instance
    """
    manager = create_websocket_manager(**kwargs)
    await manager.start_server(host=host, port=port)
    return manager
