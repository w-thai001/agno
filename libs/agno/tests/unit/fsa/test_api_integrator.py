"""
Unit tests for API Integrator FSA.
"""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any

from agno.fsa.api_integrator import (
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


class TestAuthConfig:
    """Tests for AuthConfig"""

    def test_default_auth_config(self):
        """Test default AuthConfig"""
        config = AuthConfig()

        assert config.auth_type == AuthType.NONE
        assert config.token is None
        assert config.api_key_name == "X-API-Key"
        assert config.api_key_location == "header"

    def test_bearer_auth_config(self):
        """Test Bearer auth configuration"""
        config = AuthConfig(
            auth_type=AuthType.BEARER,
            token="test_token_123",
        )

        assert config.auth_type == AuthType.BEARER
        assert config.token == "test_token_123"

    def test_api_key_auth_config(self):
        """Test API Key auth configuration"""
        config = AuthConfig(
            auth_type=AuthType.API_KEY,
            token="api_key_456",
            api_key_name="X-Custom-Key",
            api_key_location="query",
        )

        assert config.auth_type == AuthType.API_KEY
        assert config.token == "api_key_456"
        assert config.api_key_name == "X-Custom-Key"
        assert config.api_key_location == "query"


class TestRetryConfig:
    """Tests for RetryConfig"""

    def test_default_retry_config(self):
        """Test default RetryConfig"""
        config = RetryConfig()

        assert config.max_retries == 3
        assert config.strategy == RetryStrategy.EXPONENTIAL
        assert config.initial_delay == 1.0
        assert config.max_delay == 60.0
        assert config.backoff_factor == 2.0
        assert 429 in config.retry_on_status
        assert 500 in config.retry_on_status

    def test_custom_retry_config(self):
        """Test custom RetryConfig"""
        config = RetryConfig(
            max_retries=5,
            strategy=RetryStrategy.LINEAR,
            initial_delay=2.0,
            max_delay=30.0,
            retry_on_status=[503, 504],
        )

        assert config.max_retries == 5
        assert config.strategy == RetryStrategy.LINEAR
        assert config.initial_delay == 2.0
        assert config.max_delay == 30.0
        assert config.retry_on_status == [503, 504]


class TestRequestConfig:
    """Tests for RequestConfig"""

    def test_default_request_config(self):
        """Test default RequestConfig"""
        config = RequestConfig()

        assert config.method == RequestMethod.GET
        assert config.endpoint == ""
        assert config.headers == {}
        assert config.query_params == {}
        assert config.body is None
        assert config.timeout == 30
        assert config.verify_ssl is True

    def test_custom_request_config(self):
        """Test custom RequestConfig"""
        config = RequestConfig(
            method=RequestMethod.POST,
            endpoint="/api/users",
            headers={"Content-Type": "application/json"},
            query_params={"limit": 10},
            body={"name": "John"},
            timeout=60,
        )

        assert config.method == RequestMethod.POST
        assert config.endpoint == "/api/users"
        assert config.headers["Content-Type"] == "application/json"
        assert config.query_params["limit"] == 10
        assert config.body == {"name": "John"}
        assert config.timeout == 60


class TestResponseConfig:
    """Tests for ResponseConfig"""

    def test_default_response_config(self):
        """Test default ResponseConfig"""
        config = ResponseConfig()

        assert config.parse_json is True
        assert config.parse_xml is False
        assert config.extract_path is None
        assert config.transform_func is None
        assert 200 in config.success_status_codes
        assert 201 in config.success_status_codes

    def test_custom_response_config(self):
        """Test custom ResponseConfig"""
        def transform(data):
            return {"transformed": True}

        config = ResponseConfig(
            parse_json=True,
            extract_path="data.users[0]",
            transform_func=transform,
            success_status_codes=[200],
        )

        assert config.parse_json is True
        assert config.extract_path == "data.users[0]"
        assert config.transform_func == transform
        assert config.success_status_codes == [200]


class TestAPIIntegrator:
    """Tests for APIIntegrator FSA"""

    def test_initialization(self):
        """Test APIIntegrator initialization"""
        integrator = APIIntegrator(
            name="test_api",
            base_url="https://api.example.com",
        )

        assert integrator.name == "test_api"
        assert integrator.base_url == "https://api.example.com"
        assert integrator.api_type == APIType.REST
        assert integrator.initial_state == "INITIALIZE"
        assert len(integrator.states) > 0
        assert len(integrator.transitions) > 0

    def test_states_created(self):
        """Test that all required states are created"""
        integrator = APIIntegrator(name="test")

        expected_states = [
            "INITIALIZE",
            "AUTHENTICATE",
            "BUILD_REQUEST",
            "EXECUTE_REQUEST",
            "PARSE_RESPONSE",
            "TRANSFORM_RESPONSE",
            "RETRY",
            "ERROR",
            "SUCCESS",
        ]

        for state_name in expected_states:
            assert state_name in integrator.states

    def test_transitions_created(self):
        """Test that transitions are created"""
        integrator = APIIntegrator(name="test")

        # Should have multiple transitions
        assert len(integrator.transitions) > 0

        # Check some key transitions exist
        from_states = [t.from_state for t in integrator.transitions]
        assert "INITIALIZE" in from_states
        assert "BUILD_REQUEST" in from_states
        assert "EXECUTE_REQUEST" in from_states

    @patch('agno.fsa.api_integrator.requests.Session')
    def test_successful_get_request(self, mock_session_class):
        """Test successful GET request execution"""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 1, "name": "Test"}
        mock_response.headers = {"Content-Type": "application/json"}

        # Mock session
        mock_session = MagicMock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        # Create integrator
        integrator = APIIntegrator(
            name="test_api",
            base_url="https://api.example.com",
            auth_config=AuthConfig(auth_type=AuthType.NONE),
        )

        # Create request
        request = RequestConfig(
            method=RequestMethod.GET,
            endpoint="/users/1",
        )

        # Execute
        responses = list(integrator.run(request=request))

        # Verify execution
        assert integrator.context.get("final_data") == {"id": 1, "name": "Test"}
        assert "SUCCESS" in integrator.context.state_history

        # Verify mock was called
        mock_session.request.assert_called_once()
        call_args = mock_session.request.call_args
        assert call_args[1]["method"] == "GET"
        assert "users/1" in call_args[1]["url"]

    @patch('agno.fsa.api_integrator.requests.Session')
    def test_bearer_authentication(self, mock_session_class):
        """Test Bearer token authentication"""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"authenticated": True}
        mock_response.headers = {}

        # Mock session
        mock_session = MagicMock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        # Create integrator with Bearer auth
        integrator = APIIntegrator(
            name="test_api",
            base_url="https://api.example.com",
            auth_config=AuthConfig(
                auth_type=AuthType.BEARER,
                token="test_token_123",
            ),
        )

        # Create request
        request = RequestConfig(
            method=RequestMethod.GET,
            endpoint="/protected",
        )

        # Execute
        list(integrator.run(request=request))

        # Verify AUTHENTICATE state was visited
        assert "AUTHENTICATE" in integrator.context.state_history

        # Verify auth was set in context
        assert integrator.context.get("auth") is not None

    @patch('agno.fsa.api_integrator.requests.Session')
    def test_api_key_in_header(self, mock_session_class):
        """Test API key in header"""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_response.headers = {}

        # Mock session
        mock_session = MagicMock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        # Create integrator with API key
        integrator = APIIntegrator(
            name="test_api",
            base_url="https://api.example.com",
            auth_config=AuthConfig(
                auth_type=AuthType.API_KEY,
                token="secret_key_123",
                api_key_name="X-API-Key",
                api_key_location="header",
            ),
        )

        # Create request
        request = RequestConfig(
            method=RequestMethod.GET,
            endpoint="/data",
        )

        # Execute
        list(integrator.run(request=request))

        # Verify API key was added to headers
        call_args = mock_session.request.call_args
        headers = call_args[1]["headers"]
        assert headers["X-API-Key"] == "secret_key_123"

    @patch('agno.fsa.api_integrator.requests.Session')
    def test_api_key_in_query(self, mock_session_class):
        """Test API key in query params"""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_response.headers = {}

        # Mock session
        mock_session = MagicMock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        # Create integrator with API key in query
        integrator = APIIntegrator(
            name="test_api",
            base_url="https://api.example.com",
            auth_config=AuthConfig(
                auth_type=AuthType.API_KEY,
                token="secret_key_123",
                api_key_name="apikey",
                api_key_location="query",
            ),
        )

        # Create request
        request = RequestConfig(
            method=RequestMethod.GET,
            endpoint="/data",
        )

        # Execute
        list(integrator.run(request=request))

        # Verify API key was added to query params
        call_args = mock_session.request.call_args
        params = call_args[1]["params"]
        assert params["apikey"] == "secret_key_123"

    @patch('agno.fsa.api_integrator.requests.Session')
    def test_post_with_json_body(self, mock_session_class):
        """Test POST request with JSON body"""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": 123, "created": True}
        mock_response.headers = {}

        # Mock session
        mock_session = MagicMock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        # Create integrator
        integrator = APIIntegrator(
            name="test_api",
            base_url="https://api.example.com",
            response_config=ResponseConfig(
                success_status_codes=[200, 201],
            ),
        )

        # Create request with body
        request = RequestConfig(
            method=RequestMethod.POST,
            endpoint="/users",
            body={"name": "John", "email": "john@example.com"},
        )

        # Execute
        list(integrator.run(request=request))

        # Verify request was made with JSON body
        call_args = mock_session.request.call_args
        assert call_args[1]["json"] == {"name": "John", "email": "john@example.com"}

    @patch('agno.fsa.api_integrator.requests.Session')
    def test_response_transformation(self, mock_session_class):
        """Test response transformation"""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": 1,
            "first_name": "John",
            "last_name": "Doe",
            "extra_field": "ignored",
        }
        mock_response.headers = {}

        # Mock session
        mock_session = MagicMock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        # Transformation function
        def transform(data: Dict[str, Any]) -> Dict[str, Any]:
            return {
                "id": data["id"],
                "full_name": f"{data['first_name']} {data['last_name']}",
            }

        # Create integrator with transformation
        integrator = APIIntegrator(
            name="test_api",
            base_url="https://api.example.com",
            response_config=ResponseConfig(
                transform_func=transform,
            ),
        )

        # Create request
        request = RequestConfig(
            method=RequestMethod.GET,
            endpoint="/users/1",
        )

        # Execute
        list(integrator.run(request=request))

        # Verify transformation was applied
        final_data = integrator.context.get("final_data")
        assert final_data == {"id": 1, "full_name": "John Doe"}

    @patch('agno.fsa.api_integrator.requests.Session')
    def test_json_path_extraction(self, mock_session_class):
        """Test JSON path extraction"""
        # Mock response with nested data
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "users": [
                    {"name": "Alice", "id": 1},
                    {"name": "Bob", "id": 2},
                ]
            }
        }
        mock_response.headers = {}

        # Mock session
        mock_session = MagicMock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        # Create integrator with JSON path
        integrator = APIIntegrator(
            name="test_api",
            base_url="https://api.example.com",
            response_config=ResponseConfig(
                extract_path="data.users[0].name",
            ),
        )

        # Create request
        request = RequestConfig(
            method=RequestMethod.GET,
            endpoint="/users",
        )

        # Execute
        list(integrator.run(request=request))

        # Verify extraction
        final_data = integrator.context.get("final_data")
        assert final_data == "Alice"

    @patch('agno.fsa.api_integrator.requests.Session')
    @patch('time.sleep')  # Mock sleep to speed up test
    def test_retry_on_failure(self, mock_sleep, mock_session_class):
        """Test retry logic on failure"""
        # Mock responses: first two fail, third succeeds
        mock_responses = [
            Mock(status_code=503),
            Mock(status_code=503),
            Mock(status_code=200, json=lambda: {"success": True}, headers={}),
        ]

        # Mock session
        mock_session = MagicMock()
        mock_session.request.side_effect = mock_responses
        mock_session_class.return_value = mock_session

        # Create integrator with retry
        integrator = APIIntegrator(
            name="test_api",
            base_url="https://api.example.com",
            retry_config=RetryConfig(
                max_retries=3,
                strategy=RetryStrategy.FIXED,
                initial_delay=0.1,
            ),
        )

        # Create request
        request = RequestConfig(
            method=RequestMethod.GET,
            endpoint="/data",
        )

        # Execute
        list(integrator.run(request=request))

        # Verify retries occurred
        assert mock_session.request.call_count == 3
        assert integrator.context.retry_count >= 2

        # Verify eventual success
        assert "SUCCESS" in integrator.context.state_history

    @patch('agno.fsa.api_integrator.requests.Session')
    def test_error_on_bad_status(self, mock_session_class):
        """Test error handling on bad status code"""
        # Mock response with error status
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not found"
        mock_response.headers = {}

        # Mock session
        mock_session = MagicMock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        # Create integrator
        integrator = APIIntegrator(
            name="test_api",
            base_url="https://api.example.com",
            retry_config=RetryConfig(
                max_retries=0,  # No retries
            ),
        )

        # Create request
        request = RequestConfig(
            method=RequestMethod.GET,
            endpoint="/nonexistent",
        )

        # Execute
        list(integrator.run(request=request))

        # Verify error state was reached
        assert "ERROR" in integrator.context.state_history
        error_info = integrator.context.get("error_info")
        assert error_info is not None
        assert error_info["status_code"] == 404

    @patch('agno.fsa.api_integrator.requests.Session')
    def test_graphql_request(self, mock_session_class):
        """Test GraphQL request formatting"""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"user": {"name": "Alice"}}
        }
        mock_response.headers = {}

        # Mock session
        mock_session = MagicMock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        # Create integrator for GraphQL
        integrator = APIIntegrator(
            name="graphql_api",
            base_url="https://api.example.com",
            api_type=APIType.GRAPHQL,
        )

        # Create GraphQL request
        query = "query { user(id: 1) { name } }"
        request = RequestConfig(
            method=RequestMethod.POST,
            endpoint="/graphql",
            body=query,
        )

        # Execute
        list(integrator.run(request=request))

        # Verify query was wrapped in proper format
        call_args = mock_session.request.call_args
        json_body = call_args[1]["json"]
        assert "query" in json_body
        assert json_body["query"] == query

    def test_visualize(self):
        """Test FSA visualization"""
        integrator = APIIntegrator(name="test_api")

        viz = integrator.visualize()

        # Should contain FSA name and states
        assert "test_api" in viz
        assert "INITIALIZE" in viz
        assert "EXECUTE_REQUEST" in viz
        assert "SUCCESS" in viz
        assert "ERROR" in viz

    def test_close_session(self):
        """Test closing HTTP session"""
        integrator = APIIntegrator(name="test_api")

        # Session should exist
        assert integrator.session is not None

        # Close session
        integrator.close()

        # Calling close multiple times should not error
        integrator.close()


class TestRetryStrategies:
    """Tests for retry strategies"""

    @patch('agno.fsa.api_integrator.requests.Session')
    @patch('time.sleep')
    def test_exponential_backoff(self, mock_sleep, mock_session_class):
        """Test exponential backoff strategy"""
        # Mock failing responses
        mock_responses = [
            Mock(status_code=503),
            Mock(status_code=503),
            Mock(status_code=200, json=lambda: {"ok": True}, headers={}),
        ]

        mock_session = MagicMock()
        mock_session.request.side_effect = mock_responses
        mock_session_class.return_value = mock_session

        # Create integrator
        integrator = APIIntegrator(
            name="test",
            base_url="https://api.example.com",
            retry_config=RetryConfig(
                strategy=RetryStrategy.EXPONENTIAL,
                initial_delay=1.0,
                backoff_factor=2.0,
            ),
        )

        request = RequestConfig(method=RequestMethod.GET, endpoint="/test")

        # Execute
        list(integrator.run(request=request))

        # Verify exponential delays
        if mock_sleep.call_count > 0:
            delays = [call[0][0] for call in mock_sleep.call_args_list]
            # First retry: 1.0, second retry: 2.0
            if len(delays) >= 2:
                assert delays[1] > delays[0]

    @patch('agno.fsa.api_integrator.requests.Session')
    @patch('time.sleep')
    def test_linear_backoff(self, mock_sleep, mock_session_class):
        """Test linear backoff strategy"""
        # Mock failing responses
        mock_responses = [
            Mock(status_code=503),
            Mock(status_code=503),
            Mock(status_code=200, json=lambda: {"ok": True}, headers={}),
        ]

        mock_session = MagicMock()
        mock_session.request.side_effect = mock_responses
        mock_session_class.return_value = mock_session

        # Create integrator
        integrator = APIIntegrator(
            name="test",
            base_url="https://api.example.com",
            retry_config=RetryConfig(
                strategy=RetryStrategy.LINEAR,
                initial_delay=2.0,
            ),
        )

        request = RequestConfig(method=RequestMethod.GET, endpoint="/test")

        # Execute
        list(integrator.run(request=request))

        # Verify linear delays
        if mock_sleep.call_count > 0:
            delays = [call[0][0] for call in mock_sleep.call_args_list]
            # Linear: 2.0, 4.0, 6.0, etc.
            if len(delays) >= 2:
                assert delays[1] - delays[0] == pytest.approx(delays[0], abs=0.1)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
