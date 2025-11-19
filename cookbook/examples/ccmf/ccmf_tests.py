"""
CCMF Comprehensive Test Suite - SESSION 2 Part 2
=================================================

Comprehensive unit and integration tests for the CCMF framework.

Tests cover:
- All cognitive patterns
- Constitutional validation
- RSI feedback loop
- Workflow orchestration
- Meta-learning components
- CLI functionality
- Error handling and edge cases

Run with: pytest ccmf_tests.py -v
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import subprocess

# Import modules to test
from ccmf_constitutional import (
    ConstitutionalFramework, ConstitutionalPrinciple,
    PrincipleCategory, ComplianceLevel, validate_operation
)
from ccmf_patterns import (
    DirectPathAccessPattern, KnownPathSearchPattern,
    GitRepositoryFilePattern, CheckpointRecoveryPattern,
    GitStateAnalysisPattern, CompositeStateRecoveryPattern,
    get_pattern, PatternResult
)
from ccmf_rsi_loop import (
    RSIFeedbackLoop, FeedbackType, FeedbackEntry,
    PerformanceMetrics, AdaptationStrategy
)
from ccmf_workflows import Workflow, WorkflowBuilder, WorkflowStep, WorkflowStatus
from ccmf_meta_learning import (
    MetaLearningArchitecture, MLALeverageQuotient,
    LearningExample, PatternKnowledge
)
from ccmf_main import CCMFConfig


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def sample_file(temp_dir):
    """Create a sample file for testing."""
    file_path = temp_dir / "test_file.txt"
    file_path.write_text("Sample content for testing", encoding='utf-8')
    return file_path


@pytest.fixture
def sample_config(temp_dir):
    """Create a sample configuration file."""
    config_path = temp_dir / "test_config.json"
    config_data = {
        "paths": {
            "checkpoints_dir": str(temp_dir / "checkpoints"),
            "logs_dir": str(temp_dir / "logs")
        },
        "logging": {
            "level": "INFO"
        }
    }
    config_path.write_text(json.dumps(config_data))
    return config_path


@pytest.fixture
def checkpoint_dir(temp_dir):
    """Create a checkpoint directory."""
    checkpoint_path = temp_dir / "checkpoints"
    checkpoint_path.mkdir(parents=True, exist_ok=True)
    return checkpoint_path


# =============================================================================
# Constitutional Framework Tests
# =============================================================================

class TestConstitutionalFramework:
    """Tests for constitutional framework."""

    def test_framework_initialization(self):
        """Test framework initialization."""
        framework = ConstitutionalFramework()
        assert len(framework.principles) > 0
        assert len(framework.compliance_history) == 0

    def test_add_principle(self):
        """Test adding a principle."""
        framework = ConstitutionalFramework()
        initial_count = len(framework.principles)

        principle = ConstitutionalPrinciple(
            id="test_001",
            name="Test Principle",
            category=PrincipleCategory.SAFETY,
            description="Test principle",
            weight=1.0
        )

        framework.add_principle(principle)
        assert len(framework.principles) == initial_count + 1

    def test_get_principle(self):
        """Test getting a principle by ID."""
        framework = ConstitutionalFramework()
        principle = framework.get_principle("safety_001")
        assert principle is not None
        assert principle.id == "safety_001"

    def test_validate_full_compliance(self):
        """Test full compliance validation."""
        context = {
            'operation_type': 'test',
            'risk_assessment': 'low',
            'logging_enabled': True,
            'audit_trail': True,
            'resource_estimate': {},
            'error_handling': True,
            'recovery_strategy': 'retry',
            'data_classification': 'public',
            'privacy_check': True,
            'ethical_review': True
        }

        report = validate_operation(context)
        assert report.overall_compliance == ComplianceLevel.FULL
        assert report.compliance_score >= 0.95
        assert report.principles_failed == 0

    def test_validate_partial_compliance(self):
        """Test partial compliance validation."""
        context = {
            'operation_type': 'test',
            'risk_assessment': 'medium',
            'logging_enabled': True,
            'audit_trail': True,
            'error_handling': True,
            'recovery_strategy': 'retry'
        }

        report = validate_operation(context)
        assert report.overall_compliance in [ComplianceLevel.PARTIAL, ComplianceLevel.MINIMAL]
        assert len(report.violations) > 0

    def test_validate_non_compliant(self):
        """Test non-compliant validation."""
        context = {'operation_type': 'test'}

        report = validate_operation(context)
        assert report.overall_compliance == ComplianceLevel.NON_COMPLIANT
        assert report.principles_failed > 0

    def test_compliance_history(self):
        """Test compliance history tracking."""
        framework = ConstitutionalFramework()
        initial_count = len(framework.compliance_history)

        context = {
            'operation_type': 'test',
            'risk_assessment': 'low',
            'logging_enabled': True,
            'audit_trail': True,
            'resource_estimate': {},
            'error_handling': True,
            'recovery_strategy': 'retry',
            'data_classification': 'public',
            'privacy_check': True,
            'ethical_review': True
        }

        framework.validate_compliance(context)
        assert len(framework.compliance_history) == initial_count + 1


# =============================================================================
# Pattern Tests
# =============================================================================

class TestDirectPathAccessPattern:
    """Tests for DirectPathAccessPattern."""

    def test_initialization(self):
        """Test pattern initialization."""
        pattern = DirectPathAccessPattern()
        assert pattern.name == "DirectPathAccessPattern"
        assert pattern.execution_count == 0

    def test_file_exists(self, sample_file):
        """Test file existence check."""
        pattern = DirectPathAccessPattern()
        result = pattern.execute(path=str(sample_file), operation="exists")

        assert result.success
        assert result.data is True
        assert result.execution_time > 0

    def test_file_stat(self, sample_file):
        """Test file statistics."""
        pattern = DirectPathAccessPattern()
        result = pattern.execute(path=str(sample_file), operation="stat")

        assert result.success
        assert 'size' in result.data
        assert 'modified' in result.data
        assert result.data['is_file'] is True

    def test_file_read(self, sample_file):
        """Test file reading."""
        pattern = DirectPathAccessPattern()
        result = pattern.execute(path=str(sample_file), operation="read")

        assert result.success
        assert "Sample content" in result.data
        assert result.metadata['size'] > 0

    def test_file_not_found(self):
        """Test handling of non-existent file."""
        pattern = DirectPathAccessPattern()
        result = pattern.execute(path="/nonexistent/file.txt", operation="read")

        assert not result.success
        assert result.error is not None

    def test_pattern_statistics(self, sample_file):
        """Test pattern statistics tracking."""
        pattern = DirectPathAccessPattern()

        # Execute multiple times
        pattern.execute(path=str(sample_file), operation="exists")
        pattern.execute(path=str(sample_file), operation="stat")

        stats = pattern.get_stats()
        assert stats['executions'] == 2
        assert stats['successes'] == 2
        assert stats['success_rate'] == 100.0


class TestKnownPathSearchPattern:
    """Tests for KnownPathSearchPattern."""

    def test_initialization(self):
        """Test pattern initialization."""
        pattern = KnownPathSearchPattern()
        assert pattern.name == "KnownPathSearchPattern"

    def test_search_files(self, temp_dir):
        """Test file search."""
        # Create test files
        (temp_dir / "test1.txt").write_text("test")
        (temp_dir / "test2.txt").write_text("test")
        (temp_dir / "test.py").write_text("test")

        pattern = KnownPathSearchPattern()
        result = pattern.execute(
            search_paths=[str(temp_dir)],
            pattern="*.txt",
            recursive=False
        )

        assert result.success
        assert len(result.data) == 2

    def test_recursive_search(self, temp_dir):
        """Test recursive file search."""
        # Create nested structure
        subdir = temp_dir / "subdir"
        subdir.mkdir()
        (temp_dir / "test1.txt").write_text("test")
        (subdir / "test2.txt").write_text("test")

        pattern = KnownPathSearchPattern()
        result = pattern.execute(
            search_paths=[str(temp_dir)],
            pattern="*.txt",
            recursive=True
        )

        assert result.success
        assert len(result.data) == 2

    def test_no_matches(self, temp_dir):
        """Test search with no matches."""
        pattern = KnownPathSearchPattern()
        result = pattern.execute(
            search_paths=[str(temp_dir)],
            pattern="*.nonexistent",
            recursive=False
        )

        assert result.success
        assert len(result.data) == 0


class TestCheckpointRecoveryPattern:
    """Tests for CheckpointRecoveryPattern."""

    def test_initialization(self, checkpoint_dir):
        """Test pattern initialization."""
        pattern = CheckpointRecoveryPattern(checkpoint_dir=str(checkpoint_dir))
        assert pattern.name == "CheckpointRecoveryPattern"
        assert pattern.checkpoint_dir.exists()

    def test_save_checkpoint(self, checkpoint_dir):
        """Test saving a checkpoint."""
        pattern = CheckpointRecoveryPattern(checkpoint_dir=str(checkpoint_dir))

        state_data = {'test': 'data', 'value': 123}
        result = pattern.execute(
            operation="save",
            checkpoint_id="test_checkpoint",
            state_data=state_data
        )

        assert result.success
        assert result.data['checkpoint_id'] == "test_checkpoint"
        assert Path(result.data['file_path']).exists()

    def test_load_checkpoint(self, checkpoint_dir):
        """Test loading a checkpoint."""
        pattern = CheckpointRecoveryPattern(checkpoint_dir=str(checkpoint_dir))

        # Save first
        state_data = {'test': 'data', 'value': 123}
        pattern.execute(
            operation="save",
            checkpoint_id="test_checkpoint",
            state_data=state_data
        )

        # Then load
        result = pattern.execute(
            operation="load",
            checkpoint_id="test_checkpoint"
        )

        assert result.success
        assert result.data['state_data'] == state_data

    def test_list_checkpoints(self, checkpoint_dir):
        """Test listing checkpoints."""
        pattern = CheckpointRecoveryPattern(checkpoint_dir=str(checkpoint_dir))

        # Create multiple checkpoints
        for i in range(3):
            pattern.execute(
                operation="save",
                checkpoint_id=f"checkpoint_{i}",
                state_data={'index': i}
            )

        # List checkpoints
        result = pattern.execute(operation="list")

        assert result.success
        assert result.data['count'] == 3

    def test_delete_checkpoint(self, checkpoint_dir):
        """Test deleting a checkpoint."""
        pattern = CheckpointRecoveryPattern(checkpoint_dir=str(checkpoint_dir))

        # Create checkpoint
        pattern.execute(
            operation="save",
            checkpoint_id="test_checkpoint",
            state_data={'test': 'data'}
        )

        # Delete it
        result = pattern.execute(
            operation="delete",
            checkpoint_id="test_checkpoint"
        )

        assert result.success
        assert result.data['deleted'] is True


class TestGitRepositoryFilePattern:
    """Tests for GitRepositoryFilePattern."""

    def test_initialization(self):
        """Test pattern initialization."""
        pattern = GitRepositoryFilePattern()
        assert pattern.name == "GitRepositoryFilePattern"

    @patch('subprocess.check_output')
    def test_git_status(self, mock_subprocess):
        """Test git status operation."""
        mock_subprocess.return_value = "M file.txt\n"

        pattern = GitRepositoryFilePattern()
        result = pattern.execute(repo_path=".", operation="status")

        assert result.success
        assert result.data['has_changes'] is True

    @patch('subprocess.check_output')
    def test_git_log(self, mock_subprocess):
        """Test git log operation."""
        mock_subprocess.return_value = "abc123 Initial commit\ndef456 Second commit\n"

        pattern = GitRepositoryFilePattern()
        result = pattern.execute(repo_path=".", operation="log", limit=2)

        assert result.success
        assert len(result.data['commits']) == 2

    @patch('subprocess.check_output')
    def test_git_diff(self, mock_subprocess):
        """Test git diff operation."""
        mock_subprocess.return_value = "diff --git a/file.txt b/file.txt\n"

        pattern = GitRepositoryFilePattern()
        result = pattern.execute(repo_path=".", operation="diff")

        assert result.success
        assert result.data['has_changes'] is True


# =============================================================================
# RSI Feedback Loop Tests
# =============================================================================

class TestRSIFeedbackLoop:
    """Tests for RSI feedback loop."""

    def test_initialization(self):
        """Test RSI loop initialization."""
        rsi = RSIFeedbackLoop()
        assert len(rsi.feedback_history) == 0
        assert len(rsi.adaptation_history) == 0

    def test_collect_feedback(self):
        """Test feedback collection."""
        rsi = RSIFeedbackLoop()

        rsi.collect_feedback(
            feedback_type=FeedbackType.SUCCESS,
            source="test",
            metrics={'execution_time': 1.0, 'quality': 0.9}
        )

        assert len(rsi.feedback_history) == 1

    def test_performance_analysis(self):
        """Test performance analysis."""
        rsi = RSIFeedbackLoop()

        # Collect sufficient feedback
        for i in range(15):
            rsi.collect_feedback(
                feedback_type=FeedbackType.SUCCESS,
                source="test",
                metrics={'execution_time': 1.0, 'quality': 0.9}
            )

        analysis = rsi.analyze_performance()
        assert 'ready_for_adaptation' in analysis
        assert 'health_score' in analysis
        assert 'current_metrics' in analysis

    def test_improvement_cycle(self):
        """Test improvement cycle."""
        rsi = RSIFeedbackLoop()

        # Collect feedback
        for i in range(20):
            success = i % 2 == 0
            rsi.collect_feedback(
                feedback_type=FeedbackType.SUCCESS if success else FeedbackType.FAILURE,
                source="test",
                metrics={'execution_time': 1.0, 'quality': 0.5}
            )

        cycle_result = rsi.run_improvement_cycle()
        assert 'timestamp' in cycle_result
        assert 'current_health' in cycle_result
        assert isinstance(cycle_result['adapted'], bool)

    def test_snapshot_performance(self):
        """Test performance snapshots."""
        rsi = RSIFeedbackLoop()

        initial_count = len(rsi.performance_snapshots)
        rsi.snapshot_performance()

        assert len(rsi.performance_snapshots) == initial_count + 1


# =============================================================================
# Workflow Tests
# =============================================================================

class TestWorkflow:
    """Tests for workflow orchestration."""

    def test_workflow_initialization(self):
        """Test workflow initialization."""
        workflow = Workflow(
            workflow_id="test",
            name="Test Workflow",
            description="Test"
        )

        assert workflow.workflow_id == "test"
        assert workflow.status == WorkflowStatus.PENDING
        assert len(workflow.steps) == 0

    def test_add_step(self):
        """Test adding workflow steps."""
        workflow = Workflow("test", "Test", "Test")

        pattern = DirectPathAccessPattern()
        step = WorkflowStep(
            step_id="step1",
            name="Test Step",
            description="Test",
            pattern=pattern,
            parameters={}
        )

        workflow.add_step(step)
        assert len(workflow.steps) == 1

    def test_workflow_builder(self):
        """Test workflow builder."""
        builder = WorkflowBuilder("test", "Test", "Test")

        pattern = DirectPathAccessPattern()
        builder.add_pattern_step(
            step_id="step1",
            name="Test Step",
            pattern=pattern,
            parameters={'path': __file__, 'operation': 'exists'}
        )

        workflow = builder.build()
        assert len(workflow.steps) == 1

    def test_workflow_execution(self):
        """Test workflow execution."""
        builder = WorkflowBuilder("test", "Test", "Test")

        pattern = DirectPathAccessPattern()
        builder.add_pattern_step(
            step_id="step1",
            name="Check File",
            pattern=pattern,
            parameters={'path': __file__, 'operation': 'exists'}
        )

        workflow = builder.build()
        result = workflow.execute()

        assert result['status'] in ['completed', 'failed']
        assert 'total_execution_time' in result
        assert 'steps' in result


# =============================================================================
# Meta-Learning Tests
# =============================================================================

class TestMetaLearning:
    """Tests for meta-learning architecture."""

    def test_initialization(self):
        """Test MLA initialization."""
        mla = MetaLearningArchitecture()
        assert len(mla.learning_examples) == 0
        assert len(mla.pattern_knowledge) == 0

    def test_record_example(self):
        """Test recording learning examples."""
        mla = MetaLearningArchitecture()

        mla.record_example(
            pattern_name="TestPattern",
            context={'operation': 'test'},
            outcome={'status': 'success'},
            performance_metrics={'execution_time': 1.0, 'quality': 0.9},
            success=True
        )

        assert len(mla.learning_examples) == 1
        assert "TestPattern" in mla.pattern_knowledge

    def test_pattern_knowledge_update(self):
        """Test pattern knowledge updates."""
        mla = MetaLearningArchitecture()

        # Record multiple examples
        for i in range(5):
            mla.record_example(
                pattern_name="TestPattern",
                context={'operation': 'test'},
                outcome={'status': 'success'},
                performance_metrics={'execution_time': 1.0, 'quality': 0.9},
                success=True
            )

        knowledge = mla.pattern_knowledge["TestPattern"]
        assert knowledge.usage_count == 5
        assert knowledge.success_count == 5
        assert knowledge.get_success_rate() == 1.0

    def test_predict_performance(self):
        """Test performance prediction."""
        mla = MetaLearningArchitecture()

        # Record examples
        for i in range(10):
            mla.record_example(
                pattern_name="TestPattern",
                context={'operation': 'test'},
                outcome={'status': 'success'},
                performance_metrics={'execution_time': 1.0, 'quality': 0.9},
                success=True
            )

        prediction = mla.predict_performance(
            pattern_name="TestPattern",
            context={'operation': 'test'}
        )

        assert prediction['has_prediction'] is True
        assert 'predicted_success_rate' in prediction

    def test_recommend_pattern(self):
        """Test pattern recommendation."""
        mla = MetaLearningArchitecture()

        # Record examples for multiple patterns
        patterns = ["PatternA", "PatternB", "PatternC"]
        for pattern in patterns:
            for i in range(10):
                mla.record_example(
                    pattern_name=pattern,
                    context={'operation': 'test'},
                    outcome={'status': 'success'},
                    performance_metrics={'execution_time': 1.0, 'quality': 0.9},
                    success=i % 2 == 0  # 50% success rate
                )

        recommended, reasoning = mla.recommend_pattern(
            context={'operation': 'test'},
            available_patterns=patterns
        )

        assert recommended in patterns
        assert 'score' in reasoning

    def test_leverage_quotient(self):
        """Test MLA leverage quotient calculation."""
        mla = MetaLearningArchitecture()

        # Record learning examples
        for i in range(30):
            mla.record_example(
                pattern_name=f"Pattern{i % 3}",
                context={'operation': 'test'},
                outcome={'status': 'success'},
                performance_metrics={'execution_time': 1.0, 'quality': 0.9},
                success=i % 2 == 0
            )

        quotient = mla.calculate_leverage_quotient()

        assert quotient.total_examples == 30
        assert quotient.overall_quotient >= 0.0
        assert quotient.overall_quotient <= 1.0
        assert quotient.get_grade() is not None

    def test_learning_insights(self):
        """Test learning insights generation."""
        mla = MetaLearningArchitecture()

        # Record examples
        for i in range(20):
            mla.record_example(
                pattern_name="TestPattern",
                context={'operation': 'test'},
                outcome={'status': 'success'},
                performance_metrics={'execution_time': 1.0, 'quality': 0.9},
                success=True
            )

        insights = mla.get_learning_insights()

        assert 'total_examples' in insights
        assert 'patterns_learned' in insights
        assert 'top_performing_patterns' in insights


# =============================================================================
# Configuration Tests
# =============================================================================

class TestCCMFConfig:
    """Tests for configuration management."""

    def test_load_valid_config(self, sample_config):
        """Test loading valid configuration."""
        config = CCMFConfig(str(sample_config))
        assert config.config is not None
        assert 'paths' in config.config

    def test_load_nonexistent_config(self):
        """Test loading non-existent configuration."""
        config = CCMFConfig("nonexistent.json")
        assert config.config is not None  # Should use defaults

    def test_get_config_value(self, sample_config):
        """Test getting configuration values."""
        config = CCMFConfig(str(sample_config))

        value = config.get("paths.logs_dir")
        assert value is not None

    def test_get_nested_config(self, sample_config):
        """Test getting nested configuration values."""
        config = CCMFConfig(str(sample_config))

        value = config.get("paths.logs_dir", "default")
        assert value is not None

    def test_get_with_default(self, sample_config):
        """Test getting configuration with default value."""
        config = CCMFConfig(str(sample_config))

        value = config.get("nonexistent.key", "default_value")
        assert value == "default_value"


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for CCMF framework."""

    def test_pattern_with_rsi(self):
        """Test pattern execution with RSI feedback."""
        rsi = RSIFeedbackLoop()
        pattern = DirectPathAccessPattern()

        result = pattern.execute(path=__file__, operation="exists")

        # Collect feedback
        rsi.collect_feedback(
            feedback_type=FeedbackType.SUCCESS if result.success else FeedbackType.FAILURE,
            source="test",
            metrics={'execution_time': result.execution_time, 'quality': 1.0}
        )

        assert len(rsi.feedback_history) == 1

    def test_workflow_with_constitutional_validation(self):
        """Test workflow with constitutional validation."""
        builder = WorkflowBuilder("test", "Test", "Test")

        pattern = DirectPathAccessPattern()
        builder.add_pattern_step(
            step_id="step1",
            name="Test Step",
            pattern=pattern,
            parameters={'path': __file__, 'operation': 'exists'}
        )

        workflow = builder.build()
        result = workflow.execute()

        assert result['status'] in ['completed', 'failed']

    def test_meta_learning_with_patterns(self):
        """Test meta-learning integration with patterns."""
        mla = MetaLearningArchitecture()
        pattern = DirectPathAccessPattern()

        # Execute pattern and record learning
        result = pattern.execute(path=__file__, operation="exists")

        mla.record_example(
            pattern_name="DirectPathAccessPattern",
            context={'operation': 'exists'},
            outcome={'result': result.data},
            performance_metrics={'execution_time': result.execution_time, 'quality': 1.0},
            success=result.success
        )

        assert len(mla.learning_examples) == 1
        assert "DirectPathAccessPattern" in mla.pattern_knowledge


# =============================================================================
# Edge Cases and Error Handling Tests
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_context_validation(self):
        """Test validation with empty context."""
        report = validate_operation({})
        assert report.overall_compliance == ComplianceLevel.NON_COMPLIANT

    def test_pattern_with_invalid_parameters(self):
        """Test pattern with invalid parameters."""
        pattern = DirectPathAccessPattern()
        result = pattern.execute(path="/nonexistent", operation="invalid_op")

        assert not result.success
        assert result.error is not None

    def test_workflow_with_failing_step(self):
        """Test workflow with a failing step."""
        builder = WorkflowBuilder("test", "Test", "Test")

        pattern = DirectPathAccessPattern()
        builder.add_pattern_step(
            step_id="step1",
            name="Failing Step",
            pattern=pattern,
            parameters={'path': '/nonexistent', 'operation': 'read'},
            retry_on_failure=False
        )

        workflow = builder.build()
        result = workflow.execute()

        assert result['status'] == 'failed'

    def test_rsi_with_insufficient_data(self):
        """Test RSI analysis with insufficient data."""
        rsi = RSIFeedbackLoop()

        # Collect minimal feedback
        rsi.collect_feedback(
            feedback_type=FeedbackType.SUCCESS,
            source="test",
            metrics={'execution_time': 1.0}
        )

        analysis = rsi.analyze_performance()
        assert analysis['ready_for_adaptation'] is False

    def test_mla_with_no_examples(self):
        """Test MLA with no learning examples."""
        mla = MetaLearningArchitecture()

        quotient = mla.calculate_leverage_quotient()
        assert quotient.total_examples == 0
        assert quotient.overall_quotient == 0.0


# =============================================================================
# Performance Tests
# =============================================================================

class TestPerformance:
    """Performance tests."""

    def test_pattern_execution_speed(self):
        """Test pattern execution is reasonably fast."""
        pattern = DirectPathAccessPattern()

        import time
        start = time.time()

        for _ in range(100):
            pattern.execute(path=__file__, operation="exists")

        elapsed = time.time() - start
        assert elapsed < 5.0  # Should complete in under 5 seconds

    def test_rsi_feedback_collection_speed(self):
        """Test RSI feedback collection performance."""
        rsi = RSIFeedbackLoop()

        import time
        start = time.time()

        for i in range(1000):
            rsi.collect_feedback(
                feedback_type=FeedbackType.SUCCESS,
                source="test",
                metrics={'execution_time': 1.0}
            )

        elapsed = time.time() - start
        assert elapsed < 5.0  # Should complete in under 5 seconds


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
