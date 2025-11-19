# FSA (Finite State Automaton) Examples

This directory contains examples and cookbook recipes for using FSAs in the Agno Framework.

## What is an FSA?

A Finite State Automaton (FSA) in Agno is a state-driven approach to agent orchestration. FSAs allow you to define explicit states and transitions, providing predictable and traceable execution flows.

## Features

- **State-driven execution**: Clear separation of logic into distinct states
- **Conditional transitions**: Define explicit conditions for moving between states
- **Context passing**: Share data between states via StateContext
- **Built-in error handling**: Automatic error state management
- **Retry logic**: Configurable retry strategies with backoff
- **Execution history**: Track the path through states for debugging

## Available FSAs

### API Integrator FSA

A production-ready FSA for API integration operations including:

- **Multiple API Types**: REST, GraphQL, and SOAP support
- **Authentication Methods**: Bearer token, API Key, Basic Auth, OAuth 2.0
- **Request Building**: Configure HTTP method, headers, query params, and body
- **Response Parsing**: Automatic JSON/XML parsing with path extraction
- **Retry Logic**: Exponential, linear, or fixed backoff strategies
- **Response Transformation**: Custom transformation functions

## Quick Start

```python
from agno.fsa import (
    APIIntegrator,
    AuthConfig,
    AuthType,
    RequestConfig,
    RequestMethod,
)

# Create an API integrator
integrator = APIIntegrator(
    name="my_api",
    base_url="https://api.example.com",
    auth_config=AuthConfig(
        auth_type=AuthType.BEARER,
        token="your_token_here",
    ),
)

# Create a request
request = RequestConfig(
    method=RequestMethod.GET,
    endpoint="/users/123",
)

# Execute
for response in integrator.run(request=request):
    print(response.content)
```

## Examples

See `api_integrator_examples.py` for comprehensive examples including:

1. **Simple REST API with Bearer Token** - Basic authenticated API call
2. **REST API with API Key** - Using API key in headers or query params
3. **GraphQL API** - Making GraphQL queries
4. **POST with JSON Body** - Creating resources
5. **Response Transformation** - Custom data transformation
6. **JSON Path Extraction** - Extracting specific fields
7. **Retry Logic** - Exponential backoff on failures
8. **Basic Authentication** - Using username/password
9. **Custom Headers and Params** - Advanced request configuration
10. **SOAP API** - XML-based SOAP requests
11. **Error Handling** - Error recovery and state history
12. **FSA Visualization** - Understanding the state machine

## Running Examples

```bash
# Run all examples
python cookbook/fsa/api_integrator_examples.py

# Or import specific examples in your code
from cookbook.fsa.api_integrator_examples import example_rest_api_with_bearer
example_rest_api_with_bearer()
```

## Creating Custom FSAs

You can create your own FSAs by extending the base `FSA` class:

```python
from agno.fsa import FSA, State, StateContext, Transition

class MyCustomFSA(FSA):
    def __init__(self, name: str = "my_fsa", **kwargs):
        super().__init__(name=name, initial_state="START", **kwargs)

        # Add states
        self.add_state(State(
            name="START",
            execute_func=self._start_state,
        ))

        self.add_state(State(
            name="PROCESS",
            execute_func=self._process_state,
        ))

        self.add_state(State(
            name="END",
            is_terminal=True,
        ))

        # Add transitions
        self.add_transition(Transition(
            from_state="START",
            to_state="PROCESS",
            condition=lambda ctx: ctx.get("ready") == True,
        ))

        self.add_transition(Transition(
            from_state="PROCESS",
            to_state="END",
            condition=lambda ctx: ctx.get("complete") == True,
        ))

    def _start_state(self, context: StateContext) -> StateContext:
        # State logic here
        context.set("ready", True)
        return context

    def _process_state(self, context: StateContext) -> StateContext:
        # Processing logic
        context.set("complete", True)
        return context
```

## State Machine Structure

The API Integrator FSA follows this state flow:

```
INITIALIZE
    │
    ├─→ AUTHENTICATE (if auth required)
    │       │
    │       └─→ BUILD_REQUEST
    │
    └─→ BUILD_REQUEST (if no auth)
            │
            └─→ EXECUTE_REQUEST
                    │
                    ├─→ PARSE_RESPONSE (on success)
                    │       │
                    │       └─→ TRANSFORM_RESPONSE
                    │               │
                    │               └─→ SUCCESS ✓
                    │
                    ├─→ RETRY (on retryable error)
                    │       │
                    │       └─→ EXECUTE_REQUEST (retry)
                    │
                    └─→ ERROR ✗ (on failure)
```

## Best Practices

1. **Use specific authentication types**: Choose the most appropriate auth method for your API
2. **Configure retry logic**: Set reasonable max_retries and backoff strategies
3. **Transform responses**: Use transformation functions to extract only needed data
4. **Handle errors gracefully**: Check for error states in your response handlers
5. **Close sessions**: Always call `integrator.close()` when done
6. **Monitor state history**: Use `context.state_history` for debugging

## Advanced Features

### Custom Response Transformation

```python
def transform_data(data: dict) -> dict:
    return {
        "id": data["id"],
        "name": data["name"].upper(),
        "active": data.get("status") == "active",
    }

integrator = APIIntegrator(
    name="api",
    base_url="https://api.example.com",
    response_config=ResponseConfig(
        transform_func=transform_data,
    ),
)
```

### Retry with Linear Backoff

```python
integrator = APIIntegrator(
    name="api",
    base_url="https://api.example.com",
    retry_config=RetryConfig(
        max_retries=5,
        strategy=RetryStrategy.LINEAR,
        initial_delay=2.0,
        max_delay=10.0,
    ),
)
```

### JSON Path Extraction

```python
# Extract nested data: data.users[0].name
integrator = APIIntegrator(
    name="api",
    base_url="https://api.example.com",
    response_config=ResponseConfig(
        extract_path="data.users[0].name",
    ),
)
```

## Documentation

For more information on FSAs and the Agno Framework, see:
- [Agno Documentation](https://docs.agno.ai)
- [API Reference](https://docs.agno.ai/api-reference)
- [Workflow Documentation](https://docs.agno.ai/workflows)

## Contributing

When adding new FSA examples:
1. Create a new example function in `api_integrator_examples.py`
2. Document the use case clearly
3. Include error handling
4. Add it to the main() function (commented out if it requires credentials)
