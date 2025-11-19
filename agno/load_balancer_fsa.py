"""Load Balancer Finite State Automaton for request distribution."""

import logging
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class State(Enum):
    """FSA states for load balancer."""
    IDLE = "idle"
    ROUTING = "routing"
    BALANCING = "balancing"
    COMPLETED = "completed"


class Strategy(Enum):
    """Load balancing strategies."""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"


@dataclass
class Backend:
    """Represents a backend server."""
    name: str
    address: str
    healthy: bool = True
    active_connections: int = 0
    total_requests: int = 0


class LoadBalancerFSA:
    """Finite State Automaton for load balancing."""

    def __init__(self, strategy: Strategy = Strategy.ROUND_ROBIN):
        self.state = State.IDLE
        self.strategy = strategy
        self._backends: Dict[str, Backend] = {}
        self._round_robin_index = 0
        self._lock = threading.Lock()
        self._health_check_fn: Optional[Callable[[Backend], bool]] = None
        logger.info(f"Load balancer initialized (strategy: {strategy.value})")

    def add_backend(self, name: str, address: str):
        """Add a backend server."""
        with self._lock:
            if name in self._backends:
                raise ValueError(f"Backend {name} already exists")

            backend = Backend(name=name, address=address)
            self._backends[name] = backend
            logger.info(f"Added backend {name} ({address})")

    def remove_backend(self, name: str):
        """Remove a backend server."""
        with self._lock:
            if name not in self._backends:
                return False

            del self._backends[name]
            logger.info(f"Removed backend {name}")
            return True

    def set_health_check(self, health_check_fn: Callable[[Backend], bool]):
        """Set health check function."""
        self._health_check_fn = health_check_fn
        logger.debug("Health check function registered")

    def mark_healthy(self, name: str):
        """Mark backend as healthy."""
        with self._lock:
            if name in self._backends:
                self._backends[name].healthy = True
                logger.info(f"Backend {name} marked healthy")

    def mark_unhealthy(self, name: str):
        """Mark backend as unhealthy."""
        with self._lock:
            if name in self._backends:
                self._backends[name].healthy = False
                logger.warning(f"Backend {name} marked unhealthy")

    def get_backend(self) -> Optional[Backend]:
        """Get next backend based on strategy."""
        with self._lock:
            if not self._backends:
                logger.error("No backends available")
                return None

            self._transition(State.IDLE, State.ROUTING)

            # Run health checks
            if self._health_check_fn:
                self._run_health_checks()

            # Get healthy backends
            healthy_backends = [b for b in self._backends.values() if b.healthy]

            if not healthy_backends:
                logger.error("No healthy backends available")
                self._transition(State.ROUTING, State.IDLE)
                return None

            self._transition(State.ROUTING, State.BALANCING)

            # Select backend based on strategy
            if self.strategy == Strategy.ROUND_ROBIN:
                backend = self._round_robin_select(healthy_backends)
            else:  # LEAST_CONNECTIONS
                backend = self._least_connections_select(healthy_backends)

            if backend:
                backend.active_connections += 1
                backend.total_requests += 1
                logger.debug(f"Routed to {backend.name} ({backend.active_connections} active)")

            self._transition(State.BALANCING, State.COMPLETED)
            self._transition(State.COMPLETED, State.IDLE)

            return backend

    def release_backend(self, backend: Backend):
        """Release backend after request completion."""
        with self._lock:
            if backend.name in self._backends:
                backend.active_connections = max(0, backend.active_connections - 1)
                logger.debug(f"Released {backend.name} ({backend.active_connections} active)")

    def get_stats(self) -> Dict:
        """Get load balancer statistics."""
        with self._lock:
            total_backends = len(self._backends)
            healthy_backends = sum(1 for b in self._backends.values() if b.healthy)
            total_connections = sum(b.active_connections for b in self._backends.values())

            backends_info = {
                name: {
                    "address": b.address,
                    "healthy": b.healthy,
                    "active_connections": b.active_connections,
                    "total_requests": b.total_requests
                }
                for name, b in self._backends.items()
            }

            return {
                "strategy": self.strategy.value,
                "state": self.state.value,
                "total_backends": total_backends,
                "healthy_backends": healthy_backends,
                "total_connections": total_connections,
                "backends": backends_info
            }

    def _round_robin_select(self, backends: List[Backend]) -> Optional[Backend]:
        """Select backend using round-robin strategy."""
        if not backends:
            return None

        selected = backends[self._round_robin_index % len(backends)]
        self._round_robin_index = (self._round_robin_index + 1) % len(backends)
        return selected

    def _least_connections_select(self, backends: List[Backend]) -> Optional[Backend]:
        """Select backend with least active connections."""
        if not backends:
            return None

        return min(backends, key=lambda b: b.active_connections)

    def _run_health_checks(self):
        """Run health checks on all backends."""
        for backend in self._backends.values():
            try:
                is_healthy = self._health_check_fn(backend)
                backend.healthy = is_healthy
                if not is_healthy:
                    logger.warning(f"Health check failed for {backend.name}")
            except Exception as e:
                logger.error(f"Health check error for {backend.name}: {e}")
                backend.healthy = False

    def _transition(self, from_state: State, to_state: State):
        """Transition between states."""
        logger.debug(f"State transition: {from_state.value} -> {to_state.value}")
        self.state = to_state
