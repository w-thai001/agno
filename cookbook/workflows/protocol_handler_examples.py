"""📚 Protocol Handler Examples - Comprehensive Usage Demonstrations

This file contains detailed examples for using the Protocol Handler workflow
with various communication protocols. Each example demonstrates best practices
and common use cases.

Examples included:
1. HTTP REST API calls (GET, POST, PUT, DELETE)
2. WebSocket real-time communication
3. MQTT IoT messaging
4. Authentication patterns (Bearer, API Key, Basic Auth)
5. Error handling and retries
6. Circuit breaker in action
7. Connection pooling benefits
8. Caching strategies

Run the examples individually or all together to see the protocol handler in action.
"""

import asyncio
from datetime import datetime

from agno.storage.sqlite import SqliteStorage
from agno.utils.log import logger
from agno.utils.pprint import pprint_run_response

from protocol_handler import (
    AuthCredentials,
    AuthType,
    CircuitBreakerConfig,
    ConnectionPoolConfig,
    ProtocolConfig,
    ProtocolHandler,
    ProtocolType,
    RetryPolicy,
    TimeoutConfig,
)


# ============================================================================
# Example 1: REST API - Full CRUD Operations
# ============================================================================


def example_1_rest_api_crud():
    """Demonstrate full CRUD operations with REST API."""
    print("\n" + "=" * 80)
    print("Example 1: REST API - Full CRUD Operations")
    print("=" * 80 + "\n")

    # Initialize protocol handler
    handler = ProtocolHandler(
        session_id="rest-api-example",
        storage=SqliteStorage(
            table_name="protocol_examples",
            db_file="tmp/protocol_examples.db",
        ),
        debug_mode=True,
    )

    # Configuration for JSONPlaceholder API
    config = ProtocolConfig(
        protocol_type=ProtocolType.HTTP,
        endpoint="https://jsonplaceholder.typicode.com",
        retry_policy=RetryPolicy(max_attempts=3, initial_delay=1.0),
        timeout_config=TimeoutConfig(connect_timeout=10.0, read_timeout=30.0),
    )

    # CREATE - POST a new post
    print("\n📝 CREATE: Creating a new post...")
    new_post = {
        "title": "Agno Protocol Handler is Awesome",
        "body": "This demonstrates creating a resource via REST API",
        "userId": 1,
    }

    response = handler.run(
        config=config,
        operation="send",
        method="POST",
        path="/posts",
        data=new_post,
        use_cache=False,
    )
    pprint_run_response(response, markdown=True)

    # READ - GET a post
    print("\n📖 READ: Fetching post #1...")
    response = handler.run(
        config=config,
        operation="send",
        method="GET",
        path="/posts/1",
        use_cache=True,  # This will cache the response
    )
    pprint_run_response(response, markdown=True)

    # UPDATE - PUT to update a post
    print("\n✏️ UPDATE: Updating post #1...")
    updated_post = {
        "id": 1,
        "title": "Updated Title",
        "body": "This post has been updated using PUT",
        "userId": 1,
    }

    response = handler.run(
        config=config,
        operation="send",
        method="PUT",
        path="/posts/1",
        data=updated_post,
        use_cache=False,
    )
    pprint_run_response(response, markdown=True)

    # DELETE - DELETE a post
    print("\n🗑️ DELETE: Deleting post #1...")
    response = handler.run(
        config=config,
        operation="send",
        method="DELETE",
        path="/posts/1",
        use_cache=False,
    )
    pprint_run_response(response, markdown=True)

    # LIST - GET multiple resources
    print("\n📋 LIST: Fetching all users...")
    response = handler.run(
        config=config,
        operation="send",
        method="GET",
        path="/users",
        use_cache=True,
    )
    pprint_run_response(response, markdown=True)


# ============================================================================
# Example 2: Authentication Methods
# ============================================================================


def example_2_authentication():
    """Demonstrate different authentication methods."""
    print("\n" + "=" * 80)
    print("Example 2: Authentication Methods")
    print("=" * 80 + "\n")

    handler = ProtocolHandler(
        session_id="auth-example",
        debug_mode=True,
    )

    # Bearer Token Authentication
    print("\n🔐 Bearer Token Authentication")
    bearer_config = ProtocolConfig(
        protocol_type=ProtocolType.HTTP,
        endpoint="https://api.github.com",
        auth_credentials=AuthCredentials(
            auth_type=AuthType.BEARER,
            token="ghp_your_token_here",  # Replace with actual token
        ),
    )

    # Note: This will fail without a valid token
    print("Configuration with Bearer token created (requires valid token to execute)")

    # API Key Authentication
    print("\n🔑 API Key Authentication")
    api_key_config = ProtocolConfig(
        protocol_type=ProtocolType.HTTP,
        endpoint="https://api.example.com",
        auth_credentials=AuthCredentials(
            auth_type=AuthType.API_KEY,
            token="your-api-key-here",
        ),
    )

    print("Configuration with API Key created")

    # Basic Authentication
    print("\n👤 Basic Authentication")
    basic_config = ProtocolConfig(
        protocol_type=ProtocolType.HTTP,
        endpoint="https://httpbin.org",
        auth_credentials=AuthCredentials(
            auth_type=AuthType.BASIC,
            username="testuser",
            password="testpass",
        ),
    )

    # Test basic auth with httpbin
    response = handler.run(
        config=basic_config,
        operation="send",
        method="GET",
        path="/basic-auth/testuser/testpass",
        use_cache=False,
    )
    pprint_run_response(response, markdown=True)

    # Custom Headers Authentication
    print("\n📋 Custom Headers Authentication")
    custom_headers_config = ProtocolConfig(
        protocol_type=ProtocolType.HTTP,
        endpoint="https://httpbin.org",
        auth_credentials=AuthCredentials(
            auth_type=AuthType.NONE,
            headers={
                "X-Custom-Auth": "custom-token",
                "X-Client-ID": "agno-protocol-handler",
            },
        ),
    )

    response = handler.run(
        config=custom_headers_config,
        operation="send",
        method="GET",
        path="/headers",
        use_cache=False,
    )
    pprint_run_response(response, markdown=True)


# ============================================================================
# Example 3: Retry Logic and Error Handling
# ============================================================================


def example_3_retry_and_errors():
    """Demonstrate retry logic and error handling."""
    print("\n" + "=" * 80)
    print("Example 3: Retry Logic and Error Handling")
    print("=" * 80 + "\n")

    handler = ProtocolHandler(
        session_id="retry-example",
        debug_mode=True,
    )

    # Configuration with aggressive retry policy
    config = ProtocolConfig(
        protocol_type=ProtocolType.HTTP,
        endpoint="https://httpbin.org",
        retry_policy=RetryPolicy(
            max_attempts=5,
            initial_delay=0.5,
            max_delay=10.0,
            exponential_base=2.0,
            jitter=True,
        ),
    )

    # Test with endpoint that returns 500 (server error)
    print("\n⚠️ Testing retry with 500 error...")
    response = handler.run(
        config=config,
        operation="send",
        method="GET",
        path="/status/500",
        use_cache=False,
    )
    pprint_run_response(response, markdown=True)

    # Test with endpoint that delays response
    print("\n⏱️ Testing with delayed response...")
    config_with_timeout = ProtocolConfig(
        protocol_type=ProtocolType.HTTP,
        endpoint="https://httpbin.org",
        timeout_config=TimeoutConfig(
            connect_timeout=5.0,
            read_timeout=3.0,  # Short timeout to demonstrate timeout handling
        ),
        retry_policy=RetryPolicy(max_attempts=2),
    )

    response = handler.run(
        config=config_with_timeout,
        operation="send",
        method="GET",
        path="/delay/5",  # This will timeout
        use_cache=False,
    )
    pprint_run_response(response, markdown=True)

    # Test successful request after retries
    print("\n✅ Testing successful request...")
    response = handler.run(
        config=config,
        operation="send",
        method="GET",
        path="/status/200",
        use_cache=False,
    )
    pprint_run_response(response, markdown=True)


# ============================================================================
# Example 4: Circuit Breaker Pattern
# ============================================================================


def example_4_circuit_breaker():
    """Demonstrate circuit breaker pattern in action."""
    print("\n" + "=" * 80)
    print("Example 4: Circuit Breaker Pattern")
    print("=" * 80 + "\n")

    handler = ProtocolHandler(
        session_id="circuit-breaker-example",
        debug_mode=True,
    )

    # Configuration with tight circuit breaker settings
    config = ProtocolConfig(
        protocol_type=ProtocolType.HTTP,
        endpoint="https://httpbin.org",
        circuit_breaker=CircuitBreakerConfig(
            failure_threshold=3,  # Open after 3 failures
            success_threshold=2,  # Close after 2 successes
            timeout=10.0,  # Try again after 10 seconds
            enabled=True,
        ),
        retry_policy=RetryPolicy(max_attempts=1),  # No retries to see circuit breaker
    )

    # Trigger circuit breaker by making failing requests
    print("\n🔴 Making requests that will fail to trigger circuit breaker...")
    for i in range(5):
        print(f"\nRequest {i + 1}:")
        response = handler.run(
            config=config,
            operation="send",
            method="GET",
            path="/status/500",
            use_cache=False,
        )
        pprint_run_response(response, markdown=True)

        # After 3 failures, circuit should be open
        if i >= 2:
            print("⚡ Circuit breaker should be OPEN now!")

    # Try a successful request (circuit is open, so it will be rejected)
    print("\n⚠️ Attempting request with circuit breaker OPEN...")
    response = handler.run(
        config=config,
        operation="send",
        method="GET",
        path="/status/200",
        use_cache=False,
    )
    pprint_run_response(response, markdown=True)

    # Wait for circuit to go half-open
    print("\n⏳ Waiting for circuit breaker timeout...")
    import time

    time.sleep(11)

    # Try again, circuit should be half-open
    print("\n🟡 Circuit should be HALF_OPEN, testing with successful request...")
    response = handler.run(
        config=config,
        operation="send",
        method="GET",
        path="/status/200",
        use_cache=False,
    )
    pprint_run_response(response, markdown=True)


# ============================================================================
# Example 5: Connection Pooling
# ============================================================================


def example_5_connection_pooling():
    """Demonstrate connection pooling benefits."""
    print("\n" + "=" * 80)
    print("Example 5: Connection Pooling")
    print("=" * 80 + "\n")

    handler = ProtocolHandler(
        session_id="pooling-example",
        debug_mode=True,
    )

    # Configuration with connection pooling
    config = ProtocolConfig(
        protocol_type=ProtocolType.HTTP,
        endpoint="https://jsonplaceholder.typicode.com",
        pool_config=ConnectionPoolConfig(
            max_connections=20,
            max_keepalive_connections=10,
            keepalive_expiry=300.0,
        ),
    )

    # Make multiple requests to demonstrate connection reuse
    print("\n🔄 Making multiple requests to demonstrate connection pooling...")
    start_time = datetime.now()

    for i in range(10):
        response = handler.run(
            config=config,
            operation="send",
            method="GET",
            path=f"/posts/{i + 1}",
            use_cache=False,
        )
        print(f"Request {i + 1} completed")

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    print(f"\n✅ Completed 10 requests in {duration:.2f} seconds")
    print("Connection pooling keeps connections alive for better performance!")


# ============================================================================
# Example 6: WebSocket Real-time Communication
# ============================================================================


def example_6_websocket():
    """Demonstrate WebSocket communication."""
    print("\n" + "=" * 80)
    print("Example 6: WebSocket Real-time Communication")
    print("=" * 80 + "\n")

    print("📝 Note: This example requires a WebSocket server.")
    print("You can use wss://echo.websocket.org for testing.\n")

    # Uncomment to test with a live WebSocket server
    """
    handler = ProtocolHandler(
        session_id="websocket-example",
        debug_mode=True,
    )

    config = ProtocolConfig(
        protocol_type=ProtocolType.WEBSOCKET,
        endpoint="wss://echo.websocket.org",
        timeout_config=TimeoutConfig(
            connect_timeout=10.0,
            read_timeout=10.0,
        ),
    )

    # Send a message
    print("📤 Sending message via WebSocket...")
    response = handler.run(
        config=config,
        operation="send",
        data={"message": "Hello from Agno!", "timestamp": str(datetime.now())},
    )
    pprint_run_response(response, markdown=True)

    # Receive the echo
    print("\n📥 Receiving message via WebSocket...")
    response = handler.run(
        config=config,
        operation="receive",
        timeout=5.0,
    )
    pprint_run_response(response, markdown=True)
    """

    print("Uncomment the code above to test with a live WebSocket server.")


# ============================================================================
# Example 7: MQTT IoT Messaging
# ============================================================================


def example_7_mqtt():
    """Demonstrate MQTT pub/sub messaging."""
    print("\n" + "=" * 80)
    print("Example 7: MQTT IoT Messaging")
    print("=" * 80 + "\n")

    print("📝 Note: This example requires an MQTT broker.")
    print("You can use mqtt://test.mosquitto.org:1883 for testing.\n")

    # Uncomment to test with a live MQTT broker
    """
    handler = ProtocolHandler(
        session_id="mqtt-example",
        debug_mode=True,
    )

    config = ProtocolConfig(
        protocol_type=ProtocolType.MQTT,
        endpoint="mqtt://test.mosquitto.org:1883",
        extra_config={"client_id": f"agno-handler-{int(datetime.now().timestamp())}"},
    )

    # Publish sensor data
    print("📤 Publishing sensor data to MQTT topic...")
    sensor_data = {
        "temperature": 22.5,
        "humidity": 65,
        "timestamp": str(datetime.now()),
    }

    response = handler.run(
        config=config,
        operation="send",
        data=sensor_data,
        topic="agno/sensors/room1/temperature",
        qos=1,
    )
    pprint_run_response(response, markdown=True)

    # Subscribe and receive messages
    print("\n📥 Subscribing to MQTT topic...")
    response = handler.run(
        config=config,
        operation="receive",
        topic="agno/sensors/#",  # Wildcard subscription
        timeout=5.0,
    )
    pprint_run_response(response, markdown=True)
    """

    print("Uncomment the code above to test with a live MQTT broker.")


# ============================================================================
# Example 8: Caching Strategies
# ============================================================================


def example_8_caching():
    """Demonstrate caching strategies."""
    print("\n" + "=" * 80)
    print("Example 8: Caching Strategies")
    print("=" * 80 + "\n")

    handler = ProtocolHandler(
        session_id="caching-example",
        storage=SqliteStorage(
            table_name="cache_examples",
            db_file="tmp/protocol_examples.db",
        ),
        debug_mode=True,
    )

    config = ProtocolConfig(
        protocol_type=ProtocolType.HTTP,
        endpoint="https://jsonplaceholder.typicode.com",
    )

    # First request - will fetch from API
    print("\n📡 First request - fetching from API...")
    start_time = datetime.now()
    response = handler.run(
        config=config,
        operation="send",
        method="GET",
        path="/posts/1",
        use_cache=True,
    )
    duration_1 = (datetime.now() - start_time).total_seconds()
    pprint_run_response(response, markdown=True)
    print(f"Time taken: {duration_1:.3f} seconds")

    # Second request - will use cache
    print("\n💾 Second request - should use cache...")
    start_time = datetime.now()
    response = handler.run(
        config=config,
        operation="send",
        method="GET",
        path="/posts/1",
        use_cache=True,
    )
    duration_2 = (datetime.now() - start_time).total_seconds()
    pprint_run_response(response, markdown=True)
    print(f"Time taken: {duration_2:.3f} seconds")

    print(
        f"\n⚡ Cache speedup: {duration_1 / duration_2:.2f}x faster"
        if duration_2 > 0
        else "\n⚡ Cache hit!"
    )

    # Third request - bypass cache
    print("\n🔄 Third request - bypassing cache...")
    start_time = datetime.now()
    response = handler.run(
        config=config,
        operation="send",
        method="GET",
        path="/posts/1",
        use_cache=False,
    )
    duration_3 = (datetime.now() - start_time).total_seconds()
    pprint_run_response(response, markdown=True)
    print(f"Time taken: {duration_3:.3f} seconds")


# ============================================================================
# Main Entry Point
# ============================================================================


def run_all_examples():
    """Run all examples sequentially."""
    print("\n" + "=" * 80)
    print("🚀 Running All Protocol Handler Examples")
    print("=" * 80)

    examples = [
        ("REST API CRUD", example_1_rest_api_crud),
        ("Authentication", example_2_authentication),
        ("Retry and Errors", example_3_retry_and_errors),
        ("Circuit Breaker", example_4_circuit_breaker),
        ("Connection Pooling", example_5_connection_pooling),
        ("WebSocket", example_6_websocket),
        ("MQTT", example_7_mqtt),
        ("Caching", example_8_caching),
    ]

    for name, example_func in examples:
        try:
            print(f"\n\n{'=' * 80}")
            print(f"Running: {name}")
            print(f"{'=' * 80}")
            example_func()
        except Exception as e:
            logger.error(f"Example '{name}' failed: {str(e)}")
            continue

    print("\n" + "=" * 80)
    print("✨ All examples completed!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        example_num = sys.argv[1]
        examples = {
            "1": example_1_rest_api_crud,
            "2": example_2_authentication,
            "3": example_3_retry_and_errors,
            "4": example_4_circuit_breaker,
            "5": example_5_connection_pooling,
            "6": example_6_websocket,
            "7": example_7_mqtt,
            "8": example_8_caching,
        }

        if example_num in examples:
            examples[example_num]()
        else:
            print(f"Unknown example: {example_num}")
            print("Available examples: 1-8 or 'all'")
    else:
        # Run select examples by default (skip ones requiring external servers)
        print("Running selected examples (HTTP/HTTPS only)...")
        print("Use 'python protocol_handler_examples.py <1-8>' to run specific examples")
        example_1_rest_api_crud()
        example_2_authentication()
        example_3_retry_and_errors()
        example_8_caching()
