#!/usr/bin/env python3
"""
CCMF Main CLI Entry Point - SESSION 2 Part 2
=============================================

Main command-line interface for the Constitutional Cognitive Meta-Framework.

This module provides a comprehensive CLI with subcommands for:
- Pattern execution
- Workflow management
- Performance analysis
- Metrics display
- Compliance validation

Usage:
    ccmf_main.py run-pattern <pattern_name> [options]
    ccmf_main.py run-workflow <workflow_file> [options]
    ccmf_main.py analyze-performance [options]
    ccmf_main.py show-metrics [options]
    ccmf_main.py validate-compliance <context_file> [options]

Configuration:
    Loads settings from ccmf_config.json by default.
    Use --config to specify a different configuration file.
"""

import argparse
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import traceback

# Import CCMF modules
from ccmf_constitutional import validate_operation, ConstitutionalFramework
from ccmf_patterns import (
    DirectPathAccessPattern, KnownPathSearchPattern,
    GitRepositoryFilePattern, CheckpointRecoveryPattern,
    GitStateAnalysisPattern, CompositeStateRecoveryPattern,
    get_pattern
)
from ccmf_rsi_loop import RSIFeedbackLoop, FeedbackType
from ccmf_workflows import WorkflowBuilder
from ccmf_meta_learning import MetaLearningArchitecture

# Version information
__version__ = "1.0.0"
__author__ = "CCMF Development Team"

# Exit codes
EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_CONFIG_ERROR = 2
EXIT_INVALID_INPUT = 3
EXIT_PATTERN_ERROR = 4
EXIT_WORKFLOW_ERROR = 5


# =============================================================================
# Configuration Management
# =============================================================================

class CCMFConfig:
    """Configuration manager for CCMF."""

    def __init__(self, config_path: str = "ccmf_config.json"):
        """
        Initialize configuration manager.

        Args:
            config_path: Path to configuration file
        """
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self.load_config()

    def load_config(self):
        """Load configuration from file."""
        if not self.config_path.exists():
            logging.warning(f"Config file not found: {self.config_path}. Using defaults.")
            self.config = self._get_default_config()
            return

        try:
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
            logging.info(f"Loaded configuration from {self.config_path}")
        except Exception as e:
            logging.error(f"Error loading config: {e}")
            self.config = self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "paths": {
                "checkpoints_dir": ".ccmf_checkpoints",
                "logs_dir": ".ccmf_logs",
                "repositories": {"default": "."}
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            },
            "rsi_loop": {"enabled": True},
            "meta_learning": {"enabled": True}
        }

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.

        Args:
            key: Configuration key (supports dot notation, e.g., "paths.logs_dir")
            default: Default value if key not found

        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self.config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value


# =============================================================================
# Logging Setup
# =============================================================================

def setup_logging(config: CCMFConfig, verbose: bool = False, quiet: bool = False):
    """
    Setup logging configuration.

    Args:
        config: Configuration manager
        verbose: Enable verbose logging
        quiet: Enable quiet mode (errors only)
    """
    # Determine log level
    if quiet:
        level = logging.ERROR
    elif verbose:
        level = logging.DEBUG
    else:
        level_name = config.get("logging.level", "INFO")
        level = getattr(logging, level_name, logging.INFO)

    # Setup format
    log_format = config.get("logging.format",
                           "%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Create logs directory
    logs_dir = Path(config.get("paths.logs_dir", ".ccmf_logs"))
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Configure logging
    logging.basicConfig(
        level=level,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(logs_dir / "ccmf_cli.log")
        ]
    )


# =============================================================================
# Pattern Execution
# =============================================================================

def run_pattern_command(args, config: CCMFConfig) -> int:
    """
    Execute a cognitive pattern.

    Args:
        args: Command arguments
        config: Configuration manager

    Returns:
        Exit code
    """
    logging.info(f"Running pattern: {args.pattern}")

    try:
        # Get pattern
        pattern_name = args.pattern
        pattern_class_name = f"{pattern_name}Pattern" if not pattern_name.endswith("Pattern") else pattern_name

        # Create pattern instance
        if pattern_class_name == "CheckpointRecoveryPattern":
            checkpoint_dir = config.get("patterns.CheckpointRecoveryPattern.default_checkpoint_dir",
                                       ".ccmf_checkpoints")
            pattern = get_pattern(pattern_class_name, checkpoint_dir=checkpoint_dir)
        elif pattern_class_name == "CompositeStateRecoveryPattern":
            checkpoint_dir = config.get("patterns.CompositeStateRecoveryPattern.default_checkpoint_dir",
                                       ".ccmf_checkpoints")
            pattern = get_pattern(pattern_class_name, checkpoint_dir=checkpoint_dir)
        else:
            pattern = get_pattern(pattern_class_name)

        # Parse parameters
        parameters = {}
        if args.parameters:
            try:
                parameters = json.loads(args.parameters)
            except json.JSONDecodeError as e:
                logging.error(f"Invalid JSON in parameters: {e}")
                return EXIT_INVALID_INPUT

        # Execute pattern
        logging.info(f"Executing pattern with parameters: {parameters}")
        result = pattern.execute(**parameters)

        # Display result
        print("\n" + "=" * 70)
        print(f"Pattern: {pattern.name}")
        print("=" * 70)
        print(f"Success: {result.success}")
        print(f"Execution Time: {result.execution_time:.4f}s")

        if result.success:
            print(f"\nResult Data:")
            if isinstance(result.data, dict):
                for key, value in result.data.items():
                    print(f"  {key}: {value}")
            else:
                print(f"  {result.data}")

            print(f"\nMetadata:")
            for key, value in result.metadata.items():
                print(f"  {key}: {value}")
        else:
            print(f"\nError: {result.error}")

        # Pattern statistics
        stats = pattern.get_stats()
        print(f"\nPattern Statistics:")
        print(f"  Total Executions: {stats['executions']}")
        print(f"  Success Rate: {stats['success_rate']:.2f}%")

        return EXIT_SUCCESS if result.success else EXIT_PATTERN_ERROR

    except Exception as e:
        logging.error(f"Error executing pattern: {e}")
        if args.verbose:
            traceback.print_exc()
        return EXIT_PATTERN_ERROR


# =============================================================================
# Workflow Execution
# =============================================================================

def run_workflow_command(args, config: CCMFConfig) -> int:
    """
    Execute a workflow from file.

    Args:
        args: Command arguments
        config: Configuration manager

    Returns:
        Exit code
    """
    logging.info(f"Running workflow: {args.workflow_file}")

    try:
        # Load workflow definition
        workflow_path = Path(args.workflow_file)
        if not workflow_path.exists():
            logging.error(f"Workflow file not found: {workflow_path}")
            return EXIT_INVALID_INPUT

        with open(workflow_path, 'r') as f:
            workflow_def = json.load(f)

        # Build workflow
        builder = WorkflowBuilder(
            workflow_id=workflow_def.get('workflow_id', 'cli_workflow'),
            name=workflow_def.get('name', 'CLI Workflow'),
            description=workflow_def.get('description', '')
        )

        # Enable RSI if configured
        if config.get("rsi_loop.enabled", True):
            builder.with_rsi(True)

        # Add steps
        for step_def in workflow_def.get('steps', []):
            pattern_name = step_def['pattern']
            pattern = get_pattern(pattern_name)

            builder.add_pattern_step(
                step_id=step_def['step_id'],
                name=step_def['name'],
                pattern=pattern,
                parameters=step_def.get('parameters', {}),
                description=step_def.get('description', ''),
                depends_on=step_def.get('depends_on', [])
            )

        # Build and execute
        workflow = builder.build()
        logging.info(f"Executing workflow: {workflow.name}")

        result = workflow.execute()

        # Display results
        print("\n" + "=" * 70)
        print(f"Workflow: {result['name']}")
        print("=" * 70)
        print(f"Status: {result['status']}")
        print(f"Total Execution Time: {result['total_execution_time']:.4f}s")

        print(f"\nSteps Summary:")
        print(f"  Total: {result['steps']['total']}")
        print(f"  Completed: {result['steps']['completed']}")
        print(f"  Failed: {result['steps']['failed']}")
        print(f"  Skipped: {result['steps']['skipped']}")

        print(f"\nStep Details:")
        for step in result['step_details']:
            status_icon = "✓" if step['status'] == 'completed' else "✗" if step['status'] == 'failed' else "○"
            print(f"  {status_icon} {step['name']}: {step['status']} ({step['execution_time']:.4f}s)")

        return EXIT_SUCCESS if result['status'] == 'completed' else EXIT_WORKFLOW_ERROR

    except Exception as e:
        logging.error(f"Error executing workflow: {e}")
        if args.verbose:
            traceback.print_exc()
        return EXIT_WORKFLOW_ERROR


# =============================================================================
# Performance Analysis
# =============================================================================

def analyze_performance_command(args, config: CCMFConfig) -> int:
    """
    Analyze performance using RSI feedback loop.

    Args:
        args: Command arguments
        config: Configuration manager

    Returns:
        Exit code
    """
    logging.info("Analyzing performance")

    try:
        # Create RSI loop
        rsi_loop = RSIFeedbackLoop()

        # Load feedback history if available
        # (In a real implementation, this would load from persistent storage)

        # Analyze performance
        analysis = rsi_loop.analyze_performance()

        # Display results
        print("\n" + "=" * 70)
        print("Performance Analysis")
        print("=" * 70)

        print(f"\nReady for Adaptation: {analysis.get('ready_for_adaptation', False)}")
        print(f"Health Score: {analysis.get('health_score', 0.0):.2%}")

        if 'current_metrics' in analysis:
            metrics = analysis['current_metrics']
            print(f"\nCurrent Metrics:")
            print(f"  Success Rate: {metrics.get('success_rate', 0.0):.2%}")
            print(f"  Avg Execution Time: {metrics.get('execution_time', 0.0):.4f}s")
            print(f"  Quality Score: {metrics.get('quality_score', 0.0):.4f}")
            print(f"  Error Count: {metrics.get('error_count', 0)}")

        if 'trends' in analysis:
            print(f"\nTrends:")
            for trend_name, trend_value in analysis['trends'].items():
                print(f"  {trend_name}: {trend_value}")

        if analysis.get('problems'):
            print(f"\nProblems Identified ({len(analysis['problems'])}):")
            for problem in analysis['problems']:
                print(f"  • {problem['description']} (severity: {problem['severity']:.2f})")

        # Run improvement cycle if requested
        if args.run_cycle:
            print("\n" + "-" * 70)
            print("Running Improvement Cycle")
            print("-" * 70)

            cycle_result = rsi_loop.run_improvement_cycle()

            print(f"\nCycle completed at: {cycle_result['timestamp']}")
            print(f"Current health: {cycle_result['current_health']:.2%}")
            print(f"Adapted: {cycle_result['adapted']}")

            if cycle_result['decision']:
                decision = cycle_result['decision']
                print(f"\nAdaptation Decision:")
                print(f"  Strategy: {decision['strategy']}")
                print(f"  Reason: {decision['reason']}")
                print(f"  Confidence: {decision['confidence']:.2%}")

        return EXIT_SUCCESS

    except Exception as e:
        logging.error(f"Error analyzing performance: {e}")
        if args.verbose:
            traceback.print_exc()
        return EXIT_FAILURE


# =============================================================================
# Metrics Display
# =============================================================================

def show_metrics_command(args, config: CCMFConfig) -> int:
    """
    Display performance metrics.

    Args:
        args: Command arguments
        config: Configuration manager

    Returns:
        Exit code
    """
    logging.info("Displaying metrics")

    try:
        # Create MLA
        mla = MetaLearningArchitecture()

        # Calculate leverage quotient
        quotient = mla.calculate_leverage_quotient()

        # Display results
        print("\n" + "=" * 70)
        print("Meta-Learning Architecture Metrics")
        print("=" * 70)

        print(f"\nMLA Leverage Quotient: {quotient.overall_quotient:.4f}")
        print(f"Grade: {quotient.get_grade()}")

        print(f"\nDetailed Metrics:")
        print(f"  Total Examples: {quotient.total_examples}")
        print(f"  Successful Examples: {quotient.successful_examples}")
        print(f"  Patterns Learned: {quotient.patterns_learned}")
        print(f"  Avg Performance Gain: {quotient.average_performance_gain:+.4f}")
        print(f"  Transfer Learning: {quotient.transfer_learning_effectiveness:.4f}")
        print(f"  Knowledge Reuse Rate: {quotient.knowledge_reuse_rate:.4f}")

        # Get learning insights
        insights = mla.get_learning_insights()

        if insights.get('top_performing_patterns'):
            print(f"\nTop Performing Patterns:")
            for pattern_info in insights['top_performing_patterns'][:5]:
                print(f"  • {pattern_info['name']}: {pattern_info['success_rate']:.2%} " +
                      f"({pattern_info['usage_count']} uses)")

        if insights.get('patterns_needing_improvement'):
            print(f"\nPatterns Needing Improvement:")
            for pattern_info in insights['patterns_needing_improvement']:
                print(f"  • {pattern_info['name']}: {pattern_info['success_rate']:.2%} " +
                      f"({pattern_info['usage_count']} uses)")

        # Export metrics if requested
        if args.export:
            export_path = Path(args.export)
            export_data = {
                'timestamp': datetime.now().isoformat(),
                'leverage_quotient': quotient.to_dict(),
                'insights': insights
            }

            with open(export_path, 'w') as f:
                json.dump(export_data, f, indent=2)

            print(f"\n✓ Metrics exported to: {export_path}")

        return EXIT_SUCCESS

    except Exception as e:
        logging.error(f"Error displaying metrics: {e}")
        if args.verbose:
            traceback.print_exc()
        return EXIT_FAILURE


# =============================================================================
# Compliance Validation
# =============================================================================

def validate_compliance_command(args, config: CCMFConfig) -> int:
    """
    Validate constitutional compliance.

    Args:
        args: Command arguments
        config: Configuration manager

    Returns:
        Exit code
    """
    logging.info(f"Validating compliance for context: {args.context_file}")

    try:
        # Load context
        context_path = Path(args.context_file)
        if not context_path.exists():
            logging.error(f"Context file not found: {context_path}")
            return EXIT_INVALID_INPUT

        with open(context_path, 'r') as f:
            context = json.load(f)

        # Validate compliance
        report = validate_operation(context)

        # Display results
        print("\n" + "=" * 70)
        print("Constitutional Compliance Validation")
        print("=" * 70)

        print(f"\nCompliance Level: {report.overall_compliance.value.upper()}")
        print(f"Compliance Score: {report.compliance_score:.2%}")

        print(f"\nPrinciples:")
        print(f"  Checked: {report.principles_checked}")
        print(f"  Passed: {report.principles_passed}")
        print(f"  Failed: {report.principles_failed}")

        if report.violations:
            print(f"\nViolations ({len(report.violations)}):")
            for violation in report.violations:
                mandatory_flag = " [MANDATORY]" if violation['mandatory'] else ""
                print(f"  • {violation['principle_name']}{mandatory_flag}")
                print(f"    Category: {violation['category']}")
                print(f"    Reason: {violation['reason']}")

        if report.recommendations:
            print(f"\nRecommendations:")
            for rec in report.recommendations:
                print(f"  • {rec}")

        # Export report if requested
        if args.export:
            export_path = Path(args.export)
            with open(export_path, 'w') as f:
                json.dump(report.to_dict(), f, indent=2)

            print(f"\n✓ Report exported to: {export_path}")

        # Return exit code based on compliance
        if report.principles_failed == 0:
            return EXIT_SUCCESS
        else:
            return EXIT_FAILURE

    except Exception as e:
        logging.error(f"Error validating compliance: {e}")
        if args.verbose:
            traceback.print_exc()
        return EXIT_FAILURE


# =============================================================================
# Argument Parser
# =============================================================================

def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        prog="ccmf",
        description="Constitutional Cognitive Meta-Framework (CCMF) CLI",
        epilog="For more information, see the documentation."
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"CCMF v{__version__}"
    )

    parser.add_argument(
        "--config",
        type=str,
        default="ccmf_config.json",
        help="Path to configuration file (default: ccmf_config.json)"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )

    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Quiet mode (errors only)"
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # run-pattern
    pattern_parser = subparsers.add_parser(
        "run-pattern",
        help="Execute a cognitive pattern"
    )
    pattern_parser.add_argument(
        "pattern",
        type=str,
        help="Pattern name (e.g., DirectPathAccess, KnownPathSearch)"
    )
    pattern_parser.add_argument(
        "--parameters", "-p",
        type=str,
        help="Pattern parameters as JSON string"
    )

    # run-workflow
    workflow_parser = subparsers.add_parser(
        "run-workflow",
        help="Execute a workflow from file"
    )
    workflow_parser.add_argument(
        "workflow_file",
        type=str,
        help="Path to workflow definition file (JSON)"
    )

    # analyze-performance
    analyze_parser = subparsers.add_parser(
        "analyze-performance",
        help="Analyze system performance"
    )
    analyze_parser.add_argument(
        "--run-cycle",
        action="store_true",
        help="Run improvement cycle after analysis"
    )

    # show-metrics
    metrics_parser = subparsers.add_parser(
        "show-metrics",
        help="Display performance metrics"
    )
    metrics_parser.add_argument(
        "--export",
        type=str,
        help="Export metrics to file (JSON)"
    )

    # validate-compliance
    compliance_parser = subparsers.add_parser(
        "validate-compliance",
        help="Validate constitutional compliance"
    )
    compliance_parser.add_argument(
        "context_file",
        type=str,
        help="Path to context file (JSON)"
    )
    compliance_parser.add_argument(
        "--export",
        type=str,
        help="Export report to file (JSON)"
    )

    return parser


# =============================================================================
# Main Entry Point
# =============================================================================

def main() -> int:
    """
    Main entry point for CCMF CLI.

    Returns:
        Exit code
    """
    # Parse arguments
    parser = create_parser()
    args = parser.parse_args()

    # Load configuration
    try:
        config = CCMFConfig(args.config)
    except Exception as e:
        print(f"Error loading configuration: {e}", file=sys.stderr)
        return EXIT_CONFIG_ERROR

    # Setup logging
    setup_logging(config, args.verbose, args.quiet)

    # Log startup
    logging.info(f"CCMF CLI v{__version__} started")
    logging.info(f"Configuration loaded from: {args.config}")

    # Handle command
    if not args.command:
        parser.print_help()
        return EXIT_SUCCESS

    try:
        if args.command == "run-pattern":
            return run_pattern_command(args, config)
        elif args.command == "run-workflow":
            return run_workflow_command(args, config)
        elif args.command == "analyze-performance":
            return analyze_performance_command(args, config)
        elif args.command == "show-metrics":
            return show_metrics_command(args, config)
        elif args.command == "validate-compliance":
            return validate_compliance_command(args, config)
        else:
            parser.print_help()
            return EXIT_INVALID_INPUT

    except KeyboardInterrupt:
        logging.warning("Operation cancelled by user")
        return EXIT_FAILURE
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        if args.verbose:
            traceback.print_exc()
        return EXIT_FAILURE


if __name__ == "__main__":
    sys.exit(main())
