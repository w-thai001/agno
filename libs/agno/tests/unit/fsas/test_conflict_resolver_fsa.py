"""
Unit tests for ConflictResolverFSA.

Tests cover:
- Basic conflict detection and classification
- Resource conflict resolution
- Data conflict reconciliation
- Timing/scheduling conflict resolution
- Priority-based resolution
- Multi-party negotiation
- Rollback scenarios
- Edge cases (unresolvable conflicts, circular conflicts)
- Error handling scenarios
- Complex multi-conflict scenarios
"""

import pytest
from unittest.mock import patch

from agno.fsas.conflict_resolver_fsa import (
    ConflictResolverFSA,
    Conflict,
    ConflictType,
    Resolution,
    ResolutionStrategy,
    ConflictScenario,
    ValidationResult,
    Operation,
    ResourceConflict,
    DataConflict,
    TimingConflict,
    ResourceAllocation,
    DataState,
    Schedule,
    PriorityRules,
    ResolutionPlan,
    Agent,
    NegotiatedResolution,
    RollbackResult,
    FSAState,
)


class TestConflictDetectionAndClassification:
    """Tests for basic conflict detection and classification."""

    def test_detect_resource_conflicts(self):
        """Test detection of resource allocation conflicts."""
        fsa = ConflictResolverFSA()

        # Create operations that compete for the same resource
        operations = [
            Operation(
                operation_id="op1",
                agent_id="agent1",
                operation_type="use",
                resource_ids=["resource_a"],
                priority=1,
            ),
            Operation(
                operation_id="op2",
                agent_id="agent2",
                operation_type="use",
                resource_ids=["resource_a"],
                priority=2,
            ),
            Operation(
                operation_id="op3",
                agent_id="agent3",
                operation_type="use",
                resource_ids=["resource_b"],
                priority=1,
            ),
        ]

        conflicts = fsa.detect_conflicts(operations)

        # Should detect one conflict for resource_a
        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == ConflictType.RESOURCE
        assert isinstance(conflicts[0], ResourceConflict)
        assert conflicts[0].resource_id == "resource_a"
        assert len(conflicts[0].requested_by) == 2

    def test_detect_data_conflicts(self):
        """Test detection of data inconsistency conflicts."""
        fsa = ConflictResolverFSA()

        operations = [
            Operation(
                operation_id="op1",
                agent_id="agent1",
                operation_type="write",
                data_keys=["key1"],
                metadata={"value": "value_a"},
            ),
            Operation(
                operation_id="op2",
                agent_id="agent2",
                operation_type="write",
                data_keys=["key1"],
                metadata={"value": "value_b"},
            ),
            Operation(
                operation_id="op3",
                agent_id="agent3",
                operation_type="read",
                data_keys=["key1"],
            ),
        ]

        conflicts = fsa.detect_conflicts(operations)

        # Should detect one data conflict
        data_conflicts = [c for c in conflicts if c.conflict_type == ConflictType.DATA]
        assert len(data_conflicts) == 1
        assert isinstance(data_conflicts[0], DataConflict)
        assert data_conflicts[0].data_key == "key1"

    def test_detect_timing_conflicts(self):
        """Test detection of timing/scheduling conflicts."""
        fsa = ConflictResolverFSA()

        operations = [
            Operation(
                operation_id="op1",
                agent_id="agent1",
                operation_type="execute",
                resource_ids=["resource_a"],
                timestamp=1.0,
            ),
            Operation(
                operation_id="op2",
                agent_id="agent2",
                operation_type="execute",
                resource_ids=["resource_a"],
                timestamp=1.5,  # Overlaps with op1
            ),
        ]

        conflicts = fsa.detect_conflicts(operations)

        # Should detect both resource and timing conflict
        timing_conflicts = [c for c in conflicts if c.conflict_type == ConflictType.TIMING]
        assert len(timing_conflicts) >= 1

    def test_classify_conflict(self):
        """Test conflict classification."""
        fsa = ConflictResolverFSA()

        # Test resource conflict classification
        resource_conflict = ResourceConflict(
            conflict_id="c1",
            conflict_type=ConflictType.RESOURCE,
            involved_agents=["agent1", "agent2"],
            involved_operations=["op1", "op2"],
            resource_id="resource_a",
        )

        assert fsa.classify_conflict(resource_conflict) == ConflictType.RESOURCE

        # Test data conflict classification
        data_conflict = DataConflict(
            conflict_id="c2",
            conflict_type=ConflictType.DATA,
            involved_agents=["agent1", "agent2"],
            involved_operations=["op1", "op2"],
            data_key="key1",
        )

        assert fsa.classify_conflict(data_conflict) == ConflictType.DATA

        # Test circular dependency classification
        circular_conflict = Conflict(
            conflict_id="c3",
            conflict_type=ConflictType.UNKNOWN,
            involved_agents=["agent1"],
            involved_operations=["op1", "op2"],
            metadata={"circular_dependency": True},
        )

        assert fsa.classify_conflict(circular_conflict) == ConflictType.CIRCULAR


class TestResourceConflictResolution:
    """Tests for resource conflict resolution."""

    def test_resolve_resource_conflict_priority_based(self):
        """Test priority-based resource allocation."""
        fsa = ConflictResolverFSA()
        fsa.priority_rules = PriorityRules(
            agent_priorities={"agent1": 10, "agent2": 5},
            preemption_enabled=True,
        )

        conflict = ResourceConflict(
            conflict_id="c1",
            conflict_type=ConflictType.RESOURCE,
            involved_agents=["agent1", "agent2"],
            involved_operations=["op1", "op2"],
            resource_id="resource_a",
            requested_by=["agent1", "agent2"],
            available_capacity=1.0,
            metadata={"agent1_requested": 0.6, "agent2_requested": 0.6},
        )

        allocation = fsa.resolve_resource_conflict(conflict)

        # Higher priority agent should get allocation
        assert "agent1" in allocation.allocations
        assert allocation.allocations["agent1"] == 0.6
        assert "agent2" in allocation.denied

    def test_resolve_resource_conflict_fair_share(self):
        """Test fair-share resource allocation."""
        fsa = ConflictResolverFSA()
        fsa.priority_rules = PriorityRules(
            agent_priorities={"agent1": 10, "agent2": 5},
            preemption_enabled=False,
            fairness_weight=0.8,  # High fairness
        )

        conflict = ResourceConflict(
            conflict_id="c1",
            conflict_type=ConflictType.RESOURCE,
            involved_agents=["agent1", "agent2"],
            involved_operations=["op1", "op2"],
            resource_id="resource_a",
            requested_by=["agent1", "agent2"],
            available_capacity=2.0,
            metadata={"agent1_requested": 1.0, "agent2_requested": 1.0},
        )

        allocation = fsa.resolve_resource_conflict(conflict)

        # Both should get some allocation
        assert len(allocation.allocations) >= 1
        assert allocation.resource_id == "resource_a"


class TestDataConflictResolution:
    """Tests for data conflict reconciliation."""

    def test_resolve_data_conflict_version_based(self):
        """Test version-based data conflict resolution."""
        fsa = ConflictResolverFSA()

        conflict = DataConflict(
            conflict_id="c1",
            conflict_type=ConflictType.DATA,
            involved_agents=["agent1", "agent2"],
            involved_operations=["op1", "op2"],
            data_key="shared_data",
            conflicting_values={"agent1": "value_a", "agent2": "value_b"},
            versions=[1, 2],
            metadata={"agent1_version": 1, "agent2_version": 2},
        )

        data_state = fsa.resolve_data_conflict(conflict)

        # Should select value with highest version
        assert data_state.data_key == "shared_data"
        assert data_state.resolved_value == "value_b"
        assert data_state.version == 3  # Increment version

    def test_resolve_data_conflict_no_version(self):
        """Test data conflict resolution without version info."""
        fsa = ConflictResolverFSA()

        conflict = DataConflict(
            conflict_id="c1",
            conflict_type=ConflictType.DATA,
            involved_agents=["agent1", "agent2"],
            involved_operations=["op1", "op2"],
            data_key="shared_data",
            conflicting_values={"agent1": "value_a", "agent2": "value_b"},
        )

        data_state = fsa.resolve_data_conflict(conflict)

        # Should still produce a resolution
        assert data_state.data_key == "shared_data"
        assert data_state.resolved_value in ["value_a", "value_b"]


class TestTimingConflictResolution:
    """Tests for timing/scheduling conflict resolution."""

    def test_resolve_timing_conflict(self):
        """Test timing conflict resolution with priority-based scheduling."""
        fsa = ConflictResolverFSA()
        fsa.priority_rules = PriorityRules(
            operation_priorities={"op1": 10, "op2": 5, "op3": 8},
        )

        conflict = TimingConflict(
            conflict_id="c1",
            conflict_type=ConflictType.TIMING,
            involved_agents=["agent1", "agent2", "agent3"],
            involved_operations=["op1", "op2", "op3"],
            competing_operations=["op1", "op2", "op3"],
            time_slot=(0.0, 10.0),
            resource_id="resource_a",
        )

        schedule = fsa.resolve_timing_conflict(conflict)

        # Should create time slots for all operations
        assert len(schedule.time_slots) == 3
        assert "op1" in schedule.time_slots
        assert "op2" in schedule.time_slots
        assert "op3" in schedule.time_slots

        # Higher priority operation should get earlier slot
        assert schedule.time_slots["op1"][0] < schedule.time_slots["op2"][0]


class TestPriorityBasedResolution:
    """Tests for priority-based conflict resolution."""

    def test_apply_priority_rules(self):
        """Test applying priority rules to multiple conflicts."""
        fsa = ConflictResolverFSA()

        conflicts = [
            Conflict(
                conflict_id="c1",
                conflict_type=ConflictType.RESOURCE,
                involved_agents=["agent1"],
                involved_operations=["op1"],
                severity=3,
            ),
            Conflict(
                conflict_id="c2",
                conflict_type=ConflictType.DATA,
                involved_agents=["agent2"],
                involved_operations=["op2"],
                severity=8,
            ),
            Conflict(
                conflict_id="c3",
                conflict_type=ConflictType.TIMING,
                involved_agents=["agent3"],
                involved_operations=["op3"],
                severity=5,
            ),
        ]

        rules = PriorityRules(
            agent_priorities={"agent1": 1, "agent2": 10, "agent3": 5},
        )

        plan = fsa.apply_priority_rules(conflicts, rules)

        # Should create a resolution plan
        assert plan.strategy == ResolutionStrategy.PRIORITY_BASED
        assert len(plan.steps) == 3
        assert len(plan.conflicts) == 3

        # Should order by severity (highest first)
        assert "c2" in plan.steps[0]  # Severity 8


class TestMultiPartyNegotiation:
    """Tests for multi-party conflict negotiation."""

    def test_negotiate_solution_resource_conflict(self):
        """Test negotiation for resource conflicts."""
        fsa = ConflictResolverFSA()

        parties = [
            Agent(agent_id="agent1", name="Agent 1", priority=10),
            Agent(agent_id="agent2", name="Agent 2", priority=5),
            Agent(agent_id="agent3", name="Agent 3", priority=8),
        ]

        conflict = Conflict(
            conflict_id="c1",
            conflict_type=ConflictType.RESOURCE,
            involved_agents=["agent1", "agent2", "agent3"],
            involved_operations=["op1", "op2", "op3"],
        )

        resolution = fsa.negotiate_solution(parties, conflict)

        # Should produce a negotiated resolution
        assert resolution.resolution_id is not None
        assert len(resolution.participating_agents) == 3
        assert len(resolution.agreed_terms) > 0
        assert 0.0 <= resolution.consensus_level <= 1.0

    def test_negotiate_solution_data_conflict(self):
        """Test negotiation for data conflicts."""
        fsa = ConflictResolverFSA()

        parties = [
            Agent(agent_id="agent1", name="Agent 1", priority=10, state={"data_key": "value_a"}),
            Agent(agent_id="agent2", name="Agent 2", priority=5, state={"data_key": "value_b"}),
        ]

        conflict = Conflict(
            conflict_id="c1",
            conflict_type=ConflictType.DATA,
            involved_agents=["agent1", "agent2"],
            involved_operations=["op1", "op2"],
            metadata={"data_key": "data_key"},
        )

        resolution = fsa.negotiate_solution(parties, conflict)

        # Should produce agreed terms
        assert "data_value" in resolution.agreed_terms
        assert len(resolution.compromises) > 0


class TestRollbackScenarios:
    """Tests for rollback functionality."""

    def test_rollback_on_failure(self):
        """Test rollback when resolution fails."""
        fsa = ConflictResolverFSA(enable_rollback=True)

        # Set up initial state
        fsa.resources["resource_a"] = {"capacity": 10.0, "allocations": {}}
        fsa.data_store["key1"] = {"value": "initial", "version": 1}
        fsa._save_state()

        # Modify state
        fsa.resources["resource_a"]["allocations"] = {"agent1": 5.0}
        fsa.data_store["key1"] = {"value": "modified", "version": 2}

        # Create a failed resolution
        resolution = Resolution(
            resolution_id="r1",
            conflict_id="c1",
            strategy=ResolutionStrategy.ROLLBACK,
            success=False,
        )

        # Rollback
        rollback_result = fsa.rollback_on_failure(resolution)

        # Should restore previous state
        assert rollback_result.success
        assert fsa.data_store["key1"]["value"] == "initial"

    def test_rollback_without_history(self):
        """Test rollback when no history is available."""
        fsa = ConflictResolverFSA(enable_rollback=True)

        resolution = Resolution(
            resolution_id="r1",
            conflict_id="c1",
            strategy=ResolutionStrategy.ROLLBACK,
            success=False,
        )

        rollback_result = fsa.rollback_on_failure(resolution)

        # Should fail gracefully
        assert not rollback_result.success
        assert rollback_result.error_message is not None


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_circular_dependency_detection(self):
        """Test detection of circular dependencies."""
        fsa = ConflictResolverFSA()

        # Create circular dependency: op1 -> op2 -> op3 -> op1
        operations = [
            Operation(operation_id="op1", agent_id="agent1", operation_type="task", dependencies=["op2"]),
            Operation(operation_id="op2", agent_id="agent2", operation_type="task", dependencies=["op3"]),
            Operation(operation_id="op3", agent_id="agent3", operation_type="task", dependencies=["op1"]),
        ]

        conflicts = fsa.detect_conflicts(operations)

        # Should detect circular dependency
        circular_conflicts = [c for c in conflicts if c.conflict_type == ConflictType.CIRCULAR]
        assert len(circular_conflicts) > 0

    def test_unresolvable_conflict_handling(self):
        """Test handling of unresolvable conflicts."""
        fsa = ConflictResolverFSA(enable_rollback=False, max_retries=1)

        # Create a conflict that will fail resolution
        conflict = Conflict(
            conflict_id="c1",
            conflict_type=ConflictType.UNKNOWN,
            involved_agents=[],
            involved_operations=[],
        )

        # Mock resolution to always fail
        with patch.object(fsa, "_resolve_by_type", side_effect=Exception("Resolution failed")):
            with pytest.raises(RuntimeError):
                fsa.execute(conflict)

    def test_empty_operations_list(self):
        """Test conflict detection with empty operations list."""
        fsa = ConflictResolverFSA()

        conflicts = fsa.detect_conflicts([])

        # Should return empty list
        assert len(conflicts) == 0

    def test_single_operation_no_conflict(self):
        """Test that single operation produces no conflicts."""
        fsa = ConflictResolverFSA()

        operations = [
            Operation(
                operation_id="op1",
                agent_id="agent1",
                operation_type="use",
                resource_ids=["resource_a"],
            )
        ]

        conflicts = fsa.detect_conflicts(operations)

        # Should detect no conflicts
        assert len(conflicts) == 0


class TestErrorHandling:
    """Tests for error handling scenarios."""

    def test_execute_with_invalid_conflict(self):
        """Test execute method with invalid conflict."""
        fsa = ConflictResolverFSA()

        with pytest.raises(ValueError):
            fsa.execute(None)

    def test_resolution_validation_failure(self):
        """Test resolution validation with over-allocated resources."""
        fsa = ConflictResolverFSA()
        fsa.resources["resource_a"] = {"capacity": 1.0}

        # Create resolution that exceeds capacity
        resolution = Resolution(
            resolution_id="r1",
            conflict_id="c1",
            strategy=ResolutionStrategy.FAIR_SHARE,
            success=True,
            resource_allocations=[
                ResourceAllocation(
                    resource_id="resource_a",
                    allocations={"agent1": 0.6, "agent2": 0.6},  # Total = 1.2 > 1.0
                )
            ],
        )

        # Validation should fail
        assert not fsa._validate_resolution(resolution)

    def test_state_transitions(self):
        """Test FSA state transitions."""
        fsa = ConflictResolverFSA(debug_mode=True)

        assert fsa.state == FSAState.IDLE

        fsa._transition_state(FSAState.DETECTING)
        assert fsa.state == FSAState.DETECTING

        fsa._transition_state(FSAState.RESOLVING)
        assert fsa.state == FSAState.RESOLVING


class TestComplexMultiConflictScenarios:
    """Tests for complex scenarios with multiple conflicts."""

    def test_multiple_conflict_types(self):
        """Test scenario with multiple types of conflicts."""
        fsa = ConflictResolverFSA()

        operations = [
            Operation(
                operation_id="op1",
                agent_id="agent1",
                operation_type="write",
                resource_ids=["resource_a"],
                data_keys=["key1"],
                timestamp=1.0,
                metadata={"value": "value_a"},
            ),
            Operation(
                operation_id="op2",
                agent_id="agent2",
                operation_type="write",
                resource_ids=["resource_a"],
                data_keys=["key1"],
                timestamp=1.5,
                metadata={"value": "value_b"},
            ),
        ]

        conflicts = fsa.detect_conflicts(operations)

        # Should detect multiple types
        conflict_types = {c.conflict_type for c in conflicts}
        assert ConflictType.RESOURCE in conflict_types
        assert ConflictType.DATA in conflict_types

    def test_validation_scenario(self):
        """Test conflict validation with expected results."""
        fsa = ConflictResolverFSA()

        scenario = ConflictScenario(
            scenario_id="scenario1",
            operations=[
                Operation(
                    operation_id="op1",
                    agent_id="agent1",
                    operation_type="use",
                    resource_ids=["resource_a"],
                ),
                Operation(
                    operation_id="op2",
                    agent_id="agent2",
                    operation_type="use",
                    resource_ids=["resource_a"],
                ),
            ],
            expected_conflicts=[ConflictType.RESOURCE],
        )

        result = fsa.validate(scenario)

        # Should correctly identify resource conflict
        assert result.true_positives >= 1
        assert result.false_negatives == 0
        assert result.accuracy > 0.5

    def test_full_resolution_pipeline(self):
        """Test complete resolution pipeline from detection to application."""
        fsa = ConflictResolverFSA(enable_rollback=True)
        fsa.agents = {
            "agent1": Agent(agent_id="agent1", name="Agent 1", priority=10),
            "agent2": Agent(agent_id="agent2", name="Agent 2", priority=5),
        }
        fsa.resources["resource_a"] = {"capacity": 10.0}
        fsa.priority_rules = PriorityRules(
            agent_priorities={"agent1": 10, "agent2": 5},
            preemption_enabled=True,
        )

        conflict = ResourceConflict(
            conflict_id="c1",
            conflict_type=ConflictType.RESOURCE,
            involved_agents=["agent1", "agent2"],
            involved_operations=["op1", "op2"],
            resource_id="resource_a",
            requested_by=["agent1", "agent2"],
            available_capacity=10.0,
            metadata={"agent1_requested": 6.0, "agent2_requested": 6.0},
        )

        resolution = fsa.execute(conflict)

        # Should successfully resolve
        assert resolution.success
        assert len(resolution.resource_allocations) > 0
        assert fsa.state == FSAState.COMPLETED

    def test_reset_functionality(self):
        """Test FSA reset functionality."""
        fsa = ConflictResolverFSA()

        # Add some state
        fsa.operations = [Operation(operation_id="op1", agent_id="agent1", operation_type="test")]
        fsa.conflicts = [
            Conflict(
                conflict_id="c1",
                conflict_type=ConflictType.RESOURCE,
                involved_agents=["agent1"],
                involved_operations=["op1"],
            )
        ]
        fsa.state = FSAState.RESOLVING

        # Reset
        fsa.reset()

        # Should clear state
        assert fsa.state == FSAState.IDLE
        assert len(fsa.operations) == 0
        assert len(fsa.conflicts) == 0
        assert len(fsa.resolutions) == 0
