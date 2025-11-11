"""
FSA-1.1: Prompt Optimizer

Optimizes prompts for AI-based code analysis and generation tasks.
Provides specialized prompts for different code analysis dimensions.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


class AnalysisType(Enum):
    """Types of code analysis."""

    SYNTAX = "syntax"
    STYLE = "style"
    SECURITY = "security"
    PERFORMANCE = "performance"
    BEST_PRACTICES = "best_practices"
    OVERALL = "overall"


@dataclass
class OptimizedPrompt:
    """An optimized prompt for code analysis."""

    analysis_type: AnalysisType
    prompt: str
    context: Optional[str] = None
    examples: Optional[List[str]] = None


class PromptOptimizer:
    """
    Optimizes prompts for AI-assisted code analysis.

    Provides specialized, well-structured prompts for different code analysis
    dimensions including syntax, style, security, performance, and best practices.
    """

    # Prompt templates for different analysis types
    PROMPT_TEMPLATES = {
        AnalysisType.SYNTAX: """Analyze the following {language} code for syntax errors and correctness:

```{language}
{code}
```

Provide:
1. List of syntax errors (if any)
2. Severity of each error (critical, major, minor)
3. Line numbers where errors occur
4. Suggested fixes

Format your response as JSON with this structure:
{{
    "errors": [
        {{"line": <number>, "severity": "<level>", "message": "<error>", "fix": "<suggestion>"}}
    ],
    "is_valid": <boolean>,
    "score": <0-100>
}}""",
        AnalysisType.STYLE: """Analyze the following {language} code for style compliance and readability:

```{language}
{code}
```

Evaluate against:
- Naming conventions (variables, functions, classes)
- Code formatting and indentation
- Comment quality and documentation
- Code organization and structure
- Idiomatic {language} patterns

Provide:
1. Style violations found
2. Recommendations for improvement
3. Overall style score (0-100)

Format your response as JSON:
{{
    "violations": [
        {{"line": <number>, "category": "<type>", "message": "<issue>", "suggestion": "<fix>"}}
    ],
    "score": <0-100>,
    "recommendations": ["<recommendation>", ...]
}}""",
        AnalysisType.SECURITY: """Analyze the following {language} code for security vulnerabilities:

```{language}
{code}
```

Check for:
- SQL injection vulnerabilities
- XSS (Cross-Site Scripting) risks
- Insecure data handling
- Authentication/authorization issues
- Cryptography misuse
- Input validation problems
- Information disclosure

Provide:
1. Security vulnerabilities found
2. Severity rating (critical, high, medium, low)
3. Detailed explanation of each vulnerability
4. Remediation recommendations

Format your response as JSON:
{{
    "vulnerabilities": [
        {{
            "line": <number>,
            "severity": "<level>",
            "type": "<vulnerability-type>",
            "description": "<details>",
            "remediation": "<fix>"
        }}
    ],
    "score": <0-100>,
    "overall_risk": "<level>"
}}""",
        AnalysisType.PERFORMANCE: """Analyze the following {language} code for performance optimization opportunities:

```{language}
{code}
```

Evaluate:
- Algorithm complexity (time and space)
- Inefficient operations or patterns
- Resource usage (memory, I/O, CPU)
- Optimization opportunities
- Scalability concerns

Provide:
1. Performance issues identified
2. Impact assessment (high, medium, low)
3. Optimization suggestions
4. Expected improvement

Format your response as JSON:
{{
    "issues": [
        {{
            "line": <number>,
            "impact": "<level>",
            "issue": "<description>",
            "optimization": "<suggestion>",
            "expected_improvement": "<details>"
        }}
    ],
    "score": <0-100>,
    "complexity": "<O-notation>"
}}""",
        AnalysisType.BEST_PRACTICES: """Analyze the following {language} code for adherence to best practices:

```{language}
{code}
```

Evaluate:
- Design patterns usage
- Error handling
- Code reusability
- Maintainability
- Testing considerations
- Documentation completeness
- SOLID principles (for OOP)

Provide:
1. Best practice violations
2. Recommendations for improvement
3. Overall best practices score

Format your response as JSON:
{{
    "violations": [
        {{
            "category": "<type>",
            "message": "<issue>",
            "recommendation": "<fix>"
        }}
    ],
    "score": <0-100>,
    "strengths": ["<positive>", ...],
    "improvements": ["<suggestion>", ...]
}}""",
        AnalysisType.OVERALL: """Perform a comprehensive code quality analysis of the following {language} code:

```{language}
{code}
```

Analyze across all dimensions:
1. Syntax correctness
2. Style and readability
3. Security vulnerabilities
4. Performance optimization
5. Best practices adherence

Provide:
1. Overall quality score (0-100)
2. Scores for each dimension
3. Top issues to address (prioritized)
4. Actionable recommendations

Format your response as JSON:
{{
    "overall_score": <0-100>,
    "dimension_scores": {{
        "syntax": <0-100>,
        "style": <0-100>,
        "security": <0-100>,
        "performance": <0-100>,
        "best_practices": <0-100>
    }},
    "top_issues": [
        {{"priority": "<level>", "category": "<type>", "message": "<issue>", "fix": "<suggestion>"}}
    ],
    "summary": "<overall-assessment>"
}}""",
    }

    def __init__(self):
        """Initialize the PromptOptimizer."""
        pass

    def optimize_for_analysis(
        self, code: str, language: str, analysis_type: AnalysisType, context: Optional[str] = None
    ) -> OptimizedPrompt:
        """
        Generate an optimized prompt for code analysis.

        Args:
            code: The code to analyze
            language: Programming language (python, javascript, etc.)
            analysis_type: Type of analysis to perform
            context: Optional additional context

        Returns:
            OptimizedPrompt with the optimized prompt string
        """
        template = self.PROMPT_TEMPLATES.get(analysis_type)
        if not template:
            raise ValueError(f"Unknown analysis type: {analysis_type}")

        # Format the prompt with code and language
        prompt = template.format(language=language, code=code)

        # Add context if provided
        if context:
            prompt = f"{context}\n\n{prompt}"

        return OptimizedPrompt(analysis_type=analysis_type, prompt=prompt, context=context)

    def get_batch_prompts(
        self, code: str, language: str, analysis_types: List[AnalysisType]
    ) -> Dict[AnalysisType, OptimizedPrompt]:
        """
        Generate multiple optimized prompts for batch analysis.

        Args:
            code: The code to analyze
            language: Programming language
            analysis_types: List of analysis types to generate prompts for

        Returns:
            Dictionary mapping analysis types to optimized prompts
        """
        return {
            analysis_type: self.optimize_for_analysis(code, language, analysis_type)
            for analysis_type in analysis_types
        }

    def get_all_prompts(self, code: str, language: str) -> Dict[AnalysisType, OptimizedPrompt]:
        """
        Generate prompts for all analysis types.

        Args:
            code: The code to analyze
            language: Programming language

        Returns:
            Dictionary mapping all analysis types to optimized prompts
        """
        return self.get_batch_prompts(code, language, list(AnalysisType))
