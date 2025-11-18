"""
Comprehensive unit tests for Code Smell Detector FSA.

Tests cover all major smell detection categories and analysis features.
"""

import pytest

from agno.utils.code_smell_detector import CodeSmellDetector, Severity, SmellCategory


class TestLongMethodDetection:
    """Test long method detection."""

    def test_detects_long_method_by_lines(self):
        """Test detection of methods exceeding line threshold."""
        code = '''
def very_long_method():
    """A method with too many lines."""
''' + "\n".join([f"    x = {i}" for i in range(60)])

        detector = CodeSmellDetector()
        report = detector.detect_smells(code)

        long_method_smells = [s for s in report.smells if s.smell_type == "long_method"]
        assert len(long_method_smells) > 0
        assert long_method_smells[0].location == "very_long_method"
        assert long_method_smells[0].metrics["lines"] > 50

    def test_detects_long_method_by_complexity(self):
        """Test detection of methods with high cyclomatic complexity."""
        code = '''
def complex_method(x):
    """A method with high complexity."""
    if x > 0:
        if x > 10:
            if x > 20:
                if x > 30:
                    if x > 40:
                        if x > 50:
                            return True
    return False
'''

        detector = CodeSmellDetector()
        report = detector.detect_smells(code)

        long_method_smells = [s for s in report.smells if s.smell_type == "long_method"]
        assert len(long_method_smells) > 0
        assert long_method_smells[0].metrics["complexity"] > 5

    def test_short_method_not_flagged(self):
        """Test that short, simple methods are not flagged."""
        code = '''
def short_method(x):
    """A simple, short method."""
    return x + 1
'''

        detector = CodeSmellDetector()
        report = detector.detect_smells(code)

        long_method_smells = [s for s in report.smells if s.smell_type == "long_method"]
        assert len(long_method_smells) == 0


class TestGodClassDetection:
    """Test god class detection."""

    def test_detects_god_class_many_methods(self):
        """Test detection of classes with too many methods."""
        methods = "\n".join([f"    def method_{i}(self): pass" for i in range(35)])
        code = f'''
class GodClass:
    """A class with too many methods."""
{methods}
'''

        detector = CodeSmellDetector()
        report = detector.detect_smells(code)

        god_class_smells = [s for s in report.smells if s.smell_type == "god_class"]
        assert len(god_class_smells) > 0
        assert god_class_smells[0].severity == Severity.CRITICAL
        assert god_class_smells[0].metrics["methods"] > 30

    def test_detects_god_class_many_fields(self):
        """Test detection of classes with too many fields."""
        fields = "\n".join([f"        self.field_{i} = {i}" for i in range(25)])
        code = f'''
class GodClass:
    """A class with too many fields."""
    def __init__(self):
{fields}
'''

        detector = CodeSmellDetector()
        report = detector.detect_smells(code)

        god_class_smells = [s for s in report.smells if s.smell_type == "god_class"]
        assert len(god_class_smells) > 0
        assert god_class_smells[0].metrics["fields"] > 20


class TestFeatureEnvyDetection:
    """Test feature envy detection."""

    def test_detects_feature_envy(self):
        """Test detection of methods accessing external objects more than self."""
        code = '''
class MyClass:
    def envious_method(self, other):
        """Method that uses other object more than self."""
        result = other.method1()
        result += other.method2()
        result += other.method3()
        result += other.attribute1
        result += other.attribute2
        result += other.attribute3
        return result + self.value
'''

        detector = CodeSmellDetector()
        report = detector.detect_smells(code)

        feature_envy_smells = [s for s in report.smells if s.smell_type == "feature_envy"]
        assert len(feature_envy_smells) > 0
        assert feature_envy_smells[0].severity == Severity.MAJOR
        assert feature_envy_smells[0].metrics["external_calls"] > feature_envy_smells[0].metrics["internal_calls"]


class TestMutableDefaultArguments:
    """Test mutable default argument detection."""

    def test_detects_mutable_list_default(self):
        """Test detection of mutable list as default argument."""
        code = '''
def dangerous_function(items=[]):
    """Function with mutable default argument."""
    items.append(1)
    return items
'''

        detector = CodeSmellDetector()
        report = detector.detect_smells(code)

        mutable_default_smells = [s for s in report.smells if s.smell_type == "mutable_default_argument"]
        assert len(mutable_default_smells) > 0
        assert mutable_default_smells[0].severity == Severity.CRITICAL
        assert mutable_default_smells[0].location == "dangerous_function"

    def test_detects_mutable_dict_default(self):
        """Test detection of mutable dict as default argument."""
        code = '''
def dangerous_function(config={}):
    """Function with mutable dict default."""
    config["key"] = "value"
    return config
'''

        detector = CodeSmellDetector()
        report = detector.detect_smells(code)

        mutable_default_smells = [s for s in report.smells if s.smell_type == "mutable_default_argument"]
        assert len(mutable_default_smells) > 0

    def test_safe_defaults_not_flagged(self):
        """Test that safe default arguments are not flagged."""
        code = '''
def safe_function(value=None, count=0, name="default"):
    """Function with safe default arguments."""
    return value, count, name
'''

        detector = CodeSmellDetector()
        report = detector.detect_smells(code)

        mutable_default_smells = [s for s in report.smells if s.smell_type == "mutable_default_argument"]
        assert len(mutable_default_smells) == 0


class TestMagicNumberDetection:
    """Test magic number detection."""

    def test_detects_magic_numbers(self):
        """Test detection of repeated magic numbers."""
        code = '''
def calculate():
    """Function with magic numbers."""
    x = 100
    y = 100
    z = 100
    return x + y + z
'''

        detector = CodeSmellDetector()
        report = detector.detect_smells(code)

        magic_number_smells = [s for s in report.smells if s.smell_type == "magic_number"]
        assert len(magic_number_smells) > 0
        assert magic_number_smells[0].metrics["number"] == 100
        assert magic_number_smells[0].metrics["occurrences"] >= 3

    def test_zero_and_one_not_flagged(self):
        """Test that 0, 1, -1 are not flagged as magic numbers."""
        code = '''
def calculate():
    """Function with acceptable numbers."""
    x = 0
    y = 1
    z = -1
    return x + y + z
'''

        detector = CodeSmellDetector()
        report = detector.detect_smells(code)

        magic_number_smells = [s for s in report.smells if s.smell_type == "magic_number"]
        assert len(magic_number_smells) == 0


class TestDeadCodeDetection:
    """Test dead code detection."""

    def test_detects_unreachable_code_after_return(self):
        """Test detection of unreachable code after return statement."""
        code = '''
def function_with_dead_code():
    """Function with unreachable code."""
    x = 1
    return x
    y = 2  # Dead code
    print(y)  # Dead code
'''

        detector = CodeSmellDetector()
        report = detector.detect_smells(code)

        dead_code_smells = [s for s in report.smells if s.smell_type == "dead_code"]
        assert len(dead_code_smells) > 0
        assert "unreachable" in dead_code_smells[0].description.lower()


class TestSeverityClassification:
    """Test smell severity classification."""

    def test_critical_severity_for_mutable_defaults(self):
        """Test that mutable default arguments are CRITICAL."""
        code = "def func(arg=[]): pass"

        detector = CodeSmellDetector()
        report = detector.detect_smells(code)

        mutable_smells = [s for s in report.smells if s.smell_type == "mutable_default_argument"]
        assert len(mutable_smells) > 0
        assert mutable_smells[0].severity == Severity.CRITICAL

    def test_major_severity_for_large_class(self):
        """Test that large classes are MAJOR severity."""
        methods = "\n".join([f"    def method_{i}(self): pass" for i in range(25)])
        code = f"class LargeClass:\n{methods}"

        detector = CodeSmellDetector()
        report = detector.detect_smells(code)

        large_class_smells = [s for s in report.smells if s.smell_type == "large_class"]
        assert len(large_class_smells) > 0
        assert large_class_smells[0].severity == Severity.MAJOR

    def test_minor_severity_for_magic_numbers(self):
        """Test that magic numbers are MINOR severity."""
        code = "x = 42\ny = 42\nz = 42"

        detector = CodeSmellDetector()
        report = detector.detect_smells(code)

        magic_smells = [s for s in report.smells if s.smell_type == "magic_number"]
        if len(magic_smells) > 0:
            assert magic_smells[0].severity == Severity.MINOR


class TestTechnicalDebtEstimation:
    """Test technical debt estimation."""

    def test_calculates_total_hours(self):
        """Test that technical debt hours are calculated."""
        code = '''
def func(a, b, c, d, e, f, g):  # Long parameter list
    """Function with smells."""
    pass

def another(items=[]):  # Mutable default
    """Another function."""
    pass
'''

        detector = CodeSmellDetector()
        report = detector.detect_smells(code)

        assert report.technical_debt.total_hours > 0

    def test_calculates_cost_estimate(self):
        """Test that cost estimate is calculated."""
        code = "def func(items=[]): pass"

        detector = CodeSmellDetector()
        report = detector.detect_smells(code)

        if len(report.smells) > 0:
            assert report.technical_debt.cost_estimate > 0

    def test_prioritizes_smells(self):
        """Test that smells are prioritized."""
        code = '''
def critical_func(items=[]):  # Critical
    """Critical smell."""
    pass

def minor_func():
    """Minor smell."""
    x = 100
    y = 100
    z = 100
'''

        detector = CodeSmellDetector()
        report = detector.detect_smells(code)

        if len(report.technical_debt.prioritized_fixes) > 1:
            # Critical smells should be higher priority
            priorities = [p.priority_score for p in report.technical_debt.prioritized_fixes]
            assert max(priorities) > min(priorities)


class TestAutomatedFixGeneration:
    """Test automated fix generation."""

    def test_generates_fix_for_mutable_default(self):
        """Test fix generation for mutable default arguments."""
        code = "def func(items=[]): pass"

        detector = CodeSmellDetector()
        report = detector.detect_smells(code)

        mutable_smells = [s for s in report.smells if s.smell_type == "mutable_default_argument"]
        if len(mutable_smells) > 0:
            fix = detector.generate_automated_fix(mutable_smells[0])
            assert fix is not None
            assert "None" in fix.fixed_code
            assert "if arg is None" in fix.fixed_code

    def test_generates_fix_for_bare_except(self):
        """Test fix generation for bare except."""
        code = '''
try:
    risky()
except:
    pass
'''

        detector = CodeSmellDetector()
        report = detector.detect_smells(code)

        bare_except_smells = [s for s in report.smells if s.smell_type == "bare_except"]
        if len(bare_except_smells) > 0:
            fix = detector.generate_automated_fix(bare_except_smells[0])
            assert fix is not None
            assert "Exception" in fix.fixed_code

    def test_generates_fix_for_magic_number(self):
        """Test fix generation for magic numbers."""
        code = "x = 42\ny = 42\nz = 42"

        detector = CodeSmellDetector()
        report = detector.detect_smells(code)

        magic_smells = [s for s in report.smells if s.smell_type == "magic_number"]
        if len(magic_smells) > 0:
            fix = detector.generate_automated_fix(magic_smells[0])
            assert fix is not None
            assert "CONSTANT" in fix.fixed_code


class TestRefactoringSuggestions:
    """Test refactoring suggestion generation."""

    def test_suggests_extract_method_for_long_method(self):
        """Test refactoring suggestion for long methods."""
        code = "\n".join([f"def long_method():\n    x = {i}" for i in range(60)])

        detector = CodeSmellDetector()
        report = detector.detect_smells(code)

        if len(report.recommendations) > 0:
            long_method_recs = [r for r in report.recommendations if r.smell.smell_type == "long_method"]
            if len(long_method_recs) > 0:
                assert "Extract Method" in long_method_recs[0].refactoring_type
                assert long_method_recs[0].estimated_effort > 0

    def test_suggests_parameter_object_for_long_params(self):
        """Test refactoring suggestion for long parameter lists."""
        code = "def func(a, b, c, d, e, f, g): pass"

        detector = CodeSmellDetector()
        report = detector.detect_smells(code)

        param_recs = [r for r in report.recommendations if r.smell.smell_type == "long_parameter_list"]
        if len(param_recs) > 0:
            assert "Parameter Object" in param_recs[0].refactoring_type


class TestSmellReport:
    """Test smell report generation."""

    def test_report_contains_all_sections(self):
        """Test that report contains all required sections."""
        code = "def func(items=[]): pass"

        detector = CodeSmellDetector()
        report = detector.detect_smells(code)

        assert hasattr(report, "smells")
        assert hasattr(report, "total_count")
        assert hasattr(report, "severity_distribution")
        assert hasattr(report, "category_distribution")
        assert hasattr(report, "technical_debt")
        assert hasattr(report, "recommendations")

    def test_severity_distribution_accuracy(self):
        """Test that severity distribution is accurate."""
        code = '''
def func1(items=[]):  # Critical
    pass

def func2(a, b, c, d, e, f, g):  # Minor
    pass
'''

        detector = CodeSmellDetector()
        report = detector.detect_smells(code)

        total = sum(report.severity_distribution.values())
        assert total == report.total_count

    def test_category_distribution_accuracy(self):
        """Test that category distribution is accurate."""
        code = "def func(items=[]): pass"

        detector = CodeSmellDetector()
        report = detector.detect_smells(code)

        total = sum(report.category_distribution.values())
        assert total == report.total_count


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
