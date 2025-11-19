"""
FSA CLI Interface - Command-line interface for FSA operations

Provides commands for initializing, building, optimizing, validating,
and orchestrating FSA workflows from the command line.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

from agno.fsa.registry import FSARegistry, get_registry, FSAHealthStatus
from agno.fsa.pipeline_manager import FSAPipeline, FSAPipelineManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FSACLIHandler:
    """
    Command-line interface handler for FSA operations

    Commands:
    - init: Initialize FSA configuration
    - build: Build an FSA pipeline from configuration
    - optimize: Optimize FSA performance
    - validate: Validate FSA configuration and health
    - orchestrate: Execute FSA orchestration
    - list: List registered FSA modules
    - health: Check FSA module health
    """

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or ".fsarc.json"
        self.config: Dict[str, Any] = {}
        self.registry = get_registry()
        self.pipeline_manager = FSAPipelineManager(registry=self.registry)
        self._load_config()

    def _load_config(self) -> None:
        """Load FSA configuration from file"""
        config_file = Path(self.config_path)
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    self.config = json.load(f)
                logger.info(f"Loaded FSA configuration from {self.config_path}")
            except Exception as e:
                logger.warning(f"Failed to load config from {self.config_path}: {e}")
                self.config = {}
        else:
            logger.debug(f"No configuration file found at {self.config_path}")
            self.config = {}

    def _save_config(self) -> None:
        """Save FSA configuration to file"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            logger.info(f"Saved FSA configuration to {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to save config to {self.config_path}: {e}")

    def init(self, args: argparse.Namespace) -> int:
        """
        Initialize FSA configuration

        Creates a default .fsarc.json configuration file
        """
        print("🚀 Initializing FSA Framework Configuration")

        # Check if config already exists
        if Path(self.config_path).exists() and not args.force:
            print(f"❌ Configuration file already exists at {self.config_path}")
            print("   Use --force to overwrite")
            return 1

        # Create default configuration
        default_config = {
            "version": "1.0.0",
            "modules": {},
            "pipelines": {},
            "settings": {
                "max_workers": 4,
                "enable_caching": True,
                "cache_ttl_seconds": 3600,
                "log_level": "INFO",
            },
            "created_at": datetime.now().isoformat(),
        }

        self.config = default_config
        self._save_config()

        print(f"✅ Created FSA configuration at {self.config_path}")
        print(f"   Version: {default_config['version']}")
        print(f"   Settings: {json.dumps(default_config['settings'], indent=2)}")

        return 0

    def build(self, args: argparse.Namespace) -> int:
        """
        Build an FSA pipeline from configuration

        Creates a pipeline based on the configuration file
        """
        print("🔨 Building FSA Pipeline")

        if not self.config:
            print("❌ No configuration loaded. Run 'fsa init' first.")
            return 1

        pipeline_name = args.pipeline
        if pipeline_name not in self.config.get("pipelines", {}):
            print(f"❌ Pipeline '{pipeline_name}' not found in configuration")
            return 1

        pipeline_config = self.config["pipelines"][pipeline_name]

        try:
            # Create pipeline
            pipeline = FSAPipeline(
                name=pipeline_name,
                description=pipeline_config.get("description", ""),
                registry=self.registry,
            )

            # Add stages
            for stage_config in pipeline_config.get("stages", []):
                pipeline.add_stage(
                    name=stage_config["name"],
                    fsa_module_name=stage_config.get("fsa_module"),
                    inputs=stage_config.get("inputs", {}),
                    depends_on=stage_config.get("depends_on", []),
                    retry_config=stage_config.get("retry_config"),
                    timeout_ms=stage_config.get("timeout_ms"),
                    parallel=stage_config.get("parallel", False),
                )

            print(f"✅ Built pipeline '{pipeline_name}' with {len(pipeline.stages)} stages")

            # Show execution order
            execution_order = pipeline.get_execution_order()
            print("\n📊 Execution Order:")
            for i, batch in enumerate(execution_order, 1):
                if len(batch) > 1:
                    print(f"   Batch {i} (parallel): {', '.join(batch)}")
                else:
                    print(f"   Stage {i}: {batch[0]}")

            # Execute if requested
            if args.execute:
                print(f"\n▶️  Executing pipeline '{pipeline_name}'...")
                result = self.pipeline_manager.execute_pipeline(
                    pipeline,
                    initial_inputs=args.inputs or {},
                )

                print(f"\n{'✅' if result.is_successful() else '❌'} Pipeline Status: {result.status}")
                print(f"   Duration: {result.total_duration_ms:.2f}ms")
                print(f"   Success Rate: {result.success_rate*100:.1f}%")

                if args.verbose:
                    print("\n📝 Stage Results:")
                    for stage_result in result.stage_results:
                        status_emoji = "✅" if stage_result.is_successful() else "❌"
                        print(f"   {status_emoji} {stage_result.stage_name}: {stage_result.status.value}")
                        if stage_result.error:
                            print(f"      Error: {stage_result.error}")

            return 0

        except Exception as e:
            print(f"❌ Failed to build pipeline: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()
            return 1

    def optimize(self, args: argparse.Namespace) -> int:
        """
        Optimize FSA performance

        Analyzes pipeline performance and suggests optimizations
        """
        print("⚡ Optimizing FSA Performance")

        # Get metrics
        metrics = self.pipeline_manager.get_metrics()

        if not metrics:
            print("ℹ️  No performance data available yet")
            print("   Execute some pipelines first to collect metrics")
            return 0

        print("\n📊 Performance Metrics:")
        for pipeline_name, pipeline_metrics in metrics.items():
            print(f"\n   Pipeline: {pipeline_name}")
            print(f"   ├─ Executions: {pipeline_metrics['execution_count']}")
            print(f"   ├─ Avg Duration: {pipeline_metrics['avg_duration_ms']:.2f}ms")
            print(f"   ├─ Min Duration: {pipeline_metrics['min_duration_ms']:.2f}ms")
            print(f"   ├─ Max Duration: {pipeline_metrics['max_duration_ms']:.2f}ms")
            print(f"   └─ P95 Duration: {pipeline_metrics['p95_duration_ms']:.2f}ms")

            # Optimization suggestions
            avg_duration = pipeline_metrics['avg_duration_ms']
            if avg_duration > 1000:
                print(f"      💡 Consider enabling parallel execution for independent stages")
            if pipeline_metrics['max_duration_ms'] > avg_duration * 3:
                print(f"      💡 High variance detected - check for intermittent issues")

        return 0

    def validate(self, args: argparse.Namespace) -> int:
        """
        Validate FSA configuration and health

        Checks configuration validity and performs health checks on modules
        """
        print("🔍 Validating FSA Configuration")

        # Validate config file
        if not self.config:
            print("⚠️  No configuration loaded")
            return 1

        config_issues = []

        # Check required fields
        if "version" not in self.config:
            config_issues.append("Missing 'version' field")

        if "settings" not in self.config:
            config_issues.append("Missing 'settings' field")

        # Validate pipelines
        for pipeline_name, pipeline_config in self.config.get("pipelines", {}).items():
            if "stages" not in pipeline_config:
                config_issues.append(f"Pipeline '{pipeline_name}' missing 'stages'")

        if config_issues:
            print("\n❌ Configuration Issues:")
            for issue in config_issues:
                print(f"   • {issue}")
            return 1

        print("✅ Configuration is valid")

        # Health checks
        if args.health_check:
            print("\n🏥 Running Health Checks...")
            health_results = self.registry.health_check_all()

            healthy_count = sum(1 for h in health_results.values() if h.is_healthy())
            total_count = len(health_results)

            print(f"\n📊 Health Status: {healthy_count}/{total_count} modules healthy")

            for module_name, health in health_results.items():
                status_emoji = {
                    FSAHealthStatus.HEALTHY: "✅",
                    FSAHealthStatus.DEGRADED: "⚠️",
                    FSAHealthStatus.UNHEALTHY: "❌",
                    FSAHealthStatus.UNKNOWN: "❓",
                }[health.status]

                print(f"   {status_emoji} {module_name}: {health.status.value}")
                if args.verbose:
                    print(f"      Message: {health.message}")
                    print(f"      Last Check: {health.last_check.isoformat()}")

        return 0

    def orchestrate(self, args: argparse.Namespace) -> int:
        """
        Execute FSA orchestration

        Runs a complete FSA workflow orchestration
        """
        print("🎭 Executing FSA Orchestration")

        pipeline_name = args.pipeline
        if not pipeline_name:
            print("❌ Pipeline name required (use --pipeline)")
            return 1

        # Load inputs from file if provided
        inputs = {}
        if args.inputs_file:
            try:
                with open(args.inputs_file, 'r') as f:
                    inputs = json.load(f)
                print(f"📄 Loaded inputs from {args.inputs_file}")
            except Exception as e:
                print(f"❌ Failed to load inputs: {e}")
                return 1

        # Build and execute pipeline
        args.execute = True
        return self.build(args)

    def list_modules(self, args: argparse.Namespace) -> int:
        """
        List registered FSA modules

        Shows all modules registered in the FSA registry
        """
        print("📋 Registered FSA Modules")

        modules = self.registry.list_modules()

        if not modules:
            print("ℹ️  No modules registered yet")
            return 0

        print(f"\nFound {len(modules)} registered modules:\n")

        for module in modules:
            status = "🟢" if module["instantiated"] else "⚪"
            print(f"{status} {module['name']} (v{module['version']})")
            if module['dependencies']:
                print(f"   ├─ Dependencies: {', '.join(module['dependencies'])}")
            print(f"   ├─ Lazy Load: {module['lazy_load']}")
            print(f"   └─ Instantiated: {module['instantiated']}")

            if args.verbose and module['metadata']:
                print(f"      Metadata: {json.dumps(module['metadata'], indent=6)}")
            print()

        return 0

    def health_check(self, args: argparse.Namespace) -> int:
        """
        Check health of FSA modules

        Performs health checks on specified or all modules
        """
        print("🏥 FSA Module Health Check")

        if args.module:
            # Check specific module
            health = self.registry.health_check(args.module, force=True)

            status_emoji = {
                FSAHealthStatus.HEALTHY: "✅",
                FSAHealthStatus.DEGRADED: "⚠️",
                FSAHealthStatus.UNHEALTHY: "❌",
                FSAHealthStatus.UNKNOWN: "❓",
            }[health.status]

            print(f"\n{status_emoji} {args.module}: {health.status.value}")
            print(f"   Message: {health.message}")
            print(f"   Last Check: {health.last_check.isoformat()}")

            if health.metadata:
                print(f"   Metadata:")
                for key, value in health.metadata.items():
                    print(f"      • {key}: {value}")

            return 0 if health.is_healthy() else 1

        else:
            # Check all modules
            health_results = self.registry.health_check_all()

            healthy_count = sum(1 for h in health_results.values() if h.is_healthy())
            total_count = len(health_results)

            print(f"\n📊 Overall: {healthy_count}/{total_count} modules healthy\n")

            for module_name, health in health_results.items():
                status_emoji = {
                    FSAHealthStatus.HEALTHY: "✅",
                    FSAHealthStatus.DEGRADED: "⚠️",
                    FSAHealthStatus.UNHEALTHY: "❌",
                    FSAHealthStatus.UNKNOWN: "❓",
                }[health.status]

                print(f"{status_emoji} {module_name}: {health.status.value}")
                if args.verbose:
                    print(f"   Message: {health.message}")

            return 0 if healthy_count == total_count else 1


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for FSA CLI"""
    parser = argparse.ArgumentParser(
        description="FSA Framework Command-Line Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--config",
        type=str,
        default=".fsarc.json",
        help="Path to FSA configuration file",
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Init command
    init_parser = subparsers.add_parser("init", help="Initialize FSA configuration")
    init_parser.add_argument("--force", action="store_true", help="Overwrite existing configuration")

    # Build command
    build_parser = subparsers.add_parser("build", help="Build FSA pipeline")
    build_parser.add_argument("pipeline", type=str, help="Pipeline name")
    build_parser.add_argument("--execute", action="store_true", help="Execute pipeline after building")
    build_parser.add_argument("--inputs", type=json.loads, help="Pipeline inputs as JSON")

    # Optimize command
    optimize_parser = subparsers.add_parser("optimize", help="Optimize FSA performance")

    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate FSA configuration")
    validate_parser.add_argument("--health-check", action="store_true", help="Include health checks")

    # Orchestrate command
    orchestrate_parser = subparsers.add_parser("orchestrate", help="Execute FSA orchestration")
    orchestrate_parser.add_argument("pipeline", type=str, help="Pipeline name")
    orchestrate_parser.add_argument("--inputs-file", type=str, help="Path to inputs JSON file")

    # List command
    list_parser = subparsers.add_parser("list", help="List registered FSA modules")

    # Health command
    health_parser = subparsers.add_parser("health", help="Check FSA module health")
    health_parser.add_argument("--module", type=str, help="Specific module to check")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point for FSA CLI"""
    parser = create_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    # Configure logging based on verbosity
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Create CLI handler
    handler = FSACLIHandler(config_path=args.config)

    # Execute command
    command_map = {
        "init": handler.init,
        "build": handler.build,
        "optimize": handler.optimize,
        "validate": handler.validate,
        "orchestrate": handler.orchestrate,
        "list": handler.list_modules,
        "health": handler.health_check,
    }

    command_func = command_map.get(args.command)
    if command_func:
        try:
            return command_func(args)
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted by user")
            return 130
        except Exception as e:
            print(f"\n❌ Error: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()
            return 1
    else:
        print(f"Unknown command: {args.command}")
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
