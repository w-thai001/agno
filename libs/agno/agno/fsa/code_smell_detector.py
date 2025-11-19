"""Code Smell Detector FSA for identifying common code smells."""

import ast
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
import logging

from agno.fsa.base import FSA, Transition

logger = logging.getLogger(__name__)


class DetectorState(str, Enum):
    """States for Code Smell Detector FSA."""

    INITIAL = "initial"
    ANALYZING_CODE = "analyzing_code"
    DETECTING_SMELLS = "detecting_smells"
    GENERATING_REPORT = "generating_report"
    COMPLETED = "completed"


@dataclass
class CodeSmell:
    """Detected code smell."""

    smell_type: str
    severity: str  # "high", "medium", "low"
    message: str
    file_path: str = ""
    line_number: int = 0
    details: str = ""


@dataclass
class SmellReport:
    """Code smell detection report."""

    total_files: int = 0
    total_smells: int = 0
    smells_by_type: Dict[str, int] = field(default_factory=dict)
    smells: List[CodeSmell] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)


class CodeSmellDetector(FSA):
    """FSA for detecting code smells."""

    def __init__(self):
        super().__init__(name="CodeSmellDetector", initial_state=DetectorState.INITIAL)

        # Thresholds
        self.max_method_lines = 50
        self.max_parameters = 5
        self.max_nesting_depth = 4
        self.max_class_methods = 20
        self.max_class_lines = 500

        # Initialize context
        self.context = {
            "code_files": [],
            "file_data": {},
            "smells": [],
            "report": None,
        }

        # Setup transitions
        self._setup_transitions()

    def _setup_transitions(self):
        """Setup FSA transitions."""
        transitions = [
            Transition(
                from_state=DetectorState.INITIAL,
                to_state=DetectorState.ANALYZING_CODE,
                condition=lambda ctx: len(ctx.get("code_files", [])) > 0,
                action=self._analyze_code,
            ),
            Transition(
                from_state=DetectorState.ANALYZING_CODE,
                to_state=DetectorState.DETECTING_SMELLS,
                action=self._detect_smells,
            ),
            Transition(
                from_state=DetectorState.DETECTING_SMELLS,
                to_state=DetectorState.GENERATING_REPORT,
                action=self._generate_report,
            ),
            Transition(
                from_state=DetectorState.GENERATING_REPORT,
                to_state=DetectorState.COMPLETED,
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
                    file_data[path] = {"content": content, "tree": tree, "lines": content.split("\n")}
                except SyntaxError as e:
                    logger.warning(f"Syntax error in {path}: {e}")

            except Exception as e:
                logger.error(f"Error analyzing {path}: {e}")

        context["file_data"] = file_data
        logger.info(f"Analyzed {len(file_data)} files")
        return context

    def _detect_smells(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Detect code smells."""
        logger.info("Detecting code smells...")

        smells = []
        file_data = context["file_data"]

        for file_path, data in file_data.items():
            tree = data["tree"]
            content = data["content"]
            lines = data["lines"]

            # Detect various smells
            smells.extend(self._detect_long_methods(file_path, tree, lines))
            smells.extend(self._detect_too_many_parameters(file_path, tree))
            smells.extend(self._detect_deep_nesting(file_path, tree))
            smells.extend(self._detect_large_classes(file_path, tree, lines))
            smells.extend(self._detect_duplicate_code(file_path, lines))

        context["smells"] = smells
        logger.info(f"Detected {len(smells)} code smells")
        return context

    def _detect_long_methods(self, file_path: str, tree: ast.AST, lines: List[str]) -> List[CodeSmell]:
        """Detect methods that are too long."""
        smells = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Calculate method length
                if hasattr(node, "end_lineno") and hasattr(node, "lineno"):
                    method_lines = node.end_lineno - node.lineno

                    if method_lines > self.max_method_lines:
                        smells.append(
                            CodeSmell(
                                smell_type="long_method",
                                severity="high" if method_lines > self.max_method_lines * 2 else "medium",
                                message=f"Method '{node.name}' is too long ({method_lines} lines)",
                                file_path=file_path,
                                line_number=node.lineno,
                                details=f"Consider breaking into smaller methods (max: {self.max_method_lines} lines)",
                            )
                        )

        return smells

    def _detect_too_many_parameters(self, file_path: str, tree: ast.AST) -> List[CodeSmell]:
        """Detect methods with too many parameters."""
        smells = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                param_count = len(node.args.args)

                if param_count > self.max_parameters:
                    smells.append(
                        CodeSmell(
                            smell_type="too_many_parameters",
                            severity="medium",
                            message=f"Method '{node.name}' has too many parameters ({param_count})",
                            file_path=file_path,
                            line_number=node.lineno,
                            details=f"Consider using parameter object (max: {self.max_parameters} parameters)",
                        )
                    )

        return smells

    def _detect_deep_nesting(self, file_path: str, tree: ast.AST) -> List[CodeSmell]:
        """Detect deeply nested code blocks."""
        smells = []

        def get_nesting_depth(node, depth=0):
            """Calculate nesting depth."""
            max_depth = depth

            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                    child_depth = get_nesting_depth(child, depth + 1)
                    max_depth = max(max_depth, child_depth)
                else:
                    child_depth = get_nesting_depth(child, depth)
                    max_depth = max(max_depth, child_depth)

            return max_depth

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                nesting_depth = get_nesting_depth(node)

                if nesting_depth > self.max_nesting_depth:
                    smells.append(
                        CodeSmell(
                            smell_type="deep_nesting",
                            severity="high",
                            message=f"Method '{node.name}' has deep nesting ({nesting_depth} levels)",
                            file_path=file_path,
                            line_number=node.lineno,
                            details=f"Simplify logic or extract methods (max: {self.max_nesting_depth} levels)",
                        )
                    )

        return smells

    def _detect_large_classes(self, file_path: str, tree: ast.AST, lines: List[str]) -> List[CodeSmell]:
        """Detect classes that are too large."""
        smells = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Count methods
                method_count = sum(1 for item in node.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)))

                # Calculate class size
                if hasattr(node, "end_lineno") and hasattr(node, "lineno"):
                    class_lines = node.end_lineno - node.lineno

                    # Too many methods
                    if method_count > self.max_class_methods:
                        smells.append(
                            CodeSmell(
                                smell_type="large_class",
                                severity="high",
                                message=f"Class '{node.name}' has too many methods ({method_count})",
                                file_path=file_path,
                                line_number=node.lineno,
                                details=f"Consider splitting into smaller classes (max: {self.max_class_methods} methods)",
                            )
                        )

                    # Too many lines
                    if class_lines > self.max_class_lines:
                        smells.append(
                            CodeSmell(
                                smell_type="large_class",
                                severity="medium",
                                message=f"Class '{node.name}' is too large ({class_lines} lines)",
                                file_path=file_path,
                                line_number=node.lineno,
                                details=f"Consider refactoring (max: {self.max_class_lines} lines)",
                            )
                        )

        return smells

    def _detect_duplicate_code(self, file_path: str, lines: List[str]) -> List[CodeSmell]:
        """Detect duplicate code blocks."""
        smells = []

        # Simple duplication: find identical consecutive lines
        duplicate_threshold = 5
        i = 0

        while i < len(lines) - duplicate_threshold:
            # Skip empty lines and comments
            if not lines[i].strip() or lines[i].strip().startswith("#"):
                i += 1
                continue

            # Check for duplicates
            for j in range(i + duplicate_threshold, len(lines) - duplicate_threshold):
                if lines[i].strip() == lines[j].strip():
                    # Found potential duplicate
                    duplicate_length = 1
                    while (
                        i + duplicate_length < len(lines)
                        and j + duplicate_length < len(lines)
                        and lines[i + duplicate_length].strip() == lines[j + duplicate_length].strip()
                    ):
                        duplicate_length += 1

                    if duplicate_length >= duplicate_threshold:
                        smells.append(
                            CodeSmell(
                                smell_type="duplicate_code",
                                severity="medium",
                                message=f"Duplicate code block found ({duplicate_length} lines)",
                                file_path=file_path,
                                line_number=i + 1,
                                details=f"Also appears at line {j + 1}. Consider extracting to a function.",
                            )
                        )
                        break

            i += 1

        return smells

    def _generate_report(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate smell detection report."""
        logger.info("Generating smell report...")

        smells = context["smells"]

        # Count by type
        smells_by_type = {}
        for smell in smells:
            smells_by_type[smell.smell_type] = smells_by_type.get(smell.smell_type, 0) + 1

        # Count by severity
        severity_counts = {"high": 0, "medium": 0, "low": 0}
        for smell in smells:
            severity_counts[smell.severity] += 1

        report = SmellReport(
            total_files=len(context["file_data"]),
            total_smells=len(smells),
            smells_by_type=smells_by_type,
            smells=smells,
            summary={"by_severity": severity_counts, "by_type": smells_by_type},
        )

        context["report"] = report
        logger.info(f"Generated report: {len(smells)} smells found")
        return context

    def detect(self, code_files: List[Any]) -> SmellReport:
        """
        Detect code smells in given files.

        Args:
            code_files: List of file paths or dicts with 'path' and 'content'

        Returns:
            SmellReport with detected smells
        """
        # Reset FSA
        self.reset()

        # Set context
        self.context["code_files"] = code_files

        # Run FSA
        final_context = self.run()

        return final_context.get("report")


def print_smell_report(report: SmellReport):
    """Print formatted code smell report."""
    print("\n" + "=" * 80)
    print("CODE SMELL DETECTION REPORT")
    print("=" * 80)

    # Summary
    print("\n📊 SUMMARY:")
    print("-" * 80)
    print(f"  Files Analyzed:     {report.total_files}")
    print(f"  Total Smells:       {report.total_smells}")
    print(f"  High Severity:      {report.summary['by_severity']['high']}")
    print(f"  Medium Severity:    {report.summary['by_severity']['medium']}")
    print(f"  Low Severity:       {report.summary['by_severity']['low']}")

    # Smells by type
    if report.smells_by_type:
        print("\n🔍 SMELLS BY TYPE:")
        print("-" * 80)
        for smell_type, count in sorted(report.smells_by_type.items(), key=lambda x: x[1], reverse=True):
            print(f"  {smell_type.replace('_', ' ').title()}: {count}")

    # Top smells
    if report.smells:
        print("\n⚠️  DETECTED SMELLS:")
        print("-" * 80)

        # Sort by severity
        severity_order = {"high": 0, "medium": 1, "low": 2}
        sorted_smells = sorted(report.smells, key=lambda s: (severity_order[s.severity], s.file_path))

        for i, smell in enumerate(sorted_smells[:15], 1):
            severity_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}[smell.severity]
            print(f"  {i}. {severity_icon} [{smell.smell_type.upper()}] {smell.message}")
            print(f"     File: {smell.file_path}:{smell.line_number}")
            if smell.details:
                print(f"     → {smell.details}")

        if len(report.smells) > 15:
            print(f"\n  ... and {len(report.smells) - 15} more smells")

    # Final verdict
    print("\n" + "=" * 80)
    if report.total_smells == 0:
        print("✅ No code smells detected! Great job!")
    elif report.summary["by_severity"]["high"] == 0:
        print("⚠️  Some code smells detected, but no critical issues.")
    else:
        print(f"❌ {report.summary['by_severity']['high']} critical code smell(s) detected.")
    print("=" * 80 + "\n")
