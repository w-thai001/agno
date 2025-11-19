"""
Comprehensive API Integrator Toolkit for Agno Framework

A production-ready toolkit that handles API integration operations including:
- REST/GraphQL/SOAP endpoint management
- Request builder with method/headers/body configuration
- Response parsing and transformation
- Authentication integration (Bearer/API Key/OAuth/Basic)
- Retry logic with exponential backoff
- Rate limiting
- Error handling and logging
- Timeout management
- Connection pooling
"""

import json
import time
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List, Literal, Optional, Callable, Union
from dataclasses import dataclass, field
from urllib.parse import urljoin
import xml.etree.ElementTree as ET

from agno.tools import Toolkit
from agno.utils.log import logger

try:
    import requests
    from requests.adapters import HTTPAdapter
    from requests.auth import HTTPBasicAuth
    from urllib3.util.retry import Retry as UrllibRetry
except ImportError:
    raise ImportError("`requests` not installed. Please install using `pip install requests`")


@dataclass
class RateLimiter:
    """Token bucket rate limiter for API requests."""

    requests_per_second: float
    burst_size: int = 10
    tokens: float = field(init=False)
    last_update: float = field(init=False)
    lock: threading.Lock = field(default_factory=threading.Lock, init=False)

    def __post_init__(self):
        self.tokens = self.burst_size
        self.last_update = time.time()

    def acquire(self, tokens: int = 1) -> bool:
        """Acquire tokens from the bucket, waiting if necessary."""
        with self.lock:
            now = time.time()
            elapsed = now - self.last_update

            # Refill tokens based on time elapsed
            self.tokens = min(
                self.burst_size,
                self.tokens + elapsed * self.requests_per_second
            )
            self.last_update = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True

            # Wait for tokens to be available
            wait_time = (tokens - self.tokens) / self.requests_per_second
            time.sleep(wait_time)
            self.tokens = 0
            self.last_update = time.time()
            return True


@dataclass
class RequestConfig:
    """Configuration for API requests."""

    method: str = "GET"
    endpoint: str = ""
    params: Optional[Dict[str, Any]] = None
    headers: Optional[Dict[str, str]] = None
    data: Optional[Union[Dict[str, Any], str]] = None
    json_data: Optional[Dict[str, Any]] = None
    timeout: Optional[int] = None
    auth: Optional[tuple] = None
    verify_ssl: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "method": self.method,
            "endpoint": self.endpoint,
            "params": self.params,
            "headers": self.headers,
        }


@dataclass
class ResponseTransform:
    """Configuration for response transformation."""

    extract_path: Optional[str] = None  # JSON path to extract (e.g., "data.items")
    transform_func: Optional[Callable] = None  # Custom transformation function
    include_metadata: bool = True  # Include status code, headers, etc.

    def apply(self, response: requests.Response) -> Dict[str, Any]:
        """Apply transformation to response."""
        result = {}

        # Parse response based on content type
        content_type = response.headers.get("Content-Type", "")

        if "application/json" in content_type:
            try:
                data = response.json()
            except json.JSONDecodeError:
                data = {"text": response.text}
        elif "application/xml" in content_type or "text/xml" in content_type:
            data = self._parse_xml(response.text)
        else:
            data = {"text": response.text}

        # Extract specific path if specified
        if self.extract_path and isinstance(data, dict):
            data = self._extract_json_path(data, self.extract_path)

        # Apply custom transformation
        if self.transform_func:
            data = self.transform_func(data)

        # Build result
        if self.include_metadata:
            result = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "data": data,
            }
        else:
            result = data

        return result

    @staticmethod
    def _parse_xml(xml_string: str) -> Dict[str, Any]:
        """Parse XML to dictionary."""
        try:
            root = ET.fromstring(xml_string)
            return {"xml": ResponseTransform._element_to_dict(root)}
        except ET.ParseError as e:
            return {"error": f"XML parse error: {str(e)}", "text": xml_string}

    @staticmethod
    def _element_to_dict(element: ET.Element) -> Dict[str, Any]:
        """Convert XML element to dictionary."""
        result = {}

        # Add attributes
        if element.attrib:
            result["@attributes"] = element.attrib

        # Add text content
        if element.text and element.text.strip():
            result["text"] = element.text.strip()

        # Add child elements
        for child in element:
            child_data = ResponseTransform._element_to_dict(child)
            if child.tag in result:
                # Handle multiple elements with same tag
                if not isinstance(result[child.tag], list):
                    result[child.tag] = [result[child.tag]]
                result[child.tag].append(child_data)
            else:
                result[child.tag] = child_data

        return result

    @staticmethod
    def _extract_json_path(data: Dict[str, Any], path: str) -> Any:
        """Extract data from JSON path (e.g., 'data.items.0')."""
        keys = path.split(".")
        result = data

        for key in keys:
            if isinstance(result, dict):
                result = result.get(key)
            elif isinstance(result, list):
                try:
                    result = result[int(key)]
                except (ValueError, IndexError):
                    return None
            else:
                return None

        return result


class ApiIntegratorToolkit(Toolkit):
    """
    Production-ready API Integrator Toolkit with comprehensive features:

    - Multiple authentication methods (Bearer, API Key, OAuth, Basic Auth)
    - Automatic retry with exponential backoff
    - Rate limiting with token bucket algorithm
    - Connection pooling for performance
    - Response parsing and transformation
    - GraphQL and SOAP support
    - Comprehensive error handling and logging
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        # Authentication
        auth_type: Literal["bearer", "api_key", "basic", "oauth2", "custom"] = "bearer",
        api_key: Optional[str] = None,
        bearer_token: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        oauth2_token: Optional[str] = None,
        custom_auth_header: Optional[Dict[str, str]] = None,
        # Request configuration
        default_headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
        verify_ssl: bool = True,
        # Retry configuration
        max_retries: int = 3,
        retry_backoff_factor: float = 2.0,
        retry_on_status: Optional[List[int]] = None,
        # Rate limiting
        enable_rate_limiting: bool = False,
        requests_per_second: float = 10.0,
        burst_size: int = 20,
        # Connection pooling
        pool_connections: int = 10,
        pool_maxsize: int = 20,
        # Response transformation
        default_transform: Optional[ResponseTransform] = None,
    ):
        super().__init__(name="api_integrator")

        # Base configuration
        self.base_url = base_url.rstrip("/") if base_url else None
        self.timeout = timeout
        self.verify_ssl = verify_ssl

        # Authentication
        self.auth_type = auth_type
        self.api_key = api_key
        self.bearer_token = bearer_token
        self.username = username
        self.password = password
        self.oauth2_token = oauth2_token
        self.custom_auth_header = custom_auth_header or {}

        # Headers
        self.default_headers = default_headers or {}

        # Retry configuration
        self.max_retries = max_retries
        self.retry_backoff_factor = retry_backoff_factor
        self.retry_on_status = retry_on_status or [429, 500, 502, 503, 504]

        # Rate limiting
        self.rate_limiter = None
        if enable_rate_limiting:
            self.rate_limiter = RateLimiter(
                requests_per_second=requests_per_second,
                burst_size=burst_size
            )

        # Response transformation
        self.default_transform = default_transform or ResponseTransform()

        # Setup session with connection pooling
        self.session = self._create_session(pool_connections, pool_maxsize)

        # Register toolkit functions
        self.register(self.rest_request)
        self.register(self.graphql_query)
        self.register(self.soap_request)
        self.register(self.batch_requests)
        self.register(self.test_connection)

    def _create_session(self, pool_connections: int, pool_maxsize: int) -> requests.Session:
        """Create a session with connection pooling and retry logic."""
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = UrllibRetry(
            total=0,  # We'll handle retries manually for better control
            backoff_factor=self.retry_backoff_factor,
            status_forcelist=self.retry_on_status,
            allowed_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
        )

        # Configure HTTP adapter with connection pooling
        adapter = HTTPAdapter(
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize,
            max_retries=retry_strategy
        )

        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers based on auth type."""
        headers = self.default_headers.copy()

        if self.auth_type == "bearer" and self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        elif self.auth_type == "api_key" and self.api_key:
            headers["X-API-Key"] = self.api_key
        elif self.auth_type == "oauth2" and self.oauth2_token:
            headers["Authorization"] = f"Bearer {self.oauth2_token}"
        elif self.auth_type == "custom":
            headers.update(self.custom_auth_header)

        return headers

    def _get_auth(self) -> Optional[HTTPBasicAuth]:
        """Get authentication object for basic auth."""
        if self.auth_type == "basic" and self.username and self.password:
            return HTTPBasicAuth(self.username, self.password)
        return None

    def _build_url(self, endpoint: str) -> str:
        """Build full URL from base_url and endpoint."""
        if endpoint.startswith(("http://", "https://")):
            return endpoint

        if self.base_url:
            return urljoin(self.base_url + "/", endpoint.lstrip("/"))

        return endpoint

    def _execute_request(
        self,
        config: RequestConfig,
        transform: Optional[ResponseTransform] = None
    ) -> Dict[str, Any]:
        """
        Execute HTTP request with retry logic and rate limiting.

        Args:
            config: Request configuration
            transform: Response transformation configuration

        Returns:
            Dictionary containing response data
        """
        url = self._build_url(config.endpoint)
        headers = {**self._get_auth_headers(), **(config.headers or {})}
        timeout = config.timeout or self.timeout
        transform = transform or self.default_transform

        logger.info(f"API Request: {config.method} {url}")
        logger.debug(f"Request config: {config.to_dict()}")

        # Apply rate limiting
        if self.rate_limiter:
            self.rate_limiter.acquire()

        # Retry logic with exponential backoff
        last_exception = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.request(
                    method=config.method,
                    url=url,
                    params=config.params,
                    data=config.data,
                    json=config.json_data,
                    headers=headers,
                    auth=self._get_auth(),
                    timeout=timeout,
                    verify=self.verify_ssl
                )

                # Check if retry is needed based on status code
                if response.status_code in self.retry_on_status and attempt < self.max_retries:
                    wait_time = self.retry_backoff_factor ** attempt
                    logger.warning(
                        f"Request failed with status {response.status_code}. "
                        f"Retrying in {wait_time}s (attempt {attempt + 1}/{self.max_retries})"
                    )
                    time.sleep(wait_time)
                    continue

                # Transform and return response
                result = transform.apply(response)

                if not response.ok:
                    logger.error(f"Request failed: {response.status_code} - {response.text[:200]}")
                    result["error"] = f"HTTP {response.status_code}"
                    result["success"] = False
                else:
                    result["success"] = True

                logger.info(f"API Response: {response.status_code}")
                return result

            except requests.exceptions.Timeout as e:
                last_exception = e
                if attempt < self.max_retries:
                    wait_time = self.retry_backoff_factor ** attempt
                    logger.warning(f"Request timeout. Retrying in {wait_time}s (attempt {attempt + 1}/{self.max_retries})")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Request timeout after {self.max_retries} retries")

            except requests.exceptions.ConnectionError as e:
                last_exception = e
                if attempt < self.max_retries:
                    wait_time = self.retry_backoff_factor ** attempt
                    logger.warning(f"Connection error. Retrying in {wait_time}s (attempt {attempt + 1}/{self.max_retries})")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Connection error after {self.max_retries} retries")

            except requests.exceptions.RequestException as e:
                last_exception = e
                logger.error(f"Request exception: {str(e)}")
                break

            except Exception as e:
                last_exception = e
                logger.error(f"Unexpected error: {str(e)}")
                break

        # If we get here, all retries failed
        error_message = f"Request failed after {self.max_retries} retries: {str(last_exception)}"
        logger.error(error_message)
        return {
            "error": error_message,
            "success": False,
            "exception": str(last_exception)
        }

    def rest_request(
        self,
        endpoint: str,
        method: Literal["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"] = "GET",
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        extract_path: Optional[str] = None,
        include_metadata: bool = True,
    ) -> str:
        """
        Make a REST API request with retry logic and rate limiting.

        Args:
            endpoint: API endpoint (relative to base_url or absolute URL)
            method: HTTP method (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS)
            params: Query parameters
            headers: Additional headers
            data: Form data to send
            json_data: JSON data to send
            timeout: Request timeout in seconds
            extract_path: JSON path to extract from response (e.g., "data.items")
            include_metadata: Include status code and headers in response

        Returns:
            JSON string containing response data

        Example:
            >>> rest_request(
            ...     endpoint="/users",
            ...     method="GET",
            ...     params={"limit": 10},
            ...     extract_path="data"
            ... )
        """
        config = RequestConfig(
            method=method,
            endpoint=endpoint,
            params=params,
            headers=headers,
            data=data,
            json_data=json_data,
            timeout=timeout
        )

        transform = ResponseTransform(
            extract_path=extract_path,
            include_metadata=include_metadata
        )

        result = self._execute_request(config, transform)
        return json.dumps(result, indent=2, default=str)

    def graphql_query(
        self,
        query: str,
        variables: Optional[Dict[str, Any]] = None,
        operation_name: Optional[str] = None,
        endpoint: str = "/graphql",
        extract_path: Optional[str] = None,
    ) -> str:
        """
        Execute a GraphQL query.

        Args:
            query: GraphQL query string
            variables: Query variables
            operation_name: Operation name for the query
            endpoint: GraphQL endpoint (default: /graphql)
            extract_path: JSON path to extract from response (e.g., "data.user")

        Returns:
            JSON string containing response data

        Example:
            >>> graphql_query(
            ...     query=\"""
            ...     query GetUser($id: ID!) {
            ...         user(id: $id) {
            ...             name
            ...             email
            ...         }
            ...     }
            ...     \""",
            ...     variables={"id": "123"},
            ...     extract_path="data.user"
            ... )
        """
        payload = {"query": query}

        if variables:
            payload["variables"] = variables

        if operation_name:
            payload["operationName"] = operation_name

        config = RequestConfig(
            method="POST",
            endpoint=endpoint,
            json_data=payload,
            headers={"Content-Type": "application/json"}
        )

        transform = ResponseTransform(
            extract_path=extract_path,
            include_metadata=True
        )

        result = self._execute_request(config, transform)

        # Check for GraphQL errors
        if isinstance(result.get("data"), dict) and "errors" in result["data"]:
            result["graphql_errors"] = result["data"]["errors"]
            logger.error(f"GraphQL errors: {result['graphql_errors']}")

        return json.dumps(result, indent=2, default=str)

    def soap_request(
        self,
        soap_action: str,
        soap_body: str,
        endpoint: str,
        soap_version: Literal["1.1", "1.2"] = "1.1",
        namespace: Optional[str] = None,
    ) -> str:
        """
        Execute a SOAP request.

        Args:
            soap_action: SOAP action to perform
            soap_body: SOAP body XML content
            endpoint: SOAP endpoint
            soap_version: SOAP version (1.1 or 1.2)
            namespace: XML namespace

        Returns:
            JSON string containing parsed response

        Example:
            >>> soap_request(
            ...     soap_action="GetUser",
            ...     soap_body='<GetUser><userId>123</userId></GetUser>',
            ...     endpoint="/soap",
            ...     namespace="http://example.com/users"
            ... )
        """
        # Build SOAP envelope
        if soap_version == "1.1":
            envelope = f"""<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
               {f'xmlns:ns="{namespace}"' if namespace else ''}>
    <soap:Header/>
    <soap:Body>
        {soap_body}
    </soap:Body>
</soap:Envelope>"""
            content_type = f"text/xml; charset=utf-8"
            soap_action_header = f'"{soap_action}"'
        else:  # SOAP 1.2
            envelope = f"""<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope"
               {f'xmlns:ns="{namespace}"' if namespace else ''}>
    <soap:Header/>
    <soap:Body>
        {soap_body}
    </soap:Body>
</soap:Envelope>"""
            content_type = f"application/soap+xml; charset=utf-8; action={soap_action}"
            soap_action_header = None

        headers = {"Content-Type": content_type}
        if soap_action_header:
            headers["SOAPAction"] = soap_action_header

        config = RequestConfig(
            method="POST",
            endpoint=endpoint,
            data=envelope,
            headers=headers
        )

        result = self._execute_request(config, ResponseTransform())
        return json.dumps(result, indent=2, default=str)

    def batch_requests(
        self,
        requests_config: str,
        parallel: bool = False,
        stop_on_error: bool = False,
    ) -> str:
        """
        Execute multiple API requests in batch.

        Args:
            requests_config: JSON string containing list of request configurations
            parallel: Execute requests in parallel (not implemented, reserved for future)
            stop_on_error: Stop execution if any request fails

        Returns:
            JSON string containing array of responses

        Example:
            >>> batch_requests(
            ...     requests_config='''[
            ...         {"endpoint": "/users/1", "method": "GET"},
            ...         {"endpoint": "/users/2", "method": "GET"}
            ...     ]'''
            ... )
        """
        try:
            configs = json.loads(requests_config)
            if not isinstance(configs, list):
                return json.dumps({"error": "requests_config must be a JSON array"})

            results = []

            for i, cfg in enumerate(configs):
                logger.info(f"Executing batch request {i + 1}/{len(configs)}")

                config = RequestConfig(
                    method=cfg.get("method", "GET"),
                    endpoint=cfg.get("endpoint", ""),
                    params=cfg.get("params"),
                    headers=cfg.get("headers"),
                    data=cfg.get("data"),
                    json_data=cfg.get("json_data"),
                    timeout=cfg.get("timeout")
                )

                result = self._execute_request(config)
                results.append(result)

                if stop_on_error and not result.get("success", False):
                    logger.warning(f"Stopping batch execution due to error at request {i + 1}")
                    break

            return json.dumps({
                "total": len(configs),
                "completed": len(results),
                "results": results
            }, indent=2, default=str)

        except json.JSONDecodeError as e:
            return json.dumps({"error": f"Invalid JSON in requests_config: {str(e)}"})
        except Exception as e:
            return json.dumps({"error": f"Batch execution failed: {str(e)}"})

    def test_connection(
        self,
        endpoint: Optional[str] = None,
        timeout: int = 5,
    ) -> str:
        """
        Test API connection and authentication.

        Args:
            endpoint: Endpoint to test (default: base_url or "/")
            timeout: Connection timeout in seconds

        Returns:
            JSON string with connection status

        Example:
            >>> test_connection(endpoint="/health")
        """
        test_endpoint = endpoint or "/"

        try:
            start_time = time.time()

            config = RequestConfig(
                method="GET",
                endpoint=test_endpoint,
                timeout=timeout
            )

            result = self._execute_request(config)

            elapsed = time.time() - start_time

            return json.dumps({
                "connected": result.get("success", False),
                "status_code": result.get("status_code"),
                "response_time_ms": round(elapsed * 1000, 2),
                "endpoint": self._build_url(test_endpoint),
                "auth_type": self.auth_type,
                "ssl_verified": self.verify_ssl,
            }, indent=2)

        except Exception as e:
            return json.dumps({
                "connected": False,
                "error": str(e)
            }, indent=2)

    def __del__(self):
        """Clean up session on deletion."""
        if hasattr(self, 'session'):
            self.session.close()
