"""Service Mesh Manager Finite State Automaton"""
from enum import Enum
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass

class MeshState(Enum):
    """Service mesh states"""
    IDLE = "idle"
    DISCOVERING = "discovering"
    CONFIGURING = "configuring"
    MONITORING = "monitoring"
    SCALING = "scaling"
    ERROR = "error"
    SHUTDOWN = "shutdown"
@dataclass
class Transition:
    """State transition definition"""
    from_state: MeshState
    to_state: MeshState
    event: str
    guard: Optional[Callable[[Dict[str, Any]], bool]] = None

class ServiceMeshFSA:
    """Finite State Automaton for managing service mesh lifecycle"""
    def __init__(self, initial_state: MeshState = MeshState.IDLE):
        self.current_state: MeshState = initial_state
        self.context: Dict[str, Any] = {"services": [], "metrics": {}, "errors": []}
        self.transitions: List[Transition] = self._define_transitions()
        self.state_handlers: Dict[MeshState, Callable] = self._define_handlers()
    def _define_transitions(self) -> List[Transition]:
        """Define valid state transitions"""
        return [
            Transition(MeshState.IDLE, MeshState.DISCOVERING, "start"),
            Transition(MeshState.DISCOVERING, MeshState.CONFIGURING, "services_found"),
            Transition(MeshState.CONFIGURING, MeshState.MONITORING, "config_applied"),
            Transition(MeshState.MONITORING, MeshState.SCALING, "scale_needed"),
            Transition(MeshState.MONITORING, MeshState.CONFIGURING, "reconfigure"),
            Transition(MeshState.SCALING, MeshState.MONITORING, "scaled"),
            Transition(MeshState.MONITORING, MeshState.SHUTDOWN, "stop"),
            Transition(MeshState.DISCOVERING, MeshState.ERROR, "discovery_failed"),
            Transition(MeshState.CONFIGURING, MeshState.ERROR, "config_failed"),
            Transition(MeshState.ERROR, MeshState.DISCOVERING, "retry"),
            Transition(MeshState.ERROR, MeshState.SHUTDOWN, "abort")]
    def _define_handlers(self) -> Dict[MeshState, Callable]:
        """Define state entry handlers"""
        return {
            MeshState.IDLE: self._handle_idle,
            MeshState.DISCOVERING: self._handle_discovering,
            MeshState.CONFIGURING: self._handle_configuring,
            MeshState.MONITORING: self._handle_monitoring,
            MeshState.SCALING: self._handle_scaling,
            MeshState.ERROR: self._handle_error,
            MeshState.SHUTDOWN: self._handle_shutdown}
    def trigger(self, event: str, data: Optional[Dict[str, Any]] = None) -> bool:
        """Trigger state transition based on event"""
        for transition in self.transitions:
            if transition.from_state == self.current_state and transition.event == event:
                if transition.guard is None or transition.guard(self.context):
                    self._transition_to(transition.to_state, data or {})
                    return True
        return False
    def _transition_to(self, new_state: MeshState, data: Dict[str, Any]):
        """Execute state transition"""
        self.current_state = new_state
        self.context.update(data)
        handler = self.state_handlers.get(new_state)
        if handler:
            handler()

    def _handle_idle(self): self.context["status"] = "waiting"
    def _handle_discovering(self): self.context["status"] = "discovering services"
    def _handle_configuring(self): self.context["status"] = "applying configuration"
    def _handle_monitoring(self): self.context["status"] = "monitoring mesh health"
    def _handle_scaling(self): self.context["status"] = "scaling services"
    def _handle_error(self): self.context["status"] = f"error: {self.context.get('error')}"
    def _handle_shutdown(self): self.context["status"] = "shutting down"

    def get_state(self) -> str:
        """Get current state and status"""
        return f"{self.current_state.value}: {self.context.get('status', 'unknown')}"
