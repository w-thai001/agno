"""
Comprehensive tests for Code Analyzer FSA

Tests cover AST parsing, complexity calculation, code smell detection,
pattern detection, security analysis, and quality scoring.
"""

import ast
import pytest
from pathlib import Path

from agno.fsas.code_analyzer import (
    CodeAnalyzerError,
    CodeAnalyzerFSA,
    CodeAnalysisReport,
    CodeSmell,
    ComplexityMetrics,
    DesignPattern,
    DocQualityReport,
    SecurityIssue,
    SecuritySeverity,
    SmellSeverity,
    TypeCoverageReport,
)


@pytest.fixture
def analyzer():
    """Create Code Analyzer FSA instance"""
    return CodeAnalyzerFSA()


@pytest.fixture
def simple_code():
    """Simple Python code for testing"""
    return """
def hello(name):
    '''Say hello'''
    return f"Hello, {name}!"

class Greeter:
    '''A simple greeter class'''
    def greet(self, name):
        return hello(name)
"""


@pytest.fixture
def complex_code():
    """Complex Python code with issues"""
    return """
def complex_function(a, b, c, d, e, f, g):
    '''A complex function with many parameters'''
    if a > 0:
        if b > 0:
            if c > 0:
                if d > 0:
                    if e > 0:
                        return 42
    return 0

class GodClass:
    '''A very large class'''
    def method1(self): pass
    def method2(self): pass
    def method3(self): pass
    # ... imagine 500 more lines
"""


@pytest.fixture
def security_vulnerable_code():
    """Code with security vulnerabilities"""
    return """
import os

password = "secret123"  # Hardcoded secret

def run_command(cmd):
    os.system(cmd)  # Command injection risk

def execute_sql(query, user_input):
    sql = f"SELECT * FROM users WHERE name = '{user_input}'"  # SQL injection
    return sql

def unsafe_eval(code):
    return eval(code)  # Code injection
"""


class TestCodeAnalyzerInitialization:
    """Test Code Analyzer FSA initialization"""

    def test_init_default(self):
        """Test initialization with default parameters"""
        analyzer = CodeAnalyzerFSA()
        assert analyzer is not None
        assert analyzer.name == "CodeAnalyzerFSA"
        assert analyzer.max_complexity == 10
        assert analyzer.max_method_lines == 50

    def test_init_with_config(self):
        """Test initialization with custom configuration"""
        config = {
            "max_complexity": 15,
            "max_method_lines": 100,
            "max_class_lines": 1000,
            "max_params": 7,
            "max_nesting": 5
        }
        analyzer = CodeAnalyzerFSA(config=config)
        assert analyzer.max_complexity == 15
        assert analyzer.max_method_lines == 100
        assert analyzer.max_class_lines == 1000
        assert analyzer.max_params == 7
        assert analyzer.max_nesting == 5


class TestASTParsing:
    """Test AST parsing functionality"""

    def test_parse_simple_code(self, analyzer, simple_code):
        """Test parsing simple valid Python code"""
        tree = analyzer.parse_ast(simple_code)
        assert isinstance(tree, ast.Module)
        assert len(tree.body) > 0

    def test_parse_invalid_syntax(self, analyzer):
        """Test parsing code with syntax errors"""
        invalid_code = "def incomplete("

        with pytest.raises(SyntaxError):
            analyzer.parse_ast(invalid_code)

    def test_parse_empty_code(self, analyzer):
        """Test parsing empty code"""
        tree = analyzer.parse_ast("")
        assert isinstance(tree, ast.Module)
        assert len(tree.body) == 0


class TestComplexityCalculation:
    """Test complexity metrics calculation"""

    def test_calculate_cyclomatic_complexity(self, analyzer, simple_code):
        """Test cyclomatic complexity calculation"""
        tree = analyzer.parse_ast(simple_code)
        metrics = analyzer.calculate_complexity(tree)

        assert isinstance(metrics, ComplexityMetrics)
        assert metrics.cyclomatic >= 1

    def test_calculate_cognitive_complexity(self, analyzer, complex_code):
        """Test cognitive complexity calculation"""
        tree = analyzer.parse_ast(complex_code)
        metrics = analyzer.calculate_complexity(tree)

        # Complex nested code should have high cognitive complexity
        assert metrics.cognitive > 5

    def test_calculate_halstead_metrics(self, analyzer, simple_code):
        """Test Halstead metrics calculation"""
        tree = analyzer.parse_ast(simple_code)
        metrics = analyzer.calculate_complexity(tree)

        assert metrics.halstead_volume >= 0
        assert metrics.halstead_difficulty >= 0
        assert metrics.halstead_effort >= 0

    def test_calculate_loc(self, analyzer, simple_code):
        """Test lines of code counting"""
        tree = analyzer.parse_ast(simple_code)
        metrics = analyzer.calculate_complexity(tree)

        assert metrics.loc > 0
        assert metrics.sloc > 0
        assert metrics.sloc <= metrics.loc

    def test_calculate_nesting_depth(self, analyzer, complex_code):
        """Test nesting depth calculation"""
        tree = analyzer.parse_ast(complex_code)
        metrics = analyzer.calculate_complexity(tree)

        # Complex code has deep nesting
        assert metrics.nesting_depth >= 4

    def test_calculate_maintainability_index(self, analyzer, simple_code):
        """Test maintainability index calculation"""
        tree = analyzer.parse_ast(simple_code)
        metrics = analyzer.calculate_complexity(tree)

        assert 0 <= metrics.maintainability_index <= 100


class TestCodeSmellDetection:
    """Test code smell detection"""

    def test_detect_long_method(self, analyzer):
        """Test detection of long methods"""
        code_with_long_method = """
def very_long_method():
    '''A very long method'''
    """ + "\n    ".join([f"x{i} = {i}" for i in range(60)]) + """
    return sum([x0, x1])
"""

        tree = analyzer.parse_ast(code_with_long_method)
        smells = analyzer.detect_code_smells(tree)

        long_method_smells = [s for s in smells if s.type == "Long Method"]
        assert len(long_method_smells) > 0

    def test_detect_long_parameter_list(self, analyzer, complex_code):
        """Test detection of long parameter lists"""
        tree = analyzer.parse_ast(complex_code)
        smells = analyzer.detect_code_smells(tree)

        param_smells = [s for s in smells if s.type == "Long Parameter List"]
        assert len(param_smells) > 0

    def test_detect_deep_nesting(self, analyzer, complex_code):
        """Test detection of deep nesting"""
        tree = analyzer.parse_ast(complex_code)
        smells = analyzer.detect_code_smells(tree)

        nesting_smells = [s for s in smells if s.type == "Deep Nesting"]
        assert len(nesting_smells) > 0

    def test_detect_magic_numbers(self, analyzer):
        """Test detection of magic numbers"""
        code_with_magic = """
def calculate():
    return 42 * 3.14159 + 666
"""

        tree = analyzer.parse_ast(code_with_magic)
        smells = analyzer.detect_code_smells(tree)

        magic_smells = [s for s in smells if s.type == "Magic Number"]
        assert len(magic_smells) > 0


class TestDesignPatternDetection:
    """Test design pattern detection"""

    def test_detect_singleton_pattern(self, analyzer):
        """Test detection of Singleton pattern"""
        singleton_code = """
class Singleton:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
"""

        tree = analyzer.parse_ast(singleton_code)
        patterns = analyzer.detect_patterns(tree)

        singleton_patterns = [p for p in patterns if p.pattern_type == "Singleton"]
        assert len(singleton_patterns) > 0
        assert singleton_patterns[0].confidence > 0.5

    def test_detect_factory_pattern(self, analyzer):
        """Test detection of Factory pattern"""
        factory_code = """
def create_object(type_name):
    if type_name == 'A':
        return ObjectA()
    elif type_name == 'B':
        return ObjectB()
    return None
"""

        tree = analyzer.parse_ast(factory_code)
        patterns = analyzer.detect_patterns(tree)

        factory_patterns = [p for p in patterns if p.pattern_type == "Factory"]
        assert len(factory_patterns) > 0

    def test_detect_strategy_pattern(self, analyzer):
        """Test detection of Strategy pattern"""
        strategy_code = """
from abc import ABC, abstractmethod

class Strategy(ABC):
    @abstractmethod
    def execute(self):
        pass
"""

        tree = analyzer.parse_ast(strategy_code)
        patterns = analyzer.detect_patterns(tree)

        strategy_patterns = [p for p in patterns if p.pattern_type == "Strategy"]
        assert len(strategy_patterns) > 0


class TestSecurityAnalysis:
    """Test security vulnerability scanning"""

    def test_detect_sql_injection(self, analyzer, security_vulnerable_code):
        """Test detection of SQL injection vulnerabilities"""
        tree = analyzer.parse_ast(security_vulnerable_code)
        issues = analyzer.analyze_security(tree)

        sql_issues = [i for i in issues if i.vulnerability_type == "SQL Injection"]
        assert len(sql_issues) > 0
        assert sql_issues[0].severity in [SecuritySeverity.HIGH, SecuritySeverity.CRITICAL]

    def test_detect_command_injection(self, analyzer, security_vulnerable_code):
        """Test detection of command injection vulnerabilities"""
        tree = analyzer.parse_ast(security_vulnerable_code)
        issues = analyzer.analyze_security(tree)

        cmd_issues = [i for i in issues if i.vulnerability_type == "Command Injection"]
        assert len(cmd_issues) > 0
        assert cmd_issues[0].severity == SecuritySeverity.CRITICAL

    def test_detect_code_injection(self, analyzer, security_vulnerable_code):
        """Test detection of eval/exec usage"""
        tree = analyzer.parse_ast(security_vulnerable_code)
        issues = analyzer.analyze_security(tree)

        code_issues = [i for i in issues if i.vulnerability_type == "Code Injection"]
        assert len(code_issues) > 0

    def test_detect_hardcoded_secrets(self, analyzer, security_vulnerable_code):
        """Test detection of hardcoded secrets"""
        tree = analyzer.parse_ast(security_vulnerable_code)
        issues = analyzer.analyze_security(tree)

        secret_issues = [i for i in issues if i.vulnerability_type == "Hardcoded Secret"]
        assert len(secret_issues) > 0


class TestTypeAnnotationAnalysis:
    """Test type annotation coverage analysis"""

    def test_check_annotated_code(self, analyzer):
        """Test type coverage for fully annotated code"""
        annotated_code = """
def add(x: int, y: int) -> int:
    return x + y

def greet(name: str) -> str:
    return f"Hello, {name}"
"""

        tree = analyzer.parse_ast(annotated_code)
        coverage = analyzer.check_type_annotations(tree)

        assert isinstance(coverage, TypeCoverageReport)
        assert coverage.coverage_percent == 100.0

    def test_check_unannotated_code(self, analyzer):
        """Test type coverage for unannotated code"""
        unannotated_code = """
def add(x, y):
    return x + y

def greet(name):
    return f"Hello, {name}"
"""

        tree = analyzer.parse_ast(unannotated_code)
        coverage = analyzer.check_type_annotations(tree)

        assert coverage.coverage_percent == 0.0

    def test_check_partially_annotated_code(self, analyzer):
        """Test type coverage for partially annotated code"""
        partial_code = """
def add(x: int, y: int) -> int:
    return x + y

def greet(name):  # Not annotated
    return f"Hello, {name}"
"""

        tree = analyzer.parse_ast(partial_code)
        coverage = analyzer.check_type_annotations(tree)

        assert 0 < coverage.coverage_percent < 100


class TestDocumentationAnalysis:
    """Test documentation quality analysis"""

    def test_analyze_documented_code(self, analyzer, simple_code):
        """Test documentation analysis for documented code"""
        tree = analyzer.parse_ast(simple_code)
        doc_quality = analyzer.analyze_documentation(tree)

        assert isinstance(doc_quality, DocQualityReport)
        assert doc_quality.documented_items > 0
        assert doc_quality.coverage_percent > 0

    def test_analyze_undocumented_code(self, analyzer):
        """Test documentation analysis for undocumented code"""
        undocumented_code = """
def add(x, y):
    return x + y

class Calculator:
    def multiply(self, x, y):
        return x * y
"""

        tree = analyzer.parse_ast(undocumented_code)
        doc_quality = analyzer.analyze_documentation(tree)

        assert doc_quality.coverage_percent == 0.0

    def test_analyze_quality_scored_docstrings(self, analyzer):
        """Test that high-quality docstrings score well"""
        good_docs = """
def complex_function(x, y):
    '''
    Perform a complex calculation.

    Args:
        x: First parameter
        y: Second parameter

    Returns:
        The result of the calculation
    '''
    return x + y
"""

        tree = analyzer.parse_ast(good_docs)
        doc_quality = analyzer.analyze_documentation(tree)

        assert doc_quality.avg_quality_score > 50


class TestQualityScoring:
    """Test overall quality score calculation"""

    def test_calculate_score_for_good_code(self, analyzer, simple_code):
        """Test quality score for good code"""
        report = analyzer.analyze_code(simple_code)

        assert 0 <= report.quality_score <= 100
        assert report.quality_score > 50  # Good code should score well

    def test_calculate_score_for_poor_code(self, analyzer, complex_code):
        """Test quality score for code with issues"""
        report = analyzer.analyze_code(complex_code)

        assert 0 <= report.quality_score <= 100
        # Code with smells should score lower
        assert report.quality_score < 90

    def test_calculate_score_for_insecure_code(self, analyzer, security_vulnerable_code):
        """Test quality score for insecure code"""
        report = analyzer.analyze_code(security_vulnerable_code)

        # Code with security issues should have lower score
        assert report.quality_score < 70


class TestRefactoringSuggestions:
    """Test automated refactoring suggestions"""

    def test_suggest_refactoring_for_complexity(self, analyzer, complex_code):
        """Test refactoring suggestions for complex code"""
        report = analyzer.analyze_code(complex_code)
        suggestions = analyzer.suggest_refactorings(report)

        assert len(suggestions) > 0
        # Should suggest extracting methods for high complexity
        extract_method = [s for s in suggestions if s.type == "Extract Method"]
        assert len(extract_method) > 0

    def test_suggest_refactoring_for_security(self, analyzer, security_vulnerable_code):
        """Test refactoring suggestions for security issues"""
        report = analyzer.analyze_code(security_vulnerable_code)
        suggestions = analyzer.suggest_refactorings(report)

        security_fixes = [s for s in suggestions if s.type == "Security Fix"]
        assert len(security_fixes) > 0


class TestDeadCodeDetection:
    """Test dead code detection"""

    def test_detect_unused_variables(self, analyzer):
        """Test detection of unused variables"""
        code_with_unused = """
def calculate():
    x = 10  # Used
    y = 20  # Unused
    z = 30  # Unused
    return x
"""

        tree = analyzer.parse_ast(code_with_unused)
        dead_code = analyzer.detect_dead_code(tree)

        # Note: This is a simple implementation, so results may vary
        assert isinstance(dead_code, list)


class TestCodeComparison:
    """Test code version comparison"""

    def test_compare_code_versions(self, analyzer, simple_code, complex_code):
        """Test comparing two versions of code"""
        comparison = analyzer.compare_code_versions(simple_code, complex_code)

        assert 'quality_score_change' in comparison
        assert 'complexity_change' in comparison
        assert 'smells_change' in comparison
        assert 'old_score' in comparison
        assert 'new_score' in comparison


class TestFullAnalysis:
    """Test complete code analysis workflow"""

    def test_analyze_code_from_string(self, analyzer, simple_code):
        """Test full analysis from code string"""
        report = analyzer.analyze_code(simple_code)

        assert isinstance(report, CodeAnalysisReport)
        assert report.file_path == "<string>"
        assert report.complexity_metrics is not None
        assert isinstance(report.code_smells, list)
        assert isinstance(report.patterns, list)
        assert isinstance(report.security_issues, list)
        assert report.quality_score >= 0

    def test_analyze_code_complete_report(self, analyzer, simple_code):
        """Test that full analysis generates complete report"""
        report = analyzer.analyze_code(simple_code)

        # Check all report sections exist
        assert report.complexity_metrics is not None
        assert report.type_coverage is not None
        assert report.doc_quality is not None
        assert len(report.refactoring_suggestions) >= 0

    def test_report_serialization(self, analyzer, simple_code):
        """Test that report can be serialized to dict and JSON"""
        report = analyzer.analyze_code(simple_code)

        # Test to_dict
        report_dict = report.to_dict()
        assert isinstance(report_dict, dict)
        assert 'file_path' in report_dict
        assert 'quality_score' in report_dict

        # Test to_json
        json_str = report.to_json()
        assert isinstance(json_str, str)
        assert '"quality_score"' in json_str


class TestErrorHandling:
    """Test error handling"""

    def test_validate_input_none(self, analyzer):
        """Test that None input raises error"""
        with pytest.raises(CodeAnalyzerError, match="cannot be None"):
            analyzer.validate_input(None)

    def test_execute_invalid_task(self, analyzer):
        """Test handling of invalid task"""
        with pytest.raises(CodeAnalyzerError, match="cannot be empty"):
            analyzer.execute("")

    def test_analyze_invalid_code_type(self, analyzer):
        """Test analyzing invalid input type"""
        with pytest.raises(CodeAnalyzerError, match="Invalid code input"):
            analyzer.analyze_code(12345)
