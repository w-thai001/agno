"""
Complexity Analyzer FSA - Comprehensive Code Complexity Measurement Tool

This module provides advanced code complexity analysis including cyclomatic complexity,
cognitive complexity, Halstead metrics, maintainability index, code entropy, and
actionable refactoring recommendations.
"""

import ast
import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class ComplexityLevel(Enum):
    """Classification of complexity levels"""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    VERY_COMPLEX = "very_complex"


class RefactoringType(Enum):
    """Types of refactoring suggestions"""
    EXTRACT_METHOD = "extract_method"
    SIMPLIFY_CONDITIONAL = "simplify_conditional"
    SPLIT_FUNCTION = "split_function"
    DECOMPOSE_CLASS = "decompose_class"
    INTRODUCE_GUARD_CLAUSE = "introduce_guard_clause"
    STRATEGY_PATTERN = "strategy_pattern"
    REDUCE_NESTING = "reduce_nesting"
    SIMPLIFY_LOGIC = "simplify_logic"


@dataclass
class HalsteadMetrics:
    """Halstead software science metrics"""
    n1: int = 0  # Distinct operators
    n2: int = 0  # Distinct operands
    N1: int = 0  # Total operators
    N2: int = 0  # Total operands

    @property
    def vocabulary(self) -> int:
        """Program vocabulary: n = n1 + n2"""
        return self.n1 + self.n2

    @property
    def length(self) -> int:
        """Program length: N = N1 + N2"""
        return self.N1 + self.N2

    @property
    def volume(self) -> float:
        """Program volume: V = N * log2(n)"""
        if self.vocabulary == 0:
            return 0.0
        return self.length * math.log2(self.vocabulary)

    @property
    def difficulty(self) -> float:
        """Program difficulty: D = (n1/2) * (N2/n2)"""
        if self.n2 == 0:
            return 0.0
        return (self.n1 / 2) * (self.N2 / self.n2)

    @property
    def effort(self) -> float:
        """Program effort: E = D * V"""
        return self.difficulty * self.volume

    @property
    def time(self) -> float:
        """Time to program: T = E / 18 (seconds)"""
        return self.effort / 18

    @property
    def bugs(self) -> float:
        """Estimated bugs: B = V / 3000"""
        return self.volume / 3000


@dataclass
class LOCMetrics:
    """Lines of Code metrics"""
    physical: int = 0  # Total lines
    logical: int = 0   # Statement lines
    comments: int = 0  # Comment lines
    blank: int = 0     # Blank lines

    @property
    def code_to_comment_ratio(self) -> float:
        """Ratio of code lines to comment lines"""
        if self.comments == 0:
            return float('inf')
        return self.logical / self.comments


@dataclass
class FunctionComplexity:
    """Complexity metrics for a function"""
    name: str
    cyclomatic: int = 1
    cognitive: int = 0
    halstead: HalsteadMetrics = field(default_factory=HalsteadMetrics)
    loc: LOCMetrics = field(default_factory=LOCMetrics)
    params: int = 0
    variables: int = 0
    nesting_depth: int = 0
    return_statements: int = 0
    function_calls: int = 0

    @property
    def complexity_level(self) -> ComplexityLevel:
        """Determine overall complexity level"""
        if self.cyclomatic <= 10 and self.cognitive <= 5:
            return ComplexityLevel.SIMPLE
        elif self.cyclomatic <= 20 and self.cognitive <= 10:
            return ComplexityLevel.MODERATE
        elif self.cyclomatic <= 50:
            return ComplexityLevel.COMPLEX
        return ComplexityLevel.VERY_COMPLEX


@dataclass
class ClassComplexity:
    """Complexity metrics for a class"""
    name: str
    methods_complexity: List[FunctionComplexity] = field(default_factory=list)
    attributes_count: int = 0

    @property
    def avg_method_complexity(self) -> float:
        """Average cyclomatic complexity of methods"""
        if not self.methods_complexity:
            return 0.0
        return sum(m.cyclomatic for m in self.methods_complexity) / len(self.methods_complexity)

    @property
    def total_complexity(self) -> int:
        """Sum of all method complexities"""
        return sum(m.cyclomatic for m in self.methods_complexity)


@dataclass
class ModuleComplexity:
    """Complexity metrics for a module"""
    functions: List[FunctionComplexity] = field(default_factory=list)
    classes: List[ClassComplexity] = field(default_factory=list)
    imports_count: int = 0

    @property
    def total_complexity(self) -> int:
        """Total cyclomatic complexity"""
        func_complexity = sum(f.cyclomatic for f in self.functions)
        class_complexity = sum(c.total_complexity for c in self.classes)
        return func_complexity + class_complexity

    @property
    def avg_complexity(self) -> float:
        """Average complexity per function/method"""
        total_items = len(self.functions) + sum(len(c.methods_complexity) for c in self.classes)
        if total_items == 0:
            return 0.0
        return self.total_complexity / total_items


@dataclass
class Hotspot:
    """Complexity hotspot in code"""
    location: str
    complexity_score: int
    metric_type: str
    severity: str
    description: str


@dataclass
class RefactoringSuggestion:
    """Refactoring recommendation"""
    hotspot: Hotspot
    refactoring_type: RefactoringType
    description: str
    estimated_reduction: int


@dataclass
class ComplexityReport:
    """Comprehensive complexity analysis report"""
    module: ModuleComplexity
    cyclomatic_total: int = 0
    cognitive_total: int = 0
    halstead: HalsteadMetrics = field(default_factory=HalsteadMetrics)
    maintainability_index: float = 0.0
    max_nesting_depth: int = 0
    entropy: float = 0.0
    loc: LOCMetrics = field(default_factory=LOCMetrics)
    hotspots: List[Hotspot] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ComplexityTrend:
    """Complexity trend analysis over time"""
    dates: List[datetime] = field(default_factory=list)
    complexity_values: List[int] = field(default_factory=list)

    @property
    def trend_direction(self) -> str:
        """Determine if complexity is increasing or decreasing"""
        if len(self.complexity_values) < 2:
            return "stable"
        recent = sum(self.complexity_values[-3:]) / min(3, len(self.complexity_values[-3:]))
        older = sum(self.complexity_values[:3]) / min(3, len(self.complexity_values[:3]))
        if recent > older * 1.1:
            return "increasing"
        elif recent < older * 0.9:
            return "decreasing"
        return "stable"

    @property
    def rate_of_change(self) -> float:
        """Rate of complexity change"""
        if len(self.complexity_values) < 2:
            return 0.0
        return (self.complexity_values[-1] - self.complexity_values[0]) / len(self.complexity_values)


@dataclass
class ComplexityBudget:
    """Complexity budget constraints"""
    max_function_cyclomatic: int = 10
    max_function_cognitive: int = 5
    max_class_complexity: int = 50
    max_module_complexity: int = 100
    max_nesting_depth: int = 4


@dataclass
class BudgetReport:
    """Complexity budget compliance report"""
    actual: Dict[str, int] = field(default_factory=dict)
    budget: ComplexityBudget = field(default_factory=ComplexityBudget)
    over_budget: bool = False
    violations: List[str] = field(default_factory=list)


class ComplexityAnalyzer:
    """
    Comprehensive Code Complexity Analyzer

    Computes multiple complexity metrics including cyclomatic complexity,
    cognitive complexity, Halstead metrics, maintainability index, code entropy,
    and provides actionable refactoring recommendations.
    """

    def __init__(self):
        self.operators = set()
        self.operands = set()
        self.operator_counts = Counter()
        self.operand_counts = Counter()

    def analyze(self, code: Union[str, Path]) -> ComplexityReport:
        """
        Main analysis entry point

        Args:
            code: Source code string or path to file

        Returns:
            ComplexityReport with comprehensive metrics
        """
        if isinstance(code, Path):
            code = code.read_text()

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            raise ValueError(f"Invalid Python syntax: {e}")

        # Calculate LOC metrics
        loc = self._calculate_loc_metrics(code)

        # Analyze module structure
        module = self._analyze_module(tree)

        # Calculate aggregate metrics
        cyclomatic_total = module.total_complexity
        cognitive_total = self._calculate_total_cognitive(module)
        halstead = self._calculate_module_halstead(tree)
        max_nesting = self._calculate_max_nesting(tree)
        entropy = self.calculate_code_entropy(code)

        # Calculate maintainability index
        mi = self.calculate_maintainability_index({
            'halstead_volume': halstead.volume,
            'cyclomatic': cyclomatic_total,
            'loc': loc.logical
        })

        report = ComplexityReport(
            module=module,
            cyclomatic_total=cyclomatic_total,
            cognitive_total=cognitive_total,
            halstead=halstead,
            maintainability_index=mi,
            max_nesting_depth=max_nesting,
            entropy=entropy,
            loc=loc
        )

        # Detect hotspots
        report.hotspots = self.detect_complexity_hotspots(report, threshold=10)

        return report

    def calculate_cyclomatic_complexity(self, node: ast.AST) -> int:
        """
        Calculate McCabe cyclomatic complexity

        Formula: M = E - N + 2P (simplified to counting decision points + 1)

        Args:
            node: AST node to analyze

        Returns:
            Cyclomatic complexity value
        """
        complexity = 1

        for child in ast.walk(node):
            # Decision points
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.With):
                complexity += len(child.items)
            elif isinstance(child, ast.AsyncWith):
                complexity += len(child.items)
            elif isinstance(child, ast.BoolOp):
                # Each 'and'/'or' adds a decision point
                complexity += len(child.values) - 1
            elif isinstance(child, (ast.ListComp, ast.DictComp, ast.SetComp, ast.GeneratorExp)):
                # Comprehensions add complexity
                for generator in child.generators if hasattr(child, 'generators') else []:
                    complexity += 1
                    complexity += len(generator.ifs)

        return complexity

    def calculate_cognitive_complexity(self, node: ast.AST, nesting: int = 0) -> int:
        """
        Calculate cognitive complexity (more human-oriented than cyclomatic)

        Args:
            node: AST node to analyze
            nesting: Current nesting level

        Returns:
            Cognitive complexity value
        """
        complexity = 0

        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                # Control flow structures increment by 1 + nesting
                complexity += 1 + nesting
                complexity += self.calculate_cognitive_complexity(child, nesting + 1)
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1 + nesting
                complexity += self.calculate_cognitive_complexity(child, nesting + 1)
            elif isinstance(child, (ast.IfExp, ast.Lambda)):
                # Ternary and lambda add complexity
                complexity += 1 + nesting
                complexity += self.calculate_cognitive_complexity(child, nesting + 1)
            elif isinstance(child, ast.BoolOp):
                # Boolean operations add complexity
                complexity += len(child.values) - 1
                complexity += self.calculate_cognitive_complexity(child, nesting)
            else:
                complexity += self.calculate_cognitive_complexity(child, nesting)

        return complexity

    def calculate_halstead_metrics(self, node: ast.AST) -> HalsteadMetrics:
        """
        Calculate Halstead software science metrics

        Args:
            node: AST node to analyze

        Returns:
            HalsteadMetrics object
        """
        operators = set()
        operands = set()
        operator_counts = Counter()
        operand_counts = Counter()

        for child in ast.walk(node):
            # Operators
            if isinstance(child, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod,
                                 ast.Pow, ast.LShift, ast.RShift, ast.BitOr,
                                 ast.BitXor, ast.BitAnd, ast.FloorDiv)):
                op_name = child.__class__.__name__
                operators.add(op_name)
                operator_counts[op_name] += 1
            elif isinstance(child, (ast.And, ast.Or, ast.Not)):
                op_name = child.__class__.__name__
                operators.add(op_name)
                operator_counts[op_name] += 1
            elif isinstance(child, (ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt,
                                   ast.GtE, ast.Is, ast.IsNot, ast.In, ast.NotIn)):
                op_name = child.__class__.__name__
                operators.add(op_name)
                operator_counts[op_name] += 1
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                operators.add('def')
                operator_counts['def'] += 1
            elif isinstance(child, (ast.If, ast.For, ast.While, ast.With)):
                op_name = child.__class__.__name__.lower()
                operators.add(op_name)
                operator_counts[op_name] += 1
            elif isinstance(child, ast.Return):
                operators.add('return')
                operator_counts['return'] += 1

            # Operands
            if isinstance(child, ast.Name):
                operands.add(child.id)
                operand_counts[child.id] += 1
            elif isinstance(child, (ast.Constant, ast.Num, ast.Str)):
                value = str(getattr(child, 'value', getattr(child, 'n', getattr(child, 's', ''))))
                operands.add(value)
                operand_counts[value] += 1

        return HalsteadMetrics(
            n1=len(operators),
            n2=len(operands),
            N1=sum(operator_counts.values()),
            N2=sum(operand_counts.values())
        )

    def calculate_maintainability_index(self, metrics: Dict[str, Any]) -> float:
        """
        Calculate maintainability index

        Formula: MI = 171 - 5.2*ln(V) - 0.23*G - 16.2*ln(LOC)
        Scale: 0-100, higher is better

        Args:
            metrics: Dictionary with 'halstead_volume', 'cyclomatic', 'loc'

        Returns:
            Maintainability index (0-100)
        """
        volume = metrics.get('halstead_volume', 1)
        cyclomatic = metrics.get('cyclomatic', 1)
        loc = metrics.get('loc', 1)

        if volume <= 0:
            volume = 1
        if loc <= 0:
            loc = 1

        mi = 171 - 5.2 * math.log(volume) - 0.23 * cyclomatic - 16.2 * math.log(loc)

        # Normalize to 0-100 scale
        return max(0, min(100, mi))

    def calculate_nesting_depth(self, node: ast.AST, current_depth: int = 0) -> int:
        """
        Calculate maximum nesting depth of control structures

        Args:
            node: AST node to analyze
            current_depth: Current nesting level

        Returns:
            Maximum nesting depth
        """
        max_depth = current_depth

        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.With,
                                 ast.AsyncFor, ast.AsyncWith, ast.ExceptHandler)):
                child_depth = self.calculate_nesting_depth(child, current_depth + 1)
                max_depth = max(max_depth, child_depth)
            else:
                child_depth = self.calculate_nesting_depth(child, current_depth)
                max_depth = max(max_depth, child_depth)

        return max_depth

    def calculate_code_entropy(self, code: str) -> float:
        """
        Calculate Shannon entropy of token distribution

        Higher entropy = more complex/unpredictable code
        Formula: H = -Σ(p(x) * log2(p(x)))

        Args:
            code: Source code string

        Returns:
            Entropy value
        """
        # Tokenize code
        tokens = []
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                tokens.append(node.__class__.__name__)
        except:
            # Fallback to simple tokenization
            tokens = code.split()

        if not tokens:
            return 0.0

        # Calculate frequency distribution
        total = len(tokens)
        frequencies = Counter(tokens)

        # Calculate Shannon entropy
        entropy = 0.0
        for count in frequencies.values():
            p = count / total
            entropy -= p * math.log2(p)

        return entropy

    def analyze_function_complexity(self, func: ast.FunctionDef) -> FunctionComplexity:
        """
        Analyze complexity of a single function

        Args:
            func: FunctionDef AST node

        Returns:
            FunctionComplexity object
        """
        cyclomatic = self.calculate_cyclomatic_complexity(func)
        cognitive = self.calculate_cognitive_complexity(func)
        halstead = self.calculate_halstead_metrics(func)
        nesting = self.calculate_nesting_depth(func)

        # Count parameters
        params = len(func.args.args) + len(func.args.posonlyargs) + len(func.args.kwonlyargs)
        if func.args.vararg:
            params += 1
        if func.args.kwarg:
            params += 1

        # Count local variables
        variables = len([n for n in ast.walk(func) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)])

        # Count return statements
        returns = len([n for n in ast.walk(func) if isinstance(n, ast.Return)])

        # Count function calls
        calls = len([n for n in ast.walk(func) if isinstance(n, ast.Call)])

        # Calculate LOC
        if hasattr(func, 'lineno') and hasattr(func, 'end_lineno'):
            loc_count = func.end_lineno - func.lineno + 1
        else:
            loc_count = 1

        loc = LOCMetrics(physical=loc_count, logical=loc_count)

        return FunctionComplexity(
            name=func.name,
            cyclomatic=cyclomatic,
            cognitive=cognitive,
            halstead=halstead,
            loc=loc,
            params=params,
            variables=variables,
            nesting_depth=nesting,
            return_statements=returns,
            function_calls=calls
        )

    def analyze_class_complexity(self, cls: ast.ClassDef) -> ClassComplexity:
        """
        Analyze complexity of a class

        Args:
            cls: ClassDef AST node

        Returns:
            ClassComplexity object
        """
        methods = []
        attributes = 0

        for node in cls.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(self.analyze_function_complexity(node))
            elif isinstance(node, ast.Assign):
                attributes += len(node.targets)
            elif isinstance(node, ast.AnnAssign):
                attributes += 1

        return ClassComplexity(
            name=cls.name,
            methods_complexity=methods,
            attributes_count=attributes
        )

    def analyze_module_complexity(self, module: ast.Module) -> ModuleComplexity:
        """
        Analyze complexity of entire module

        Args:
            module: Module AST node

        Returns:
            ModuleComplexity object
        """
        return self._analyze_module(module)

    def detect_complexity_hotspots(self, report: ComplexityReport, threshold: int = 10) -> List[Hotspot]:
        """
        Detect complexity hotspots in code

        Args:
            report: ComplexityReport to analyze
            threshold: Complexity threshold for hotspot detection

        Returns:
            List of Hotspot objects
        """
        hotspots = []

        # Check functions
        for func in report.module.functions:
            if func.cyclomatic > threshold:
                severity = self._get_severity(func.cyclomatic, threshold)
                hotspots.append(Hotspot(
                    location=f"Function '{func.name}'",
                    complexity_score=func.cyclomatic,
                    metric_type="cyclomatic",
                    severity=severity,
                    description=f"High cyclomatic complexity: {func.cyclomatic}"
                ))

            if func.cognitive > threshold:
                severity = self._get_severity(func.cognitive, threshold)
                hotspots.append(Hotspot(
                    location=f"Function '{func.name}'",
                    complexity_score=func.cognitive,
                    metric_type="cognitive",
                    severity=severity,
                    description=f"High cognitive complexity: {func.cognitive}"
                ))

            if func.nesting_depth > 4:
                hotspots.append(Hotspot(
                    location=f"Function '{func.name}'",
                    complexity_score=func.nesting_depth,
                    metric_type="nesting",
                    severity="high",
                    description=f"Deep nesting: {func.nesting_depth} levels"
                ))

        # Check classes
        for cls in report.module.classes:
            if cls.total_complexity > threshold * 3:
                severity = self._get_severity(cls.total_complexity, threshold * 3)
                hotspots.append(Hotspot(
                    location=f"Class '{cls.name}'",
                    complexity_score=cls.total_complexity,
                    metric_type="class_complexity",
                    severity=severity,
                    description=f"God class with complexity: {cls.total_complexity}"
                ))

        # Sort by severity and complexity
        return sorted(hotspots, key=lambda h: (h.severity, h.complexity_score), reverse=True)

    def suggest_refactorings(self, hotspot: Hotspot) -> List[RefactoringSuggestion]:
        """
        Suggest refactorings for a complexity hotspot

        Args:
            hotspot: Hotspot to analyze

        Returns:
            List of RefactoringSuggestion objects
        """
        suggestions = []

        if hotspot.metric_type == "cyclomatic":
            if hotspot.complexity_score > 20:
                suggestions.append(RefactoringSuggestion(
                    hotspot=hotspot,
                    refactoring_type=RefactoringType.EXTRACT_METHOD,
                    description="Extract complex logic into separate methods",
                    estimated_reduction=hotspot.complexity_score // 2
                ))
                suggestions.append(RefactoringSuggestion(
                    hotspot=hotspot,
                    refactoring_type=RefactoringType.STRATEGY_PATTERN,
                    description="Replace conditional logic with strategy pattern",
                    estimated_reduction=hotspot.complexity_score // 3
                ))
            elif hotspot.complexity_score > 10:
                suggestions.append(RefactoringSuggestion(
                    hotspot=hotspot,
                    refactoring_type=RefactoringType.SIMPLIFY_CONDITIONAL,
                    description="Simplify conditional logic to reduce complexity",
                    estimated_reduction=hotspot.complexity_score // 2
                ))
            else:
                # Even for lower complexity, provide some guidance
                suggestions.append(RefactoringSuggestion(
                    hotspot=hotspot,
                    refactoring_type=RefactoringType.EXTRACT_METHOD,
                    description="Consider extracting logical blocks into separate methods",
                    estimated_reduction=max(1, hotspot.complexity_score // 2)
                ))

        if hotspot.metric_type == "nesting":
            suggestions.append(RefactoringSuggestion(
                hotspot=hotspot,
                refactoring_type=RefactoringType.INTRODUCE_GUARD_CLAUSE,
                description="Introduce guard clauses to reduce nesting",
                estimated_reduction=hotspot.complexity_score // 2
            ))
            suggestions.append(RefactoringSuggestion(
                hotspot=hotspot,
                refactoring_type=RefactoringType.REDUCE_NESTING,
                description="Extract nested blocks into separate functions",
                estimated_reduction=hotspot.complexity_score // 2
            ))

        if hotspot.metric_type == "class_complexity":
            suggestions.append(RefactoringSuggestion(
                hotspot=hotspot,
                refactoring_type=RefactoringType.DECOMPOSE_CLASS,
                description="Split class into smaller, focused classes",
                estimated_reduction=hotspot.complexity_score // 2
            ))

        if hotspot.metric_type == "cognitive":
            suggestions.append(RefactoringSuggestion(
                hotspot=hotspot,
                refactoring_type=RefactoringType.SIMPLIFY_LOGIC,
                description="Simplify complex logic for better readability",
                estimated_reduction=hotspot.complexity_score // 3
            ))

        return suggestions

    def compute_complexity_trend(self, history: List[ComplexityReport]) -> ComplexityTrend:
        """
        Compute complexity trend over time

        Args:
            history: List of historical ComplexityReport objects

        Returns:
            ComplexityTrend object
        """
        dates = [report.timestamp for report in history]
        values = [report.cyclomatic_total for report in history]

        return ComplexityTrend(dates=dates, complexity_values=values)

    def enforce_complexity_budget(self, report: ComplexityReport, budget: ComplexityBudget) -> BudgetReport:
        """
        Enforce complexity budget constraints

        Args:
            report: ComplexityReport to check
            budget: ComplexityBudget constraints

        Returns:
            BudgetReport with violations
        """
        violations = []
        actual = {}

        # Check function complexities
        for func in report.module.functions:
            if func.cyclomatic > budget.max_function_cyclomatic:
                violations.append(
                    f"Function '{func.name}' exceeds cyclomatic budget: "
                    f"{func.cyclomatic} > {budget.max_function_cyclomatic}"
                )
            if func.cognitive > budget.max_function_cognitive:
                violations.append(
                    f"Function '{func.name}' exceeds cognitive budget: "
                    f"{func.cognitive} > {budget.max_function_cognitive}"
                )
            if func.nesting_depth > budget.max_nesting_depth:
                violations.append(
                    f"Function '{func.name}' exceeds nesting budget: "
                    f"{func.nesting_depth} > {budget.max_nesting_depth}"
                )

        # Check class complexities
        for cls in report.module.classes:
            if cls.total_complexity > budget.max_class_complexity:
                violations.append(
                    f"Class '{cls.name}' exceeds complexity budget: "
                    f"{cls.total_complexity} > {budget.max_class_complexity}"
                )

        # Check module complexity
        if report.module.total_complexity > budget.max_module_complexity:
            violations.append(
                f"Module exceeds complexity budget: "
                f"{report.module.total_complexity} > {budget.max_module_complexity}"
            )

        actual['module_total'] = report.module.total_complexity

        return BudgetReport(
            actual=actual,
            budget=budget,
            over_budget=len(violations) > 0,
            violations=violations
        )

    def rank_by_complexity(self, items: List[Union[FunctionComplexity, ClassComplexity]]) -> List[Union[FunctionComplexity, ClassComplexity]]:
        """
        Sort items by complexity descending

        Args:
            items: List of FunctionComplexity or ClassComplexity objects

        Returns:
            Sorted list
        """
        return sorted(items, key=lambda x: x.cyclomatic if isinstance(x, FunctionComplexity) else x.total_complexity, reverse=True)

    def visualize_complexity(self, report: ComplexityReport, output: Path) -> bool:
        """
        Visualize complexity metrics (placeholder for future implementation)

        Args:
            report: ComplexityReport to visualize
            output: Output file path

        Returns:
            True if successful
        """
        # Placeholder for visualization logic
        # Could generate charts, heatmaps, etc.
        return True

    # Private helper methods

    def _analyze_module(self, tree: ast.Module) -> ModuleComplexity:
        """Analyze module and extract all complexity metrics"""
        functions = []
        classes = []
        imports = 0

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imports += 1

        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(self.analyze_function_complexity(node))
            elif isinstance(node, ast.ClassDef):
                classes.append(self.analyze_class_complexity(node))

        return ModuleComplexity(
            functions=functions,
            classes=classes,
            imports_count=imports
        )

    def _calculate_total_cognitive(self, module: ModuleComplexity) -> int:
        """Calculate total cognitive complexity for module"""
        total = sum(f.cognitive for f in module.functions)
        for cls in module.classes:
            total += sum(m.cognitive for m in cls.methods_complexity)
        return total

    def _calculate_module_halstead(self, tree: ast.Module) -> HalsteadMetrics:
        """Calculate Halstead metrics for entire module"""
        return self.calculate_halstead_metrics(tree)

    def _calculate_max_nesting(self, tree: ast.Module) -> int:
        """Calculate maximum nesting depth in module"""
        return self.calculate_nesting_depth(tree)

    def _calculate_loc_metrics(self, code: str) -> LOCMetrics:
        """Calculate lines of code metrics"""
        lines = code.split('\n')
        physical = len(lines)
        blank = sum(1 for line in lines if not line.strip())
        comments = sum(1 for line in lines if line.strip().startswith('#'))
        logical = physical - blank - comments

        return LOCMetrics(
            physical=physical,
            logical=max(1, logical),
            comments=comments,
            blank=blank
        )

    def _get_severity(self, value: int, threshold: int) -> str:
        """Determine severity level based on threshold"""
        if value > threshold * 3:
            return "critical"
        elif value > threshold * 2:
            return "high"
        elif value > threshold:
            return "medium"
        return "low"
