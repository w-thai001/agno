"""
API Integrator Workflow - Multi-step API integration orchestration

A workflow that coordinates multiple API operations, including:
- API discovery and documentation parsing
- Multi-endpoint data aggregation
- Data transformation and enrichment
- Error recovery and retry strategies
"""

import json
from typing import Optional, Iterator, Dict, Any, List
from dataclasses import dataclass, field

from agno.agent import Agent
from agno.workflow import Workflow, RunResponse, RunEvent
from agno.models.openai import OpenAIChat
from agno.storage.workflow.sqlite import SqliteWorkflowStorage

from api_integrator_toolkit import ApiIntegratorToolkit, ResponseTransform


@dataclass
class ApiWorkflowResult:
    """Result from API workflow execution."""

    success: bool
    data: Any
    steps_completed: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "data": self.data,
            "steps_completed": self.steps_completed,
            "errors": self.errors,
            "metadata": self.metadata,
        }


class ApiIntegratorWorkflow(Workflow):
    """
    Multi-step API integration workflow.

    This workflow orchestrates complex API operations by coordinating
    multiple specialized agents:
    1. API Explorer - Discovers and understands API structure
    2. Data Fetcher - Retrieves data from endpoints
    3. Data Transformer - Transforms and enriches data
    4. Validator - Validates responses and ensures data quality
    """

    def __init__(
        self,
        # API Configuration
        base_url: str,
        api_key: Optional[str] = None,
        bearer_token: Optional[str] = None,
        auth_type: str = "bearer",
        # Workflow Configuration
        session_id: Optional[str] = None,
        storage: Optional[SqliteWorkflowStorage] = None,
        # Model Configuration
        model_id: str = "gpt-4o",
        # Toolkit Configuration
        enable_rate_limiting: bool = True,
        requests_per_second: float = 10.0,
        max_retries: int = 3,
        **toolkit_kwargs
    ):
        """
        Initialize API Integrator Workflow.

        Args:
            base_url: Base URL for the API
            api_key: API key for authentication
            bearer_token: Bearer token for authentication
            auth_type: Authentication type
            session_id: Session ID for workflow continuity
            storage: Storage backend for workflow state
            model_id: Language model to use
            enable_rate_limiting: Enable rate limiting
            requests_per_second: Maximum requests per second
            max_retries: Maximum retry attempts
            **toolkit_kwargs: Additional toolkit configuration
        """
        super().__init__(
            name="API Integrator Workflow",
            session_id=session_id,
            storage=storage,
        )

        # Initialize API toolkit (shared across agents)
        self.toolkit = ApiIntegratorToolkit(
            base_url=base_url,
            api_key=api_key,
            bearer_token=bearer_token,
            auth_type=auth_type,
            enable_rate_limiting=enable_rate_limiting,
            requests_per_second=requests_per_second,
            max_retries=max_retries,
            **toolkit_kwargs
        )

        # Initialize session state
        if "results" not in self.session_state:
            self.session_state["results"] = []
        if "api_cache" not in self.session_state:
            self.session_state["api_cache"] = {}

        # Agent 1: API Explorer - Understands API structure and capabilities
        self.api_explorer: Agent = Agent(
            name="API Explorer",
            role="Discover and understand API endpoints and structure",
            model=OpenAIChat(id=model_id),
            tools=[self.toolkit],
            instructions=f"""You are an API exploration specialist. Your role is to:

1. Test API connectivity using test_connection
2. Understand API structure and available endpoints
3. Identify required parameters and authentication
4. Document API capabilities for other agents

Base URL: {base_url}
Authentication: {auth_type}

When exploring an API:
- Start by testing the connection
- Try common endpoints like /health, /api, /v1, etc.
- Analyze response structures
- Document your findings clearly

Provide structured output about API capabilities.
""",
            markdown=True,
            show_tool_calls=True,
        )

        # Agent 2: Data Fetcher - Retrieves data from API endpoints
        self.data_fetcher: Agent = Agent(
            name="Data Fetcher",
            role="Fetch data from API endpoints efficiently",
            model=OpenAIChat(id=model_id),
            tools=[self.toolkit],
            instructions=f"""You are a data fetching specialist. Your role is to:

1. Make efficient API requests based on requirements
2. Handle pagination and large datasets
3. Use batch_requests for multiple endpoints
4. Extract relevant data using extract_path parameter

Guidelines:
- Use appropriate HTTP methods (GET, POST, etc.)
- Handle query parameters correctly
- Extract only needed data to reduce response size
- Report any errors clearly

Be efficient and precise in data retrieval.
""",
            markdown=True,
            show_tool_calls=True,
        )

        # Agent 3: Data Transformer - Transforms and enriches data
        self.data_transformer: Agent = Agent(
            name="Data Transformer",
            role="Transform and enrich API responses",
            model=OpenAIChat(id="gpt-4o-mini"),  # Use smaller model for transformation
            instructions="""You are a data transformation specialist. Your role is to:

1. Parse and structure API responses
2. Extract relevant information
3. Combine data from multiple sources
4. Format data according to requirements
5. Handle missing or invalid data gracefully

Provide clean, well-structured output.
""",
            markdown=True,
        )

        # Agent 4: Validator - Validates responses and data quality
        self.validator: Agent = Agent(
            name="Validator",
            role="Validate API responses and ensure data quality",
            model=OpenAIChat(id="gpt-4o-mini"),
            instructions="""You are a data validation specialist. Your role is to:

1. Verify response status codes and structures
2. Check for required fields
3. Validate data types and formats
4. Identify inconsistencies or errors
5. Suggest corrections or retry strategies

Be thorough but concise in your validation reports.
""",
            markdown=True,
        )

    def run(
        self,
        task: str,
        validate: bool = True,
        use_cache: bool = True,
        stream: bool = True,
    ) -> Iterator[RunResponse]:
        """
        Execute the API integration workflow.

        Args:
            task: Description of the API integration task
            validate: Validate responses before proceeding
            use_cache: Use cached results when available
            stream: Stream responses

        Yields:
            RunResponse objects with workflow progress

        Example:
            >>> workflow.run("Fetch all users and their posts, then combine the data")
        """
        logger_prefix = f"[{self.name}]"

        yield RunResponse(
            content=f"{logger_prefix} Starting API integration workflow",
            event=RunEvent.workflow_started,
        )

        try:
            # Step 1: Explore API (if not cached)
            if not use_cache or "api_structure" not in self.session_state["api_cache"]:
                yield RunResponse(
                    content=f"\n{logger_prefix} **Step 1: Exploring API structure**\n",
                    event=RunEvent.workflow_running,
                )

                exploration_result = self.api_explorer.run(
                    f"Test the API connection and explore available endpoints. Task: {task}"
                )

                if exploration_result and exploration_result.content:
                    self.session_state["api_cache"]["api_structure"] = exploration_result.content
                    yield RunResponse(
                        content=f"{exploration_result.content}\n",
                        event=RunEvent.workflow_running,
                    )

            # Step 2: Fetch data
            yield RunResponse(
                content=f"\n{logger_prefix} **Step 2: Fetching data**\n",
                event=RunEvent.workflow_running,
            )

            api_info = self.session_state["api_cache"].get("api_structure", "")
            fetch_prompt = f"""Based on the API structure:
{api_info}

Fetch the required data for this task: {task}

Use the most efficient approach (single request, batch requests, etc.)
"""

            fetch_result = self.data_fetcher.run(fetch_prompt)

            if not fetch_result or not fetch_result.content:
                yield RunResponse(
                    content=f"{logger_prefix} Error: Failed to fetch data",
                    event=RunEvent.workflow_completed,
                )
                return

            yield RunResponse(
                content=f"{fetch_result.content}\n",
                event=RunEvent.workflow_running,
            )

            # Step 3: Validate data (if requested)
            if validate:
                yield RunResponse(
                    content=f"\n{logger_prefix} **Step 3: Validating data**\n",
                    event=RunEvent.workflow_running,
                )

                validation_result = self.validator.run(
                    f"Validate this API response and check for any issues:\n\n{fetch_result.content}"
                )

                if validation_result and validation_result.content:
                    yield RunResponse(
                        content=f"{validation_result.content}\n",
                        event=RunEvent.workflow_running,
                    )

                    # Check if validation failed
                    if "error" in validation_result.content.lower() or "invalid" in validation_result.content.lower():
                        yield RunResponse(
                            content=f"{logger_prefix} Warning: Validation found issues",
                            event=RunEvent.workflow_running,
                        )

            # Step 4: Transform data
            yield RunResponse(
                content=f"\n{logger_prefix} **Step 4: Transforming data**\n",
                event=RunEvent.workflow_running,
            )

            transform_result = self.data_transformer.run(
                f"Transform and structure this data according to the task requirements:\n\nTask: {task}\n\nData:\n{fetch_result.content}"
            )

            if transform_result and transform_result.content:
                yield RunResponse(
                    content=f"{transform_result.content}\n",
                    event=RunEvent.workflow_running,
                )

            # Store result
            result = ApiWorkflowResult(
                success=True,
                data=transform_result.content if transform_result else None,
                steps_completed=["explore", "fetch", "validate", "transform"] if validate else ["explore", "fetch", "transform"],
                metadata={
                    "task": task,
                    "validated": validate,
                    "cached": use_cache,
                }
            )

            self.session_state["results"].append(result.to_dict())

            # Final summary
            yield RunResponse(
                content=f"\n{logger_prefix} **Workflow completed successfully!**\n\nSteps completed: {', '.join(result.steps_completed)}",
                event=RunEvent.workflow_completed,
            )

        except Exception as e:
            error_msg = f"{logger_prefix} Workflow error: {str(e)}"
            yield RunResponse(
                content=error_msg,
                event=RunEvent.workflow_completed,
            )

            # Store error result
            error_result = ApiWorkflowResult(
                success=False,
                data=None,
                errors=[str(e)],
                metadata={"task": task}
            )
            self.session_state["results"].append(error_result.to_dict())

    def get_results(self) -> List[Dict[str, Any]]:
        """Get all workflow results from session."""
        return self.session_state.get("results", [])

    def clear_cache(self):
        """Clear API cache."""
        self.session_state["api_cache"] = {}

    def get_api_info(self) -> Optional[str]:
        """Get cached API structure information."""
        return self.session_state.get("api_cache", {}).get("api_structure")


class MultiApiWorkflow(Workflow):
    """
    Workflow for integrating multiple APIs together.

    This workflow can:
    - Fetch data from multiple APIs
    - Combine and correlate data across APIs
    - Handle dependencies between API calls
    """

    def __init__(
        self,
        apis: Dict[str, Dict[str, Any]],
        session_id: Optional[str] = None,
        storage: Optional[SqliteWorkflowStorage] = None,
        model_id: str = "gpt-4o",
    ):
        """
        Initialize Multi-API Workflow.

        Args:
            apis: Dictionary mapping API names to configuration dicts
                  Each config should have: base_url, api_key, auth_type, etc.
            session_id: Session ID for workflow continuity
            storage: Storage backend
            model_id: Language model to use

        Example:
            >>> workflow = MultiApiWorkflow(apis={
            ...     "users": {"base_url": "https://api.users.com", "api_key": "..."},
            ...     "orders": {"base_url": "https://api.orders.com", "api_key": "..."}
            ... })
        """
        super().__init__(
            name="Multi-API Integrator",
            session_id=session_id,
            storage=storage,
        )

        # Create toolkits for each API
        self.toolkits = {}
        for api_name, config in apis.items():
            self.toolkits[api_name] = ApiIntegratorToolkit(**config)

        # Create orchestrator agent with access to all API toolkits
        self.orchestrator: Agent = Agent(
            name="API Orchestrator",
            role="Coordinate multiple API integrations",
            model=OpenAIChat(id=model_id),
            tools=list(self.toolkits.values()),
            instructions=f"""You are a multi-API orchestration specialist. You have access to these APIs:

{chr(10).join(f"- {name}: {toolkit.base_url}" for name, toolkit in self.toolkits.items())}

Your role is to:
1. Understand which APIs to query for different data
2. Coordinate requests across multiple APIs
3. Combine and correlate data from different sources
4. Handle dependencies (e.g., fetch user ID from one API, then use it in another)
5. Optimize by using batch requests when possible

Be intelligent about API selection and data correlation.
""",
            markdown=True,
            show_tool_calls=True,
        )

    def run(self, task: str, stream: bool = True) -> Iterator[RunResponse]:
        """
        Execute multi-API integration task.

        Args:
            task: Description of the integration task
            stream: Stream responses

        Yields:
            RunResponse objects with progress

        Example:
            >>> workflow.run(
            ...     "Get user profile from users API and their order history from orders API for user ID 123"
            ... )
        """
        yield RunResponse(
            content=f"[{self.name}] Starting multi-API integration",
            event=RunEvent.workflow_started,
        )

        # Run orchestrator
        result = self.orchestrator.run(task, stream=stream)

        if result:
            yield RunResponse(
                content=result.content,
                event=RunEvent.workflow_completed,
            )
        else:
            yield RunResponse(
                content="Error: Orchestration failed",
                event=RunEvent.workflow_completed,
            )


# Factory functions for easy workflow creation

def create_api_workflow(
    base_url: str,
    api_key: Optional[str] = None,
    **kwargs
) -> ApiIntegratorWorkflow:
    """
    Factory function to create an API Integrator Workflow.

    Args:
        base_url: Base URL for the API
        api_key: API key for authentication
        **kwargs: Additional configuration

    Returns:
        Configured ApiIntegratorWorkflow instance

    Example:
        >>> workflow = create_api_workflow(
        ...     base_url="https://api.example.com",
        ...     api_key="your-api-key",
        ...     enable_rate_limiting=True
        ... )
        >>> for response in workflow.run("Fetch all users"):
        ...     print(response.content)
    """
    return ApiIntegratorWorkflow(
        base_url=base_url,
        api_key=api_key,
        **kwargs
    )


def create_multi_api_workflow(
    apis: Dict[str, Dict[str, Any]],
    **kwargs
) -> MultiApiWorkflow:
    """
    Factory function to create a Multi-API Workflow.

    Args:
        apis: Dictionary of API configurations
        **kwargs: Additional configuration

    Returns:
        Configured MultiApiWorkflow instance

    Example:
        >>> workflow = create_multi_api_workflow(apis={
        ...     "github": {
        ...         "base_url": "https://api.github.com",
        ...         "bearer_token": "ghp_...",
        ...     },
        ...     "jira": {
        ...         "base_url": "https://company.atlassian.net",
        ...         "username": "user@example.com",
        ...         "password": "api-token",
        ...         "auth_type": "basic"
        ...     }
        ... })
    """
    return MultiApiWorkflow(apis=apis, **kwargs)


# Example usage
if __name__ == "__main__":
    import asyncio

    # Example 1: Single API Workflow
    print("=" * 80)
    print("Example 1: Single API Workflow")
    print("=" * 80)

    workflow = create_api_workflow(
        base_url="https://jsonplaceholder.typicode.com",
        auth_type="bearer",
        enable_rate_limiting=False,
    )

    print("\nTask: Fetch all posts and filter to show only posts from user ID 1\n")

    for response in workflow.run(
        task="Fetch all posts and filter to show only posts from user ID 1",
        validate=True,
        stream=True
    ):
        if response.content:
            print(response.content)

    # Example 2: Multi-API Workflow
    print("\n" + "=" * 80)
    print("Example 2: Multi-API Workflow (Conceptual)")
    print("=" * 80)
    print("\nThis would integrate multiple APIs together.")
    print("Configure with your actual API endpoints and credentials.")
