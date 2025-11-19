"""
Claude Code Mastery Framework (CCMF) v1.0 - Unit Tests

Comprehensive test suite for all CCMF modules.

Test Coverage:
- Constitutional validation
- All pattern implementations
- RSI feedback loop
- State recovery workflows
- Edge cases and error handling

Run with: python -m unittest ccmf_tests
Or: python ccmf_tests.py
"""

import unittest
import tempfile
import os
from datetime import datetime
from typing import Any, Dict

from agno.ccmf_constitutional import (
    ConstitutionalValidator,
    BasePattern,
    ProtocolViolation,
    ExecutionLog,
    Severity
)
from agno.ccmf_patterns import (
    DirectPathAccessPattern,
    KnownPathSearchPattern,
    GitRepositoryFilePattern
)
from agno.ccmf_workflows import (
    CheckpointRecoveryPattern,
    GitStateAnalysisPattern,
    CompositeStateRecoveryPattern
)
from agno.ccmf_rsi_loop import (
    ExecutionAnalyzer,
    PatternOptimizer,
    RSIFeedbackLoop
)


class TestConstitutionalValidator(unittest.TestCase):
    """Test suite for ConstitutionalValidator class."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = ConstitutionalValidator()

    def test_initialization(self):
        """Test validator initialization."""
        self.assertIsInstance(self.validator, ConstitutionalValidator)
        self.assertEqual(len(self.validator.violations), 0)
        self.assertEqual(self.validator.validation_count, 0)

    def test_forbidden_methods_blocked(self):
        """Test that forbidden methods are blocked."""
        forbidden = ['read_list', 'file_list', 'file_find_by_name']

        for method in forbidden:
            is_valid, violation = self.validator.validate_method(method)

            self.assertFalse(is_valid, f"{method} should be blocked")
            self.assertIsNotNone(violation)
            self.assertEqual(violation.protocol, "TFCP")
            self.assertEqual(violation.severity, Severity.CRITICAL)

    def test_allowed_methods_pass(self):
        """Test that allowed methods pass validation."""
        # Method validation only blocks prohibited methods
        # So any non-prohibited method should pass method validation
        allowed = ['powershell_subprocess', 'git_command', 'other_method']

        for method in allowed:
            is_valid, violation = self.validator.validate_method(method)

            self.assertTrue(is_valid, f"{method} should be allowed")
            self.assertIsNone(violation)

    def test_operation_validation(self):
        """Test operation validation."""
        # Test permitted operations
        is_valid, violation = self.validator.validate_operation(
            'powershell_subprocess',
            'test operation'
        )
        self.assertTrue(is_valid)
        self.assertIsNone(violation)

        # Test invalid operation
        is_valid, violation = self.validator.validate_operation(
            'invalid_operation',
            'test'
        )
        self.assertFalse(is_valid)
        self.assertIsNotNone(violation)
        self.assertEqual(violation.protocol, "OFAP")

    def test_file_operation_validation(self):
        """Test file operation validation."""
        # Test valid file operation
        is_valid, violation = self.validator.validate_file_operation(
            operation='read',
            file_path='/test/path',
            method='powershell_subprocess'
        )
        self.assertTrue(is_valid)

        # Test forbidden method
        is_valid, violation = self.validator.validate_file_operation(
            operation='read',
            file_path='/test/path',
            method='read_list'
        )
        self.assertFalse(is_valid)
        self.assertIsNotNone(violation)

    def test_leverage_quotient_calculation(self):
        """Test Leverage Quotient calculation."""
        # Test standard calculation
        lq = self.validator.calculate_leverage_quotient(
            progress_towards_goal=0.8,
            energy_efficiency=0.9,
            cost=0.2
        )

        # LQ = (0.6 * 0.8 + 0.4 * 0.9) / 0.2 = 0.84 / 0.2 = 4.2
        self.assertAlmostEqual(lq, 4.2, places=2)

        # Test with different weights
        lq2 = self.validator.calculate_leverage_quotient(
            progress_towards_goal=1.0,
            energy_efficiency=0.5,
            cost=0.5,
            progress_weight=0.7,
            efficiency_weight=0.3
        )

        # LQ = (0.7 * 1.0 + 0.3 * 0.5) / 0.5 = 0.85 / 0.5 = 1.7
        self.assertAlmostEqual(lq2, 1.7, places=2)

    def test_leverage_quotient_edge_cases(self):
        """Test LQ calculation edge cases."""
        # Test zero cost raises error
        with self.assertRaises(ValueError):
            self.validator.calculate_leverage_quotient(
                progress_towards_goal=1.0,
                energy_efficiency=1.0,
                cost=0.0
            )

        # Test invalid weights
        with self.assertRaises(ValueError):
            self.validator.calculate_leverage_quotient(
                progress_towards_goal=1.0,
                energy_efficiency=1.0,
                cost=1.0,
                progress_weight=0.5,
                efficiency_weight=0.6  # Sum > 1.0
            )

    def test_violation_tracking(self):
        """Test that violations are tracked correctly."""
        initial_count = len(self.validator.violations)

        # Trigger violation
        self.validator.validate_method('read_list')

        self.assertEqual(len(self.validator.violations), initial_count + 1)

        # Get violations by protocol
        tfcp_violations = self.validator.get_violations(protocol="TFCP")
        self.assertGreater(len(tfcp_violations), 0)

        # Get violations by severity
        critical_violations = self.validator.get_violations(severity=Severity.CRITICAL)
        self.assertGreater(len(critical_violations), 0)

    def test_violation_report_generation(self):
        """Test violation report generation."""
        # Trigger some violations
        self.validator.validate_method('read_list')
        self.validator.validate_method('file_list')

        report = self.validator.generate_violation_report()

        self.assertIn("CCMF CONSTITUTIONAL VALIDATION REPORT", report)
        self.assertIn("Total Validations", report)
        self.assertIn("Total Violations", report)

    def test_clear_violations(self):
        """Test clearing violations."""
        self.validator.validate_method('read_list')
        self.assertGreater(len(self.validator.violations), 0)

        self.validator.clear_violations()
        self.assertEqual(len(self.validator.violations), 0)


class TestGitRepositoryFilePattern(unittest.TestCase):
    """Test suite for GitRepositoryFilePattern."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = ConstitutionalValidator()
        self.pattern = GitRepositoryFilePattern(self.validator)
        self.test_repo = '/home/user/agno'  # Assuming this exists

    def test_initialization(self):
        """Test pattern initialization."""
        self.assertEqual(self.pattern.pattern_id, "git_repo_file_v1")
        self.assertEqual(self.pattern.pattern_name, "Git Repository File Pattern")
        self.assertIn("ASAEP", self.pattern.constitutional_requirements)
        self.assertIn("OFAP", self.pattern.constitutional_requirements)

    def test_list_operation(self):
        """Test git ls-files operation."""
        success, result, error = self.pattern.execute_with_validation({
            'repo_path': self.test_repo,
            'operation': 'list',
            'file_pattern': '*.md'
        })

        if success:
            self.assertTrue(result.get('success'))
            self.assertIn('files', result)
            self.assertIn('count', result)
            self.assertIsInstance(result['files'], list)

    def test_invalid_operation(self):
        """Test invalid operation handling."""
        with self.assertRaises(ValueError):
            self.pattern.execute({
                'repo_path': self.test_repo,
                'operation': 'invalid_op',
                'file_pattern': '*.md'
            })

    def test_missing_inputs(self):
        """Test missing required inputs."""
        with self.assertRaises(ValueError):
            self.pattern.execute({
                'repo_path': self.test_repo,
                # Missing operation and file_pattern
            })

    def test_lq_score(self):
        """Test LQ score calculation."""
        success, result, error = self.pattern.execute_with_validation({
            'repo_path': self.test_repo,
            'operation': 'list',
            'file_pattern': '*.py'
        })

        if success:
            # Git patterns should have high LQ (~9.0)
            self.assertGreater(self.pattern.average_lq, 8.0)

    def test_performance_tracking(self):
        """Test performance metrics tracking."""
        # Execute pattern
        self.pattern.execute_with_validation({
            'repo_path': self.test_repo,
            'operation': 'list',
            'file_pattern': '*.py'
        })

        perf = self.pattern.get_performance_summary()

        self.assertIn('total_executions', perf)
        self.assertIn('successful_executions', perf)
        self.assertIn('success_rate', perf)
        self.assertIn('average_lq', perf)
        self.assertGreater(perf['total_executions'], 0)

    def test_execution_logs(self):
        """Test execution logging."""
        self.pattern.execute_with_validation({
            'repo_path': self.test_repo,
            'operation': 'list',
            'file_pattern': '*.md'
        })

        logs = self.pattern.get_execution_logs(limit=1)
        self.assertEqual(len(logs), 1)

        log = logs[0]
        self.assertIsInstance(log, ExecutionLog)
        self.assertEqual(log.pattern_id, self.pattern.pattern_id)


class TestDirectPathAccessPattern(unittest.TestCase):
    """Test suite for DirectPathAccessPattern."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = ConstitutionalValidator()
        self.pattern = DirectPathAccessPattern(self.validator)

    def test_initialization(self):
        """Test pattern initialization."""
        self.assertEqual(self.pattern.pattern_id, "direct_path_access_v1")
        self.assertIn("ASAEP", self.pattern.constitutional_requirements)

    def test_invalid_operation(self):
        """Test invalid operation."""
        with self.assertRaises(ValueError):
            self.pattern.execute({
                'file_path': '/test/path',
                'operation': 'invalid'
            })

    def test_missing_inputs(self):
        """Test missing inputs."""
        with self.assertRaises(ValueError):
            self.pattern.execute({
                'file_path': '/test/path'
                # Missing operation
            })


class TestKnownPathSearchPattern(unittest.TestCase):
    """Test suite for KnownPathSearchPattern."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = ConstitutionalValidator()
        self.pattern = KnownPathSearchPattern(self.validator)

    def test_initialization(self):
        """Test pattern initialization."""
        self.assertEqual(self.pattern.pattern_id, "known_path_search_v1")

    def test_invalid_inputs(self):
        """Test invalid input handling."""
        # Non-list search_paths
        with self.assertRaises(ValueError):
            self.pattern.execute({
                'search_paths': 'not_a_list',
                'read_content': False
            })

        # Empty search_paths
        with self.assertRaises(ValueError):
            self.pattern.execute({
                'search_paths': [],
                'read_content': False
            })


class TestExecutionAnalyzer(unittest.TestCase):
    """Test suite for ExecutionAnalyzer."""

    def setUp(self):
        """Set up test fixtures."""
        self.analyzer = ExecutionAnalyzer()
        self.validator = ConstitutionalValidator()

    def test_initialization(self):
        """Test analyzer initialization."""
        self.assertIsInstance(self.analyzer, ExecutionAnalyzer)
        self.assertEqual(len(self.analyzer.analysis_cache), 0)

    def test_analyze_pattern_no_data(self):
        """Test analyzing pattern with no execution data."""
        pattern = GitRepositoryFilePattern(self.validator)

        analysis = self.analyzer.analyze_pattern_performance(pattern)

        self.assertEqual(analysis['total_executions'], 0)
        self.assertEqual(analysis['analysis_status'], 'insufficient_data')

    def test_analyze_pattern_with_data(self):
        """Test analyzing pattern with execution data."""
        pattern = GitRepositoryFilePattern(self.validator)

        # Execute pattern
        pattern.execute_with_validation({
            'repo_path': '/home/user/agno',
            'operation': 'list',
            'file_pattern': '*.py'
        })

        analysis = self.analyzer.analyze_pattern_performance(pattern)

        self.assertGreater(analysis['total_executions'], 0)
        self.assertIn('success_rate', analysis)
        self.assertIn('avg_lq', analysis)
        self.assertIn('recommendations', analysis)

    def test_identify_bottlenecks(self):
        """Test bottleneck identification."""
        pattern1 = GitRepositoryFilePattern(self.validator)
        pattern2 = DirectPathAccessPattern(self.validator)

        # Execute patterns
        pattern1.execute_with_validation({
            'repo_path': '/home/user/agno',
            'operation': 'list',
            'file_pattern': '*.py'
        })

        bottlenecks = self.analyzer.identify_bottlenecks([pattern1, pattern2])

        self.assertIsInstance(bottlenecks, list)
        # Should be sorted by severity
        if len(bottlenecks) > 1:
            self.assertGreaterEqual(
                bottlenecks[0]['severity_score'],
                bottlenecks[1]['severity_score']
            )

    def test_calculate_improvement_opportunities(self):
        """Test improvement opportunity calculation."""
        pattern = GitRepositoryFilePattern(self.validator)

        # Execute pattern
        pattern.execute_with_validation({
            'repo_path': '/home/user/agno',
            'operation': 'list',
            'file_pattern': '*.py'
        })

        opportunity = self.analyzer.calculate_improvement_opportunities(pattern)

        self.assertIsInstance(opportunity, float)
        self.assertGreaterEqual(opportunity, 0.0)


class TestPatternOptimizer(unittest.TestCase):
    """Test suite for PatternOptimizer."""

    def setUp(self):
        """Set up test fixtures."""
        self.analyzer = ExecutionAnalyzer()
        self.optimizer = PatternOptimizer(self.analyzer)
        self.validator = ConstitutionalValidator()

    def test_initialization(self):
        """Test optimizer initialization."""
        self.assertIsInstance(self.optimizer, PatternOptimizer)
        self.assertIsInstance(self.optimizer.analyzer, ExecutionAnalyzer)

    def test_suggest_optimizations(self):
        """Test optimization suggestions."""
        pattern = GitRepositoryFilePattern(self.validator)

        # Execute pattern
        for _ in range(5):
            pattern.execute_with_validation({
                'repo_path': '/home/user/agno',
                'operation': 'list',
                'file_pattern': '*.py'
            })

        optimizations = self.optimizer.suggest_optimizations(pattern)

        self.assertIsInstance(optimizations, list)
        if optimizations:
            opt = optimizations[0]
            self.assertIn('optimization_type', opt)
            self.assertIn('description', opt)
            self.assertIn('expected_lq_improvement', opt)
            self.assertIn('priority', opt)

    def test_optimize_timeout_values(self):
        """Test timeout optimization."""
        pattern = GitRepositoryFilePattern(self.validator)

        # Execute pattern multiple times
        for _ in range(10):
            pattern.execute_with_validation({
                'repo_path': '/home/user/agno',
                'operation': 'list',
                'file_pattern': '*.py'
            })

        timeout_opt = self.optimizer.optimize_timeout_values(pattern)

        self.assertIn('status', timeout_opt)
        if timeout_opt['status'] == 'success':
            self.assertIn('recommended_timeout', timeout_opt)
            self.assertIn('current_stats', timeout_opt)


class TestRSIFeedbackLoop(unittest.TestCase):
    """Test suite for RSIFeedbackLoop."""

    def setUp(self):
        """Set up test fixtures."""
        self.rsi_loop = RSIFeedbackLoop()
        self.validator = ConstitutionalValidator()

    def test_initialization(self):
        """Test RSI loop initialization."""
        self.assertIsInstance(self.rsi_loop, RSIFeedbackLoop)
        self.assertEqual(len(self.rsi_loop.patterns), 0)
        self.assertEqual(self.rsi_loop.cycle_count, 0)

    def test_register_pattern(self):
        """Test pattern registration."""
        pattern = GitRepositoryFilePattern(self.validator)

        self.rsi_loop.register_pattern(pattern)

        self.assertEqual(len(self.rsi_loop.patterns), 1)
        self.assertIn(pattern.pattern_id, self.rsi_loop.patterns)

    def test_unregister_pattern(self):
        """Test pattern unregistration."""
        pattern = GitRepositoryFilePattern(self.validator)

        self.rsi_loop.register_pattern(pattern)
        success = self.rsi_loop.unregister_pattern(pattern.pattern_id)

        self.assertTrue(success)
        self.assertEqual(len(self.rsi_loop.patterns), 0)

        # Try unregistering non-existent pattern
        success = self.rsi_loop.unregister_pattern("nonexistent")
        self.assertFalse(success)

    def test_run_improvement_cycle(self):
        """Test running improvement cycle."""
        pattern = GitRepositoryFilePattern(self.validator)

        # Execute pattern
        pattern.execute_with_validation({
            'repo_path': '/home/user/agno',
            'operation': 'list',
            'file_pattern': '*.py'
        })

        self.rsi_loop.register_pattern(pattern)

        cycle_result = self.rsi_loop.run_improvement_cycle()

        self.assertIn('cycle_number', cycle_result)
        self.assertEqual(cycle_result['cycle_number'], 1)
        self.assertIn('patterns_analyzed', cycle_result)
        self.assertIn('improvement_summary', cycle_result)

    def test_get_improvement_history(self):
        """Test getting improvement history."""
        pattern = GitRepositoryFilePattern(self.validator)

        pattern.execute_with_validation({
            'repo_path': '/home/user/agno',
            'operation': 'list',
            'file_pattern': '*.py'
        })

        self.rsi_loop.register_pattern(pattern)
        self.rsi_loop.run_improvement_cycle()

        history = self.rsi_loop.get_improvement_history()

        self.assertIsInstance(history, list)
        self.assertGreater(len(history), 0)

    def test_export_rsi_report(self):
        """Test exporting RSI report."""
        pattern = GitRepositoryFilePattern(self.validator)

        pattern.execute_with_validation({
            'repo_path': '/home/user/agno',
            'operation': 'list',
            'file_pattern': '*.py'
        })

        self.rsi_loop.register_pattern(pattern)
        self.rsi_loop.run_improvement_cycle()

        report = self.rsi_loop.export_rsi_report()

        self.assertIsInstance(report, str)
        self.assertIn("CCMF_RSI_Report", report)
        self.assertIn("report_version", report)

    def test_get_summary(self):
        """Test getting RSI loop summary."""
        summary = self.rsi_loop.get_summary()

        self.assertIn('cycles_run', summary)
        self.assertIn('patterns_registered', summary)
        self.assertIn('overall_success_rate', summary)


class TestGitStateAnalysisPattern(unittest.TestCase):
    """Test suite for GitStateAnalysisPattern."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = ConstitutionalValidator()
        self.pattern = GitStateAnalysisPattern(self.validator)

    def test_initialization(self):
        """Test pattern initialization."""
        self.assertEqual(self.pattern.pattern_id, "git_state_analysis_v1")

    def test_analysis_with_valid_repo(self):
        """Test analysis with valid repository."""
        success, result, error = self.pattern.execute_with_validation({
            'repo_path': '/home/user/agno',
            'analysis_depth': 5
        })

        if success:
            self.assertIn('current_branch', result)
            self.assertIn('is_clean', result)
            self.assertIn('uncommitted_files', result)
            self.assertIn('recent_commits', result)


class TestCompositeStateRecoveryPattern(unittest.TestCase):
    """Test suite for CompositeStateRecoveryPattern."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = ConstitutionalValidator()
        self.pattern = CompositeStateRecoveryPattern(self.validator)

    def test_initialization(self):
        """Test pattern initialization."""
        self.assertEqual(self.pattern.pattern_id, "composite_state_recovery_v1")

    def test_missing_inputs(self):
        """Test missing required inputs."""
        with self.assertRaises(ValueError):
            self.pattern.execute({
                'checkpoint_paths': []
                # Missing repo_path and fallback_paths
            })


def run_test_suite():
    """Run the complete test suite."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    test_classes = [
        TestConstitutionalValidator,
        TestGitRepositoryFilePattern,
        TestDirectPathAccessPattern,
        TestKnownPathSearchPattern,
        TestExecutionAnalyzer,
        TestPatternOptimizer,
        TestRSIFeedbackLoop,
        TestGitStateAnalysisPattern,
        TestCompositeStateRecoveryPattern,
    ]

    for test_class in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(test_class))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "=" * 70)
    print("CCMF Test Suite Results")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("=" * 70)

    return result


if __name__ == '__main__':
    run_test_suite()
