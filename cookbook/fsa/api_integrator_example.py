"""
API Integrator FSA - Comprehensive Examples

This file demonstrates various use cases for the API Integrator FSA including:
- Basic REST API integration
- GraphQL queries
- Authentication methods
- Error handling and retry logic
- Caching strategies
- Circuit breaker patterns
- Metrics and monitoring
"""

from agno.agent import Agent
from agno.models.openai import OpenAIChat

from cookbook.fsa.api_integrator import (
    APIIntegratorConfig,
    APIIntegratorToolkit,
    AuthConfig,
    AuthType,
    CacheConfig,
    CircuitBreakerConfig,
    RateLimitConfig,
    RetryConfig,
)


def example_1_basic_rest_api():
    """Example 1: Basic REST API integration with an agent."""
    print("\n" + "=" * 80)
    print("Example 1: Basic REST API Integration")
    print("=" * 80)

    # Create toolkit with default configuration
    toolkit = APIIntegratorToolkit()

    # Create an agent
    api_agent = Agent(
        name="API Integration Agent",
        model=OpenAIChat(id="gpt-4o"),
        tools=[toolkit],
        instructions=[
            "You are an expert at integrating with external APIs.",
            "Help users make API requests and process responses.",
            "Always register endpoints before making requests.",
        ],
        markdown=True,
        show_tool_calls=True,
    )

    # Interact with the agent
    api_agent.print_response(
        """
        Please help me with the following:
        1. Register a GitHub API endpoint to get user information
           URL: https://api.github.com/users/{username}
           Name it 'github_user'
        2. Make a request to get information about the user 'octocat'
        3. Show me the response
        """,
        stream=True,
    )


def example_2_custom_configuration():
    """Example 2: Custom configuration with retry, rate limiting, and caching."""
    print("\n" + "=" * 80)
    print("Example 2: Custom Configuration")
    print("=" * 80)

    # Create custom configuration
    config = APIIntegratorConfig(
        default_timeout=60,
        verify_ssl=True,
        # Retry configuration
        retry_config=RetryConfig(
            max_retries=5,
            initial_delay=2.0,
            max_delay=120.0,
            exponential_base=2.0,
            retry_on_status_codes=[408, 429, 500, 502, 503, 504],
        ),
        # Rate limiting configuration
        rate_limit_config=RateLimitConfig(
            requests_per_second=5.0,
            burst_size=10,
            enabled=True,
        ),
        # Cache configuration
        cache_config=CacheConfig(
            enabled=True,
            ttl=600,  # 10 minutes
            max_size=500,
        ),
        # Circuit breaker configuration
        circuit_breaker_config=CircuitBreakerConfig(
            enabled=True,
            failure_threshold=3,
            success_threshold=2,
            timeout=30,
        ),
    )

    # Create toolkit with custom config
    toolkit = APIIntegratorToolkit(config=config)

    # Create agent
    api_agent = Agent(
        name="Resilient API Agent",
        model=OpenAIChat(id="gpt-4o"),
        tools=[toolkit],
        instructions=[
            "You are a resilient API integration specialist.",
            "The system has advanced retry logic, rate limiting, and circuit breakers.",
            "Monitor API health and provide metrics when requested.",
        ],
        markdown=True,
        show_tool_calls=True,
    )

    api_agent.print_response(
        """
        Set up an endpoint for JSONPlaceholder API:
        - Name: 'get_posts'
        - URL: https://jsonplaceholder.typicode.com/posts
        - Method: GET

        Then make a request and show me the first 3 posts.
        Also show me the cache and circuit breaker metrics.
        """,
        stream=True,
    )


def example_3_authentication():
    """Example 3: Different authentication methods."""
    print("\n" + "=" * 80)
    print("Example 3: Authentication Methods")
    print("=" * 80)

    # Create config with default authentication
    config = APIIntegratorConfig(
        default_auth=AuthConfig(
            auth_type=AuthType.BEARER,
            token="your_default_token_here",  # Replace with actual token
        )
    )

    toolkit = APIIntegratorToolkit(config=config)

    api_agent = Agent(
        name="Authenticated API Agent",
        model=OpenAIChat(id="gpt-4o"),
        tools=[toolkit],
        instructions=[
            "You help users make authenticated API requests.",
            "Support Bearer tokens, API keys, OAuth, and Basic auth.",
            "Always handle credentials securely.",
        ],
        markdown=True,
        show_tool_calls=True,
    )

    api_agent.print_response(
        """
        Show me examples of how to:
        1. Register an endpoint that requires Bearer token authentication
        2. Make a request with API key authentication (X-API-Key header)
        3. List all registered endpoints
        """,
        stream=True,
    )


def example_4_graphql():
    """Example 4: GraphQL API integration."""
    print("\n" + "=" * 80)
    print("Example 4: GraphQL Integration")
    print("=" * 80)

    toolkit = APIIntegratorToolkit()

    api_agent = Agent(
        name="GraphQL API Agent",
        model=OpenAIChat(id="gpt-4o"),
        tools=[toolkit],
        instructions=[
            "You are an expert in GraphQL API integration.",
            "Help users construct and execute GraphQL queries.",
            "Explain GraphQL responses clearly.",
        ],
        markdown=True,
        show_tool_calls=True,
    )

    api_agent.print_response(
        """
        Help me work with a GraphQL API:
        1. Register a GraphQL endpoint:
           Name: 'spacex_graphql'
           URL: https://spacex-production.up.railway.app/
           Type: GRAPHQL

        2. Execute this query to get SpaceX launch information:
           query {
             launches(limit: 3) {
               mission_name
               launch_date_local
               launch_success
             }
           }

        3. Show me the results
        """,
        stream=True,
    )


def example_5_monitoring_and_metrics():
    """Example 5: Monitoring, metrics, and circuit breaker management."""
    print("\n" + "=" * 80)
    print("Example 5: Monitoring and Metrics")
    print("=" * 80)

    config = APIIntegratorConfig(
        circuit_breaker_config=CircuitBreakerConfig(
            enabled=True,
            failure_threshold=2,  # Low threshold for demo
            success_threshold=2,
            timeout=10,
        ),
        rate_limit_config=RateLimitConfig(
            requests_per_second=10.0,
            burst_size=20,
            enabled=True,
        ),
    )

    toolkit = APIIntegratorToolkit(config=config)

    api_agent = Agent(
        name="Monitoring API Agent",
        model=OpenAIChat(id="gpt-4o"),
        tools=[toolkit],
        instructions=[
            "You are an API monitoring and operations specialist.",
            "Help users track API performance, cache efficiency, and system health.",
            "Provide insights from metrics and suggest optimizations.",
        ],
        markdown=True,
        show_tool_calls=True,
    )

    api_agent.print_response(
        """
        Set up monitoring for an API endpoint:
        1. Register an endpoint called 'test_api' at https://httpbin.org/get
        2. Make 3 requests to it
        3. Show me the following metrics:
           - API call metrics (requests, success rate, duration)
           - Cache metrics (hit rate, size)
           - Circuit breaker status
        4. Analyze the metrics and provide insights
        """,
        stream=True,
    )


def example_6_error_handling():
    """Example 6: Error handling and recovery."""
    print("\n" + "=" * 80)
    print("Example 6: Error Handling and Recovery")
    print("=" * 80)

    config = APIIntegratorConfig(
        retry_config=RetryConfig(
            max_retries=3,
            initial_delay=1.0,
            max_delay=10.0,
        ),
        circuit_breaker_config=CircuitBreakerConfig(
            enabled=True,
            failure_threshold=3,
            timeout=15,
        ),
    )

    toolkit = APIIntegratorToolkit(config=config)

    api_agent = Agent(
        name="Resilient API Agent",
        model=OpenAIChat(id="gpt-4o"),
        tools=[toolkit],
        instructions=[
            "You are an expert at handling API failures gracefully.",
            "Monitor circuit breakers and suggest recovery actions.",
            "Help users understand error responses and retry strategies.",
        ],
        markdown=True,
        show_tool_calls=True,
    )

    api_agent.print_response(
        """
        Demonstrate error handling:
        1. Register an endpoint 'delay_endpoint' at https://httpbin.org/delay/3
        2. Try to make a request with a 2-second timeout (it will timeout)
        3. Check the circuit breaker status
        4. Explain what happened and how the retry mechanism worked
        """,
        stream=True,
    )


def example_7_advanced_workflow():
    """Example 7: Advanced workflow with multiple endpoints."""
    print("\n" + "=" * 80)
    print("Example 7: Advanced Multi-Endpoint Workflow")
    print("=" * 80)

    toolkit = APIIntegratorToolkit()

    api_agent = Agent(
        name="Integration Workflow Agent",
        model=OpenAIChat(id="gpt-4o"),
        tools=[toolkit],
        instructions=[
            "You orchestrate complex workflows involving multiple APIs.",
            "Chain requests together, using output from one as input to another.",
            "Handle errors gracefully and provide detailed reports.",
        ],
        markdown=True,
        show_tool_calls=True,
    )

    api_agent.print_response(
        """
        Create a workflow that:
        1. Registers endpoints for JSONPlaceholder API:
           - 'list_users' at https://jsonplaceholder.typicode.com/users
           - 'user_posts' at https://jsonplaceholder.typicode.com/posts?userId={user_id}

        2. Gets the list of users
        3. Finds the first user
        4. Gets that user's posts
        5. Summarizes the workflow results with metrics
        """,
        stream=True,
    )


def example_8_cache_management():
    """Example 8: Cache management and optimization."""
    print("\n" + "=" * 80)
    print("Example 8: Cache Management")
    print("=" * 80)

    config = APIIntegratorConfig(
        cache_config=CacheConfig(
            enabled=True,
            ttl=30,  # Short TTL for demo
            max_size=100,
        )
    )

    toolkit = APIIntegratorToolkit(config=config)

    api_agent = Agent(
        name="Cache Management Agent",
        model=OpenAIChat(id="gpt-4o"),
        tools=[toolkit],
        instructions=[
            "You are an expert in API caching strategies.",
            "Help users optimize cache performance and manage cache lifecycle.",
            "Explain cache metrics and provide recommendations.",
        ],
        markdown=True,
        show_tool_calls=True,
    )

    api_agent.print_response(
        """
        Demonstrate caching:
        1. Register endpoint 'random_data' at https://httpbin.org/uuid
        2. Make the same request 3 times
        3. Show cache metrics (should show hits after first request)
        4. Invalidate the cache for this endpoint
        5. Make the request again and show updated metrics
        6. Clean up any expired cache entries
        """,
        stream=True,
    )


def example_9_direct_manager_use():
    """Example 9: Direct manager usage without agent (programmatic)."""
    print("\n" + "=" * 80)
    print("Example 9: Direct Manager Usage (Programmatic)")
    print("=" * 80)

    from cookbook.fsa.api_integrator import (
        APIEndpoint,
        APIIntegratorManager,
        APIRequest,
        APIType,
        HTTPMethod,
    )

    # Create manager directly
    manager = APIIntegratorManager(
        config=APIIntegratorConfig(
            retry_config=RetryConfig(max_retries=2),
            cache_config=CacheConfig(enabled=True, ttl=300),
        )
    )

    # Register endpoint
    endpoint = APIEndpoint(
        name="httpbin_get",
        url="https://httpbin.org/get",
        api_type=APIType.REST,
        method=HTTPMethod.GET,
        headers={"Accept": "application/json"},
        timeout=30,
        description="HTTPBin GET endpoint for testing",
    )
    manager.register_endpoint(endpoint)
    print(f"✓ Registered endpoint: {endpoint.name}")

    # Make request
    request = APIRequest(
        endpoint_name="httpbin_get",
        params={"test": "value", "foo": "bar"},
    )

    print(f"\n📡 Making request to {endpoint.name}...")
    response = manager.make_request(request)

    print(f"\n📊 Response:")
    print(f"  Status: {response.status_code}")
    print(f"  Success: {response.success}")
    print(f"  Duration: {response.duration_ms:.2f}ms")
    print(f"  From Cache: {response.from_cache}")
    print(f"  Body Preview: {str(response.body)[:200]}...")

    # Make same request again (should be cached)
    print(f"\n📡 Making same request again (should hit cache)...")
    response2 = manager.make_request(request)
    print(f"  From Cache: {response2.from_cache}")
    print(f"  Duration: {response2.duration_ms:.2f}ms")

    # Get metrics
    print(f"\n📈 Metrics:")
    metrics = manager.get_metrics("httpbin_get")
    print(f"  Total Requests: {metrics['total_requests']}")
    print(f"  Successful: {metrics['successful_requests']}")
    print(f"  Failed: {metrics['failed_requests']}")
    print(f"  Avg Duration: {metrics['avg_duration_ms']:.2f}ms")
    print(f"  Cache Hits: {metrics['cache_hits']}")
    print(f"  Cache Misses: {metrics['cache_misses']}")

    cache_metrics = manager.get_cache_metrics()
    print(f"\n💾 Cache Metrics:")
    print(f"  Hit Rate: {cache_metrics['hit_rate_percent']:.1f}%")
    print(f"  Size: {cache_metrics['size']}/{cache_metrics['max_size']}")


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("API Integrator FSA - Comprehensive Examples")
    print("=" * 80)
    print("\nThis demonstration shows various capabilities of the API Integrator FSA.")
    print("Note: Some examples require internet connectivity and may make real API calls.")
    print("\nChoose an example to run:")
    print("  1. Basic REST API integration")
    print("  2. Custom configuration (retry, rate limiting, caching)")
    print("  3. Authentication methods")
    print("  4. GraphQL integration")
    print("  5. Monitoring and metrics")
    print("  6. Error handling and recovery")
    print("  7. Advanced multi-endpoint workflow")
    print("  8. Cache management")
    print("  9. Direct manager usage (programmatic)")
    print("  0. Run all examples")

    choice = input("\nEnter choice (0-9): ").strip()

    examples = {
        "1": example_1_basic_rest_api,
        "2": example_2_custom_configuration,
        "3": example_3_authentication,
        "4": example_4_graphql,
        "5": example_5_monitoring_and_metrics,
        "6": example_6_error_handling,
        "7": example_7_advanced_workflow,
        "8": example_8_cache_management,
        "9": example_9_direct_manager_use,
    }

    if choice == "0":
        for example_func in examples.values():
            example_func()
            print("\n" + "-" * 80)
            input("Press Enter to continue to next example...")
    elif choice in examples:
        examples[choice]()
    else:
        print("Invalid choice. Running example 1 by default.")
        example_1_basic_rest_api()


if __name__ == "__main__":
    # Run direct manager example (doesn't require interactive agent)
    example_9_direct_manager_use()

    # Uncomment to run interactive examples (requires OpenAI API key)
    # main()
