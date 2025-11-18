"""
Unit tests for Quality Assurance FSA.

This module contains comprehensive tests for the QualityAssuranceFSA class,
covering code quality analysis, test coverage, documentation validation,
performance profiling, standards compliance, best practices, and more.
"""

import ast
import tempfile
import time
from pathlib import Path

import pytest

from agno.fsas.quality_assurance_fsa import (
    BestPracticesReport,
    CodeQualityMetrics,
    ComplianceReport,
    CoverageReport,
    DetailedQualityReport,
    DocumentationReport,
    FSAImplementation,
    Improvement,
    PerformanceMetrics,
    QAState,
    QualityAssuranceFSA,
    QualityReport,
    QualityScore,
    ValidationResult,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def qa_fsa():
    """Create a QualityAssuranceFSA instance for testing."""
    return QualityAssuranceFSA(
        name="TestQAFSA",
        quality_threshold=70.0,
        coverage_threshold=80.0,
        performance_threshold=1.0,
    )


@pytest.fixture
def sample_code():
    """Sample Python code for testing."""
    return '''"""Sample module for testing."""

import logging

logger = logging.getLogger(__name__)


class SampleClass:
    """A sample class for testing purposes."""

    def __init__(self, name: str):
        """Initialize sample class.

        Args:
            name: Name of the instance
        """
        self.name = name

    def greet(self) -> str:
        """Return a greeting message.

        Returns:
            Greeting message string
        """
        try:
            return f"Hello, {self.name}!"
        except Exception as e:
            logger.error(f"Error in greet: {e}")
            raise


def add_numbers(a: int, b: int) -> int:
    """Add two numbers.

    Args:
        a: First number
        b: Second number

    Returns:
        Sum of a and b
    """
    return a + b


def undocumented_function():
    """This function has minimal documentation."""
    pass
'''


@pytest.fixture
def sample_test_code():
    """Sample test code for coverage testing."""
    return '''"""Test module for sample code."""

import pytest


class TestSampleClass:
    """Test cases for SampleClass."""

    def test_greet(self):
        """Test the greet method."""
        from sample import SampleClass
        obj = SampleClass("World")
        assert obj.greet() == "Hello, World!"


def test_add_numbers():
    """Test add_numbers function."""
    from sample import add_numbers
    assert add_numbers(2, 3) == 5
'''


@pytest.fixture
def poor_quality_code():
    """Poor quality code for testing code quality metrics."""
    return '''def poorFunction():
    x=1;y=2;z=3
    if x>0:
        if y>0:
            if z>0:
                if x<10:
                    if y<10:
                        if z<10:
                            return "nested"
    return x+y+z

def veryLongFunctionNameThatViolatesNamingConventions():
    pass

class badclassname:
    pass

def use_eval():
    eval("1+1")
'''


@pytest.fixture
def fsa_implementation(sample_code):
    """Create an FSAImplementation for testing."""
    fsa = FSAImplementation(name="TestFSA", source_code=sample_code)
    return fsa


# ============================================================================
# Test Basic Initialization and Validation
# ============================================================================


def test_qa_fsa_initialization(qa_fsa):
    """Test QualityAssuranceFSA initialization."""
    assert qa_fsa.name == "TestQAFSA"
    assert qa_fsa.quality_threshold == 70.0
    assert qa_fsa.coverage_threshold == 80.0
    assert qa_fsa.performance_threshold == 1.0
    assert qa_fsa.state == QAState.INITIALIZED
    assert len(qa_fsa.state_history) == 1
    assert qa_fsa.state_history[0][0] == QAState.INITIALIZED


def test_validate_fsa_success(qa_fsa, fsa_implementation):
    """Test successful FSA validation."""
    result = qa_fsa.validate(fsa_implementation)

    assert isinstance(result, ValidationResult)
    assert result.is_valid
    assert len(result.validation_errors) == 0
    assert "TestFSA" in str(result.validation_info)


def test_validate_fsa_missing_name(qa_fsa):
    """Test validation with missing FSA name."""
    fsa = FSAImplementation(name="", source_code="# code")
    result = qa_fsa.validate(fsa)

    assert not result.is_valid
    assert any("name" in error.lower() for error in result.validation_errors)


def test_validate_fsa_missing_source(qa_fsa):
    """Test validation with missing source code."""
    fsa = FSAImplementation(name="TestFSA", source_code="")
    result = qa_fsa.validate(fsa)

    assert not result.is_valid
    assert any("source code" in error.lower() for error in result.validation_errors)


# ============================================================================
# Test Code Quality Analysis
# ============================================================================


def test_analyze_code_quality_basic(qa_fsa, sample_code):
    """Test basic code quality analysis."""
    metrics = qa_fsa.analyze_code_quality(sample_code)

    assert isinstance(metrics, CodeQualityMetrics)
    assert metrics.total_lines > 0
    assert metrics.code_lines > 0
    assert metrics.comment_lines > 0
    assert metrics.functions_count >= 2  # add_numbers, undocumented_function
    assert metrics.classes_count >= 1  # SampleClass
    assert metrics.complexity > 0


def test_analyze_code_quality_poor_code(qa_fsa, poor_quality_code):
    """Test code quality analysis with poor quality code."""
    metrics = qa_fsa.analyze_code_quality(poor_quality_code)

    assert len(metrics.code_smells) > 0
    assert len(metrics.naming_violations) > 0
    assert len(metrics.security_issues) > 0  # Should detect eval usage
    assert any("eval" in issue.lower() for issue in metrics.security_issues)


def test_analyze_code_quality_syntax_error(qa_fsa):
    """Test code quality analysis with syntax error."""
    bad_code = "def broken_function(\n    invalid syntax here"
    metrics = qa_fsa.analyze_code_quality(bad_code)

    # Should handle syntax error gracefully
    assert isinstance(metrics, CodeQualityMetrics)
    assert len(metrics.code_smells) > 0


# ============================================================================
# Test Coverage Analysis
# ============================================================================


def test_check_test_coverage_with_files(qa_fsa, sample_code, sample_test_code):
    """Test coverage analysis with actual files."""
    # Create temporary files
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(sample_code)
        fsa_module = f.name

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(sample_test_code)
        test_module = f.name

    try:
        report = qa_fsa.check_test_coverage(fsa_module, test_module)

        assert isinstance(report, CoverageReport)
        assert report.total_statements > 0
        assert report.test_count > 0
        assert report.coverage_percentage >= 0
    finally:
        # Cleanup
        Path(fsa_module).unlink(missing_ok=True)
        Path(test_module).unlink(missing_ok=True)


def test_check_test_coverage_missing_files(qa_fsa):
    """Test coverage analysis with missing files."""
    report = qa_fsa.check_test_coverage("/nonexistent/module.py", "/nonexistent/test.py")

    assert isinstance(report, CoverageReport)
    assert report.total_statements == 0
    assert report.coverage_percentage == 0


# ============================================================================
# Test Documentation Validation
# ============================================================================


def test_validate_documentation_complete(qa_fsa, fsa_implementation):
    """Test documentation validation with well-documented code."""
    report = qa_fsa.validate_documentation(fsa_implementation)

    assert isinstance(report, DocumentationReport)
    assert report.has_module_docstring
    assert report.total_functions > 0
    assert report.documented_functions > 0
    assert report.total_classes > 0
    assert report.documented_classes > 0
    assert report.documentation_coverage > 0


def test_validate_documentation_incomplete(qa_fsa):
    """Test documentation validation with poorly documented code."""
    poor_docs_code = '''
def func1():
    pass

def func2():
    pass

class MyClass:
    def method1(self):
        pass
'''
    fsa = FSAImplementation(name="PoorDocs", source_code=poor_docs_code)
    report = qa_fsa.validate_documentation(fsa)

    assert not report.has_module_docstring
    assert len(report.missing_docstrings) > 0
    assert report.documentation_coverage < 50


# ============================================================================
# Test Performance Profiling
# ============================================================================


def test_profile_performance_fast_execution(qa_fsa, fsa_implementation):
    """Test performance profiling with fast execution."""
    metrics = qa_fsa.profile_performance(fsa_implementation)

    assert isinstance(metrics, PerformanceMetrics)
    assert metrics.execution_time >= 0
    assert metrics.memory_usage >= 0
    assert metrics.peak_memory >= 0
    assert metrics.performance_score >= 0


def test_profile_performance_slow_execution(qa_fsa):
    """Test performance profiling with slow execution."""
    # Create a slow FSA
    class SlowFSA(FSAImplementation):
        def execute(self, *args, **kwargs):
            time.sleep(0.1)  # Simulate slow operation
            return {"status": "slow"}

    slow_fsa = SlowFSA(name="SlowFSA", source_code="# slow code")
    metrics = qa_fsa.profile_performance(slow_fsa)

    assert metrics.execution_time >= 0.1
    # Should detect bottleneck if threshold is low
    qa_fsa.performance_threshold = 0.05
    metrics = qa_fsa.profile_performance(slow_fsa)
    assert len(metrics.bottlenecks) > 0


# ============================================================================
# Test Standards Compliance
# ============================================================================


def test_check_standards_compliance_good_code(qa_fsa, fsa_implementation):
    """Test standards compliance with good code."""
    report = qa_fsa.check_standards_compliance(fsa_implementation)

    assert isinstance(report, ComplianceReport)
    assert report.type_hint_coverage > 0  # Sample code has type hints
    assert report.compliance_score > 0


def test_check_standards_compliance_violations(qa_fsa, poor_quality_code):
    """Test standards compliance with code violations."""
    fsa = FSAImplementation(name="PoorCode", source_code=poor_quality_code)
    report = qa_fsa.check_standards_compliance(fsa)

    assert len(report.pep8_violations) > 0  # Should detect multiple statements on one line
    assert len(report.naming_violations) > 0  # Should detect bad naming
    assert not report.follows_naming_conventions


# ============================================================================
# Test Best Practices Validation
# ============================================================================


def test_validate_best_practices_good_code(qa_fsa, sample_code):
    """Test best practices validation with good code."""
    report = qa_fsa.validate_best_practices(sample_code)

    assert isinstance(report, BestPracticesReport)
    assert report.uses_error_handling  # Sample code has try-except
    assert report.uses_logging  # Sample code imports logging
    assert report.uses_type_annotations  # Sample code has type hints
    assert report.error_handling_coverage > 0


def test_validate_best_practices_poor_code(qa_fsa):
    """Test best practices validation with poor code."""
    poor_code = '''
def no_error_handling():
    risky_operation()

def another_function():
    more_risky_stuff()
'''
    report = qa_fsa.validate_best_practices(poor_code)

    assert not report.uses_error_handling
    assert not report.uses_logging
    assert report.best_practices_score < 50


# ============================================================================
# Test Quality Score Aggregation
# ============================================================================


def test_aggregate_quality_metrics_high_quality(qa_fsa):
    """Test quality metrics aggregation with high quality reports."""
    code_quality = CodeQualityMetrics(
        total_lines=100,
        code_lines=80,
        complexity=5,
        maintainability_index=85.0,
    )
    coverage = CoverageReport(coverage_percentage=90.0)
    documentation = DocumentationReport(documentation_coverage=85.0)
    performance = PerformanceMetrics(performance_score=90.0)
    compliance = ComplianceReport(compliance_score=88.0)
    best_practices = BestPracticesReport(best_practices_score=87.0)

    reports = [code_quality, coverage, documentation, performance, compliance, best_practices]
    score = qa_fsa.aggregate_quality_metrics(reports)

    assert isinstance(score, QualityScore)
    assert score.overall_score > 80
    assert score.grade in ["A", "B"]
    assert score.passed_threshold


def test_aggregate_quality_metrics_low_quality(qa_fsa):
    """Test quality metrics aggregation with low quality reports."""
    code_quality = CodeQualityMetrics(maintainability_index=40.0, code_smells=["smell1", "smell2"])
    coverage = CoverageReport(coverage_percentage=30.0)
    documentation = DocumentationReport(documentation_coverage=25.0)
    performance = PerformanceMetrics(performance_score=45.0)
    compliance = ComplianceReport(compliance_score=40.0)
    best_practices = BestPracticesReport(best_practices_score=35.0)

    reports = [code_quality, coverage, documentation, performance, compliance, best_practices]
    score = qa_fsa.aggregate_quality_metrics(reports)

    assert score.overall_score < 50
    assert score.grade in ["D", "F"]
    assert not score.passed_threshold


# ============================================================================
# Test Improvement Recommendations
# ============================================================================


def test_recommend_improvements_low_coverage(qa_fsa):
    """Test improvement recommendations for low test coverage."""
    report = QualityReport(
        fsa_name="TestFSA",
        coverage=CoverageReport(
            coverage_percentage=50.0,
            uncovered_functions=["func1", "func2", "func3"]
        )
    )

    improvements = qa_fsa.recommend_improvements(report)

    assert len(improvements) > 0
    assert any(imp.category == "Test Coverage" for imp in improvements)
    assert any(imp.priority == "high" for imp in improvements)


def test_recommend_improvements_missing_docs(qa_fsa):
    """Test improvement recommendations for missing documentation."""
    report = QualityReport(
        fsa_name="TestFSA",
        documentation=DocumentationReport(
            documentation_coverage=40.0,
            missing_docstrings=["func1", "func2"]
        )
    )

    improvements = qa_fsa.recommend_improvements(report)

    assert any(imp.category == "Documentation" for imp in improvements)
    assert any("docstring" in imp.description.lower() for imp in improvements)


def test_recommend_improvements_security_issues(qa_fsa):
    """Test improvement recommendations for security issues."""
    report = QualityReport(
        fsa_name="TestFSA",
        code_quality=CodeQualityMetrics(
            security_issues=["SQL injection", "XSS vulnerability"]
        )
    )

    improvements = qa_fsa.recommend_improvements(report)

    assert any(imp.category == "Security" for imp in improvements)
    assert any(imp.priority == "critical" for imp in improvements)


def test_recommend_improvements_sorted_by_priority(qa_fsa):
    """Test that improvements are sorted by priority."""
    report = QualityReport(
        fsa_name="TestFSA",
        coverage=CoverageReport(coverage_percentage=50.0),
        documentation=DocumentationReport(documentation_coverage=40.0),
        code_quality=CodeQualityMetrics(security_issues=["Critical issue"])
    )

    improvements = qa_fsa.recommend_improvements(report)

    # Critical should come first
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    for i in range(len(improvements) - 1):
        curr_priority = priority_order.get(improvements[i].priority, 99)
        next_priority = priority_order.get(improvements[i + 1].priority, 99)
        assert curr_priority <= next_priority


# ============================================================================
# Test Full Execution Pipeline
# ============================================================================


def test_execute_full_pipeline(qa_fsa, fsa_implementation):
    """Test complete QA execution pipeline."""
    report = qa_fsa.execute(fsa_implementation)

    assert isinstance(report, QualityReport)
    assert report.fsa_name == "TestFSA"
    assert report.code_quality is not None
    assert report.coverage is not None
    assert report.documentation is not None
    assert report.performance is not None
    assert report.compliance is not None
    assert report.best_practices is not None
    assert report.quality_score is not None
    assert len(report.improvements) > 0
    assert report.execution_time > 0


def test_execute_state_transitions(qa_fsa, fsa_implementation):
    """Test that execution goes through proper state transitions."""
    initial_state = qa_fsa.state
    report = qa_fsa.execute(fsa_implementation)

    # Check state history
    states = [state for state, _ in qa_fsa.state_history]

    assert QAState.INITIALIZED in states
    assert QAState.ANALYZING_CODE in states
    assert QAState.CHECKING_COVERAGE in states
    assert QAState.VALIDATING_DOCS in states
    assert QAState.PROFILING_PERFORMANCE in states
    assert QAState.CHECKING_COMPLIANCE in states
    assert QAState.VALIDATING_PRACTICES in states
    assert QAState.AGGREGATING_METRICS in states
    assert QAState.GENERATING_RECOMMENDATIONS in states
    assert QAState.COMPLETED in states

    # Final state should be COMPLETED
    assert qa_fsa.state == QAState.COMPLETED


# ============================================================================
# Test Edge Cases
# ============================================================================


def test_execute_with_invalid_fsa_strict_mode(qa_fsa):
    """Test execution with invalid FSA in strict mode."""
    qa_fsa.enable_strict_mode = True
    invalid_fsa = FSAImplementation(name="", source_code="")

    with pytest.raises(ValueError):
        qa_fsa.execute(invalid_fsa)


def test_execute_with_invalid_fsa_non_strict_mode(qa_fsa):
    """Test execution with invalid FSA in non-strict mode."""
    qa_fsa.enable_strict_mode = False
    invalid_fsa = FSAImplementation(name="InvalidFSA", source_code="# minimal")

    # Should complete without raising exception
    report = qa_fsa.execute(invalid_fsa)
    assert isinstance(report, QualityReport)


def test_generate_detailed_report(qa_fsa, fsa_implementation):
    """Test detailed quality report generation."""
    detailed_report = qa_fsa.generate_detailed_report(fsa_implementation)

    assert isinstance(detailed_report, DetailedQualityReport)
    assert detailed_report.quality_report is not None
    assert len(detailed_report.state_transitions) > 0
    assert len(detailed_report.analysis_logs) > 0
    assert "threshold" in detailed_report.raw_metrics


def test_error_handling_recovery(qa_fsa):
    """Test error handling and recovery."""
    # Force error state
    qa_fsa.state = QAState.ERROR

    # Trigger error handling
    qa_fsa.error_handling()

    # Should reset to initialized
    assert qa_fsa.state == QAState.INITIALIZED
    assert qa_fsa._current_report is None


# ============================================================================
# Test Multi-Metric Quality Reports
# ============================================================================


def test_quality_report_all_metrics_present(qa_fsa, fsa_implementation):
    """Test that quality report includes all metric types."""
    report = qa_fsa.execute(fsa_implementation)

    # All metric types should be present
    assert report.code_quality is not None
    assert report.coverage is not None
    assert report.documentation is not None
    assert report.performance is not None
    assert report.compliance is not None
    assert report.best_practices is not None
    assert report.quality_score is not None

    # Quality score should have all component scores
    assert report.quality_score.code_quality_score >= 0
    assert report.quality_score.test_coverage_score >= 0
    assert report.quality_score.documentation_score >= 0
    assert report.quality_score.performance_score >= 0
    assert report.quality_score.compliance_score >= 0
    assert report.quality_score.best_practices_score >= 0


# ============================================================================
# Test Threshold Enforcement
# ============================================================================


def test_threshold_enforcement_pass(qa_fsa, fsa_implementation):
    """Test threshold enforcement when quality passes."""
    qa_fsa.quality_threshold = 50.0  # Set low threshold
    report = qa_fsa.execute(fsa_implementation)

    # Should pass with well-written sample code
    assert report.quality_score.passed_threshold


def test_threshold_enforcement_fail(qa_fsa, poor_quality_code):
    """Test threshold enforcement when quality fails."""
    qa_fsa.quality_threshold = 90.0  # Set high threshold
    fsa = FSAImplementation(name="PoorQuality", source_code=poor_quality_code)
    report = qa_fsa.execute(fsa)

    # Should fail with poor quality code
    assert not report.quality_score.passed_threshold


def test_custom_thresholds(qa_fsa):
    """Test initialization with custom thresholds."""
    custom_qa = QualityAssuranceFSA(
        quality_threshold=85.0,
        coverage_threshold=90.0,
        performance_threshold=0.5
    )

    assert custom_qa.quality_threshold == 85.0
    assert custom_qa.coverage_threshold == 90.0
    assert custom_qa.performance_threshold == 0.5
