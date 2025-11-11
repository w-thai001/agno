"""
FSA-3.2: RSI Code Optimizer - Demonstration

This demo showcases Recursive Self-Improvement capabilities:
- Iterative code optimization through multiple cycles
- Quality assessment using FSA-2.1 at each iteration
- Improvement tracking and convergence detection
- Rollback on quality degradation
- Comprehensive metrics and visualization

Run: python cookbook/rsi/rsi_demo.py
"""

from agno.rsi import RSICodeOptimizer


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print(f"{'=' * 80}\n")


def print_iteration_table(result):
    """Print iteration metrics in table format."""
    if not result.iterations:
        print("No iterations recorded")
        return

    print(f"{'Iter':<6} {'Quality':<10} {'Delta':<10} {'Improvements':<50}")
    print("-" * 80)

    # Initial state
    print(f"{'0':<6} {result.original_quality:<10.2f} {'-':<10} {'(Initial)':<50}")

    for metrics in result.iterations:
        quality = f"{metrics.quality_score:.2f}"
        delta = f"{metrics.quality_delta:+.2f}"
        improvements = ", ".join(metrics.improvements_applied[:2])
        if len(metrics.improvements_applied) > 2:
            improvements += "..."
        print(f"{metrics.iteration:<6} {quality:<10} {delta:<10} {improvements:<50}")


def print_dimension_trajectory(result):
    """Print quality dimension evolution."""
    if not result.iterations:
        return

    dimensions = list(result.iterations[0].dimension_scores.keys())

    print(f"\n{'Dimension':<20} {'Initial':<10} {'Final':<10} {'Change':<10}")
    print("-" * 50)

    # Get initial validation
    from agno.validator import CodeQualityValidator

    validator = CodeQualityValidator()
    initial_validation = validator.validateCode(result.original_code, result.language)
    initial_dims = {dim: score.score for dim, score in initial_validation.report.dimensions.items()}

    final_dims = result.iterations[-1].dimension_scores

    for dim in dimensions:
        initial = initial_dims.get(dim, 0)
        final = final_dims.get(dim, 0)
        change = final - initial

        status = "✓" if change >= 0 else "✗"
        print(f"{status} {dim:<18} {initial:<10} {final:<10} {change:+.1f}")


def visualize_trajectory(result):
    """Visualize quality improvement trajectory."""
    print("\nQuality Improvement Trajectory:")
    print("-" * 80)

    # Collect all quality points
    qualities = [result.original_quality] + [m.quality_score for m in result.iterations]

    max_quality = max(qualities)
    min_quality = min(qualities)
    quality_range = max_quality - min_quality if max_quality > min_quality else 1

    for i, quality in enumerate(qualities):
        # Normalize to 0-60 range for visualization
        normalized = int((quality - min_quality) / quality_range * 60) if quality_range > 0 else 30

        bar = "█" * normalized
        label = "Initial" if i == 0 else f"Iter {i}"

        print(f"{label:<8} {quality:5.1f} | {bar}")

    print("-" * 80)
    print(f"Improvement: {result.total_improvement:+.1f} points\n")


def demo_basic_optimization():
    """Demonstrate basic RSI optimization."""
    print_section("Demo 1: Basic RSI Optimization")

    optimizer = RSICodeOptimizer(
        convergence_threshold=2.0,
        quality_target=95.0,
        max_iterations=5,
    )

    # Code with security issues
    code = '''
def get_user(user_id):
    import sqlite3
    conn = sqlite3.connect('database.db')
    query = "SELECT * FROM users WHERE id='" + str(user_id) + "'"
    result = conn.execute(query)
    return result.fetchone()
'''

    print("Original Code:")
    print(code)
    print("\nStarting RSI optimization...")

    result = optimizer.optimizeCode(code, language="python", max_iterations=5)

    print(f"\n{result.summary}\n")

    print_iteration_table(result)
    visualize_trajectory(result)

    print("\nOptimized Code:")
    print(result.optimized_code)


def demo_convergence_detection():
    """Demonstrate convergence detection."""
    print_section("Demo 2: Convergence Detection")

    optimizer = RSICodeOptimizer(
        convergence_threshold=1.0,  # Stricter threshold
        quality_target=98.0,
        max_iterations=10,
    )

    # Already decent code
    code = '''
def calculate_average(numbers):
    """Calculate the average of a list of numbers."""
    if not numbers:
        return 0
    return sum(numbers) / len(numbers)
'''

    print("Original Code (already decent quality):")
    print(code)

    result = optimizer.optimizeCode(code, language="python")

    print(f"\n{result.summary}\n")
    print(f"Convergence Reason: {result.convergence_reason.value}")
    print(f"Total Iterations: {len(result.iterations)}")

    print_iteration_table(result)


def demo_multiple_improvements():
    """Demonstrate multiple improvement types."""
    print_section("Demo 3: Multiple Improvement Types")

    optimizer = RSICodeOptimizer(
        convergence_threshold=2.0,
        quality_target=95.0,
        max_iterations=5,
    )

    # Code with multiple issues
    code = '''
def processData(input):
    result = eval(input)
    x = result + 10
    return x
'''

    print("Original Code (multiple issues):")
    print(code)
    print("\nIssues:")
    print("  • Security: eval() usage")
    print("  • Style: camelCase naming")
    print("  • Missing: docstrings, error handling\n")

    result = optimizer.optimizeCode(code, language="python", max_iterations=5)

    print(f"\n{result.summary}\n")

    # Show improvements applied
    print("Improvements Applied per Iteration:")
    for metrics in result.iterations:
        print(f"\nIteration {metrics.iteration}:")
        for improvement in metrics.improvements_applied:
            print(f"  • {improvement}")

    print(f"\nFinal Quality: {result.final_quality:.1f}/100")
    print(f"Total Improvement: {result.total_improvement:+.1f} points")


def demo_dimension_tracking():
    """Demonstrate quality dimension tracking."""
    print_section("Demo 4: Quality Dimension Tracking")

    optimizer = RSICodeOptimizer(max_iterations=5)

    code = '''
def getData(id):
    import sqlite3
    conn = sqlite3.connect('db.db')
    result = eval("SELECT * FROM data WHERE id=" + str(id))
    return result
'''

    print("Original Code:")
    print(code)

    result = optimizer.optimizeCode(code, language="python")

    print(f"\n{result.summary}\n")

    print_dimension_trajectory(result)

    print("\nDimension Scores Over Iterations:")
    for metrics in result.iterations:
        print(f"\nIteration {metrics.iteration}:")
        for dim, score in metrics.dimension_scores.items():
            status = "✓" if score >= 70 else "⚠" if score >= 50 else "✗"
            print(f"  {status} {dim:<20} {score}/100")


def demo_trajectory_visualization():
    """Demonstrate optimization trajectory visualization."""
    print_section("Demo 5: Optimization Trajectory Visualization")

    optimizer = RSICodeOptimizer(
        convergence_threshold=1.5,
        quality_target=95.0,
        max_iterations=7,
    )

    code = '''
password = "admin123"

def login(user, pwd):
    if pwd == password:
        return True
    return False

def getUsers():
    query = "SELECT * FROM users"
    return eval(query)
'''

    print("Original Code (multiple security issues):")
    print(code)

    result = optimizer.optimizeCode(code, language="python", max_iterations=7)

    print(f"\n{result.summary}\n")

    visualize_trajectory(result)

    # Show quality metrics
    print("Quality Metrics:")
    print(f"  Initial:     {result.original_quality:.2f}/100")
    print(f"  Final:       {result.final_quality:.2f}/100")
    print(f"  Improvement: {result.total_improvement:+.2f}")
    print(f"  Iterations:  {len(result.iterations)}")
    print(f"  Time:        {result.total_time_ms:.0f}ms")


def demo_metrics_dashboard():
    """Demonstrate comprehensive metrics dashboard."""
    print_section("Demo 6: Comprehensive Metrics Dashboard")

    optimizer = RSICodeOptimizer(max_iterations=5)

    code = '''
def calc(x):
    return eval(x)

def getData(id):
    query = "SELECT * FROM data WHERE id='" + id + "'"
    return query
'''

    result = optimizer.optimizeCode(code, language="python")

    print("╔" + "═" * 78 + "╗")
    print("║" + " RSI OPTIMIZATION METRICS DASHBOARD ".center(78) + "║")
    print("╚" + "═" * 78 + "╝")

    print(f"\n📊 Overall Statistics")
    print(f"├─ Initial Quality:      {result.original_quality:.2f}/100")
    print(f"├─ Final Quality:        {result.final_quality:.2f}/100")
    print(f"├─ Total Improvement:    {result.total_improvement:+.2f} points")
    print(f"├─ Iterations:           {len(result.iterations)}")
    print(f"├─ Convergence:          {result.convergence_reason.value}")
    print(f"├─ Success:              {'YES ✓' if result.success else 'NO ✗'}")
    print(f"└─ Total Time:           {result.total_time_ms:.0f}ms")

    print(f"\n🔄 Iteration Summary")
    for metrics in result.iterations:
        print(f"├─ Iteration {metrics.iteration}")
        print(f"│  ├─ Quality:          {metrics.quality_score:.2f}/100 ({metrics.quality_delta:+.2f})")
        print(f"│  ├─ Improvements:     {len(metrics.improvements_applied)}")
        print(f"│  └─ Validation Time:  {metrics.validation_time_ms:.2f}ms")

    if result.iterations:
        print(f"\n🎯 Dimension Breakdown (Final)")
        final_metrics = result.iterations[-1]
        for dim, score in final_metrics.dimension_scores.items():
            bar_length = int(score / 100 * 40)
            bar = "█" * bar_length + "░" * (40 - bar_length)
            print(f"├─ {dim:<20} [{bar}] {score}/100")

    print(f"\n✨ Improvements Applied")
    all_improvements = []
    for metrics in result.iterations:
        all_improvements.extend(metrics.improvements_applied)

    for i, improvement in enumerate(all_improvements, 1):
        prefix = "└─" if i == len(all_improvements) else "├─"
        print(f"{prefix} {improvement}")


def demo_comparison():
    """Demonstrate before/after comparison."""
    print_section("Demo 7: Before/After Comparison")

    optimizer = RSICodeOptimizer(max_iterations=5)

    code = '''
def processUser(userId):
    import sqlite3
    conn = sqlite3.connect('users.db')
    query = "SELECT * FROM users WHERE id='" + userId + "'"
    user = eval(conn.execute(query).fetchone())
    return user
'''

    print("BEFORE Optimization:")
    print("=" * 80)
    print(code)

    # Get initial quality
    from agno.validator import CodeQualityValidator

    validator = CodeQualityValidator()
    initial_validation = validator.validateCode(code, "python")

    print("\nInitial Quality Report:")
    print(f"Overall Score: {initial_validation.report.overall_score}/100")
    for dim, score in initial_validation.report.dimensions.items():
        print(f"  {dim}: {score.score}/100")

    if initial_validation.top_issues:
        print(f"\nTop Issues ({len(initial_validation.top_issues)}):")
        for issue in initial_validation.top_issues[:5]:
            print(f"  • [{issue.severity.value}] {issue.message}")

    print("\n" + "=" * 80)
    print("Running RSI Optimization...")
    print("=" * 80)

    result = optimizer.optimizeCode(code, language="python", max_iterations=5)

    print("\nAFTER Optimization:")
    print("=" * 80)
    print(result.optimized_code)

    print("\nFinal Quality Report:")
    final_validation = validator.validateCode(result.optimized_code, "python")
    print(f"Overall Score: {final_validation.report.overall_score}/100")
    for dim, score in final_validation.report.dimensions.items():
        print(f"  {dim}: {score.score}/100")

    print("\n" + "=" * 80)
    print("IMPROVEMENT SUMMARY")
    print("=" * 80)
    print(f"Quality:    {result.original_quality:.1f} → {result.final_quality:.1f} ({result.total_improvement:+.1f})")
    print(f"Iterations: {len(result.iterations)}")
    print(f"Time:       {result.total_time_ms:.0f}ms")


def main():
    """Run all demos."""
    print("\n")
    print("█" * 80)
    print("█" + " " * 78 + "█")
    print("█" + "  FSA-3.2: RSI CODE OPTIMIZER DEMONSTRATION  ".center(78) + "█")
    print("█" + " " * 78 + "█")
    print("█" * 80)
    print("\nRecursive Self-Improvement with:")
    print("  • FSA-2.1: Code Quality Validator (quality assessment)")
    print("  • FSA-3.1: Multi-Step Code Builder (improvement generation)")
    print("  • Iterative optimization loop")
    print("  • Convergence detection")
    print("  • Comprehensive metrics tracking")

    try:
        demo_basic_optimization()
        demo_convergence_detection()
        demo_multiple_improvements()
        demo_dimension_tracking()
        demo_trajectory_visualization()
        demo_metrics_dashboard()
        demo_comparison()

        # Final summary
        print_section("Demo Complete!")
        print("The RSI Code Optimizer successfully demonstrated:")
        print("  ✓ Iterative code optimization (up to 5-7 iterations)")
        print("  ✓ Quality assessment using FSA-2.1")
        print("  ✓ Multiple improvement types (security, style, performance)")
        print("  ✓ Convergence detection (plateau, target reached)")
        print("  ✓ Quality tracking per iteration")
        print("  ✓ Dimension-level metrics")
        print("  ✓ Comprehensive metrics dashboard")
        print("  ✓ Before/after comparison")
        print("\nKey Features:")
        print("  • optimizeCode(code, max_iterations) - Main RSI loop")
        print("  • assessQuality(code) - FSA-2.1 integration")
        print("  • generateImprovements() - FSA-3.1 ready")
        print("  • trackIteration() - Metrics tracking")
        print("  • Automatic convergence detection")
        print("  • Rollback on quality degradation")
        print("\n")

    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
