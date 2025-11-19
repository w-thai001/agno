"""Unit tests for EventBus FSA."""

import asyncio
import re
from typing import List

import pytest

from agno.fsa import Event, EventBus


@pytest.fixture
def event_bus():
    """Create a fresh EventBus instance for each test."""
    return EventBus(name="TestBus")


def test_event_creation():
    """Test Event dataclass creation."""
    event = Event(topic="test.topic", data={"key": "value"}, metadata={"source": "test"})
    assert event.topic == "test.topic"
    assert event.data == {"key": "value"}
    assert event.metadata == {"source": "test"}
    assert event.event_id is not None


def test_event_to_dict():
    """Test Event serialization to dict."""
    event = Event(topic="test", data="data", event_id="123", metadata={"x": 1})
    event_dict = event.to_dict()
    assert event_dict["topic"] == "test"
    assert event_dict["data"] == "data"
    assert event_dict["event_id"] == "123"
    assert event_dict["metadata"]["x"] == 1


def test_event_from_dict():
    """Test Event deserialization from dict."""
    event_data = {"topic": "test", "data": "data", "event_id": "123", "metadata": {"x": 1}}
    event = Event.from_dict(event_data)
    assert event.topic == "test"
    assert event.data == "data"
    assert event.event_id == "123"
    assert event.metadata["x"] == 1


def test_event_bus_initialization(event_bus):
    """Test EventBus initialization."""
    assert event_bus.name == "TestBus"
    assert event_bus.history_size == 100
    assert event_bus.get_subscriber_count() == 0


def test_subscribe_and_publish_sync(event_bus):
    """Test basic subscribe and publish synchronously."""
    received_events: List[Event] = []

    def handler(event: Event):
        received_events.append(event)

    event_bus.subscribe("user.created", handler)
    event_bus.publish_sync("user.created", data={"user_id": 123})

    assert len(received_events) == 1
    assert received_events[0].topic == "user.created"
    assert received_events[0].data == {"user_id": 123}


@pytest.mark.asyncio
async def test_subscribe_and_publish_async(event_bus):
    """Test subscribe and publish with async handler."""
    received_events: List[Event] = []

    async def async_handler(event: Event):
        await asyncio.sleep(0.01)  # Simulate async work
        received_events.append(event)

    event_bus.subscribe("user.created", async_handler)
    await event_bus.publish("user.created", data={"user_id": 456})

    assert len(received_events) == 1
    assert received_events[0].topic == "user.created"
    assert received_events[0].data == {"user_id": 456}


def test_multiple_subscribers(event_bus):
    """Test multiple subscribers to same topic."""
    call_counts = {"handler1": 0, "handler2": 0}

    def handler1(event: Event):
        call_counts["handler1"] += 1

    def handler2(event: Event):
        call_counts["handler2"] += 1

    event_bus.subscribe("test.topic", handler1)
    event_bus.subscribe("test.topic", handler2)
    event_bus.publish_sync("test.topic")

    assert call_counts["handler1"] == 1
    assert call_counts["handler2"] == 1
    assert event_bus.get_subscriber_count("test.topic") == 2


def test_pattern_subscription(event_bus):
    """Test pattern-based topic matching."""
    received_events: List[Event] = []

    def handler(event: Event):
        received_events.append(event)

    # Subscribe to pattern matching "user.*"
    pattern = re.compile(r"^user\..*$")
    event_bus.subscribe(pattern, handler)

    event_bus.publish_sync("user.created", data="data1")
    event_bus.publish_sync("user.updated", data="data2")
    event_bus.publish_sync("user.deleted", data="data3")
    event_bus.publish_sync("order.created", data="data4")  # Should not match

    assert len(received_events) == 3
    assert all(e.topic.startswith("user.") for e in received_events)


def test_unsubscribe(event_bus):
    """Test unsubscribing from topics."""
    received_events: List[Event] = []

    def handler(event: Event):
        received_events.append(event)

    event_bus.subscribe("test.topic", handler)
    event_bus.publish_sync("test.topic", data="data1")

    # Unsubscribe
    result = event_bus.unsubscribe("test.topic", handler)
    assert result is True

    event_bus.publish_sync("test.topic", data="data2")

    # Should only have received first event
    assert len(received_events) == 1


def test_unsubscribe_pattern(event_bus):
    """Test unsubscribing from pattern."""
    received_events: List[Event] = []

    def handler(event: Event):
        received_events.append(event)

    pattern = re.compile(r"^test\..*$")
    event_bus.subscribe(pattern, handler)
    event_bus.publish_sync("test.topic", data="data1")

    # Unsubscribe from pattern
    result = event_bus.unsubscribe(pattern, handler)
    assert result is True

    event_bus.publish_sync("test.topic", data="data2")

    # Should only have received first event
    assert len(received_events) == 1


def test_event_history(event_bus):
    """Test event history tracking."""
    event_bus.publish_sync("topic1", data="data1")
    event_bus.publish_sync("topic2", data="data2")
    event_bus.publish_sync("topic3", data="data3")

    history = event_bus.get_history()
    assert len(history) == 3
    # History should be in reverse order (most recent first)
    assert history[0].topic == "topic3"
    assert history[1].topic == "topic2"
    assert history[2].topic == "topic1"


def test_event_history_filtering(event_bus):
    """Test filtering event history by topic."""
    event_bus.publish_sync("user.created", data="data1")
    event_bus.publish_sync("user.updated", data="data2")
    event_bus.publish_sync("order.created", data="data3")

    user_history = event_bus.get_history(topic="user.created")
    assert len(user_history) == 1
    assert user_history[0].topic == "user.created"


def test_event_history_limit(event_bus):
    """Test event history size limit."""
    # Create event bus with small history size
    small_bus = EventBus(history_size=5)

    # Publish more events than history size
    for i in range(10):
        small_bus.publish_sync(f"topic{i}", data=i)

    history = small_bus.get_history()
    assert len(history) == 5
    # Should only have last 5 events
    assert history[0].topic == "topic9"
    assert history[4].topic == "topic5"


def test_clear_history(event_bus):
    """Test clearing event history."""
    event_bus.publish_sync("topic1")
    event_bus.publish_sync("topic2")

    assert len(event_bus.get_history()) == 2

    event_bus.clear_history()
    assert len(event_bus.get_history()) == 0


def test_get_subscriber_count(event_bus):
    """Test getting subscriber counts."""

    def handler1(event: Event):
        pass

    def handler2(event: Event):
        pass

    event_bus.subscribe("topic1", handler1)
    event_bus.subscribe("topic1", handler2)
    event_bus.subscribe("topic2", handler1)

    assert event_bus.get_subscriber_count("topic1") == 2
    assert event_bus.get_subscriber_count("topic2") == 1
    assert event_bus.get_subscriber_count() == 3


def test_clear_subscribers(event_bus):
    """Test clearing all subscribers."""

    def handler(event: Event):
        pass

    event_bus.subscribe("topic1", handler)
    event_bus.subscribe("topic2", handler)

    assert event_bus.get_subscriber_count() == 2

    event_bus.clear_subscribers()
    assert event_bus.get_subscriber_count() == 0


def test_handler_error_handling(event_bus):
    """Test that errors in handlers don't stop other handlers."""
    call_log: List[str] = []

    def good_handler(event: Event):
        call_log.append("good")

    def bad_handler(event: Event):
        call_log.append("bad")
        raise ValueError("Handler error")

    def another_good_handler(event: Event):
        call_log.append("good2")

    event_bus.subscribe("test", good_handler)
    event_bus.subscribe("test", bad_handler)
    event_bus.subscribe("test", another_good_handler)

    event_bus.publish_sync("test")

    # All handlers should have been called despite error in one
    assert "good" in call_log
    assert "bad" in call_log
    assert "good2" in call_log


@pytest.mark.asyncio
async def test_mixed_sync_async_handlers(event_bus):
    """Test mixing sync and async handlers."""
    call_log: List[str] = []

    def sync_handler(event: Event):
        call_log.append("sync")

    async def async_handler(event: Event):
        await asyncio.sleep(0.01)
        call_log.append("async")

    event_bus.subscribe("test", sync_handler)
    event_bus.subscribe("test", async_handler)

    await event_bus.publish("test")

    assert "sync" in call_log
    assert "async" in call_log


def test_publish_sync_skips_async_handlers(event_bus):
    """Test that publish_sync skips async handlers."""
    call_log: List[str] = []

    def sync_handler(event: Event):
        call_log.append("sync")

    async def async_handler(event: Event):
        call_log.append("async")

    event_bus.subscribe("test", sync_handler)
    event_bus.subscribe("test", async_handler)

    event_bus.publish_sync("test")

    assert "sync" in call_log
    assert "async" not in call_log  # Async handler should be skipped


def test_event_metadata(event_bus):
    """Test event metadata handling."""
    received_events: List[Event] = []

    def handler(event: Event):
        received_events.append(event)

    event_bus.subscribe("test", handler)
    event_bus.publish_sync("test", data="data", metadata={"priority": "high", "source": "api"})

    assert len(received_events) == 1
    assert received_events[0].metadata["priority"] == "high"
    assert received_events[0].metadata["source"] == "api"
