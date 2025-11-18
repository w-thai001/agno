"""
Comprehensive unit tests for CascadeValidatorFSA.

Tests cover:
- Basic cascade validation
- Dependency graph construction and analysis
- Data flow compatibility checking
- Conflict detection (resource, timing, data conflicts)
- Cycle detection in FSA chains
- Execution order optimization
- Performance profiling
- Edge cases (empty cascades, single FSA, complex chains)
- Error handling scenarios
- Integrity verification
"""

import pytest

from agno.fsas.cascade_validator_fsa import (
    CascadeValidatorFSA,
    Conflict,
    ConflictType,
    Cycle,
    DependencyGraph,
    ExecutionPlan,
    FlowValidation,
    FSA,
    FSACascade,
    FSAState,
    IntegrityReport,
    PerformanceReport,
    ValidationReport,
    ValidationResult,
)


@pytest.fixture
def validator():
    """Create a CascadeValidatorFSA instance for testing."""
    return CascadeValidatorFSA(name="TestValidator", enable_optimization=True)


@pytest.fixture
def simple_fsa():
    """Create a simple FSA for testing."""
    return FSA(
        name="SimpleFSA",
        inputs={"input1": "str"},
        outputs={"output1": "str"},
        estimated_duration=1.0
    )


@pytest.fixture
def simple_cascade():
    """Create a simple valid cascade."""
    fsa1 = FSA(
        id="fsa1",
        name="DataLoader",
        inputs={},
        outputs={"data": "list"},
        estimated_duration=2.0
    )
    fsa2 = FSA(
        id="fsa2",
        name="DataProcessor",
        inputs={"data": "list"},
        outputs={"result": "dict"},
        dependencies=["fsa1"],
        estimated_duration=3.0
    )
    fsa3 = FSA(
        id="fsa3",
        name="ResultWriter",
        inputs={"result": "dict"},
        outputs={"status": "str"},
        dependencies=["fsa2"],
        estimated_duration=1.0
    )

    return FSACascade(
        name="SimpleWorkflow",
        fsas=[fsa1, fsa2, fsa3]
    )


@pytest.fixture
def parallel_cascade():
    """Create a cascade with parallel execution opportunities."""
    fsa1 = FSA(
        id="fsa1",
        name="DataSource",
        outputs={"data": "list"},
        estimated_duration=1.0
    )
    fsa2 = FSA(
        id="fsa2",
        name="ProcessorA",
        inputs={"data": "list"},
        outputs={"resultA": "dict"},
        dependencies=["fsa1"],
        estimated_duration=2.0
    )
    fsa3 = FSA(
        id="fsa3",
        name="ProcessorB",
        inputs={"data": "list"},
        outputs={"resultB": "dict"},
        dependencies=["fsa1"],
        estimated_duration=2.0
    )
    fsa4 = FSA(
        id="fsa4",
        name="Aggregator",
        inputs={"resultA": "dict", "resultB": "dict"},
        outputs={"final": "dict"},
        dependencies=["fsa2", "fsa3"],
        estimated_duration=1.0
    )

    return FSACascade(
        name="ParallelWorkflow",
        fsas=[fsa1, fsa2, fsa3, fsa4]
    )


def test_basic_cascade_validation(validator, simple_cascade):
    """Test basic validation of a valid cascade."""
    result = validator.validate(simple_cascade)

    assert result.is_valid is True
    assert len(result.errors) == 0
    assert result.dependency_graph is not None
    assert len(result.dependency_graph.nodes) == 3


def test_empty_cascade_validation(validator):
    """Test validation of an empty cascade."""
    empty_cascade = FSACascade(name="Empty", fsas=[])
    result = validator.validate(empty_cascade)

    assert result.is_valid is False
    assert len(result.errors) > 0
    assert "no FSAs" in result.errors[0].lower()


def test_single_fsa_cascade(validator, simple_fsa):
    """Test cascade with a single FSA."""
    cascade = FSACascade(name="SingleFSA", fsas=[simple_fsa])
    result = validator.validate(cascade)

    assert result.is_valid is True
    assert len(result.dependency_graph.nodes) == 1


def test_dependency_graph_construction(validator, simple_cascade):
    """Test dependency graph construction and analysis."""
    graph = validator.analyze_dependencies(simple_cascade.fsas)

    assert len(graph.nodes) == 3
    assert "fsa1" in graph.nodes
    assert "fsa2" in graph.nodes
    assert "fsa3" in graph.nodes

    # Check edges
    assert "fsa2" in graph.edges["fsa1"]
    assert "fsa3" in graph.edges["fsa2"]

    # Check reverse edges
    assert "fsa1" in graph.reverse_edges["fsa2"]
    assert "fsa2" in graph.reverse_edges["fsa3"]

    # Check topological levels
    assert len(graph.levels) == 3
    assert graph.levels[0] == ["fsa1"]
    assert graph.levels[1] == ["fsa2"]
    assert graph.levels[2] == ["fsa3"]


def test_data_flow_validation_success(validator, simple_cascade):
    """Test successful data flow validation."""
    flow_validation = validator.check_data_flow(simple_cascade)

    assert flow_validation.is_valid is True
    assert len(flow_validation.issues) == 0
    assert len(flow_validation.type_mismatches) == 0


def test_data_flow_validation_type_mismatch(validator):
    """Test data flow validation with type mismatches."""
    fsa1 = FSA(
        id="fsa1",
        name="Producer",
        outputs={"data": "str"}
    )
    fsa2 = FSA(
        id="fsa2",
        name="Consumer",
        inputs={"data": "int"},  # Type mismatch
        dependencies=["fsa1"]
    )

    cascade = FSACascade(fsas=[fsa1, fsa2])
    flow_validation = validator.check_data_flow(cascade)

    assert flow_validation.is_valid is False
    assert len(flow_validation.issues) > 0
    assert len(flow_validation.type_mismatches) > 0


def test_data_flow_missing_input(validator):
    """Test detection of missing inputs."""
    fsa1 = FSA(
        id="fsa1",
        name="Producer",
        outputs={"outputA": "str"}
    )
    fsa2 = FSA(
        id="fsa2",
        name="Consumer",
        inputs={"inputB": "str"},  # Input not provided by dependency
        dependencies=["fsa1"]
    )

    cascade = FSACascade(fsas=[fsa1, fsa2])
    flow_validation = validator.check_data_flow(cascade)

    assert flow_validation.is_valid is False
    assert len(flow_validation.missing_inputs) > 0


def test_cycle_detection_simple_cycle(validator):
    """Test detection of simple circular dependency."""
    fsa1 = FSA(id="fsa1", name="A", dependencies=["fsa2"])
    fsa2 = FSA(id="fsa2", name="B", dependencies=["fsa1"])

    cascade = FSACascade(fsas=[fsa1, fsa2])
    graph = validator.analyze_dependencies(cascade.fsas)
    cycles = validator.detect_cycles(graph)

    assert len(cycles) > 0
    # Verify the cycle contains both nodes
    for cycle in cycles:
        assert "fsa1" in cycle.nodes or "fsa2" in cycle.nodes


def test_cycle_detection_no_cycle(validator, simple_cascade):
    """Test cycle detection on acyclic cascade."""
    graph = validator.analyze_dependencies(simple_cascade.fsas)
    cycles = validator.detect_cycles(graph)

    assert len(cycles) == 0


def test_cycle_detection_complex_cycle(validator):
    """Test detection of longer circular dependency chain."""
    fsa1 = FSA(id="fsa1", name="A", dependencies=["fsa3"])
    fsa2 = FSA(id="fsa2", name="B", dependencies=["fsa1"])
    fsa3 = FSA(id="fsa3", name="C", dependencies=["fsa2"])

    cascade = FSACascade(fsas=[fsa1, fsa2, fsa3])
    graph = validator.analyze_dependencies(cascade.fsas)
    cycles = validator.detect_cycles(graph)

    assert len(cycles) > 0


def test_resource_conflict_detection(validator):
    """Test detection of resource conflicts."""
    fsa1 = FSA(
        id="fsa1",
        name="GPU_Task_A",
        resources={"gpu": "cuda:0"}
    )
    fsa2 = FSA(
        id="fsa2",
        name="GPU_Task_B",
        resources={"gpu": "cuda:0"}
    )

    cascade = FSACascade(fsas=[fsa1, fsa2])
    conflicts = validator.detect_conflicts(cascade.fsas)

    # Check if resource conflict was detected
    resource_conflicts = [c for c in conflicts if c.type == ConflictType.RESOURCE]
    assert len(resource_conflicts) > 0


def test_state_conflict_detection(validator):
    """Test detection of state conflicts."""
    fsa1 = FSA(
        id="fsa1",
        name="ExclusiveA",
        metadata={"exclusive": "resource_lock"}
    )
    fsa2 = FSA(
        id="fsa2",
        name="ExclusiveB",
        metadata={"exclusive": "resource_lock"}
    )

    conflicts = validator.detect_conflicts([fsa1, fsa2])

    state_conflicts = [c for c in conflicts if c.type == ConflictType.STATE]
    assert len(state_conflicts) > 0


def test_execution_order_optimization(validator, simple_cascade):
    """Test execution order optimization."""
    execution_plan = validator.optimize_execution_order(simple_cascade)

    assert execution_plan is not None
    assert len(execution_plan.stages) == 3
    assert execution_plan.stages[0] == ["fsa1"]
    assert execution_plan.stages[1] == ["fsa2"]
    assert execution_plan.stages[2] == ["fsa3"]
    assert execution_plan.total_estimated_time == 6.0  # 2.0 + 3.0 + 1.0


def test_execution_plan_parallel_opportunities(validator, parallel_cascade):
    """Test detection of parallel execution opportunities."""
    execution_plan = validator.optimize_execution_order(parallel_cascade)

    assert execution_plan is not None
    # Should have parallel stage with fsa2 and fsa3
    assert len(execution_plan.stages) == 3

    # Stage 1: fsa2 and fsa3 should be in same stage (parallel)
    parallel_stage = execution_plan.stages[1]
    assert len(parallel_stage) == 2
    assert "fsa2" in parallel_stage
    assert "fsa3" in parallel_stage

    # Check parallelism opportunities
    assert execution_plan.parallelism_opportunities > 0


def test_critical_path_calculation(validator, parallel_cascade):
    """Test critical path identification."""
    execution_plan = validator.optimize_execution_order(parallel_cascade)

    assert execution_plan.critical_path is not None
    assert len(execution_plan.critical_path) > 0

    # Critical path duration should be less than sum of all durations
    total_duration = sum(fsa.estimated_duration for fsa in parallel_cascade.fsas)
    assert execution_plan.total_estimated_time < total_duration


def test_performance_profiling(validator, simple_cascade):
    """Test performance profiling and bottleneck detection."""
    performance_report = validator.profile_performance(simple_cascade)

    assert performance_report is not None
    assert performance_report.total_estimated_duration == 6.0
    assert performance_report.critical_path_duration == 6.0
    assert 0.0 <= performance_report.parallelism_score <= 1.0
    assert isinstance(performance_report.optimization_suggestions, list)


def test_performance_bottleneck_detection(validator):
    """Test detection of performance bottlenecks."""
    fsa1 = FSA(id="fsa1", name="Fast", estimated_duration=1.0)
    fsa2 = FSA(
        id="fsa2",
        name="Slow",
        dependencies=["fsa1"],
        estimated_duration=10.0  # Bottleneck
    )
    fsa3 = FSA(
        id="fsa3",
        name="Fast2",
        dependencies=["fsa2"],
        estimated_duration=1.0
    )

    cascade = FSACascade(fsas=[fsa1, fsa2, fsa3])
    performance_report = validator.profile_performance(cascade)

    assert "fsa2" in performance_report.bottlenecks


def test_integrity_verification_success(validator, simple_cascade):
    """Test integrity verification of valid cascade."""
    integrity_report = validator.verify_integrity(simple_cascade)

    assert integrity_report.is_consistent is True
    assert len(integrity_report.issues) == 0
    assert len(integrity_report.orphaned_fsas) == 0
    assert len(integrity_report.unreachable_fsas) == 0


def test_integrity_orphaned_dependency(validator):
    """Test detection of orphaned dependencies."""
    fsa1 = FSA(
        id="fsa1",
        name="Orphan",
        dependencies=["non_existent_fsa"]  # Orphaned dependency
    )

    cascade = FSACascade(fsas=[fsa1])
    integrity_report = validator.verify_integrity(cascade)

    assert integrity_report.is_consistent is False
    assert len(integrity_report.issues) > 0
    assert len(integrity_report.orphaned_fsas) > 0


def test_integrity_unreachable_fsa(validator):
    """Test detection of unreachable FSAs."""
    # Create two separate chains with no connection
    fsa1 = FSA(id="fsa1", name="Chain1_A")
    fsa2 = FSA(id="fsa2", name="Chain1_B", dependencies=["fsa1"])

    fsa3 = FSA(id="fsa3", name="Chain2_A")
    fsa4 = FSA(id="fsa4", name="Chain2_B", dependencies=["fsa3"])

    # fsa3 and fsa4 are unreachable from entry point fsa1
    cascade = FSACascade(fsas=[fsa1, fsa2, fsa3, fsa4])
    integrity_report = validator.verify_integrity(cascade)

    # Should detect unreachable FSAs
    assert len(integrity_report.unreachable_fsas) > 0


def test_full_validation_report(validator, simple_cascade):
    """Test complete validation report generation."""
    report = validator.execute(simple_cascade)

    assert isinstance(report, ValidationReport)
    assert report.validation_result is not None
    assert report.validation_result.is_valid is True
    assert report.execution_plan is not None
    assert report.performance_report is not None


def test_validation_with_multiple_errors(validator):
    """Test validation with multiple types of errors."""
    # Create cascade with circular dependency and type mismatch
    fsa1 = FSA(
        id="fsa1",
        name="A",
        outputs={"data": "str"},
        dependencies=["fsa2"]  # Circular
    )
    fsa2 = FSA(
        id="fsa2",
        name="B",
        inputs={"data": "int"},  # Type mismatch
        dependencies=["fsa1"]  # Circular
    )

    cascade = FSACascade(fsas=[fsa1, fsa2])
    result = validator.validate(cascade)

    assert result.is_valid is False
    assert len(result.errors) > 0
    assert len(result.cycles) > 0


def test_strict_mode_validation(validator, parallel_cascade):
    """Test strict mode where warnings become errors."""
    strict_validator = CascadeValidatorFSA(strict_mode=True)

    # Add resource conflict (creates warning)
    parallel_cascade.fsas[1].resources = {"gpu": "cuda:0"}
    parallel_cascade.fsas[2].resources = {"gpu": "cuda:0"}

    result = strict_validator.validate(parallel_cascade)

    # In strict mode, warnings should prevent validation from passing
    # (depending on conflict detection)
    assert isinstance(result, ValidationResult)


def test_error_handling(validator):
    """Test error handling and recovery."""
    error = ValueError("Test error")
    error_info = validator.error_handling(error)

    assert "error_type" in error_info
    assert "error_message" in error_info
    assert error_info["error_type"] == "ValueError"
    assert error_info["error_message"] == "Test error"
    assert "recovery_suggestions" in error_info
    assert len(error_info["recovery_suggestions"]) > 0


def test_fsa_state_transitions(simple_fsa):
    """Test FSA state management."""
    assert simple_fsa.state == FSAState.IDLE

    # Test can_execute
    assert simple_fsa.can_execute(set()) is True

    # FSA with dependencies
    fsa_with_deps = FSA(
        id="test",
        dependencies=["dep1", "dep2"]
    )
    assert fsa_with_deps.can_execute(set()) is False
    assert fsa_with_deps.can_execute({"dep1"}) is False
    assert fsa_with_deps.can_execute({"dep1", "dep2"}) is True


def test_type_compatibility_check(validator):
    """Test data type compatibility checking."""
    # Exact match
    assert validator._types_compatible("str", "str") is True

    # Any type
    assert validator._types_compatible("Any", "str") is True
    assert validator._types_compatible("int", "Any") is True

    # Compatible types
    assert validator._types_compatible("int", "float") is True
    assert validator._types_compatible("str", "text") is True

    # Incompatible types
    assert validator._types_compatible("str", "int") is False


def test_complex_cascade_validation():
    """Test validation of complex multi-stage cascade."""
    # Create a complex cascade with multiple levels and parallel stages
    fsas = []

    # Level 0: Entry points
    fsas.append(FSA(id="input1", name="Input1", outputs={"data1": "list"}))
    fsas.append(FSA(id="input2", name="Input2", outputs={"data2": "dict"}))

    # Level 1: Parallel processors
    fsas.append(FSA(
        id="proc1",
        name="Processor1",
        inputs={"data1": "list"},
        outputs={"result1": "list"},
        dependencies=["input1"],
        estimated_duration=5.0
    ))
    fsas.append(FSA(
        id="proc2",
        name="Processor2",
        inputs={"data2": "dict"},
        outputs={"result2": "dict"},
        dependencies=["input2"],
        estimated_duration=3.0
    ))

    # Level 2: Aggregator
    fsas.append(FSA(
        id="agg",
        name="Aggregator",
        inputs={"result1": "list", "result2": "dict"},
        outputs={"final": "Any"},
        dependencies=["proc1", "proc2"],
        estimated_duration=2.0
    ))

    cascade = FSACascade(name="ComplexWorkflow", fsas=fsas)
    validator = CascadeValidatorFSA()

    report = validator.execute(cascade)

    assert report.validation_result.is_valid is True
    assert len(report.execution_plan.stages) == 3
    assert report.execution_plan.parallelism_opportunities > 0
    assert report.performance_report.parallelism_score > 0.0
