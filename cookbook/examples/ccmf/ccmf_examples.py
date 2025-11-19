"""
CCMF Comprehensive Examples - SESSION 2
========================================

This module provides comprehensive, working examples for ALL CCMF patterns
and demonstrates the full power and versatility of the Constitutional
Cognitive Meta-Framework.

Examples include:
1. All cognitive patterns (DirectPathAccessPattern, KnownPathSearchPattern, etc.)
2. Constitutional compliance validation
3. RSI feedback loop integration
4. Workflow orchestration
5. Meta-learning and leverage quotient calculations
6. End-to-end integrated scenarios

Each example is executable and demonstrates real-world usage.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Import all CCMF modules
from ccmf_constitutional import (
    ConstitutionalFramework, ConstitutionalPrinciple,
    PrincipleCategory, validate_operation, ComplianceLevel
)
from ccmf_patterns import (
    DirectPathAccessPattern, KnownPathSearchPattern,
    GitRepositoryFilePattern, CheckpointRecoveryPattern,
    GitStateAnalysisPattern, CompositeStateRecoveryPattern,
    get_pattern
)
from ccmf_rsi_loop import RSIFeedbackLoop, FeedbackType
from ccmf_workflows import Workflow, WorkflowBuilder, WorkflowStep
from ccmf_meta_learning import MetaLearningArchitecture, MLALeverageQuotient


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'=' * 70}")
    print(f"{title.center(70)}")
    print('=' * 70)


def print_subsection(title: str):
    """Print a formatted subsection header."""
    print(f"\n{'-' * 70}")
    print(f"  {title}")
    print('-' * 70)


# =============================================================================
# EXAMPLE 1: DirectPathAccessPattern
# =============================================================================

def example_1_direct_path_access():
    """
    Example 1: DirectPathAccessPattern

    Demonstrates direct file access operations including:
    - Checking file existence
    - Reading file statistics
    - Reading file contents
    """
    print_section("EXAMPLE 1: DirectPathAccessPattern")

    pattern = DirectPathAccessPattern()

    # Example 1a: Check if file exists
    print_subsection("1a. Check File Existence")
    result = pattern.execute(path=__file__, operation="exists")
    print(f"File exists: {result.data}")
    print(f"Execution time: {result.execution_time:.4f}s")
    print(f"Success: {result.success}")

    # Example 1b: Get file statistics
    print_subsection("1b. Get File Statistics")
    result = pattern.execute(path=__file__, operation="stat")
    if result.success:
        print(f"File size: {result.data['size']} bytes")
        print(f"Modified: {result.data['modified']}")
        print(f"Is file: {result.data['is_file']}")

    # Example 1c: Read file contents (first 100 chars)
    print_subsection("1c. Read File Contents")
    result = pattern.execute(path=__file__, operation="read")
    if result.success:
        content = result.data[:100] + "..." if len(result.data) > 100 else result.data
        print(f"Content (first 100 chars):\n{content}")
        print(f"Total size: {result.metadata['size']} characters")

    # Show pattern statistics
    print_subsection("Pattern Statistics")
    stats = pattern.get_stats()
    print(f"Executions: {stats['executions']}")
    print(f"Success rate: {stats['success_rate']:.2f}%")


# =============================================================================
# EXAMPLE 2: KnownPathSearchPattern
# =============================================================================

def example_2_known_path_search():
    """
    Example 2: KnownPathSearchPattern

    Demonstrates searching for files in known directories using patterns.
    """
    print_section("EXAMPLE 2: KnownPathSearchPattern")

    pattern = KnownPathSearchPattern()

    # Example 2a: Search for Python files in current directory (non-recursive)
    print_subsection("2a. Search for Python Files (Non-Recursive)")
    result = pattern.execute(
        search_paths=["."],
        pattern="*.py",
        recursive=False
    )
    if result.success:
        print(f"Found {len(result.data)} Python files:")
        for file_path in result.data[:5]:  # Show first 5
            print(f"  - {file_path}")
        if len(result.data) > 5:
            print(f"  ... and {len(result.data) - 5} more")

    # Example 2b: Search for CCMF modules (recursive)
    print_subsection("2b. Search for CCMF Modules (Recursive)")
    result = pattern.execute(
        search_paths=["."],
        pattern="ccmf_*.py",
        recursive=True
    )
    if result.success:
        print(f"Found {len(result.data)} CCMF modules:")
        for file_path in result.data:
            print(f"  - {file_path}")

    # Show pattern statistics
    print_subsection("Pattern Statistics")
    stats = pattern.get_stats()
    print(f"Executions: {stats['executions']}")
    print(f"Success rate: {stats['success_rate']:.2f}%")


# =============================================================================
# EXAMPLE 3: GitRepositoryFilePattern
# =============================================================================

def example_3_git_repository_file():
    """
    Example 3: GitRepositoryFilePattern

    Demonstrates Git repository operations including status, log, and diff.
    """
    print_section("EXAMPLE 3: GitRepositoryFilePattern")

    pattern = GitRepositoryFilePattern()

    # Find git repository root
    current_dir = Path.cwd()
    repo_path = current_dir
    while repo_path != repo_path.parent:
        if (repo_path / ".git").exists():
            break
        repo_path = repo_path.parent

    if not (repo_path / ".git").exists():
        print("Not in a Git repository. Skipping Git examples.")
        return

    # Example 3a: Get repository status
    print_subsection("3a. Repository Status")
    result = pattern.execute(repo_path=str(repo_path), operation="status")
    if result.success:
        print(f"Has uncommitted changes: {result.data['has_changes']}")
        if result.data['raw_output']:
            print(f"Status summary:\n{result.data['raw_output'][:200]}")

    # Example 3b: Get recent commit history
    print_subsection("3b. Recent Commit History")
    result = pattern.execute(repo_path=str(repo_path), operation="log", limit=5)
    if result.success:
        print(f"Recent commits ({len(result.data['commits'])}):")
        for commit in result.data['commits']:
            print(f"  - {commit}")

    # Example 3c: Get diff
    print_subsection("3c. Repository Diff")
    result = pattern.execute(repo_path=str(repo_path), operation="diff")
    if result.success:
        if result.data['has_changes']:
            diff_preview = result.data['diff'][:300] + "..." if len(result.data['diff']) > 300 else result.data['diff']
            print(f"Diff preview:\n{diff_preview}")
        else:
            print("No uncommitted changes.")

    # Show pattern statistics
    print_subsection("Pattern Statistics")
    stats = pattern.get_stats()
    print(f"Executions: {stats['executions']}")
    print(f"Success rate: {stats['success_rate']:.2f}%")


# =============================================================================
# EXAMPLE 4: CheckpointRecoveryPattern
# =============================================================================

def example_4_checkpoint_recovery():
    """
    Example 4: CheckpointRecoveryPattern

    Demonstrates checkpoint creation, listing, loading, and deletion.
    """
    print_section("EXAMPLE 4: CheckpointRecoveryPattern")

    pattern = CheckpointRecoveryPattern(checkpoint_dir=".ccmf_examples_checkpoints")

    # Example 4a: Save a checkpoint
    print_subsection("4a. Save Checkpoint")
    test_data = {
        'iteration': 42,
        'model_state': {'weights': [1.0, 2.0, 3.0]},
        'training_loss': 0.123,
        'accuracy': 0.95
    }
    result = pattern.execute(
        operation="save",
        checkpoint_id="example_checkpoint",
        state_data=test_data,
        metadata={'experiment': 'ccmf_demo', 'version': '1.0'}
    )
    if result.success:
        print(f"Checkpoint saved: {result.data['checkpoint_id']}")
        print(f"File: {result.data['file_path']}")

    # Example 4b: List all checkpoints
    print_subsection("4b. List Checkpoints")
    result = pattern.execute(operation="list")
    if result.success:
        print(f"Found {result.data['count']} checkpoint(s):")
        for cp in result.data['checkpoints']:
            print(f"  - {cp['checkpoint_id']} ({cp['timestamp']})")

    # Example 4c: Load a checkpoint
    print_subsection("4c. Load Checkpoint")
    result = pattern.execute(operation="load", checkpoint_id="example_checkpoint")
    if result.success:
        print(f"Checkpoint loaded: {result.data['checkpoint_id']}")
        print(f"State data: {result.data['state_data']}")

    # Example 4d: Delete checkpoint (cleanup)
    print_subsection("4d. Delete Checkpoint")
    result = pattern.execute(operation="delete", checkpoint_id="example_checkpoint")
    if result.success:
        print(f"Checkpoint deleted: {result.data['checkpoint_id']}")

    # Show pattern statistics
    print_subsection("Pattern Statistics")
    stats = pattern.get_stats()
    print(f"Executions: {stats['executions']}")
    print(f"Success rate: {stats['success_rate']:.2f}%")


# =============================================================================
# EXAMPLE 5: GitStateAnalysisPattern
# =============================================================================

def example_5_git_state_analysis():
    """
    Example 5: GitStateAnalysisPattern

    Demonstrates comprehensive Git repository state analysis.
    """
    print_section("EXAMPLE 5: GitStateAnalysisPattern")

    pattern = GitStateAnalysisPattern()

    # Find git repository root
    current_dir = Path.cwd()
    repo_path = current_dir
    while repo_path != repo_path.parent:
        if (repo_path / ".git").exists():
            break
        repo_path = repo_path.parent

    if not (repo_path / ".git").exists():
        print("Not in a Git repository. Skipping Git state analysis.")
        return

    # Example 5a: Analyze Git state
    print_subsection("5a. Comprehensive Git State Analysis")
    result = pattern.execute(repo_path=str(repo_path))
    if result.success:
        data = result.data
        print(f"Current branch: {data['current_branch']}")
        print(f"Has uncommitted changes: {data['has_uncommitted_changes']}")
        print(f"Total commits: {data['total_commits']}")
        print(f"\nRecent commits ({len(data['recent_commits'])}):")
        for commit in data['recent_commits']:
            print(f"  - {commit}")
        if data['remotes']:
            print(f"\nRemotes ({len(data['remotes'])}):")
            for remote in data['remotes'][:3]:
                print(f"  - {remote}")

    # Show pattern statistics
    print_subsection("Pattern Statistics")
    stats = pattern.get_stats()
    print(f"Executions: {stats['executions']}")
    print(f"Success rate: {stats['success_rate']:.2f}%")


# =============================================================================
# EXAMPLE 6: CompositeStateRecoveryPattern
# =============================================================================

def example_6_composite_state_recovery():
    """
    Example 6: CompositeStateRecoveryPattern

    Demonstrates multi-source state recovery with fallback strategies.
    """
    print_section("EXAMPLE 6: CompositeStateRecoveryPattern")

    pattern = CompositeStateRecoveryPattern(checkpoint_dir=".ccmf_examples_checkpoints")

    # Find git repository root
    current_dir = Path.cwd()
    repo_path = current_dir
    while repo_path != repo_path.parent:
        if (repo_path / ".git").exists():
            break
        repo_path = repo_path.parent

    # Example 6a: Recover state from all sources
    print_subsection("6a. Multi-Source State Recovery")
    result = pattern.execute(
        repo_path=str(repo_path),
        recovery_sources=['checkpoint', 'git', 'filesystem']
    )
    if result.success:
        data = result.data
        print(f"Recovery timestamp: {data['recovery_timestamp']}")
        print(f"Sources attempted: {result.metadata['sources_attempted']}")
        print(f"Sources succeeded: {result.metadata['sources_succeeded']}")

        for source_name, source_data in data['sources'].items():
            print(f"\n  [{source_name.upper()}]")
            if source_data['success']:
                print(f"    ✓ Success")
                # Show sample data
                if 'data' in source_data:
                    print(f"    Data keys: {list(source_data['data'].keys())[:5]}")
            else:
                print(f"    ✗ Failed: {source_data.get('error', 'Unknown error')}")

    # Show pattern statistics
    print_subsection("Pattern Statistics")
    stats = pattern.get_stats()
    print(f"Executions: {stats['executions']}")
    print(f"Success rate: {stats['success_rate']:.2f}%")


# =============================================================================
# EXAMPLE 7: Constitutional Compliance Validation
# =============================================================================

def example_7_constitutional_compliance():
    """
    Example 7: Constitutional Compliance Validation

    Demonstrates constitutional framework and compliance validation.
    """
    print_section("EXAMPLE 7: Constitutional Compliance Validation")

    framework = ConstitutionalFramework()

    # Example 7a: Full compliance scenario
    print_subsection("7a. Full Compliance Scenario")
    compliant_context = {
        'operation_type': 'data_analysis',
        'risk_assessment': 'low',
        'logging_enabled': True,
        'audit_trail': True,
        'resource_estimate': {'cpu': 'low', 'memory': 'medium'},
        'error_handling': True,
        'recovery_strategy': 'retry_with_backoff',
        'data_classification': 'internal',
        'privacy_check': True,
        'ethical_review': True
    }
    report = validate_operation(compliant_context)
    print(f"Compliance Level: {report.overall_compliance.value}")
    print(f"Compliance Score: {report.compliance_score:.2%}")
    print(f"Principles Passed: {report.principles_passed}/{report.principles_checked}")

    # Example 7b: Partial compliance scenario
    print_subsection("7b. Partial Compliance Scenario")
    partial_context = {
        'operation_type': 'file_modification',
        'risk_assessment': 'medium',
        'logging_enabled': True,
        'audit_trail': True,
        'error_handling': True,
        'recovery_strategy': 'fail_fast',
        'data_classification': 'confidential',
        'privacy_check': True,
        'ethical_review': True
    }
    report = validate_operation(partial_context)
    print(f"Compliance Level: {report.overall_compliance.value}")
    print(f"Compliance Score: {report.compliance_score:.2%}")
    print(f"Principles Passed: {report.principles_passed}/{report.principles_checked}")
    if report.violations:
        print(f"\nViolations:")
        for v in report.violations:
            print(f"  - {v['principle_name']}: {v['reason']}")

    # Example 7c: Non-compliant scenario
    print_subsection("7c. Non-Compliant Scenario")
    non_compliant_context = {
        'operation_type': 'system_modification'
    }
    report = validate_operation(non_compliant_context)
    print(f"Compliance Level: {report.overall_compliance.value}")
    print(f"Compliance Score: {report.compliance_score:.2%}")
    print(f"Principles Failed: {report.principles_failed}/{report.principles_checked}")

    print(f"\nViolations ({len(report.violations)}):")
    for v in report.violations[:5]:
        print(f"  - {v['principle_name']}: {v['reason']}")

    if report.recommendations:
        print(f"\nRecommendations:")
        for rec in report.recommendations:
            print(f"  - {rec}")


# =============================================================================
# EXAMPLE 8: RSI Feedback Loop
# =============================================================================

def example_8_rsi_feedback_loop():
    """
    Example 8: RSI Feedback Loop Integration

    Demonstrates the Recursive Self-Improvement feedback loop.
    """
    print_section("EXAMPLE 8: RSI Feedback Loop")

    rsi_loop = RSIFeedbackLoop()

    # Example 8a: Simulate operations and collect feedback
    print_subsection("8a. Collecting Feedback from Operations")
    import random
    import time

    operations = [
        ('file_read', 0.8),
        ('file_write', 0.75),
        ('search', 0.9),
        ('analysis', 0.7)
    ]

    print("Simulating 20 operations...")
    for i in range(20):
        op_name, success_prob = random.choice(operations)
        success = random.random() < success_prob
        exec_time = random.uniform(0.1, 1.5)
        quality = random.uniform(0.7, 1.0) if success else random.uniform(0.3, 0.6)

        rsi_loop.collect_feedback(
            feedback_type=FeedbackType.SUCCESS if success else FeedbackType.FAILURE,
            source=f"operation_{op_name}",
            metrics={
                'execution_time': exec_time,
                'quality': quality
            },
            severity=0.3 if success else 0.7,
            message=f"{op_name} {'completed' if success else 'failed'}"
        )

    print(f"Collected {len(rsi_loop.feedback_history)} feedback entries")

    # Example 8b: Analyze performance
    print_subsection("8b. Performance Analysis")
    analysis = rsi_loop.analyze_performance()
    print(f"Ready for adaptation: {analysis['ready_for_adaptation']}")
    print(f"Health score: {analysis['health_score']:.2%}")
    print(f"Current metrics:")
    metrics = analysis['current_metrics']
    print(f"  - Success rate: {metrics['success_rate']:.2%}")
    print(f"  - Avg execution time: {metrics['execution_time']:.4f}s")
    print(f"  - Quality score: {metrics['quality_score']:.4f}")
    print(f"  - Error count: {metrics['error_count']}")

    # Example 8c: Run improvement cycle
    print_subsection("8c. Improvement Cycle")
    cycle_result = rsi_loop.run_improvement_cycle()
    print(f"Cycle completed at: {cycle_result['timestamp']}")
    print(f"Current health: {cycle_result['current_health']:.2%}")
    print(f"Adapted: {cycle_result['adapted']}")

    if cycle_result['decision']:
        decision = cycle_result['decision']
        print(f"\nAdaptation Decision:")
        print(f"  Strategy: {decision['strategy']}")
        print(f"  Reason: {decision['reason']}")
        print(f"  Confidence: {decision['confidence']:.2%}")
        print(f"  Expected improvement: {decision['expected_improvement']:.2%}")


# =============================================================================
# EXAMPLE 9: Meta-Learning and Leverage Quotient
# =============================================================================

def example_9_meta_learning():
    """
    Example 9: Meta-Learning Architecture and MLA Leverage Quotient

    Demonstrates meta-learning capabilities and leverage quotient calculation.
    """
    print_section("EXAMPLE 9: Meta-Learning & MLA Leverage Quotient")

    mla = MetaLearningArchitecture()

    # Example 9a: Record learning examples
    print_subsection("9a. Recording Learning Examples")
    import random

    patterns = ['DirectPathAccessPattern', 'KnownPathSearchPattern', 'GitRepositoryFilePattern']
    contexts = [
        {'operation': 'read', 'size': 'small', 'type': 'config'},
        {'operation': 'read', 'size': 'large', 'type': 'data'},
        {'operation': 'search', 'scope': 'local', 'pattern': '*.py'},
        {'operation': 'search', 'scope': 'global', 'pattern': '*.txt'},
        {'operation': 'git_status', 'repo': 'local'},
        {'operation': 'git_log', 'repo': 'remote'}
    ]

    print("Recording 50 learning examples...")
    for i in range(50):
        pattern = random.choice(patterns)
        context = random.choice(contexts)

        # Simulate pattern-specific success rates
        if pattern == 'DirectPathAccessPattern':
            success_rate = 0.9
        elif pattern == 'KnownPathSearchPattern':
            success_rate = 0.85
        else:
            success_rate = 0.75

        success = random.random() < success_rate

        mla.record_example(
            pattern_name=pattern,
            context=context,
            outcome={'status': 'success' if success else 'failure'},
            performance_metrics={
                'execution_time': random.uniform(0.05, 1.0),
                'quality': random.uniform(0.7, 1.0) if success else random.uniform(0.2, 0.5)
            },
            success=success
        )

    print(f"Recorded {len(mla.learning_examples)} examples")
    print(f"Patterns with knowledge: {len(mla.pattern_knowledge)}")

    # Example 9b: Calculate MLA Leverage Quotient
    print_subsection("9b. MLA Leverage Quotient")
    quotient = mla.calculate_leverage_quotient()

    print(f"\n{'*' * 70}")
    print(f"{'MLA LEVERAGE QUOTIENT'.center(70)}")
    print('*' * 70)
    print(f"\n  Overall Quotient: {quotient.overall_quotient:.4f}")
    print(f"  Grade: {quotient.get_grade()}")
    print(f"\n  Metrics:")
    print(f"    • Total Examples: {quotient.total_examples}")
    print(f"    • Successful Examples: {quotient.successful_examples}")
    print(f"    • Patterns Learned: {quotient.patterns_learned}")
    print(f"    • Avg Performance Gain: {quotient.average_performance_gain:+.4f}")
    print(f"    • Transfer Learning Effectiveness: {quotient.transfer_learning_effectiveness:.4f}")
    print(f"    • Knowledge Reuse Rate: {quotient.knowledge_reuse_rate:.4f}")
    print('*' * 70)

    # Example 9c: Pattern recommendation
    print_subsection("9c. Pattern Recommendation")
    test_contexts = [
        {'operation': 'read', 'size': 'small', 'type': 'config'},
        {'operation': 'search', 'scope': 'local', 'pattern': '*.py'}
    ]

    for context in test_contexts:
        recommended, reasoning = mla.recommend_pattern(context, patterns)
        print(f"\nContext: {context}")
        print(f"  Recommended Pattern: {recommended}")
        print(f"  Confidence Score: {reasoning['score']:.4f}")
        if 'prediction' in reasoning:
            pred = reasoning['prediction']
            print(f"  Predicted Success Rate: {pred['predicted_success_rate']:.2%}")
            print(f"  Prediction Confidence: {pred['confidence']:.2%}")

    # Example 9d: Learning insights
    print_subsection("9d. Learning Insights")
    insights = mla.get_learning_insights()

    print(f"\nTotal learning examples: {insights['total_examples']}")
    print(f"Patterns learned: {insights['patterns_learned']}")

    print(f"\nTop Performing Patterns:")
    for pattern_info in insights['top_performing_patterns'][:3]:
        print(f"  • {pattern_info['name']}: {pattern_info['success_rate']:.2%} " +
              f"({pattern_info['usage_count']} uses)")

    if insights['patterns_needing_improvement']:
        print(f"\nPatterns Needing Improvement:")
        for pattern_info in insights['patterns_needing_improvement']:
            print(f"  • {pattern_info['name']}: {pattern_info['success_rate']:.2%} " +
                  f"({pattern_info['usage_count']} uses)")


# =============================================================================
# EXAMPLE 10: Integrated Workflow
# =============================================================================

def example_10_integrated_workflow():
    """
    Example 10: Integrated Workflow

    Demonstrates a complete workflow integrating patterns, constitutional
    validation, RSI feedback, and meta-learning.
    """
    print_section("EXAMPLE 10: Integrated Workflow")

    # Create workflow
    builder = WorkflowBuilder(
        workflow_id="ccmf_integrated_demo",
        name="CCMF Integrated Demonstration",
        description="End-to-end demonstration of CCMF capabilities"
    ).with_rsi(True)

    # Add workflow steps
    builder.add_pattern_step(
        step_id="step1",
        name="Verify Current File",
        pattern=DirectPathAccessPattern(),
        parameters={'path': __file__, 'operation': 'exists'},
        description="Verify the examples file exists"
    )

    builder.add_pattern_step(
        step_id="step2",
        name="Get File Statistics",
        pattern=DirectPathAccessPattern(),
        parameters={'path': __file__, 'operation': 'stat'},
        description="Get statistics for the examples file",
        depends_on=['step1']
    )

    builder.add_pattern_step(
        step_id="step3",
        name="Search for CCMF Modules",
        pattern=KnownPathSearchPattern(),
        parameters={
            'search_paths': ['.'],
            'pattern': 'ccmf_*.py',
            'recursive': False
        },
        description="Find all CCMF module files",
        depends_on=['step1']
    )

    # Build and execute workflow
    workflow = builder.build()

    print_subsection("10a. Workflow Configuration")
    print(f"Workflow ID: {workflow.workflow_id}")
    print(f"Name: {workflow.name}")
    print(f"Total steps: {len(workflow.steps)}")
    print(f"RSI enabled: {workflow.enable_rsi}")

    print_subsection("10b. Executing Workflow")
    result = workflow.execute()

    print_subsection("10c. Workflow Results")
    print(f"Status: {result['status']}")
    print(f"Total execution time: {result['total_execution_time']:.4f}s")
    print(f"\nSteps Summary:")
    print(f"  • Total: {result['steps']['total']}")
    print(f"  • Completed: {result['steps']['completed']}")
    print(f"  • Failed: {result['steps']['failed']}")
    print(f"  • Skipped: {result['steps']['skipped']}")

    print(f"\nStep Details:")
    for step in result['step_details']:
        status_icon = "✓" if step['status'] == 'completed' else "✗" if step['status'] == 'failed' else "○"
        print(f"  {status_icon} {step['name']}: {step['status']} ({step['execution_time']:.4f}s)")

    print_subsection("10d. Execution Logs (Last 5)")
    for log in result['logs'][-5:]:
        level_icon = "ℹ" if log['level'] == 'INFO' else "⚠" if log['level'] == 'WARNING' else "✗"
        print(f"  {level_icon} [{log['level']}] {log['message']}")


# =============================================================================
# Main Execution
# =============================================================================

def run_all_examples():
    """Run all CCMF examples."""
    print("\n")
    print("=" * 70)
    print("CCMF COMPREHENSIVE EXAMPLES - SESSION 2".center(70))
    print("Constitutional Cognitive Meta-Framework".center(70))
    print("=" * 70)
    print("\nDemonstrating the POWER and VERSATILITY of the CCMF Framework")
    print(f"Execution started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    examples = [
        example_1_direct_path_access,
        example_2_known_path_search,
        example_3_git_repository_file,
        example_4_checkpoint_recovery,
        example_5_git_state_analysis,
        example_6_composite_state_recovery,
        example_7_constitutional_compliance,
        example_8_rsi_feedback_loop,
        example_9_meta_learning,
        example_10_integrated_workflow
    ]

    for i, example_func in enumerate(examples, 1):
        try:
            example_func()
        except Exception as e:
            print(f"\n⚠ Warning: Example {i} encountered an error: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 70)
    print("ALL EXAMPLES COMPLETED".center(70))
    print(f"Execution finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)


if __name__ == "__main__":
    run_all_examples()
