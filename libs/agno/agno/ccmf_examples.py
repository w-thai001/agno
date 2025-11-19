"""
Claude Code Mastery Framework (CCMF) v1.0 - Examples Module

Working usage examples demonstrating all CCMF patterns and features.

This module provides comprehensive examples for:
- Constitutional validation
- File operation patterns
- State recovery workflows
- RSI feedback loops
- Pattern optimization

Each example demonstrates proper pattern usage, constitutional compliance,
and RSI tracking for meta-level self-improvement.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from agno.ccmf_constitutional import ConstitutionalValidator
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

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def example_direct_path_access() -> Dict[str, Any]:
    """
    Demonstrate DirectPathAccessPattern usage.

    Shows:
    - Testing file existence
    - Reading file content
    - Constitutional validation
    - LQ scoring

    Returns:
        Dictionary with example results
    """
    logger.info("Running example_direct_path_access")

    validator = ConstitutionalValidator()
    pattern = DirectPathAccessPattern(validator)

    results = {
        "example": "Direct Path Access",
        "operations": []
    }

    # Test file existence
    print("\n--- Testing file existence ---")
    success, result, error = pattern.execute_with_validation({
        'file_path': '/home/user/agno/README.md',
        'operation': 'test'
    })

    test_result = {
        "operation": "test",
        "success": success,
        "exists": result.get("exists") if result else False,
        "error": error
    }
    results["operations"].append(test_result)

    print(f"File exists: {test_result['exists']}")
    print(f"Success: {success}")

    # Read file content (only if exists)
    if success and result and result.get("exists"):
        print("\n--- Reading file content ---")
        success, result, error = pattern.execute_with_validation({
            'file_path': '/home/user/agno/README.md',
            'operation': 'read'
        })

        read_result = {
            "operation": "read",
            "success": success,
            "content_length": len(result.get("content", "")) if result else 0,
            "size_bytes": result.get("size_bytes") if result else 0,
            "error": error
        }
        results["operations"].append(read_result)

        print(f"Content length: {read_result['content_length']} chars")
        print(f"Size: {read_result['size_bytes']} bytes")

    # Show performance summary
    perf = pattern.get_performance_summary()
    results["performance"] = perf

    print(f"\nPattern LQ Score: {perf['average_lq']:.2f}")
    print(f"Success Rate: {perf['success_rate']:.1f}%")

    return results


def example_known_path_search() -> Dict[str, Any]:
    """
    Demonstrate KnownPathSearchPattern with multiple paths.

    Shows:
    - Searching through multiple candidate paths
    - Iterative testing with PowerShell
    - Search logging
    - LQ degradation with attempts

    Returns:
        Dictionary with example results
    """
    logger.info("Running example_known_path_search")

    validator = ConstitutionalValidator()
    pattern = KnownPathSearchPattern(validator)

    print("\n--- Known Path Search ---")
    print("Searching for configuration files...")

    success, result, error = pattern.execute_with_validation({
        'search_paths': [
            '/home/user/agno/nonexistent.json',
            '/home/user/agno/config.json',
            '/home/user/agno/package.json',
            '/home/user/agno/README.md',
        ],
        'read_content': False
    })

    results = {
        "example": "Known Path Search",
        "success": success,
        "found": result.get("found") if result else False,
        "attempts": result.get("attempts") if result else 0,
        "path": result.get("path") if result else None,
        "error": error
    }

    if success and result:
        print(f"Found: {results['found']}")
        print(f"Attempts: {results['attempts']}")
        if results['found']:
            print(f"Path: {results['path']}")

        # Show search log
        if "search_log" in result:
            print("\nSearch Log:")
            for entry in result["search_log"]:
                status = "✓ FOUND" if entry.get("exists") else "✗ Not found"
                print(f"  Attempt {entry['attempt']}: {status} - {entry['path']}")

    perf = pattern.get_performance_summary()
    results["performance"] = perf
    print(f"\nPattern LQ Score: {perf['average_lq']:.2f}")

    return results


def example_git_repository() -> Dict[str, Any]:
    """
    Demonstrate GitRepositoryFilePattern for all operations.

    Shows:
    - Listing files (git ls-files)
    - Reading files (git show)
    - Getting commit log (git log)
    - High LQ scoring

    Returns:
        Dictionary with example results
    """
    logger.info("Running example_git_repository")

    validator = ConstitutionalValidator()
    pattern = GitRepositoryFilePattern(validator)

    results = {
        "example": "Git Repository Operations",
        "operations": []
    }

    # List Python files
    print("\n--- Listing Python files ---")
    success, list_result, error = pattern.execute_with_validation({
        'repo_path': '/home/user/agno',
        'operation': 'list',
        'file_pattern': '*.py'
    })

    list_op = {
        "operation": "list",
        "success": success,
        "count": list_result.get("count") if list_result else 0,
        "error": error
    }
    results["operations"].append(list_op)

    print(f"Found {list_op['count']} Python files")

    # Read specific file from git
    print("\n--- Reading file from git ---")
    success, read_result, error = pattern.execute_with_validation({
        'repo_path': '/home/user/agno',
        'operation': 'read',
        'file_pattern': 'README.md'
    })

    read_op = {
        "operation": "read",
        "success": success,
        "size_bytes": read_result.get("size_bytes") if read_result else 0,
        "error": error
    }
    results["operations"].append(read_op)

    if success:
        print(f"Read {read_op['size_bytes']} bytes from README.md")

    # Get commit log
    print("\n--- Getting commit log ---")
    success, log_result, error = pattern.execute_with_validation({
        'repo_path': '/home/user/agno',
        'operation': 'log',
        'file_pattern': 'README.md'
    })

    log_op = {
        "operation": "log",
        "success": success,
        "commits": log_result.get("count") if log_result else 0,
        "error": error
    }
    results["operations"].append(log_op)

    if success and log_result:
        print(f"Found {log_op['commits']} commits")
        if log_result.get("commits"):
            print(f"Latest: {log_result['commits'][0][:60]}...")

    # Show performance summary
    perf = pattern.get_performance_summary()
    results["performance"] = perf

    print(f"\nPattern LQ Score: {perf['average_lq']:.2f}")
    print(f"Total Executions: {perf['total_executions']}")

    return results


def example_checkpoint_recovery() -> Dict[str, Any]:
    """
    Demonstrate CheckpointRecoveryPattern.

    Shows:
    - Searching for checkpoint files
    - Timestamp parsing
    - Recovery strategies (latest, all, specific)
    - State loading

    Returns:
        Dictionary with example results
    """
    logger.info("Running example_checkpoint_recovery")

    validator = ConstitutionalValidator()
    pattern = CheckpointRecoveryPattern(validator)

    print("\n--- Checkpoint Recovery ---")
    print("Searching for checkpoint files...")

    success, result, error = pattern.execute_with_validation({
        'checkpoint_paths': [
            '/home/user/.ccmf/checkpoints/checkpoint_20240115_120000.json',
            '/home/user/.ccmf/checkpoints/checkpoint_20240115_130000.json',
            '/tmp/checkpoint_latest.json',
        ],
        'recovery_strategy': 'latest'
    })

    results = {
        "example": "Checkpoint Recovery",
        "success": success,
        "checkpoint_used": result.get("checkpoint_used") if result else None,
        "checkpoint_age": result.get("checkpoint_age") if result else None,
        "has_state": "recovered_state" in result if result else False,
        "error": error
    }

    if success and result:
        print(f"Success: {success}")
        if results["checkpoint_used"]:
            print(f"Checkpoint: {results['checkpoint_used']}")
            print(f"Age: {results['checkpoint_age']:.1f} seconds")
    else:
        print(f"Recovery failed: {error or 'No checkpoints found'}")

    perf = pattern.get_performance_summary()
    results["performance"] = perf
    print(f"\nPattern LQ Score: {perf['average_lq']:.2f}")

    return results


def example_git_state_analysis() -> Dict[str, Any]:
    """
    Demonstrate GitStateAnalysisPattern.

    Shows:
    - Current branch detection
    - Working tree status
    - Recent commit history
    - Diff analysis

    Returns:
        Dictionary with example results
    """
    logger.info("Running example_git_state_analysis")

    validator = ConstitutionalValidator()
    pattern = GitStateAnalysisPattern(validator)

    print("\n--- Git State Analysis ---")
    print("Analyzing repository state...")

    success, result, error = pattern.execute_with_validation({
        'repo_path': '/home/user/agno',
        'analysis_depth': 10
    })

    results = {
        "example": "Git State Analysis",
        "success": success,
        "error": error
    }

    if success and result:
        results.update({
            "current_branch": result.get("current_branch"),
            "is_clean": result.get("is_clean"),
            "uncommitted_files": len(result.get("uncommitted_files", [])),
            "recent_commits": len(result.get("recent_commits", []))
        })

        print(f"Branch: {results['current_branch']}")
        print(f"Clean: {results['is_clean']}")
        print(f"Uncommitted files: {results['uncommitted_files']}")
        print(f"Recent commits: {results['recent_commits']}")

        if result.get("recent_commits"):
            print("\nRecent commits:")
            for i, commit in enumerate(result["recent_commits"][:3], 1):
                print(f"  {i}. {commit[:70]}...")

    perf = pattern.get_performance_summary()
    results["performance"] = perf
    print(f"\nPattern LQ Score: {perf['average_lq']:.2f}")

    return results


def example_composite_state_recovery() -> Dict[str, Any]:
    """
    Demonstrate CompositeStateRecoveryPattern.

    Shows:
    - Multi-source recovery (checkpoints + git + fallback)
    - Priority-based fallback
    - State merging
    - Confidence scoring

    Returns:
        Dictionary with example results
    """
    logger.info("Running example_composite_state_recovery")

    validator = ConstitutionalValidator()
    pattern = CompositeStateRecoveryPattern(validator)

    print("\n--- Composite State Recovery ---")
    print("Attempting multi-source recovery...")

    success, result, error = pattern.execute_with_validation({
        'checkpoint_paths': [
            '/tmp/checkpoint_20240101_120000.json',
        ],
        'repo_path': '/home/user/agno',
        'fallback_paths': [
            '/home/user/agno/README.md',
        ]
    })

    results = {
        "example": "Composite State Recovery",
        "success": success,
        "error": error
    }

    if success and result:
        results.update({
            "sources_used": result.get("recovery_sources_used", []),
            "confidence_score": result.get("confidence_score"),
            "recovery_time": result.get("recovery_time")
        })

        print(f"Success: {success}")
        print(f"Sources used: {', '.join(results['sources_used'])}")
        print(f"Confidence: {results['confidence_score']:.2f}")
        print(f"Recovery time: {results['recovery_time']:.3f}s")

        # Show merged state summary
        if "merged_state" in result:
            merged = result["merged_state"]
            print(f"\nMerged state keys: {list(merged.keys())}")

    perf = pattern.get_performance_summary()
    results["performance"] = perf
    print(f"\nPattern LQ Score: {perf['average_lq']:.2f}")

    return results


def example_rsi_feedback_loop() -> Dict[str, Any]:
    """
    Demonstrate RSI feedback loop with pattern optimization.

    Shows:
    - Pattern registration
    - Performance analysis
    - Optimization suggestions
    - Improvement cycles

    Returns:
        Dictionary with example results
    """
    logger.info("Running example_rsi_feedback_loop")

    validator = ConstitutionalValidator()

    print("\n--- RSI Feedback Loop ---")

    # Create patterns
    git_pattern = GitRepositoryFilePattern(validator)
    search_pattern = KnownPathSearchPattern(validator)

    # Execute some operations to generate data
    print("Executing pattern operations to generate data...")
    for i in range(5):
        git_pattern.execute_with_validation({
            'repo_path': '/home/user/agno',
            'operation': 'list',
            'file_pattern': '*.py' if i % 2 == 0 else '*.md'
        })

    # Set up RSI loop
    rsi_loop = RSIFeedbackLoop()
    rsi_loop.register_pattern(git_pattern)
    rsi_loop.register_pattern(search_pattern)

    print(f"Registered {len(rsi_loop.patterns)} patterns")

    # Run improvement cycle
    print("\nRunning improvement cycle...")
    cycle_result = rsi_loop.run_improvement_cycle()

    results = {
        "example": "RSI Feedback Loop",
        "cycle_number": cycle_result["cycle_number"],
        "patterns_analyzed": cycle_result["patterns_analyzed"],
        "total_optimizations": cycle_result["total_optimizations_suggested"],
        "summary": cycle_result["improvement_summary"]
    }

    print(f"\nCycle #{results['cycle_number']} completed")
    print(f"Patterns analyzed: {results['patterns_analyzed']}")
    print(f"Optimizations suggested: {results['total_optimizations']}")

    # Show optimizations for git pattern
    if git_pattern.pattern_id in cycle_result["optimizations_by_pattern"]:
        opts = cycle_result["optimizations_by_pattern"][git_pattern.pattern_id]
        print(f"\nOptimizations for {git_pattern.pattern_name}:")
        for i, opt in enumerate(opts[:3], 1):
            print(f"  {i}. {opt['optimization_type']} (priority={opt['priority']})")
            print(f"     {opt['description']}")
            print(f"     Expected LQ improvement: +{opt['expected_lq_improvement']:.2f}")

    # Get overall summary
    summary = rsi_loop.get_summary()
    results["rsi_summary"] = summary

    print(f"\nRSI Loop Summary:")
    print(f"  Cycles run: {summary['cycles_run']}")
    print(f"  Patterns registered: {summary['patterns_registered']}")
    print(f"  Overall success rate: {summary['overall_success_rate']:.1f}%")
    print(f"  Average LQ: {summary['average_lq']:.2f}")

    return results


def example_constitutional_validation() -> Dict[str, Any]:
    """
    Demonstrate constitutional validation and violation reporting.

    Shows:
    - Forbidden method detection
    - Allowed method validation
    - LQ calculation
    - Violation tracking and reporting

    Returns:
        Dictionary with example results
    """
    logger.info("Running example_constitutional_validation")

    validator = ConstitutionalValidator()

    print("\n--- Constitutional Validation ---")

    results = {
        "example": "Constitutional Validation",
        "forbidden_tests": [],
        "allowed_tests": []
    }

    # Test forbidden methods
    print("\nTesting forbidden methods (should be blocked):")
    forbidden_methods = ['read_list', 'file_list', 'file_find_by_name']

    for method in forbidden_methods:
        is_valid, violation = validator.validate_file_operation(
            operation='test',
            file_path='/test/path',
            method=method
        )

        test_result = {
            "method": method,
            "valid": is_valid,
            "blocked": not is_valid
        }
        results["forbidden_tests"].append(test_result)

        status = "✗ BLOCKED" if not is_valid else "✓ ALLOWED (ERROR!)"
        print(f"  {status}: {method}")

    # Test allowed methods
    print("\nTesting allowed methods (should pass):")
    allowed_methods = ['powershell_subprocess', 'git_command']

    for method in allowed_methods:
        is_valid, violation = validator.validate_file_operation(
            operation='test',
            file_path='/test/path',
            method=method
        )

        test_result = {
            "method": method,
            "valid": is_valid,
            "allowed": is_valid
        }
        results["allowed_tests"].append(test_result)

        status = "✓ ALLOWED" if is_valid else "✗ BLOCKED (ERROR!)"
        print(f"  {status}: {method}")

    # Calculate LQ
    print("\nLeverage Quotient Calculation:")
    lq = validator.calculate_leverage_quotient(
        progress_towards_goal=0.8,
        energy_efficiency=0.9,
        cost=0.2
    )
    results["lq_example"] = lq

    print(f"  Progress: 0.8, Efficiency: 0.9, Cost: 0.2")
    print(f"  LQ = I(a,G) / C(a) = {lq:.2f}")
    print(f"  Interpretation: Action returns {lq:.1f}x value for cost")

    # Get violation report
    print("\nViolation Report:")
    report = validator.generate_violation_report()
    results["violation_report"] = report

    # Print summary
    lines = report.split('\n')
    for line in lines[:15]:  # First 15 lines
        print(f"  {line}")

    results["total_validations"] = validator.validation_count
    results["total_violations"] = len(validator.violations)

    return results


def example_pattern_comparison() -> Dict[str, Any]:
    """
    Compare performance of different patterns.

    Shows:
    - LQ score comparison
    - Execution time comparison
    - Success rate comparison
    - Use case recommendations

    Returns:
        Dictionary with comparison results
    """
    logger.info("Running example_pattern_comparison")

    validator = ConstitutionalValidator()

    print("\n--- Pattern Performance Comparison ---")

    # Create patterns
    patterns = [
        DirectPathAccessPattern(validator),
        GitRepositoryFilePattern(validator),
    ]

    comparison = {
        "example": "Pattern Comparison",
        "patterns": []
    }

    # Execute each pattern
    for pattern in patterns:
        print(f"\nTesting {pattern.pattern_name}...")

        if isinstance(pattern, DirectPathAccessPattern):
            pattern.execute_with_validation({
                'file_path': '/home/user/agno/README.md',
                'operation': 'test'
            })
        elif isinstance(pattern, GitRepositoryFilePattern):
            pattern.execute_with_validation({
                'repo_path': '/home/user/agno',
                'operation': 'list',
                'file_pattern': '*.md'
            })

        perf = pattern.get_performance_summary()

        pattern_data = {
            "pattern_id": pattern.pattern_id,
            "pattern_name": pattern.pattern_name,
            "avg_lq": perf["average_lq"],
            "success_rate": perf["success_rate"],
            "total_executions": perf["total_executions"]
        }
        comparison["patterns"].append(pattern_data)

        print(f"  LQ Score: {pattern_data['avg_lq']:.2f}")
        print(f"  Success Rate: {pattern_data['success_rate']:.1f}%")

    # Rank by LQ
    comparison["patterns"].sort(key=lambda p: p["avg_lq"], reverse=True)

    print("\n--- Pattern Rankings (by LQ) ---")
    for i, p in enumerate(comparison["patterns"], 1):
        print(f"  {i}. {p['pattern_name']}: LQ={p['avg_lq']:.2f}")

    return comparison


def run_all_examples() -> Dict[str, Any]:
    """
    Run all examples in sequence.

    Returns:
        Dictionary with all example results
    """
    print("\n" + "=" * 70)
    print("  CCMF v1.0 - Comprehensive Examples")
    print("  Meta-level RSI Framework FOR Fellou Agents BY Fellou Agents")
    print("=" * 70)

    all_results = {
        "framework_version": "1.0.0",
        "examples": []
    }

    examples = [
        ("Constitutional Validation", example_constitutional_validation),
        ("Direct Path Access", example_direct_path_access),
        ("Known Path Search", example_known_path_search),
        ("Git Repository", example_git_repository),
        ("Checkpoint Recovery", example_checkpoint_recovery),
        ("Git State Analysis", example_git_state_analysis),
        ("Composite State Recovery", example_composite_state_recovery),
        ("RSI Feedback Loop", example_rsi_feedback_loop),
        ("Pattern Comparison", example_pattern_comparison),
    ]

    for name, func in examples:
        print(f"\n{'=' * 70}")
        print(f"Example: {name}")
        print('=' * 70)

        try:
            result = func()
            result["status"] = "success"
            all_results["examples"].append(result)
        except Exception as e:
            logger.exception(f"Example {name} failed")
            all_results["examples"].append({
                "example": name,
                "status": "error",
                "error": str(e)
            })
            print(f"\n✗ Error: {e}")

    print("\n" + "=" * 70)
    print("All examples completed!")
    print("=" * 70)

    return all_results


# Main entry point
if __name__ == '__main__':
    results = run_all_examples()

    # Print summary
    print("\n\n=== SUMMARY ===")
    successful = sum(1 for e in results["examples"] if e.get("status") == "success")
    total = len(results["examples"])
    print(f"Completed: {successful}/{total} examples")

    # Export results to JSON
    try:
        output_file = "/tmp/ccmf_examples_results.json"
        with open(output_file, 'w') as f:
            json.dumps(results, indent=2, default=str)
        print(f"\nResults exported to: {output_file}")
    except Exception as e:
        logger.error(f"Could not export results: {e}")
