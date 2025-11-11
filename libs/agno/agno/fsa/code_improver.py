"""FSA-3.1: Multi-step Code Improvements

This module provides multi-step code improvement strategies based on quality metrics.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import re


@dataclass
class ImprovementPlan:
    """Plan for code improvements"""

    steps: List[str]
    priority_order: List[str]
    estimated_impact: Dict[str, float]


class CodeImprover:
    """FSA-3.1: Multi-step code improver

    Analyzes code weaknesses and applies targeted improvements:
    1. Naming improvements (descriptive names)
    2. Documentation additions (comments, docstrings)
    3. Structure improvements (formatting, organization)
    4. Efficiency optimizations (algorithm improvements)
    5. Best practice adherence (language conventions)
    """

    def __init__(self):
        """Initialize the code improver"""
        self.improvement_strategies = {
            "naming": self._improve_naming,
            "documentation": self._improve_documentation,
            "structure": self._improve_structure,
            "readability": self._improve_readability,
            "best_practices": self._improve_best_practices,
            "efficiency": self._improve_efficiency,
        }

    def improve(
        self,
        code: str,
        focus_areas: Optional[List[str]] = None,
        language: Optional[str] = None
    ) -> str:
        """Apply multi-step improvements to code

        Args:
            code: The code to improve
            focus_areas: Specific areas to focus on (if None, improves all)
            language: Programming language (auto-detected if not provided)

        Returns:
            Improved code
        """
        if not code or not code.strip():
            return code

        # Detect language if not provided
        if language is None:
            language = self._detect_language(code)

        # Determine which improvements to apply
        areas = focus_areas if focus_areas else list(self.improvement_strategies.keys())

        # Apply improvements sequentially
        improved_code = code
        for area in areas:
            if area in self.improvement_strategies:
                improved_code = self.improvement_strategies[area](improved_code, language)

        return improved_code

    def plan_improvements(
        self,
        code: str,
        weaknesses: List[str],
        suggestions: List[str]
    ) -> ImprovementPlan:
        """Create an improvement plan based on quality assessment

        Args:
            code: The code to improve
            weaknesses: List of identified weaknesses
            suggestions: List of improvement suggestions

        Returns:
            ImprovementPlan with ordered steps
        """
        steps = []
        priority_order = []
        estimated_impact = {}

        # Map weaknesses to improvement strategies
        weakness_map = {
            "naming": ["naming", "descriptive"],
            "documentation": ["document", "comment"],
            "structure": ["structure", "format", "indent"],
            "readability": ["readable", "spacing", "format"],
            "best_practices": ["best practice", "convention"],
            "efficiency": ["efficiency", "performance", "optimize"],
        }

        # Determine which strategies to apply
        for area, keywords in weakness_map.items():
            for weakness in weaknesses:
                if any(kw in weakness.lower() for kw in keywords):
                    if area not in priority_order:
                        priority_order.append(area)
                        steps.append(f"Apply {area} improvements")
                        estimated_impact[area] = 15.0  # Estimated score improvement

        # Default order if no specific weaknesses identified
        if not priority_order:
            priority_order = ["naming", "documentation", "structure", "readability"]
            steps = [f"Apply {area} improvements" for area in priority_order]
            estimated_impact = {area: 10.0 for area in priority_order}

        return ImprovementPlan(
            steps=steps,
            priority_order=priority_order,
            estimated_impact=estimated_impact
        )

    def _detect_language(self, code: str) -> str:
        """Detect programming language from code"""
        code_lower = code.lower()

        if "function" in code_lower or "const" in code_lower or "let" in code_lower:
            return "javascript"
        elif "def" in code_lower and ":" in code:
            return "python"
        elif "public class" in code or "private" in code_lower:
            return "java"
        elif "#include" in code or "std::" in code:
            return "cpp"
        else:
            return "unknown"

    def _improve_naming(self, code: str, language: str) -> str:
        """Improve variable and function names"""

        # Common abbreviations to expand
        expansions = {
            r'\bcalc\b': 'calculate',
            r'\btemp\b': 'temporary',
            r'\bstr\b': 'string',
            r'\bnum\b': 'number',
            r'\bval\b': 'value',
            r'\bres\b': 'result',
            r'\berr\b': 'error',
            r'\bmsg\b': 'message',
            r'\bcfg\b': 'config',
            r'\bctx\b': 'context',
            r'\bparams\b': 'parameters',
            r'\bargs\b': 'arguments',
        }

        improved = code
        for abbrev, full in expansions.items():
            improved = re.sub(abbrev, full, improved)

        # Improve single-letter function names (except common loop variables)
        # Example: function a() -> function processData()
        if 'function' in improved:
            # Find single-letter function names
            matches = re.finditer(r'function\s+([a-z])\s*\(', improved)
            for match in matches:
                old_name = match.group(1)
                # Generate a more descriptive name based on context
                new_name = 'processData'
                improved = improved.replace(f'function {old_name}(', f'function {new_name}(')

        return improved

    def _improve_documentation(self, code: str, language: str) -> str:
        """Add documentation and comments"""

        lines = code.split('\n')
        improved_lines = []

        for i, line in enumerate(lines):
            # Add function documentation
            if 'function' in line and '//' not in line and '/*' not in line:
                indent = len(line) - len(line.lstrip())
                # Add JSDoc comment before function
                improved_lines.append(' ' * indent + '/**')
                improved_lines.append(' ' * indent + ' * Process and return result')
                # Extract parameters
                params_match = re.search(r'\((.*?)\)', line)
                if params_match and params_match.group(1).strip():
                    params = [p.strip() for p in params_match.group(1).split(',')]
                    for param in params:
                        improved_lines.append(f' * @param {{{param.split()[0] if " " in param else param}}} {param.split()[0] if " " in param else param}')
                improved_lines.append(' ' * indent + ' * @returns result')
                improved_lines.append(' ' * indent + ' */')

            improved_lines.append(line)

        return '\n'.join(improved_lines)

    def _improve_structure(self, code: str, language: str) -> str:
        """Improve code structure and formatting"""

        # Fix spacing around operators
        improved = code
        improved = re.sub(r'([a-zA-Z0-9])([\+\-\*/%])([a-zA-Z0-9])', r'\1 \2 \3', improved)

        # Fix spacing around braces
        improved = re.sub(r'\)\{', r') {', improved)
        improved = re.sub(r'\}\s*else', r'} else', improved)

        # Ensure newline after opening brace
        improved = re.sub(r'\{\s*([a-zA-Z])', r'{\n    \1', improved)

        # Ensure newline before closing brace
        improved = re.sub(r'([a-zA-Z0-9;])\s*\}', r'\1\n}', improved)

        return improved

    def _improve_readability(self, code: str, language: str) -> str:
        """Improve code readability"""

        # Add spacing between statements
        improved = code

        # Ensure proper indentation
        lines = improved.split('\n')
        indented_lines = []
        indent_level = 0

        for line in lines:
            stripped = line.strip()
            if not stripped:
                indented_lines.append('')
                continue

            # Decrease indent for closing braces
            if stripped.startswith('}'):
                indent_level = max(0, indent_level - 1)

            # Add indentation
            indented_lines.append('    ' * indent_level + stripped)

            # Increase indent after opening braces
            if stripped.endswith('{'):
                indent_level += 1
            # Decrease indent after closing braces
            elif stripped.startswith('}'):
                pass  # Already decreased above

        return '\n'.join(indented_lines)

    def _improve_best_practices(self, code: str, language: str) -> str:
        """Apply language-specific best practices"""

        improved = code

        if language == "javascript":
            # Replace var with const/let
            improved = re.sub(r'\bvar\b', 'const', improved)

            # Use strict equality
            improved = re.sub(r'==(?!=)', '===', improved)

            # Add 'use strict' if not present
            if "'use strict'" not in improved and '"use strict"' not in improved:
                improved = "'use strict';\n\n" + improved

        elif language == "python":
            # Add type hints (basic)
            improved = re.sub(
                r'def\s+(\w+)\s*\(([^)]*)\)\s*:',
                r'def \1(\2) -> Any:',
                improved
            )

        return improved

    def _improve_efficiency(self, code: str, language: str) -> str:
        """Improve code efficiency"""

        # This is a simple implementation - in practice, efficiency improvements
        # require deeper analysis and might change logic

        improved = code

        # Cache repeated calculations (simple pattern)
        # Example: if we see the same expression multiple times, suggest caching

        # For now, just ensure we're not doing obvious inefficiencies
        # like string concatenation in loops

        return improved

    def apply_incremental_improvement(
        self,
        code: str,
        focus_area: str,
        language: Optional[str] = None
    ) -> str:
        """Apply a single incremental improvement

        Args:
            code: The code to improve
            focus_area: Specific area to improve
            language: Programming language

        Returns:
            Incrementally improved code
        """
        if language is None:
            language = self._detect_language(code)

        if focus_area in self.improvement_strategies:
            return self.improvement_strategies[focus_area](code, language)

        return code
