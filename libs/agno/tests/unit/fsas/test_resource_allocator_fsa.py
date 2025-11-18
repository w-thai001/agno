"""
Unit tests for Resource Allocator FSA.

Tests cover:
- Basic resource allocation
- Fair-share allocation strategy
- Priority-based allocation
- Demand-based allocation
- Resource monitoring
- Quota enforcement
- Dynamic rebalancing
- Resource contention resolution
- Idle resource reclamation
- Prediction accuracy
- Edge cases
- Error handling
"""

from datetime import datetime, timedelta

import pytest

from agno.fsas.resource_allocator_fsa import (
    Agent,
    AllocationRequest,
    AllocationState,
    AllocationStrategy,
    DemandForecast,
    EnforcementResult,
    FSAState,
    OptimizationResult,
    Quotas,
    RebalanceResult,
    ReclaimResult,
    Resolution,
    ResourceAllocatorFSA,
    ResourceAllocation,
    ResourceConflict,
    ResourcePool,
    Resources,
    ResourceUsage,
    ValidationResult,
)


class TestResourceAllocatorFSABasics:
    """Test basic functionality of Resource Allocator FSA."""

    def test_initialization(self):
        """Test FSA initialization with resource pool."""
        total_resources = Resources(
            cpu_cores=16.0, memory_mb=32768.0, tokens=100000, api_quota=1000
        )
        fsa = ResourceAllocatorFSA(total_resources=total_resources)

        assert fsa.resource_pool.total == total_resources
        assert fsa.state == FSAState.IDLE
        assert fsa.allocation_count == 0
        assert len(fsa.allocations) == 0

    def test_resources_arithmetic(self):
        """Test resource arithmetic operations."""
        r1 = Resources(cpu_cores=4.0, memory_mb=8192.0, tokens=1000, api_quota=100)
        r2 = Resources(cpu_cores=2.0, memory_mb=4096.0, tokens=500, api_quota=50)

        # Addition
        r3 = r1 + r2
        assert r3.cpu_cores == 6.0
        assert r3.memory_mb == 12288.0
        assert r3.tokens == 1500
        assert r3.api_quota == 150

        # Subtraction
        r4 = r1 - r2
        assert r4.cpu_cores == 2.0
        assert r4.memory_mb == 4096.0
        assert r4.tokens == 500
        assert r4.api_quota == 50

        # Multiplication
        r5 = r1 * 2.0
        assert r5.cpu_cores == 8.0
        assert r5.memory_mb == 16384.0
        assert r5.tokens == 2000
        assert r5.api_quota == 200

    def test_resource_sufficiency(self):
        """Test resource sufficiency checking."""
        available = Resources(
            cpu_cores=8.0, memory_mb=16384.0, tokens=5000, api_quota=500
        )
        required = Resources(
            cpu_cores=4.0, memory_mb=8192.0, tokens=2000, api_quota=200
        )
        excessive = Resources(
            cpu_cores=10.0, memory_mb=20000.0, tokens=6000, api_quota=600
        )

        assert available.is_sufficient(required)
        assert not available.is_sufficient(excessive)

    def test_basic_resource_allocation(self):
        """Test basic resource allocation across agents."""
        total_resources = Resources(
            cpu_cores=16.0, memory_mb=32768.0, tokens=100000, api_quota=1000
        )
        fsa = ResourceAllocatorFSA(total_resources=total_resources)

        # Create agents
        agent1 = Agent(
            agent_id="agent-1",
            name="Agent 1",
            priority=5,
            min_resources=Resources(
                cpu_cores=2.0, memory_mb=4096.0, tokens=10000, api_quota=100
            ),
        )
        agent2 = Agent(
            agent_id="agent-2",
            name="Agent 2",
            priority=5,
            min_resources=Resources(
                cpu_cores=2.0, memory_mb=4096.0, tokens=10000, api_quota=100
            ),
        )

        # Create allocation request
        request = AllocationRequest(
            agents=[agent1, agent2], strategy=AllocationStrategy.FAIR_SHARE
        )

        # Execute allocation
        result = fsa.execute(request)

        assert result.success
        assert len(result.allocations) == 2
        assert "agent-1" in result.allocations
        assert "agent-2" in result.allocations
        assert fsa.allocation_count == 1


class TestAllocationStrategies:
    """Test different allocation strategies."""

    def test_fair_share_allocation(self):
        """Test fair-share allocation strategy."""
        total_resources = Resources(
            cpu_cores=10.0, memory_mb=20000.0, tokens=50000, api_quota=500
        )
        fsa = ResourceAllocatorFSA(total_resources=total_resources)

        # Create agents with equal priority
        agents = [
            Agent(
                agent_id=f"agent-{i}",
                name=f"Agent {i}",
                priority=5,
                min_resources=Resources(
                    cpu_cores=1.0, memory_mb=2000.0, tokens=5000, api_quota=50
                ),
            )
            for i in range(5)
        ]

        request = AllocationRequest(
            agents=agents, strategy=AllocationStrategy.FAIR_SHARE
        )

        result = fsa.execute(request)

        assert result.success
        assert len(result.allocations) == 5

        # Each agent should get approximately equal resources
        for agent_id, resources in result.allocations.items():
            assert resources.cpu_cores >= 1.0  # At least minimum
            assert resources.memory_mb >= 2000.0

    def test_priority_based_allocation(self):
        """Test priority-based allocation strategy."""
        total_resources = Resources(
            cpu_cores=10.0, memory_mb=20000.0, tokens=50000, api_quota=500
        )
        fsa = ResourceAllocatorFSA(total_resources=total_resources)

        # Create agents with different priorities
        high_priority = Agent(
            agent_id="high-priority",
            name="High Priority",
            priority=10,
            min_resources=Resources(
                cpu_cores=1.0, memory_mb=2000.0, tokens=5000, api_quota=50
            ),
        )
        low_priority = Agent(
            agent_id="low-priority",
            name="Low Priority",
            priority=2,
            min_resources=Resources(
                cpu_cores=1.0, memory_mb=2000.0, tokens=5000, api_quota=50
            ),
        )

        # Allocate with priority strategy
        allocations = fsa._priority_allocation(
            [high_priority, low_priority], fsa.resource_pool
        )

        # High priority should get more resources
        high_alloc = allocations[high_priority]
        low_alloc = allocations[low_priority]

        assert high_alloc.cpu_cores > low_alloc.cpu_cores
        assert high_alloc.memory_mb > low_alloc.memory_mb

    def test_demand_based_allocation(self):
        """Test demand-based allocation strategy."""
        total_resources = Resources(
            cpu_cores=16.0, memory_mb=32768.0, tokens=100000, api_quota=1000
        )
        fsa = ResourceAllocatorFSA(total_resources=total_resources)

        agent = Agent(
            agent_id="agent-1",
            name="Agent 1",
            priority=5,
            min_resources=Resources(
                cpu_cores=2.0, memory_mb=4096.0, tokens=10000, api_quota=100
            ),
        )

        # Add usage history
        for i in range(10):
            usage = ResourceUsage(
                agent_id="agent-1",
                current=Resources(
                    cpu_cores=3.0, memory_mb=6000.0, tokens=15000, api_quota=150
                ),
                peak=Resources(
                    cpu_cores=4.0, memory_mb=8000.0, tokens=20000, api_quota=200
                ),
                average=Resources(
                    cpu_cores=3.0, memory_mb=6000.0, tokens=15000, api_quota=150
                ),
            )
            fsa.usage_history["agent-1"].append(usage)

        # Allocate with demand-based strategy
        allocations = fsa._demand_based_allocation([agent], fsa.resource_pool)

        # Should allocate based on history with buffer
        alloc = allocations[agent]
        assert alloc.cpu_cores >= 3.0  # At least average
        assert alloc.memory_mb >= 6000.0


class TestValidation:
    """Test allocation request validation."""

    def test_valid_request(self):
        """Test validation of valid allocation request."""
        total_resources = Resources(
            cpu_cores=16.0, memory_mb=32768.0, tokens=100000, api_quota=1000
        )
        fsa = ResourceAllocatorFSA(total_resources=total_resources)

        agent = Agent(
            agent_id="agent-1",
            name="Agent 1",
            priority=5,
            min_resources=Resources(
                cpu_cores=2.0, memory_mb=4096.0, tokens=10000, api_quota=100
            ),
        )

        request = AllocationRequest(agents=[agent])
        validation = fsa.validate(request)

        assert validation.valid
        assert len(validation.errors) == 0

    def test_insufficient_resources(self):
        """Test validation with insufficient resources."""
        total_resources = Resources(
            cpu_cores=2.0, memory_mb=4096.0, tokens=10000, api_quota=100
        )
        fsa = ResourceAllocatorFSA(total_resources=total_resources)

        # Request more than available
        agent = Agent(
            agent_id="agent-1",
            name="Agent 1",
            priority=5,
            min_resources=Resources(
                cpu_cores=10.0, memory_mb=40960.0, tokens=100000, api_quota=1000
            ),
        )

        request = AllocationRequest(agents=[agent])
        validation = fsa.validate(request)

        assert not validation.valid
        assert len(validation.errors) > 0
        assert "Insufficient resources" in validation.errors[0]

    def test_negative_resources(self):
        """Test validation with negative resource requests."""
        total_resources = Resources(
            cpu_cores=16.0, memory_mb=32768.0, tokens=100000, api_quota=1000
        )
        fsa = ResourceAllocatorFSA(total_resources=total_resources)

        agent = Agent(
            agent_id="agent-1",
            name="Agent 1",
            priority=5,
            min_resources=Resources(
                cpu_cores=-2.0, memory_mb=4096.0, tokens=10000, api_quota=100
            ),
        )

        request = AllocationRequest(agents=[agent])
        validation = fsa.validate(request)

        assert not validation.valid
        assert any("negative" in error.lower() for error in validation.errors)

    def test_empty_agents_list(self):
        """Test validation with empty agents list."""
        total_resources = Resources(
            cpu_cores=16.0, memory_mb=32768.0, tokens=100000, api_quota=1000
        )
        fsa = ResourceAllocatorFSA(total_resources=total_resources)

        request = AllocationRequest(agents=[])
        validation = fsa.validate(request)

        assert not validation.valid
        assert "No agents specified" in validation.errors[0]

    def test_duplicate_agent_ids(self):
        """Test validation with duplicate agent IDs."""
        total_resources = Resources(
            cpu_cores=16.0, memory_mb=32768.0, tokens=100000, api_quota=1000
        )
        fsa = ResourceAllocatorFSA(total_resources=total_resources)

        agent1 = Agent(
            agent_id="agent-1",
            name="Agent 1",
            priority=5,
            min_resources=Resources(
                cpu_cores=2.0, memory_mb=4096.0, tokens=10000, api_quota=100
            ),
        )
        agent2 = Agent(
            agent_id="agent-1",  # Duplicate ID
            name="Agent 2",
            priority=5,
            min_resources=Resources(
                cpu_cores=2.0, memory_mb=4096.0, tokens=10000, api_quota=100
            ),
        )

        request = AllocationRequest(agents=[agent1, agent2])
        validation = fsa.validate(request)

        assert not validation.valid
        assert any("Duplicate" in error for error in validation.errors)


class TestMonitoring:
    """Test resource monitoring and tracking."""

    def test_monitor_usage(self):
        """Test real-time usage monitoring."""
        total_resources = Resources(
            cpu_cores=16.0, memory_mb=32768.0, tokens=100000, api_quota=1000
        )
        fsa = ResourceAllocatorFSA(total_resources=total_resources)

        agent = Agent(
            agent_id="agent-1",
            name="Agent 1",
            priority=5,
            min_resources=Resources(
                cpu_cores=2.0, memory_mb=4096.0, tokens=10000, api_quota=100
            ),
        )

        request = AllocationRequest(agents=[agent])
        result = fsa.execute(request)

        # Monitor usage
        usage = fsa.monitor_usage("agent-1")

        assert usage.agent_id == "agent-1"
        assert usage.current.cpu_cores >= 0
        assert usage.utilization_percent >= 0

    def test_usage_history(self):
        """Test usage history tracking."""
        total_resources = Resources(
            cpu_cores=16.0, memory_mb=32768.0, tokens=100000, api_quota=1000
        )
        fsa = ResourceAllocatorFSA(total_resources=total_resources)

        agent = Agent(
            agent_id="agent-1",
            name="Agent 1",
            priority=5,
            min_resources=Resources(
                cpu_cores=2.0, memory_mb=4096.0, tokens=10000, api_quota=100
            ),
        )

        request = AllocationRequest(agents=[agent])
        fsa.execute(request)

        # Monitor multiple times
        for _ in range(5):
            fsa.monitor_usage("agent-1")

        # Check history
        assert len(fsa.usage_history["agent-1"]) == 5


class TestQuotaEnforcement:
    """Test quota enforcement and throttling."""

    def test_quota_enforcement_within_limits(self):
        """Test quota enforcement when within limits."""
        fsa = ResourceAllocatorFSA(
            total_resources=Resources(
                cpu_cores=16.0, memory_mb=32768.0, tokens=100000, api_quota=1000
            )
        )

        usage = ResourceUsage(
            agent_id="agent-1",
            current=Resources(
                cpu_cores=4.0, memory_mb=8192.0, tokens=5000, api_quota=50
            ),
            peak=Resources(
                cpu_cores=4.0, memory_mb=8192.0, tokens=5000, api_quota=50
            ),
            average=Resources(
                cpu_cores=4.0, memory_mb=8192.0, tokens=5000, api_quota=50
            ),
        )

        limits = Quotas(
            max_cpu_percent=80.0,
            max_memory_mb=16384.0,
            max_tokens_per_minute=10000,
            max_api_calls_per_minute=100,
        )

        result = fsa.enforce_quotas(usage, limits)

        assert not result.throttled
        assert len(result.violations) == 0

    def test_quota_enforcement_violations(self):
        """Test quota enforcement with violations."""
        fsa = ResourceAllocatorFSA(
            total_resources=Resources(
                cpu_cores=16.0, memory_mb=32768.0, tokens=100000, api_quota=1000
            )
        )

        usage = ResourceUsage(
            agent_id="agent-1",
            current=Resources(
                cpu_cores=90.0, memory_mb=20000.0, tokens=15000, api_quota=150
            ),
            peak=Resources(
                cpu_cores=90.0, memory_mb=20000.0, tokens=15000, api_quota=150
            ),
            average=Resources(
                cpu_cores=90.0, memory_mb=20000.0, tokens=15000, api_quota=150
            ),
        )

        limits = Quotas(
            max_cpu_percent=80.0,
            max_memory_mb=16384.0,
            max_tokens_per_minute=10000,
            max_api_calls_per_minute=100,
        )

        result = fsa.enforce_quotas(usage, limits)

        assert result.throttled
        assert len(result.violations) > 0
        assert result.action_taken != ""


class TestDynamicRebalancing:
    """Test dynamic rebalancing of resources."""

    def test_rebalance_allocation(self):
        """Test dynamic rebalancing of allocations."""
        total_resources = Resources(
            cpu_cores=16.0, memory_mb=32768.0, tokens=100000, api_quota=1000
        )
        fsa = ResourceAllocatorFSA(total_resources=total_resources)

        # Create agents
        agent1 = Agent(
            agent_id="agent-1",
            name="Agent 1",
            priority=5,
            min_resources=Resources(
                cpu_cores=1.0, memory_mb=2048.0, tokens=5000, api_quota=50
            ),
        )
        agent2 = Agent(
            agent_id="agent-2",
            name="Agent 2",
            priority=5,
            min_resources=Resources(
                cpu_cores=1.0, memory_mb=2048.0, tokens=5000, api_quota=50
            ),
        )

        # Allocate resources
        request = AllocationRequest(agents=[agent1, agent2])
        fsa.execute(request)

        # Create allocation state with usage info
        usage1 = ResourceUsage(
            agent_id="agent-1",
            current=Resources(
                cpu_cores=1.0, memory_mb=2000.0, tokens=2000, api_quota=20
            ),
            peak=Resources(
                cpu_cores=2.0, memory_mb=4000.0, tokens=4000, api_quota=40
            ),
            average=Resources(
                cpu_cores=1.5, memory_mb=3000.0, tokens=3000, api_quota=30
            ),
            utilization_percent=30.0,  # Low utilization
        )

        usage2 = ResourceUsage(
            agent_id="agent-2",
            current=Resources(
                cpu_cores=7.0, memory_mb=14000.0, tokens=40000, api_quota=400
            ),
            peak=Resources(
                cpu_cores=8.0, memory_mb=16000.0, tokens=45000, api_quota=450
            ),
            average=Resources(
                cpu_cores=7.5, memory_mb=15000.0, tokens=42000, api_quota=420
            ),
            utilization_percent=90.0,  # High utilization
        )

        state = AllocationState(
            allocations=fsa.allocations.copy(),
            usage={"agent-1": usage1, "agent-2": usage2},
            pool=fsa.resource_pool,
        )

        # Rebalance
        result = fsa.rebalance_allocation(state)

        assert result.success
        assert fsa.rebalance_count == 1
        # Resources should be reclaimed from low-utilization agent
        assert result.reclaimed.cpu_cores > 0 or result.reclaimed.memory_mb > 0


class TestPrediction:
    """Test resource demand prediction."""

    def test_predict_demand_no_history(self):
        """Test prediction with no historical data."""
        total_resources = Resources(
            cpu_cores=16.0, memory_mb=32768.0, tokens=100000, api_quota=1000
        )
        fsa = ResourceAllocatorFSA(total_resources=total_resources)

        agent = Agent(
            agent_id="agent-1",
            name="Agent 1",
            priority=5,
            min_resources=Resources(
                cpu_cores=2.0, memory_mb=4096.0, tokens=10000, api_quota=100
            ),
        )
        fsa.agents["agent-1"] = agent

        forecast = fsa.predict_demand("agent-1", "1h")

        assert forecast.agent_id == "agent-1"
        assert forecast.confidence < 0.5  # Low confidence without history
        assert forecast.predicted_resources.cpu_cores >= 0

    def test_predict_demand_with_history(self):
        """Test prediction with historical data."""
        total_resources = Resources(
            cpu_cores=16.0, memory_mb=32768.0, tokens=100000, api_quota=1000
        )
        fsa = ResourceAllocatorFSA(total_resources=total_resources)

        # Add usage history
        for i in range(20):
            usage = ResourceUsage(
                agent_id="agent-1",
                current=Resources(
                    cpu_cores=3.0 + i * 0.1,
                    memory_mb=6000.0 + i * 100,
                    tokens=15000 + i * 100,
                    api_quota=150 + i,
                ),
                peak=Resources(
                    cpu_cores=4.0, memory_mb=8000.0, tokens=20000, api_quota=200
                ),
                average=Resources(
                    cpu_cores=3.5, memory_mb=7000.0, tokens=17000, api_quota=170
                ),
            )
            fsa.usage_history["agent-1"].append(usage)

        forecast = fsa.predict_demand("agent-1", "1h")

        assert forecast.agent_id == "agent-1"
        assert forecast.confidence > 0.5  # Higher confidence with history
        assert forecast.predicted_resources.cpu_cores > 3.0  # Should predict growth

    def test_prediction_caching(self):
        """Test prediction result caching."""
        total_resources = Resources(
            cpu_cores=16.0, memory_mb=32768.0, tokens=100000, api_quota=1000
        )
        fsa = ResourceAllocatorFSA(total_resources=total_resources)

        agent = Agent(
            agent_id="agent-1",
            name="Agent 1",
            priority=5,
            min_resources=Resources(
                cpu_cores=2.0, memory_mb=4096.0, tokens=10000, api_quota=100
            ),
        )
        fsa.agents["agent-1"] = agent

        # First prediction
        forecast1 = fsa.predict_demand("agent-1", "1h")

        # Second prediction (should use cache)
        forecast2 = fsa.predict_demand("agent-1", "1h")

        assert forecast1.predicted_resources == forecast2.predicted_resources
        assert forecast1.confidence == forecast2.confidence


class TestIdleResourceReclamation:
    """Test idle resource reclamation."""

    def test_reclaim_idle_resources(self):
        """Test reclaiming resources from idle agents."""
        total_resources = Resources(
            cpu_cores=16.0, memory_mb=32768.0, tokens=100000, api_quota=1000
        )
        fsa = ResourceAllocatorFSA(total_resources=total_resources)

        agent = Agent(
            agent_id="agent-1",
            name="Agent 1",
            priority=5,
            min_resources=Resources(
                cpu_cores=1.0, memory_mb=2048.0, tokens=5000, api_quota=50
            ),
        )

        request = AllocationRequest(agents=[agent])
        fsa.execute(request)

        # Create old usage (idle)
        old_timestamp = datetime.now() - timedelta(seconds=400)
        usage = ResourceUsage(
            agent_id="agent-1",
            current=Resources(
                cpu_cores=0.1, memory_mb=500.0, tokens=100, api_quota=10
            ),
            peak=Resources(
                cpu_cores=2.0, memory_mb=4000.0, tokens=10000, api_quota=100
            ),
            average=Resources(
                cpu_cores=1.0, memory_mb=2000.0, tokens=5000, api_quota=50
            ),
            utilization_percent=5.0,  # Very low utilization
            timestamp=old_timestamp,
        )
        fsa.current_usage["agent-1"] = usage

        # Reclaim idle resources
        result = fsa.reclaim_idle_resources(idle_threshold=300)

        assert result.success
        assert "agent-1" in result.affected_agents


class TestResourceContention:
    """Test resource contention resolution."""

    def test_handle_resource_contention(self):
        """Test handling resource conflicts."""
        total_resources = Resources(
            cpu_cores=16.0, memory_mb=32768.0, tokens=100000, api_quota=1000
        )
        fsa = ResourceAllocatorFSA(total_resources=total_resources)

        # Create agents
        agent1 = Agent(
            agent_id="agent-1", name="Agent 1", priority=8, min_resources=Resources()
        )
        agent2 = Agent(
            agent_id="agent-2", name="Agent 2", priority=3, min_resources=Resources()
        )

        fsa.agents["agent-1"] = agent1
        fsa.agents["agent-2"] = agent2

        # Create conflict
        conflict = ResourceConflict(
            conflict_id="conflict-1",
            agents=["agent-1", "agent-2"],
            resource_type="cpu",
            requested=20.0,
            available=10.0,
        )

        # Resolve conflict
        resolution = fsa.handle_resource_contention([conflict])

        assert resolution.success
        assert len(resolution.allocations) == 2
        # Higher priority agent should get more
        assert resolution.allocations["agent-1"] > resolution.allocations["agent-2"]

    def test_handle_no_conflicts(self):
        """Test handling empty conflict list."""
        total_resources = Resources(
            cpu_cores=16.0, memory_mb=32768.0, tokens=100000, api_quota=1000
        )
        fsa = ResourceAllocatorFSA(total_resources=total_resources)

        resolution = fsa.handle_resource_contention([])

        assert resolution.success
        assert len(resolution.allocations) == 0


class TestOptimization:
    """Test resource optimization."""

    def test_optimize_efficiency_underutilized(self):
        """Test optimization for underutilized resources."""
        total_resources = Resources(
            cpu_cores=16.0, memory_mb=32768.0, tokens=100000, api_quota=1000
        )
        fsa = ResourceAllocatorFSA(total_resources=total_resources)

        allocation = ResourceAllocation(
            agent_id="agent-1",
            allocated=Resources(
                cpu_cores=8.0, memory_mb=16384.0, tokens=50000, api_quota=500
            ),
            requested=Resources(
                cpu_cores=2.0, memory_mb=4096.0, tokens=10000, api_quota=100
            ),
            utilization=30.0,  # Underutilized
        )

        result = fsa.optimize_efficiency(allocation)

        assert result.efficiency_gain > 0
        assert len(result.recommendations) > 0
        assert fsa.optimization_count == 1

    def test_optimize_efficiency_overutilized(self):
        """Test optimization for overutilized resources."""
        total_resources = Resources(
            cpu_cores=16.0, memory_mb=32768.0, tokens=100000, api_quota=1000
        )
        fsa = ResourceAllocatorFSA(total_resources=total_resources)

        allocation = ResourceAllocation(
            agent_id="agent-1",
            allocated=Resources(
                cpu_cores=4.0, memory_mb=8192.0, tokens=20000, api_quota=200
            ),
            requested=Resources(
                cpu_cores=2.0, memory_mb=4096.0, tokens=10000, api_quota=100
            ),
            utilization=95.0,  # Overutilized
        )

        result = fsa.optimize_efficiency(allocation)

        assert len(result.recommendations) > 0


class TestMetrics:
    """Test metrics and state management."""

    def test_get_metrics(self):
        """Test retrieving performance metrics."""
        total_resources = Resources(
            cpu_cores=16.0, memory_mb=32768.0, tokens=100000, api_quota=1000
        )
        fsa = ResourceAllocatorFSA(total_resources=total_resources)

        metrics = fsa.get_metrics()

        assert "allocation_count" in metrics
        assert "rebalance_count" in metrics
        assert "optimization_count" in metrics
        assert "total_allocated" in metrics
        assert "total_available" in metrics
        assert "active_agents" in metrics
        assert "state" in metrics

    def test_get_allocation_state(self):
        """Test retrieving current allocation state."""
        total_resources = Resources(
            cpu_cores=16.0, memory_mb=32768.0, tokens=100000, api_quota=1000
        )
        fsa = ResourceAllocatorFSA(total_resources=total_resources)

        agent = Agent(
            agent_id="agent-1",
            name="Agent 1",
            priority=5,
            min_resources=Resources(
                cpu_cores=2.0, memory_mb=4096.0, tokens=10000, api_quota=100
            ),
        )

        request = AllocationRequest(agents=[agent])
        fsa.execute(request)

        state = fsa.get_allocation_state()

        assert isinstance(state, AllocationState)
        assert len(state.allocations) == 1
        assert state.pool == fsa.resource_pool


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_resource_exhaustion(self):
        """Test handling complete resource exhaustion."""
        total_resources = Resources(
            cpu_cores=2.0, memory_mb=4096.0, tokens=10000, api_quota=100
        )
        fsa = ResourceAllocatorFSA(total_resources=total_resources)

        # Create multiple agents that exceed capacity
        agents = [
            Agent(
                agent_id=f"agent-{i}",
                name=f"Agent {i}",
                priority=5,
                min_resources=Resources(
                    cpu_cores=2.0, memory_mb=4096.0, tokens=10000, api_quota=100
                ),
            )
            for i in range(5)
        ]

        request = AllocationRequest(agents=agents)
        result = fsa.execute(request)

        # Should fail due to insufficient resources
        assert not result.success

    def test_zero_resources(self):
        """Test allocation with zero resources."""
        total_resources = Resources(
            cpu_cores=0.0, memory_mb=0.0, tokens=0, api_quota=0
        )
        fsa = ResourceAllocatorFSA(total_resources=total_resources)

        agent = Agent(
            agent_id="agent-1",
            name="Agent 1",
            priority=5,
            min_resources=Resources(
                cpu_cores=1.0, memory_mb=2048.0, tokens=5000, api_quota=50
            ),
        )

        request = AllocationRequest(agents=[agent])
        result = fsa.execute(request)

        assert not result.success

    def test_invalid_agent_priority(self):
        """Test agent with invalid priority."""
        with pytest.raises(ValueError):
            Agent(
                agent_id="agent-1",
                name="Agent 1",
                priority=15,  # Invalid (> 10)
                min_resources=Resources(),
            )

    def test_monitor_nonexistent_agent(self):
        """Test monitoring non-existent agent."""
        total_resources = Resources(
            cpu_cores=16.0, memory_mb=32768.0, tokens=100000, api_quota=1000
        )
        fsa = ResourceAllocatorFSA(total_resources=total_resources)

        with pytest.raises(ValueError):
            fsa.monitor_usage("nonexistent-agent")
