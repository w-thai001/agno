"""
CCMF Interactive Demonstration - SESSION 2
===========================================

Interactive CLI demonstration of the Constitutional Cognitive Meta-Framework.

Features:
- Interactive menu system
- Colored output (with fallback to plain text)
- Live demonstrations of all CCMF capabilities
- Performance metrics and execution logs
- User-friendly interface

Run this module to experience the CCMF framework interactively!
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable, List, Dict, Any

# Import all CCMF modules
from ccmf_constitutional import (
    ConstitutionalFramework, validate_operation, ComplianceLevel
)
from ccmf_patterns import (
    DirectPathAccessPattern, KnownPathSearchPattern,
    GitRepositoryFilePattern, CheckpointRecoveryPattern,
    GitStateAnalysisPattern, CompositeStateRecoveryPattern
)
from ccmf_rsi_loop import RSIFeedbackLoop, FeedbackType
from ccmf_workflows import WorkflowBuilder
from ccmf_meta_learning import MetaLearningArchitecture

# Try to import colorama for colored output
try:
    from colorama import init, Fore, Back, Style
    init(autoreset=True)
    HAS_COLOR = True
except ImportError:
    HAS_COLOR = False
    # Fallback: create dummy color objects
    class DummyColor:
        def __getattr__(self, name):
            return ""
    Fore = Back = Style = DummyColor()


# =============================================================================
# Color Utilities
# =============================================================================

class Colors:
    """Color utilities with fallback support."""

    @staticmethod
    def header(text: str) -> str:
        """Return header styled text."""
        return f"{Fore.CYAN}{Style.BRIGHT}{text}{Style.RESET_ALL}" if HAS_COLOR else text

    @staticmethod
    def success(text: str) -> str:
        """Return success styled text."""
        return f"{Fore.GREEN}{text}{Style.RESET_ALL}" if HAS_COLOR else text

    @staticmethod
    def error(text: str) -> str:
        """Return error styled text."""
        return f"{Fore.RED}{text}{Style.RESET_ALL}" if HAS_COLOR else text

    @staticmethod
    def warning(text: str) -> str:
        """Return warning styled text."""
        return f"{Fore.YELLOW}{text}{Style.RESET_ALL}" if HAS_COLOR else text

    @staticmethod
    def info(text: str) -> str:
        """Return info styled text."""
        return f"{Fore.BLUE}{text}{Style.RESET_ALL}" if HAS_COLOR else text

    @staticmethod
    def highlight(text: str) -> str:
        """Return highlighted text."""
        return f"{Fore.MAGENTA}{Style.BRIGHT}{text}{Style.RESET_ALL}" if HAS_COLOR else text

    @staticmethod
    def dim(text: str) -> str:
        """Return dimmed text."""
        return f"{Style.DIM}{text}{Style.RESET_ALL}" if HAS_COLOR else text


# =============================================================================
# UI Utilities
# =============================================================================

def clear_screen():
    """Clear the terminal screen."""
    os.system('clear' if os.name != 'nt' else 'cls')


def print_banner():
    """Print the CCMF demo banner."""
    banner = """
╔═══════════════════════════════════════════════════════════════════════╗
║                                                                       ║
║              CONSTITUTIONAL COGNITIVE META-FRAMEWORK                  ║
║                     Interactive Demonstration                         ║
║                                                                       ║
║                         CCMF Demo v1.0                                ║
║                                                                       ║
╚═══════════════════════════════════════════════════════════════════════╝
"""
    print(Colors.header(banner))


def print_separator(char="=", length=70):
    """Print a separator line."""
    print(Colors.dim(char * length))


def print_section_header(title: str):
    """Print a section header."""
    print("\n" + "=" * 70)
    print(Colors.header(f" {title}".center(70)))
    print("=" * 70)


def print_subsection_header(title: str):
    """Print a subsection header."""
    print("\n" + Colors.info(f"── {title} "))
    print(Colors.dim("─" * 70))


def print_metric(label: str, value: Any, unit: str = ""):
    """Print a metric with label and value."""
    print(f"  {Colors.info('•')} {label}: {Colors.highlight(str(value))}{unit}")


def print_status(success: bool, message: str):
    """Print a status message."""
    if success:
        print(f"  {Colors.success('✓')} {message}")
    else:
        print(f"  {Colors.error('✗')} {message}")


def wait_for_enter(prompt: str = "\nPress Enter to continue..."):
    """Wait for user to press Enter."""
    input(Colors.dim(prompt))


def get_user_choice(prompt: str, valid_choices: List[str]) -> str:
    """Get user input with validation."""
    while True:
        choice = input(Colors.highlight(prompt)).strip().lower()
        if choice in valid_choices:
            return choice
        print(Colors.error(f"Invalid choice. Please enter one of: {', '.join(valid_choices)}"))


# =============================================================================
# Demo Modules
# =============================================================================

class CCMFDemo:
    """Main demo class."""

    def __init__(self):
        """Initialize the demo."""
        self.running = True
        self.metrics = {
            'demos_run': 0,
            'patterns_tested': 0,
            'workflows_executed': 0
        }

    def run(self):
        """Run the main demo loop."""
        clear_screen()
        print_banner()
        print(Colors.info("\nWelcome to the CCMF Interactive Demonstration!"))
        print(Colors.dim("This demo showcases the power and versatility of the"))
        print(Colors.dim("Constitutional Cognitive Meta-Framework.\n"))
        wait_for_enter()

        while self.running:
            self.show_main_menu()

    def show_main_menu(self):
        """Show the main menu."""
        clear_screen()
        print_banner()

        print(Colors.header("\n📋 MAIN MENU\n"))

        menu_items = [
            ("1", "Cognitive Patterns Demonstration"),
            ("2", "Constitutional Compliance Validation"),
            ("3", "RSI Feedback Loop Demo"),
            ("4", "Meta-Learning Architecture Demo"),
            ("5", "Integrated Workflow Demo"),
            ("6", "Performance Metrics Dashboard"),
            ("7", "About CCMF"),
            ("0", "Exit")
        ]

        for key, label in menu_items:
            if key == "0":
                print()
            print(f"  {Colors.highlight(key)}. {label}")

        print()
        print_separator("-")
        print(Colors.dim(f"\nDemos run: {self.metrics['demos_run']} | " +
                         f"Patterns tested: {self.metrics['patterns_tested']} | " +
                         f"Workflows: {self.metrics['workflows_executed']}"))

        choice = get_user_choice("\n➤ Select an option: ",
                                [str(i) for i in range(8)])

        if choice == "1":
            self.demo_patterns()
        elif choice == "2":
            self.demo_constitutional()
        elif choice == "3":
            self.demo_rsi_loop()
        elif choice == "4":
            self.demo_meta_learning()
        elif choice == "5":
            self.demo_integrated_workflow()
        elif choice == "6":
            self.show_metrics_dashboard()
        elif choice == "7":
            self.show_about()
        elif choice == "0":
            self.exit_demo()

    def demo_patterns(self):
        """Demonstrate cognitive patterns."""
        clear_screen()
        print_section_header("COGNITIVE PATTERNS DEMONSTRATION")

        patterns_menu = [
            ("1", "DirectPathAccessPattern"),
            ("2", "KnownPathSearchPattern"),
            ("3", "GitRepositoryFilePattern"),
            ("4", "CheckpointRecoveryPattern"),
            ("5", "GitStateAnalysisPattern"),
            ("6", "CompositeStateRecoveryPattern"),
            ("0", "Back to Main Menu")
        ]

        print()
        for key, label in patterns_menu:
            if key == "0":
                print()
            print(f"  {Colors.highlight(key)}. {label}")

        choice = get_user_choice("\n➤ Select a pattern to demo: ",
                                [str(i) for i in range(7)])

        if choice == "1":
            self._demo_direct_path_access()
        elif choice == "2":
            self._demo_known_path_search()
        elif choice == "3":
            self._demo_git_repository()
        elif choice == "4":
            self._demo_checkpoint_recovery()
        elif choice == "5":
            self._demo_git_state_analysis()
        elif choice == "6":
            self._demo_composite_recovery()
        elif choice == "0":
            return

        self.metrics['demos_run'] += 1
        self.metrics['patterns_tested'] += 1
        wait_for_enter()

    def _demo_direct_path_access(self):
        """Demo DirectPathAccessPattern."""
        print_subsection_header("DirectPathAccessPattern Demo")

        pattern = DirectPathAccessPattern()
        test_file = __file__

        print(Colors.info(f"\n➤ Testing file: {test_file}\n"))

        # Check existence
        print(Colors.dim("⏳ Checking file existence..."))
        result = pattern.execute(path=test_file, operation="exists")
        print_status(result.success, f"File exists: {result.data}")
        print_metric("Execution time", f"{result.execution_time:.4f}", "s")

        # Get stats
        print(Colors.dim("\n⏳ Getting file statistics..."))
        result = pattern.execute(path=test_file, operation="stat")
        if result.success:
            print_status(True, "Statistics retrieved")
            print_metric("Size", f"{result.data['size']:,}", " bytes")
            print_metric("Modified", result.data['modified'])
            print_metric("Execution time", f"{result.execution_time:.4f}", "s")

        # Pattern stats
        stats = pattern.get_stats()
        print(Colors.dim("\n📊 Pattern Statistics:"))
        print_metric("Total executions", stats['executions'])
        print_metric("Success rate", f"{stats['success_rate']:.1f}", "%")

    def _demo_known_path_search(self):
        """Demo KnownPathSearchPattern."""
        print_subsection_header("KnownPathSearchPattern Demo")

        pattern = KnownPathSearchPattern()

        print(Colors.info("\n➤ Searching for Python files in current directory\n"))
        print(Colors.dim("⏳ Executing search..."))

        result = pattern.execute(
            search_paths=["."],
            pattern="*.py",
            recursive=False
        )

        if result.success:
            print_status(True, f"Found {len(result.data)} files")
            print_metric("Execution time", f"{result.execution_time:.4f}", "s")

            if result.data:
                print(Colors.dim("\n📁 Files found:"))
                for i, file_path in enumerate(result.data[:10], 1):
                    print(f"    {i}. {Path(file_path).name}")
                if len(result.data) > 10:
                    print(Colors.dim(f"    ... and {len(result.data) - 10} more"))

    def _demo_git_repository(self):
        """Demo GitRepositoryFilePattern."""
        print_subsection_header("GitRepositoryFilePattern Demo")

        pattern = GitRepositoryFilePattern()

        # Find git repo
        repo_path = Path.cwd()
        while repo_path != repo_path.parent:
            if (repo_path / ".git").exists():
                break
            repo_path = repo_path.parent

        if not (repo_path / ".git").exists():
            print_status(False, "Not in a Git repository")
            return

        print(Colors.info(f"\n➤ Repository: {repo_path}\n"))

        # Get status
        print(Colors.dim("⏳ Getting repository status..."))
        result = pattern.execute(repo_path=str(repo_path), operation="status")
        if result.success:
            print_status(True, "Status retrieved")
            print_metric("Has changes", result.data['has_changes'])
            print_metric("Execution time", f"{result.execution_time:.4f}", "s")

        # Get log
        print(Colors.dim("\n⏳ Getting recent commits..."))
        result = pattern.execute(repo_path=str(repo_path), operation="log", limit=5)
        if result.success:
            print_status(True, f"Retrieved {len(result.data['commits'])} commits")
            print(Colors.dim("\n📝 Recent commits:"))
            for commit in result.data['commits']:
                print(f"    {commit}")

    def _demo_checkpoint_recovery(self):
        """Demo CheckpointRecoveryPattern."""
        print_subsection_header("CheckpointRecoveryPattern Demo")

        pattern = CheckpointRecoveryPattern(checkpoint_dir=".ccmf_demo_checkpoints")

        # Save checkpoint
        print(Colors.info("\n➤ Saving checkpoint\n"))
        test_data = {
            'demo_state': 'active',
            'timestamp': datetime.now().isoformat(),
            'data': {'value': 42, 'status': 'testing'}
        }

        print(Colors.dim("⏳ Creating checkpoint..."))
        result = pattern.execute(
            operation="save",
            checkpoint_id="demo_checkpoint",
            state_data=test_data
        )

        if result.success:
            print_status(True, "Checkpoint saved")
            print_metric("Checkpoint ID", result.data['checkpoint_id'])
            print_metric("Execution time", f"{result.execution_time:.4f}", "s")

        # List checkpoints
        print(Colors.dim("\n⏳ Listing checkpoints..."))
        result = pattern.execute(operation="list")
        if result.success:
            print_status(True, f"Found {result.data['count']} checkpoint(s)")

        # Load checkpoint
        print(Colors.dim("\n⏳ Loading checkpoint..."))
        result = pattern.execute(operation="load", checkpoint_id="demo_checkpoint")
        if result.success:
            print_status(True, "Checkpoint loaded")
            print_metric("State data", str(result.data['state_data'])[:50] + "...")

        # Cleanup
        pattern.execute(operation="delete", checkpoint_id="demo_checkpoint")

    def _demo_git_state_analysis(self):
        """Demo GitStateAnalysisPattern."""
        print_subsection_header("GitStateAnalysisPattern Demo")

        pattern = GitStateAnalysisPattern()

        # Find git repo
        repo_path = Path.cwd()
        while repo_path != repo_path.parent:
            if (repo_path / ".git").exists():
                break
            repo_path = repo_path.parent

        if not (repo_path / ".git").exists():
            print_status(False, "Not in a Git repository")
            return

        print(Colors.info(f"\n➤ Analyzing repository: {repo_path}\n"))
        print(Colors.dim("⏳ Running comprehensive analysis..."))

        result = pattern.execute(repo_path=str(repo_path))

        if result.success:
            print_status(True, "Analysis complete")
            print_metric("Execution time", f"{result.execution_time:.4f}", "s")

            data = result.data
            print(Colors.dim("\n📊 Repository State:"))
            print_metric("Current branch", data['current_branch'])
            print_metric("Uncommitted changes", data['has_uncommitted_changes'])
            print_metric("Total commits", data['total_commits'])
            print_metric("Remotes", len(data['remotes']))

    def _demo_composite_recovery(self):
        """Demo CompositeStateRecoveryPattern."""
        print_subsection_header("CompositeStateRecoveryPattern Demo")

        pattern = CompositeStateRecoveryPattern(checkpoint_dir=".ccmf_demo_checkpoints")

        repo_path = Path.cwd()
        while repo_path != repo_path.parent:
            if (repo_path / ".git").exists():
                break
            repo_path = repo_path.parent

        print(Colors.info("\n➤ Multi-source state recovery\n"))
        print(Colors.dim("⏳ Attempting recovery from all sources..."))

        result = pattern.execute(
            repo_path=str(repo_path),
            recovery_sources=['checkpoint', 'git', 'filesystem']
        )

        if result.success:
            print_status(True, "Recovery complete")
            print_metric("Execution time", f"{result.execution_time:.4f}", "s")
            print_metric("Sources attempted", result.metadata['sources_attempted'])
            print_metric("Sources succeeded", result.metadata['sources_succeeded'])

            print(Colors.dim("\n📦 Recovery Sources:"))
            for source, data in result.data['sources'].items():
                status = Colors.success("✓") if data['success'] else Colors.error("✗")
                print(f"    {status} {source.upper()}")

    def demo_constitutional(self):
        """Demonstrate constitutional compliance."""
        clear_screen()
        print_section_header("CONSTITUTIONAL COMPLIANCE VALIDATION")

        framework = ConstitutionalFramework()

        # Demo different compliance scenarios
        scenarios = [
            {
                'name': 'Full Compliance',
                'context': {
                    'operation_type': 'data_read',
                    'risk_assessment': 'low',
                    'logging_enabled': True,
                    'audit_trail': True,
                    'resource_estimate': {'cpu': 'low', 'memory': 'low'},
                    'error_handling': True,
                    'recovery_strategy': 'retry_with_backoff',
                    'data_classification': 'public',
                    'privacy_check': True,
                    'ethical_review': True
                }
            },
            {
                'name': 'Partial Compliance',
                'context': {
                    'operation_type': 'data_modification',
                    'risk_assessment': 'medium',
                    'logging_enabled': True,
                    'audit_trail': True,
                    'error_handling': True,
                    'recovery_strategy': 'fail_fast',
                    'data_classification': 'internal'
                }
            },
            {
                'name': 'Non-Compliant',
                'context': {
                    'operation_type': 'system_modification'
                }
            }
        ]

        for scenario in scenarios:
            print_subsection_header(f"Scenario: {scenario['name']}")
            print(Colors.dim("\n⏳ Validating compliance..."))

            report = validate_operation(scenario['context'])

            # Display results
            if report.overall_compliance == ComplianceLevel.FULL:
                status_color = Colors.success
            elif report.overall_compliance == ComplianceLevel.PARTIAL:
                status_color = Colors.warning
            else:
                status_color = Colors.error

            print(f"\n  Compliance Level: {status_color(report.overall_compliance.value.upper())}")
            print_metric("Compliance Score", f"{report.compliance_score:.1%}")
            print_metric("Principles Passed", f"{report.principles_passed}/{report.principles_checked}")
            print_metric("Principles Failed", report.principles_failed)

            if report.violations:
                print(Colors.dim(f"\n  ⚠ Violations ({len(report.violations)}):"))
                for v in report.violations[:3]:
                    print(f"      • {v['principle_name']}")

            if report.recommendations:
                print(Colors.dim(f"\n  💡 Recommendations:"))
                for rec in report.recommendations[:2]:
                    print(f"      • {rec}")

            print()

        self.metrics['demos_run'] += 1
        wait_for_enter()

    def demo_rsi_loop(self):
        """Demonstrate RSI feedback loop."""
        clear_screen()
        print_section_header("RSI FEEDBACK LOOP DEMONSTRATION")

        rsi_loop = RSIFeedbackLoop()

        print(Colors.info("\n➤ Simulating operations and collecting feedback\n"))
        print(Colors.dim("⏳ Running 30 operations..."))

        import random

        operations = [
            ('file_read', 0.85),
            ('file_write', 0.80),
            ('search', 0.90),
            ('analysis', 0.75),
            ('transform', 0.70)
        ]

        progress_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        for i in range(30):
            print(f"\r  {progress_chars[i % len(progress_chars)]} Processing operation {i+1}/30...", end='', flush=True)

            op_name, success_prob = random.choice(operations)
            success = random.random() < success_prob

            rsi_loop.collect_feedback(
                feedback_type=FeedbackType.SUCCESS if success else FeedbackType.FAILURE,
                source=f"demo_{op_name}",
                metrics={
                    'execution_time': random.uniform(0.1, 1.0),
                    'quality': random.uniform(0.7, 1.0) if success else random.uniform(0.3, 0.6)
                },
                severity=0.3 if success else 0.7
            )
            time.sleep(0.05)

        print(f"\r  {Colors.success('✓')} Completed 30 operations{' ' * 30}")

        # Analyze performance
        print_subsection_header("Performance Analysis")
        analysis = rsi_loop.analyze_performance()

        print_metric("Health Score", f"{analysis['health_score']:.1%}")
        print_metric("Success Rate", f"{analysis['current_metrics']['success_rate']:.1%}")
        print_metric("Avg Execution Time", f"{analysis['current_metrics']['execution_time']:.4f}", "s")
        print_metric("Quality Score", f"{analysis['current_metrics']['quality_score']:.4f}")
        print_metric("Error Count", analysis['current_metrics']['error_count'])

        # Run improvement cycle
        print_subsection_header("Improvement Cycle")
        print(Colors.dim("⏳ Running improvement cycle..."))

        cycle_result = rsi_loop.run_improvement_cycle()

        print_status(True, "Cycle completed")
        print_metric("Current Health", f"{cycle_result['current_health']:.1%}")
        print_metric("Adapted", cycle_result['adapted'])

        if cycle_result['decision']:
            decision = cycle_result['decision']
            print(Colors.dim("\n  📋 Adaptation Decision:"))
            print(f"      Strategy: {Colors.highlight(decision['strategy'])}")
            print(f"      Confidence: {decision['confidence']:.1%}")
            print(f"      Expected improvement: {decision['expected_improvement']:.1%}")

        self.metrics['demos_run'] += 1
        wait_for_enter()

    def demo_meta_learning(self):
        """Demonstrate meta-learning architecture."""
        clear_screen()
        print_section_header("META-LEARNING ARCHITECTURE DEMONSTRATION")

        mla = MetaLearningArchitecture()

        print(Colors.info("\n➤ Recording learning examples\n"))
        print(Colors.dim("⏳ Simulating 60 learning examples..."))

        import random

        patterns = ['DirectPathAccessPattern', 'KnownPathSearchPattern', 'GitRepositoryFilePattern']
        contexts = [
            {'operation': 'read', 'size': 'small'},
            {'operation': 'read', 'size': 'large'},
            {'operation': 'search', 'scope': 'local'},
            {'operation': 'git_status', 'repo': 'local'}
        ]

        progress_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        for i in range(60):
            print(f"\r  {progress_chars[i % len(progress_chars)]} Recording example {i+1}/60...", end='', flush=True)

            pattern = random.choice(patterns)
            context = random.choice(contexts)
            success = random.random() > 0.25

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
            time.sleep(0.03)

        print(f"\r  {Colors.success('✓')} Recorded 60 examples{' ' * 30}")

        # Calculate leverage quotient
        print_subsection_header("MLA Leverage Quotient")
        print(Colors.dim("⏳ Calculating quotient..."))

        quotient = mla.calculate_leverage_quotient()

        print()
        print(Colors.highlight("╔══════════════════════════════════════════════════════════════╗"))
        print(Colors.highlight("║         META-LEARNING ARCHITECTURE LEVERAGE QUOTIENT         ║"))
        print(Colors.highlight("╚══════════════════════════════════════════════════════════════╝"))
        print()

        # Overall quotient with visual bar
        bar_length = 40
        filled = int(quotient.overall_quotient * bar_length)
        bar = "█" * filled + "░" * (bar_length - filled)
        print(f"  Overall Quotient: {Colors.highlight(f'{quotient.overall_quotient:.4f}')}")
        print(f"  {bar} {Colors.success(quotient.get_grade())}")

        print()
        print(Colors.dim("  📊 Detailed Metrics:"))
        print_metric("Total Examples", quotient.total_examples)
        print_metric("Successful Examples", quotient.successful_examples)
        print_metric("Patterns Learned", quotient.patterns_learned)
        print_metric("Avg Performance Gain", f"{quotient.average_performance_gain:+.4f}")
        print_metric("Transfer Learning", f"{quotient.transfer_learning_effectiveness:.4f}")
        print_metric("Knowledge Reuse Rate", f"{quotient.knowledge_reuse_rate:.4f}")

        # Learning insights
        print_subsection_header("Learning Insights")
        insights = mla.get_learning_insights()

        print(Colors.dim("\n  🏆 Top Performing Patterns:"))
        for pattern_info in insights['top_performing_patterns'][:3]:
            print(f"      {Colors.success('•')} {pattern_info['name']}: " +
                  f"{pattern_info['success_rate']:.1%} ({pattern_info['usage_count']} uses)")

        self.metrics['demos_run'] += 1
        wait_for_enter()

    def demo_integrated_workflow(self):
        """Demonstrate integrated workflow."""
        clear_screen()
        print_section_header("INTEGRATED WORKFLOW DEMONSTRATION")

        print(Colors.info("\n➤ Building comprehensive workflow\n"))
        print(Colors.dim("⏳ Creating workflow with multiple patterns..."))

        # Build workflow
        builder = WorkflowBuilder(
            workflow_id="ccmf_demo_workflow",
            name="CCMF Demo Workflow",
            description="Integrated demonstration workflow"
        ).with_rsi(True)

        builder.add_pattern_step(
            step_id="step1",
            name="Verify File",
            pattern=DirectPathAccessPattern(),
            parameters={'path': __file__, 'operation': 'exists'},
            description="Check if demo file exists"
        )

        builder.add_pattern_step(
            step_id="step2",
            name="Search Modules",
            pattern=KnownPathSearchPattern(),
            parameters={
                'search_paths': ['.'],
                'pattern': 'ccmf_*.py',
                'recursive': False
            },
            description="Find CCMF modules",
            depends_on=['step1']
        )

        workflow = builder.build()

        print(Colors.success("✓ Workflow created"))
        print_metric("Total steps", len(workflow.steps))
        print_metric("RSI enabled", workflow.enable_rsi)

        # Execute workflow
        print_subsection_header("Workflow Execution")
        print(Colors.dim("⏳ Executing workflow...\n"))

        result = workflow.execute()

        # Display results
        if result['status'] == 'completed':
            print(Colors.success("\n  ✓ Workflow completed successfully!"))
        else:
            print(Colors.error(f"\n  ✗ Workflow {result['status']}"))

        print_metric("Total execution time", f"{result['total_execution_time']:.4f}", "s")

        print(Colors.dim("\n  📊 Steps Summary:"))
        print_metric("Completed", result['steps']['completed'])
        print_metric("Failed", result['steps']['failed'])
        print_metric("Skipped", result['steps']['skipped'])

        print(Colors.dim("\n  📝 Execution Steps:"))
        for step in result['step_details']:
            if step['status'] == 'completed':
                status = Colors.success("✓")
            elif step['status'] == 'failed':
                status = Colors.error("✗")
            else:
                status = Colors.dim("○")

            print(f"      {status} {step['name']} ({step['execution_time']:.4f}s)")

        self.metrics['demos_run'] += 1
        self.metrics['workflows_executed'] += 1
        wait_for_enter()

    def show_metrics_dashboard(self):
        """Show performance metrics dashboard."""
        clear_screen()
        print_section_header("PERFORMANCE METRICS DASHBOARD")

        print(Colors.dim("\n📊 Session Statistics:\n"))

        print_metric("Total demos run", self.metrics['demos_run'])
        print_metric("Patterns tested", self.metrics['patterns_tested'])
        print_metric("Workflows executed", self.metrics['workflows_executed'])

        print(Colors.dim("\n\n💡 Framework Status:\n"))
        print_metric("CCMF Version", "1.0.0")
        print_metric("Session start", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print_metric("Color support", "Yes" if HAS_COLOR else "No (fallback)")

        wait_for_enter()

    def show_about(self):
        """Show about information."""
        clear_screen()
        print_section_header("ABOUT CCMF")

        about_text = """
The Constitutional Cognitive Meta-Framework (CCMF) is a comprehensive
framework for building AI systems with:

  • Constitutional Principles: Ethical guidelines and safety constraints
  • Cognitive Patterns: Reusable patterns for common operations
  • RSI Feedback Loop: Recursive self-improvement mechanisms
  • Meta-Learning: Learning from past experiences
  • Workflow Orchestration: Complex multi-step operation management

Key Features:
  ✓ Production-ready patterns for file access, search, and Git operations
  ✓ Constitutional compliance validation for all operations
  ✓ Self-improving feedback loops with adaptation strategies
  ✓ Meta-learning architecture with leverage quotient calculations
  ✓ Comprehensive workflow engine with dependency management
  ✓ Error handling, recovery, and checkpointing
  ✓ Performance monitoring and metrics

Version: 1.0.0
Session: 2 (Examples and Demo)
        """

        print(Colors.info(about_text))
        wait_for_enter()

    def exit_demo(self):
        """Exit the demo."""
        clear_screen()
        print_banner()

        print(Colors.success("\n✨ Thank you for exploring the CCMF framework!\n"))
        print(Colors.dim("Session Summary:"))
        print_metric("Demos run", self.metrics['demos_run'])
        print_metric("Patterns tested", self.metrics['patterns_tested'])
        print_metric("Workflows executed", self.metrics['workflows_executed'])

        print(Colors.dim("\n\nFor more information, see the documentation and examples.\n"))

        self.running = False


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    """Main entry point for the demo."""
    try:
        demo = CCMFDemo()
        demo.run()
    except KeyboardInterrupt:
        print(Colors.warning("\n\n⚠ Demo interrupted by user"))
    except Exception as e:
        print(Colors.error(f"\n\n✗ Error: {e}"))
        import traceback
        traceback.print_exc()
    finally:
        print()


if __name__ == "__main__":
    main()
