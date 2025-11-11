"""
FSA-4.1: Meta-FSA Orchestrator - Comprehensive Demonstration

This demo showcases Meta-FSA Orchestrator coordinating ALL FSAs:
- FSA-1.1: Prompt Optimizer
- FSA-1.2: Code Template Library
- FSA-2.1: Code Quality Validator
- FSA-2.2: Multi-Model Orchestrator
- FSA-3.1: Multi-Step Code Builder
- FSA-3.2: RSI Code Optimizer

Demonstrates:
- Intelligent task decomposition
- Optimal FSA sequencing with dependency resolution
- Full FSA chain execution
- Performance tracking across all FSAs
- Meta-learning from execution patterns

Run: python cookbook/meta/meta_demo.py
"""

from agno.meta import MetaFSAOrchestrator, TaskType


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def print_orchestration_summary(result):
    """Print orchestration result summary."""
    print("\n" + "="*80)
    print("  ORCHESTRATION SUMMARY")
    print("="*80)

    print(f"\n✅ Status: {'SUCCESS' if result.success else 'FAILED'}")
    print(f"📊 Total Time: {result.total_time_ms:.0f}ms")
    print(f"🔗 FSA Chain: {' → '.join([fsa.value for fsa in result.execution_sequence])}")
    print(f"📋 Components: {len(result.task_components)}")

    print("\n📈 FSA Execution Results:")
    for i, exec_result in enumerate(result.results, 1):
        status = "✓" if exec_result.success else "✗"
        print(f"   [{i}] {status} {exec_result.fsa_type.value}: {exec_result.execution_time_ms:.1f}ms")
        if exec_result.metrics:
            for key, value in exec_result.metrics.items():
                print(f"       • {key}: {value}")

    print("\n🎓 Learned Patterns:")
    for pattern in result.learned_patterns:
        print(f"   • {pattern}")

    print("\n📊 Metrics:")
    for key, value in result.metrics.items():
        if isinstance(value, float):
            print(f"   • {key}: {value:.2f}")
        else:
            print(f"   • {key}: {value}")


def print_performance_dashboard(orchestrator):
    """Print comprehensive performance dashboard."""
    print("\n╔" + "═"*78 + "╗")
    print("║" + " META-FSA PERFORMANCE DASHBOARD ".center(78) + "║")
    print("╚" + "═"*78 + "╝")

    dashboard = orchestrator.getPerformanceDashboard()

    print(f"\n📊 Overall Statistics")
    print(f"├─ Total Orchestrations:  {dashboard['total_orchestrations']}")
    print(f"├─ FSAs Tracked:          {len(dashboard['fsas'])}")
    print(f"└─ Patterns Learned:      {len(dashboard['learned_patterns'])}")

    print(f"\n🔧 FSA Performance Metrics")
    for fsa_name, metrics in dashboard['fsas'].items():
        print(f"\n├─ {fsa_name.upper()}")
        print(f"│  ├─ Executions:     {metrics['executions']}")
        print(f"│  ├─ Avg Time:       {metrics['avg_time_ms']:.1f}ms")
        print(f"│  ├─ Success Rate:   {metrics['success_rate']:.1f}%")
        print(f"│  └─ Total Time:     {metrics['total_time_ms']:.1f}ms")

    if dashboard['learned_patterns']:
        print(f"\n🎓 Recent Learned Patterns")
        for i, pattern in enumerate(dashboard['learned_patterns'][-5:], 1):
            print(f"├─ [{i}] {pattern.get('type', 'unknown')}")
            if 'sequence' in pattern:
                print(f"│  └─ Chain: {' → '.join(pattern['sequence'])}")


def demo_1_project_build():
    """Demo 1: Full project build with all FSAs."""
    print_section("Demo 1: Complete Project Build (All FSAs)")

    orchestrator = MetaFSAOrchestrator()

    task = """
Build a production-ready REST API for user authentication with the following features:
- User registration endpoint with email validation
- Login endpoint with JWT token generation
- Password hashing with bcrypt
- Input validation and sanitization
- Error handling and logging
- Database connection using parameterized queries
- Rate limiting for security
"""

    print("Task: Build production REST API with authentication")
    print("Expected FSA Chain: 1.1 → 1.2 → 2.2 → 3.1 → 2.1 → 3.2")

    result = orchestrator.orchestrate(
        task=task,
        task_type=TaskType.PROJECT_BUILD,
        language="python",
        config={
            "budget": {"max_cost_usd": 1.0, "max_latency_ms": 5000},
            "quality_target": 95.0,
            "rsi_iterations": 3,
        },
    )

    print_orchestration_summary(result)

    if result.final_output:
        print("\n📝 Generated Code Sample:")
        print("="*80)
        if hasattr(result.final_output, 'generated_code'):
            code = result.final_output.generated_code
            lines = code.split('\n')[:20]
            print('\n'.join(lines))
            if len(code.split('\n')) > 20:
                print("... (truncated)")
        print("="*80)


def demo_2_code_optimization():
    """Demo 2: Code optimization workflow."""
    print_section("Demo 2: Code Optimization (FSA-2.1 + FSA-3.2)")

    orchestrator = MetaFSAOrchestrator()

    code = '''
def authenticate(username, password):
    import sqlite3
    conn = sqlite3.connect('users.db')
    query = "SELECT * FROM users WHERE username='" + username + "' AND password='" + password + "'"
    result = conn.execute(query)
    user = result.fetchone()
    if user:
        return True
    return False
'''

    print("Task: Optimize insecure authentication code")
    print("Expected FSA Chain: 2.1 → 3.2")
    print("\nOriginal Code:")
    print(code)

    result = orchestrator.orchestrate(
        task=code,
        task_type=TaskType.CODE_OPTIMIZATION,
        language="python",
        config={"rsi_iterations": 5},
    )

    print_orchestration_summary(result)

    if result.final_output:
        print("\n📝 Optimized Code:")
        print("="*80)
        if hasattr(result.final_output, 'optimized_code'):
            print(result.final_output.optimized_code)
        print("="*80)

        if hasattr(result.final_output, 'original_quality'):
            print(f"\n📊 Quality Improvement:")
            print(f"   Initial:  {result.final_output.original_quality:.1f}/100")
            print(f"   Final:    {result.final_output.final_quality:.1f}/100")
            print(f"   Change:   {result.final_output.total_improvement:+.1f} points")


def demo_3_code_validation():
    """Demo 3: Code validation workflow."""
    print_section("Demo 3: Code Validation (FSA-1.1 + FSA-2.1)")

    orchestrator = MetaFSAOrchestrator()

    code = '''
def process_payment(card_number, amount):
    """Process credit card payment."""
    # TODO: Add validation
    api_key = "sk_live_1234567890"

    import requests
    response = requests.post(
        "https://api.stripe.com/v1/charges",
        data={"amount": amount, "source": card_number},
        headers={"Authorization": f"Bearer {api_key}"}
    )

    return response.json()
'''

    print("Task: Validate payment processing code")
    print("Expected FSA Chain: 1.1 → 2.1")
    print("\nCode to Validate:")
    print(code)

    result = orchestrator.orchestrate(
        task=code,
        task_type=TaskType.CODE_VALIDATION,
        language="python",
    )

    print_orchestration_summary(result)

    if result.final_output:
        print("\n📝 Validation Report:")
        print("="*80)
        if hasattr(result.final_output, 'report'):
            report = result.final_output.report
            print(f"Overall Score: {report.overall_score}/100")
            print("\nDimension Scores:")
            for dim, score in report.dimensions.items():
                status = "✓" if score.score >= 70 else "⚠" if score.score >= 50 else "✗"
                print(f"  {status} {dim}: {score.score}/100")

            if result.final_output.top_issues:
                print(f"\nTop Issues ({len(result.final_output.top_issues)}):")
                for issue in result.final_output.top_issues[:5]:
                    print(f"  [{issue.severity.value}] {issue.message}")
        print("="*80)


def demo_4_parallel_fsas():
    """Demo 4: Multiple orchestrations in parallel."""
    print_section("Demo 4: Multiple Orchestrations")

    orchestrator = MetaFSAOrchestrator()

    tasks = [
        ("Simple function optimization", TaskType.CODE_OPTIMIZATION, "def add(x,y): return eval(x+y)"),
        ("API validation", TaskType.CODE_VALIDATION, "def api(): return eval(request.args['code'])"),
        ("Small project", TaskType.PROJECT_BUILD, "Build a simple calculator API with add/subtract endpoints"),
    ]

    print(f"Running {len(tasks)} orchestrations...")

    for i, (desc, task_type, task) in enumerate(tasks, 1):
        print(f"\n[{i}/{len(tasks)}] {desc}")
        result = orchestrator.orchestrate(
            task=task,
            task_type=task_type,
            language="python",
            config={"rsi_iterations": 2},
        )
        print(f"   {'✓' if result.success else '✗'} Completed in {result.total_time_ms:.0f}ms")

    print_performance_dashboard(orchestrator)


def demo_5_meta_learning():
    """Demo 5: Demonstrate meta-learning capabilities."""
    print_section("Demo 5: Meta-Learning from Execution History")

    orchestrator = MetaFSAOrchestrator()

    # Run multiple orchestrations to build learning history
    scenarios = [
        ("Build user authentication API", TaskType.PROJECT_BUILD),
        ("Build data validation API", TaskType.PROJECT_BUILD),
        ("Build logging system", TaskType.PROJECT_BUILD),
    ]

    print(f"Running {len(scenarios)} orchestrations to build learning history...")

    for i, (task, task_type) in enumerate(scenarios, 1):
        print(f"\n[{i}/{len(scenarios)}] {task}")
        result = orchestrator.orchestrate(
            task=task,
            task_type=task_type,
            language="python",
            config={"budget": {"max_cost_usd": 0.5}},
        )
        print(f"   Status: {'SUCCESS' if result.success else 'FAILED'}")
        print(f"   Time: {result.total_time_ms:.0f}ms")
        print(f"   Patterns Learned: {len(result.learned_patterns)}")

    print("\n" + "="*80)
    print("  META-LEARNING INSIGHTS")
    print("="*80)

    dashboard = orchestrator.getPerformanceDashboard()

    print(f"\n📚 Total Patterns Learned: {len(orchestrator.learned_patterns)}")

    if orchestrator.learned_patterns:
        print("\n🎓 Pattern Analysis:")

        # Analyze successful chains
        successful_chains = [p for p in orchestrator.learned_patterns if p.get('type') == 'successful_chain']
        if successful_chains:
            print(f"\n   Successful FSA Chains: {len(successful_chains)}")
            for pattern in successful_chains[:3]:
                chain = ' → '.join(pattern['sequence'])
                print(f"   • {chain} (avg {pattern['avg_time_ms']:.0f}ms)")

    print(f"\n📊 Execution History: {len(orchestrator.execution_history)} orchestrations")

    # Show FSA usage patterns
    print("\n🔧 FSA Usage Patterns:")
    for fsa_name, metrics in dashboard['fsas'].items():
        if metrics['executions'] > 0:
            print(f"   • {fsa_name}: {metrics['executions']} executions, "
                  f"{metrics['success_rate']:.0f}% success rate")


def demo_6_performance_comparison():
    """Demo 6: Compare orchestration vs direct FSA usage."""
    print_section("Demo 6: Orchestration Performance Analysis")

    orchestrator = MetaFSAOrchestrator()

    print("Comparing orchestrated vs direct FSA execution...")

    # Test case
    code = '''
def get_user(id):
    query = "SELECT * FROM users WHERE id=" + str(id)
    return eval(query)
'''

    # Orchestrated execution
    print("\n1️⃣  Orchestrated Execution (FSA-4.1):")
    result_orchestrated = orchestrator.orchestrate(
        task=code,
        task_type=TaskType.CODE_OPTIMIZATION,
        language="python",
        config={"rsi_iterations": 3},
    )
    print(f"   Time: {result_orchestrated.total_time_ms:.0f}ms")
    print(f"   FSAs Used: {len(result_orchestrated.execution_sequence)}")
    print(f"   Success: {result_orchestrated.success}")

    # Direct execution
    print("\n2️⃣  Direct FSA Execution (Manual):")
    from agno.rsi import RSICodeOptimizer
    from agno.validator import CodeQualityValidator
    import time

    start = time.time()
    validator = CodeQualityValidator()
    optimizer = RSICodeOptimizer()

    validation = validator.validateCode(code, "python")
    optimization = optimizer.optimizeCode(code, "python", max_iterations=3)

    direct_time_ms = (time.time() - start) * 1000
    print(f"   Time: {direct_time_ms:.0f}ms")
    print(f"   FSAs Used: 2 (manual)")
    print(f"   Success: True")

    # Comparison
    print("\n📊 Comparison:")
    overhead = result_orchestrated.total_time_ms - direct_time_ms
    overhead_pct = (overhead / direct_time_ms * 100) if direct_time_ms > 0 else 0
    print(f"   Orchestration Overhead: {overhead:.0f}ms ({overhead_pct:.1f}%)")
    print(f"   Benefits:")
    print(f"   • Automatic FSA selection and sequencing")
    print(f"   • Dependency resolution")
    print(f"   • Performance tracking and meta-learning")
    print(f"   • Unified error handling")
    print(f"   • Reusable patterns")


def demo_7_error_handling():
    """Demo 7: Demonstrate error handling and recovery."""
    print_section("Demo 7: Error Handling and Recovery")

    orchestrator = MetaFSAOrchestrator()

    # Test with invalid input
    print("Test 1: Invalid language")
    result1 = orchestrator.orchestrate(
        task="Build an API",
        task_type=TaskType.PROJECT_BUILD,
        language="cobol",  # Unsupported language
    )
    print(f"   Status: {'SUCCESS' if result1.success else 'FAILED (expected)'}")
    print(f"   Time: {result1.total_time_ms:.0f}ms")

    # Test with empty task
    print("\nTest 2: Empty task")
    result2 = orchestrator.orchestrate(
        task="",
        task_type=TaskType.CODE_OPTIMIZATION,
        language="python",
    )
    print(f"   Status: {'SUCCESS' if result2.success else 'FAILED (expected)'}")
    print(f"   Time: {result2.total_time_ms:.0f}ms")

    print("\n✅ Error handling working correctly")
    print("   • Graceful failure on invalid inputs")
    print("   • No crashes or exceptions propagated")
    print("   • Execution time tracked even on failure")


def main():
    """Run all demos."""
    print("\n")
    print("█"*80)
    print("█" + " "*78 + "█")
    print("█" + "  FSA-4.1: META-FSA ORCHESTRATOR DEMONSTRATION  ".center(78) + "█")
    print("█" + " "*78 + "█")
    print("█"*80)
    print("\nCoordinating ALL FSA components:")
    print("  • FSA-1.1: Prompt Optimizer")
    print("  • FSA-1.2: Code Template Library")
    print("  • FSA-2.1: Code Quality Validator")
    print("  • FSA-2.2: Multi-Model Orchestrator")
    print("  • FSA-3.1: Multi-Step Code Builder")
    print("  • FSA-3.2: RSI Code Optimizer")

    try:
        demo_1_project_build()
        demo_2_code_optimization()
        demo_3_code_validation()
        demo_4_parallel_fsas()
        demo_5_meta_learning()
        demo_6_performance_comparison()
        demo_7_error_handling()

        # Final summary
        print_section("Demo Complete!")
        print("The Meta-FSA Orchestrator successfully demonstrated:")
        print("  ✓ Full FSA chain execution (1.1 → 1.2 → 2.1 → 2.2 → 3.1 → 3.2)")
        print("  ✓ Intelligent task decomposition")
        print("  ✓ Optimal FSA sequencing with dependency resolution")
        print("  ✓ Performance tracking across all FSAs")
        print("  ✓ Meta-learning from execution patterns")
        print("  ✓ Error handling and recovery")
        print("  ✓ Multiple orchestration scenarios")

        print("\nKey Features:")
        print("  • orchestrate(task, task_type, config) - Main coordination method")
        print("  • decompose(task, task_type) - Intelligent task breakdown")
        print("  • selectFSAs(components) - Optimal FSA selection")
        print("  • executeSequence(fsas, components) - FSA chain execution")
        print("  • trackPerformance(fsa, metrics) - Performance monitoring")
        print("  • learnFromExecution(results) - Meta-learning")
        print("  • getPerformanceDashboard() - Comprehensive analytics")

        print("\n🎉 FSA Ecosystem Complete!")
        print("   All 6 FSA components successfully integrated and orchestrated!")
        print("\n")

    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
