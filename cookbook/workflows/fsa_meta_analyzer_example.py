"""
Example: Using the FSA Meta-Analyzer to analyze workflows.

This example demonstrates how to use the FSA Meta-Analyzer to analyze,
validate, and optimize workflow FSAs in the Agno framework.
"""

from agno.workflows.fsa_meta_analyzer import FSAMetaAnalyzer

# Import example workflows to analyze
from cookbook.workflows.blog_post_generator import BlogPostGenerator
from cookbook.workflows.employee_recruiter import EmployeeRecruitmentWorkflow
from cookbook.workflows.personalized_email_generator import PersonalizedEmailGenerator


def analyze_single_workflow():
    """Example: Analyze a single workflow."""
    print("=" * 80)
    print("Example 1: Analyzing a Single Workflow")
    print("=" * 80)

    # Create the meta-analyzer
    analyzer = FSAMetaAnalyzer(
        session_id="meta_analysis_single",
        debug_mode=True,
    )

    # Analyze the BlogPostGenerator workflow
    print("\nAnalyzing BlogPostGenerator workflow...\n")

    responses = analyzer.run(
        workflow_class=BlogPostGenerator,
        include_performance=True,
        include_patterns=True,
        include_dependencies=True,
        include_optimization=True,
    )

    # Print all responses
    for response in responses:
        if response.content:
            print(response.content)

    # Get cached reports
    reports = analyzer.get_cached_reports()
    if reports:
        report = reports[0]

        print("\n" + "=" * 80)
        print("Detailed Analysis Results")
        print("=" * 80)

        # FSA Structure
        if report.fsa_structure:
            fsa = report.fsa_structure
            print(f"\nFSA Structure:")
            print(f"  Workflow: {fsa.workflow_name}")
            print(f"  Total States: {len(fsa.states)}")
            print(f"  Total Transitions: {len(fsa.transitions)}")
            print(f"  Entry State: {fsa.entry_state}")
            print(f"  Exit States: {fsa.exit_states}")
            print(f"  Error States: {fsa.error_states}")
            print(f"  Loop States: {fsa.loop_states}")
            print(f"  Agents: {fsa.agents}")
            print(f"\nComplexity Metrics:")
            for metric, value in fsa.complexity_metrics.items():
                print(f"  - {metric}: {value}")

        # Validation Report
        if report.validation_report:
            val = report.validation_report
            print(f"\nValidation Report:")
            print(f"  Valid: {val.is_valid}")
            print(f"  Total Issues: {len(val.issues)}")

            if val.issues:
                print("\n  Top Issues:")
                for i, issue in enumerate(val.issues[:5], 1):
                    print(f"    {i}. [{issue.severity.value.upper()}] {issue.category}")
                    print(f"       {issue.message}")
                    if issue.recommendation:
                        print(f"       Recommendation: {issue.recommendation}")

        # Quality Metrics
        if report.quality_metrics:
            qm = report.quality_metrics
            print(f"\nQuality Metrics:")
            print(f"  Overall Score: {qm.overall_quality_score:.1f}/100 (Grade: {qm.quality_grade})")
            print(f"  Maintainability: {qm.maintainability_index:.1f}/100")
            print(f"  Reliability: {qm.reliability_score:.1f}/100")
            print(f"  Efficiency: {qm.efficiency_score:.1f}/100")
            print(f"  Testability: {qm.testability_score:.1f}/100")
            print(f"  Best Practices: {qm.best_practices_score:.1f}/100")

            if qm.antipatterns_detected:
                print(f"\n  Antipatterns Detected:")
                for ap in qm.antipatterns_detected:
                    print(f"    - {ap}")

            if qm.improvement_areas:
                print(f"\n  Improvement Areas:")
                for area in qm.improvement_areas:
                    print(f"    - {area}")

        # Performance Analysis
        if report.performance_analysis:
            perf = report.performance_analysis
            print(f"\nPerformance Analysis:")
            print(f"  Performance Score: {perf.performance_score:.1f}/100")

            if perf.slowest_states:
                print(f"\n  Predicted Slowest States:")
                for state, score in perf.slowest_states:
                    print(f"    - {state}: complexity {score:.1f}")

            if perf.profile.bottleneck_states:
                print(f"\n  Bottleneck States:")
                for state in perf.profile.bottleneck_states:
                    print(f"    - {state}")

            if perf.recommendations:
                print(f"\n  Performance Recommendations:")
                for rec in perf.recommendations[:3]:
                    print(f"    - {rec}")

        # Pattern Analysis
        if report.pattern_analysis:
            pa = report.pattern_analysis
            print(f"\nPattern Analysis:")
            print(f"  Total Patterns: {len(pa.patterns)}")

            if pa.pattern_frequency:
                print(f"\n  Pattern Frequency:")
                for pattern_type, count in list(pa.pattern_frequency.items())[:5]:
                    print(f"    - {pattern_type.value}: {count}")

            if pa.antipatterns:
                print(f"\n  Antipatterns:")
                for ap in pa.antipatterns[:3]:
                    print(f"    - {ap.pattern_type.value}: {ap.description}")

        # Optimization Plan
        if report.optimization_plan:
            opt = report.optimization_plan
            print(f"\nOptimization Plan:")
            print(f"  Health: {opt.overall_health.upper()} ({opt.health_score:.1f}/100)")
            print(f"  Total Recommendations: {len(opt.recommendations)}")

            if opt.quick_wins:
                print(f"\n  Quick Wins ({len(opt.quick_wins)}):")
                for qw in opt.quick_wins[:3]:
                    print(f"    - [{qw.priority.upper()}] {qw.title}")
                    print(f"      {qw.description[:100]}...")
                    if qw.code_example:
                        print(f"      Example provided: Yes")

            if opt.long_term_improvements:
                print(f"\n  Long-term Improvements ({len(opt.long_term_improvements)}):")
                for lt in opt.long_term_improvements[:3]:
                    print(f"    - [{lt.priority.upper()}] {lt.title}")
                    print(f"      Impact: {lt.impact}")
                    print(f"      Effort: {lt.effort}")


def analyze_multiple_workflows():
    """Example: Analyze multiple workflows and compare them."""
    print("\n\n" + "=" * 80)
    print("Example 2: Analyzing Multiple Workflows")
    print("=" * 80)

    analyzer = FSAMetaAnalyzer(
        session_id="meta_analysis_multiple",
        debug_mode=True,
    )

    print("\nAnalyzing multiple workflows...\n")

    workflows = [
        BlogPostGenerator,
        EmployeeRecruitmentWorkflow,
        PersonalizedEmailGenerator,
    ]

    responses = analyzer.run(
        workflow_classes=workflows,
        include_performance=True,
        include_patterns=True,
        include_dependencies=True,
        include_optimization=True,
        generate_visualizations=True,
    )

    # Print all responses
    for response in responses:
        if response.content:
            print(response.content)


def analyze_with_static_components():
    """Example: Use individual analyzer components directly."""
    print("\n\n" + "=" * 80)
    print("Example 3: Using Individual Analyzer Components")
    print("=" * 80)

    from agno.workflows.fsa_meta_analyzer import (
        FSAStaticAnalyzer,
        FSAValidator,
        QualityMetricsCalculator,
    )

    # 1. Static Analysis
    print("\n1. Static Analysis")
    print("-" * 40)

    static_analyzer = FSAStaticAnalyzer()
    fsa_structure = static_analyzer.analyze_workflow(BlogPostGenerator)

    print(f"Analyzed: {fsa_structure.workflow_name}")
    print(f"States: {len(fsa_structure.states)}")
    print(f"Transitions: {len(fsa_structure.transitions)}")
    print(f"\nState Details:")
    for state_name, state in list(fsa_structure.states.items())[:5]:
        print(f"  - {state_name} ({state.state_type})")
        if state.agent_calls:
            print(f"    Agent calls: {state.agent_calls}")

    # 2. Validation
    print("\n2. Validation")
    print("-" * 40)

    validator = FSAValidator()
    validation_report = validator.validate(fsa_structure)

    print(f"Valid: {validation_report.is_valid}")
    print(f"Issues: {len(validation_report.issues)}")

    for issue in validation_report.issues[:3]:
        print(f"  - [{issue.severity.value}] {issue.message}")

    # 3. Quality Metrics
    print("\n3. Quality Metrics")
    print("-" * 40)

    quality_calc = QualityMetricsCalculator()
    quality_metrics = quality_calc.calculate_metrics(fsa_structure, validation_report)

    print(f"Overall Score: {quality_metrics.overall_quality_score:.1f}/100")
    print(f"Grade: {quality_metrics.quality_grade}")
    print(f"Maintainability: {quality_metrics.maintainability_index:.1f}/100")
    print(f"Reliability: {quality_metrics.reliability_score:.1f}/100")


def export_analysis_report():
    """Example: Export analysis report to file."""
    print("\n\n" + "=" * 80)
    print("Example 4: Exporting Analysis Report")
    print("=" * 80)

    analyzer = FSAMetaAnalyzer(session_id="meta_analysis_export")

    # Run analysis
    list(analyzer.run(workflow_class=BlogPostGenerator))

    # Get the report
    reports = analyzer.get_cached_reports()
    if reports:
        report = reports[0]

        # Export to file
        output_path = "/tmp/fsa_analysis_report.json"
        success = analyzer.export_report(report, output_path)

        if success:
            print(f"\n✓ Report exported successfully to: {output_path}")
        else:
            print(f"\n✗ Failed to export report")


if __name__ == "__main__":
    # Run all examples
    try:
        analyze_single_workflow()
    except Exception as e:
        print(f"Error in Example 1: {e}")

    try:
        analyze_multiple_workflows()
    except Exception as e:
        print(f"Error in Example 2: {e}")

    try:
        analyze_with_static_components()
    except Exception as e:
        print(f"Error in Example 3: {e}")

    try:
        export_analysis_report()
    except Exception as e:
        print(f"Error in Example 4: {e}")
