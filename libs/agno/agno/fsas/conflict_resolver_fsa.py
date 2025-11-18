"""
Conflict Resolver FSA: Detect, analyze, and resolve conflicts between competing FSAs,
resource contention, data inconsistencies, and operational conflicts in multi-agent systems.

Provides automated conflict resolution strategies with configurable priority rules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import uuid4

from agno.utils.log import logger


class ConflictType(Enum):
    """Types of conflicts that can occur in multi-agent systems."""

    RESOURCE = "resource"  # Resource allocation conflicts
    DATA = "data"  # Data inconsistency conflicts
    TIMING = "timing"  # Scheduling/timing conflicts
    PRIORITY = "priority"  # Priority conflicts
    DEPENDENCY = "dependency"  # Dependency conflicts
    CIRCULAR = "circular"  # Circular dependency conflicts
    UNKNOWN = "unknown"  # Unknown conflict type


class ResolutionStrategy(Enum):
    """Strategies for resolving conflicts."""

    PRIORITY_BASED = "priority_based"  # Use priority rules
    FAIR_SHARE = "fair_share"  # Fair resource allocation
    NEGOTIATION = "negotiation"  # Multi-party negotiation
    ROLLBACK = "rollback"  # Rollback to previous state
    FIRST_COME_FIRST_SERVE = "fcfs"  # First-come-first-serve
    PREEMPTION = "preemption"  # Preempt lower priority
    MERGE = "merge"  # Merge conflicting states
    ABORT = "abort"  # Abort conflicting operations


class FSAState(Enum):
    """States in the Conflict Resolver FSA."""

    IDLE = "idle"
    DETECTING = "detecting"
    CLASSIFYING = "classifying"
    ANALYZING = "analyzing"
    RESOLVING = "resolving"
    NEGOTIATING = "negotiating"
    APPLYING = "applying"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLBACK = "rollback"


@dataclass
class Agent:
    """Represents an agent in a multi-agent system."""

    agent_id: str
    name: str
    priority: int = 0
    resources: Dict[str, Any] = field(default_factory=dict)
    state: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Operation:
    """Represents an operation performed by an agent."""

    operation_id: str
    agent_id: str
    operation_type: str
    resource_ids: List[str] = field(default_factory=list)
    data_keys: List[str] = field(default_factory=list)
    timestamp: float = 0.0
    priority: int = 0
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Conflict:
    """Base class for conflicts."""

    conflict_id: str
    conflict_type: ConflictType
    involved_agents: List[str]
    involved_operations: List[str]
    severity: int = 1  # 1-10 scale
    detected_at: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResourceConflict(Conflict):
    """Resource allocation conflict."""

    resource_id: str = ""
    requested_by: List[str] = field(default_factory=list)
    available_capacity: float = 0.0
    total_requested: float = 0.0

    def __post_init__(self):
        self.conflict_type = ConflictType.RESOURCE


@dataclass
class DataConflict(Conflict):
    """Data inconsistency conflict."""

    data_key: str = ""
    conflicting_values: Dict[str, Any] = field(default_factory=dict)
    versions: List[int] = field(default_factory=list)

    def __post_init__(self):
        self.conflict_type = ConflictType.DATA


@dataclass
class TimingConflict(Conflict):
    """Timing/scheduling conflict."""

    time_slot: Tuple[float, float] = (0.0, 0.0)
    competing_operations: List[str] = field(default_factory=list)
    resource_id: Optional[str] = None

    def __post_init__(self):
        self.conflict_type = ConflictType.TIMING


@dataclass
class ResourceAllocation:
    """Result of resource conflict resolution."""

    resource_id: str
    allocations: Dict[str, float]  # agent_id -> allocated amount
    denied: List[str] = field(default_factory=list)
    wait_queue: List[str] = field(default_factory=list)


@dataclass
class DataState:
    """Result of data conflict resolution."""

    data_key: str
    resolved_value: Any
    version: int
    merged_from: List[str] = field(default_factory=list)


@dataclass
class Schedule:
    """Result of timing conflict resolution."""

    time_slots: Dict[str, Tuple[float, float]]  # operation_id -> (start, end)
    resource_id: Optional[str] = None
    conflicts_resolved: int = 0


@dataclass
class PriorityRules:
    """Priority rules for conflict resolution."""

    agent_priorities: Dict[str, int] = field(default_factory=dict)
    operation_priorities: Dict[str, int] = field(default_factory=dict)
    default_priority: int = 0
    preemption_enabled: bool = False
    fairness_weight: float = 0.5  # 0.0 = pure priority, 1.0 = pure fairness


@dataclass
class ResolutionPlan:
    """Plan for resolving multiple conflicts."""

    plan_id: str
    conflicts: List[Conflict]
    strategy: ResolutionStrategy
    steps: List[str] = field(default_factory=list)
    estimated_time: float = 0.0
    success_probability: float = 1.0


@dataclass
class NegotiatedResolution:
    """Result of negotiation between multiple parties."""

    resolution_id: str
    participating_agents: List[str]
    agreed_terms: Dict[str, Any] = field(default_factory=dict)
    compromises: List[str] = field(default_factory=list)
    consensus_level: float = 0.0  # 0.0 to 1.0


@dataclass
class Resolution:
    """Result of conflict resolution."""

    resolution_id: str
    conflict_id: str
    strategy: ResolutionStrategy
    success: bool
    resource_allocations: List[ResourceAllocation] = field(default_factory=list)
    data_states: List[DataState] = field(default_factory=list)
    schedules: List[Schedule] = field(default_factory=list)
    negotiated: Optional[NegotiatedResolution] = None
    rollback_performed: bool = False
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RollbackResult:
    """Result of rollback operation."""

    rollback_id: str
    resolution_id: str
    success: bool
    reverted_operations: List[str] = field(default_factory=list)
    restored_state: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None


@dataclass
class ConflictScenario:
    """Scenario for validating conflict detection and resolution."""

    scenario_id: str
    operations: List[Operation]
    expected_conflicts: List[ConflictType]
    agents: List[Agent] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Result of validating conflict detection."""

    scenario_id: str
    detected_conflicts: List[Conflict]
    expected_conflicts: List[ConflictType]
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    accuracy: float = 0.0


@dataclass
class ConflictResolverFSA:
    """
    Finite State Automaton for conflict detection and resolution in multi-agent systems.

    This FSA detects, analyzes, and resolves conflicts between competing FSAs,
    resource contention, data inconsistencies, and operational conflicts.

    Attributes:
        fsa_id: Unique identifier for this FSA instance
        state: Current state of the FSA
        agents: Dictionary of agents in the system
        operations: List of operations being tracked
        conflicts: List of detected conflicts
        resolutions: List of resolution results
        priority_rules: Priority rules for conflict resolution
        enable_negotiation: Whether to enable negotiation for conflicts
        enable_rollback: Whether to enable rollback on failures
        max_retries: Maximum number of resolution retries
        debug_mode: Enable debug logging
    """

    # FSA identification
    fsa_id: str = field(default_factory=lambda: str(uuid4()))
    state: FSAState = FSAState.IDLE

    # Agent and operation tracking
    agents: Dict[str, Agent] = field(default_factory=dict)
    operations: List[Operation] = field(default_factory=list)
    conflicts: List[Conflict] = field(default_factory=list)
    resolutions: List[Resolution] = field(default_factory=list)

    # Configuration
    priority_rules: PriorityRules = field(default_factory=PriorityRules)
    enable_negotiation: bool = True
    enable_rollback: bool = True
    max_retries: int = 3
    debug_mode: bool = False

    # Resource tracking
    resources: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    data_store: Dict[str, Any] = field(default_factory=dict)

    # History for rollback
    state_history: List[Dict[str, Any]] = field(default_factory=list)
    operation_history: List[Operation] = field(default_factory=list)

    def __post_init__(self):
        """Initialize the FSA."""
        if self.debug_mode:
            logger.debug(f"ConflictResolverFSA initialized: {self.fsa_id}")

    def execute(self, conflict: Conflict) -> Resolution:
        """
        Main conflict resolution pipeline.

        Args:
            conflict: The conflict to resolve

        Returns:
            Resolution: The resolution result

        Raises:
            ValueError: If conflict is invalid
            RuntimeError: If resolution fails after max retries
        """
        if not conflict:
            raise ValueError("Conflict cannot be None")

        logger.info(f"Executing conflict resolution for {conflict.conflict_id}")
        self._transition_state(FSAState.RESOLVING)

        # Save current state for potential rollback
        self._save_state()

        retry_count = 0
        while retry_count < self.max_retries:
            try:
                # Classify the conflict
                self._transition_state(FSAState.CLASSIFYING)
                conflict_type = self.classify_conflict(conflict)
                logger.debug(f"Classified conflict as {conflict_type}")

                # Analyze and select resolution strategy
                self._transition_state(FSAState.ANALYZING)
                strategy = self._select_resolution_strategy(conflict)

                # Resolve based on conflict type
                self._transition_state(FSAState.RESOLVING)
                resolution = self._resolve_by_type(conflict, strategy)

                # Validate the resolution
                self._transition_state(FSAState.VALIDATING)
                if self._validate_resolution(resolution):
                    # Apply the resolution
                    self._transition_state(FSAState.APPLYING)
                    self._apply_resolution(resolution)
                    self._transition_state(FSAState.COMPLETED)

                    self.resolutions.append(resolution)
                    logger.info(f"Successfully resolved conflict {conflict.conflict_id}")
                    return resolution
                else:
                    logger.warning(f"Resolution validation failed for {conflict.conflict_id}")
                    retry_count += 1

            except Exception as e:
                logger.error(f"Error during conflict resolution: {e}")
                retry_count += 1

                if retry_count >= self.max_retries:
                    if self.enable_rollback:
                        self._transition_state(FSAState.ROLLBACK)
                        rollback_result = self._perform_rollback(conflict)
                        resolution = Resolution(
                            resolution_id=str(uuid4()),
                            conflict_id=conflict.conflict_id,
                            strategy=ResolutionStrategy.ROLLBACK,
                            success=False,
                            rollback_performed=True,
                            error_message=str(e),
                        )
                        self._transition_state(FSAState.FAILED)
                        return resolution
                    else:
                        self._transition_state(FSAState.FAILED)
                        raise RuntimeError(f"Failed to resolve conflict after {self.max_retries} retries: {e}")

        # If we get here, we've exhausted retries
        self._transition_state(FSAState.FAILED)
        return Resolution(
            resolution_id=str(uuid4()),
            conflict_id=conflict.conflict_id,
            strategy=ResolutionStrategy.ABORT,
            success=False,
            error_message="Exceeded maximum retries",
        )

    def validate(self, conflict_scenario: ConflictScenario) -> ValidationResult:
        """
        Validate conflict detection against a scenario.

        Args:
            conflict_scenario: Scenario with expected conflicts

        Returns:
            ValidationResult: Validation metrics
        """
        logger.info(f"Validating conflict scenario {conflict_scenario.scenario_id}")

        # Detect conflicts in the scenario
        detected = self.detect_conflicts(conflict_scenario.operations)

        # Calculate validation metrics
        detected_types = {c.conflict_type for c in detected}
        expected_types = set(conflict_scenario.expected_conflicts)

        true_positives = len(detected_types & expected_types)
        false_positives = len(detected_types - expected_types)
        false_negatives = len(expected_types - detected_types)

        total = true_positives + false_positives + false_negatives
        accuracy = true_positives / total if total > 0 else 1.0

        result = ValidationResult(
            scenario_id=conflict_scenario.scenario_id,
            detected_conflicts=detected,
            expected_conflicts=conflict_scenario.expected_conflicts,
            true_positives=true_positives,
            false_positives=false_positives,
            false_negatives=false_negatives,
            accuracy=accuracy,
        )

        logger.info(f"Validation accuracy: {accuracy:.2%}")
        return result

    def detect_conflicts(self, operations: List[Operation]) -> List[Conflict]:
        """
        Identify all conflicts in a list of operations.

        Args:
            operations: List of operations to analyze

        Returns:
            List of detected conflicts
        """
        logger.debug(f"Detecting conflicts in {len(operations)} operations")
        self._transition_state(FSAState.DETECTING)

        conflicts = []
        self.operations = operations

        # Detect resource conflicts
        conflicts.extend(self._detect_resource_conflicts(operations))

        # Detect data conflicts
        conflicts.extend(self._detect_data_conflicts(operations))

        # Detect timing conflicts
        conflicts.extend(self._detect_timing_conflicts(operations))

        # Detect circular dependencies
        conflicts.extend(self._detect_circular_dependencies(operations))

        self.conflicts = conflicts
        logger.info(f"Detected {len(conflicts)} conflicts")

        return conflicts

    def classify_conflict(self, conflict: Conflict) -> ConflictType:
        """
        Categorize conflict patterns.

        Args:
            conflict: The conflict to classify

        Returns:
            ConflictType: The classified type
        """
        # Already typed conflicts
        if isinstance(conflict, ResourceConflict):
            return ConflictType.RESOURCE
        elif isinstance(conflict, DataConflict):
            return ConflictType.DATA
        elif isinstance(conflict, TimingConflict):
            return ConflictType.TIMING

        # Analyze metadata for additional classification
        if conflict.metadata.get("circular_dependency"):
            return ConflictType.CIRCULAR
        elif conflict.metadata.get("priority_conflict"):
            return ConflictType.PRIORITY
        elif conflict.metadata.get("dependency_conflict"):
            return ConflictType.DEPENDENCY

        return conflict.conflict_type

    def resolve_resource_conflict(self, conflict: ResourceConflict) -> ResourceAllocation:
        """
        Resolve resource contention.

        Args:
            conflict: Resource conflict to resolve

        Returns:
            ResourceAllocation: The allocation decision
        """
        logger.debug(f"Resolving resource conflict for {conflict.resource_id}")

        allocations = {}
        denied = []
        wait_queue = []

        # Get total available capacity
        available = conflict.available_capacity
        requests = {}

        # Collect all requests with priorities
        for agent_id in conflict.requested_by:
            priority = self.priority_rules.agent_priorities.get(agent_id, self.priority_rules.default_priority)
            requests[agent_id] = {
                "priority": priority,
                "amount": conflict.metadata.get(f"{agent_id}_requested", 1.0),
            }

        # Sort by priority (higher first)
        sorted_requests = sorted(requests.items(), key=lambda x: x[1]["priority"], reverse=True)

        # Allocate based on strategy
        if self.priority_rules.preemption_enabled:
            # Pure priority-based allocation
            for agent_id, req in sorted_requests:
                if available >= req["amount"]:
                    allocations[agent_id] = req["amount"]
                    available -= req["amount"]
                else:
                    denied.append(agent_id)
        else:
            # Fair-share with priority weighting
            fairness = self.priority_rules.fairness_weight
            for agent_id, req in sorted_requests:
                weight = (1 - fairness) * req["priority"] + fairness
                allocated = min(req["amount"] * weight, available)
                if allocated > 0:
                    allocations[agent_id] = allocated
                    available -= allocated
                else:
                    wait_queue.append(agent_id)

        return ResourceAllocation(
            resource_id=conflict.resource_id,
            allocations=allocations,
            denied=denied,
            wait_queue=wait_queue,
        )

    def resolve_data_conflict(self, conflict: DataConflict) -> DataState:
        """
        Reconcile data inconsistencies.

        Args:
            conflict: Data conflict to resolve

        Returns:
            DataState: The reconciled data state
        """
        logger.debug(f"Resolving data conflict for key {conflict.data_key}")

        # Strategy: Last-write-wins with version tracking
        max_version = max(conflict.versions) if conflict.versions else 0
        merged_from = []

        # Find the value with the highest version
        resolved_value = None
        for agent_id, value in conflict.conflicting_values.items():
            version = conflict.metadata.get(f"{agent_id}_version", 0)
            if version == max_version:
                resolved_value = value
                merged_from.append(agent_id)

        # If no version info, use first value
        if resolved_value is None and conflict.conflicting_values:
            resolved_value = next(iter(conflict.conflicting_values.values()))
            merged_from = list(conflict.conflicting_values.keys())

        return DataState(
            data_key=conflict.data_key,
            resolved_value=resolved_value,
            version=max_version + 1,
            merged_from=merged_from,
        )

    def resolve_timing_conflict(self, conflict: TimingConflict) -> Schedule:
        """
        Coordinate timing conflicts.

        Args:
            conflict: Timing conflict to resolve

        Returns:
            Schedule: The resolved schedule
        """
        logger.debug(f"Resolving timing conflict for time slot {conflict.time_slot}")

        time_slots = {}
        current_time = conflict.time_slot[0]

        # Get operation priorities
        op_priorities = []
        for op_id in conflict.competing_operations:
            priority = self.priority_rules.operation_priorities.get(op_id, self.priority_rules.default_priority)
            op_priorities.append((op_id, priority))

        # Sort by priority
        op_priorities.sort(key=lambda x: x[1], reverse=True)

        # Allocate time slots sequentially by priority
        duration = conflict.time_slot[1] - conflict.time_slot[0]
        slot_duration = duration / len(op_priorities)

        for op_id, _ in op_priorities:
            time_slots[op_id] = (current_time, current_time + slot_duration)
            current_time += slot_duration

        return Schedule(
            time_slots=time_slots,
            resource_id=conflict.resource_id,
            conflicts_resolved=len(conflict.competing_operations),
        )

    def apply_priority_rules(self, conflicts: List[Conflict], rules: PriorityRules) -> ResolutionPlan:
        """
        Apply priority-based resolution to multiple conflicts.

        Args:
            conflicts: List of conflicts to resolve
            rules: Priority rules to apply

        Returns:
            ResolutionPlan: The resolution plan
        """
        logger.debug(f"Applying priority rules to {len(conflicts)} conflicts")

        self.priority_rules = rules
        plan = ResolutionPlan(
            plan_id=str(uuid4()),
            conflicts=conflicts,
            strategy=ResolutionStrategy.PRIORITY_BASED,
        )

        # Sort conflicts by severity
        sorted_conflicts = sorted(conflicts, key=lambda c: c.severity, reverse=True)

        # Generate resolution steps
        for conflict in sorted_conflicts:
            step = f"Resolve {conflict.conflict_type.value} conflict {conflict.conflict_id}"
            plan.steps.append(step)

        plan.estimated_time = len(conflicts) * 0.1  # Rough estimate
        plan.success_probability = 0.95 ** len(conflicts)  # Decreases with more conflicts

        return plan

    def negotiate_solution(self, parties: List[Agent], conflict: Conflict) -> NegotiatedResolution:
        """
        Multi-party conflict negotiation.

        Args:
            parties: List of agents involved in negotiation
            conflict: The conflict to negotiate

        Returns:
            NegotiatedResolution: The negotiated result
        """
        logger.debug(f"Negotiating solution with {len(parties)} parties")
        self._transition_state(FSAState.NEGOTIATING)

        # Simple negotiation: weighted average based on priority
        total_priority = sum(p.priority for p in parties)
        agreed_terms = {}
        compromises = []

        if conflict.conflict_type == ConflictType.RESOURCE:
            # Negotiate resource allocation
            for party in parties:
                weight = party.priority / total_priority if total_priority > 0 else 1.0 / len(parties)
                agreed_terms[party.agent_id] = {"allocation_weight": weight}
                if weight < 0.5:
                    compromises.append(f"{party.name} accepts reduced allocation")

        elif conflict.conflict_type == ConflictType.DATA:
            # Negotiate data value through voting
            votes = {}
            for party in parties:
                value = party.state.get(conflict.metadata.get("data_key", ""), None)
                votes[value] = votes.get(value, 0) + party.priority

            winning_value = max(votes.items(), key=lambda x: x[1])[0] if votes else None
            agreed_terms["data_value"] = winning_value
            compromises.append("Data value determined by weighted voting")

        # Calculate consensus level
        consensus = min(1.0, total_priority / (len(parties) * 10))  # Normalize to 0-1

        return NegotiatedResolution(
            resolution_id=str(uuid4()),
            participating_agents=[p.agent_id for p in parties],
            agreed_terms=agreed_terms,
            compromises=compromises,
            consensus_level=consensus,
        )

    def rollback_on_failure(self, resolution: Resolution) -> RollbackResult:
        """
        Handle resolution failures with rollback.

        Args:
            resolution: The failed resolution

        Returns:
            RollbackResult: The rollback result
        """
        logger.warning(f"Rolling back failed resolution {resolution.resolution_id}")
        return self._perform_rollback(resolution.conflict_id)

    def _detect_resource_conflicts(self, operations: List[Operation]) -> List[ResourceConflict]:
        """Detect conflicts in resource allocation."""
        conflicts = []
        resource_requests: Dict[str, List[Operation]] = {}

        # Group operations by resource
        for op in operations:
            for resource_id in op.resource_ids:
                if resource_id not in resource_requests:
                    resource_requests[resource_id] = []
                resource_requests[resource_id].append(op)

        # Check for conflicts
        for resource_id, ops in resource_requests.items():
            if len(ops) > 1:
                conflict = ResourceConflict(
                    conflict_id=str(uuid4()),
                    conflict_type=ConflictType.RESOURCE,
                    involved_agents=[op.agent_id for op in ops],
                    involved_operations=[op.operation_id for op in ops],
                    resource_id=resource_id,
                    requested_by=[op.agent_id for op in ops],
                    available_capacity=self.resources.get(resource_id, {}).get("capacity", 1.0),
                    total_requested=len(ops),
                    severity=min(10, len(ops)),
                )
                conflicts.append(conflict)

        return conflicts

    def _detect_data_conflicts(self, operations: List[Operation]) -> List[DataConflict]:
        """Detect conflicts in data access."""
        conflicts = []
        data_access: Dict[str, List[Operation]] = {}

        # Group operations by data key
        for op in operations:
            for data_key in op.data_keys:
                if data_key not in data_access:
                    data_access[data_key] = []
                data_access[data_key].append(op)

        # Check for write conflicts
        for data_key, ops in data_access.items():
            write_ops = [op for op in ops if op.operation_type == "write"]
            if len(write_ops) > 1:
                conflict = DataConflict(
                    conflict_id=str(uuid4()),
                    conflict_type=ConflictType.DATA,
                    involved_agents=[op.agent_id for op in write_ops],
                    involved_operations=[op.operation_id for op in write_ops],
                    data_key=data_key,
                    conflicting_values={op.agent_id: op.metadata.get("value") for op in write_ops},
                    severity=min(10, len(write_ops)),
                )
                conflicts.append(conflict)

        return conflicts

    def _detect_timing_conflicts(self, operations: List[Operation]) -> List[TimingConflict]:
        """Detect timing and scheduling conflicts."""
        conflicts = []

        # Check for overlapping time windows
        for i, op1 in enumerate(operations):
            for op2 in operations[i + 1 :]:
                # Check if operations overlap in time
                if self._operations_overlap(op1, op2):
                    conflict = TimingConflict(
                        conflict_id=str(uuid4()),
                        conflict_type=ConflictType.TIMING,
                        involved_agents=[op1.agent_id, op2.agent_id],
                        involved_operations=[op1.operation_id, op2.operation_id],
                        competing_operations=[op1.operation_id, op2.operation_id],
                        time_slot=(min(op1.timestamp, op2.timestamp), max(op1.timestamp, op2.timestamp)),
                        severity=5,
                    )
                    conflicts.append(conflict)

        return conflicts

    def _detect_circular_dependencies(self, operations: List[Operation]) -> List[Conflict]:
        """Detect circular dependency conflicts."""
        conflicts = []
        dependency_graph: Dict[str, Set[str]] = {}

        # Build dependency graph
        for op in operations:
            if op.operation_id not in dependency_graph:
                dependency_graph[op.operation_id] = set()
            dependency_graph[op.operation_id].update(op.dependencies)

        # Detect cycles using DFS
        visited = set()
        rec_stack = set()

        def has_cycle(node: str, path: List[str]) -> bool:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in dependency_graph.get(node, set()):
                if neighbor not in visited:
                    if has_cycle(neighbor, path):
                        return True
                elif neighbor in rec_stack:
                    # Cycle detected
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:]
                    conflict = Conflict(
                        conflict_id=str(uuid4()),
                        conflict_type=ConflictType.CIRCULAR,
                        involved_agents=[],
                        involved_operations=cycle,
                        severity=9,
                        metadata={"circular_dependency": True, "cycle": cycle},
                    )
                    conflicts.append(conflict)
                    return True

            path.pop()
            rec_stack.remove(node)
            return False

        for op in operations:
            if op.operation_id not in visited:
                has_cycle(op.operation_id, [])

        return conflicts

    def _operations_overlap(self, op1: Operation, op2: Operation) -> bool:
        """Check if two operations overlap in time or resources."""
        # Check resource overlap
        shared_resources = set(op1.resource_ids) & set(op2.resource_ids)
        if not shared_resources:
            return False

        # Simple time overlap check
        time_diff = abs(op1.timestamp - op2.timestamp)
        return time_diff < 1.0  # Operations within 1 time unit are considered overlapping

    def _select_resolution_strategy(self, conflict: Conflict) -> ResolutionStrategy:
        """Select the best resolution strategy for a conflict."""
        if conflict.conflict_type == ConflictType.CIRCULAR:
            return ResolutionStrategy.ABORT

        if len(conflict.involved_agents) > 2 and self.enable_negotiation:
            return ResolutionStrategy.NEGOTIATION

        if conflict.severity > 7:
            return ResolutionStrategy.PRIORITY_BASED

        if conflict.conflict_type == ConflictType.RESOURCE:
            return ResolutionStrategy.FAIR_SHARE

        if conflict.conflict_type == ConflictType.DATA:
            return ResolutionStrategy.MERGE

        return ResolutionStrategy.PRIORITY_BASED

    def _resolve_by_type(self, conflict: Conflict, strategy: ResolutionStrategy) -> Resolution:
        """Resolve conflict based on its type."""
        resolution = Resolution(
            resolution_id=str(uuid4()),
            conflict_id=conflict.conflict_id,
            strategy=strategy,
            success=False,
        )

        try:
            if isinstance(conflict, ResourceConflict):
                allocation = self.resolve_resource_conflict(conflict)
                resolution.resource_allocations.append(allocation)
                resolution.success = True

            elif isinstance(conflict, DataConflict):
                data_state = self.resolve_data_conflict(conflict)
                resolution.data_states.append(data_state)
                resolution.success = True

            elif isinstance(conflict, TimingConflict):
                schedule = self.resolve_timing_conflict(conflict)
                resolution.schedules.append(schedule)
                resolution.success = True

            elif strategy == ResolutionStrategy.NEGOTIATION:
                parties = [self.agents[aid] for aid in conflict.involved_agents if aid in self.agents]
                negotiated = self.negotiate_solution(parties, conflict)
                resolution.negotiated = negotiated
                resolution.success = negotiated.consensus_level > 0.5

            else:
                # Default resolution
                resolution.success = True
                resolution.metadata["strategy"] = "default"

        except Exception as e:
            resolution.success = False
            resolution.error_message = str(e)
            logger.error(f"Error resolving conflict: {e}")

        return resolution

    def _validate_resolution(self, resolution: Resolution) -> bool:
        """Validate that a resolution is valid and consistent."""
        if not resolution.success:
            return False

        # Validate resource allocations don't exceed capacity
        for allocation in resolution.resource_allocations:
            total_allocated = sum(allocation.allocations.values())
            resource_capacity = self.resources.get(allocation.resource_id, {}).get("capacity", float("inf"))
            if total_allocated > resource_capacity:
                logger.warning(f"Resource allocation exceeds capacity: {total_allocated} > {resource_capacity}")
                return False

        return True

    def _apply_resolution(self, resolution: Resolution):
        """Apply a resolution to the system state."""
        # Update resource allocations
        for allocation in resolution.resource_allocations:
            if allocation.resource_id not in self.resources:
                self.resources[allocation.resource_id] = {}
            self.resources[allocation.resource_id]["allocations"] = allocation.allocations

        # Update data states
        for data_state in resolution.data_states:
            self.data_store[data_state.data_key] = {
                "value": data_state.resolved_value,
                "version": data_state.version,
            }

        logger.debug(f"Applied resolution {resolution.resolution_id}")

    def _save_state(self):
        """Save current state for potential rollback."""
        state_snapshot = {
            "resources": self.resources.copy(),
            "data_store": self.data_store.copy(),
            "timestamp": len(self.state_history),
        }
        self.state_history.append(state_snapshot)

        # Keep only last 100 states
        if len(self.state_history) > 100:
            self.state_history.pop(0)

    def _perform_rollback(self, conflict_id: str) -> RollbackResult:
        """Perform rollback to previous state."""
        if not self.state_history:
            return RollbackResult(
                rollback_id=str(uuid4()),
                resolution_id=conflict_id,
                success=False,
                error_message="No state history available for rollback",
            )

        # Restore previous state
        previous_state = self.state_history.pop()
        self.resources = previous_state["resources"]
        self.data_store = previous_state["data_store"]

        return RollbackResult(
            rollback_id=str(uuid4()),
            resolution_id=conflict_id,
            success=True,
            restored_state=previous_state,
        )

    def _transition_state(self, new_state: FSAState):
        """Transition to a new FSA state."""
        if self.debug_mode:
            logger.debug(f"FSA state transition: {self.state} -> {new_state}")
        self.state = new_state

    def reset(self):
        """Reset the FSA to initial state."""
        self.state = FSAState.IDLE
        self.operations = []
        self.conflicts = []
        self.resolutions = []
        self.state_history = []
        logger.debug("FSA reset to initial state")
