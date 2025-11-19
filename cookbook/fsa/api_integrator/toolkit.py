"""
API Integrator Toolkit - Agno Framework integration.

Provides tools for API integration operations that can be used by Agno Agents.
"""

from typing import Any, Dict, List, Optional

from agno.tools import Toolkit
from agno.utils.log import logger

from .manager import APIIntegratorManager
from .models import (
    APIEndpoint,
    APIIntegratorConfig,
    APIRequest,
    APIType,
    AuthConfig,
    AuthType,
    GraphQLRequest,
    HTTPMethod,
    SOAPRequest,
)


class APIIntegratorToolkit(Toolkit):
    """
    Toolkit for API integration operations.

    Provides comprehensive API integration capabilities including:
    - REST/GraphQL/SOAP endpoint management
    - Request execution with authentication
    - Retry logic and rate limiting
    - Caching and circuit breaker patterns
    - Metrics and monitoring
    """

    def __init__(
        self,
        config: Optional[APIIntegratorConfig] = None,
        register_all: bool = True,
        name: str = "api_integrator_toolkit",
    ):
        """
        Initialize API Integrator Toolkit.

        Args:
            config: API integrator configuration
            register_all: Register all tools by default
            name: Toolkit name
        """
        super().__init__(name=name)

        self.config = config or APIIntegratorConfig()
        self.manager = APIIntegratorManager(config=self.config)

        if register_all:
            self.register(self.register_endpoint)
            self.register(self.make_rest_request)
            self.register(self.make_graphql_request)
            self.register(self.make_soap_request)
            self.register(self.list_endpoints)
            self.register(self.get_endpoint_info)
            self.register(self.get_metrics)
            self.register(self.get_cache_metrics)
            self.register(self.get_circuit_breaker_status)
            self.register(self.reset_circuit_breaker)
            self.register(self.invalidate_cache)
            self.register(self.cleanup_cache)

        logger.info(f"APIIntegratorToolkit initialized with {len(self.functions)} tools")

    def register_endpoint(
        self,
        name: str,
        url: str,
        api_type: str = "REST",
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
        description: Optional[str] = None,
    ) -> str:
        """
        Register a new API endpoint.

        Args:
            name: Unique endpoint identifier
            url: Full URL or URL template (use {param} for path parameters)
            api_type: API type (REST, GRAPHQL, SOAP)
            method: HTTP method (GET, POST, PUT, PATCH, DELETE)
            headers: Default headers for this endpoint
            timeout: Request timeout in seconds
            description: Endpoint description

        Returns:
            Success message

        Example:
            register_endpoint(
                name="get_user",
                url="https://api.example.com/users/{user_id}",
                method="GET",
                headers={"Accept": "application/json"}
            )
        """
        try:
            endpoint = APIEndpoint(
                name=name,
                url=url,
                api_type=APIType(api_type.upper()),
                method=HTTPMethod(method.upper()),
                headers=headers or {},
                timeout=timeout,
                description=description,
            )

            self.manager.register_endpoint(endpoint)
            return f"Successfully registered endpoint '{name}' ({api_type} {method} {url})"

        except Exception as e:
            logger.error(f"Failed to register endpoint: {e}")
            return f"Error registering endpoint: {str(e)}"

    def make_rest_request(
        self,
        endpoint_name: str,
        method: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        body: Optional[Any] = None,
        path_params: Optional[Dict[str, str]] = None,
        auth_type: Optional[str] = None,
        auth_token: Optional[str] = None,
        skip_cache: bool = False,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Make a REST API request.

        Args:
            endpoint_name: Name of the registered endpoint
            method: HTTP method override (GET, POST, PUT, PATCH, DELETE)
            headers: Additional headers
            params: Query parameters
            body: Request body (dict for JSON, str for other)
            path_params: URL path parameters (e.g., {"user_id": "123"})
            auth_type: Authentication type (BEARER, API_KEY, BASIC, OAUTH2)
            auth_token: Authentication token
            skip_cache: Skip cache lookup and storage
            timeout: Request timeout override

        Returns:
            API response as dictionary

        Example:
            make_rest_request(
                endpoint_name="get_user",
                path_params={"user_id": "123"},
                auth_type="BEARER",
                auth_token="your_token_here"
            )
        """
        try:
            # Build authentication config
            auth = None
            if auth_type:
                auth = AuthConfig(
                    auth_type=AuthType(auth_type.upper()),
                    token=auth_token,
                )

            # Build request
            request = APIRequest(
                endpoint_name=endpoint_name,
                method=HTTPMethod(method.upper()) if method else None,
                headers=headers or {},
                params=params or {},
                body=body,
                path_params=path_params or {},
                auth=auth,
                timeout=timeout,
            )

            # Execute request
            response = self.manager.make_request(request, skip_cache=skip_cache)

            return response.model_dump()

        except Exception as e:
            logger.error(f"Failed to make REST request: {e}")
            return {
                "success": False,
                "error": str(e),
                "status_code": 0,
                "endpoint_name": endpoint_name,
            }

    def make_graphql_request(
        self,
        endpoint_name: str,
        query: str,
        variables: Optional[Dict[str, Any]] = None,
        operation_name: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Make a GraphQL request.

        Args:
            endpoint_name: Name of the registered GraphQL endpoint
            query: GraphQL query or mutation
            variables: Query variables
            operation_name: Operation name (for multiple operations in one query)
            headers: Additional headers

        Returns:
            API response as dictionary

        Example:
            make_graphql_request(
                endpoint_name="github_api",
                query="query { viewer { login } }",
                headers={"Authorization": "bearer YOUR_TOKEN"}
            )
        """
        try:
            request = GraphQLRequest(
                endpoint_name=endpoint_name,
                query=query,
                variables=variables or {},
                operation_name=operation_name,
                headers=headers or {},
            )

            response = self.manager.make_graphql_request(request)
            return response.model_dump()

        except Exception as e:
            logger.error(f"Failed to make GraphQL request: {e}")
            return {
                "success": False,
                "error": str(e),
                "status_code": 0,
                "endpoint_name": endpoint_name,
            }

    def make_soap_request(
        self,
        endpoint_name: str,
        action: str,
        body: str,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Make a SOAP request.

        Args:
            endpoint_name: Name of the registered SOAP endpoint
            action: SOAP action
            body: SOAP envelope XML
            headers: Additional headers

        Returns:
            API response as dictionary

        Example:
            make_soap_request(
                endpoint_name="weather_service",
                action="GetWeather",
                body='<?xml version="1.0"?>...'
            )
        """
        try:
            request = SOAPRequest(
                endpoint_name=endpoint_name,
                action=action,
                body=body,
                headers=headers or {},
            )

            response = self.manager.make_soap_request(request)
            return response.model_dump()

        except Exception as e:
            logger.error(f"Failed to make SOAP request: {e}")
            return {
                "success": False,
                "error": str(e),
                "status_code": 0,
                "endpoint_name": endpoint_name,
            }

    def list_endpoints(self) -> List[str]:
        """
        List all registered endpoints.

        Returns:
            List of endpoint names

        Example:
            endpoints = list_endpoints()
            # Returns: ["get_user", "create_post", "github_api"]
        """
        return self.manager.list_endpoints()

    def get_endpoint_info(self, endpoint_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about an endpoint.

        Args:
            endpoint_name: Name of the endpoint

        Returns:
            Endpoint configuration as dictionary or None if not found

        Example:
            info = get_endpoint_info("get_user")
        """
        endpoint = self.manager.get_endpoint(endpoint_name)
        return endpoint.model_dump() if endpoint else None

    def get_metrics(self, endpoint_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get API call metrics.

        Args:
            endpoint_name: Specific endpoint name, or None for all endpoints

        Returns:
            Metrics dictionary with request counts, durations, etc.

        Example:
            # Get all metrics
            all_metrics = get_metrics()

            # Get metrics for specific endpoint
            user_metrics = get_metrics("get_user")
        """
        return self.manager.get_metrics(endpoint_name)

    def get_cache_metrics(self) -> Dict[str, Any]:
        """
        Get cache performance metrics.

        Returns:
            Cache metrics including hit rate, size, evictions

        Example:
            cache_stats = get_cache_metrics()
            # Returns: {"hits": 100, "misses": 20, "hit_rate_percent": 83.3, ...}
        """
        return self.manager.get_cache_metrics()

    def get_circuit_breaker_status(self, endpoint_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get circuit breaker status.

        Args:
            endpoint_name: Specific endpoint name, or None for all endpoints

        Returns:
            Circuit breaker status (CLOSED, OPEN, HALF_OPEN) and metrics

        Example:
            status = get_circuit_breaker_status("get_user")
            # Returns: {"state": "CLOSED", "failure_count": 0, ...}
        """
        return self.manager.get_circuit_breaker_status(endpoint_name)

    def reset_circuit_breaker(self, endpoint_name: str) -> str:
        """
        Manually reset a circuit breaker to CLOSED state.

        Args:
            endpoint_name: Name of the endpoint

        Returns:
            Success message

        Example:
            result = reset_circuit_breaker("get_user")
        """
        try:
            self.manager.reset_circuit_breaker(endpoint_name)
            return f"Circuit breaker for '{endpoint_name}' has been reset to CLOSED state"
        except Exception as e:
            return f"Error resetting circuit breaker: {str(e)}"

    def invalidate_cache(self, endpoint_name: Optional[str] = None) -> str:
        """
        Invalidate cache entries.

        Args:
            endpoint_name: Specific endpoint name, or None to clear all cache

        Returns:
            Success message with count of invalidated entries

        Example:
            # Clear cache for specific endpoint
            result = invalidate_cache("get_user")

            # Clear all cache
            result = invalidate_cache()
        """
        try:
            count = self.manager.invalidate_cache(endpoint_name)
            if endpoint_name:
                return f"Invalidated cache for '{endpoint_name}' ({count} entries removed)"
            else:
                return f"Cleared entire cache ({count} entries removed)"
        except Exception as e:
            return f"Error invalidating cache: {str(e)}"

    def cleanup_cache(self) -> str:
        """
        Clean up expired cache entries.

        Returns:
            Success message with count of cleaned entries

        Example:
            result = cleanup_cache()
            # Returns: "Cleaned up 15 expired cache entries"
        """
        try:
            count = self.manager.cleanup_expired_cache()
            return f"Cleaned up {count} expired cache entries"
        except Exception as e:
            return f"Error cleaning cache: {str(e)}"
