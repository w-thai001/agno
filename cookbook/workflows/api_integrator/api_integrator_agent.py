"""
API Integrator Agent - Intelligent API interaction agent

An autonomous agent that can intelligently interact with APIs, handle
complex scenarios, and make decisions based on API responses.
"""

from typing import Optional, Dict, Any
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.storage.agent.sqlite import SqliteAgentStorage

from api_integrator_toolkit import ApiIntegratorToolkit, ResponseTransform


class ApiIntegratorAgent:
    """
    Intelligent API Integrator Agent that can:
    - Understand API documentation and structure
    - Make intelligent API calls based on user requests
    - Handle errors and retry failed requests
    - Chain multiple API calls together
    - Extract and format relevant information
    """

    def __init__(
        self,
        # API Configuration
        base_url: str,
        api_key: Optional[str] = None,
        bearer_token: Optional[str] = None,
        auth_type: str = "bearer",
        # Model Configuration
        model_id: str = "gpt-4o",
        # Agent Configuration
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        storage: Optional[SqliteAgentStorage] = None,
        # Toolkit Configuration
        enable_rate_limiting: bool = True,
        requests_per_second: float = 10.0,
        max_retries: int = 3,
        timeout: int = 30,
        **toolkit_kwargs
    ):
        """
        Initialize API Integrator Agent.

        Args:
            base_url: Base URL for the API
            api_key: API key for authentication
            bearer_token: Bearer token for authentication
            auth_type: Authentication type (bearer, api_key, basic, oauth2)
            model_id: Language model to use
            session_id: Session ID for conversation continuity
            user_id: User ID for storage
            storage: Storage backend for agent memory
            enable_rate_limiting: Enable rate limiting
            requests_per_second: Maximum requests per second
            max_retries: Maximum retry attempts
            timeout: Request timeout in seconds
            **toolkit_kwargs: Additional toolkit configuration
        """
        # Initialize API toolkit
        self.toolkit = ApiIntegratorToolkit(
            base_url=base_url,
            api_key=api_key,
            bearer_token=bearer_token,
            auth_type=auth_type,
            enable_rate_limiting=enable_rate_limiting,
            requests_per_second=requests_per_second,
            max_retries=max_retries,
            timeout=timeout,
            **toolkit_kwargs
        )

        # Create instructions for the agent
        instructions = self._create_instructions()

        # Initialize the agent
        self.agent = Agent(
            name="API Integrator",
            model=OpenAIChat(id=model_id),
            tools=[self.toolkit],
            instructions=instructions,
            session_id=session_id,
            user_id=user_id,
            storage=storage,
            show_tool_calls=True,
            markdown=True,
            debug_mode=False,
            add_history_to_messages=True,
            num_history_responses=5,
            add_datetime_to_instructions=True,
            description="Expert API integration agent that can interact with any REST, GraphQL, or SOAP API",
        )

    def _create_instructions(self) -> str:
        """Create detailed instructions for the agent."""
        return f"""You are an expert API integration agent with access to comprehensive API tools.

Your capabilities include:
1. Making REST API requests (GET, POST, PUT, DELETE, PATCH)
2. Executing GraphQL queries and mutations
3. Sending SOAP requests
4. Handling various authentication methods
5. Parsing and transforming API responses
6. Executing batch requests
7. Testing API connections

Base API URL: {self.toolkit.base_url or 'Not configured'}
Authentication Type: {self.toolkit.auth_type}
Rate Limiting: {'Enabled' if self.toolkit.rate_limiter else 'Disabled'}
Max Retries: {self.toolkit.max_retries}

Guidelines:
- Always use the appropriate tool for the task (rest_request, graphql_query, soap_request)
- When making requests, provide clear descriptions of what you're doing
- If a request fails, analyze the error and suggest solutions
- Use extract_path parameter to simplify responses when needed
- For complex operations, break them down into multiple steps
- Always validate responses before proceeding with dependent requests
- If you encounter rate limiting or errors, explain the issue to the user
- Use batch_requests for multiple independent API calls

When the user asks about API capabilities:
- Explain what endpoints are available (if you know)
- Describe authentication requirements
- Suggest best practices for the specific API

Error Handling:
- If a request fails with 4xx status, check authentication and parameters
- If a request fails with 5xx status, suggest retrying or checking API status
- If rate limited (429), explain the rate limit and wait time
- Always provide actionable next steps

Be conversational, helpful, and proactive in solving API integration challenges.
"""

    def run(self, message: str, stream: bool = True):
        """
        Run the agent with a user message.

        Args:
            message: User message/request
            stream: Stream the response

        Returns:
            Agent response
        """
        return self.agent.run(message, stream=stream)

    def print_response(self, message: str):
        """
        Run the agent and print the response.

        Args:
            message: User message/request
        """
        self.agent.print_response(message, stream=True)

    def get_session_state(self) -> Dict[str, Any]:
        """Get current session state."""
        return self.agent.session_state or {}

    def clear_session(self):
        """Clear agent session and history."""
        if hasattr(self.agent, 'memory') and self.agent.memory:
            self.agent.memory.clear()
        self.agent.session_state = {}


def create_api_integrator_agent(
    base_url: str,
    api_key: Optional[str] = None,
    **kwargs
) -> ApiIntegratorAgent:
    """
    Factory function to create an API Integrator Agent.

    Args:
        base_url: Base URL for the API
        api_key: API key for authentication
        **kwargs: Additional configuration options

    Returns:
        Configured ApiIntegratorAgent instance

    Example:
        >>> agent = create_api_integrator_agent(
        ...     base_url="https://api.example.com",
        ...     api_key="your-api-key",
        ...     enable_rate_limiting=True,
        ...     requests_per_second=5.0
        ... )
        >>> agent.print_response("Get the list of users")
    """
    return ApiIntegratorAgent(
        base_url=base_url,
        api_key=api_key,
        **kwargs
    )


# Example usage
if __name__ == "__main__":
    # Example: JSONPlaceholder API
    agent = create_api_integrator_agent(
        base_url="https://jsonplaceholder.typicode.com",
        auth_type="bearer",  # JSONPlaceholder doesn't require auth, but this is for demo
        enable_rate_limiting=True,
        requests_per_second=5.0,
        max_retries=3,
    )

    print("API Integrator Agent initialized!")
    print("\nExample queries you can try:")
    print("- 'Get all posts'")
    print("- 'Get user with ID 1'")
    print("- 'Create a new post with title \"Test\" and body \"This is a test\"'")
    print("- 'Get the first 5 comments'")
    print("\nAgent is ready for interaction!")

    # Interactive mode
    while True:
        try:
            user_input = input("\n\nYou: ").strip()
            if user_input.lower() in ['exit', 'quit', 'bye']:
                print("Goodbye!")
                break

            if user_input:
                print("\nAgent:")
                agent.print_response(user_input)

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")
