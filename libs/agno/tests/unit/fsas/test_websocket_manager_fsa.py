"""
Comprehensive Test Suite for WebSocket Manager FSA

This module provides extensive pytest tests for the WebSocket Manager FSA,
covering all major functionality including connection management, message routing,
room management, authentication, rate limiting, and more.

Author: Agno Framework
License: MIT
"""

import asyncio
import json
import time
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from agno.fsas.infrastructure.websocket_manager_fsa import (
    WebSocketManagerFSA,
    WebSocketConnection,
    WebSocketMessage,
    ConnectionState,
    MessageType,
    MessagePriority,
    EventType,
    ConnectionMetrics,
    RateLimitConfig,
    ReconnectStrategy,
    CompressionConfig,
    RoomManager,
    RateLimiter,
    AuthenticationManager,
    MessageQueue,
    create_websocket_manager,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket connection."""
    ws = AsyncMock()
    ws.send = AsyncMock()
    ws.recv = AsyncMock()
    ws.ping = AsyncMock()
    ws.close = AsyncMock()
    ws.remote_address = ("127.0.0.1", 12345)
    return ws


@pytest.fixture
def websocket_manager():
    """Create a WebSocket Manager FSA instance."""
    return WebSocketManagerFSA(
        heartbeat_interval=10,
        heartbeat_timeout=30,
        enable_metrics=True,
    )


@pytest.fixture
def rate_limit_config():
    """Create a rate limit configuration."""
    return RateLimitConfig(
        max_messages=10,
        window_seconds=60,
        burst_size=5,
        enabled=True,
    )


@pytest.fixture
def reconnect_strategy():
    """Create a reconnect strategy."""
    return ReconnectStrategy(
        enabled=True,
        initial_delay=1,
        max_delay=30,
        max_attempts=5,
        exponential_backoff=True,
        jitter=True,
    )


@pytest.fixture
def compression_config():
    """Create a compression configuration."""
    return CompressionConfig(
        enabled=True,
        threshold_bytes=1024,
        level=6,
    )


# ============================================================================
# Test WebSocketMessage
# ============================================================================


def test_websocket_message_creation():
    """Test WebSocketMessage creation and defaults."""
    msg = WebSocketMessage()
    assert msg.id is not None
    assert msg.type == MessageType.TEXT
    assert msg.data == ""
    assert msg.priority == MessagePriority.NORMAL
    assert msg.timestamp is not None
    assert msg.room is None
    assert msg.sender_id is None
    assert msg.recipient_id is None
    assert msg.compressed is False
    assert msg.retry_count == 0


def test_websocket_message_to_dict():
    """Test WebSocketMessage to_dict conversion."""
    msg = WebSocketMessage(
        data="test message",
        room="test_room",
        sender_id="sender_1",
    )
    msg_dict = msg.to_dict()

    assert msg_dict["id"] == msg.id
    assert msg_dict["type"] == "text"
    assert msg_dict["data"] == "test message"
    assert msg_dict["room"] == "test_room"
    assert msg_dict["sender_id"] == "sender_1"


def test_websocket_message_from_dict():
    """Test WebSocketMessage from_dict creation."""
    data = {
        "id": "test_id",
        "type": "binary",
        "data": "test",
        "priority": 2,
        "room": "room1",
    }
    msg = WebSocketMessage.from_dict(data)

    assert msg.id == "test_id"
    assert msg.type == MessageType.BINARY
    assert msg.data == "test"
    assert msg.priority == MessagePriority.HIGH


def test_websocket_message_with_metadata():
    """Test WebSocketMessage with custom metadata."""
    msg = WebSocketMessage(
        data="test",
        metadata={"key": "value", "timestamp": 123456},
    )
    assert msg.metadata["key"] == "value"
    assert msg.metadata["timestamp"] == 123456


# ============================================================================
# Test ConnectionMetrics
# ============================================================================


def test_connection_metrics_creation():
    """Test ConnectionMetrics creation."""
    metrics = ConnectionMetrics(connection_id="test_conn")
    assert metrics.connection_id == "test_conn"
    assert metrics.state == ConnectionState.DISCONNECTED
    assert metrics.messages_sent == 0
    assert metrics.messages_received == 0
    assert metrics.errors == 0


def test_connection_metrics_uptime():
    """Test ConnectionMetrics uptime calculation."""
    metrics = ConnectionMetrics(connection_id="test_conn")
    metrics.connected_at = time.time() - 100
    uptime = metrics.uptime()
    assert uptime is not None
    assert 99 <= uptime <= 101


def test_connection_metrics_uptime_disconnected():
    """Test ConnectionMetrics uptime with disconnection."""
    metrics = ConnectionMetrics(connection_id="test_conn")
    metrics.connected_at = time.time() - 100
    metrics.disconnected_at = metrics.connected_at + 50
    uptime = metrics.uptime()
    assert uptime is not None
    assert 49 <= uptime <= 51


def test_connection_metrics_to_dict():
    """Test ConnectionMetrics to_dict conversion."""
    metrics = ConnectionMetrics(connection_id="test_conn")
    metrics.messages_sent = 10
    metrics.bytes_sent = 1024
    metrics_dict = metrics.to_dict()

    assert metrics_dict["connection_id"] == "test_conn"
    assert metrics_dict["messages_sent"] == 10
    assert metrics_dict["bytes_sent"] == 1024


# ============================================================================
# Test WebSocketConnection
# ============================================================================


@pytest.mark.asyncio
async def test_websocket_connection_creation(mock_websocket):
    """Test WebSocketConnection creation."""
    connection = WebSocketConnection(
        connection_id="test_conn",
        websocket=mock_websocket,
        is_server=True,
        user_id="user_1",
        session_id="session_1",
    )

    assert connection.connection_id == "test_conn"
    assert connection.is_server is True
    assert connection.user_id == "user_1"
    assert connection.session_id == "session_1"
    assert connection.state == ConnectionState.CONNECTED
    assert connection.authenticated is False


@pytest.mark.asyncio
async def test_websocket_connection_send_message(mock_websocket):
    """Test sending a message through WebSocketConnection."""
    connection = WebSocketConnection(
        connection_id="test_conn",
        websocket=mock_websocket,
    )

    msg = WebSocketMessage(data="test message")
    result = await connection.send_message(msg)

    assert result is True
    mock_websocket.send.assert_called_once()
    assert connection.metrics.messages_sent == 1


@pytest.mark.asyncio
async def test_websocket_connection_send_binary_message(mock_websocket):
    """Test sending a binary message through WebSocketConnection."""
    connection = WebSocketConnection(
        connection_id="test_conn",
        websocket=mock_websocket,
    )

    msg = WebSocketMessage(type=MessageType.BINARY, data=b"binary data")
    result = await connection.send_message(msg)

    assert result is True
    mock_websocket.send.assert_called_once_with(b"binary data")


@pytest.mark.asyncio
async def test_websocket_connection_receive_message(mock_websocket):
    """Test receiving a message through WebSocketConnection."""
    mock_websocket.recv.return_value = "test message"

    connection = WebSocketConnection(
        connection_id="test_conn",
        websocket=mock_websocket,
    )

    msg = await connection.receive_message()

    assert msg is not None
    assert msg.type == MessageType.TEXT
    assert msg.data == "test message"
    assert connection.metrics.messages_received == 1


@pytest.mark.asyncio
async def test_websocket_connection_send_heartbeat(mock_websocket):
    """Test sending heartbeat through WebSocketConnection."""
    connection = WebSocketConnection(
        connection_id="test_conn",
        websocket=mock_websocket,
    )

    result = await connection.send_heartbeat()

    assert result is True
    mock_websocket.ping.assert_called_once()
    assert connection.last_heartbeat_sent is not None


@pytest.mark.asyncio
async def test_websocket_connection_close(mock_websocket):
    """Test closing WebSocketConnection."""
    connection = WebSocketConnection(
        connection_id="test_conn",
        websocket=mock_websocket,
    )

    await connection.close(code=1000, reason="Test close")

    assert connection.state == ConnectionState.CLOSED
    mock_websocket.close.assert_called_once_with(code=1000, reason="Test close")


@pytest.mark.asyncio
async def test_websocket_connection_join_room(mock_websocket):
    """Test joining a room."""
    connection = WebSocketConnection(
        connection_id="test_conn",
        websocket=mock_websocket,
    )

    result = connection.join_room("room1")
    assert result is True
    assert "room1" in connection.rooms

    # Try joining again
    result = connection.join_room("room1")
    assert result is False


@pytest.mark.asyncio
async def test_websocket_connection_leave_room(mock_websocket):
    """Test leaving a room."""
    connection = WebSocketConnection(
        connection_id="test_conn",
        websocket=mock_websocket,
    )

    connection.join_room("room1")
    result = connection.leave_room("room1")
    assert result is True
    assert "room1" not in connection.rooms


@pytest.mark.asyncio
async def test_websocket_connection_is_in_room(mock_websocket):
    """Test checking if connection is in a room."""
    connection = WebSocketConnection(
        connection_id="test_conn",
        websocket=mock_websocket,
    )

    connection.join_room("room1")
    assert connection.is_in_room("room1") is True
    assert connection.is_in_room("room2") is False


# ============================================================================
# Test RoomManager
# ============================================================================


@pytest.mark.asyncio
async def test_room_manager_create_room():
    """Test creating a room."""
    room_manager = RoomManager()
    result = await room_manager.create_room("room1", {"name": "Test Room"})

    assert result is True
    assert "room1" in room_manager.rooms
    assert room_manager.room_metadata["room1"]["name"] == "Test Room"

    # Try creating again
    result = await room_manager.create_room("room1")
    assert result is False


@pytest.mark.asyncio
async def test_room_manager_delete_room():
    """Test deleting a room."""
    room_manager = RoomManager()
    await room_manager.create_room("room1")

    result = await room_manager.delete_room("room1")
    assert result is True
    assert "room1" not in room_manager.rooms


@pytest.mark.asyncio
async def test_room_manager_add_connection():
    """Test adding a connection to a room."""
    room_manager = RoomManager()
    result = await room_manager.add_connection("room1", "conn1")

    assert result is True
    assert "conn1" in room_manager.rooms["room1"]


@pytest.mark.asyncio
async def test_room_manager_remove_connection():
    """Test removing a connection from a room."""
    room_manager = RoomManager()
    await room_manager.add_connection("room1", "conn1")

    result = await room_manager.remove_connection("room1", "conn1")
    assert result is True
    assert "room1" not in room_manager.rooms  # Room should be cleaned up


@pytest.mark.asyncio
async def test_room_manager_get_room_connections():
    """Test getting all connections in a room."""
    room_manager = RoomManager()
    await room_manager.add_connection("room1", "conn1")
    await room_manager.add_connection("room1", "conn2")

    connections = await room_manager.get_room_connections("room1")
    assert len(connections) == 2
    assert "conn1" in connections
    assert "conn2" in connections


@pytest.mark.asyncio
async def test_room_manager_get_connection_rooms():
    """Test getting all rooms a connection is in."""
    room_manager = RoomManager()
    await room_manager.add_connection("room1", "conn1")
    await room_manager.add_connection("room2", "conn1")

    rooms = await room_manager.get_connection_rooms("conn1")
    assert len(rooms) == 2
    assert "room1" in rooms
    assert "room2" in rooms


@pytest.mark.asyncio
async def test_room_manager_get_room_count():
    """Test getting connection count in a room."""
    room_manager = RoomManager()
    await room_manager.add_connection("room1", "conn1")
    await room_manager.add_connection("room1", "conn2")
    await room_manager.add_connection("room1", "conn3")

    count = await room_manager.get_room_count("room1")
    assert count == 3


@pytest.mark.asyncio
async def test_room_manager_list_rooms():
    """Test listing all rooms."""
    room_manager = RoomManager()
    await room_manager.create_room("room1")
    await room_manager.create_room("room2")
    await room_manager.create_room("room3")

    rooms = room_manager.list_rooms()
    assert len(rooms) == 3
    assert "room1" in rooms


# ============================================================================
# Test RateLimiter
# ============================================================================


@pytest.mark.asyncio
async def test_rate_limiter_allow_within_limit(rate_limit_config):
    """Test rate limiter allows requests within limit."""
    rate_limiter = RateLimiter(rate_limit_config)

    allowed, retry_after = await rate_limiter.check_rate_limit("conn1")
    assert allowed is True
    assert retry_after == 0.0


@pytest.mark.asyncio
async def test_rate_limiter_block_over_limit(rate_limit_config):
    """Test rate limiter blocks requests over limit."""
    rate_limit_config.max_messages = 2
    rate_limiter = RateLimiter(rate_limit_config)

    # First two should pass
    for _ in range(2):
        allowed, _ = await rate_limiter.check_rate_limit("conn1")
        assert allowed is True

    # Third should be blocked
    allowed, retry_after = await rate_limiter.check_rate_limit("conn1")
    assert allowed is False
    assert retry_after > 0


@pytest.mark.asyncio
async def test_rate_limiter_refill_tokens(rate_limit_config):
    """Test rate limiter token refill."""
    rate_limit_config.max_messages = 1
    rate_limit_config.window_seconds = 1
    rate_limiter = RateLimiter(rate_limit_config)

    # Use up token
    allowed, _ = await rate_limiter.check_rate_limit("conn1")
    assert allowed is True

    # Should be blocked
    allowed, _ = await rate_limiter.check_rate_limit("conn1")
    assert allowed is False

    # Wait for refill
    await asyncio.sleep(1.5)

    # Should be allowed again
    allowed, _ = await rate_limiter.check_rate_limit("conn1")
    assert allowed is True


@pytest.mark.asyncio
async def test_rate_limiter_reset(rate_limit_config):
    """Test rate limiter reset."""
    rate_limiter = RateLimiter(rate_limit_config)

    await rate_limiter.check_rate_limit("conn1")
    await rate_limiter.reset("conn1")

    # Should have full tokens again
    allowed, _ = await rate_limiter.check_rate_limit("conn1")
    assert allowed is True


@pytest.mark.asyncio
async def test_rate_limiter_disabled():
    """Test rate limiter when disabled."""
    config = RateLimitConfig(enabled=False)
    rate_limiter = RateLimiter(config)

    # Should always allow
    for _ in range(100):
        allowed, _ = await rate_limiter.check_rate_limit("conn1")
        assert allowed is True


# ============================================================================
# Test AuthenticationManager
# ============================================================================


@pytest.mark.asyncio
async def test_authentication_manager_register_handler():
    """Test registering authentication handler."""
    auth_manager = AuthenticationManager()

    async def test_handler(credentials):
        return credentials.get("valid", False)

    auth_manager.register_auth_handler(test_handler)
    assert len(auth_manager.auth_handlers) == 1


@pytest.mark.asyncio
async def test_authentication_manager_authenticate_success():
    """Test successful authentication."""
    auth_manager = AuthenticationManager()

    async def test_handler(credentials):
        return credentials.get("username") == "test"

    auth_manager.register_auth_handler(test_handler)

    success, error = await auth_manager.authenticate(
        "conn1",
        {"username": "test", "password": "pass"}
    )

    assert success is True
    assert error is None
    assert await auth_manager.is_authenticated("conn1") is True


@pytest.mark.asyncio
async def test_authentication_manager_authenticate_failure():
    """Test failed authentication."""
    auth_manager = AuthenticationManager()

    async def test_handler(credentials):
        return credentials.get("username") == "test"

    auth_manager.register_auth_handler(test_handler)

    success, error = await auth_manager.authenticate(
        "conn1",
        {"username": "wrong", "password": "pass"}
    )

    assert success is False
    assert error is not None


@pytest.mark.asyncio
async def test_authentication_manager_validate_token():
    """Test token validation."""
    auth_manager = AuthenticationManager()

    async def test_validator(token):
        if token == "valid_token":
            return {"user_id": "user1", "username": "test"}
        return None

    auth_manager.register_token_validator(test_validator)

    user_info = await auth_manager.validate_token("valid_token")
    assert user_info is not None
    assert user_info["user_id"] == "user1"

    user_info = await auth_manager.validate_token("invalid_token")
    assert user_info is None


@pytest.mark.asyncio
async def test_authentication_manager_revoke():
    """Test revoking authentication."""
    auth_manager = AuthenticationManager()

    async def test_handler(credentials):
        return True

    auth_manager.register_auth_handler(test_handler)
    await auth_manager.authenticate("conn1", {})

    await auth_manager.revoke("conn1")
    assert await auth_manager.is_authenticated("conn1") is False


# ============================================================================
# Test MessageQueue
# ============================================================================


@pytest.mark.asyncio
async def test_message_queue_enqueue():
    """Test enqueuing messages."""
    queue = MessageQueue(max_size=10)
    msg = WebSocketMessage(data="test")

    result = await queue.enqueue("conn1", msg)
    assert result is True

    size = await queue.get_queue_size("conn1")
    assert size == 1


@pytest.mark.asyncio
async def test_message_queue_dequeue():
    """Test dequeuing messages."""
    queue = MessageQueue(max_size=10)
    msg = WebSocketMessage(data="test")

    await queue.enqueue("conn1", msg)
    dequeued = await queue.dequeue("conn1")

    assert dequeued is not None
    assert dequeued.data == "test"


@pytest.mark.asyncio
async def test_message_queue_priority():
    """Test message queue priority."""
    queue = MessageQueue(max_size=10)

    low_msg = WebSocketMessage(data="low", priority=MessagePriority.LOW)
    high_msg = WebSocketMessage(data="high", priority=MessagePriority.HIGH)
    normal_msg = WebSocketMessage(data="normal", priority=MessagePriority.NORMAL)

    await queue.enqueue("conn1", low_msg)
    await queue.enqueue("conn1", normal_msg)
    await queue.enqueue("conn1", high_msg)

    # Should dequeue in priority order
    msg1 = await queue.dequeue("conn1")
    assert msg1.data == "high"

    msg2 = await queue.dequeue("conn1")
    assert msg2.data == "normal"

    msg3 = await queue.dequeue("conn1")
    assert msg3.data == "low"


@pytest.mark.asyncio
async def test_message_queue_max_size():
    """Test message queue max size enforcement."""
    queue = MessageQueue(max_size=2)

    msg1 = WebSocketMessage(data="msg1", priority=MessagePriority.LOW)
    msg2 = WebSocketMessage(data="msg2", priority=MessagePriority.NORMAL)
    msg3 = WebSocketMessage(data="msg3", priority=MessagePriority.HIGH)

    await queue.enqueue("conn1", msg1)
    await queue.enqueue("conn1", msg2)
    await queue.enqueue("conn1", msg3)  # Should drop lowest priority

    size = await queue.get_queue_size("conn1")
    assert size == 2


@pytest.mark.asyncio
async def test_message_queue_clear():
    """Test clearing message queue."""
    queue = MessageQueue(max_size=10)

    for i in range(5):
        msg = WebSocketMessage(data=f"msg{i}")
        await queue.enqueue("conn1", msg)

    await queue.clear("conn1")
    size = await queue.get_queue_size("conn1")
    assert size == 0


# ============================================================================
# Test WebSocketManagerFSA
# ============================================================================


def test_websocket_manager_creation():
    """Test WebSocket Manager FSA creation."""
    manager = WebSocketManagerFSA(
        heartbeat_interval=20,
        heartbeat_timeout=60,
        enable_metrics=True,
    )

    assert manager.heartbeat_interval == 20
    assert manager.heartbeat_timeout == 60
    assert manager.enable_metrics is True
    assert manager.is_running is False


def test_websocket_manager_event_registration(websocket_manager):
    """Test event handler registration."""
    handler_called = []

    def test_handler(data):
        handler_called.append(data)

    websocket_manager.on(EventType.CONNECTION_OPENED, test_handler)
    assert len(websocket_manager.event_handlers[EventType.CONNECTION_OPENED]) == 1


@pytest.mark.asyncio
async def test_websocket_manager_emit_event(websocket_manager):
    """Test event emission."""
    handler_called = []

    async def test_handler(data):
        handler_called.append(data)

    websocket_manager.on(EventType.CONNECTION_OPENED, test_handler)
    await websocket_manager._emit_event(
        EventType.CONNECTION_OPENED,
        {"connection_id": "test"}
    )

    assert len(handler_called) == 1
    assert handler_called[0]["connection_id"] == "test"


def test_websocket_manager_register_message_handler(websocket_manager):
    """Test message handler registration."""
    async def test_handler(connection_id, data):
        pass

    websocket_manager.register_message_handler("test_type", test_handler)
    assert "test_type" in websocket_manager.message_handlers


@pytest.mark.asyncio
async def test_websocket_manager_create_room(websocket_manager):
    """Test creating a room."""
    result = await websocket_manager.create_room(
        "room1",
        {"name": "Test Room"}
    )

    assert result is True
    assert "room1" in websocket_manager.list_rooms()


@pytest.mark.asyncio
async def test_websocket_manager_delete_room(websocket_manager):
    """Test deleting a room."""
    await websocket_manager.create_room("room1")
    result = await websocket_manager.delete_room("room1")

    assert result is True
    assert "room1" not in websocket_manager.list_rooms()


def test_websocket_manager_get_global_metrics(websocket_manager):
    """Test getting global metrics."""
    metrics = websocket_manager.get_global_metrics()

    assert "total_connections" in metrics
    assert "active_connections" in metrics
    assert "total_messages" in metrics
    assert "uptime_seconds" in metrics
    assert metrics["active_connections"] == 0


def test_create_websocket_manager():
    """Test factory function for creating WebSocket manager."""
    manager = create_websocket_manager(
        heartbeat_interval=15,
        enable_metrics=False,
    )

    assert isinstance(manager, WebSocketManagerFSA)
    assert manager.heartbeat_interval == 15
    assert manager.enable_metrics is False


# ============================================================================
# Test Configuration Classes
# ============================================================================


def test_rate_limit_config_defaults():
    """Test RateLimitConfig default values."""
    config = RateLimitConfig()
    assert config.max_messages == 100
    assert config.window_seconds == 60
    assert config.burst_size == 10
    assert config.enabled is True


def test_reconnect_strategy_defaults():
    """Test ReconnectStrategy default values."""
    strategy = ReconnectStrategy()
    assert strategy.enabled is True
    assert strategy.initial_delay == 1
    assert strategy.max_delay == 60
    assert strategy.exponential_backoff is True
    assert strategy.jitter is True


def test_compression_config_defaults():
    """Test CompressionConfig default values."""
    config = CompressionConfig()
    assert config.enabled is True
    assert config.threshold_bytes == 1024
    assert config.level == 6


def test_rate_limit_config_custom():
    """Test RateLimitConfig with custom values."""
    config = RateLimitConfig(
        max_messages=50,
        window_seconds=30,
        burst_size=5,
        enabled=False,
    )
    assert config.max_messages == 50
    assert config.window_seconds == 30
    assert config.enabled is False


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_websocket_manager_register_and_unregister(
    websocket_manager,
    mock_websocket
):
    """Test connection registration and unregistration."""
    connection = WebSocketConnection(
        connection_id="test_conn",
        websocket=mock_websocket,
        user_id="user1",
    )

    await websocket_manager._register_connection(connection)
    assert "test_conn" in websocket_manager.connections
    assert "user1" in websocket_manager.user_connections

    await websocket_manager._unregister_connection("test_conn")
    assert "test_conn" not in websocket_manager.connections


@pytest.mark.asyncio
async def test_websocket_manager_send_to_user(
    websocket_manager,
    mock_websocket
):
    """Test sending message to all user connections."""
    # Create multiple connections for same user
    conn1 = WebSocketConnection(
        connection_id="conn1",
        websocket=mock_websocket,
        user_id="user1",
    )
    conn2 = WebSocketConnection(
        connection_id="conn2",
        websocket=mock_websocket,
        user_id="user1",
    )

    await websocket_manager._register_connection(conn1)
    await websocket_manager._register_connection(conn2)

    msg = WebSocketMessage(data="test message")
    count = await websocket_manager.send_to_user("user1", msg)

    assert count == 2


@pytest.mark.asyncio
async def test_websocket_manager_join_leave_room(
    websocket_manager,
    mock_websocket
):
    """Test joining and leaving rooms."""
    connection = WebSocketConnection(
        connection_id="test_conn",
        websocket=mock_websocket,
    )

    await websocket_manager._register_connection(connection)

    # Join room
    result = await websocket_manager.join_room("test_conn", "room1")
    assert result is True
    assert connection.is_in_room("room1")

    # Leave room
    result = await websocket_manager.leave_room("test_conn", "room1")
    assert result is True
    assert not connection.is_in_room("room1")


@pytest.mark.asyncio
async def test_websocket_manager_broadcast_to_room(
    websocket_manager,
    mock_websocket
):
    """Test broadcasting message to room."""
    # Create connections
    conn1 = WebSocketConnection("conn1", mock_websocket)
    conn2 = WebSocketConnection("conn2", mock_websocket)
    conn3 = WebSocketConnection("conn3", mock_websocket)

    await websocket_manager._register_connection(conn1)
    await websocket_manager._register_connection(conn2)
    await websocket_manager._register_connection(conn3)

    # Add to room
    await websocket_manager.join_room("conn1", "room1")
    await websocket_manager.join_room("conn2", "room1")

    # Broadcast
    msg = WebSocketMessage(data="broadcast")
    count = await websocket_manager.broadcast_to_room("room1", msg)

    assert count == 2


@pytest.mark.asyncio
async def test_websocket_manager_broadcast_with_exclusion(
    websocket_manager,
    mock_websocket
):
    """Test broadcasting with connection exclusion."""
    conn1 = WebSocketConnection("conn1", mock_websocket)
    conn2 = WebSocketConnection("conn2", mock_websocket)

    await websocket_manager._register_connection(conn1)
    await websocket_manager._register_connection(conn2)

    await websocket_manager.join_room("conn1", "room1")
    await websocket_manager.join_room("conn2", "room1")

    msg = WebSocketMessage(data="broadcast")
    count = await websocket_manager.broadcast_to_room(
        "room1",
        msg,
        exclude=["conn1"]
    )

    assert count == 1


@pytest.mark.asyncio
async def test_websocket_manager_get_connection_count(websocket_manager):
    """Test getting connection count."""
    count = await websocket_manager.get_connection_count()
    assert count == 0


@pytest.mark.asyncio
async def test_websocket_manager_list_connections(
    websocket_manager,
    mock_websocket
):
    """Test listing all connections."""
    conn1 = WebSocketConnection("conn1", mock_websocket)
    conn2 = WebSocketConnection("conn2", mock_websocket)

    await websocket_manager._register_connection(conn1)
    await websocket_manager._register_connection(conn2)

    connections = websocket_manager.list_connections()
    assert len(connections) == 2
    assert "conn1" in connections
    assert "conn2" in connections


@pytest.mark.asyncio
async def test_websocket_manager_get_connection(
    websocket_manager,
    mock_websocket
):
    """Test getting a specific connection."""
    conn = WebSocketConnection("conn1", mock_websocket)
    await websocket_manager._register_connection(conn)

    retrieved = websocket_manager.get_connection("conn1")
    assert retrieved is not None
    assert retrieved.connection_id == "conn1"


@pytest.mark.asyncio
async def test_websocket_manager_authenticate_connection(
    websocket_manager,
    mock_websocket
):
    """Test connection authentication."""
    conn = WebSocketConnection("conn1", mock_websocket)
    await websocket_manager._register_connection(conn)

    # Register auth handler
    async def test_handler(credentials):
        return credentials.get("valid", False)

    websocket_manager.auth_manager.register_auth_handler(test_handler)

    # Authenticate
    result = await websocket_manager.authenticate_connection(
        "conn1",
        {"valid": True}
    )

    assert result is True
    assert conn.authenticated is True


# ============================================================================
# Edge Case Tests
# ============================================================================


@pytest.mark.asyncio
async def test_send_to_nonexistent_connection(websocket_manager):
    """Test sending message to non-existent connection."""
    msg = WebSocketMessage(data="test")
    result = await websocket_manager.send_to_connection("nonexistent", msg)
    assert result is False


@pytest.mark.asyncio
async def test_join_room_nonexistent_connection(websocket_manager):
    """Test joining room with non-existent connection."""
    result = await websocket_manager.join_room("nonexistent", "room1")
    assert result is False


@pytest.mark.asyncio
async def test_broadcast_to_empty_room(websocket_manager):
    """Test broadcasting to empty room."""
    msg = WebSocketMessage(data="test")
    count = await websocket_manager.broadcast_to_room("empty_room", msg)
    assert count == 0


@pytest.mark.asyncio
async def test_get_metrics_nonexistent_connection(websocket_manager):
    """Test getting metrics for non-existent connection."""
    metrics = websocket_manager.get_connection_metrics("nonexistent")
    assert metrics is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
