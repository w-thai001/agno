"""
Claude Code Mastery Framework (CCMF) v1.0 - Interactive Demo

Interactive CLI demonstration showcasing framework capabilities.

This demo provides hands-on exploration of:
- Constitutional validation with real-time feedback
- Pattern execution with performance metrics
- RSI feedback loops
- Pattern optimization
- Performance comparisons

Run this module to explore CCMF features interactively.
"""

import sys
import time
from typing import Optional

from agno.ccmf_constitutional import ConstitutionalValidator
from agno.ccmf_patterns import (
    DirectPathAccessPattern,
    KnownPathSearchPattern,
    GitRepositoryFilePattern
)
from agno.ccmf_workflows import (
    GitStateAnalysisPattern,
    CompositeStateRecoveryPattern
)
from agno.ccmf_rsi_loop import (
    ExecutionAnalyzer,
    PatternOptimizer,
    RSIFeedbackLoop
)


def print_banner():
    """Print CCMF demo banner."""
    print("\n" + "=" * 80)
    print("  ███████╗███████╗███╗   ███╗███████╗    ██╗   ██╗ ██╗    ██████╗ ")
    print("  ██╔════╝██╔════╝████╗ ████║██╔════╝    ██║   ██║███║   ██╔═████╗")
    print("  ██║     ██║     ██╔████╔██║█████╗      ██║   ██║╚██║   ██║██╔██║")
    print("  ██║     ██║     ██║╚██╔╝██║██╔══╝      ╚██╗ ██╔╝ ██║   ████╔╝██║")
    print("  ╚██████╗███████╗██║ ╚═╝ ██║██║          ╚████╔╝  ██║██╗╚██████╔╝")
    print("   ╚═════╝╚══════╝╚═╝     ╚═╝╚═╝           ╚═══╝   ╚═╝╚═╝ ╚═════╝ ")
    print()
    print("  Claude Code Mastery Framework - Interactive Demo")
    print("  Meta-level RSI Framework FOR Fellou Agents BY Fellou Agents")
    print("=" * 80 + "\n")


def print_separator(char: str = "-", length: int = 80):
    """Print separator line."""
    print(char * length)


def get_input(prompt: str, default: Optional[str] = None) -> str:
    """
    Get user input with optional default value.

    Args:
        prompt: Input prompt
        default: Default value if user presses Enter

    Returns:
        User input or default
    """
    if default:
        prompt = f"{prompt} [{default}]: "
    else:
        prompt = f"{prompt}: "

    user_input = input(prompt).strip()
    return user_input if user_input else (default or "")


def pause(message: str = "\nPress Enter to continue..."):
    """Pause execution until user presses Enter."""
    input(message)


def demo_menu() -> str:
    """
    Display demo menu and get user choice.

    Returns:
        User's menu selection
    """
    print("\n" + "=" * 80)
    print("CCMF Demo Menu")
    print("=" * 80)
    print("\nPattern Demonstrations:")
    print("  1. Constitutional Validation Demo")
    print("  2. Direct Path Access Pattern")
    print("  3. Known Path Search Pattern")
    print("  4. Git Repository Pattern")
    print("  5. Git State Analysis Pattern")
    print("  6. Composite State Recovery")
    print("\nRSI & Optimization:")
    print("  7. RSI Feedback Loop Demo")
    print("  8. Pattern Optimization Demo")
    print("  9. Performance Comparison")
    print("\nUtilities:")
    print("  A. Run All Demos")
    print("  H. Help & Information")
    print("  0. Exit")
    print_separator()

    return get_input("\nSelect demo (0-9, A, H)").upper()


def demo_constitutional():
    """Demonstrate constitutional validation."""
    print("\n" + "=" * 80)
    print("DEMO: Constitutional Validation")
    print("=" * 80)

    validator = ConstitutionalValidator()

    # Test forbidden methods
    print("\n--- Testing Forbidden Method Detection ---")
    print("Testing methods that should be BLOCKED:")
    print_separator("-", 40)

    forbidden = ['read_list', 'file_list', 'file_find_by_name']
    for method in forbidden:
        is_valid, violation = validator.validate_file_operation(
            operation='test',
            file_path='/test/path',
            method=method
        )
        status = "✗ BLOCKED" if not is_valid else "✓ ALLOWED (ERROR!)"
        print(f"  {status}: {method}")

    # Test allowed methods
    print("\n--- Testing Allowed Method Validation ---")
    print("Testing methods that should be ALLOWED:")
    print_separator("-", 40)

    allowed = ['powershell_subprocess', 'git_command']
    for method in allowed:
        is_valid, violation = validator.validate_file_operation(
            operation='test',
            file_path='/test/path',
            method=method
        )
        status = "✓ ALLOWED" if is_valid else "✗ BLOCKED (ERROR!)"
        print(f"  {status}: {method}")

    # Calculate LQ
    print("\n--- Leverage Quotient (LQ) Calculation ---")
    print("Formula: LQ = I(a,G) / C(a)")
    print("where I(a,G) = w_p * P(a,G) + w_e * ΔE_f(a,G)")
    print_separator("-", 40)

    progress = 0.8
    efficiency = 0.9
    cost = 0.2

    lq = validator.calculate_leverage_quotient(
        progress_towards_goal=progress,
        energy_efficiency=efficiency,
        cost=cost
    )

    print(f"  Progress towards goal (P): {progress}")
    print(f"  Energy efficiency (E): {efficiency}")
    print(f"  Cost (C): {cost}")
    print(f"  Weights: progress=0.6, efficiency=0.4")
    print(f"\n  Impact (I) = 0.6 * {progress} + 0.4 * {efficiency} = {0.6 * progress + 0.4 * efficiency:.2f}")
    print(f"  LQ = {0.6 * progress + 0.4 * efficiency:.2f} / {cost} = {lq:.2f}")
    print(f"\n  ✓ Action returns {lq:.1f}x value for cost invested")

    # Violation report
    print("\n--- Violation Report ---")
    print_separator("-", 40)

    report = validator.generate_violation_report()
    lines = report.split('\n')

    # Print report summary
    for line in lines[:20]:
        print(line)

    print(f"\n  Total validations: {validator.validation_count}")
    print(f"  Total violations: {len(validator.violations)}")

    pause()


def demo_direct_path():
    """Demonstrate DirectPathAccessPattern."""
    print("\n" + "=" * 80)
    print("DEMO: Direct Path Access Pattern")
    print("=" * 80)

    validator = ConstitutionalValidator()
    pattern = DirectPathAccessPattern(validator)

    # Get file path from user
    default_path = "/home/user/agno/README.md"
    file_path = get_input("\nEnter file path to test", default_path)

    # Test existence
    print("\n--- Testing File Existence ---")
    print(f"File path: {file_path}")
    print("Operation: Test-Path (PowerShell subprocess)")
    print_separator("-", 40)

    start_time = time.time()
    success, result, error = pattern.execute_with_validation({
        'file_path': file_path,
        'operation': 'test'
    })
    duration = time.time() - start_time

    if success and result:
        exists = result.get("exists", False)
        print(f"  ✓ Execution successful")
        print(f"  File exists: {'Yes' if exists else 'No'}")
        print(f"  Duration: {duration:.3f}s")

        # Read content if exists
        if exists:
            print("\n--- Reading File Content ---")
            read_choice = get_input("Read file content? (y/n)", "y")

            if read_choice.lower() == 'y':
                print("Operation: Get-Content -Raw (PowerShell subprocess)")
                print_separator("-", 40)

                start_time = time.time()
                success, result, error = pattern.execute_with_validation({
                    'file_path': file_path,
                    'operation': 'read'
                })
                duration = time.time() - start_time

                if success and result:
                    content = result.get("content", "")
                    size_bytes = result.get("size_bytes", 0)

                    print(f"  ✓ Read successful")
                    print(f"  Size: {size_bytes} bytes")
                    print(f"  Duration: {duration:.3f}s")

                    # Show preview
                    preview_lines = content.split('\n')[:5]
                    print("\n  Content preview (first 5 lines):")
                    for line in preview_lines:
                        print(f"    {line[:76]}")
                    if len(content.split('\n')) > 5:
                        print("    ...")
    else:
        print(f"  ✗ Error: {error}")

    # Show performance metrics
    print("\n--- Pattern Performance ---")
    print_separator("-", 40)
    perf = pattern.get_performance_summary()
    print(f"  Total executions: {perf['total_executions']}")
    print(f"  Success rate: {perf['success_rate']:.1f}%")
    print(f"  Average LQ: {perf['average_lq']:.2f}")

    pause()


def demo_known_path_search():
    """Demonstrate KnownPathSearchPattern."""
    print("\n" + "=" * 80)
    print("DEMO: Known Path Search Pattern")
    print("=" * 80)

    validator = ConstitutionalValidator()
    pattern = KnownPathSearchPattern(validator)

    print("\n--- Configuring Search Paths ---")
    print("Enter paths to search (one per line, empty line to finish):")
    print_separator("-", 40)

    search_paths = []
    default_paths = [
        '/home/user/agno/config.json',
        '/home/user/agno/package.json',
        '/home/user/agno/README.md',
    ]

    use_defaults = get_input("Use default paths? (y/n)", "y")

    if use_defaults.lower() == 'y':
        search_paths = default_paths
        for path in search_paths:
            print(f"  + {path}")
    else:
        while True:
            path = input("  Path: ").strip()
            if not path:
                break
            search_paths.append(path)

    if not search_paths:
        print("  No paths specified. Using defaults.")
        search_paths = default_paths

    # Execute search
    print("\n--- Executing Search ---")
    print(f"Searching through {len(search_paths)} paths...")
    print_separator("-", 40)

    start_time = time.time()
    success, result, error = pattern.execute_with_validation({
        'search_paths': search_paths,
        'read_content': False
    })
    duration = time.time() - start_time

    if success and result:
        found = result.get("found", False)
        attempts = result.get("attempts", 0)
        path = result.get("path")

        print(f"  ✓ Search complete")
        print(f"  Attempts: {attempts}")
        print(f"  Found: {'Yes' if found else 'No'}")
        if found:
            print(f"  Path: {path}")
        print(f"  Duration: {duration:.3f}s")

        # Show search log
        if "search_log" in result:
            print("\n--- Search Log ---")
            print_separator("-", 40)
            for entry in result["search_log"]:
                attempt = entry.get("attempt")
                exists = entry.get("exists", False)
                entry_path = entry.get("path")
                status = "✓ FOUND" if exists else "✗ Not found"
                print(f"  Attempt {attempt}: {status}")
                print(f"    Path: {entry_path}")
    else:
        print(f"  ✗ Error: {error}")

    # Show performance metrics
    print("\n--- Pattern Performance ---")
    print_separator("-", 40)
    perf = pattern.get_performance_summary()
    print(f"  Average LQ: {perf['average_lq']:.2f}")
    print(f"  Note: LQ decreases with attempts (7.0 - 0.5 * attempts)")

    pause()


def demo_git_pattern():
    """Demonstrate GitRepositoryFilePattern."""
    print("\n" + "=" * 80)
    print("DEMO: Git Repository Pattern")
    print("=" * 80)

    validator = ConstitutionalValidator()
    pattern = GitRepositoryFilePattern(validator)

    # Get repo path
    default_repo = "/home/user/agno"
    repo_path = get_input("\nEnter repository path", default_repo)

    # List files
    print("\n--- Listing Files (git ls-files) ---")
    file_pattern = get_input("Enter file pattern (e.g., *.py)", "*.py")
    print(f"Command: git -C {repo_path} ls-files {file_pattern}")
    print_separator("-", 40)

    start_time = time.time()
    success, result, error = pattern.execute_with_validation({
        'repo_path': repo_path,
        'operation': 'list',
        'file_pattern': file_pattern
    })
    duration = time.time() - start_time

    if success and result:
        files = result.get("files", [])
        count = result.get("count", 0)

        print(f"  ✓ Found {count} files")
        print(f"  Duration: {duration:.3f}s")

        # Show first few files
        if files:
            print("\n  Sample files:")
            for file in files[:10]:
                print(f"    - {file}")
            if len(files) > 10:
                print(f"    ... and {len(files) - 10} more")

        # Offer to read a file
        if files and len(files) > 0:
            print("\n--- Reading File (git show HEAD:file) ---")
            read_choice = get_input("Read first file? (y/n)", "n")

            if read_choice.lower() == 'y':
                file_to_read = files[0]
                print(f"Reading: {file_to_read}")
                print_separator("-", 40)

                start_time = time.time()
                success, result, error = pattern.execute_with_validation({
                    'repo_path': repo_path,
                    'operation': 'read',
                    'file_pattern': file_to_read
                })
                duration = time.time() - start_time

                if success and result:
                    content = result.get("content", "")
                    size = result.get("size_bytes", 0)

                    print(f"  ✓ Read successful")
                    print(f"  Size: {size} bytes")
                    print(f"  Duration: {duration:.3f}s")

                    # Show preview
                    lines = content.split('\n')[:10]
                    print("\n  Content preview:")
                    for line in lines:
                        print(f"    {line[:76]}")
    else:
        print(f"  ✗ Error: {error}")

    # Show performance metrics
    print("\n--- Pattern Performance ---")
    print_separator("-", 40)
    perf = pattern.get_performance_summary()
    print(f"  Total executions: {perf['total_executions']}")
    print(f"  Success rate: {perf['success_rate']:.1f}%")
    print(f"  Average LQ: {perf['average_lq']:.2f} (Git patterns have high LQ ~9.0)")

    pause()


def demo_git_state():
    """Demonstrate GitStateAnalysisPattern."""
    print("\n" + "=" * 80)
    print("DEMO: Git State Analysis Pattern")
    print("=" * 80)

    validator = ConstitutionalValidator()
    pattern = GitStateAnalysisPattern(validator)

    # Get repo path
    default_repo = "/home/user/agno"
    repo_path = get_input("\nEnter repository path", default_repo)

    print("\n--- Analyzing Repository State ---")
    print("Running git commands:")
    print("  - git branch --show-current")
    print("  - git status --porcelain")
    print("  - git log --oneline")
    print("  - git diff --stat")
    print_separator("-", 40)

    start_time = time.time()
    success, result, error = pattern.execute_with_validation({
        'repo_path': repo_path,
        'analysis_depth': 10
    })
    duration = time.time() - start_time

    if success and result:
        print(f"  ✓ Analysis complete ({duration:.3f}s)")

        print("\n--- Repository Information ---")
        print(f"  Branch: {result.get('current_branch')}")
        print(f"  Clean: {'Yes' if result.get('is_clean') else 'No'}")
        print(f"  Uncommitted files: {len(result.get('uncommitted_files', []))}")

        # Show uncommitted files
        uncommitted = result.get('uncommitted_files', [])
        if uncommitted:
            print("\n  Uncommitted files:")
            for file in uncommitted[:5]:
                print(f"    - {file}")
            if len(uncommitted) > 5:
                print(f"    ... and {len(uncommitted) - 5} more")

        # Show recent commits
        commits = result.get('recent_commits', [])
        if commits:
            print(f"\n  Recent commits ({len(commits)}):")
            for i, commit in enumerate(commits[:5], 1):
                print(f"    {i}. {commit[:70]}")

        # Show diff summary
        diff = result.get('diff_summary', '')
        if diff:
            print("\n  Diff summary:")
            for line in diff.split('\n')[:10]:
                if line.strip():
                    print(f"    {line}")
    else:
        print(f"  ✗ Error: {error}")

    # Show performance
    print("\n--- Pattern Performance ---")
    print_separator("-", 40)
    perf = pattern.get_performance_summary()
    print(f"  Average LQ: {perf['average_lq']:.2f}")

    pause()


def demo_composite_recovery():
    """Demonstrate CompositeStateRecoveryPattern."""
    print("\n" + "=" * 80)
    print("DEMO: Composite State Recovery")
    print("=" * 80)

    validator = ConstitutionalValidator()
    pattern = CompositeStateRecoveryPattern(validator)

    print("\n--- Multi-Source Recovery ---")
    print("This pattern tries recovery in priority order:")
    print("  1. Checkpoint files (highest priority)")
    print("  2. Git repository analysis")
    print("  3. Fallback paths (lowest priority)")
    print_separator("-", 40)

    # Use defaults
    checkpoint_paths = [
        '/tmp/checkpoint_20240101_120000.json',
    ]
    repo_path = get_input("\nEnter repository path", "/home/user/agno")
    fallback_paths = [
        f'{repo_path}/README.md',
    ]

    print("\nRecovery sources:")
    print(f"  Checkpoints: {len(checkpoint_paths)} paths")
    print(f"  Git repo: {repo_path}")
    print(f"  Fallbacks: {len(fallback_paths)} paths")

    print("\n--- Executing Recovery ---")
    print_separator("-", 40)

    start_time = time.time()
    success, result, error = pattern.execute_with_validation({
        'checkpoint_paths': checkpoint_paths,
        'repo_path': repo_path,
        'fallback_paths': fallback_paths
    })
    duration = time.time() - start_time

    if success and result:
        sources = result.get('recovery_sources_used', [])
        confidence = result.get('confidence_score', 0)

        print(f"  ✓ Recovery complete ({duration:.3f}s)")
        print(f"\n  Sources used: {', '.join(sources) if sources else 'None'}")
        print(f"  Confidence: {confidence:.2%}")

        # Show source priority
        print("\n  Source priority and confidence:")
        if 'checkpoint' in sources:
            print("    ✓ Checkpoint: 0.90+ confidence")
        if 'git' in sources:
            print("    ✓ Git: 0.70 confidence")
        if 'fallback' in sources:
            print("    ✓ Fallback: 0.40 confidence")

        # Show merged state
        if 'merged_state' in result:
            merged = result['merged_state']
            print(f"\n  Merged state keys: {list(merged.keys())[:5]}")
    else:
        print(f"  ✗ Error: {error}")

    # Show performance
    print("\n--- Pattern Performance ---")
    print_separator("-", 40)
    perf = pattern.get_performance_summary()
    print(f"  Average LQ: {perf['average_lq']:.2f}")
    print(f"  Note: LQ varies 4.0-9.5 based on sources")

    pause()


def demo_rsi_loop():
    """Demonstrate RSI feedback loop."""
    print("\n" + "=" * 80)
    print("DEMO: RSI Feedback Loop")
    print("=" * 80)

    validator = ConstitutionalValidator()

    print("\n--- Creating Patterns ---")
    print_separator("-", 40)

    # Create patterns
    git_pattern = GitRepositoryFilePattern(validator)
    print(f"  Created: {git_pattern.pattern_name}")

    # Execute operations
    print("\n--- Generating Performance Data ---")
    print("Executing pattern operations...")
    print_separator("-", 40)

    for i in range(5):
        success, result, error = git_pattern.execute_with_validation({
            'repo_path': '/home/user/agno',
            'operation': 'list',
            'file_pattern': '*.py' if i % 2 == 0 else '*.md'
        })
        if success:
            print(f"  Execution {i+1}: ✓ Success (LQ={result.get('lq_score', 0):.2f})")

    # Set up RSI loop
    print("\n--- Setting Up RSI Loop ---")
    print_separator("-", 40)

    rsi_loop = RSIFeedbackLoop()
    rsi_loop.register_pattern(git_pattern)

    print(f"  Registered {len(rsi_loop.patterns)} pattern(s)")

    # Run improvement cycle
    print("\n--- Running Improvement Cycle ---")
    print_separator("-", 40)

    cycle_result = rsi_loop.run_improvement_cycle()

    print(f"  Cycle #{cycle_result['cycle_number']} complete")
    print(f"  Patterns analyzed: {cycle_result['patterns_analyzed']}")
    print(f"  Optimizations suggested: {cycle_result['total_optimizations_suggested']}")

    # Show optimizations
    if git_pattern.pattern_id in cycle_result["optimizations_by_pattern"]:
        opts = cycle_result["optimizations_by_pattern"][git_pattern.pattern_id]

        print(f"\n--- Optimizations for {git_pattern.pattern_name} ---")
        print_separator("-", 40)

        for i, opt in enumerate(opts[:3], 1):
            print(f"\n  {i}. {opt['optimization_type'].upper()}")
            print(f"     Priority: {opt['priority']}/10")
            print(f"     Complexity: {opt['implementation_complexity']}")
            print(f"     Expected LQ gain: +{opt['expected_lq_improvement']:.2f}")
            print(f"     Description: {opt['description']}")

    # Show overall summary
    print("\n--- RSI Loop Summary ---")
    print_separator("-", 40)

    summary = rsi_loop.get_summary()
    print(f"  Cycles run: {summary['cycles_run']}")
    print(f"  Total optimizations: {summary['total_optimizations']}")
    print(f"  Overall success rate: {summary['overall_success_rate']:.1f}%")
    print(f"  Average LQ: {summary['average_lq']:.2f}")

    pause()


def demo_optimization():
    """Demonstrate pattern optimization."""
    print("\n" + "=" * 80)
    print("DEMO: Pattern Optimization")
    print("=" * 80)

    validator = ConstitutionalValidator()
    analyzer = ExecutionAnalyzer()
    optimizer = PatternOptimizer(analyzer)

    # Create and execute pattern
    print("\n--- Creating and Executing Pattern ---")
    print_separator("-", 40)

    pattern = GitRepositoryFilePattern(validator)

    # Execute multiple times
    for i in range(10):
        pattern.execute_with_validation({
            'repo_path': '/home/user/agno',
            'operation': 'list',
            'file_pattern': '*.py'
        })

    print(f"  Executed pattern {pattern.total_executions} times")

    # Analyze performance
    print("\n--- Performance Analysis ---")
    print_separator("-", 40)

    analysis = analyzer.analyze_pattern_performance(pattern)

    print(f"  Success rate: {analysis['success_rate']:.1f}%")
    print(f"  Average LQ: {analysis['avg_lq']:.2f}")
    print(f"  Average duration: {analysis['avg_duration']:.3f}s")
    print(f"  LQ trend: {analysis['lq_trend']}")
    print(f"  Duration trend: {analysis['duration_trend']}")

    # Get optimization suggestions
    print("\n--- Optimization Suggestions ---")
    print_separator("-", 40)

    optimizations = optimizer.suggest_optimizations(pattern, analysis)

    for i, opt in enumerate(optimizations, 1):
        print(f"\n  {i}. {opt['optimization_type'].upper()}")
        print(f"     Priority: {opt['priority']}/10")
        print(f"     Expected improvement: +{opt['expected_lq_improvement']:.2f} LQ")
        print(f"     {opt['description']}")

    # Calculate improvement opportunity
    print("\n--- Improvement Opportunity ---")
    print_separator("-", 40)

    opportunity = analyzer.calculate_improvement_opportunities(pattern)
    print(f"  Potential LQ gain: {opportunity:.2f}")
    print(f"  Current avg LQ: {analysis['avg_lq']:.2f}")
    print(f"  Theoretical max: {analysis['avg_lq'] + opportunity:.2f}")

    pause()


def demo_performance_comparison():
    """Compare performance of different patterns."""
    print("\n" + "=" * 80)
    print("DEMO: Performance Comparison")
    print("=" * 80)

    validator = ConstitutionalValidator()

    print("\n--- Executing Patterns ---")
    print_separator("-", 40)

    # Create patterns
    patterns = [
        DirectPathAccessPattern(validator),
        GitRepositoryFilePattern(validator),
    ]

    # Execute each
    for pattern in patterns:
        print(f"\n  Testing: {pattern.pattern_name}")

        if isinstance(pattern, DirectPathAccessPattern):
            pattern.execute_with_validation({
                'file_path': '/home/user/agno/README.md',
                'operation': 'test'
            })
        elif isinstance(pattern, GitRepositoryFilePattern):
            pattern.execute_with_validation({
                'repo_path': '/home/user/agno',
                'operation': 'list',
                'file_pattern': '*.py'
            })

        perf = pattern.get_performance_summary()
        print(f"    LQ Score: {perf['average_lq']:.2f}")
        print(f"    Success Rate: {perf['success_rate']:.1f}%")

    # Compare
    print("\n--- Performance Comparison ---")
    print_separator("-", 40)

    pattern_data = []
    for pattern in patterns:
        perf = pattern.get_performance_summary()
        pattern_data.append({
            'name': pattern.pattern_name,
            'lq': perf['average_lq'],
            'success': perf['success_rate']
        })

    # Sort by LQ
    pattern_data.sort(key=lambda p: p['lq'], reverse=True)

    print("\n  Rankings (by LQ):")
    for i, p in enumerate(pattern_data, 1):
        print(f"    {i}. {p['name']}")
        print(f"       LQ: {p['lq']:.2f} | Success: {p['success']:.1f}%")

    print("\n  Recommendations:")
    print("    - Git patterns: Best for repository operations (LQ ~9.0)")
    print("    - Direct path: Best for known file access (LQ ~8.0)")
    print("    - Known search: Use when path uncertain (LQ 7.0-2.0)")

    pause()


def show_help():
    """Show help information."""
    print("\n" + "=" * 80)
    print("CCMF Demo - Help & Information")
    print("=" * 80)

    print("\n--- About CCMF ---")
    print("The Claude Code Mastery Framework (CCMF) is a meta-level RSI")
    print("(Recursive Self-Improvement) framework designed FOR Fellou agents")
    print("BY Fellou agents.")

    print("\n--- Framework Components ---")
    print("  • Constitutional Layer: Enforces protocols and validates operations")
    print("  • Pattern Library: File operation patterns with LQ scoring")
    print("  • Workflows: State recovery and composite patterns")
    print("  • RSI Loop: Performance analysis and optimization")

    print("\n--- Key Concepts ---")
    print("  • LQ (Leverage Quotient): Measures value/cost ratio of actions")
    print("  • Constitutional Compliance: All ops validated against protocols")
    print("  • RSI Tracking: Performance metrics for continuous improvement")
    print("  • PowerShell/Git Only: No forbidden file methods")

    print("\n--- Demo Navigation ---")
    print("  • Select numbered options from the menu")
    print("  • Press Enter to use default values")
    print("  • Press Ctrl+C to return to menu anytime")
    print("  • Option 'A' runs all demonstrations")

    pause()


def run_all_demos():
    """Run all demonstrations in sequence."""
    demos = [
        ("Constitutional Validation", demo_constitutional),
        ("Direct Path Access", demo_direct_path),
        ("Git Repository", demo_git_pattern),
        ("Git State Analysis", demo_git_state),
        ("RSI Feedback Loop", demo_rsi_loop),
    ]

    for name, func in demos:
        func()
        print("\n")


def main():
    """Main demo entry point."""
    print_banner()

    print("Welcome to the CCMF Interactive Demo!")
    print("\nThis demo showcases all framework capabilities with hands-on examples.")
    print("You can execute patterns, analyze performance, and explore RSI features.")

    pause()

    while True:
        try:
            choice = demo_menu()

            if choice == '0':
                print("\n" + "=" * 80)
                print("Thank you for exploring CCMF v1.0!")
                print("For more information, see documentation at:")
                print("  /home/user/agno/libs/agno/agno/ccmf_*.py")
                print("=" * 80 + "\n")
                break
            elif choice == '1':
                demo_constitutional()
            elif choice == '2':
                demo_direct_path()
            elif choice == '3':
                demo_known_path_search()
            elif choice == '4':
                demo_git_pattern()
            elif choice == '5':
                demo_git_state()
            elif choice == '6':
                demo_composite_recovery()
            elif choice == '7':
                demo_rsi_loop()
            elif choice == '8':
                demo_optimization()
            elif choice == '9':
                demo_performance_comparison()
            elif choice == 'A':
                run_all_demos()
            elif choice == 'H':
                show_help()
            else:
                print("\n✗ Invalid choice. Please select 0-9, A, or H.")
                pause()

        except KeyboardInterrupt:
            print("\n\nReturning to menu...")
            time.sleep(0.5)
        except Exception as e:
            print(f"\n✗ Error: {e}")
            pause()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted. Goodbye!")
        sys.exit(0)
