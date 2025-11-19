"""
Agent with Rate Limiting Example

This example demonstrates how to integrate rate limiting
with Agno agents to prevent exceeding API limits.
"""

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.rate_limit import TokenBucketRateLimiter, RateLimitExceeded
from agno.tools import Function


def get_weather(city: str) -> str:
    """
    Get weather for a city (simulated external API)

    Args:
        city: Name of the city
    """
    # Simulate API call
    return f"The weather in {city} is sunny, 72°F"


def main():
    print("=" * 60)
    print("Agent with Rate Limiting Example")
    print("=" * 60)

    # Create rate limiters
    # 1. Model API rate limiter (e.g., OpenAI limits)
    model_limiter = TokenBucketRateLimiter(
        rate_limit_id="openai_api",
        capacity=5,  # Allow 5 requests initially
        refill_rate=5 / 60,  # 5 requests per minute
        raise_on_limit=True,  # Raise exception when limited
    )

    # 2. External API rate limiter (e.g., weather API)
    weather_api_limiter = TokenBucketRateLimiter(
        rate_limit_id="weather_api",
        capacity=3,
        refill_rate=3 / 60,
        raise_on_limit=True,
    )

    # Create pre-hook for rate limiting tool calls
    def rate_limit_weather_api(function_call):
        """Pre-hook to enforce rate limiting on weather API"""
        if not weather_api_limiter.allow_request():
            retry_after = weather_api_limiter.get_retry_after()
            raise RateLimitExceeded(
                message=f"Weather API rate limit exceeded",
                retry_after=retry_after,
                current_state=weather_api_limiter.current_state,
            )

    # Create tool with rate limiting hook
    weather_tool = Function.from_callable(get_weather)
    weather_tool.pre_hook = rate_limit_weather_api

    # Create agent (note: using show_tool_calls for demo purposes)
    agent = Agent(
        name="WeatherAgent",
        model=OpenAIChat(id="gpt-4o-mini"),  # Using mini model for faster demo
        tools=[weather_tool],
        description="An agent that checks weather with rate limiting",
        instructions=[
            "You are a helpful weather assistant.",
            "When asked about weather, use the get_weather tool.",
        ],
        markdown=True,
        show_tool_calls=True,
    )

    # Test scenarios
    print("\n" + "=" * 60)
    print("Scenario 1: Normal requests within rate limit")
    print("=" * 60)

    queries = [
        "What's the weather in New York?",
        "How about San Francisco?",
        "And Seattle?",
    ]

    for i, query in enumerate(queries, 1):
        print(f"\n[Request {i}] {query}")
        print("-" * 60)

        try:
            # Check model rate limit before making request
            if not model_limiter.allow_request():
                retry_after = model_limiter.get_retry_after()
                print(f"✗ Model rate limit exceeded! Retry after {retry_after:.2f}s")
                continue

            # Run agent (this may use weather tool, which has its own rate limit)
            response = agent.run(query)
            print(f"✓ Response: {response.content}")

            # Show rate limiter stats
            model_metrics = model_limiter.get_metrics()
            weather_metrics = weather_api_limiter.get_metrics()

            print(f"\nModel API: {model_metrics['current_capacity']:.1f} tokens | " f"State: {model_limiter.current_state.value}")

            print(
                f"Weather API: {weather_metrics['current_capacity']:.1f} tokens | "
                f"State: {weather_api_limiter.current_state.value}"
            )

        except RateLimitExceeded as e:
            print(f"✗ Rate limit error: {e}")

    # Now try to exceed weather API rate limit
    print("\n" + "=" * 60)
    print("Scenario 2: Exceeding weather API rate limit")
    print("=" * 60)

    print("\nMaking 5 rapid weather requests to exceed the limit...")
    print("-" * 60)

    for i in range(1, 6):
        query = f"What's the weather in City{i}?"
        print(f"\n[Request {i}] {query}")

        try:
            if model_limiter.allow_request():
                response = agent.run(query)
                print(f"✓ Response: {response.content[:100]}...")
            else:
                print(f"✗ Model rate limited")

        except RateLimitExceeded as e:
            print(f"✗ Tool rate limited: {e}")

        # Show weather API stats
        weather_metrics = weather_api_limiter.get_metrics()
        print(
            f"Weather API: {weather_metrics['current_capacity']:.1f}/{weather_metrics['max_capacity']:.0f} | "
            f"Denied: {weather_metrics['denied_requests']}"
        )

    # Final statistics
    print("\n" + "=" * 60)
    print("Final Rate Limiter Statistics")
    print("=" * 60)

    print("\nModel API Limiter:")
    model_metrics = model_limiter.get_metrics()
    for key, value in model_metrics.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.2f}")
        else:
            print(f"  {key}: {value}")

    print("\nWeather API Limiter:")
    weather_metrics = weather_api_limiter.get_metrics()
    for key, value in weather_metrics.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.2f}")
        else:
            print(f"  {key}: {value}")


if __name__ == "__main__":
    # Note: Set your OpenAI API key to run this example
    # export OPENAI_API_KEY="your-api-key"
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nNote: Make sure to set OPENAI_API_KEY environment variable")
