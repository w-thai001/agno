"""
API Integrator FSA - Production-ready finite state automaton for API integration.

Supports:
- REST, GraphQL, and SOAP endpoints
- Multiple authentication methods (Bearer, API Key, OAuth 2.0)
- Request building with headers, body, query parameters
- Response parsing and transformation
- Retry logic with exponential backoff
- Error handling and recovery
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterator, List, Literal, Optional, Union
from enum import Enum
import time
import json
import requests
from requests.auth import HTTPBasicAuth, AuthBase
from urllib.parse import urljoin
import xml.etree.ElementTree as ET

try:
    from requests_oauthlib import OAuth2Session
    oauth_available = True
except ImportError:
    oauth_available = False

from agno.fsa.base import FSA, State, StateContext, Transition
from agno.run.response import RunResponse
from agno.utils.log import logger


class AuthType(str, Enum):
    """Supported authentication types"""
    NONE = "none"
    BEARER = "bearer"
    API_KEY = "api_key"
    BASIC = "basic"
    OAUTH2 = "oauth2"


class RequestMethod(str, Enum):
    """HTTP request methods"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class APIType(str, Enum):
    """API protocol types"""
    REST = "rest"
    GRAPHQL = "graphql"
    SOAP = "soap"


class RetryStrategy(str, Enum):
    """Retry strategies"""
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    FIXED = "fixed"


@dataclass
class AuthConfig:
    """
    Authentication configuration.

    Attributes:
        auth_type: Type of authentication
        token: Bearer token or API key value
        api_key_name: Name of the API key header/param
        api_key_location: Where to place API key ('header' or 'query')
        username: Username for basic auth
        password: Password for basic auth
        oauth_client_id: OAuth 2.0 client ID
        oauth_client_secret: OAuth 2.0 client secret
        oauth_token_url: OAuth 2.0 token endpoint
        oauth_authorize_url: OAuth 2.0 authorization endpoint
        oauth_redirect_uri: OAuth 2.0 redirect URI
        oauth_scope: OAuth 2.0 scopes
    """
    auth_type: AuthType = AuthType.NONE
    token: Optional[str] = None
    api_key_name: Optional[str] = "X-API-Key"
    api_key_location: Literal["header", "query"] = "header"
    username: Optional[str] = None
    password: Optional[str] = None
    oauth_client_id: Optional[str] = None
    oauth_client_secret: Optional[str] = None
    oauth_token_url: Optional[str] = None
    oauth_authorize_url: Optional[str] = None
    oauth_redirect_uri: Optional[str] = None
    oauth_scope: Optional[List[str]] = None


@dataclass
class RetryConfig:
    """
    Retry configuration.

    Attributes:
        max_retries: Maximum number of retry attempts
        strategy: Retry strategy (exponential, linear, fixed)
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        backoff_factor: Multiplier for exponential backoff
        retry_on_status: HTTP status codes to retry on
    """
    max_retries: int = 3
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    initial_delay: float = 1.0
    max_delay: float = 60.0
    backoff_factor: float = 2.0
    retry_on_status: List[int] = field(default_factory=lambda: [429, 500, 502, 503, 504])


@dataclass
class RequestConfig:
    """
    HTTP request configuration.

    Attributes:
        method: HTTP method
        endpoint: API endpoint path
        headers: Request headers
        query_params: Query parameters
        body: Request body (JSON, dict, or string)
        timeout: Request timeout in seconds
        verify_ssl: Whether to verify SSL certificates
        follow_redirects: Whether to follow redirects
    """
    method: RequestMethod = RequestMethod.GET
    endpoint: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    query_params: Dict[str, Any] = field(default_factory=dict)
    body: Optional[Union[Dict[str, Any], str]] = None
    timeout: int = 30
    verify_ssl: bool = True
    follow_redirects: bool = True


@dataclass
class ResponseConfig:
    """
    Response parsing and transformation configuration.

    Attributes:
        parse_json: Whether to parse response as JSON
        parse_xml: Whether to parse response as XML
        extract_path: JSON path or XPath to extract from response
        transform_func: Custom transformation function
        success_status_codes: List of status codes considered successful
    """
    parse_json: bool = True
    parse_xml: bool = False
    extract_path: Optional[str] = None
    transform_func: Optional[Callable[[Any], Any]] = None
    success_status_codes: List[int] = field(default_factory=lambda: [200, 201, 202, 204])


class OAuth2Bearer(AuthBase):
    """Custom OAuth2 Bearer auth for requests"""

    def __init__(self, token: str):
        self.token = token

    def __call__(self, r):
        r.headers["Authorization"] = f"Bearer {self.token}"
        return r


class APIIntegrator(FSA):
    """
    Production-ready API Integrator FSA.

    A comprehensive finite state automaton for handling API integrations with
    support for multiple protocols, authentication methods, retry logic, and
    response transformation.

    States:
        - INITIALIZE: Setup and validation
        - AUTHENTICATE: Handle authentication if required
        - BUILD_REQUEST: Construct HTTP request
        - EXECUTE_REQUEST: Make API call
        - PARSE_RESPONSE: Parse response data
        - TRANSFORM_RESPONSE: Transform parsed data
        - RETRY: Handle retry with backoff
        - ERROR: Error handling
        - SUCCESS: Terminal success state

    Example:
        >>> integrator = APIIntegrator(
        ...     name="github_api",
        ...     base_url="https://api.github.com",
        ...     auth_config=AuthConfig(auth_type=AuthType.BEARER, token="ghp_xxx"),
        ...     retry_config=RetryConfig(max_retries=3)
        ... )
        >>> request = RequestConfig(
        ...     method=RequestMethod.GET,
        ...     endpoint="/users/octocat"
        ... )
        >>> for response in integrator.run(request=request):
        ...     if response.event == "RunCompleted":
        ...         print(response.content)
    """

    def __init__(
        self,
        name: str = "api_integrator",
        base_url: str = "",
        api_type: APIType = APIType.REST,
        auth_config: Optional[AuthConfig] = None,
        retry_config: Optional[RetryConfig] = None,
        response_config: Optional[ResponseConfig] = None,
        default_headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ):
        """
        Initialize API Integrator FSA.

        Args:
            name: Name of the integrator
            base_url: Base URL for API endpoints
            api_type: Type of API (REST, GraphQL, SOAP)
            auth_config: Authentication configuration
            retry_config: Retry configuration
            response_config: Response parsing configuration
            default_headers: Default headers for all requests
            **kwargs: Additional FSA arguments
        """
        super().__init__(name=name, initial_state="INITIALIZE", **kwargs)

        # Configuration
        self.base_url = base_url.rstrip("/") if base_url else ""
        self.api_type = api_type
        self.auth_config = auth_config or AuthConfig()
        self.retry_config = retry_config or RetryConfig()
        self.response_config = response_config or ResponseConfig()
        self.default_headers = default_headers or {}

        # Session for connection pooling
        self.session = requests.Session()

        # Build state machine
        self._build_states()
        self._build_transitions()

    def _build_states(self) -> None:
        """Build FSA states"""

        # INITIALIZE state
        self.add_state(State(
            name="INITIALIZE",
            execute_func=self._initialize,
            on_enter=lambda ctx: logger.info("Initializing API integration"),
        ))

        # AUTHENTICATE state
        self.add_state(State(
            name="AUTHENTICATE",
            execute_func=self._authenticate,
            on_enter=lambda ctx: logger.info("Authenticating"),
        ))

        # BUILD_REQUEST state
        self.add_state(State(
            name="BUILD_REQUEST",
            execute_func=self._build_request,
            on_enter=lambda ctx: logger.info("Building request"),
        ))

        # EXECUTE_REQUEST state
        self.add_state(State(
            name="EXECUTE_REQUEST",
            execute_func=self._execute_request,
            on_enter=lambda ctx: logger.info("Executing request"),
            max_retries=self.retry_config.max_retries,
        ))

        # PARSE_RESPONSE state
        self.add_state(State(
            name="PARSE_RESPONSE",
            execute_func=self._parse_response,
            on_enter=lambda ctx: logger.info("Parsing response"),
        ))

        # TRANSFORM_RESPONSE state
        self.add_state(State(
            name="TRANSFORM_RESPONSE",
            execute_func=self._transform_response,
            on_enter=lambda ctx: logger.info("Transforming response"),
        ))

        # RETRY state
        self.add_state(State(
            name="RETRY",
            execute_func=self._handle_retry,
            on_enter=lambda ctx: logger.info("Handling retry"),
        ))

        # ERROR state
        self.add_state(State(
            name="ERROR",
            execute_func=self._handle_error,
            is_terminal=True,
        ))

        # SUCCESS state
        self.add_state(State(
            name="SUCCESS",
            execute_func=self._handle_success,
            is_terminal=True,
        ))

    def _build_transitions(self) -> None:
        """Build FSA transitions"""

        # INITIALIZE -> AUTHENTICATE or BUILD_REQUEST
        self.add_transition(Transition(
            from_state="INITIALIZE",
            to_state="AUTHENTICATE",
            condition=lambda ctx: self.auth_config.auth_type != AuthType.NONE,
            priority=10,
        ))

        self.add_transition(Transition(
            from_state="INITIALIZE",
            to_state="BUILD_REQUEST",
            condition=lambda ctx: self.auth_config.auth_type == AuthType.NONE,
            priority=5,
        ))

        # AUTHENTICATE -> BUILD_REQUEST or ERROR
        self.add_transition(Transition(
            from_state="AUTHENTICATE",
            to_state="BUILD_REQUEST",
            condition=lambda ctx: not ctx.error,
            priority=10,
        ))

        self.add_transition(Transition(
            from_state="AUTHENTICATE",
            to_state="ERROR",
            condition=lambda ctx: ctx.error is not None,
            priority=5,
        ))

        # BUILD_REQUEST -> EXECUTE_REQUEST or ERROR
        self.add_transition(Transition(
            from_state="BUILD_REQUEST",
            to_state="EXECUTE_REQUEST",
            condition=lambda ctx: ctx.get("request_built") == True,
            priority=10,
        ))

        self.add_transition(Transition(
            from_state="BUILD_REQUEST",
            to_state="ERROR",
            condition=lambda ctx: ctx.error is not None,
            priority=5,
        ))

        # EXECUTE_REQUEST -> PARSE_RESPONSE, RETRY, or ERROR
        self.add_transition(Transition(
            from_state="EXECUTE_REQUEST",
            to_state="PARSE_RESPONSE",
            condition=lambda ctx: (
                ctx.get("response") is not None
                and ctx.get("response").status_code in self.response_config.success_status_codes
            ),
            priority=10,
        ))

        self.add_transition(Transition(
            from_state="EXECUTE_REQUEST",
            to_state="RETRY",
            condition=lambda ctx: (
                ctx.get("response") is not None
                and ctx.get("response").status_code in self.retry_config.retry_on_status
                and ctx.retry_count < self.retry_config.max_retries
            ),
            priority=8,
        ))

        self.add_transition(Transition(
            from_state="EXECUTE_REQUEST",
            to_state="ERROR",
            condition=lambda ctx: (
                ctx.error is not None
                or (ctx.get("response") is not None
                    and ctx.get("response").status_code not in self.response_config.success_status_codes
                    and ctx.get("response").status_code not in self.retry_config.retry_on_status)
            ),
            priority=5,
        ))

        # RETRY -> EXECUTE_REQUEST
        self.add_transition(Transition(
            from_state="RETRY",
            to_state="EXECUTE_REQUEST",
            condition=lambda ctx: ctx.get("retry_ready") == True,
            priority=10,
        ))

        # PARSE_RESPONSE -> TRANSFORM_RESPONSE or ERROR
        self.add_transition(Transition(
            from_state="PARSE_RESPONSE",
            to_state="TRANSFORM_RESPONSE",
            condition=lambda ctx: ctx.get("parsed_data") is not None,
            priority=10,
        ))

        self.add_transition(Transition(
            from_state="PARSE_RESPONSE",
            to_state="ERROR",
            condition=lambda ctx: ctx.error is not None,
            priority=5,
        ))

        # TRANSFORM_RESPONSE -> SUCCESS or ERROR
        self.add_transition(Transition(
            from_state="TRANSFORM_RESPONSE",
            to_state="SUCCESS",
            condition=lambda ctx: ctx.get("final_data") is not None,
            priority=10,
        ))

        self.add_transition(Transition(
            from_state="TRANSFORM_RESPONSE",
            to_state="ERROR",
            condition=lambda ctx: ctx.error is not None,
            priority=5,
        ))

    def _initialize(self, context: StateContext) -> StateContext:
        """Initialize the integration"""
        try:
            # Validate configuration
            request_config = context.get("request")
            if not request_config:
                raise ValueError("Request configuration is required")

            if not isinstance(request_config, RequestConfig):
                raise ValueError("request must be a RequestConfig instance")

            # Store request config
            context.set("request_config", request_config)

            # Initialize retry counter
            context.set("attempt", 0)

            logger.debug(f"Initialized API integration for {self.base_url}")

        except Exception as e:
            context.set_error(e)
            logger.error(f"Initialization error: {e}")

        return context

    def _authenticate(self, context: StateContext) -> StateContext:
        """Handle authentication"""
        try:
            auth = None

            if self.auth_config.auth_type == AuthType.BEARER:
                if not self.auth_config.token:
                    raise ValueError("Bearer token is required")
                auth = OAuth2Bearer(self.auth_config.token)

            elif self.auth_config.auth_type == AuthType.API_KEY:
                if not self.auth_config.token:
                    raise ValueError("API key is required")
                # Store API key for request building
                context.set("api_key", self.auth_config.token)
                context.set("api_key_name", self.auth_config.api_key_name)
                context.set("api_key_location", self.auth_config.api_key_location)

            elif self.auth_config.auth_type == AuthType.BASIC:
                if not self.auth_config.username or not self.auth_config.password:
                    raise ValueError("Username and password are required for basic auth")
                auth = HTTPBasicAuth(self.auth_config.username, self.auth_config.password)

            elif self.auth_config.auth_type == AuthType.OAUTH2:
                if not oauth_available:
                    raise ImportError("requests-oauthlib is required for OAuth2. Install with: pip install requests-oauthlib")

                if not all([
                    self.auth_config.oauth_client_id,
                    self.auth_config.oauth_client_secret,
                    self.auth_config.oauth_token_url,
                ]):
                    raise ValueError("OAuth2 requires client_id, client_secret, and token_url")

                # Create OAuth2 session
                oauth = OAuth2Session(
                    self.auth_config.oauth_client_id,
                    redirect_uri=self.auth_config.oauth_redirect_uri,
                    scope=self.auth_config.oauth_scope,
                )

                # Fetch token
                token = oauth.fetch_token(
                    token_url=self.auth_config.oauth_token_url,
                    client_secret=self.auth_config.oauth_client_secret,
                )

                auth = OAuth2Bearer(token["access_token"])
                context.set("oauth_token", token)

            # Store auth object
            if auth:
                context.set("auth", auth)

            logger.debug(f"Authentication configured: {self.auth_config.auth_type}")

        except Exception as e:
            context.set_error(e)
            logger.error(f"Authentication error: {e}")

        return context

    def _build_request(self, context: StateContext) -> StateContext:
        """Build HTTP request"""
        try:
            request_config: RequestConfig = context.get("request_config")

            # Build URL
            if self.base_url:
                url = urljoin(self.base_url + "/", request_config.endpoint.lstrip("/"))
            else:
                url = request_config.endpoint

            context.set("url", url)

            # Build headers
            headers = {**self.default_headers, **request_config.headers}

            # Add content-type based on API type
            if self.api_type == APIType.GRAPHQL and "Content-Type" not in headers:
                headers["Content-Type"] = "application/json"
            elif self.api_type == APIType.SOAP and "Content-Type" not in headers:
                headers["Content-Type"] = "text/xml; charset=utf-8"

            # Add API key to headers if needed
            if self.auth_config.auth_type == AuthType.API_KEY:
                if context.get("api_key_location") == "header":
                    headers[context.get("api_key_name")] = context.get("api_key")

            context.set("headers", headers)

            # Build query params
            params = dict(request_config.query_params)

            # Add API key to query params if needed
            if self.auth_config.auth_type == AuthType.API_KEY:
                if context.get("api_key_location") == "query":
                    params[context.get("api_key_name")] = context.get("api_key")

            context.set("params", params)

            # Build body
            body = request_config.body

            # For GraphQL, wrap query in proper format
            if self.api_type == APIType.GRAPHQL and body:
                if isinstance(body, str):
                    body = {"query": body}
                elif isinstance(body, dict) and "query" not in body:
                    body = {"query": json.dumps(body)}

            context.set("body", body)

            # Store method
            context.set("method", request_config.method.value)

            # Store timeout
            context.set("timeout", request_config.timeout)

            # Store SSL verification setting
            context.set("verify_ssl", request_config.verify_ssl)

            context.set("request_built", True)

            logger.debug(f"Built request: {request_config.method.value} {url}")

        except Exception as e:
            context.set_error(e)
            logger.error(f"Request building error: {e}")

        return context

    def _execute_request(self, context: StateContext) -> StateContext:
        """Execute HTTP request"""
        try:
            # Increment attempt counter
            attempt = context.get("attempt", 0) + 1
            context.set("attempt", attempt)

            # Prepare request parameters
            request_params = {
                "method": context.get("method"),
                "url": context.get("url"),
                "headers": context.get("headers"),
                "params": context.get("params"),
                "timeout": context.get("timeout"),
                "verify": context.get("verify_ssl"),
                "allow_redirects": True,
            }

            # Add auth
            auth = context.get("auth")
            if auth:
                request_params["auth"] = auth

            # Add body
            body = context.get("body")
            if body:
                if isinstance(body, dict):
                    if self.api_type == APIType.SOAP:
                        request_params["data"] = json.dumps(body)
                    else:
                        request_params["json"] = body
                else:
                    request_params["data"] = body

            # Log request
            logger.info(f"Attempt {attempt}: {request_params['method']} {request_params['url']}")

            # Make request
            response = self.session.request(**request_params)

            # Store response
            context.set("response", response)

            logger.debug(f"Response status: {response.status_code}")

        except requests.exceptions.Timeout as e:
            logger.error(f"Request timeout: {e}")
            context.set_error(e)

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error: {e}")
            context.set_error(e)

        except Exception as e:
            logger.error(f"Request execution error: {e}")
            context.set_error(e)

        return context

    def _handle_retry(self, context: StateContext) -> StateContext:
        """Handle retry with backoff"""
        try:
            # Increment retry counter
            retry_count = context.increment_retry()

            # Calculate delay based on strategy
            if self.retry_config.strategy == RetryStrategy.EXPONENTIAL:
                delay = min(
                    self.retry_config.initial_delay * (self.retry_config.backoff_factor ** (retry_count - 1)),
                    self.retry_config.max_delay
                )
            elif self.retry_config.strategy == RetryStrategy.LINEAR:
                delay = min(
                    self.retry_config.initial_delay * retry_count,
                    self.retry_config.max_delay
                )
            else:  # FIXED
                delay = self.retry_config.initial_delay

            logger.info(f"Retry {retry_count}/{self.retry_config.max_retries} after {delay}s")

            # Sleep for delay
            time.sleep(delay)

            # Clear error state
            context.clear_error()

            # Mark ready for retry
            context.set("retry_ready", True)

        except Exception as e:
            logger.error(f"Retry handling error: {e}")
            context.set_error(e)

        return context

    def _parse_response(self, context: StateContext) -> StateContext:
        """Parse response data"""
        try:
            response = context.get("response")
            if not response:
                raise ValueError("No response to parse")

            parsed_data = None

            # Parse JSON
            if self.response_config.parse_json:
                try:
                    parsed_data = response.json()
                except json.JSONDecodeError:
                    # Not JSON, try text
                    parsed_data = response.text

            # Parse XML
            elif self.response_config.parse_xml:
                try:
                    root = ET.fromstring(response.content)
                    parsed_data = self._xml_to_dict(root)
                except ET.ParseError as e:
                    logger.error(f"XML parsing error: {e}")
                    parsed_data = response.text

            # Default to text
            else:
                parsed_data = response.text

            # Extract specific path if configured
            if self.response_config.extract_path and isinstance(parsed_data, dict):
                parsed_data = self._extract_json_path(parsed_data, self.response_config.extract_path)

            context.set("parsed_data", parsed_data)

            logger.debug("Response parsed successfully")

        except Exception as e:
            logger.error(f"Response parsing error: {e}")
            context.set_error(e)

        return context

    def _transform_response(self, context: StateContext) -> StateContext:
        """Transform parsed response"""
        try:
            parsed_data = context.get("parsed_data")

            # Apply custom transformation if provided
            if self.response_config.transform_func:
                final_data = self.response_config.transform_func(parsed_data)
            else:
                final_data = parsed_data

            # Store response metadata
            response = context.get("response")
            context.set("response_status", response.status_code)
            context.set("response_headers", dict(response.headers))

            context.set("final_data", final_data)

            logger.debug("Response transformed successfully")

        except Exception as e:
            logger.error(f"Response transformation error: {e}")
            context.set_error(e)

        return context

    def _handle_error(self, context: StateContext) -> StateContext:
        """Handle error state"""
        error = context.error
        response = context.get("response")

        error_info = {
            "error": str(error) if error else "Unknown error",
            "state_history": context.state_history,
            "attempts": context.get("attempt", 0),
        }

        if response:
            error_info["status_code"] = response.status_code
            error_info["response_text"] = response.text[:500]  # Truncate

        context.set("error_info", error_info)

        logger.error(f"API integration failed: {error_info}")

        return context

    def _handle_success(self, context: StateContext) -> StateContext:
        """Handle success state"""
        final_data = context.get("final_data")

        success_info = {
            "data": final_data,
            "status_code": context.get("response_status"),
            "attempts": context.get("attempt", 0),
            "state_history": context.state_history,
        }

        context.set("success_info", success_info)

        logger.info("API integration completed successfully")

        return context

    def _xml_to_dict(self, element: ET.Element) -> Dict[str, Any]:
        """Convert XML element to dictionary"""
        result = {element.tag: {} if element.attrib else None}
        children = list(element)

        if children:
            dd = {}
            for dc in map(self._xml_to_dict, children):
                for k, v in dc.items():
                    if k in dd:
                        if not isinstance(dd[k], list):
                            dd[k] = [dd[k]]
                        dd[k].append(v)
                    else:
                        dd[k] = v
            result[element.tag] = dd

        if element.attrib:
            result[element.tag].update(('@' + k, v) for k, v in element.attrib.items())

        if element.text:
            text = element.text.strip()
            if children or element.attrib:
                if text:
                    result[element.tag]['#text'] = text
            else:
                result[element.tag] = text

        return result

    def _extract_json_path(self, data: Dict[str, Any], path: str) -> Any:
        """
        Extract data from JSON using simple dot notation path.

        Example: "data.users[0].name"
        """
        keys = path.split(".")
        current = data

        for key in keys:
            # Handle array indexing
            if "[" in key and "]" in key:
                key_name = key[:key.index("[")]
                index = int(key[key.index("[") + 1:key.index("]")])

                if key_name:
                    current = current[key_name][index]
                else:
                    current = current[index]
            else:
                current = current[key]

        return current

    def run(self, request: Optional[RequestConfig] = None, **kwargs: Any) -> Iterator[RunResponse]:
        """
        Execute API integration.

        Args:
            request: Request configuration
            **kwargs: Additional context data

        Yields:
            RunResponse objects for execution progress
        """
        # Add request to context
        if request:
            kwargs["request"] = request

        # Call parent run
        yield from super().run(initial_context=kwargs)

    def close(self) -> None:
        """Close the HTTP session"""
        if self.session:
            self.session.close()
            logger.debug("HTTP session closed")

    def __del__(self):
        """Cleanup"""
        self.close()
