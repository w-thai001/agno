"""Quick test for FSA-4.1 Meta-FSA Orchestrator."""

from agno.meta import MetaFSAOrchestrator, TaskType

def test_code_optimization():
    """Test code optimization workflow."""
    print("Testing FSA-4.1: Code Optimization")
    print("="*80)

    orchestrator = MetaFSAOrchestrator()

    code = '''
def add(x, y):
    return eval(str(x) + "+" + str(y))
'''

    result = orchestrator.orchestrate(
        task=code,
        task_type=TaskType.CODE_OPTIMIZATION,
        language="python",
        config={"rsi_iterations": 3}
    )

    print(f"\nSuccess: {result.success}")
    print(f"FSA Chain: {' → '.join([fsa.value for fsa in result.execution_sequence])}")
    print(f"Total Time: {result.total_time_ms:.0f}ms")

    if result.final_output and hasattr(result.final_output, 'optimized_code'):
        print(f"\nQuality: {result.final_output.original_quality:.1f} → {result.final_output.final_quality:.1f}")
        print(f"Improvement: {result.final_output.total_improvement:+.1f} points")
        print("\nOptimized Code:")
        print(result.final_output.optimized_code)

    # Check performance dashboard
    dashboard = orchestrator.getPerformanceDashboard()
    print(f"\n\nPerformance Dashboard:")
    print(f"Total Orchestrations: {dashboard['total_orchestrations']}")

    for fsa_name, metrics in dashboard['fsas'].items():
        if metrics['executions'] > 0:
            print(f"\n{fsa_name}:")
            print(f"  Executions: {metrics['executions']}")
            print(f"  Success Rate: {metrics['success_rate']:.1f}%")

    return result.success


def test_project_build():
    """Test project build workflow."""
    print("\n\n" + "="*80)
    print("Testing FSA-4.1: Project Build")
    print("="*80)

    orchestrator = MetaFSAOrchestrator()

    result = orchestrator.orchestrate(
        task="Build a simple API with GET and POST endpoints",
        task_type=TaskType.PROJECT_BUILD,
        language="python",
        config={"budget": {"max_cost_usd": 0.5}, "rsi_iterations": 2}
    )

    print(f"\nSuccess: {result.success}")
    print(f"FSA Chain: {' → '.join([fsa.value for fsa in result.execution_sequence])}")
    print(f"Total Time: {result.total_time_ms:.0f}ms")
    print(f"FSAs Executed: {len(result.results)}")
    print(f"Success Rate: {result.metrics.get('success_rate', 0)*100:.0f}%")

    # Project build is successful if CODE_BUILDER succeeded
    code_builder_success = any(
        r.fsa_type.value == "fsa_3_1" and r.success
        for r in result.results
    )

    return code_builder_success


if __name__ == "__main__":
    print("FSA-4.1 Meta-FSA Orchestrator - Quick Test")
    print("="*80)

    test1 = test_code_optimization()
    test2 = test_project_build()

    print("\n\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Code Optimization: {'✓ PASS' if test1 else '✗ FAIL'}")
    print(f"Project Build: {'✓ PASS' if test2 else '✗ FAIL'}")
    print(f"\nOverall: {'✓ ALL TESTS PASSED' if test1 and test2 else '✗ SOME TESTS FAILED'}")
