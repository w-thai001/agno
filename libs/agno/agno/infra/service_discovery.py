"""Service Discovery Finite State Automaton for managing service lifecycle."""
from enum import Enum
from typing import Dict, Optional, Set, Callable, Any
from datetime import datetime
from pydantic import BaseModel, Field


class ServiceState(str, Enum):
    """Service lifecycle states."""
    PENDING = "pending"
    REGISTERING = "registering"
    AVAILABLE = "available"
    UNHEALTHY = "unhealthy"
    DRAINING = "draining"
    DEREGISTERING = "deregistering"
    TERMINATED = "terminated"


class ServiceMetadata(BaseModel):
    """Service metadata for discovery."""
    service_id: str
    name: str
    endpoint: str
    port: int
    health_check_path: str = "/health"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    last_heartbeat: Optional[datetime] = None


class ServiceDiscoveryFSA:
    """Finite State Automaton for service discovery lifecycle management."""

    # Define valid state transitions

    TRANSITIONS: Dict[ServiceState, Set[ServiceState]] = {
        ServiceState.PENDING: {ServiceState.REGISTERING, ServiceState.TERMINATED},
        ServiceState.REGISTERING: {ServiceState.AVAILABLE, ServiceState.UNHEALTHY, ServiceState.TERMINATED},
        ServiceState.AVAILABLE: {ServiceState.UNHEALTHY, ServiceState.DRAINING, ServiceState.DEREGISTERING},
        ServiceState.UNHEALTHY: {ServiceState.AVAILABLE, ServiceState.DRAINING, ServiceState.DEREGISTERING},
        ServiceState.DRAINING: {ServiceState.DEREGISTERING, ServiceState.AVAILABLE},
        ServiceState.DEREGISTERING: {ServiceState.TERMINATED},
        ServiceState.TERMINATED: set()  # Terminal state
    }

    def __init__(self, service: ServiceMetadata, initial_state: ServiceState = ServiceState.PENDING):
        """Initialize FSA with service metadata."""
        self.service, self.state = service, initial_state
        self.state_history: list[tuple[ServiceState, datetime]] = [(initial_state, datetime.now())]
        self.handlers: Dict[ServiceState, Optional[Callable]] = {}

    def transition(self, target_state: ServiceState) -> bool:
        """Attempt state transition, returns success status."""
        if target_state not in self.TRANSITIONS.get(self.state, set()):
            return False

        self.state = target_state
        self.state_history.append((target_state, datetime.now()))
        if handler := self.handlers.get(target_state):
            handler(self.service)
        return True

    def register_handler(self, state: ServiceState, handler: Callable) -> None:
        """Register callback for state entry."""
        self.handlers[state] = handler

    def can_transition_to(self, target_state: ServiceState) -> bool:
        """Check if transition to target state is valid."""
        return target_state in self.TRANSITIONS.get(self.state, set())

    def get_allowed_transitions(self) -> Set[ServiceState]:
        """Get all valid transitions from current state."""
        return self.TRANSITIONS.get(self.state, set())

    def is_operational(self) -> bool:
        """Check if service is in operational state."""
        return self.state in {ServiceState.AVAILABLE, ServiceState.DRAINING}

    def is_terminal(self) -> bool:
        """Check if service has reached terminal state."""
        return self.state == ServiceState.TERMINATED
