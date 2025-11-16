"""🧪 FSA Testing Framework Example

This example demonstrates comprehensive FSA testing with unit, integration,
property, and performance tests.

Run `pip install agno` to install dependencies.
"""

from agno.fsa.code_builder import MultiStepCodeBuilder
from agno.fsa.testing_framework import FSATestingFramework


def main():
    """Demonstrate FSA Testing Framework"""

    print("\n" + "=" * 60)
    print("FSA TESTING FRAMEWORK")
    print("=" * 60)

    # Create an FSA to test
    code_builder = MultiStepCodeBuilder(
        name="CodeBuilder",
        programming_language="python"
    )

    # Create testing framework
    test_framework = FSATestingFramework(
        name="FSATester",
        enable_unit_tests=True,
        enable_integration_tests=True,
        enable_property_tests=True,
        enable_performance_tests=True,
        performance_threshold_ms=5000.0,
        min_coverage_threshold=70.0,
        debug_mode=True
    )

    # Run tests
    result = test_framework.run({"fsa": code_builder})

    print("\n" + "=" * 60)
    print("TEST RESULTS")
    print("=" * 60)

    print(f"\nFSA Tested: {result.fsa_name}")
    print(f"Total Tests: {result.total_tests}")
    print(f"Passed: {result.passed_tests} ✅")
    print(f"Failed: {result.failed_tests} ❌")
    print(f"Pass Rate: {result.pass_rate:.1f}%")
    print(f"Total Duration: {result.total_duration:.3f}s")

    # Show test suites
    print("\n📋 TEST SUITES:")
    for suite in result.test_suites:
        status = "✅" if suite.pass_rate == 100 else "⚠️" if suite.pass_rate >= 50 else "❌"
        print(f"\n  {status} {suite.name}")
        print(f"     Tests: {suite.passed_tests}/{suite.total_tests}")
        print(f"     Pass Rate: {suite.pass_rate:.1f}%")
        print(f"     Duration: {suite.total_duration:.3f}s")

        # Show individual tests
        for test in suite.tests:
            test_status = "✓" if test.passed else "✗"
            print(f"      {test_status} {test.test_name} ({test.duration:.3f}s)")
            if not test.passed and test.error:
                print(f"         Error: {test.error}")

    # Show coverage
    print("\n📊 COVERAGE:")
    print(f"  States: {result.coverage.states_tested}/{result.coverage.total_states} ({result.coverage.state_coverage:.1f}%)")
    print(f"  Transitions: {result.coverage.transitions_tested}/{result.coverage.total_transitions} ({result.coverage.transition_coverage:.1f}%)")
    print(f"  Overall: {result.coverage.overall_coverage:.1f}%")

    # Show coverage bar
    coverage = result.coverage.overall_coverage
    bar_length = 40
    filled = int(bar_length * coverage / 100)
    bar = "█" * filled + "░" * (bar_length - filled)
    print(f"  [{bar}] {coverage:.1f}%")

    # Show issues
    if result.issues_found:
        print("\n🐛 ISSUES FOUND:")
        for i, issue in enumerate(result.issues_found, 1):
            print(f"  {i}. {issue}")

    # Show recommendations
    if result.recommendations:
        print("\n💡 RECOMMENDATIONS:")
        for i, rec in enumerate(result.recommendations, 1):
            print(f"  {i}. {rec}")

    # Overall status
    print("\n" + "=" * 60)
    if result.pass_rate == 100 and result.coverage.overall_coverage >= test_framework.min_coverage_threshold:
        print("✅ ALL TESTS PASSED - FSA IS PRODUCTION READY!")
    elif result.pass_rate >= 80:
        print("⚠️  TESTS MOSTLY PASSING - MINOR FIXES NEEDED")
    else:
        print("❌ TESTS FAILING - SIGNIFICANT ISSUES FOUND")
    print("=" * 60)

    # Print full report
    print("\n" + test_framework.get_test_report())


if __name__ == "__main__":
    main()
