"""
Complexity Analyzer Example

Demonstrates comprehensive code complexity analysis with the ComplexityAnalyzer FSA.
Shows cyclomatic complexity, cognitive complexity, Halstead metrics, maintainability index,
hotspot detection, and refactoring recommendations.
"""

from agno.tools.complexity_analyzer import (
    ComplexityAnalyzer,
    ComplexityBudget,
    ComplexityLevel,
)


# Sample code to analyze
SAMPLE_CODE = """
class DataProcessor:
    '''A class for processing data with various complexity levels'''

    def __init__(self):
        self.data = []
        self.processed = False

    def simple_method(self, x):
        '''Simple method with low complexity'''
        return x * 2

    def moderate_complexity(self, items):
        '''Method with moderate complexity'''
        result = []
        for item in items:
            if item > 0:
                result.append(item * 2)
            elif item < 0:
                result.append(abs(item))
            else:
                result.append(0)
        return result

    def high_complexity_method(self, data, threshold, mode):
        '''Method with high complexity - needs refactoring'''
        results = []

        if mode == 'strict':
            for item in data:
                if item > threshold:
                    if item % 2 == 0:
                        if item % 3 == 0:
                            if item % 5 == 0:
                                results.append(item)
                            else:
                                results.append(item / 5)
                        else:
                            results.append(item / 3)
                    else:
                        results.append(item / 2)
                elif item < 0:
                    for i in range(abs(item)):
                        if i % 2 == 0:
                            results.append(i)
        elif mode == 'lenient':
            for item in data:
                if item > threshold / 2:
                    results.append(item)
        else:
            return None

        return results

    def deeply_nested_logic(self, matrix):
        '''Deeply nested method showing cognitive complexity'''
        count = 0
        for row in matrix:
            for col in row:
                if col > 0:
                    for i in range(col):
                        if i % 2 == 0:
                            while i > 0:
                                if i % 3 == 0:
                                    count += 1
                                i -= 1
        return count


def standalone_function(x, y, z):
    '''Standalone function with moderate complexity'''
    if x > 0 and y > 0:
        return x + y
    elif x < 0 or y < 0:
        if z > 0:
            return abs(x) + abs(y) + z
        return 0
    return z
"""


def print_header(title: str):
    """Print formatted section header"""
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print(f"{'=' * 80}\n")


def print_function_details(func_complexity):
    """Print detailed complexity metrics for a function"""
    print(f"  Function: {func_complexity.name}")
    print(f"    Cyclomatic Complexity: {func_complexity.cyclomatic}")
    print(f"    Cognitive Complexity:  {func_complexity.cognitive}")
    print(f"    Complexity Level:      {func_complexity.complexity_level.value}")
    print(f"    Nesting Depth:         {func_complexity.nesting_depth}")
    print(f"    Parameters:            {func_complexity.params}")
    print(f"    Local Variables:       {func_complexity.variables}")
    print(f"    Lines of Code:         {func_complexity.loc.physical}")
    print(f"    Halstead Volume:       {func_complexity.halstead.volume:.2f}")
    print(f"    Estimated Bugs:        {func_complexity.halstead.bugs:.4f}")
    print()


def main():
    """Run complete complexity analysis example"""

    print_header("Complexity Analyzer FSA - Comprehensive Code Analysis")

    # Initialize analyzer
    analyzer = ComplexityAnalyzer()

    # Perform analysis
    print("Analyzing sample code...\n")
    report = analyzer.analyze(SAMPLE_CODE)

    # Display overall metrics
    print_header("Overall Module Metrics")
    print(f"Total Cyclomatic Complexity:  {report.cyclomatic_total}")
    print(f"Total Cognitive Complexity:   {report.cognitive_total}")
    print(f"Maintainability Index:        {report.maintainability_index:.2f} / 100")
    print(f"Maximum Nesting Depth:        {report.max_nesting_depth}")
    print(f"Code Entropy:                 {report.entropy:.2f}")
    print(f"Number of Functions:          {len(report.module.functions)}")
    print(f"Number of Classes:            {len(report.module.classes)}")
    print(f"Import Count:                 {report.module.imports_count}")

    print("\nLines of Code:")
    print(f"  Physical Lines:   {report.loc.physical}")
    print(f"  Logical Lines:    {report.loc.logical}")
    print(f"  Comment Lines:    {report.loc.comments}")
    print(f"  Blank Lines:      {report.loc.blank}")

    print("\nHalstead Metrics:")
    print(f"  Vocabulary (n):   {report.halstead.vocabulary}")
    print(f"  Length (N):       {report.halstead.length}")
    print(f"  Volume (V):       {report.halstead.volume:.2f}")
    print(f"  Difficulty (D):   {report.halstead.difficulty:.2f}")
    print(f"  Effort (E):       {report.halstead.effort:.2f}")
    print(f"  Time (T):         {report.halstead.time:.2f} seconds")
    print(f"  Estimated Bugs:   {report.halstead.bugs:.4f}")

    # Maintainability interpretation
    print("\nMaintainability Assessment:")
    if report.maintainability_index >= 20:
        print("  ✓ Code is MAINTAINABLE")
    elif report.maintainability_index >= 10:
        print("  ⚠ Code is MODERATELY maintainable - consider refactoring")
    else:
        print("  ✗ Code is UNMAINTAINABLE - refactoring required")

    # Display class complexity
    if report.module.classes:
        print_header("Class Complexity Analysis")
        for cls in report.module.classes:
            print(f"Class: {cls.name}")
            print(f"  Total Complexity:       {cls.total_complexity}")
            print(f"  Average Method Complexity: {cls.avg_method_complexity:.2f}")
            print(f"  Number of Methods:      {len(cls.methods_complexity)}")
            print(f"  Number of Attributes:   {cls.attributes_count}")
            print(f"\n  Methods:")

            # Sort methods by complexity
            sorted_methods = analyzer.rank_by_complexity(cls.methods_complexity)
            for method in sorted_methods:
                print_function_details(method)

    # Display standalone function complexity
    if report.module.functions:
        print_header("Standalone Function Complexity")
        for func in report.module.functions:
            print_function_details(func)

    # Detect and display hotspots
    print_header("Complexity Hotspots")
    hotspots = analyzer.detect_complexity_hotspots(report, threshold=5)

    if hotspots:
        print(f"Found {len(hotspots)} complexity hotspot(s):\n")
        for i, hotspot in enumerate(hotspots, 1):
            print(f"{i}. {hotspot.location}")
            print(f"   Metric Type:       {hotspot.metric_type}")
            print(f"   Complexity Score:  {hotspot.complexity_score}")
            print(f"   Severity:          {hotspot.severity.upper()}")
            print(f"   Description:       {hotspot.description}")
            print()
    else:
        print("✓ No significant complexity hotspots detected!")

    # Generate refactoring suggestions
    if hotspots:
        print_header("Refactoring Recommendations")
        for hotspot in hotspots[:3]:  # Show top 3 hotspots
            suggestions = analyzer.suggest_refactorings(hotspot)
            if suggestions:
                print(f"For {hotspot.location}:")
                for j, suggestion in enumerate(suggestions, 1):
                    print(f"  {j}. {suggestion.refactoring_type.value}")
                    print(f"     {suggestion.description}")
                    print(f"     Estimated Complexity Reduction: {suggestion.estimated_reduction}")
                    print()

    # Enforce complexity budget
    print_header("Complexity Budget Enforcement")
    budget = ComplexityBudget(
        max_function_cyclomatic=10,
        max_function_cognitive=7,
        max_class_complexity=50,
        max_module_complexity=100,
        max_nesting_depth=4
    )

    print("Budget Constraints:")
    print(f"  Max Function Cyclomatic:  {budget.max_function_cyclomatic}")
    print(f"  Max Function Cognitive:   {budget.max_function_cognitive}")
    print(f"  Max Class Complexity:     {budget.max_class_complexity}")
    print(f"  Max Module Complexity:    {budget.max_module_complexity}")
    print(f"  Max Nesting Depth:        {budget.max_nesting_depth}")
    print()

    budget_report = analyzer.enforce_complexity_budget(report, budget)

    if budget_report.over_budget:
        print(f"✗ Budget VIOLATED - {len(budget_report.violations)} violation(s):\n")
        for violation in budget_report.violations:
            print(f"  • {violation}")
    else:
        print("✓ All complexity budgets are within limits!")

    # Summary recommendations
    print_header("Summary & Recommendations")

    critical_issues = [h for h in hotspots if h.severity == "critical"]
    high_issues = [h for h in hotspots if h.severity == "high"]

    if critical_issues:
        print(f"⚠ CRITICAL: {len(critical_issues)} critical complexity issue(s) found")
        print("   Immediate refactoring recommended!")
    elif high_issues:
        print(f"⚠ WARNING: {len(high_issues)} high complexity issue(s) found")
        print("   Consider refactoring in next iteration")
    else:
        print("✓ Code complexity is within acceptable limits")

    print(f"\nOverall Health Score: {report.maintainability_index:.1f} / 100")

    if report.maintainability_index >= 85:
        print("Rating: EXCELLENT - Keep up the good work!")
    elif report.maintainability_index >= 65:
        print("Rating: GOOD - Minor improvements possible")
    elif report.maintainability_index >= 40:
        print("Rating: FAIR - Refactoring recommended")
    else:
        print("Rating: POOR - Significant refactoring required")

    print("\n" + "=" * 80)
    print("Analysis complete!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
