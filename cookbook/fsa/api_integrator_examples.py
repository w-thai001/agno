"""
Comprehensive examples for API Integrator FSA.

This cookbook demonstrates various use cases for the APIIntegrator FSA including:
- REST API calls with different authentication methods
- GraphQL queries
- SOAP requests
- Retry logic with exponential backoff
- Response parsing and transformation
- Error handling
"""

import json
from typing import Any, Dict

from agno.fsa import (
    APIIntegrator,
    APIType,
    AuthConfig,
    AuthType,
    RequestConfig,
    RequestMethod,
    ResponseConfig,
    RetryConfig,
    RetryStrategy,
)
from agno.run.response import RunEvent


# ==============================================================================
# Example 1: Simple REST API call with Bearer authentication
# ==============================================================================

def example_rest_api_with_bearer():
    """
    Simple REST API call to GitHub API with Bearer token authentication.
    """
    print("\n" + "="*80)
    print("Example 1: REST API with Bearer Token")
    print("="*80)

    # Configure API integrator
    integrator = APIIntegrator(
        name="github_api",
        base_url="https://api.github.com",
        auth_config=AuthConfig(
            auth_type=AuthType.BEARER,
            token="ghp_your_token_here",  # Replace with actual token
        ),
        retry_config=RetryConfig(
            max_retries=3,
            strategy=RetryStrategy.EXPONENTIAL,
            initial_delay=1.0,
        ),
        response_config=ResponseConfig(
            parse_json=True,
            success_status_codes=[200, 201],
        ),
    )

    # Create request
    request = RequestConfig(
        method=RequestMethod.GET,
        endpoint="/users/octocat",
        headers={
            "Accept": "application/vnd.github.v3+json",
        },
    )

    # Execute
    print(f"\nFetching GitHub user data...")

    for response in integrator.run(request=request):
        if response.event == RunEvent.workflow_completed.value:
            # Get final data from context
            if hasattr(integrator, 'context'):
                final_data = integrator.context.get("final_data")
                if final_data:
                    print(f"\nUser: {final_data.get('login')}")
                    print(f"Name: {final_data.get('name')}")
                    print(f"Public Repos: {final_data.get('public_repos')}")
                    print(f"Followers: {final_data.get('followers')}")

    integrator.close()


# ==============================================================================
# Example 2: REST API with API Key authentication
# ==============================================================================

def example_rest_api_with_api_key():
    """
    REST API call with API Key authentication in header.
    """
    print("\n" + "="*80)
    print("Example 2: REST API with API Key")
    print("="*80)

    # Configure API integrator
    integrator = APIIntegrator(
        name="weather_api",
        base_url="https://api.openweathermap.org/data/2.5",
        auth_config=AuthConfig(
            auth_type=AuthType.API_KEY,
            token="your_api_key_here",  # Replace with actual key
            api_key_name="appid",
            api_key_location="query",  # API key goes in query params
        ),
    )

    # Create request
    request = RequestConfig(
        method=RequestMethod.GET,
        endpoint="/weather",
        query_params={
            "q": "London,uk",
            "units": "metric",
        },
    )

    # Execute
    print(f"\nFetching weather data for London...")

    for response in integrator.run(request=request):
        if response.event == RunEvent.workflow_completed.value:
            if hasattr(integrator, 'context'):
                final_data = integrator.context.get("final_data")
                if final_data:
                    print(f"\nTemperature: {final_data.get('main', {}).get('temp')}°C")
                    print(f"Weather: {final_data.get('weather', [{}])[0].get('description')}")
                    print(f"Humidity: {final_data.get('main', {}).get('humidity')}%")

    integrator.close()


# ==============================================================================
# Example 3: GraphQL API call
# ==============================================================================

def example_graphql_api():
    """
    GraphQL API call to GitHub GraphQL API.
    """
    print("\n" + "="*80)
    print("Example 3: GraphQL API")
    print("="*80)

    # Configure API integrator for GraphQL
    integrator = APIIntegrator(
        name="github_graphql",
        base_url="https://api.github.com",
        api_type=APIType.GRAPHQL,
        auth_config=AuthConfig(
            auth_type=AuthType.BEARER,
            token="ghp_your_token_here",  # Replace with actual token
        ),
    )

    # GraphQL query
    graphql_query = """
    query {
      viewer {
        login
        name
        email
        repositories(first: 5) {
          nodes {
            name
            description
            stargazerCount
          }
        }
      }
    }
    """

    # Create request
    request = RequestConfig(
        method=RequestMethod.POST,
        endpoint="/graphql",
        body=graphql_query,  # Will be automatically wrapped in {"query": ...}
    )

    # Execute
    print(f"\nFetching user repositories via GraphQL...")

    for response in integrator.run(request=request):
        if response.event == RunEvent.workflow_completed.value:
            if hasattr(integrator, 'context'):
                final_data = integrator.context.get("final_data")
                if final_data:
                    viewer = final_data.get('data', {}).get('viewer', {})
                    print(f"\nUser: {viewer.get('login')}")
                    print(f"Name: {viewer.get('name')}")
                    print(f"\nRepositories:")
                    for repo in viewer.get('repositories', {}).get('nodes', []):
                        print(f"  - {repo.get('name')}: {repo.get('stargazerCount')} stars")

    integrator.close()


# ==============================================================================
# Example 4: POST request with JSON body
# ==============================================================================

def example_post_with_json():
    """
    POST request with JSON body to create a resource.
    """
    print("\n" + "="*80)
    print("Example 4: POST with JSON Body")
    print("="*80)

    # Configure API integrator
    integrator = APIIntegrator(
        name="jsonplaceholder_api",
        base_url="https://jsonplaceholder.typicode.com",
        auth_config=AuthConfig(auth_type=AuthType.NONE),
    )

    # Create request
    request = RequestConfig(
        method=RequestMethod.POST,
        endpoint="/posts",
        headers={
            "Content-Type": "application/json",
        },
        body={
            "title": "My New Post",
            "body": "This is the content of my post",
            "userId": 1,
        },
    )

    # Execute
    print(f"\nCreating a new post...")

    for response in integrator.run(request=request):
        if response.event == RunEvent.workflow_completed.value:
            if hasattr(integrator, 'context'):
                final_data = integrator.context.get("final_data")
                if final_data:
                    print(f"\nPost created!")
                    print(f"ID: {final_data.get('id')}")
                    print(f"Title: {final_data.get('title')}")

    integrator.close()


# ==============================================================================
# Example 5: Response transformation
# ==============================================================================

def example_response_transformation():
    """
    REST API call with custom response transformation.
    """
    print("\n" + "="*80)
    print("Example 5: Response Transformation")
    print("="*80)

    # Custom transformation function
    def transform_user_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and transform only the fields we need"""
        return {
            "username": data.get("login"),
            "display_name": data.get("name"),
            "profile_url": data.get("html_url"),
            "repo_count": data.get("public_repos"),
            "follower_count": data.get("followers"),
            "is_hireable": data.get("hireable", False),
        }

    # Configure API integrator with transformation
    integrator = APIIntegrator(
        name="github_api_transform",
        base_url="https://api.github.com",
        auth_config=AuthConfig(
            auth_type=AuthType.BEARER,
            token="ghp_your_token_here",
        ),
        response_config=ResponseConfig(
            parse_json=True,
            transform_func=transform_user_data,
        ),
    )

    # Create request
    request = RequestConfig(
        method=RequestMethod.GET,
        endpoint="/users/torvalds",
    )

    # Execute
    print(f"\nFetching and transforming user data...")

    for response in integrator.run(request=request):
        if response.event == RunEvent.workflow_completed.value:
            if hasattr(integrator, 'context'):
                final_data = integrator.context.get("final_data")
                if final_data:
                    print(f"\nTransformed data:")
                    for key, value in final_data.items():
                        print(f"  {key}: {value}")

    integrator.close()


# ==============================================================================
# Example 6: JSON path extraction
# ==============================================================================

def example_json_path_extraction():
    """
    Extract specific data from nested JSON response using JSON path.
    """
    print("\n" + "="*80)
    print("Example 6: JSON Path Extraction")
    print("="*80)

    # Configure API integrator with JSON path extraction
    integrator = APIIntegrator(
        name="github_api_extract",
        base_url="https://api.github.com",
        auth_config=AuthConfig(
            auth_type=AuthType.BEARER,
            token="ghp_your_token_here",
        ),
        response_config=ResponseConfig(
            parse_json=True,
            extract_path="login",  # Extract only the login field
        ),
    )

    # Create request
    request = RequestConfig(
        method=RequestMethod.GET,
        endpoint="/users/octocat",
    )

    # Execute
    print(f"\nExtracting specific field from response...")

    for response in integrator.run(request=request):
        if response.event == RunEvent.workflow_completed.value:
            if hasattr(integrator, 'context'):
                final_data = integrator.context.get("final_data")
                if final_data:
                    print(f"\nExtracted login: {final_data}")

    integrator.close()


# ==============================================================================
# Example 7: Retry logic with exponential backoff
# ==============================================================================

def example_retry_logic():
    """
    Demonstrate retry logic with exponential backoff on failure.
    """
    print("\n" + "="*80)
    print("Example 7: Retry Logic with Exponential Backoff")
    print("="*80)

    # Configure API integrator with aggressive retry
    integrator = APIIntegrator(
        name="api_with_retry",
        base_url="https://httpstat.us",  # Service that can simulate status codes
        auth_config=AuthConfig(auth_type=AuthType.NONE),
        retry_config=RetryConfig(
            max_retries=5,
            strategy=RetryStrategy.EXPONENTIAL,
            initial_delay=1.0,
            max_delay=30.0,
            backoff_factor=2.0,
            retry_on_status=[429, 500, 502, 503, 504],
        ),
    )

    # Create request that might fail (simulate 503)
    request = RequestConfig(
        method=RequestMethod.GET,
        endpoint="/503",  # This endpoint returns 503
    )

    # Execute
    print(f"\nAttempting request with retries...")

    for response in integrator.run(request=request):
        if response.event == RunEvent.run_response.value:
            print(f"  {response.content}")

    integrator.close()


# ==============================================================================
# Example 8: Basic Authentication
# ==============================================================================

def example_basic_auth():
    """
    REST API call with Basic Authentication.
    """
    print("\n" + "="*80)
    print("Example 8: Basic Authentication")
    print("="*80)

    # Configure API integrator
    integrator = APIIntegrator(
        name="api_basic_auth",
        base_url="https://httpbin.org",
        auth_config=AuthConfig(
            auth_type=AuthType.BASIC,
            username="user",
            password="pass",
        ),
    )

    # Create request
    request = RequestConfig(
        method=RequestMethod.GET,
        endpoint="/basic-auth/user/pass",
    )

    # Execute
    print(f"\nTesting basic authentication...")

    for response in integrator.run(request=request):
        if response.event == RunEvent.workflow_completed.value:
            if hasattr(integrator, 'context'):
                final_data = integrator.context.get("final_data")
                if final_data:
                    print(f"\nAuthentication successful!")
                    print(f"Response: {json.dumps(final_data, indent=2)}")

    integrator.close()


# ==============================================================================
# Example 9: Custom headers and query parameters
# ==============================================================================

def example_custom_headers_params():
    """
    REST API call with custom headers and query parameters.
    """
    print("\n" + "="*80)
    print("Example 9: Custom Headers and Query Parameters")
    print("="*80)

    # Configure API integrator with default headers
    integrator = APIIntegrator(
        name="api_custom_config",
        base_url="https://httpbin.org",
        auth_config=AuthConfig(auth_type=AuthType.NONE),
        default_headers={
            "User-Agent": "Agno-API-Integrator/1.0",
            "Accept": "application/json",
        },
    )

    # Create request with additional headers and params
    request = RequestConfig(
        method=RequestMethod.GET,
        endpoint="/get",
        headers={
            "X-Custom-Header": "custom-value",
        },
        query_params={
            "param1": "value1",
            "param2": "value2",
        },
    )

    # Execute
    print(f"\nSending request with custom headers and params...")

    for response in integrator.run(request=request):
        if response.event == RunEvent.workflow_completed.value:
            if hasattr(integrator, 'context'):
                final_data = integrator.context.get("final_data")
                if final_data:
                    print(f"\nHeaders sent:")
                    for key, value in final_data.get('headers', {}).items():
                        print(f"  {key}: {value}")
                    print(f"\nQuery params:")
                    print(f"  {final_data.get('args', {})}")

    integrator.close()


# ==============================================================================
# Example 10: SOAP API call
# ==============================================================================

def example_soap_api():
    """
    SOAP API call with XML request/response.
    """
    print("\n" + "="*80)
    print("Example 10: SOAP API")
    print("="*80)

    # SOAP envelope
    soap_request = """<?xml version="1.0" encoding="utf-8"?>
    <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
        <soap:Body>
            <GetWeather xmlns="http://www.example.com/weather">
                <City>London</City>
            </GetWeather>
        </soap:Body>
    </soap:Envelope>"""

    # Configure API integrator for SOAP
    integrator = APIIntegrator(
        name="soap_api",
        base_url="https://www.example.com/soap",
        api_type=APIType.SOAP,
        auth_config=AuthConfig(auth_type=AuthType.NONE),
        response_config=ResponseConfig(
            parse_json=False,
            parse_xml=True,
        ),
    )

    # Create request
    request = RequestConfig(
        method=RequestMethod.POST,
        endpoint="/weather",
        headers={
            "SOAPAction": "http://www.example.com/weather/GetWeather",
        },
        body=soap_request,
    )

    # Execute
    print(f"\nSending SOAP request...")
    print("Note: This is a mock example - replace with actual SOAP endpoint")

    # Would execute like this:
    # for response in integrator.run(request=request):
    #     if response.event == RunEvent.workflow_completed.value:
    #         print(f"\nSOAP Response received")

    integrator.close()


# ==============================================================================
# Example 11: Handling errors and state history
# ==============================================================================

def example_error_handling():
    """
    Demonstrate error handling and state history tracking.
    """
    print("\n" + "="*80)
    print("Example 11: Error Handling and State History")
    print("="*80)

    # Configure API integrator
    integrator = APIIntegrator(
        name="api_error_demo",
        base_url="https://httpstat.us",
        auth_config=AuthConfig(auth_type=AuthType.NONE),
        retry_config=RetryConfig(
            max_retries=2,
            strategy=RetryStrategy.FIXED,
            initial_delay=0.5,
        ),
    )

    # Create request that will fail (404)
    request = RequestConfig(
        method=RequestMethod.GET,
        endpoint="/404",
    )

    # Execute
    print(f"\nAttempting request that will fail...")

    for response in integrator.run(request=request):
        if response.event == RunEvent.workflow_completed.value:
            if hasattr(integrator, 'context'):
                # Check state history
                state_history = integrator.context.state_history
                print(f"\nState history: {' -> '.join(state_history)}")

                # Check if there was an error
                error_info = integrator.context.get("error_info")
                if error_info:
                    print(f"\nError occurred:")
                    print(f"  Status: {error_info.get('status_code')}")
                    print(f"  Attempts: {error_info.get('attempts')}")

    integrator.close()


# ==============================================================================
# Example 12: FSA Visualization
# ==============================================================================

def example_visualize_fsa():
    """
    Visualize the FSA structure.
    """
    print("\n" + "="*80)
    print("Example 12: FSA Visualization")
    print("="*80)

    # Create API integrator
    integrator = APIIntegrator(
        name="api_visualize",
        base_url="https://api.example.com",
    )

    # Visualize the state machine
    print("\n" + integrator.visualize())

    integrator.close()


# ==============================================================================
# Main runner
# ==============================================================================

def main():
    """
    Run all examples.

    Note: Some examples require valid API tokens/keys to work.
    Uncomment and configure with your credentials to test.
    """
    print("\n" + "="*80)
    print("API Integrator FSA Examples")
    print("="*80)

    # Run examples that don't require authentication
    # example_rest_api_with_bearer()  # Requires GitHub token
    # example_rest_api_with_api_key()  # Requires OpenWeather API key
    # example_graphql_api()  # Requires GitHub token
    # example_post_with_json()
    # example_response_transformation()  # Requires GitHub token
    # example_json_path_extraction()  # Requires GitHub token
    # example_retry_logic()
    # example_basic_auth()
    example_custom_headers_params()
    # example_soap_api()  # Mock example
    # example_error_handling()
    example_visualize_fsa()

    print("\n" + "="*80)
    print("Examples completed!")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
