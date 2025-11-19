#!/usr/bin/env python3
"""Test script for Message Broker FSA."""

import sys
sys.path.insert(0, '/home/user/agno/libs/agno')

from agno.run.message_broker import MessageBrokerFSA, BrokerState
from agno.models.message import Message


def test_message_broker_fsa():
    """Test the message broker FSA functionality."""
    print("Testing Message Broker FSA...")

    # Initialize broker
    broker = MessageBrokerFSA()
    assert broker.state == BrokerState.IDLE, "Initial state should be IDLE"
    print("✓ Broker initialized in IDLE state")

    # Create handlers
    received_messages = []

    def handler1(msg: Message):
        print(f"  Handler 1 received: {msg.role} - {msg.get_content_string()[:50]}")
        received_messages.append(("handler1", msg))

    def handler2(msg: Message):
        print(f"  Handler 2 received: {msg.role} - {msg.get_content_string()[:50]}")
        received_messages.append(("handler2", msg))

    # Subscribe handlers
    broker.subscribe("agent.messages", handler1)
    broker.subscribe("agent.messages", handler2)
    broker.subscribe("system.events", handler1)
    print("✓ Subscribed handlers to topics")

    # Create test message
    test_message = Message(role="user", content="Hello from the message broker FSA!")

    # Test state transitions
    print("\nTesting state transitions:")
    assert broker.receive(test_message), "Should successfully receive message"
    assert broker.state == BrokerState.RECEIVING, "State should be RECEIVING"
    print(f"✓ Transitioned to {broker.state}")

    handlers = broker.route("agent.messages")
    assert broker.state == BrokerState.ROUTING, "State should be ROUTING"
    assert len(handlers) == 2, "Should have 2 handlers for agent.messages"
    print(f"✓ Transitioned to {broker.state}, found {len(handlers)} handlers")

    assert broker.deliver(test_message, handlers), "Should successfully deliver"
    assert broker.state == BrokerState.COMPLETED, "State should be COMPLETED"
    print(f"✓ Transitioned to {broker.state}")

    assert len(received_messages) == 2, "Both handlers should have received message"
    print(f"✓ Both handlers received the message")

    # Test complete process workflow
    print("\nTesting complete workflow:")
    received_messages.clear()
    broker.reset()

    test_message2 = Message(role="assistant", content="Testing the process method")
    success = broker.process(test_message2, "agent.messages")

    assert success, "Process should succeed"
    assert broker.state == BrokerState.IDLE, "Should return to IDLE after process"
    assert len(received_messages) == 2, "Both handlers should have received message"
    print(f"✓ Complete workflow successful, broker returned to {broker.state}")

    # Test error handling
    print("\nTesting error handling:")
    broker.state = BrokerState.DELIVERING
    assert not broker.receive(test_message), "Invalid transition should fail"
    assert broker.state == BrokerState.ERROR, "Should transition to ERROR"
    print(f"✓ Invalid transition properly handled: {broker.error_message}")

    # Test unsubscribe
    print("\nTesting unsubscribe:")
    broker.reset()
    broker.unsubscribe("agent.messages", handler2)
    received_messages.clear()

    success = broker.process(test_message, "agent.messages")
    assert success and len(received_messages) == 1, "Only handler1 should receive"
    print(f"✓ Unsubscribe successful, only 1 handler received message")

    print("\n✅ All tests passed!")


if __name__ == "__main__":
    test_message_broker_fsa()
