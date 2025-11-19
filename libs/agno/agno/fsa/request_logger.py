"""Request Logger FSA - HTTP request/response logging with state transitions
IDLE → REQUEST_SENT → RESPONSE_RECEIVED → COMPLETED | ERROR"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
import time


class RequestState(str, Enum):
    """FSA States for HTTP Request Logging"""
    IDLE = "idle"
    REQUEST_SENT = "request_sent"
    RESPONSE_RECEIVED = "response_received"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class RequestLog:
    """Data model for HTTP request/response log entry"""
    request_id: str
    method: str
    url: str
    state: RequestState = RequestState.IDLE

    # Timestamps
    created_at: float = field(default_factory=time.time)
    request_sent_at: Optional[float] = None
    response_received_at: Optional[float] = None
    completed_at: Optional[float] = None

    # Request/Response data
    request_headers: Optional[Dict[str, str]] = None
    request_body: Optional[Any] = None
    status_code: Optional[int] = None
    response_headers: Optional[Dict[str, str]] = None
    response_body: Optional[Any] = None
    error: Optional[str] = None

    # Metrics
    duration_ms: Optional[float] = None

    def get_duration(self) -> Optional[float]:
        """Calculate request duration in milliseconds"""
        if self.request_sent_at and self.response_received_at:
            return (self.response_received_at - self.request_sent_at) * 1000
        return None


class RequestLoggerFSA:
    """
    Finite State Automation for HTTP Request/Response Logging

    State Transitions:
        IDLE → REQUEST_SENT → RESPONSE_RECEIVED → COMPLETED
             ↘ ERROR
    """

    def __init__(self):
        self.logs: Dict[str, RequestLog] = {}
        self.current_state: RequestState = RequestState.IDLE

    def create_request(self, request_id: str, method: str, url: str,
                      headers: Optional[Dict[str, str]] = None,
                      body: Optional[Any] = None) -> RequestLog:
        """Transition: IDLE → REQUEST_SENT. Creates new request log."""
        log = RequestLog(
            request_id=request_id,
            method=method.upper(),
            url=url,
            request_headers=headers,
            request_body=body,
            state=RequestState.IDLE
        )
        # Transition to REQUEST_SENT
        log.state = RequestState.REQUEST_SENT
        log.request_sent_at = time.time()
        self.logs[request_id] = log
        self.current_state = RequestState.REQUEST_SENT
        return log

    def log_response(self, request_id: str, status_code: int,
                    headers: Optional[Dict[str, str]] = None,
                    body: Optional[Any] = None) -> Optional[RequestLog]:
        """Transition: REQUEST_SENT → RESPONSE_RECEIVED. Logs HTTP response."""
        log = self.logs.get(request_id)
        if not log or log.state != RequestState.REQUEST_SENT:
            return None
        # Transition to RESPONSE_RECEIVED
        log.state = RequestState.RESPONSE_RECEIVED
        log.response_received_at = time.time()
        log.status_code = status_code
        log.response_headers = headers
        log.response_body = body
        log.duration_ms = log.get_duration()
        self.current_state = RequestState.RESPONSE_RECEIVED
        return log

    def complete_request(self, request_id: str) -> Optional[RequestLog]:
        """Transition: RESPONSE_RECEIVED → COMPLETED. Marks request complete."""
        log = self.logs.get(request_id)
        if not log or log.state != RequestState.RESPONSE_RECEIVED:
            return None
        # Transition to COMPLETED
        log.state = RequestState.COMPLETED
        log.completed_at = time.time()
        self.current_state = RequestState.COMPLETED
        return log

    def log_error(self, request_id: str, error: str) -> Optional[RequestLog]:
        """Transition: * → ERROR. Logs error for any request state."""
        log = self.logs.get(request_id)
        if not log:
            return None
        # Transition to ERROR
        log.state = RequestState.ERROR
        log.error = error
        log.completed_at = time.time()
        self.current_state = RequestState.ERROR
        return log

    def get_log(self, request_id: str) -> Optional[RequestLog]:
        """Retrieve a specific request log"""
        return self.logs.get(request_id)

    def get_all_logs(self) -> List[RequestLog]:
        """Retrieve all request logs"""
        return list(self.logs.values())

    def get_logs_by_state(self, state: RequestState) -> List[RequestLog]:
        """Filter logs by state"""
        return [log for log in self.logs.values() if log.state == state]
