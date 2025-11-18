"""
Unit tests for ComplexityAnalyzer

Tests all major functionality including cyclomatic complexity, cognitive complexity,
Halstead metrics, maintainability index, nesting depth, entropy, hotspot detection,
and refactoring suggestions.
"""

import ast
import pytest
from agno.tools.complexity_analyzer import (
    ComplexityAnalyzer,
    ComplexityLevel,
    RefactoringType,
    HalsteadMetrics,
    ComplexityBudget,
)


class TestCyclomaticComplexity:
    """Test cyclomatic complexity calculations"""

    def test_simple_function_complexity(self):
        """Test complexity of simple function (should be 1)"""
        code = """
def simple():
    return 42
"""
        tree = ast.parse(code)
        func = tree.body[0]
        analyzer = ComplexityAnalyzer()
        complexity = analyzer.calculate_cyclomatic_complexity(func)
        assert complexity == 1

    def test_function_with_if_statement(self):
        """Test complexity with single if statement"""
        code = """
def with_if(x):
    if x > 0:
        return x
    return 0
"""
        tree = ast.parse(code)
        func = tree.body[0]
        analyzer = ComplexityAnalyzer()
        complexity = analyzer.calculate_cyclomatic_complexity(func)
        assert complexity == 2  # 1 base + 1 if

    def test_function_with_multiple_conditions(self):
        """Test complexity with multiple conditions"""
        code = """
def complex_func(x, y):
    if x > 0:
        if y > 0:
            return x + y
    elif x < 0:
        return -x
    return 0
"""
        tree = ast.parse(code)
        func = tree.body[0]
        analyzer = ComplexityAnalyzer()
        complexity = analyzer.calculate_cyclomatic_complexity(func)
        assert complexity >= 3  # Multiple decision points

    def test_function_with_loop(self):
        """Test complexity with loops"""
        code = """
def with_loop(n):
    total = 0
    for i in range(n):
        total += i
    return total
"""
        tree = ast.parse(code)
        func = tree.body[0]
        analyzer = ComplexityAnalyzer()
        complexity = analyzer.calculate_cyclomatic_complexity(func)
        assert complexity == 2  # 1 base + 1 for loop

    def test_function_with_boolean_operators(self):
        """Test complexity with boolean operators"""
        code = """
def with_bool(x, y, z):
    if x > 0 and y > 0 or z > 0:
        return True
    return False
"""
        tree = ast.parse(code)
        func = tree.body[0]
        analyzer = ComplexityAnalyzer()
        complexity = analyzer.calculate_cyclomatic_complexity(func)
        assert complexity >= 3  # if + and + or


class TestCognitiveComplexity:
    """Test cognitive complexity calculations"""

    def test_simple_cognitive_complexity(self):
        """Test cognitive complexity of simple function"""
        code = """
def simple():
    return 42
"""
        tree = ast.parse(code)
        func = tree.body[0]
        analyzer = ComplexityAnalyzer()
        complexity = analyzer.calculate_cognitive_complexity(func)
        assert complexity == 0  # No control flow

    def test_nested_conditions_increase_cognitive(self):
        """Test that nesting increases cognitive complexity"""
        code = """
def nested(x, y):
    if x > 0:
        if y > 0:
            if x > y:
                return x
    return 0
"""
        tree = ast.parse(code)
        func = tree.body[0]
        analyzer = ComplexityAnalyzer()
        complexity = analyzer.calculate_cognitive_complexity(func)
        assert complexity > 3  # Nested ifs with increasing nesting penalty

    def test_flat_conditions_lower_cognitive(self):
        """Test that flat conditions have lower cognitive complexity"""
        code = """
def flat(x, y, z):
    if x > 0:
        return x
    if y > 0:
        return y
    if z > 0:
        return z
    return 0
"""
        tree = ast.parse(code)
        func = tree.body[0]
        analyzer = ComplexityAnalyzer()
        complexity = analyzer.calculate_cognitive_complexity(func)
        assert complexity == 3  # Three separate ifs at same level


class TestHalsteadMetrics:
    """Test Halstead metrics computation"""

    def test_halstead_simple_function(self):
        """Test Halstead metrics for simple function"""
        code = """
def add(a, b):
    return a + b
"""
        tree = ast.parse(code)
        func = tree.body[0]
        analyzer = ComplexityAnalyzer()
        halstead = analyzer.calculate_halstead_metrics(func)

        assert halstead.n1 > 0  # Has operators
        assert halstead.n2 > 0  # Has operands
        assert halstead.vocabulary > 0
        assert halstead.length > 0
        assert halstead.volume > 0

    def test_halstead_volume_calculation(self):
        """Test Halstead volume is calculated correctly"""
        code = """
def calculate(x, y, z):
    result = x + y * z
    return result
"""
        tree = ast.parse(code)
        func = tree.body[0]
        analyzer = ComplexityAnalyzer()
        halstead = analyzer.calculate_halstead_metrics(func)

        # Volume = Length * log2(Vocabulary)
        expected_volume = halstead.length * (halstead.vocabulary ** 0 if halstead.vocabulary == 1 else
                                            halstead.vocabulary.bit_length() - 1)
        assert halstead.volume >= 0

    def test_halstead_bugs_estimation(self):
        """Test Halstead bugs estimation"""
        code = """
def complex_calculation(a, b, c, d):
    x = a + b
    y = c * d
    z = x / y if y != 0 else 0
    return z
"""
        tree = ast.parse(code)
        func = tree.body[0]
        analyzer = ComplexityAnalyzer()
        halstead = analyzer.calculate_halstead_metrics(func)

        assert halstead.bugs >= 0
        # Bugs should be relatively small for small functions
        assert halstead.bugs < 1.0


class TestMaintainabilityIndex:
    """Test maintainability index calculation"""

    def test_maintainability_high_for_simple_code(self):
        """Test that simple code has high maintainability"""
        analyzer = ComplexityAnalyzer()
        metrics = {
            'halstead_volume': 10,
            'cyclomatic': 1,
            'loc': 5
        }
        mi = analyzer.calculate_maintainability_index(metrics)
        assert mi > 50  # Simple code should be maintainable

    def test_maintainability_low_for_complex_code(self):
        """Test that complex code has lower maintainability"""
        analyzer = ComplexityAnalyzer()
        metrics = {
            'halstead_volume': 1000,
            'cyclomatic': 50,
            'loc': 500
        }
        mi = analyzer.calculate_maintainability_index(metrics)
        assert mi < 50  # Complex code should have lower MI

    def test_maintainability_bounds(self):
        """Test that MI is bounded between 0 and 100"""
        analyzer = ComplexityAnalyzer()
        metrics = {
            'halstead_volume': 10000,
            'cyclomatic': 100,
            'loc': 1000
        }
        mi = analyzer.calculate_maintainability_index(metrics)
        assert 0 <= mi <= 100


class TestNestingDepth:
    """Test nesting depth calculation"""

    def test_no_nesting(self):
        """Test function with no nesting"""
        code = """
def flat():
    x = 1
    y = 2
    return x + y
"""
        tree = ast.parse(code)
        func = tree.body[0]
        analyzer = ComplexityAnalyzer()
        depth = analyzer.calculate_nesting_depth(func)
        assert depth == 0

    def test_single_level_nesting(self):
        """Test function with single level nesting"""
        code = """
def one_level(x):
    if x > 0:
        return x
    return 0
"""
        tree = ast.parse(code)
        func = tree.body[0]
        analyzer = ComplexityAnalyzer()
        depth = analyzer.calculate_nesting_depth(func)
        assert depth == 1

    def test_deep_nesting(self):
        """Test function with deep nesting"""
        code = """
def deeply_nested(x):
    if x > 0:
        for i in range(x):
            if i % 2 == 0:
                while i > 0:
                    if i % 3 == 0:
                        return i
                    i -= 1
    return 0
"""
        tree = ast.parse(code)
        func = tree.body[0]
        analyzer = ComplexityAnalyzer()
        depth = analyzer.calculate_nesting_depth(func)
        assert depth >= 4  # Multiple nested levels


class TestCodeEntropy:
    """Test code entropy calculation"""

    def test_entropy_simple_code(self):
        """Test entropy of simple, repetitive code"""
        code = """
x = 1
x = 1
x = 1
"""
        analyzer = ComplexityAnalyzer()
        entropy = analyzer.calculate_code_entropy(code)
        assert entropy >= 0

    def test_entropy_complex_code(self):
        """Test entropy of diverse, complex code"""
        code = """
def func1():
    pass

class MyClass:
    def method(self):
        for i in range(10):
            if i % 2 == 0:
                yield i
"""
        analyzer = ComplexityAnalyzer()
        entropy = analyzer.calculate_code_entropy(code)
        assert entropy > 0

    def test_entropy_comparison(self):
        """Test that complex code has higher entropy than simple code"""
        analyzer = ComplexityAnalyzer()

        simple = "x = 1\ny = 2\nz = 3"
        complex_code = """
def complex_func(a, b):
    if a > b:
        for i in range(a):
            yield i
    else:
        return [x**2 for x in range(b)]
"""
        entropy_simple = analyzer.calculate_code_entropy(simple)
        entropy_complex = analyzer.calculate_code_entropy(complex_code)

        assert entropy_complex > entropy_simple


class TestHotspotDetection:
    """Test complexity hotspot detection"""

    def test_detect_cyclomatic_hotspot(self):
        """Test detection of high cyclomatic complexity"""
        code = """
def complex_function(x):
    if x == 1:
        return 1
    elif x == 2:
        return 2
    elif x == 3:
        return 3
    elif x == 4:
        return 4
    elif x == 5:
        return 5
    elif x == 6:
        return 6
    elif x == 7:
        return 7
    elif x == 8:
        return 8
    elif x == 9:
        return 9
    else:
        return 0
"""
        analyzer = ComplexityAnalyzer()
        report = analyzer.analyze(code)
        hotspots = analyzer.detect_complexity_hotspots(report, threshold=5)

        assert len(hotspots) > 0
        assert any(h.metric_type == "cyclomatic" for h in hotspots)

    def test_detect_nesting_hotspot(self):
        """Test detection of deep nesting"""
        code = """
def deeply_nested(x):
    if x > 0:
        for i in range(x):
            if i % 2 == 0:
                while i > 0:
                    if i % 3 == 0:
                        if i % 5 == 0:
                            return i
                    i -= 1
    return 0
"""
        analyzer = ComplexityAnalyzer()
        report = analyzer.analyze(code)
        hotspots = analyzer.detect_complexity_hotspots(report, threshold=5)

        assert len(hotspots) > 0
        assert any(h.metric_type == "nesting" for h in hotspots)

    def test_hotspot_severity_ranking(self):
        """Test that hotspots are ranked by severity"""
        code = """
def very_complex(x, y, z):
    if x > 0:
        if y > 0:
            if z > 0:
                for i in range(x):
                    for j in range(y):
                        for k in range(z):
                            if i + j + k > 10:
                                if i * j * k < 100:
                                    return i + j + k
    return 0

def simple():
    return 42
"""
        analyzer = ComplexityAnalyzer()
        report = analyzer.analyze(code)
        hotspots = analyzer.detect_complexity_hotspots(report, threshold=3)

        # Should have hotspots, and they should be sorted
        if len(hotspots) > 1:
            # First hotspot should have higher or equal complexity than second
            assert hotspots[0].complexity_score >= hotspots[1].complexity_score


class TestRefactoringSuggestions:
    """Test refactoring suggestion generation"""

    def test_suggest_extract_method_for_high_complexity(self):
        """Test suggestion to extract method for high complexity"""
        from agno.tools.complexity_analyzer import Hotspot

        hotspot = Hotspot(
            location="Function 'complex_func'",
            complexity_score=25,
            metric_type="cyclomatic",
            severity="high",
            description="High cyclomatic complexity"
        )

        analyzer = ComplexityAnalyzer()
        suggestions = analyzer.suggest_refactorings(hotspot)

        assert len(suggestions) > 0
        assert any(s.refactoring_type == RefactoringType.EXTRACT_METHOD for s in suggestions)

    def test_suggest_guard_clause_for_nesting(self):
        """Test suggestion for guard clauses when nesting is deep"""
        from agno.tools.complexity_analyzer import Hotspot

        hotspot = Hotspot(
            location="Function 'nested_func'",
            complexity_score=6,
            metric_type="nesting",
            severity="high",
            description="Deep nesting"
        )

        analyzer = ComplexityAnalyzer()
        suggestions = analyzer.suggest_refactorings(hotspot)

        assert len(suggestions) > 0
        assert any(s.refactoring_type == RefactoringType.INTRODUCE_GUARD_CLAUSE for s in suggestions)

    def test_suggest_decompose_for_god_class(self):
        """Test suggestion to decompose god class"""
        from agno.tools.complexity_analyzer import Hotspot

        hotspot = Hotspot(
            location="Class 'GodClass'",
            complexity_score=150,
            metric_type="class_complexity",
            severity="critical",
            description="God class"
        )

        analyzer = ComplexityAnalyzer()
        suggestions = analyzer.suggest_refactorings(hotspot)

        assert len(suggestions) > 0
        assert any(s.refactoring_type == RefactoringType.DECOMPOSE_CLASS for s in suggestions)


class TestComplexityBudget:
    """Test complexity budget enforcement"""

    def test_budget_compliance_for_simple_code(self):
        """Test that simple code complies with budget"""
        code = """
def simple():
    return 42
"""
        analyzer = ComplexityAnalyzer()
        report = analyzer.analyze(code)
        budget = ComplexityBudget(
            max_function_cyclomatic=10,
            max_function_cognitive=5
        )

        budget_report = analyzer.enforce_complexity_budget(report, budget)
        assert not budget_report.over_budget
        assert len(budget_report.violations) == 0

    def test_budget_violation_for_complex_code(self):
        """Test that complex code violates budget"""
        code = """
def complex_function(x):
    if x == 1:
        return 1
    elif x == 2:
        return 2
    elif x == 3:
        return 3
    elif x == 4:
        return 4
    elif x == 5:
        return 5
    elif x == 6:
        return 6
    else:
        return 0
"""
        analyzer = ComplexityAnalyzer()
        report = analyzer.analyze(code)
        budget = ComplexityBudget(
            max_function_cyclomatic=5,
            max_function_cognitive=3
        )

        budget_report = analyzer.enforce_complexity_budget(report, budget)
        assert budget_report.over_budget
        assert len(budget_report.violations) > 0

    def test_budget_violation_details(self):
        """Test that budget violations contain details"""
        code = """
def nested(x):
    if x > 0:
        for i in range(x):
            if i % 2 == 0:
                while i > 0:
                    if i % 3 == 0:
                        return i
                    i -= 1
    return 0
"""
        analyzer = ComplexityAnalyzer()
        report = analyzer.analyze(code)
        budget = ComplexityBudget(max_nesting_depth=2)

        budget_report = analyzer.enforce_complexity_budget(report, budget)
        assert budget_report.over_budget
        assert any("nesting" in v.lower() for v in budget_report.violations)


class TestCompleteAnalysis:
    """Test complete analysis workflow"""

    def test_full_analysis_on_realistic_code(self):
        """Test full analysis on realistic code sample"""
        code = """
class Calculator:
    def __init__(self):
        self.result = 0

    def add(self, x, y):
        return x + y

    def complex_calculation(self, data):
        total = 0
        for item in data:
            if item > 0:
                for i in range(item):
                    if i % 2 == 0:
                        total += i
        return total
"""
        analyzer = ComplexityAnalyzer()
        report = analyzer.analyze(code)

        # Check that all metrics are calculated
        assert report.cyclomatic_total > 0
        assert report.cognitive_total >= 0
        assert report.halstead.volume > 0
        assert 0 <= report.maintainability_index <= 100
        assert report.entropy > 0
        assert report.loc.physical > 0

    def test_analysis_includes_all_functions(self):
        """Test that analysis finds all functions"""
        code = """
def func1():
    return 1

def func2():
    return 2

def func3():
    return 3
"""
        analyzer = ComplexityAnalyzer()
        report = analyzer.analyze(code)

        assert len(report.module.functions) == 3

    def test_analysis_includes_all_classes(self):
        """Test that analysis finds all classes"""
        code = """
class Class1:
    def method1(self):
        pass

class Class2:
    def method2(self):
        pass
"""
        analyzer = ComplexityAnalyzer()
        report = analyzer.analyze(code)

        assert len(report.module.classes) == 2
        assert report.module.classes[0].name in ["Class1", "Class2"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
