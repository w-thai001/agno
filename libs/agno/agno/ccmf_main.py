#!/usr/bin/env python3
"""
Claude Code Mastery Framework (CCMF) v1.0 - Main Entry Point

Command-line interface for Claude Code Mastery Framework.

This module provides a comprehensive CLI for executing patterns, running demos,
and managing the CCMF framework.

Usage:
  python ccmf_main.py --pattern direct_path --file-path /path/to/file.json
  python ccmf_main.py --pattern known_path_search --search-paths ./file1.json ./file2.json
  python ccmf_main.py --pattern git_repo --repo-path /home/user/agno --operation list
  python ccmf_main.py --demo
  python ccmf_main.py --run-tests
  python ccmf_main.py --config ccmf_config.json

Examples:
  # Test file existence
  python ccmf_main.py --pattern direct_path --file-path /home/user/agno/README.md --operation test

  # Search through multiple paths
  python ccmf_main.py --pattern known_path_search --search-paths ./config.json ./package.json

  # List Python files in repository
  python ccmf_main.py --pattern git_repo --repo-path . --operation list --file-pattern "*.py"

  # Analyze repository state
  python ccmf_main.py --pattern git_state_analysis --repo-path /home/user/agno

  # Run interactive demo
  python ccmf_main.py --demo

  # Run test suite
  python ccmf_main.py --run-tests
"""

import argparse
import json
import sys
import logging
from pathlib import Path
from typing import Dict, Any, Optional

# Import all CCMF modules
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
from agno.ccmf_rsi_loop import RSIFeedbackLoop, ExecutionAnalyzer, PatternOptimizer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_banner():
    """Print CCMF banner."""
    print("\n" + "=" * 80)
    print("  Claude Code Mastery Framework (CCMF) v1.0")
    print("  Meta-level RSI Framework FOR Fellou Agents BY Fellou Agents")
    print("=" * 80 + "\n")


def load_config(config_path: str = "ccmf_config.json") -> Dict[str, Any]:
    """
    Load configuration from JSON file.

    Args:
        config_path: Path to configuration file

    Returns:
        Configuration dictionary
    """
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            logger.info(f"Loaded configuration from: {config_path}")
            return config
    except FileNotFoundError:
        logger.warning(f"Config file not found: {config_path}")
        print(f"⚠️  Config file not found: {config_path}")
        print("📝 Using default configuration...")
        return get_default_config()
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in config file: {e}")
        print(f"❌ Invalid JSON in config file: {e}")
        sys.exit(1)


def get_default_config() -> Dict[str, Any]:
    """
    Get default configuration.

    Returns:
        Default configuration dictionary
    """
    return {
        "version": "1.0",
        "framework_name": "Claude Code Mastery Framework (CCMF)",
        "repository_path": ".",
        "checkpoint_paths": [
            "./checkpoint.json",
            "./state.json",
            "./.ccmf/checkpoint.json"
        ],
        "mla_config": {
            "threshold": 5.0,
            "weight_progress": 0.6,
            "weight_efficiency": 0.4,
            "min_acceptable_lq": 2.0
        },
        "rsi_config": {
            "enable_logging": True,
            "enable_optimization": True
        },
        "verbose": False
    }


def run_pattern(
    pattern_name: str,
    inputs: Dict[str, Any],
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Execute a specific pattern with inputs.

    Args:
        pattern_name: Name of pattern to execute
        inputs: Input parameters for pattern
        config: Configuration dictionary

    Returns:
        Execution result dictionary
    """
    validator = ConstitutionalValidator()

    # Pattern registry
    patterns = {
        "direct_path": DirectPathAccessPattern(validator),
        "known_path_search": KnownPathSearchPattern(validator),
        "git_repo": GitRepositoryFilePattern(validator),
        "checkpoint_recovery": CheckpointRecoveryPattern(validator),
        "git_state_analysis": GitStateAnalysisPattern(validator),
        "composite_recovery": CompositeStateRecoveryPattern(validator)
    }

    if pattern_name not in patterns:
        logger.error(f"Unknown pattern: {pattern_name}")
        return {
            "success": False,
            "error": f"Unknown pattern: {pattern_name}",
            "available_patterns": list(patterns.keys())
        }

    pattern = patterns[pattern_name]
    logger.info(f"Executing pattern: {pattern_name}")

    # Execute pattern with validation
    success, result, error = pattern.execute_with_validation(inputs)

    if not success:
        logger.error(f"Pattern execution failed: {error}")
        return {
            "success": False,
            "pattern": pattern_name,
            "error": error
        }

    # Check MLA compliance
    mla_config = config.get("mla_config", {})
    threshold = mla_config.get("threshold", 5.0)
    lq_score = result.get("lq_score", 0.0) if isinstance(result, dict) else 0.0

    mla_compliant = lq_score >= threshold

    # Get violation report
    violations = validator.get_violations()
    violation_count = len(violations)

    # Build final result
    final_result = {
        "success": success,
        "pattern": pattern_name,
        "pattern_id": pattern.pattern_id,
        "lq_score": lq_score,
        "mla_compliant": mla_compliant,
        "mla_threshold": threshold,
        "violation_count": violation_count,
        "result": result
    }

    # Print violations if any
    if violations:
        print("\n⚠️  Constitutional Violations Detected:")
        for i, v in enumerate(violations[:5], 1):
            print(f"  {i}. [{v.severity.value.upper()}] {v.protocol}: {v.violation_type}")
        if len(violations) > 5:
            print(f"  ... and {len(violations) - 5} more")

    # Print MLA compliance
    if mla_compliant:
        print(f"\n✅ MLA Compliant: LQ Score {lq_score:.2f} >= Threshold {threshold:.2f}")
    else:
        print(f"\n⚠️  MLA Warning: LQ Score {lq_score:.2f} < Threshold {threshold:.2f}")

    return final_result


def run_demo():
    """Run interactive demo."""
    print_banner()
    print("🚀 Starting CCMF v1.0 Interactive Demo\n")

    try:
        from agno import ccmf_demo
        ccmf_demo.main()
    except ImportError as e:
        logger.error(f"Could not import ccmf_demo: {e}")
        print(f"❌ Error: Could not load demo module: {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception("Demo failed")
        print(f"❌ Demo error: {e}")
        sys.exit(1)


def run_tests(verbose: bool = False) -> bool:
    """
    Run test suite.

    Args:
        verbose: Enable verbose output

    Returns:
        True if tests passed, False otherwise
    """
    print_banner()
    print("🧪 Running CCMF v1.0 Test Suite\n")

    try:
        # Try to import test module
        from agno import ccmf_tests

        # Try running with unittest
        import unittest
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromModule(ccmf_tests)

        runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
        result = runner.run(suite)

        # Print summary
        print("\n" + "=" * 80)
        print("Test Summary")
        print("=" * 80)
        print(f"Tests run: {result.testsRun}")
        print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
        print(f"Failures: {len(result.failures)}")
        print(f"Errors: {len(result.errors)}")
        print("=" * 80)

        return result.wasSuccessful()

    except ImportError as e:
        logger.error(f"Could not import ccmf_tests: {e}")
        print(f"❌ Error: Could not load test module: {e}")
        print("⚠️  Make sure PYTHONPATH is set correctly")
        return False
    except Exception as e:
        logger.exception("Test execution failed")
        print(f"❌ Test error: {e}")
        return False


def run_examples():
    """Run example demonstrations."""
    print_banner()
    print("📚 Running CCMF v1.0 Examples\n")

    try:
        from agno.ccmf_examples import run_all_examples

        results = run_all_examples()

        print("\n" + "=" * 80)
        print("Examples Summary")
        print("=" * 80)

        successful = sum(1 for e in results["examples"] if e.get("status") == "success")
        total = len(results["examples"])

        print(f"Completed: {successful}/{total} examples")
        print("=" * 80)

        return successful == total

    except ImportError as e:
        logger.error(f"Could not import ccmf_examples: {e}")
        print(f"❌ Error: Could not load examples module: {e}")
        return False
    except Exception as e:
        logger.exception("Examples failed")
        print(f"❌ Examples error: {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Claude Code Mastery Framework (CCMF) v1.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test file existence
  %(prog)s --pattern direct_path --file-path /home/user/agno/README.md --operation test

  # Search through paths
  %(prog)s --pattern known_path_search --search-paths ./config.json ./package.json

  # List repository files
  %(prog)s --pattern git_repo --repo-path /home/user/agno --operation list --file-pattern "*.py"

  # Run interactive demo
  %(prog)s --demo

  # Run test suite
  %(prog)s --run-tests
        """
    )

    # Pattern selection
    parser.add_argument(
        "--pattern",
        type=str,
        choices=["direct_path", "known_path_search", "git_repo",
                 "checkpoint_recovery", "git_state_analysis", "composite_recovery"],
        help="Pattern to execute"
    )

    # Pattern-specific arguments
    parser.add_argument(
        "--file-path",
        type=str,
        help="File path for direct_path pattern"
    )

    parser.add_argument(
        "--search-paths",
        type=str,
        nargs="+",
        help="Search paths for known_path_search pattern"
    )

    parser.add_argument(
        "--repo-path",
        type=str,
        help="Repository path for git patterns"
    )

    parser.add_argument(
        "--file-pattern",
        type=str,
        default="*",
        help="File pattern for git operations (default: *)"
    )

    parser.add_argument(
        "--operation",
        type=str,
        default="test",
        help="Operation type (test, read, list, log, etc.)"
    )

    # Configuration
    parser.add_argument(
        "--config",
        type=str,
        default="ccmf_config.json",
        help="Path to configuration file (default: ccmf_config.json)"
    )

    # Special modes
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run interactive demo"
    )

    parser.add_argument(
        "--run-tests",
        action="store_true",
        help="Run test suite"
    )

    parser.add_argument(
        "--run-examples",
        action="store_true",
        help="Run all examples"
    )

    # Output control
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )

    parser.add_argument(
        "--json-output",
        action="store_true",
        help="Output results as JSON"
    )

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load configuration
    config = load_config(args.config)
    if args.verbose:
        config["verbose"] = True

    # Route to appropriate action
    if args.demo:
        run_demo()
        return

    if args.run_tests:
        success = run_tests(verbose=args.verbose)
        sys.exit(0 if success else 1)

    if args.run_examples:
        success = run_examples()
        sys.exit(0 if success else 1)

    if not args.pattern:
        print_banner()
        parser.print_help()
        print("\n💡 Quick Start:")
        print("  --demo          Launch interactive demonstration")
        print("  --run-tests     Run test suite")
        print("  --run-examples  Run all examples")
        print()
        return

    # Build inputs based on pattern
    inputs = {}

    if args.pattern == "direct_path":
        if not args.file_path:
            print("❌ Error: --file-path required for direct_path pattern")
            sys.exit(1)
        inputs = {
            "file_path": args.file_path,
            "operation": args.operation
        }

    elif args.pattern == "known_path_search":
        if not args.search_paths:
            print("❌ Error: --search-paths required for known_path_search pattern")
            sys.exit(1)
        inputs = {
            "search_paths": args.search_paths,
            "read_content": False
        }

    elif args.pattern == "git_repo":
        repo_path = args.repo_path or config.get("repository_path", ".")
        inputs = {
            "repo_path": repo_path,
            "operation": args.operation,
            "file_pattern": args.file_pattern
        }

    elif args.pattern == "git_state_analysis":
        repo_path = args.repo_path or config.get("repository_path", ".")
        inputs = {
            "repo_path": repo_path,
            "analysis_depth": 10
        }

    elif args.pattern == "checkpoint_recovery":
        checkpoint_paths = config.get("checkpoint_paths", [])
        inputs = {
            "checkpoint_paths": checkpoint_paths,
            "recovery_strategy": "latest"
        }

    elif args.pattern == "composite_recovery":
        repo_path = args.repo_path or config.get("repository_path", ".")
        checkpoint_paths = config.get("checkpoint_paths", [])
        inputs = {
            "repo_path": repo_path,
            "checkpoint_paths": checkpoint_paths,
            "fallback_paths": []
        }

    # Execute pattern
    print_banner()
    print(f"🔧 Executing Pattern: {args.pattern}")
    print(f"📥 Inputs:")
    for key, value in inputs.items():
        if isinstance(value, list):
            print(f"   {key}: {len(value)} items")
        else:
            print(f"   {key}: {value}")
    print()

    result = run_pattern(args.pattern, inputs, config)

    # Output result
    if args.json_output:
        print(json.dumps(result, indent=2, default=str))
    else:
        print("\n📤 Result:")
        print(f"   Success: {result.get('success')}")
        print(f"   Pattern: {result.get('pattern')}")
        print(f"   LQ Score: {result.get('lq_score', 0):.2f}")

        if result.get('result'):
            res = result['result']
            if isinstance(res, dict):
                # Print key result metrics
                for key in ['count', 'files', 'exists', 'found', 'current_branch', 'is_clean']:
                    if key in res:
                        value = res[key]
                        if isinstance(value, list):
                            print(f"   {key}: {len(value)} items")
                        else:
                            print(f"   {key}: {value}")

    # Exit with appropriate code
    sys.exit(0 if result.get("success", False) else 1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.exception("Fatal error")
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
