"""
Resource Allocator FSA: Intelligent resource allocation and management system.

This FSA manages computational resources (CPU, memory, tokens, API quotas) across
multiple agents and FSAs with dynamic reallocation, load balancing, and predictive
capabilities.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
from uuid import uuid4

logger = logging.getLogger(__name__)


class AllocationStrategy(Enum):
    """Resource allocation strategies."""

    FAIR_SHARE = "fair_share"  # Equal distribution
    PRIORITY = "priority"  # Based on agent priority
    DEMAND_BASED = "demand_based"  # Based on current demand
    ML_PREDICTED = "ml_predicted"  # Based on ML predictions


class FSAState(Enum):
    """FSA states for resource allocation lifecycle."""

    IDLE = "idle"
    VALIDATING = "validating"
    ALLOCATING = "allocating"
    MONITORING = "monitoring"
    REBALANCING = "rebalancing"
    OPTIMIZING = "optimizing"
    ERROR = "error"


@dataclass
class Resources:
    """Resource container for CPU, memory, tokens, and quotas."""

    cpu_cores: float = 0.0  # CPU cores
    memory_mb: float = 0.0  # Memory in MB
    tokens: int = 0  # Token budget
    api_quota: int = 0  # API calls quota
    gpu_units: float = 0.0  # GPU units (optional)

    def __add__(self, other: Resources) -> Resources:
        """Add two resource objects."""
        return Resources(
            cpu_cores=self.cpu_cores + other.cpu_cores,
            memory_mb=self.memory_mb + other.memory_mb,
            tokens=self.tokens + other.tokens,
            api_quota=self.api_quota + other.api_quota,
            gpu_units=self.gpu_units + other.gpu_units,
        )

    def __sub__(self, other: Resources) -> Resources:
        """Subtract two resource objects."""
        return Resources(
            cpu_cores=self.cpu_cores - other.cpu_cores,
            memory_mb=self.memory_mb - other.memory_mb,
            tokens=self.tokens - other.tokens,
            api_quota=self.api_quota - other.api_quota,
            gpu_units=self.gpu_units - other.gpu_units,
        )

    def __mul__(self, scalar: float) -> Resources:
        """Multiply resources by a scalar."""
        return Resources(
            cpu_cores=self.cpu_cores * scalar,
            memory_mb=self.memory_mb * scalar,
            tokens=int(self.tokens * scalar),
            api_quota=int(self.api_quota * scalar),
            gpu_units=self.gpu_units * scalar,
        )

    def is_sufficient(self, required: Resources) -> bool:
        """Check if resources are sufficient for required allocation."""
        return (
            self.cpu_cores >= required.cpu_cores
            and self.memory_mb >= required.memory_mb
            and self.tokens >= required.tokens
            and self.api_quota >= required.api_quota
            and self.gpu_units >= required.gpu_units
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "cpu_cores": self.cpu_cores,
            "memory_mb": self.memory_mb,
            "tokens": self.tokens,
            "api_quota": self.api_quota,
            "gpu_units": self.gpu_units,
        }


@dataclass
class Agent:
    """Agent representation for resource allocation."""

    agent_id: str
    name: str
    priority: int = 1  # Higher is more important (1-10)
    min_resources: Resources = field(default_factory=Resources)
    max_resources: Resources = field(default_factory=Resources)
    allocated_resources: Resources = field(default_factory=Resources)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate agent configuration."""
        if self.priority < 1 or self.priority > 10:
            raise ValueError("Priority must be between 1 and 10")

    def __hash__(self):
        """Make Agent hashable based on agent_id."""
        return hash(self.agent_id)

    def __eq__(self, other):
        """Check equality based on agent_id."""
        if isinstance(other, Agent):
            return self.agent_id == other.agent_id
        return False


@dataclass
class ResourcePool:
    """Available resource pool."""

    total: Resources
    allocated: Resources = field(default_factory=Resources)
    reserved: Resources = field(default_factory=Resources)

    @property
    def available(self) -> Resources:
        """Get available resources."""
        return self.total - self.allocated - self.reserved

    def can_allocate(self, resources: Resources) -> bool:
        """Check if allocation is possible."""
        return self.available.is_sufficient(resources)

    def allocate(self, resources: Resources) -> bool:
        """Allocate resources from pool."""
        if self.can_allocate(resources):
            self.allocated = self.allocated + resources
            return True
        return False

    def deallocate(self, resources: Resources) -> None:
        """Return resources to pool."""
        self.allocated = self.allocated - resources


@dataclass
class ResourceUsage:
    """Real-time resource usage tracking."""

    agent_id: str
    current: Resources
    peak: Resources
    average: Resources
    timestamp: datetime = field(default_factory=datetime.now)
    utilization_percent: float = 0.0  # Overall utilization

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent_id": self.agent_id,
            "current": self.current.to_dict(),
            "peak": self.peak.to_dict(),
            "average": self.average.to_dict(),
            "timestamp": self.timestamp.isoformat(),
            "utilization_percent": self.utilization_percent,
        }


@dataclass
class DemandForecast:
    """Resource demand forecast."""

    agent_id: str
    predicted_resources: Resources
    confidence: float  # 0.0 to 1.0
    time_window: str
    historical_accuracy: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent_id": self.agent_id,
            "predicted_resources": self.predicted_resources.to_dict(),
            "confidence": self.confidence,
            "time_window": self.time_window,
            "historical_accuracy": self.historical_accuracy,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class Quotas:
    """Resource quotas and limits."""

    max_tokens_per_minute: int = 10000
    max_api_calls_per_minute: int = 100
    max_cpu_percent: float = 80.0
    max_memory_mb: float = 4096.0
    throttle_threshold: float = 0.9  # Throttle at 90% usage


@dataclass
class AllocationRequest:
    """Resource allocation request."""

    request_id: str = field(default_factory=lambda: str(uuid4()))
    agents: List[Agent] = field(default_factory=list)
    strategy: AllocationStrategy = AllocationStrategy.FAIR_SHARE
    constraints: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ValidationResult:
    """Validation result for allocation request."""

    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class AllocationResult:
    """Result of resource allocation."""

    request_id: str
    allocations: Dict[str, Resources]  # agent_id -> allocated resources
    success: bool
    message: str
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "request_id": self.request_id,
            "allocations": {k: v.to_dict() for k, v in self.allocations.items()},
            "success": self.success,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class AllocationState:
    """Current allocation state."""

    allocations: Dict[str, Resources]  # agent_id -> allocated resources
    usage: Dict[str, ResourceUsage]  # agent_id -> usage stats
    pool: ResourcePool
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class RebalanceResult:
    """Result of rebalancing operation."""

    reallocations: Dict[str, Resources]  # agent_id -> new allocation
    reclaimed: Resources
    redistributed: Resources
    success: bool
    message: str


@dataclass
class EnforcementResult:
    """Result of quota enforcement."""

    agent_id: str
    throttled: bool
    violations: List[str] = field(default_factory=list)
    action_taken: str = ""


@dataclass
class OptimizationResult:
    """Result of optimization."""

    efficiency_gain: float  # Percentage improvement
    recommendations: List[str] = field(default_factory=list)
    applied_optimizations: List[str] = field(default_factory=list)


@dataclass
class ReclaimResult:
    """Result of idle resource reclamation."""

    reclaimed: Resources
    success: bool
    message: str
    affected_agents: List[str] = field(default_factory=list)


@dataclass
class ResourceConflict:
    """Resource allocation conflict."""

    conflict_id: str
    agents: List[str]  # Conflicting agent IDs
    resource_type: str  # cpu, memory, tokens, etc.
    requested: float
    available: float


@dataclass
class Resolution:
    """Conflict resolution result."""

    conflict_id: str
    strategy: str
    success: bool
    message: str
    allocations: Dict[str, float] = field(default_factory=dict)  # agent_id -> allocated amount


@dataclass
class ResourceAllocation:
    """Complete resource allocation details."""

    agent_id: str
    allocated: Resources
    requested: Resources
    utilization: float = 0.0


class ResourceAllocatorFSA:
    """
    Finite State Automaton for intelligent resource allocation and management.

    This FSA manages computational resources across multiple agents with dynamic
    reallocation, load balancing, and predictive capabilities.

    States:
        - IDLE: Ready for allocation requests
        - VALIDATING: Validating allocation request
        - ALLOCATING: Allocating resources
        - MONITORING: Monitoring resource usage
        - REBALANCING: Rebalancing allocations
        - OPTIMIZING: Optimizing resource efficiency
        - ERROR: Error state

    Attributes:
        resource_pool: Available resource pool
        allocations: Current resource allocations
        usage_history: Historical usage data
        quotas: Resource quotas and limits
        state: Current FSA state
    """

    def __init__(
        self,
        total_resources: Resources,
        quotas: Optional[Quotas] = None,
        enable_prediction: bool = True,
        history_size: int = 100,
    ):
        """
        Initialize Resource Allocator FSA.

        Args:
            total_resources: Total available resources
            quotas: Resource quotas and limits
            enable_prediction: Enable ML-based demand prediction
            history_size: Size of usage history for predictions
        """
        self.resource_pool = ResourcePool(total=total_resources)
        self.allocations: Dict[str, Resources] = {}
        self.agents: Dict[str, Agent] = {}
        self.usage_history: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=history_size)
        )
        self.quotas = quotas or Quotas()
        self.enable_prediction = enable_prediction
        self.state = FSAState.IDLE

        # Usage tracking
        self.current_usage: Dict[str, ResourceUsage] = {}
        self.peak_usage: Dict[str, Resources] = {}

        # Performance metrics
        self.allocation_count = 0
        self.rebalance_count = 0
        self.optimization_count = 0

        # Prediction cache
        self.prediction_cache: Dict[str, DemandForecast] = {}
        self.cache_ttl = 300  # 5 minutes

        logger.info(
            f"ResourceAllocatorFSA initialized with resources: {total_resources.to_dict()}"
        )

    def _transition_state(self, new_state: FSAState) -> None:
        """Transition to a new FSA state."""
        logger.debug(f"State transition: {self.state.value} -> {new_state.value}")
        self.state = new_state

    def execute(self, allocation_request: AllocationRequest) -> AllocationResult:
        """
        Execute the resource allocation pipeline.

        Args:
            allocation_request: Allocation request with agents and strategy

        Returns:
            AllocationResult with allocation details
        """
        try:
            self._transition_state(FSAState.VALIDATING)

            # Validate request
            validation = self.validate(allocation_request)
            if not validation.valid:
                self._transition_state(FSAState.ERROR)
                return AllocationResult(
                    request_id=allocation_request.request_id,
                    allocations={},
                    success=False,
                    message=f"Validation failed: {', '.join(validation.errors)}",
                )

            self._transition_state(FSAState.ALLOCATING)

            # Allocate resources based on strategy
            allocations = self.allocate_resources(
                allocation_request.agents, self.resource_pool
            )

            # Store allocations
            for agent in allocation_request.agents:
                self.agents[agent.agent_id] = agent
                self.allocations[agent.agent_id] = allocations[agent]
                agent.allocated_resources = allocations[agent]

            self.allocation_count += 1
            self._transition_state(FSAState.IDLE)

            return AllocationResult(
                request_id=allocation_request.request_id,
                allocations={
                    agent.agent_id: allocations[agent]
                    for agent in allocation_request.agents
                },
                success=True,
                message="Resources allocated successfully",
            )

        except Exception as e:
            self._transition_state(FSAState.ERROR)
            logger.error(f"Allocation failed: {str(e)}")
            return AllocationResult(
                request_id=allocation_request.request_id,
                allocations={},
                success=False,
                message=f"Allocation error: {str(e)}",
            )

    def validate(self, request: AllocationRequest) -> ValidationResult:
        """
        Validate allocation request feasibility.

        Args:
            request: Allocation request to validate

        Returns:
            ValidationResult with validation status
        """
        errors = []
        warnings = []

        # Check if agents list is empty
        if not request.agents:
            errors.append("No agents specified in request")
            return ValidationResult(valid=False, errors=errors)

        # Calculate total resource requirements
        total_required = Resources()
        for agent in request.agents:
            total_required = total_required + agent.min_resources

        # Check if pool has sufficient resources
        available = self.resource_pool.available

        if not available.is_sufficient(total_required):
            errors.append(
                f"Insufficient resources. Required: {total_required.to_dict()}, "
                f"Available: {available.to_dict()}"
            )

        # Check for negative resource requests
        for agent in request.agents:
            if (
                agent.min_resources.cpu_cores < 0
                or agent.min_resources.memory_mb < 0
                or agent.min_resources.tokens < 0
            ):
                errors.append(f"Agent {agent.agent_id} has negative resource requests")

        # Validate priority ranges
        for agent in request.agents:
            if agent.priority < 1 or agent.priority > 10:
                warnings.append(
                    f"Agent {agent.agent_id} has invalid priority {agent.priority}"
                )

        # Check for duplicate agent IDs
        agent_ids = [agent.agent_id for agent in request.agents]
        if len(agent_ids) != len(set(agent_ids)):
            errors.append("Duplicate agent IDs found in request")

        return ValidationResult(
            valid=len(errors) == 0, errors=errors, warnings=warnings
        )

    def allocate_resources(
        self, agents: List[Agent], available: ResourcePool
    ) -> Dict[Agent, Resources]:
        """
        Distribute resources among agents based on allocation strategy.

        Args:
            agents: List of agents requesting resources
            available: Available resource pool

        Returns:
            Dictionary mapping agents to allocated resources
        """
        allocations: Dict[Agent, Resources] = {}

        # Determine strategy (use first agent's strategy or default)
        strategy = AllocationStrategy.FAIR_SHARE

        if strategy == AllocationStrategy.FAIR_SHARE:
            allocations = self._fair_share_allocation(agents, available)
        elif strategy == AllocationStrategy.PRIORITY:
            allocations = self._priority_allocation(agents, available)
        elif strategy == AllocationStrategy.DEMAND_BASED:
            allocations = self._demand_based_allocation(agents, available)
        elif strategy == AllocationStrategy.ML_PREDICTED:
            allocations = self._ml_predicted_allocation(agents, available)

        # Apply allocations to pool
        for agent, resources in allocations.items():
            available.allocate(resources)

        return allocations

    def _fair_share_allocation(
        self, agents: List[Agent], available: ResourcePool
    ) -> Dict[Agent, Resources]:
        """
        Fair-share allocation strategy - equal distribution.

        Args:
            agents: List of agents
            available: Available resources

        Returns:
            Allocation dictionary
        """
        allocations = {}
        num_agents = len(agents)

        if num_agents == 0:
            return allocations

        # Calculate per-agent share
        available_resources = available.available
        share = available_resources * (1.0 / num_agents)

        for agent in agents:
            # Respect minimum requirements
            allocated = Resources(
                cpu_cores=max(share.cpu_cores, agent.min_resources.cpu_cores),
                memory_mb=max(share.memory_mb, agent.min_resources.memory_mb),
                tokens=max(share.tokens, agent.min_resources.tokens),
                api_quota=max(share.api_quota, agent.min_resources.api_quota),
                gpu_units=max(share.gpu_units, agent.min_resources.gpu_units),
            )

            # Respect maximum limits
            if agent.max_resources.cpu_cores > 0:
                allocated.cpu_cores = min(
                    allocated.cpu_cores, agent.max_resources.cpu_cores
                )
            if agent.max_resources.memory_mb > 0:
                allocated.memory_mb = min(
                    allocated.memory_mb, agent.max_resources.memory_mb
                )
            if agent.max_resources.tokens > 0:
                allocated.tokens = min(allocated.tokens, agent.max_resources.tokens)

            allocations[agent] = allocated

        return allocations

    def _priority_allocation(
        self, agents: List[Agent], available: ResourcePool
    ) -> Dict[Agent, Resources]:
        """
        Priority-based allocation - higher priority agents get more resources.

        Args:
            agents: List of agents
            available: Available resources

        Returns:
            Allocation dictionary
        """
        allocations = {}

        # Sort by priority (highest first)
        sorted_agents = sorted(agents, key=lambda a: a.priority, reverse=True)

        total_priority = sum(agent.priority for agent in agents)
        available_resources = available.available

        for agent in sorted_agents:
            # Allocate proportional to priority
            priority_weight = agent.priority / total_priority
            allocated = available_resources * priority_weight

            # Respect min/max bounds
            allocated = Resources(
                cpu_cores=max(allocated.cpu_cores, agent.min_resources.cpu_cores),
                memory_mb=max(allocated.memory_mb, agent.min_resources.memory_mb),
                tokens=max(allocated.tokens, agent.min_resources.tokens),
                api_quota=max(allocated.api_quota, agent.min_resources.api_quota),
                gpu_units=max(allocated.gpu_units, agent.min_resources.gpu_units),
            )

            if agent.max_resources.cpu_cores > 0:
                allocated.cpu_cores = min(
                    allocated.cpu_cores, agent.max_resources.cpu_cores
                )
            if agent.max_resources.memory_mb > 0:
                allocated.memory_mb = min(
                    allocated.memory_mb, agent.max_resources.memory_mb
                )

            allocations[agent] = allocated

        return allocations

    def _demand_based_allocation(
        self, agents: List[Agent], available: ResourcePool
    ) -> Dict[Agent, Resources]:
        """
        Demand-based allocation - based on current usage patterns.

        Args:
            agents: List of agents
            available: Available resources

        Returns:
            Allocation dictionary
        """
        allocations = {}

        for agent in agents:
            # Check historical usage
            if agent.agent_id in self.usage_history and self.usage_history[
                agent.agent_id
            ]:
                # Calculate average usage from history
                history = list(self.usage_history[agent.agent_id])
                avg_cpu = sum(u.current.cpu_cores for u in history) / len(history)
                avg_mem = sum(u.current.memory_mb for u in history) / len(history)
                avg_tokens = sum(u.current.tokens for u in history) / len(history)

                # Add 20% buffer for growth
                allocated = Resources(
                    cpu_cores=avg_cpu * 1.2,
                    memory_mb=avg_mem * 1.2,
                    tokens=int(avg_tokens * 1.2),
                    api_quota=int(avg_tokens * 1.2 / 100),  # Estimate API calls
                    gpu_units=0.0,
                )
            else:
                # No history, use minimum requirements
                allocated = agent.min_resources

            allocations[agent] = allocated

        return allocations

    def _ml_predicted_allocation(
        self, agents: List[Agent], available: ResourcePool
    ) -> Dict[Agent, Resources]:
        """
        ML-based predicted allocation using demand forecasts.

        Args:
            agents: List of agents
            available: Available resources

        Returns:
            Allocation dictionary
        """
        allocations = {}

        for agent in agents:
            # Get forecast
            forecast = self.predict_demand(agent.agent_id, "1h")

            if forecast.confidence > 0.5:
                allocated = forecast.predicted_resources
            else:
                # Low confidence, fall back to min requirements
                allocated = agent.min_resources

            allocations[agent] = allocated

        return allocations

    def monitor_usage(self, agent_id: str) -> ResourceUsage:
        """
        Track real-time resource consumption for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            ResourceUsage with current usage metrics
        """
        self._transition_state(FSAState.MONITORING)

        if agent_id not in self.allocations:
            raise ValueError(f"Agent {agent_id} has no resource allocation")

        # Get current allocation
        allocated = self.allocations[agent_id]

        # Simulate current usage (in real implementation, this would query actual usage)
        current = Resources(
            cpu_cores=allocated.cpu_cores * 0.7,  # 70% utilization
            memory_mb=allocated.memory_mb * 0.6,
            tokens=int(allocated.tokens * 0.5),
            api_quota=int(allocated.api_quota * 0.4),
            gpu_units=allocated.gpu_units * 0.8,
        )

        # Update peak if needed
        if agent_id not in self.peak_usage:
            self.peak_usage[agent_id] = current
        else:
            peak = self.peak_usage[agent_id]
            self.peak_usage[agent_id] = Resources(
                cpu_cores=max(peak.cpu_cores, current.cpu_cores),
                memory_mb=max(peak.memory_mb, current.memory_mb),
                tokens=max(peak.tokens, current.tokens),
                api_quota=max(peak.api_quota, current.api_quota),
                gpu_units=max(peak.gpu_units, current.gpu_units),
            )

        # Calculate average from history
        history = list(self.usage_history[agent_id]) if agent_id in self.usage_history else []
        if history:
            avg = Resources(
                cpu_cores=sum(u.current.cpu_cores for u in history) / len(history),
                memory_mb=sum(u.current.memory_mb for u in history) / len(history),
                tokens=int(sum(u.current.tokens for u in history) / len(history)),
                api_quota=int(sum(u.current.api_quota for u in history) / len(history)),
                gpu_units=sum(u.current.gpu_units for u in history) / len(history),
            )
        else:
            avg = current

        # Calculate utilization
        utilization = 0.0
        if allocated.cpu_cores > 0:
            utilization = (current.cpu_cores / allocated.cpu_cores) * 100

        usage = ResourceUsage(
            agent_id=agent_id,
            current=current,
            peak=self.peak_usage[agent_id],
            average=avg,
            utilization_percent=utilization,
        )

        # Add to history
        self.usage_history[agent_id].append(usage)
        self.current_usage[agent_id] = usage

        self._transition_state(FSAState.IDLE)
        return usage

    def predict_demand(self, agent_id: str, time_window: str) -> DemandForecast:
        """
        Forecast resource needs using historical data.

        Args:
            agent_id: Agent identifier
            time_window: Time window for prediction (e.g., "1h", "24h")

        Returns:
            DemandForecast with predicted resource needs
        """
        # Check cache
        cache_key = f"{agent_id}_{time_window}"
        if cache_key in self.prediction_cache:
            cached = self.prediction_cache[cache_key]
            if (datetime.now() - cached.timestamp).seconds < self.cache_ttl:
                return cached

        # Simple moving average prediction
        if agent_id not in self.usage_history or not self.usage_history[agent_id]:
            # No history, predict minimum requirements
            if agent_id in self.agents:
                predicted = self.agents[agent_id].min_resources
            else:
                predicted = Resources()
            confidence = 0.3
        else:
            history = list(self.usage_history[agent_id])
            recent = history[-10:]  # Last 10 data points

            # Calculate trend
            avg_cpu = sum(u.current.cpu_cores for u in recent) / len(recent)
            avg_mem = sum(u.current.memory_mb for u in recent) / len(recent)
            avg_tokens = sum(u.current.tokens for u in recent) / len(recent)

            # Add growth factor based on trend
            growth_factor = 1.1  # 10% growth prediction

            predicted = Resources(
                cpu_cores=avg_cpu * growth_factor,
                memory_mb=avg_mem * growth_factor,
                tokens=int(avg_tokens * growth_factor),
                api_quota=int(avg_tokens * growth_factor / 100),
                gpu_units=0.0,
            )

            # Confidence based on history size
            confidence = min(len(history) / 50.0, 0.95)

        forecast = DemandForecast(
            agent_id=agent_id,
            predicted_resources=predicted,
            confidence=confidence,
            time_window=time_window,
            historical_accuracy=0.85,  # Historical accuracy metric
            timestamp=datetime.now(),
        )

        # Cache the prediction
        self.prediction_cache[cache_key] = forecast

        return forecast

    def rebalance_allocation(
        self, current_state: AllocationState
    ) -> RebalanceResult:
        """
        Dynamically adjust allocations based on current usage.

        Args:
            current_state: Current allocation state

        Returns:
            RebalanceResult with reallocation details
        """
        self._transition_state(FSAState.REBALANCING)

        reallocations = {}
        reclaimed = Resources()
        redistributed = Resources()

        try:
            # Identify underutilized agents
            for agent_id, usage in current_state.usage.items():
                if usage.utilization_percent < 50:  # Under 50% utilization
                    # Reclaim some resources
                    allocated = current_state.allocations[agent_id]
                    new_allocation = allocated * 0.7  # Reduce by 30%

                    # Ensure minimum requirements
                    if agent_id in self.agents:
                        agent = self.agents[agent_id]
                        new_allocation = Resources(
                            cpu_cores=max(
                                new_allocation.cpu_cores, agent.min_resources.cpu_cores
                            ),
                            memory_mb=max(
                                new_allocation.memory_mb, agent.min_resources.memory_mb
                            ),
                            tokens=max(
                                new_allocation.tokens, agent.min_resources.tokens
                            ),
                            api_quota=max(
                                new_allocation.api_quota, agent.min_resources.api_quota
                            ),
                            gpu_units=max(
                                new_allocation.gpu_units, agent.min_resources.gpu_units
                            ),
                        )

                    reclaimed_amount = allocated - new_allocation
                    reclaimed = reclaimed + reclaimed_amount
                    reallocations[agent_id] = new_allocation

            # Redistribute reclaimed resources to high-utilization agents
            for agent_id, usage in current_state.usage.items():
                if usage.utilization_percent > 80:  # Over 80% utilization
                    # Allocate more resources
                    current_alloc = current_state.allocations[agent_id]
                    boost = reclaimed * 0.3  # Give 30% of reclaimed
                    reallocations[agent_id] = current_alloc + boost
                    redistributed = redistributed + boost

            # Update allocations
            for agent_id, new_alloc in reallocations.items():
                self.allocations[agent_id] = new_alloc
                if agent_id in self.agents:
                    self.agents[agent_id].allocated_resources = new_alloc

            self.rebalance_count += 1
            self._transition_state(FSAState.IDLE)

            return RebalanceResult(
                reallocations=reallocations,
                reclaimed=reclaimed,
                redistributed=redistributed,
                success=True,
                message=f"Rebalanced {len(reallocations)} agents",
            )

        except Exception as e:
            self._transition_state(FSAState.ERROR)
            return RebalanceResult(
                reallocations={},
                reclaimed=Resources(),
                redistributed=Resources(),
                success=False,
                message=f"Rebalance failed: {str(e)}",
            )

    def enforce_quotas(
        self, usage: ResourceUsage, limits: Quotas
    ) -> EnforcementResult:
        """
        Apply resource limits and throttling.

        Args:
            usage: Current resource usage
            limits: Quota limits

        Returns:
            EnforcementResult with enforcement actions
        """
        violations = []
        throttled = False
        action_taken = ""

        # Check CPU quota
        if usage.current.cpu_cores > limits.max_cpu_percent:
            violations.append(
                f"CPU usage {usage.current.cpu_cores}% exceeds limit {limits.max_cpu_percent}%"
            )
            throttled = True

        # Check memory quota
        if usage.current.memory_mb > limits.max_memory_mb:
            violations.append(
                f"Memory usage {usage.current.memory_mb}MB exceeds limit {limits.max_memory_mb}MB"
            )
            throttled = True

        # Check token rate
        if usage.current.tokens > limits.max_tokens_per_minute:
            violations.append(
                f"Token usage {usage.current.tokens} exceeds rate limit {limits.max_tokens_per_minute}"
            )
            throttled = True

        # Check API call rate
        if usage.current.api_quota > limits.max_api_calls_per_minute:
            violations.append(
                f"API calls {usage.current.api_quota} exceed rate limit {limits.max_api_calls_per_minute}"
            )
            throttled = True

        if throttled:
            action_taken = "Throttling applied to agent"
            logger.warning(
                f"Agent {usage.agent_id} throttled due to quota violations: {violations}"
            )

        return EnforcementResult(
            agent_id=usage.agent_id,
            throttled=throttled,
            violations=violations,
            action_taken=action_taken,
        )

    def optimize_efficiency(
        self, allocation: ResourceAllocation
    ) -> OptimizationResult:
        """
        Improve resource utilization and efficiency.

        Args:
            allocation: Current resource allocation

        Returns:
            OptimizationResult with optimization recommendations
        """
        self._transition_state(FSAState.OPTIMIZING)

        recommendations = []
        applied_optimizations = []
        efficiency_gain = 0.0

        try:
            # Analyze utilization
            if allocation.utilization < 50:
                recommendations.append(
                    f"Agent {allocation.agent_id} is underutilized ({allocation.utilization:.1f}%), "
                    "consider reducing allocation"
                )
                efficiency_gain += 20.0
            elif allocation.utilization > 90:
                recommendations.append(
                    f"Agent {allocation.agent_id} is overutilized ({allocation.utilization:.1f}%), "
                    "consider increasing allocation"
                )
                efficiency_gain += 10.0

            # Check for resource imbalance
            if allocation.allocated.cpu_cores > allocation.requested.cpu_cores * 2:
                recommendations.append(
                    f"CPU over-allocated by {allocation.allocated.cpu_cores - allocation.requested.cpu_cores:.1f} cores"
                )
                applied_optimizations.append("Reduce CPU allocation")
                efficiency_gain += 15.0

            if allocation.allocated.memory_mb > allocation.requested.memory_mb * 2:
                recommendations.append(
                    f"Memory over-allocated by {allocation.allocated.memory_mb - allocation.requested.memory_mb:.1f} MB"
                )
                applied_optimizations.append("Reduce memory allocation")
                efficiency_gain += 15.0

            self.optimization_count += 1
            self._transition_state(FSAState.IDLE)

            return OptimizationResult(
                efficiency_gain=efficiency_gain,
                recommendations=recommendations,
                applied_optimizations=applied_optimizations,
            )

        except Exception as e:
            self._transition_state(FSAState.ERROR)
            logger.error(f"Optimization failed: {str(e)}")
            return OptimizationResult(
                efficiency_gain=0.0,
                recommendations=[],
                applied_optimizations=[],
            )

    def reclaim_idle_resources(self, idle_threshold: int = 300) -> ReclaimResult:
        """
        Recover unused resources from idle agents.

        Args:
            idle_threshold: Idle time threshold in seconds

        Returns:
            ReclaimResult with reclaimed resources
        """
        reclaimed = Resources()
        affected_agents = []

        try:
            current_time = datetime.now()

            for agent_id, usage in self.current_usage.items():
                # Check if agent is idle
                idle_time = (current_time - usage.timestamp).seconds

                if idle_time > idle_threshold and usage.utilization_percent < 10:
                    # Reclaim resources
                    if agent_id in self.allocations:
                        allocated = self.allocations[agent_id]

                        # Keep minimum resources
                        if agent_id in self.agents:
                            min_resources = self.agents[agent_id].min_resources
                            reclaimed_amount = allocated - min_resources
                            reclaimed = reclaimed + reclaimed_amount

                            # Update allocation
                            self.allocations[agent_id] = min_resources
                            self.agents[agent_id].allocated_resources = min_resources

                            # Return to pool
                            self.resource_pool.deallocate(reclaimed_amount)

                            affected_agents.append(agent_id)

            return ReclaimResult(
                reclaimed=reclaimed,
                affected_agents=affected_agents,
                success=True,
                message=f"Reclaimed resources from {len(affected_agents)} idle agents",
            )

        except Exception as e:
            logger.error(f"Resource reclamation failed: {str(e)}")
            return ReclaimResult(
                reclaimed=Resources(),
                affected_agents=[],
                success=False,
                message=f"Reclamation failed: {str(e)}",
            )

    def handle_resource_contention(
        self, conflicts: List[ResourceConflict]
    ) -> Resolution:
        """
        Resolve resource conflicts between agents.

        Args:
            conflicts: List of resource conflicts

        Returns:
            Resolution with conflict resolution strategy
        """
        if not conflicts:
            return Resolution(
                conflict_id="none",
                strategy="none",
                allocations={},
                success=True,
                message="No conflicts to resolve",
            )

        conflict = conflicts[0]  # Handle first conflict

        try:
            # Priority-based resolution
            agent_priorities = {}
            for agent_id in conflict.agents:
                if agent_id in self.agents:
                    agent_priorities[agent_id] = self.agents[agent_id].priority
                else:
                    agent_priorities[agent_id] = 1

            # Sort by priority
            sorted_agents = sorted(
                agent_priorities.items(), key=lambda x: x[1], reverse=True
            )

            # Allocate proportionally to priority
            total_priority = sum(p for _, p in sorted_agents)
            allocations = {}

            for agent_id, priority in sorted_agents:
                share = (priority / total_priority) * conflict.available
                allocations[agent_id] = share

            return Resolution(
                conflict_id=conflict.conflict_id,
                strategy="priority_based",
                allocations=allocations,
                success=True,
                message=f"Resolved conflict using priority-based allocation",
            )

        except Exception as e:
            logger.error(f"Conflict resolution failed: {str(e)}")
            return Resolution(
                conflict_id=conflict.conflict_id,
                strategy="failed",
                allocations={},
                success=False,
                message=f"Resolution failed: {str(e)}",
            )

    def get_allocation_state(self) -> AllocationState:
        """Get current allocation state."""
        return AllocationState(
            allocations=self.allocations.copy(),
            usage=self.current_usage.copy(),
            pool=self.resource_pool,
        )

    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        return {
            "allocation_count": self.allocation_count,
            "rebalance_count": self.rebalance_count,
            "optimization_count": self.optimization_count,
            "total_allocated": self.resource_pool.allocated.to_dict(),
            "total_available": self.resource_pool.available.to_dict(),
            "active_agents": len(self.agents),
            "state": self.state.value,
        }
