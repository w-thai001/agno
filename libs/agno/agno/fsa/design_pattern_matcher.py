"""Design Pattern Matcher FSA for detecting common design patterns."""

import ast
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Set
import logging

from agno.fsa.base import FSA, Transition

logger = logging.getLogger(__name__)


class MatcherState(str, Enum):
    """States for Design Pattern Matcher FSA."""

    INITIAL = "initial"
    ANALYZING_CODE = "analyzing_code"
    MATCHING_PATTERNS = "matching_patterns"
    GENERATING_REPORT = "generating_report"
    COMPLETED = "completed"


@dataclass
class PatternMatch:
    """Detected design pattern."""

    pattern_name: str
    confidence: str  # "high", "medium", "low"
    file_path: str = ""
    class_name: str = ""
    line_number: int = 0
    evidence: List[str] = field(default_factory=list)


@dataclass
class PatternReport:
    """Pattern matching report."""

    total_files: int = 0
    total_patterns: int = 0
    patterns_by_type: Dict[str, int] = field(default_factory=dict)
    matches: List[PatternMatch] = field(default_factory=list)


class DesignPatternMatcher(FSA):
    """FSA for detecting design patterns in code."""

    def __init__(self):
        super().__init__(name="DesignPatternMatcher", initial_state=MatcherState.INITIAL)

        # Initialize context
        self.context = {
            "code_files": [],
            "file_data": {},
            "matches": [],
            "report": None,
        }

        # Setup transitions
        self._setup_transitions()

    def _setup_transitions(self):
        """Setup FSA transitions."""
        transitions = [
            Transition(
                from_state=MatcherState.INITIAL,
                to_state=MatcherState.ANALYZING_CODE,
                condition=lambda ctx: len(ctx.get("code_files", [])) > 0,
                action=self._analyze_code,
            ),
            Transition(
                from_state=MatcherState.ANALYZING_CODE,
                to_state=MatcherState.MATCHING_PATTERNS,
                action=self._match_patterns,
            ),
            Transition(
                from_state=MatcherState.MATCHING_PATTERNS,
                to_state=MatcherState.GENERATING_REPORT,
                action=self._generate_report,
            ),
            Transition(
                from_state=MatcherState.GENERATING_REPORT,
                to_state=MatcherState.COMPLETED,
                action=lambda ctx: ctx,
            ),
        ]

        self.register_transitions(transitions)

    def _analyze_code(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze code files."""
        logger.info("Analyzing code files...")

        file_data = {}

        for file_input in context["code_files"]:
            try:
                if isinstance(file_input, dict):
                    path = file_input["path"]
                    content = file_input["content"]
                else:
                    path = file_input
                    with open(path, "r") as f:
                        content = f.read()

                # Parse AST
                try:
                    tree = ast.parse(content)
                    file_data[path] = {"tree": tree, "content": content}
                except SyntaxError as e:
                    logger.warning(f"Syntax error in {path}: {e}")

            except Exception as e:
                logger.error(f"Error analyzing {path}: {e}")

        context["file_data"] = file_data
        logger.info(f"Analyzed {len(file_data)} files")
        return context

    def _match_patterns(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Match design patterns."""
        logger.info("Matching design patterns...")

        matches = []
        file_data = context["file_data"]

        for file_path, data in file_data.items():
            tree = data["tree"]

            # Detect various patterns
            matches.extend(self._detect_singleton(file_path, tree))
            matches.extend(self._detect_factory(file_path, tree))
            matches.extend(self._detect_observer(file_path, tree))
            matches.extend(self._detect_builder(file_path, tree))
            matches.extend(self._detect_strategy(file_path, tree))

        context["matches"] = matches
        logger.info(f"Detected {len(matches)} pattern matches")
        return context

    def _detect_singleton(self, file_path: str, tree: ast.AST) -> List[PatternMatch]:
        """Detect Singleton pattern."""
        matches = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                evidence = []
                has_instance_var = False
                has_get_instance = False

                # Check for __instance or _instance class variable
                for item in node.body:
                    if isinstance(item, ast.Assign):
                        for target in item.targets:
                            if isinstance(target, ast.Name) and target.id in ["_instance", "__instance"]:
                                has_instance_var = True
                                evidence.append("Has _instance class variable")

                # Check for getInstance or similar method
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        if item.name in ["get_instance", "getInstance", "instance"]:
                            has_get_instance = True
                            evidence.append(f"Has {item.name}() method")

                        # Check for __new__ override (another singleton approach)
                        if item.name == "__new__":
                            evidence.append("Overrides __new__ (singleton pattern)")
                            has_instance_var = True

                if has_instance_var or (has_get_instance and len(evidence) > 0):
                    confidence = "high" if (has_instance_var and has_get_instance) else "medium"
                    matches.append(
                        PatternMatch(
                            pattern_name="Singleton",
                            confidence=confidence,
                            file_path=file_path,
                            class_name=node.name,
                            line_number=node.lineno,
                            evidence=evidence,
                        )
                    )

        return matches

    def _detect_factory(self, file_path: str, tree: ast.AST) -> List[PatternMatch]:
        """Detect Factory pattern."""
        matches = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                evidence = []
                factory_methods = []

                # Look for create/make/build methods
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        name_lower = item.name.lower()
                        if any(keyword in name_lower for keyword in ["create", "make", "build", "factory"]):
                            # Check if method returns a class instance
                            has_return = any(isinstance(n, ast.Return) for n in ast.walk(item))
                            if has_return:
                                factory_methods.append(item.name)
                                evidence.append(f"Factory method: {item.name}()")

                if factory_methods:
                    confidence = "high" if len(factory_methods) > 1 else "medium"
                    matches.append(
                        PatternMatch(
                            pattern_name="Factory",
                            confidence=confidence,
                            file_path=file_path,
                            class_name=node.name,
                            line_number=node.lineno,
                            evidence=evidence,
                        )
                    )

        return matches

    def _detect_observer(self, file_path: str, tree: ast.AST) -> List[PatternMatch]:
        """Detect Observer pattern."""
        matches = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                evidence = []
                has_observers = False
                has_notify = False
                has_subscribe = False

                # Look for observer-related attributes and methods
                for item in node.body:
                    if isinstance(item, ast.Assign):
                        for target in item.targets:
                            if isinstance(target, ast.Name):
                                if "observer" in target.id.lower() or "listener" in target.id.lower():
                                    has_observers = True
                                    evidence.append(f"Has {target.id} attribute")

                    if isinstance(item, ast.FunctionDef):
                        name_lower = item.name.lower()

                        if "notify" in name_lower or "update" in name_lower:
                            has_notify = True
                            evidence.append(f"Has {item.name}() method")

                        if "subscribe" in name_lower or "attach" in name_lower or "register" in name_lower:
                            has_subscribe = True
                            evidence.append(f"Has {item.name}() method")

                if (has_observers and has_notify) or (has_subscribe and has_notify):
                    confidence = "high" if all([has_observers, has_notify, has_subscribe]) else "medium"
                    matches.append(
                        PatternMatch(
                            pattern_name="Observer",
                            confidence=confidence,
                            file_path=file_path,
                            class_name=node.name,
                            line_number=node.lineno,
                            evidence=evidence,
                        )
                    )

        return matches

    def _detect_builder(self, file_path: str, tree: ast.AST) -> List[PatternMatch]:
        """Detect Builder pattern."""
        matches = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                evidence = []
                builder_methods = []

                # Look for methods that return self (method chaining)
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        # Check if method returns self
                        for stmt in ast.walk(item):
                            if isinstance(stmt, ast.Return) and stmt.value:
                                if isinstance(stmt.value, ast.Name) and stmt.value.id == "self":
                                    builder_methods.append(item.name)
                                    evidence.append(f"Chainable method: {item.name}()")
                                    break

                        # Look for build() method
                        if item.name in ["build", "create", "construct"]:
                            evidence.append(f"Has {item.name}() terminator method")

                if len(builder_methods) >= 2:
                    confidence = "high" if len(builder_methods) >= 3 else "medium"
                    matches.append(
                        PatternMatch(
                            pattern_name="Builder",
                            confidence=confidence,
                            file_path=file_path,
                            class_name=node.name,
                            line_number=node.lineno,
                            evidence=evidence,
                        )
                    )

        return matches

    def _detect_strategy(self, file_path: str, tree: ast.AST) -> List[PatternMatch]:
        """Detect Strategy pattern."""
        matches = []

        # Look for abstract base classes with execute/run/apply methods
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                evidence = []
                is_abstract = False
                has_strategy_method = False

                # Check for ABC inheritance
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id in ["ABC", "Interface"]:
                        is_abstract = True
                        evidence.append("Inherits from ABC/Interface")

                # Look for strategy execution methods
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        if item.name in ["execute", "run", "apply", "process", "handle"]:
                            has_strategy_method = True
                            evidence.append(f"Has {item.name}() strategy method")

                        # Check for @abstractmethod decorator
                        for decorator in item.decorator_list:
                            if isinstance(decorator, ast.Name) and decorator.id == "abstractmethod":
                                is_abstract = True
                                evidence.append(f"Has @abstractmethod on {item.name}()")

                if is_abstract and has_strategy_method:
                    matches.append(
                        PatternMatch(
                            pattern_name="Strategy",
                            confidence="high",
                            file_path=file_path,
                            class_name=node.name,
                            line_number=node.lineno,
                            evidence=evidence,
                        )
                    )

        return matches

    def _generate_report(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate pattern matching report."""
        logger.info("Generating pattern report...")

        matches = context["matches"]

        # Count by type
        patterns_by_type = {}
        for match in matches:
            patterns_by_type[match.pattern_name] = patterns_by_type.get(match.pattern_name, 0) + 1

        report = PatternReport(
            total_files=len(context["file_data"]),
            total_patterns=len(matches),
            patterns_by_type=patterns_by_type,
            matches=matches,
        )

        context["report"] = report
        logger.info(f"Generated report: {len(matches)} patterns found")
        return context

    def match(self, code_files: List[Any]) -> PatternReport:
        """
        Match design patterns in given files.

        Args:
            code_files: List of file paths or dicts with 'path' and 'content'

        Returns:
            PatternReport with detected patterns
        """
        # Reset FSA
        self.reset()

        # Set context
        self.context["code_files"] = code_files

        # Run FSA
        final_context = self.run()

        return final_context.get("report")


def print_pattern_report(report: PatternReport):
    """Print formatted design pattern report."""
    print("\n" + "=" * 80)
    print("DESIGN PATTERN MATCHING REPORT")
    print("=" * 80)

    # Summary
    print("\n📊 SUMMARY:")
    print("-" * 80)
    print(f"  Files Analyzed:       {report.total_files}")
    print(f"  Patterns Detected:    {report.total_patterns}")

    # Patterns by type
    if report.patterns_by_type:
        print("\n🎨 PATTERNS BY TYPE:")
        print("-" * 80)
        for pattern_name, count in sorted(report.patterns_by_type.items()):
            print(f"  {pattern_name}: {count}")

    # Detected patterns
    if report.matches:
        print("\n✨ DETECTED PATTERNS:")
        print("-" * 80)

        # Group by confidence
        high_conf = [m for m in report.matches if m.confidence == "high"]
        medium_conf = [m for m in report.matches if m.confidence == "medium"]
        low_conf = [m for m in report.matches if m.confidence == "low"]

        for confidence, matches in [("HIGH", high_conf), ("MEDIUM", medium_conf), ("LOW", low_conf)]:
            if matches:
                conf_icon = {"HIGH": "🟢", "MEDIUM": "🟡", "LOW": "🔵"}[confidence]
                print(f"\n  {conf_icon} {confidence} CONFIDENCE:")
                for match in matches:
                    print(f"    • {match.pattern_name} - {match.class_name}")
                    print(f"      File: {match.file_path}:{match.line_number}")
                    if match.evidence:
                        print(f"      Evidence:")
                        for ev in match.evidence[:3]:
                            print(f"        - {ev}")

    # Final verdict
    print("\n" + "=" * 80)
    if report.total_patterns == 0:
        print("ℹ️  No design patterns detected.")
    else:
        print(f"✅ Found {report.total_patterns} design pattern(s) in your code!")
    print("=" * 80 + "\n")
