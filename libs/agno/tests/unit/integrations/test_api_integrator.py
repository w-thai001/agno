import pytest
import time
import json
from unittest.mock import Mock, patch, MagicMock
import requests
from agno.integrations import APIIntegratorFSA
from agno.integrations.api_integrator import (
    CircuitState,
    AuthType,
    EndpointType,
)


@pytest.fixture
def api_integrator():
    return APIIntegratorFSA(
        base_url="https://api.example.com",
        auth_type=AuthType.API_KEY,
        auth_credentials={"key_name": "X-API-Key", "key_value": "test_key"},
        rate_limit_calls=5,
        rate_limit_period=1,
        circuit_failure_threshold=3,
        circuit_timeout=2,
        max_retries=2,
        timeout=10,
    )


@pytest.fixture
def mock_response():
    response = Mock(spec=requests.Response)
    response.status_code = 200
    response.json.return_value = {"status": "success", "data": {"id": 1}}
    response.text = '{"status": "success"}'
    return response


class TestAPIIntegratorBasics:
    def test_initialization(self, api_integrator):
        assert api_integrator.base_url == "https://api.example.com"
        assert api_integrator.auth_type == AuthType.API_KEY
        assert api_integrator.circuit_state == CircuitState.CLOSED
        assert api_integrator.rate_limit_calls == 5

    def test_base_url_strip_trailing_slash(self):
        integrator = APIIntegratorFSA(base_url="https://api.example.com/")
        assert integrator.base_url == "https://api.example.com"

    @patch("requests.Session.request")
    def test_send_request_success(self, mock_request, api_integrator, mock_response):
        mock_request.return_value = mock_response

        response = api_integrator.send_request(
            endpoint="/users",
            method="GET",
        )

        assert response.status_code == 200
        mock_request.assert_called_once()
        call_kwargs = mock_request.call_args[1]
        assert call_kwargs["url"] == "https://api.example.com/users"
        assert call_kwargs["method"] == "GET"


class TestAuthentication:
    def test_manage_auth_api_key(self, api_integrator):
        headers = api_integrator.manage_auth()
        assert headers["X-API-Key"] == "test_key"

    def test_manage_auth_bearer(self):
        integrator = APIIntegratorFSA(
            base_url="https://api.example.com",
            auth_type=AuthType.BEARER,
            auth_credentials={"token": "bearer_token_123"},
        )
        headers = integrator.manage_auth()
        assert headers["Authorization"] == "Bearer bearer_token_123"

    def test_manage_auth_jwt(self):
        integrator = APIIntegratorFSA(
            base_url="https://api.example.com",
            auth_type=AuthType.JWT,
            auth_credentials={"token": "jwt_token_456"},
        )
        headers = integrator.manage_auth()
        assert headers["Authorization"] == "Bearer jwt_token_456"

    def test_manage_auth_oauth(self):
        integrator = APIIntegratorFSA(
            base_url="https://api.example.com",
            auth_type=AuthType.OAUTH,
            auth_credentials={"access_token": "oauth_token_789"},
        )
        headers = integrator.manage_auth()
        assert headers["Authorization"] == "Bearer oauth_token_789"

    def test_manage_auth_with_existing_headers(self, api_integrator):
        existing_headers = {"Content-Type": "application/json"}
        headers = api_integrator.manage_auth(existing_headers)
        assert headers["X-API-Key"] == "test_key"
        assert headers["Content-Type"] == "application/json"


class TestCircuitBreaker:
    def test_circuit_breaker_initial_state(self, api_integrator):
        assert api_integrator.circuit_state == CircuitState.CLOSED
        assert api_integrator.circuit_breaker_check() is True

    def test_circuit_breaker_opens_after_failures(self, api_integrator):
        for _ in range(3):
            api_integrator._record_failure()

        assert api_integrator.circuit_state == CircuitState.OPEN
        assert api_integrator.circuit_breaker_check() is False

    def test_circuit_breaker_half_open_after_timeout(self, api_integrator):
        # Open the circuit
        for _ in range(3):
            api_integrator._record_failure()

        assert api_integrator.circuit_state == CircuitState.OPEN

        # Wait for timeout
        time.sleep(2.1)

        # Should transition to HALF_OPEN
        assert api_integrator.circuit_breaker_check() is True
        assert api_integrator.circuit_state == CircuitState.HALF_OPEN

    def test_circuit_breaker_closes_after_successes(self, api_integrator):
        # Open the circuit
        for _ in range(3):
            api_integrator._record_failure()

        # Wait for timeout to transition to HALF_OPEN
        time.sleep(2.1)
        api_integrator.circuit_breaker_check()

        # Record successes to close
        for _ in range(2):
            api_integrator._record_success()

        assert api_integrator.circuit_state == CircuitState.CLOSED

    def test_circuit_breaker_reopens_on_failure_in_half_open(self, api_integrator):
        # Open the circuit
        for _ in range(3):
            api_integrator._record_failure()

        # Wait for timeout to transition to HALF_OPEN
        time.sleep(2.1)
        api_integrator.circuit_breaker_check()

        # Record failure in HALF_OPEN state
        api_integrator._record_failure()

        assert api_integrator.circuit_state == CircuitState.OPEN

    def test_reset_circuit_breaker(self, api_integrator):
        # Open the circuit
        for _ in range(3):
            api_integrator._record_failure()

        assert api_integrator.circuit_state == CircuitState.OPEN

        api_integrator.reset_circuit_breaker()

        assert api_integrator.circuit_state == CircuitState.CLOSED
        assert api_integrator._circuit_failures == 0


class TestRateLimiting:
    def test_rate_limit_status(self, api_integrator):
        status = api_integrator.get_rate_limit_status()
        assert status["current_requests"] == 0
        assert status["limit"] == 5
        assert status["available"] == 5

    def test_rate_limit_tracking(self, api_integrator):
        # Make 3 requests
        for _ in range(3):
            api_integrator.apply_rate_limit()

        status = api_integrator.get_rate_limit_status()
        assert status["current_requests"] == 3
        assert status["available"] == 2

    def test_rate_limit_enforcement(self, api_integrator):
        # Make requests up to limit
        start_time = time.time()
        for _ in range(6):  # One more than limit
            api_integrator.apply_rate_limit()

        elapsed_time = time.time() - start_time

        # Should have waited for rate limit reset
        assert elapsed_time >= 1.0

    def test_rate_limit_window_sliding(self, api_integrator):
        # Make requests
        for _ in range(3):
            api_integrator.apply_rate_limit()

        # Wait for window to slide
        time.sleep(1.1)

        # Old requests should be cleared
        status = api_integrator.get_rate_limit_status()
        assert status["current_requests"] == 0


class TestCaching:
    @patch("requests.Session.request")
    def test_caching_enabled(self, mock_request, mock_response):
        mock_request.return_value = mock_response

        integrator = APIIntegratorFSA(
            base_url="https://api.example.com",
            cache_enabled=True,
            cache_ttl=10,
        )

        # First request
        response1 = integrator.send_request(endpoint="/users", method="GET")

        # Second identical request should use cache
        response2 = integrator.send_request(endpoint="/users", method="GET")

        # Should only make one actual request
        assert mock_request.call_count == 1

    @patch("requests.Session.request")
    def test_cache_disabled(self, mock_request, mock_response):
        mock_request.return_value = mock_response

        integrator = APIIntegratorFSA(
            base_url="https://api.example.com",
            cache_enabled=False,
        )

        # First request
        integrator.send_request(endpoint="/users", method="GET")

        # Second identical request
        integrator.send_request(endpoint="/users", method="GET")

        # Should make two actual requests
        assert mock_request.call_count == 2

    @patch("requests.Session.request")
    def test_cache_expiration(self, mock_request, mock_response):
        mock_request.return_value = mock_response

        integrator = APIIntegratorFSA(
            base_url="https://api.example.com",
            cache_enabled=True,
            cache_ttl=1,  # 1 second TTL
        )

        # First request
        integrator.send_request(endpoint="/users", method="GET")

        # Wait for cache to expire
        time.sleep(1.1)

        # Second request after expiration
        integrator.send_request(endpoint="/users", method="GET")

        # Should make two actual requests
        assert mock_request.call_count == 2

    def test_clear_cache(self, api_integrator):
        api_integrator._cache["test_hash"] = {
            "response": Mock(),
            "timestamp": time.time(),
        }

        assert len(api_integrator._cache) == 1

        api_integrator.clear_cache()

        assert len(api_integrator._cache) == 0


class TestResponseHandling:
    def test_handle_response_json(self, api_integrator, mock_response):
        result = api_integrator.handle_response(mock_response)
        assert result["status"] == "success"
        assert result["data"]["id"] == 1

    def test_handle_response_with_transform(self, api_integrator, mock_response):
        def transform(data):
            return {"transformed": True, "original": data}

        result = api_integrator.handle_response(
            mock_response, transform_response=transform
        )
        assert result["transformed"] is True
        assert result["original"]["status"] == "success"

    def test_handle_response_with_validation(self, api_integrator, mock_response):
        def validate(data):
            return "status" in data

        result = api_integrator.handle_response(
            mock_response, validate_response=validate
        )
        assert result["status"] == "success"

    def test_handle_response_validation_failure(self, api_integrator, mock_response):
        def validate(data):
            return False

        with pytest.raises(ValueError, match="Response validation failed"):
            api_integrator.handle_response(mock_response, validate_response=validate)

    def test_handle_response_non_json(self, api_integrator):
        response = Mock(spec=requests.Response)
        response.json.side_effect = ValueError("No JSON")
        response.text = "Plain text response"
        response.status_code = 200

        result = api_integrator.handle_response(response)
        assert result["text"] == "Plain text response"
        assert result["status_code"] == 200


class TestGraphQL:
    @patch("requests.Session.request")
    def test_graphql_request_preparation(self, mock_request, mock_response):
        mock_request.return_value = mock_response

        integrator = APIIntegratorFSA(base_url="https://api.example.com")

        graphql_data = {
            "query": "{ user(id: 1) { name } }",
            "variables": {"id": 1},
            "operationName": "GetUser",
        }

        integrator.integrate_api(
            endpoint="/graphql",
            endpoint_type=EndpointType.GRAPHQL,
            data=graphql_data,
        )

        call_kwargs = mock_request.call_args[1]
        assert call_kwargs["method"] == "POST"
        assert call_kwargs["json"]["query"] == "{ user(id: 1) { name } }"
        assert call_kwargs["json"]["variables"] == {"id": 1}

    def test_graphql_request_missing_query(self, api_integrator):
        with pytest.raises(ValueError, match="GraphQL request requires query"):
            api_integrator._prepare_graphql_request(None)


class TestIntegration:
    @patch("requests.Session.request")
    def test_integrate_api_success(self, mock_request, api_integrator, mock_response):
        mock_request.return_value = mock_response

        result = api_integrator.integrate_api(
            endpoint="/users",
            method="GET",
        )

        assert result["status"] == "success"
        assert api_integrator.circuit_state == CircuitState.CLOSED

    @patch("requests.Session.request")
    def test_integrate_api_with_circuit_breaker_open(
        self, mock_request, api_integrator
    ):
        # Open the circuit
        for _ in range(3):
            api_integrator._record_failure()

        with pytest.raises(Exception, match="Circuit breaker is open"):
            api_integrator.integrate_api(endpoint="/users", method="GET")

    @patch("requests.Session.request")
    def test_integrate_api_with_transform(self, mock_request, api_integrator, mock_response):
        mock_request.return_value = mock_response

        def transform_req(data):
            return {"transformed": data}

        def transform_resp(data):
            return {"response_transformed": data}

        result = api_integrator.integrate_api(
            endpoint="/users",
            method="POST",
            data={"name": "test"},
            transform_request=transform_req,
            transform_response=transform_resp,
        )

        assert "response_transformed" in result

    @patch("requests.Session.request")
    def test_integrate_api_records_failure_on_exception(
        self, mock_request, api_integrator
    ):
        mock_request.side_effect = requests.exceptions.RequestException("Network error")

        initial_failures = api_integrator._circuit_failures

        with pytest.raises(requests.exceptions.RequestException):
            api_integrator.integrate_api(endpoint="/users", method="GET")

        assert api_integrator._circuit_failures > initial_failures


class TestUtilityMethods:
    def test_generate_request_hash(self, api_integrator):
        hash1 = api_integrator._generate_request_hash(
            endpoint="/users",
            method="GET",
            data={"id": 1},
            params={"page": 1},
        )

        hash2 = api_integrator._generate_request_hash(
            endpoint="/users",
            method="GET",
            data={"id": 1},
            params={"page": 1},
        )

        # Same input should produce same hash
        assert hash1 == hash2

        hash3 = api_integrator._generate_request_hash(
            endpoint="/users",
            method="GET",
            data={"id": 2},
            params={"page": 1},
        )

        # Different input should produce different hash
        assert hash1 != hash3

    def test_get_circuit_state(self, api_integrator):
        assert api_integrator.get_circuit_state() == CircuitState.CLOSED

        api_integrator.circuit_state = CircuitState.OPEN
        assert api_integrator.get_circuit_state() == CircuitState.OPEN
