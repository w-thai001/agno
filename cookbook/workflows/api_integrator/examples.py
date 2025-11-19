"""
Comprehensive Examples for API Integrator FSA

This file demonstrates all features of the API Integrator toolkit, agent, and workflow:
- Basic REST API requests
- Authentication methods (Bearer, API Key, OAuth, Basic)
- GraphQL queries
- SOAP requests
- Retry logic and error handling
- Rate limiting
- Response transformation
- Batch requests
- Agent-based API interaction
- Multi-step workflows
"""

import os
from typing import Dict, Any

# Import API Integrator components
from api_integrator_toolkit import (
    ApiIntegratorToolkit,
    ResponseTransform,
)
from api_integrator_agent import create_api_integrator_agent
from api_integrator_workflow import (
    create_api_workflow,
    create_multi_api_workflow,
)


def example_1_basic_rest_requests():
    """Example 1: Basic REST API requests with JSONPlaceholder."""
    print("\n" + "=" * 80)
    print("Example 1: Basic REST API Requests")
    print("=" * 80 + "\n")

    # Initialize toolkit
    toolkit = ApiIntegratorToolkit(
        base_url="https://jsonplaceholder.typicode.com",
        timeout=30,
        max_retries=3,
    )

    # GET request
    print("1. GET request - Fetch all posts")
    print("-" * 40)
    result = toolkit.rest_request(
        endpoint="/posts",
        method="GET",
        extract_path="data",  # Extract just the data
        include_metadata=False,
    )
    print(result[:500] + "...\n")  # Print first 500 chars

    # GET request with parameters
    print("2. GET request with parameters - Fetch posts by user")
    print("-" * 40)
    result = toolkit.rest_request(
        endpoint="/posts",
        method="GET",
        params={"userId": 1},
        extract_path="data",
    )
    print(result[:500] + "...\n")

    # POST request
    print("3. POST request - Create a new post")
    print("-" * 40)
    result = toolkit.rest_request(
        endpoint="/posts",
        method="POST",
        json_data={
            "title": "Test Post",
            "body": "This is a test post created by API Integrator",
            "userId": 1,
        },
    )
    print(result + "\n")

    # PUT request
    print("4. PUT request - Update a post")
    print("-" * 40)
    result = toolkit.rest_request(
        endpoint="/posts/1",
        method="PUT",
        json_data={
            "id": 1,
            "title": "Updated Title",
            "body": "Updated body content",
            "userId": 1,
        },
    )
    print(result + "\n")

    # DELETE request
    print("5. DELETE request - Delete a post")
    print("-" * 40)
    result = toolkit.rest_request(
        endpoint="/posts/1",
        method="DELETE",
    )
    print(result + "\n")


def example_2_authentication_methods():
    """Example 2: Different authentication methods."""
    print("\n" + "=" * 80)
    print("Example 2: Authentication Methods")
    print("=" * 80 + "\n")

    # Bearer Token Authentication
    print("1. Bearer Token Authentication")
    print("-" * 40)
    toolkit_bearer = ApiIntegratorToolkit(
        base_url="https://api.example.com",
        auth_type="bearer",
        bearer_token="your-bearer-token-here",
    )
    print(f"Auth type: {toolkit_bearer.auth_type}")
    print(f"Headers: {toolkit_bearer._get_auth_headers()}\n")

    # API Key Authentication
    print("2. API Key Authentication")
    print("-" * 40)
    toolkit_apikey = ApiIntegratorToolkit(
        base_url="https://api.example.com",
        auth_type="api_key",
        api_key="your-api-key-here",
    )
    print(f"Auth type: {toolkit_apikey.auth_type}")
    print(f"Headers: {toolkit_apikey._get_auth_headers()}\n")

    # Basic Authentication
    print("3. Basic Authentication")
    print("-" * 40)
    toolkit_basic = ApiIntegratorToolkit(
        base_url="https://api.example.com",
        auth_type="basic",
        username="user@example.com",
        password="your-password",
    )
    print(f"Auth type: {toolkit_basic.auth_type}")
    print(f"Auth object: {toolkit_basic._get_auth()}\n")

    # OAuth2 Authentication
    print("4. OAuth2 Authentication")
    print("-" * 40)
    toolkit_oauth = ApiIntegratorToolkit(
        base_url="https://api.example.com",
        auth_type="oauth2",
        oauth2_token="your-oauth-token-here",
    )
    print(f"Auth type: {toolkit_oauth.auth_type}")
    print(f"Headers: {toolkit_oauth._get_auth_headers()}\n")

    # Custom Authentication
    print("5. Custom Authentication Headers")
    print("-" * 40)
    toolkit_custom = ApiIntegratorToolkit(
        base_url="https://api.example.com",
        auth_type="custom",
        custom_auth_header={
            "X-Custom-Auth": "custom-value",
            "X-Client-ID": "client-123",
        },
    )
    print(f"Auth type: {toolkit_custom.auth_type}")
    print(f"Headers: {toolkit_custom._get_auth_headers()}\n")


def example_3_graphql_queries():
    """Example 3: GraphQL query execution."""
    print("\n" + "=" * 80)
    print("Example 3: GraphQL Queries")
    print("=" * 80 + "\n")

    toolkit = ApiIntegratorToolkit(
        base_url="https://api.github.com",
        auth_type="bearer",
        bearer_token=os.getenv("GITHUB_TOKEN", "demo-token"),
    )

    # Simple GraphQL query
    print("1. Simple GraphQL Query")
    print("-" * 40)
    query = """
    query {
        viewer {
            login
            name
            email
        }
    }
    """
    result = toolkit.graphql_query(
        query=query,
        endpoint="/graphql",
    )
    print("Query executed (requires valid GitHub token)")
    print(f"Response structure: {result[:200]}...\n")

    # GraphQL query with variables
    print("2. GraphQL Query with Variables")
    print("-" * 40)
    query = """
    query GetRepository($owner: String!, $name: String!) {
        repository(owner: $owner, name: $name) {
            name
            description
            stargazerCount
            forkCount
        }
    }
    """
    result = toolkit.graphql_query(
        query=query,
        variables={
            "owner": "facebook",
            "name": "react",
        },
        extract_path="data.repository",
    )
    print("Query with variables executed")
    print(f"Extract path used: data.repository\n")


def example_4_soap_requests():
    """Example 4: SOAP request execution."""
    print("\n" + "=" * 80)
    print("Example 4: SOAP Requests")
    print("=" * 80 + "\n")

    toolkit = ApiIntegratorToolkit(
        base_url="https://www.dataaccess.com/webservicesserver",
    )

    # SOAP 1.1 request
    print("1. SOAP 1.1 Request - Number to Words")
    print("-" * 40)
    soap_body = """
    <NumberToWords xmlns="http://www.dataaccess.com/webservicesserver/">
        <ubiNum>123</ubiNum>
    </NumberToWords>
    """
    result = toolkit.soap_request(
        soap_action="NumberToWords",
        soap_body=soap_body,
        endpoint="/NumberConversion.wso",
        soap_version="1.1",
        namespace="http://www.dataaccess.com/webservicesserver/",
    )
    print("SOAP request executed")
    print(f"Response: {result[:300]}...\n")


def example_5_retry_and_rate_limiting():
    """Example 5: Retry logic and rate limiting."""
    print("\n" + "=" * 80)
    print("Example 5: Retry Logic and Rate Limiting")
    print("=" * 80 + "\n")

    # With retry logic
    print("1. Automatic Retry with Exponential Backoff")
    print("-" * 40)
    toolkit = ApiIntegratorToolkit(
        base_url="https://jsonplaceholder.typicode.com",
        max_retries=3,
        retry_backoff_factor=2.0,
        retry_on_status=[429, 500, 502, 503, 504],
    )
    print(f"Max retries: {toolkit.max_retries}")
    print(f"Backoff factor: {toolkit.retry_backoff_factor}")
    print(f"Retry on status: {toolkit.retry_on_status}\n")

    # With rate limiting
    print("2. Rate Limiting with Token Bucket")
    print("-" * 40)
    toolkit_limited = ApiIntegratorToolkit(
        base_url="https://jsonplaceholder.typicode.com",
        enable_rate_limiting=True,
        requests_per_second=5.0,
        burst_size=10,
    )
    print(f"Rate limiting enabled: {toolkit_limited.rate_limiter is not None}")
    print(f"Requests per second: 5.0")
    print(f"Burst size: 10")

    # Make multiple requests to see rate limiting in action
    print("\nMaking 3 rapid requests (rate limited to 5/sec)...")
    import time
    start = time.time()
    for i in range(3):
        toolkit_limited.rest_request(endpoint="/posts/1", method="GET")
        print(f"  Request {i+1} completed")
    elapsed = time.time() - start
    print(f"Total time: {elapsed:.2f}s\n")


def example_6_response_transformation():
    """Example 6: Response parsing and transformation."""
    print("\n" + "=" * 80)
    print("Example 6: Response Transformation")
    print("=" * 80 + "\n")

    toolkit = ApiIntegratorToolkit(
        base_url="https://jsonplaceholder.typicode.com",
    )

    # Extract specific path
    print("1. Extract Specific JSON Path")
    print("-" * 40)
    result = toolkit.rest_request(
        endpoint="/users/1",
        method="GET",
        extract_path="data.address.city",  # Extract just the city
    )
    print(f"Extracted city: {result}\n")

    # Include/exclude metadata
    print("2. Response Without Metadata")
    print("-" * 40)
    result = toolkit.rest_request(
        endpoint="/posts/1",
        method="GET",
        include_metadata=False,  # Only return data
    )
    print(f"Data only: {result[:200]}...\n")

    # Custom transformation with default transform
    print("3. Custom Default Transformation")
    print("-" * 40)

    def custom_transform(data):
        """Custom transformation function."""
        if isinstance(data, list):
            return {"count": len(data), "items": data[:5]}  # Return count and first 5
        return data

    toolkit_custom = ApiIntegratorToolkit(
        base_url="https://jsonplaceholder.typicode.com",
        default_transform=ResponseTransform(
            transform_func=custom_transform,
            include_metadata=True,
        ),
    )
    result = toolkit_custom.rest_request(
        endpoint="/posts",
        method="GET",
    )
    print(f"Transformed result: {result[:300]}...\n")


def example_7_batch_requests():
    """Example 7: Batch API requests."""
    print("\n" + "=" * 80)
    print("Example 7: Batch Requests")
    print("=" * 80 + "\n")

    toolkit = ApiIntegratorToolkit(
        base_url="https://jsonplaceholder.typicode.com",
    )

    # Execute multiple requests in batch
    print("1. Batch Multiple GET Requests")
    print("-" * 40)
    batch_config = """
    [
        {"endpoint": "/posts/1", "method": "GET"},
        {"endpoint": "/posts/2", "method": "GET"},
        {"endpoint": "/users/1", "method": "GET"},
        {"endpoint": "/comments", "method": "GET", "params": {"postId": 1}}
    ]
    """
    result = toolkit.batch_requests(
        requests_config=batch_config,
        stop_on_error=False,
    )
    print(f"Batch results: {result[:500]}...\n")

    # Batch with stop on error
    print("2. Batch with Stop on Error")
    print("-" * 40)
    batch_config_error = """
    [
        {"endpoint": "/posts/1", "method": "GET"},
        {"endpoint": "/invalid-endpoint", "method": "GET"},
        {"endpoint": "/posts/2", "method": "GET"}
    ]
    """
    result = toolkit.batch_requests(
        requests_config=batch_config_error,
        stop_on_error=True,
    )
    print("Batch with intentional error (stopped early)")
    print(f"Results: {result[:400]}...\n")


def example_8_connection_testing():
    """Example 8: Testing API connections."""
    print("\n" + "=" * 80)
    print("Example 8: Connection Testing")
    print("=" * 80 + "\n")

    # Test successful connection
    print("1. Test Successful Connection")
    print("-" * 40)
    toolkit = ApiIntegratorToolkit(
        base_url="https://jsonplaceholder.typicode.com",
    )
    result = toolkit.test_connection(endpoint="/posts/1")
    print(result + "\n")

    # Test failed connection
    print("2. Test Failed Connection")
    print("-" * 40)
    toolkit_fail = ApiIntegratorToolkit(
        base_url="https://invalid-domain-that-does-not-exist-12345.com",
        timeout=5,
    )
    result = toolkit_fail.test_connection()
    print(result + "\n")


def example_9_agent_based_interaction():
    """Example 9: Agent-based API interaction."""
    print("\n" + "=" * 80)
    print("Example 9: Agent-Based API Interaction")
    print("=" * 80 + "\n")

    # Create agent
    agent = create_api_integrator_agent(
        base_url="https://jsonplaceholder.typicode.com",
        enable_rate_limiting=False,
        max_retries=2,
    )

    print("Agent created with intelligent API interaction capabilities")
    print("The agent can understand natural language requests and make appropriate API calls.\n")

    # Example interactions (would require actual model API key)
    print("Example interactions the agent can handle:")
    print("1. 'Get all posts from user ID 1'")
    print("2. 'Create a new post with title Test and body Hello World'")
    print("3. 'Fetch the first 5 comments'")
    print("4. 'Get user details for user ID 2 and list their posts'")
    print("\nNote: Requires OpenAI API key to run actual interactions\n")


def example_10_workflow_orchestration():
    """Example 10: Multi-step workflow orchestration."""
    print("\n" + "=" * 80)
    print("Example 10: Workflow Orchestration")
    print("=" * 80 + "\n")

    print("Single API Workflow")
    print("-" * 40)

    # Create workflow
    workflow = create_api_workflow(
        base_url="https://jsonplaceholder.typicode.com",
        enable_rate_limiting=False,
    )

    print("Workflow created with multiple specialized agents:")
    print("- API Explorer: Discovers API structure")
    print("- Data Fetcher: Retrieves data efficiently")
    print("- Data Transformer: Transforms responses")
    print("- Validator: Ensures data quality\n")

    print("Example workflow tasks:")
    print("1. 'Fetch all users and their posts, then combine the data'")
    print("2. 'Get comments for post ID 1 and format them nicely'")
    print("3. 'Find all posts by user 1 and count the total'")
    print("\nNote: Requires OpenAI API key to run actual workflows\n")

    # Multi-API Workflow
    print("\nMulti-API Workflow")
    print("-" * 40)
    print("Integrating multiple APIs together:\n")

    # Example configuration (conceptual)
    apis_config = {
        "jsonplaceholder": {
            "base_url": "https://jsonplaceholder.typicode.com",
            "auth_type": "bearer",
        },
        "github": {
            "base_url": "https://api.github.com",
            "auth_type": "bearer",
            "bearer_token": os.getenv("GITHUB_TOKEN", ""),
        },
    }

    print("Multi-API workflow can:")
    print("- Fetch data from multiple sources")
    print("- Correlate data across APIs")
    print("- Handle complex integration scenarios")
    print("\nConfiguration example:")
    print(f"  APIs: {list(apis_config.keys())}")
    print("\n")


def example_11_production_ready_features():
    """Example 11: Production-ready features showcase."""
    print("\n" + "=" * 80)
    print("Example 11: Production-Ready Features")
    print("=" * 80 + "\n")

    # Full-featured production configuration
    toolkit = ApiIntegratorToolkit(
        # Base configuration
        base_url="https://api.example.com",
        timeout=30,
        verify_ssl=True,

        # Authentication
        auth_type="bearer",
        bearer_token=os.getenv("API_TOKEN", "demo-token"),

        # Custom headers
        default_headers={
            "User-Agent": "Agno-API-Integrator/1.0",
            "Accept": "application/json",
            "X-Client-Version": "1.0.0",
        },

        # Retry configuration
        max_retries=5,
        retry_backoff_factor=2.0,
        retry_on_status=[429, 500, 502, 503, 504],

        # Rate limiting
        enable_rate_limiting=True,
        requests_per_second=10.0,
        burst_size=20,

        # Connection pooling
        pool_connections=20,
        pool_maxsize=50,
    )

    print("Production Configuration:")
    print("-" * 40)
    print(f"✓ Base URL: {toolkit.base_url}")
    print(f"✓ Authentication: {toolkit.auth_type}")
    print(f"✓ Timeout: {toolkit.timeout}s")
    print(f"✓ SSL Verification: {toolkit.verify_ssl}")
    print(f"✓ Max Retries: {toolkit.max_retries}")
    print(f"✓ Retry Backoff: {toolkit.retry_backoff_factor}x")
    print(f"✓ Rate Limiting: {'Enabled' if toolkit.rate_limiter else 'Disabled'}")
    print(f"✓ Requests/Second: 10.0")
    print(f"✓ Connection Pool: 20 connections, 50 max")
    print(f"✓ Custom Headers: {len(toolkit.default_headers)} headers")
    print("\nThis configuration provides:")
    print("  • High reliability with automatic retries")
    print("  • Rate limiting to avoid API throttling")
    print("  • Connection pooling for performance")
    print("  • Comprehensive error handling")
    print("  • Production-grade logging\n")


def run_all_examples():
    """Run all examples sequentially."""
    print("\n" + "=" * 80)
    print("API INTEGRATOR FSA - COMPREHENSIVE EXAMPLES")
    print("=" * 80)

    try:
        example_1_basic_rest_requests()
        example_2_authentication_methods()
        example_3_graphql_queries()
        example_4_soap_requests()
        example_5_retry_and_rate_limiting()
        example_6_response_transformation()
        example_7_batch_requests()
        example_8_connection_testing()
        example_9_agent_based_interaction()
        example_10_workflow_orchestration()
        example_11_production_ready_features()

        print("\n" + "=" * 80)
        print("ALL EXAMPLES COMPLETED SUCCESSFULLY!")
        print("=" * 80 + "\n")

    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run all examples
    run_all_examples()

    # Or run individual examples:
    # example_1_basic_rest_requests()
    # example_5_retry_and_rate_limiting()
    # etc.
