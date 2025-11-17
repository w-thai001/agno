import time
import hashlib
import json
from enum import Enum
from typing import Any, Dict, Optional, Callable, List
from datetime import datetime, timedelta
from collections import defaultdict
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class AuthType(Enum):
    API_KEY = "api_key"
    OAUTH = "oauth"
    JWT = "jwt"
    BEARER = "bearer"


class EndpointType(Enum):
    REST = "rest"
    GRAPHQL = "graphql"
    WEBHOOK = "webhook"


class APIIntegratorFSA:
    def __init__(
        self,
        base_url: str,
        auth_type: AuthType = AuthType.API_KEY,
        auth_credentials: Optional[Dict[str, Any]] = None,
        rate_limit_calls: int = 100,
        rate_limit_period: int = 60,
        circuit_failure_threshold: int = 5,
        circuit_timeout: int = 60,
        circuit_success_threshold: int = 2,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        timeout: int = 30,
        cache_enabled: bool = True,
        cache_ttl: int = 300,
    ):
        self.base_url = base_url.rstrip("/")
        self.auth_type = auth_type
        self.auth_credentials = auth_credentials or {}

        # Rate limiting
        self.rate_limit_calls = rate_limit_calls
        self.rate_limit_period = rate_limit_period
        self._rate_limit_tracker: List[float] = []

        # Circuit breaker
        self.circuit_state = CircuitState.CLOSED
        self.circuit_failure_threshold = circuit_failure_threshold
        self.circuit_timeout = circuit_timeout
        self.circuit_success_threshold = circuit_success_threshold
        self._circuit_failures = 0
        self._circuit_successes = 0
        self._circuit_opened_at: Optional[float] = None

        # Retry configuration
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.timeout = timeout

        # Caching
        self.cache_enabled = cache_enabled
        self.cache_ttl = cache_ttl
        self._cache: Dict[str, Dict[str, Any]] = {}

        # Request deduplication
        self._pending_requests: Dict[str, Any] = {}

        # Session with retry strategy
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        session = requests.Session()
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=self.backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def integrate_api(
        self,
        endpoint: str,
        method: str = "GET",
        endpoint_type: EndpointType = EndpointType.REST,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        transform_request: Optional[Callable] = None,
        transform_response: Optional[Callable] = None,
        validate_response: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        # Check circuit breaker
        if not self.circuit_breaker_check():
            raise Exception(f"Circuit breaker is {self.circuit_state.value}")

        # Apply rate limiting
        self.apply_rate_limit()

        # Transform request if needed
        if transform_request:
            data = transform_request(data)

        # Prepare request based on endpoint type
        if endpoint_type == EndpointType.GRAPHQL:
            data = self._prepare_graphql_request(data)
            method = "POST"

        # Send request
        try:
            response = self.send_request(
                endpoint=endpoint,
                method=method,
                data=data,
                params=params,
                headers=headers,
            )

            # Handle response
            result = self.handle_response(
                response=response,
                transform_response=transform_response,
                validate_response=validate_response,
            )

            # Record success for circuit breaker
            self._record_success()

            return result

        except Exception as e:
            # Record failure for circuit breaker
            self._record_failure()
            raise

    def send_request(
        self,
        endpoint: str,
        method: str = "GET",
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> requests.Response:
        # Generate request hash for caching and deduplication
        request_hash = self._generate_request_hash(endpoint, method, data, params)

        # Check cache
        if method.upper() == "GET" and self.cache_enabled:
            cached_response = self._get_cached_response(request_hash)
            if cached_response:
                return cached_response

        # Check for duplicate pending requests
        if request_hash in self._pending_requests:
            return self._pending_requests[request_hash]

        # Prepare headers with authentication
        request_headers = self.manage_auth(headers)

        # Build full URL
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        # Make request
        try:
            self._pending_requests[request_hash] = True

            response = self.session.request(
                method=method.upper(),
                url=url,
                json=data,
                params=params,
                headers=request_headers,
                timeout=self.timeout,
            )

            response.raise_for_status()

            # Cache GET requests
            if method.upper() == "GET" and self.cache_enabled:
                self._cache_response(request_hash, response)

            return response

        finally:
            # Remove from pending requests
            self._pending_requests.pop(request_hash, None)

    def handle_response(
        self,
        response: requests.Response,
        transform_response: Optional[Callable] = None,
        validate_response: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        try:
            result = response.json()
        except ValueError:
            result = {"text": response.text, "status_code": response.status_code}

        # Transform response if needed
        if transform_response:
            result = transform_response(result)

        # Validate response if needed
        if validate_response:
            is_valid = validate_response(result)
            if not is_valid:
                raise ValueError("Response validation failed")

        return result

    def manage_auth(self, headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        auth_headers = headers.copy() if headers else {}

        if self.auth_type == AuthType.API_KEY:
            key_name = self.auth_credentials.get("key_name", "X-API-Key")
            key_value = self.auth_credentials.get("key_value", "")
            auth_headers[key_name] = key_value

        elif self.auth_type == AuthType.BEARER or self.auth_type == AuthType.JWT:
            token = self.auth_credentials.get("token", "")
            auth_headers["Authorization"] = f"Bearer {token}"

        elif self.auth_type == AuthType.OAUTH:
            token = self.auth_credentials.get("access_token", "")
            auth_headers["Authorization"] = f"Bearer {token}"

        return auth_headers

    def apply_rate_limit(self) -> None:
        current_time = time.time()

        # Remove old timestamps outside the rate limit period
        cutoff_time = current_time - self.rate_limit_period
        self._rate_limit_tracker = [
            ts for ts in self._rate_limit_tracker if ts > cutoff_time
        ]

        # Check if rate limit is exceeded
        if len(self._rate_limit_tracker) >= self.rate_limit_calls:
            # Calculate wait time
            oldest_timestamp = self._rate_limit_tracker[0]
            wait_time = self.rate_limit_period - (current_time - oldest_timestamp)
            if wait_time > 0:
                time.sleep(wait_time)
                current_time = time.time()

        # Add current request timestamp
        self._rate_limit_tracker.append(current_time)

    def circuit_breaker_check(self) -> bool:
        current_time = time.time()

        if self.circuit_state == CircuitState.CLOSED:
            return True

        elif self.circuit_state == CircuitState.OPEN:
            # Check if timeout has elapsed
            if (
                self._circuit_opened_at
                and current_time - self._circuit_opened_at >= self.circuit_timeout
            ):
                # Transition to HALF_OPEN
                self.circuit_state = CircuitState.HALF_OPEN
                self._circuit_successes = 0
                return True
            return False

        elif self.circuit_state == CircuitState.HALF_OPEN:
            return True

        return False

    def _record_success(self) -> None:
        if self.circuit_state == CircuitState.HALF_OPEN:
            self._circuit_successes += 1
            if self._circuit_successes >= self.circuit_success_threshold:
                # Transition to CLOSED
                self.circuit_state = CircuitState.CLOSED
                self._circuit_failures = 0
                self._circuit_successes = 0
        elif self.circuit_state == CircuitState.CLOSED:
            self._circuit_failures = 0

    def _record_failure(self) -> None:
        if self.circuit_state == CircuitState.HALF_OPEN:
            # Transition back to OPEN
            self.circuit_state = CircuitState.OPEN
            self._circuit_opened_at = time.time()
            self._circuit_successes = 0
        elif self.circuit_state == CircuitState.CLOSED:
            self._circuit_failures += 1
            if self._circuit_failures >= self.circuit_failure_threshold:
                # Transition to OPEN
                self.circuit_state = CircuitState.OPEN
                self._circuit_opened_at = time.time()

    def _generate_request_hash(
        self,
        endpoint: str,
        method: str,
        data: Optional[Dict[str, Any]],
        params: Optional[Dict[str, Any]],
    ) -> str:
        request_str = f"{method}:{endpoint}:{json.dumps(data, sort_keys=True)}:{json.dumps(params, sort_keys=True)}"
        return hashlib.md5(request_str.encode()).hexdigest()

    def _get_cached_response(self, request_hash: str) -> Optional[requests.Response]:
        if request_hash in self._cache:
            cached_entry = self._cache[request_hash]
            if time.time() - cached_entry["timestamp"] < self.cache_ttl:
                return cached_entry["response"]
            else:
                # Cache expired
                del self._cache[request_hash]
        return None

    def _cache_response(self, request_hash: str, response: requests.Response) -> None:
        self._cache[request_hash] = {
            "response": response,
            "timestamp": time.time(),
        }

    def _prepare_graphql_request(self, data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not data:
            raise ValueError("GraphQL request requires query in data")

        graphql_request = {}
        if "query" in data:
            graphql_request["query"] = data["query"]
        if "variables" in data:
            graphql_request["variables"] = data["variables"]
        if "operationName" in data:
            graphql_request["operationName"] = data["operationName"]

        return graphql_request

    def reset_circuit_breaker(self) -> None:
        self.circuit_state = CircuitState.CLOSED
        self._circuit_failures = 0
        self._circuit_successes = 0
        self._circuit_opened_at = None

    def clear_cache(self) -> None:
        self._cache.clear()

    def get_circuit_state(self) -> CircuitState:
        return self.circuit_state

    def get_rate_limit_status(self) -> Dict[str, Any]:
        current_time = time.time()
        cutoff_time = current_time - self.rate_limit_period
        active_requests = [ts for ts in self._rate_limit_tracker if ts > cutoff_time]

        return {
            "current_requests": len(active_requests),
            "limit": self.rate_limit_calls,
            "period": self.rate_limit_period,
            "available": self.rate_limit_calls - len(active_requests),
        }
