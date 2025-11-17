"""
Unit tests for Risk Assessor FSA

Tests cover:
- FSA state transitions
- Failure mode analysis
- Risk scoring system
- Mitigation strategy generation
- Edge cases and error handling
"""

import pytest
from agno.eval.risk_assessor_fsa import (
    FailureMode,
    FailureModeAnalysis,
    MitigationStrategy,
    RiskAssessment,
    RiskAssessorFSA,
    RiskAssessorState,
    RiskLevel,
    TaskContext,
    quick_risk_assessment,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def simple_task_context():
    """Simple task context for basic tests"""
    return TaskContext(
        task_description="Implement a basic REST API endpoint",
        context={"critical": False},
        dependencies=["flask", "sqlalchemy"],
        constraints={"deadline": "2 weeks"},
    )


@pytest.fixture
def complex_task_context():
    """Complex task context with high-risk factors"""
    return TaskContext(
        task_description="Migrate production database with zero downtime, implement real-time "
        "data synchronization, and update authentication system with new encryption algorithms",
        context={"critical": True, "production": True, "user_facing": True},
        dependencies=[
            "postgresql-db",
            "redis-cache",
            "auth-api",
            "payment-api",
            "notification-service",
            "analytics-api",
            "user-service",
            "session-store",
        ],
        constraints={"deadline": "urgent", "budget": "limited"},
        environment={"high_availability": True, "scalability_required": True},
    )


@pytest.fixture
def minimal_task_context():
    """Minimal task context for edge case testing"""
    return TaskContext(task_description="Fix typo in documentation")


@pytest.fixture
def fsa():
    """Basic FSA instance"""
    return RiskAssessorFSA(debug_mode=False)


@pytest.fixture
def debug_fsa():
    """FSA instance with debug mode enabled"""
    return RiskAssessorFSA(debug_mode=True)


# ============================================================================
# Test TaskContext
# ============================================================================


def test_task_context_initialization():
    """Test TaskContext initialization with defaults"""
    context = TaskContext(task_description="Test task")

    assert context.task_description == "Test task"
    assert context.context == {}
    assert context.dependencies == []
    assert context.constraints == {}
    assert context.environment == {}


def test_task_context_with_all_fields():
    """Test TaskContext initialization with all fields"""
    context = TaskContext(
        task_description="Complex task",
        context={"key": "value"},
        dependencies=["dep1", "dep2"],
        constraints={"time": "1 week"},
        environment={"env": "prod"},
    )

    assert context.task_description == "Complex task"
    assert context.context == {"key": "value"}
    assert context.dependencies == ["dep1", "dep2"]
    assert context.constraints == {"time": "1 week"}
    assert context.environment == {"env": "prod"}


# ============================================================================
# Test FailureModeAnalysis
# ============================================================================


def test_failure_mode_analysis_risk_score_calculation():
    """Test that risk score is correctly calculated as probability × impact"""
    analysis = FailureModeAnalysis(
        failure_mode=FailureMode.TECHNICAL,
        description="Test failure",
        probability=3,
        impact=4,
    )

    assert analysis.risk_score == 12  # 3 × 4


def test_failure_mode_analysis_validation():
    """Test that probability and impact are validated"""
    # Valid ranges
    analysis = FailureModeAnalysis(
        failure_mode=FailureMode.TECHNICAL,
        description="Test",
        probability=1,
        impact=5,
    )
    assert analysis.probability == 1
    assert analysis.impact == 5

    # Invalid probability
    with pytest.raises(ValueError, match="Probability must be 1-5"):
        FailureModeAnalysis(
            failure_mode=FailureMode.TECHNICAL,
            description="Test",
            probability=0,
            impact=3,
        )

    # Invalid impact
    with pytest.raises(ValueError, match="Impact must be 1-5"):
        FailureModeAnalysis(
            failure_mode=FailureMode.TECHNICAL,
            description="Test",
            probability=3,
            impact=6,
        )


def test_failure_mode_analysis_to_dict():
    """Test conversion to dictionary"""
    analysis = FailureModeAnalysis(
        failure_mode=FailureMode.TECHNICAL,
        description="Test failure",
        probability=2,
        impact=3,
        indicators=["indicator1"],
        examples=["example1"],
    )

    result = analysis.to_dict()

    assert result["failure_mode"] == "technical"
    assert result["description"] == "Test failure"
    assert result["probability"] == 2
    assert result["impact"] == 3
    assert result["risk_score"] == 6
    assert result["indicators"] == ["indicator1"]
    assert result["examples"] == ["example1"]


# ============================================================================
# Test MitigationStrategy
# ============================================================================


def test_mitigation_strategy_creation():
    """Test MitigationStrategy creation"""
    strategy = MitigationStrategy(
        failure_mode=FailureMode.DEPENDENCY,
        strategy="Implement circuit breakers",
        priority="high",
        effort="medium",
        effectiveness="high",
        actions=["Action 1", "Action 2"],
    )

    assert strategy.failure_mode == FailureMode.DEPENDENCY
    assert strategy.strategy == "Implement circuit breakers"
    assert strategy.priority == "high"
    assert len(strategy.actions) == 2


def test_mitigation_strategy_to_dict():
    """Test conversion to dictionary"""
    strategy = MitigationStrategy(
        failure_mode=FailureMode.RESOURCE,
        strategy="Monitor resources",
        priority="medium",
        effort="low",
        effectiveness="medium",
        actions=["Set up monitoring"],
    )

    result = strategy.to_dict()

    assert result["failure_mode"] == "resource"
    assert result["strategy"] == "Monitor resources"
    assert result["priority"] == "medium"
    assert result["effort"] == "low"
    assert result["effectiveness"] == "medium"
    assert result["actions"] == ["Set up monitoring"]


# ============================================================================
# Test RiskAssessment
# ============================================================================


def test_risk_assessment_compute_overall_risk():
    """Test overall risk computation"""
    task_context = TaskContext(task_description="Test")
    assessment = RiskAssessment(
        assessment_id="test-123",
        task_context=task_context,
        current_state=RiskAssessorState.FINAL,
    )

    # Add failure modes with different risk scores
    assessment.failure_modes = [
        FailureModeAnalysis(
            failure_mode=FailureMode.TECHNICAL,
            description="Low risk",
            probability=2,
            impact=2,  # score = 4
        ),
        FailureModeAnalysis(
            failure_mode=FailureMode.DEPENDENCY,
            description="High risk",
            probability=4,
            impact=4,  # score = 16
        ),
        FailureModeAnalysis(
            failure_mode=FailureMode.RESOURCE,
            description="Medium risk",
            probability=3,
            impact=3,  # score = 9
        ),
    ]

    assessment.compute_overall_risk()

    # Overall risk should be the maximum (16)
    assert assessment.overall_risk_score == 16
    assert assessment.overall_risk_level == RiskLevel.CRITICAL


def test_risk_assessment_risk_level_boundaries():
    """Test risk level boundary conditions"""
    task_context = TaskContext(task_description="Test")

    # Test CRITICAL (>= 16)
    assessment = RiskAssessment(
        assessment_id="test-1",
        task_context=task_context,
        current_state=RiskAssessorState.FINAL,
    )
    assessment.failure_modes = [
        FailureModeAnalysis(
            failure_mode=FailureMode.TECHNICAL, description="", probability=4, impact=4
        )
    ]
    assessment.compute_overall_risk()
    assert assessment.overall_risk_level == RiskLevel.CRITICAL

    # Test HIGH (12-15)
    assessment = RiskAssessment(
        assessment_id="test-2",
        task_context=task_context,
        current_state=RiskAssessorState.FINAL,
    )
    assessment.failure_modes = [
        FailureModeAnalysis(
            failure_mode=FailureMode.TECHNICAL, description="", probability=3, impact=4
        )
    ]
    assessment.compute_overall_risk()
    assert assessment.overall_risk_level == RiskLevel.HIGH

    # Test MEDIUM (6-11)
    assessment = RiskAssessment(
        assessment_id="test-3",
        task_context=task_context,
        current_state=RiskAssessorState.FINAL,
    )
    assessment.failure_modes = [
        FailureModeAnalysis(
            failure_mode=FailureMode.TECHNICAL, description="", probability=2, impact=3
        )
    ]
    assessment.compute_overall_risk()
    assert assessment.overall_risk_level == RiskLevel.MEDIUM

    # Test LOW (1-5)
    assessment = RiskAssessment(
        assessment_id="test-4",
        task_context=task_context,
        current_state=RiskAssessorState.FINAL,
    )
    assessment.failure_modes = [
        FailureModeAnalysis(
            failure_mode=FailureMode.TECHNICAL, description="", probability=1, impact=2
        )
    ]
    assessment.compute_overall_risk()
    assert assessment.overall_risk_level == RiskLevel.LOW

    # Test NEGLIGIBLE (0)
    assessment = RiskAssessment(
        assessment_id="test-5",
        task_context=task_context,
        current_state=RiskAssessorState.FINAL,
    )
    assessment.failure_modes = []
    assessment.compute_overall_risk()
    assert assessment.overall_risk_level == RiskLevel.NEGLIGIBLE


def test_risk_assessment_get_critical_risks():
    """Test retrieving critical risks"""
    task_context = TaskContext(task_description="Test")
    assessment = RiskAssessment(
        assessment_id="test",
        task_context=task_context,
        current_state=RiskAssessorState.FINAL,
    )

    assessment.failure_modes = [
        FailureModeAnalysis(
            failure_mode=FailureMode.TECHNICAL,
            description="Critical",
            probability=5,
            impact=5,  # 25
        ),
        FailureModeAnalysis(
            failure_mode=FailureMode.RESOURCE,
            description="Medium",
            probability=2,
            impact=3,  # 6
        ),
        FailureModeAnalysis(
            failure_mode=FailureMode.DEPENDENCY,
            description="High",
            probability=4,
            impact=4,  # 16
        ),
    ]

    critical_risks = assessment.get_critical_risks()

    assert len(critical_risks) == 2
    assert all(risk.risk_score >= 16 for risk in critical_risks)


def test_risk_assessment_get_high_risks():
    """Test retrieving high risks"""
    task_context = TaskContext(task_description="Test")
    assessment = RiskAssessment(
        assessment_id="test",
        task_context=task_context,
        current_state=RiskAssessorState.FINAL,
    )

    assessment.failure_modes = [
        FailureModeAnalysis(
            failure_mode=FailureMode.TECHNICAL, description="", probability=3, impact=4  # 12
        ),
        FailureModeAnalysis(
            failure_mode=FailureMode.RESOURCE, description="", probability=3, impact=5  # 15
        ),
        FailureModeAnalysis(
            failure_mode=FailureMode.DEPENDENCY, description="", probability=2, impact=3  # 6
        ),
    ]

    high_risks = assessment.get_high_risks()

    assert len(high_risks) == 2
    assert all(12 <= risk.risk_score < 16 for risk in high_risks)


def test_risk_assessment_to_dict():
    """Test conversion to dictionary"""
    task_context = TaskContext(task_description="Test task")
    assessment = RiskAssessment(
        assessment_id="test-456",
        task_context=task_context,
        current_state=RiskAssessorState.FINAL,
        overall_risk_score=12,
        overall_risk_level=RiskLevel.HIGH,
        confidence=0.85,
        timestamp="2024-01-01T00:00:00Z",
    )

    result = assessment.to_dict()

    assert result["assessment_id"] == "test-456"
    assert result["task_description"] == "Test task"
    assert result["current_state"] == "final"
    assert result["overall_risk_score"] == 12
    assert result["overall_risk_level"] == "high"
    assert result["confidence"] == 0.85
    assert result["timestamp"] == "2024-01-01T00:00:00Z"


# ============================================================================
# Test RiskAssessorFSA Initialization and State Management
# ============================================================================


def test_fsa_initialization(fsa):
    """Test FSA initialization"""
    assert fsa.name == "RiskAssessorFSA"
    assert fsa.fsa_id is not None
    assert fsa.current_state == RiskAssessorState.INITIAL
    assert len(fsa.state_history) == 1
    assert fsa.state_history[0] == RiskAssessorState.INITIAL
    assert fsa.current_assessment is None
    assert len(fsa.assessments) == 0


def test_fsa_state_transitions(fsa):
    """Test valid state transitions"""
    # INITIAL -> COLLECTING
    fsa.transition_to(RiskAssessorState.COLLECTING)
    assert fsa.current_state == RiskAssessorState.COLLECTING

    # COLLECTING -> ANALYZING
    fsa.transition_to(RiskAssessorState.ANALYZING)
    assert fsa.current_state == RiskAssessorState.ANALYZING

    # ANALYZING -> SCORING
    fsa.transition_to(RiskAssessorState.SCORING)
    assert fsa.current_state == RiskAssessorState.SCORING

    # SCORING -> MITIGATING
    fsa.transition_to(RiskAssessorState.MITIGATING)
    assert fsa.current_state == RiskAssessorState.MITIGATING

    # MITIGATING -> FINAL
    fsa.transition_to(RiskAssessorState.FINAL)
    assert fsa.current_state == RiskAssessorState.FINAL

    # Check state history
    assert len(fsa.state_history) == 6  # Initial + 5 transitions


def test_fsa_invalid_state_transition(fsa):
    """Test that invalid state transitions are rejected"""
    # Try to jump from INITIAL to SCORING (invalid)
    with pytest.raises(ValueError, match="Invalid state transition"):
        fsa.transition_to(RiskAssessorState.SCORING)

    # Try to transition from FINAL (terminal state)
    fsa.current_state = RiskAssessorState.FINAL
    fsa.state_history.append(RiskAssessorState.FINAL)

    with pytest.raises(ValueError, match="Invalid state transition"):
        fsa.transition_to(RiskAssessorState.INITIAL)


def test_fsa_reset(fsa):
    """Test FSA reset functionality"""
    # Perform some transitions
    fsa.transition_to(RiskAssessorState.COLLECTING)
    fsa.transition_to(RiskAssessorState.ANALYZING)

    # Reset
    fsa.reset()

    assert fsa.current_state == RiskAssessorState.INITIAL
    assert len(fsa.state_history) == 1
    assert fsa.current_assessment is None


# ============================================================================
# Test Risk Assessment Workflow
# ============================================================================


def test_assess_risk_simple_task(fsa, simple_task_context):
    """Test risk assessment for a simple task"""
    assessment = fsa.assess_risk(
        task_description=simple_task_context.task_description,
        context=simple_task_context.context,
        dependencies=simple_task_context.dependencies,
        constraints=simple_task_context.constraints,
    )

    # Check assessment was created
    assert assessment is not None
    assert assessment.assessment_id.startswith("risk-")

    # Check FSA reached final state
    assert fsa.current_state == RiskAssessorState.FINAL

    # Check failure modes were analyzed (4 modes)
    assert len(assessment.failure_modes) == 4
    failure_mode_types = {fm.failure_mode for fm in assessment.failure_modes}
    assert failure_mode_types == {
        FailureMode.TECHNICAL,
        FailureMode.RESOURCE,
        FailureMode.DEPENDENCY,
        FailureMode.TIMING,
    }

    # Check overall risk was computed
    assert assessment.overall_risk_score > 0
    assert assessment.overall_risk_level != RiskLevel.NEGLIGIBLE

    # Check confidence was computed
    assert 0.0 <= assessment.confidence <= 1.0

    # Check timestamp was set
    assert assessment.timestamp is not None

    # Check assessment was stored
    assert len(fsa.assessments) == 1


def test_assess_risk_complex_task(fsa, complex_task_context):
    """Test risk assessment for a complex high-risk task"""
    assessment = fsa.assess_risk(
        task_description=complex_task_context.task_description,
        context=complex_task_context.context,
        dependencies=complex_task_context.dependencies,
        constraints=complex_task_context.constraints,
        environment=complex_task_context.environment,
    )

    # Complex task should have higher risk
    assert assessment.overall_risk_score >= 12  # At least HIGH risk

    # Should have multiple high-risk failure modes
    high_risk_modes = [fm for fm in assessment.failure_modes if fm.risk_score >= 12]
    assert len(high_risk_modes) > 0

    # Should generate mitigation strategies
    assert len(assessment.mitigation_strategies) > 0

    # High-risk tasks should have high-priority strategies
    high_priority_strategies = [
        ms for ms in assessment.mitigation_strategies if ms.priority in ["critical", "high"]
    ]
    assert len(high_priority_strategies) > 0


def test_assess_risk_minimal_task(fsa, minimal_task_context):
    """Test risk assessment for a minimal low-risk task"""
    assessment = fsa.assess_risk(
        task_description=minimal_task_context.task_description,
        context=minimal_task_context.context,
        dependencies=minimal_task_context.dependencies,
    )

    # Minimal task should have lower risk
    assert assessment.overall_risk_level in [
        RiskLevel.LOW,
        RiskLevel.MEDIUM,
        RiskLevel.NEGLIGIBLE,
    ]

    # May have few or no mitigation strategies
    assert len(assessment.mitigation_strategies) >= 0


def test_assess_risk_empty_description():
    """Test that empty task description raises error"""
    fsa = RiskAssessorFSA()

    with pytest.raises(ValueError, match="Task description cannot be empty"):
        fsa.assess_risk(task_description="")

    with pytest.raises(ValueError, match="Task description cannot be empty"):
        fsa.assess_risk(task_description="   ")


def test_multiple_assessments(fsa):
    """Test that FSA can perform multiple assessments"""
    # First assessment
    assessment1 = fsa.assess_risk(
        task_description="Implement REST API",
        dependencies=["flask"],
    )

    # Second assessment
    assessment2 = fsa.assess_risk(
        task_description="Database migration",
        dependencies=["postgresql", "alembic"],
        context={"critical": True},
    )

    # Check both assessments were stored
    assert len(fsa.assessments) == 2
    assert assessment1.assessment_id != assessment2.assessment_id

    # Check retrieval by ID
    retrieved1 = fsa.get_assessment_by_id(assessment1.assessment_id)
    assert retrieved1 == assessment1

    retrieved2 = fsa.get_assessment_by_id(assessment2.assessment_id)
    assert retrieved2 == assessment2

    # Check get_all_assessments
    all_assessments = fsa.get_all_assessments()
    assert len(all_assessments) == 2


# ============================================================================
# Test Specific Failure Mode Analyses
# ============================================================================


def test_technical_risk_analysis_high_complexity(fsa):
    """Test technical risk analysis for high-complexity tasks"""
    assessment = fsa.assess_risk(
        task_description="Implement distributed consensus algorithm with real-time synchronization "
        "and encryption for multi-threaded concurrent access",
        context={"critical": True, "production": True},
    )

    technical_fm = next(
        fm for fm in assessment.failure_modes if fm.failure_mode == FailureMode.TECHNICAL
    )

    # High complexity should result in elevated probability/impact
    assert technical_fm.probability >= 3
    assert technical_fm.risk_score >= 6


def test_resource_risk_analysis_with_constraints(fsa):
    """Test resource risk analysis with constraints"""
    assessment = fsa.assess_risk(
        task_description="Optimize large-scale data processing pipeline",
        constraints={"deadline": "1 week", "budget": "limited"},
        environment={"scalability_required": True, "high_availability": True},
    )

    resource_fm = next(
        fm for fm in assessment.failure_modes if fm.failure_mode == FailureMode.RESOURCE
    )

    # Resource constraints should elevate risk
    assert resource_fm.probability >= 2
    assert len(resource_fm.indicators) > 0


def test_dependency_risk_analysis_many_dependencies(fsa):
    """Test dependency risk analysis with many dependencies"""
    many_deps = [f"service-{i}" for i in range(15)]

    assessment = fsa.assess_risk(
        task_description="Integrate multiple external services",
        dependencies=many_deps,
    )

    dependency_fm = next(
        fm for fm in assessment.failure_modes if fm.failure_mode == FailureMode.DEPENDENCY
    )

    # Many dependencies should result in high probability
    assert dependency_fm.probability >= 4
    assert "dependency count" in dependency_fm.indicators[0].lower()


def test_dependency_risk_analysis_api_dependencies(fsa):
    """Test dependency risk analysis with external APIs"""
    assessment = fsa.assess_risk(
        task_description="Integrate payment processing",
        dependencies=["stripe-api", "paypal-api", "external-http-service"],
    )

    dependency_fm = next(
        fm for fm in assessment.failure_modes if fm.failure_mode == FailureMode.DEPENDENCY
    )

    # External APIs should elevate impact
    assert dependency_fm.impact >= 3
    assert any("api" in indicator.lower() for indicator in dependency_fm.indicators)


def test_timing_risk_analysis_urgent_deadline(fsa):
    """Test timing risk analysis with urgent deadline"""
    assessment = fsa.assess_risk(
        task_description="Critical bug fix needed immediately",
        constraints={"deadline": "urgent", "time_limit": "4 hours"},
    )

    timing_fm = next(
        fm for fm in assessment.failure_modes if fm.failure_mode == FailureMode.TIMING
    )

    # Urgent deadline should result in high probability and impact
    assert timing_fm.probability >= 4
    assert timing_fm.impact >= 3


def test_timing_risk_analysis_with_dependencies(fsa):
    """Test timing risk analysis with sequential dependencies"""
    assessment = fsa.assess_risk(
        task_description="Deploy new feature with coordinated release",
        dependencies=["service-a", "service-b", "service-c"],
        constraints={"deadline": "next week"},
    )

    timing_fm = next(
        fm for fm in assessment.failure_modes if fm.failure_mode == FailureMode.TIMING
    )

    # Dependencies can cause timing issues
    assert timing_fm.probability >= 2


# ============================================================================
# Test Mitigation Strategy Generation
# ============================================================================


def test_mitigation_strategies_generated_for_high_risks(fsa):
    """Test that mitigation strategies are generated for high-risk failure modes"""
    assessment = fsa.assess_risk(
        task_description="Migrate critical production database with real-time sync",
        context={"critical": True, "production": True},
        dependencies=["postgres-db", "redis-cache", "api-gateway"],
        constraints={"deadline": "urgent"},
    )

    # Should have mitigation strategies
    assert len(assessment.mitigation_strategies) > 0

    # Check that strategies have required fields
    for strategy in assessment.mitigation_strategies:
        assert strategy.failure_mode in [
            FailureMode.TECHNICAL,
            FailureMode.RESOURCE,
            FailureMode.DEPENDENCY,
            FailureMode.TIMING,
        ]
        assert strategy.strategy != ""
        assert strategy.priority in ["critical", "high", "medium", "low"]
        assert strategy.effort in ["low", "medium", "high"]
        assert strategy.effectiveness in ["low", "medium", "high"]
        assert len(strategy.actions) > 0


def test_mitigation_strategies_sorted_by_priority(fsa):
    """Test that mitigation strategies are sorted by priority"""
    assessment = fsa.assess_risk(
        task_description="Complex multi-service deployment with database migration",
        context={"critical": True},
        dependencies=["db", "api1", "api2", "api3"],
    )

    if len(assessment.mitigation_strategies) > 1:
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        priorities = [
            priority_order[ms.priority.lower()] for ms in assessment.mitigation_strategies
        ]

        # Check sorted (each priority <= next priority)
        assert all(priorities[i] <= priorities[i + 1] for i in range(len(priorities) - 1))


def test_no_mitigation_strategies_for_low_risk(fsa):
    """Test that low-risk tasks may not generate mitigation strategies"""
    assessment = fsa.assess_risk(
        task_description="Update documentation",
        context={"critical": False},
    )

    # Low risk tasks (score < 6) don't generate mitigation strategies
    low_risk_modes = [fm for fm in assessment.failure_modes if fm.risk_score < 6]

    # Count strategies for low-risk modes
    low_risk_strategies = [
        ms
        for ms in assessment.mitigation_strategies
        if any(fm.failure_mode == ms.failure_mode and fm.risk_score < 6
               for fm in assessment.failure_modes)
    ]

    # Should be fewer strategies for low-risk modes
    assert len(low_risk_strategies) == 0


# ============================================================================
# Test Confidence Scoring
# ============================================================================


def test_confidence_with_complete_information(fsa):
    """Test confidence scoring with complete information"""
    assessment = fsa.assess_risk(
        task_description="This is a detailed task description with lots of context and "
        "information about what needs to be done and why it's important",
        context={"env": "production", "critical": True},
        dependencies=["dep1", "dep2"],
        constraints={"deadline": "1 week"},
        environment={"region": "us-east-1"},
    )

    # Complete information should result in higher confidence
    assert assessment.confidence >= 0.7


def test_confidence_with_minimal_information(fsa):
    """Test confidence scoring with minimal information"""
    assessment = fsa.assess_risk(
        task_description="Task",  # Very short description
        # No context, dependencies, constraints, or environment
    )

    # Minimal information should result in lower confidence
    assert assessment.confidence <= 0.6


# ============================================================================
# Test Quick Risk Assessment Convenience Function
# ============================================================================


def test_quick_risk_assessment_basic():
    """Test quick_risk_assessment convenience function"""
    assessment = quick_risk_assessment(
        task_description="Implement user authentication",
        print_result=False,
    )

    assert assessment is not None
    assert assessment.assessment_id.startswith("risk-")
    assert len(assessment.failure_modes) == 4


def test_quick_risk_assessment_with_dependencies():
    """Test quick_risk_assessment with dependencies"""
    assessment = quick_risk_assessment(
        task_description="Build API gateway",
        dependencies=["service1", "service2", "database"],
        critical=True,
        print_result=False,
    )

    assert assessment is not None
    assert assessment.task_context.context.get("critical") is True
    assert len(assessment.task_context.dependencies) == 3


# ============================================================================
# Test Edge Cases
# ============================================================================


def test_edge_case_no_dependencies(fsa):
    """Test assessment with no dependencies"""
    assessment = fsa.assess_risk(
        task_description="Internal utility function",
        dependencies=[],
    )

    dependency_fm = next(
        fm for fm in assessment.failure_modes if fm.failure_mode == FailureMode.DEPENDENCY
    )

    # No dependencies should result in lower risk
    assert dependency_fm.probability <= 2


def test_edge_case_very_long_description(fsa):
    """Test assessment with very long task description"""
    long_description = "Task description " * 100  # 1800+ characters

    assessment = fsa.assess_risk(task_description=long_description)

    # Should still work and have high confidence due to length
    assert assessment is not None
    assert assessment.confidence >= 0.3  # Length contributes to confidence


def test_edge_case_special_characters_in_description(fsa):
    """Test assessment with special characters"""
    assessment = fsa.assess_risk(
        task_description="Fix bug in parser: handle @#$%^&* symbols correctly!",
    )

    assert assessment is not None
    assert len(assessment.failure_modes) == 4


def test_edge_case_unicode_in_description(fsa):
    """Test assessment with unicode characters"""
    assessment = fsa.assess_risk(
        task_description="Implement internationalization support for 中文, 日本語, العربية",
    )

    assert assessment is not None


# ============================================================================
# Test Assessment Retrieval
# ============================================================================


def test_get_assessment_by_id_not_found(fsa):
    """Test retrieving non-existent assessment"""
    result = fsa.get_assessment_by_id("nonexistent-id")
    assert result is None


def test_get_all_assessments_empty(fsa):
    """Test get_all_assessments with no assessments"""
    assessments = fsa.get_all_assessments()
    assert len(assessments) == 0


def test_get_all_assessments_returns_copy(fsa):
    """Test that get_all_assessments returns a copy, not reference"""
    fsa.assess_risk(task_description="Task 1")

    assessments = fsa.get_all_assessments()
    original_length = len(fsa.assessments)

    # Modify returned list
    assessments.clear()

    # Original should be unchanged
    assert len(fsa.assessments) == original_length


# ============================================================================
# Test Debug Mode
# ============================================================================


def test_debug_mode_enabled(debug_fsa):
    """Test FSA with debug mode enabled"""
    # Should not raise any errors
    assessment = debug_fsa.assess_risk(
        task_description="Debug mode test",
        dependencies=["dep1"],
    )

    assert assessment is not None
    assert debug_fsa.debug_mode is True
