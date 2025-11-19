from typing import List, Optional, Union

from agno.models.message import Message


class AgentRunException(Exception):
    def __init__(
        self,
        exc,
        user_message: Optional[Union[str, Message]] = None,
        agent_message: Optional[Union[str, Message]] = None,
        messages: Optional[List[Union[dict, Message]]] = None,
        stop_execution: bool = False,
    ):
        super().__init__(exc)
        self.user_message = user_message
        self.agent_message = agent_message
        self.messages = messages
        self.stop_execution = stop_execution


class RetryAgentRun(AgentRunException):
    """Exception raised when a tool call should be retried."""


class StopAgentRun(AgentRunException):
    """Exception raised when an agent should stop executing entirely."""

    def __init__(
        self,
        exc,
        user_message: Optional[Union[str, Message]] = None,
        agent_message: Optional[Union[str, Message]] = None,
        messages: Optional[List[Union[dict, Message]]] = None,
    ):
        super().__init__(
            exc, user_message=user_message, agent_message=agent_message, messages=messages, stop_execution=True
        )


class AgnoError(Exception):
    """Exception raised when an internal error occurs."""

    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

    def __str__(self) -> str:
        return str(self.message)


class ModelProviderError(AgnoError):
    """Exception raised when a model provider returns an error."""

    def __init__(
        self, message: str, status_code: int = 502, model_name: Optional[str] = None, model_id: Optional[str] = None
    ):
        super().__init__(message, status_code)
        self.model_name = model_name
        self.model_id = model_id


class ModelRateLimitError(ModelProviderError):
    """Exception raised when a model provider returns a rate limit error."""

    def __init__(
        self, message: str, status_code: int = 429, model_name: Optional[str] = None, model_id: Optional[str] = None
    ):
        super().__init__(message, status_code, model_name, model_id)


class CircuitBreakerError(AgnoError):
    """Base exception for circuit breaker errors."""

    def __init__(self, message: str, circuit_name: str, status_code: int = 503):
        super().__init__(message, status_code)
        self.circuit_name = circuit_name


class CircuitBreakerOpenError(CircuitBreakerError):
    """Exception raised when circuit breaker is open and rejects requests."""

    def __init__(self, message: str, circuit_name: str, failure_rate: float = 0.0, retry_after: Optional[str] = None):
        super().__init__(message, circuit_name, status_code=503)
        self.failure_rate = failure_rate
        self.retry_after = retry_after


class BulkheadFullError(AgnoError):
    """Exception raised when bulkhead is full and cannot accept more requests."""

    def __init__(self, message: str, bulkhead_name: str, max_concurrent: int = 0):
        super().__init__(message, status_code=503)
        self.bulkhead_name = bulkhead_name
        self.max_concurrent = max_concurrent
