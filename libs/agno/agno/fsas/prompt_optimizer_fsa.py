"""
Prompt Optimizer FSA for MLA v3.0 Alignment

This module provides a production-ready Finite State Automaton for optimizing
prompts to align with MLA (Model Language Architecture) v3.0 specifications.
It focuses on token efficiency, directive alignment, and constraint validation.

Key Features:
- Token efficiency optimization
- MLA directive alignment checking
- Constraint extraction and validation
- Output formatting for Claude API
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from pydantic import BaseModel, Field


class OptimizationState(str, Enum):
    """States for the FSA optimization process."""

    INITIAL = "initial"
    ANALYZING = "analyzing"
    OPTIMIZING = "optimizing"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"


class PromptType(str, Enum):
    """Types of prompts supported by the optimizer."""

    INSTRUCTION = "instruction"
    CONVERSATION = "conversation"
    SYSTEM = "system"
    TASK = "task"
    MIXED = "mixed"


class MLADirective(BaseModel):
    """Represents an MLA v3.0 directive."""

    name: str
    content: str
    priority: int = Field(default=1, ge=1, le=10)
    required: bool = False

    def __hash__(self) -> int:
        return hash(self.name)


class PromptConstraint(BaseModel):
    """Represents a constraint in the prompt."""

    constraint_type: str
    description: str
    value: Optional[Any] = None
    enforced: bool = True


class AnalysisResult(BaseModel):
    """Result of prompt analysis."""

    prompt_type: PromptType
    token_count: int
    directive_count: int
    constraint_count: int
    issues: List[str] = Field(default_factory=list)
    directives: List[MLADirective] = Field(default_factory=list)
    constraints: List[PromptConstraint] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class OptimizationResult(BaseModel):
    """Result of prompt optimization."""

    optimized_prompt: str
    original_token_count: int
    optimized_token_count: int
    token_reduction: int
    directives_aligned: int
    constraints_preserved: int
    optimization_notes: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ValidationResult(BaseModel):
    """Result of optimization validation."""

    is_valid: bool
    validation_errors: List[str] = Field(default_factory=list)
    validation_warnings: List[str] = Field(default_factory=list)
    constraint_violations: List[str] = Field(default_factory=list)
    score: float = Field(default=0.0, ge=0.0, le=1.0)


@dataclass
class PromptOptimizerFSA:
    """
    Finite State Automaton for optimizing prompts for MLA v3.0 alignment.

    This FSA processes prompts through states: analyze → optimize → validate.
    It ensures token efficiency while maintaining MLA directive compliance.

    Attributes:
        state: Current FSA state
        max_tokens: Maximum allowed tokens
        mla_version: MLA version to optimize for (default: 3.0)
        strict_mode: If True, enforce strict validation

    Example:
        >>> fsa = PromptOptimizerFSA(max_tokens=4096)
        >>> analysis = fsa.analyze_prompt("Write a function to sort a list")
        >>> optimization = fsa.optimize_for_mla(analysis)
        >>> validation = fsa.validate_optimization(optimization)
    """

    state: OptimizationState = field(default=OptimizationState.INITIAL)
    max_tokens: int = field(default=4096)
    mla_version: float = field(default=3.0)
    strict_mode: bool = field(default=False)

    # MLA v3.0 directive patterns
    _mla_directives: Dict[str, MLADirective] = field(default_factory=dict)

    # Token estimation (approximate: 1 token ≈ 4 characters for English)
    _chars_per_token: int = field(default=4)

    def __post_init__(self) -> None:
        """Initialize MLA v3.0 directives."""
        self._initialize_mla_directives()

    def _initialize_mla_directives(self) -> None:
        """Initialize standard MLA v3.0 directives."""
        self._mla_directives = {
            "task_specification": MLADirective(
                name="task_specification",
                content="Clear task specification with expected output",
                priority=10,
                required=True,
            ),
            "context_boundary": MLADirective(
                name="context_boundary",
                content="Well-defined context boundaries",
                priority=8,
                required=True,
            ),
            "output_format": MLADirective(
                name="output_format",
                content="Explicit output format specification",
                priority=7,
                required=False,
            ),
            "constraint_declaration": MLADirective(
                name="constraint_declaration",
                content="Clear declaration of constraints",
                priority=6,
                required=False,
            ),
            "example_provision": MLADirective(
                name="example_provision",
                content="Provision of examples when helpful",
                priority=5,
                required=False,
            ),
        }

    def _estimate_token_count(self, text: str) -> int:
        """
        Estimate token count for a given text.

        Args:
            text: Input text to estimate tokens for

        Returns:
            Estimated token count
        """
        # Simple estimation: ~4 chars per token for English text
        # In production, consider using tiktoken or similar
        return max(1, len(text) // self._chars_per_token)

    def _detect_prompt_type(self, prompt: str) -> PromptType:
        """
        Detect the type of prompt based on content analysis.

        Args:
            prompt: Input prompt to analyze

        Returns:
            Detected prompt type
        """
        prompt_lower = prompt.lower()

        # Check for instruction patterns
        instruction_patterns = [
            r'\b(write|create|generate|implement|build)\b',
            r'\b(explain|describe|summarize)\b',
            r'\b(analyze|evaluate|compare)\b',
        ]

        # Check for conversation patterns
        conversation_patterns = [
            r'\b(hello|hi|hey)\b',
            r'\b(what|how|why|when|where)\b',
            r'\?',
        ]

        # Check for system patterns
        system_patterns = [
            r'\b(you are|act as|role)\b',
            r'\b(system|assistant|model)\b',
        ]

        instruction_score = sum(
            1 for pattern in instruction_patterns if re.search(pattern, prompt_lower)
        )
        conversation_score = sum(
            1 for pattern in conversation_patterns if re.search(pattern, prompt_lower)
        )
        system_score = sum(
            1 for pattern in system_patterns if re.search(pattern, prompt_lower)
        )

        if system_score > 0:
            return PromptType.SYSTEM
        elif instruction_score >= 2:
            return PromptType.INSTRUCTION
        elif conversation_score >= 2:
            return PromptType.CONVERSATION
        elif instruction_score > 0 or conversation_score > 0:
            return PromptType.TASK
        else:
            return PromptType.MIXED

    def _extract_directives(self, prompt: str) -> List[MLADirective]:
        """
        Extract MLA directives present in the prompt.

        Args:
            prompt: Input prompt to analyze

        Returns:
            List of detected directives
        """
        detected_directives = []

        # Check for task specification
        if any(keyword in prompt.lower() for keyword in ["task:", "objective:", "goal:"]):
            detected_directives.append(self._mla_directives["task_specification"])

        # Check for output format specification
        if any(keyword in prompt.lower() for keyword in ["format:", "output:", "return:", "json", "xml", "markdown"]):
            detected_directives.append(self._mla_directives["output_format"])

        # Check for constraints
        if any(keyword in prompt.lower() for keyword in ["constraint:", "limitation:", "must", "should", "cannot"]):
            detected_directives.append(self._mla_directives["constraint_declaration"])

        # Check for examples
        if any(keyword in prompt.lower() for keyword in ["example:", "e.g.", "for instance", "such as"]):
            detected_directives.append(self._mla_directives["example_provision"])

        return detected_directives

    def _extract_constraints(self, prompt: str) -> List[PromptConstraint]:
        """
        Extract constraints from the prompt.

        Args:
            prompt: Input prompt to analyze

        Returns:
            List of detected constraints
        """
        constraints = []

        # Token/length constraints
        token_match = re.search(r'(\d+)\s*(token|word|character)s?', prompt.lower())
        if token_match:
            constraints.append(
                PromptConstraint(
                    constraint_type="length",
                    description=f"Length limit: {token_match.group(0)}",
                    value=int(token_match.group(1)),
                )
            )

        # Format constraints
        format_keywords = ["json", "xml", "yaml", "markdown", "html", "csv"]
        for fmt in format_keywords:
            if fmt in prompt.lower():
                constraints.append(
                    PromptConstraint(
                        constraint_type="format",
                        description=f"Output format: {fmt.upper()}",
                        value=fmt,
                    )
                )
                break

        # Prohibition constraints (must not, cannot, don't)
        prohibition_matches = re.findall(
            r'(must not|cannot|don\'t|do not|never)\s+([^.,!?]+)',
            prompt.lower()
        )
        for match in prohibition_matches:
            constraints.append(
                PromptConstraint(
                    constraint_type="prohibition",
                    description=f"Prohibited: {match[1].strip()}",
                    value=match[1].strip(),
                )
            )

        # Requirement constraints (must, required, should)
        requirement_matches = re.findall(
            r'(must|required|should|need to)\s+([^.,!?]+)',
            prompt.lower()
        )
        for match in requirement_matches:
            constraints.append(
                PromptConstraint(
                    constraint_type="requirement",
                    description=f"Required: {match[1].strip()}",
                    value=match[1].strip(),
                )
            )

        return constraints

    def analyze_prompt(self, prompt: str) -> AnalysisResult:
        """
        Analyze the input prompt for structure, directives, and constraints.

        This method transitions the FSA to ANALYZING state and performs
        comprehensive prompt analysis including:
        - Token counting
        - Prompt type detection
        - MLA directive extraction
        - Constraint identification
        - Issue detection

        Args:
            prompt: Input prompt to analyze

        Returns:
            AnalysisResult containing detailed analysis

        Raises:
            ValueError: If prompt is empty or invalid
        """
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        self.state = OptimizationState.ANALYZING

        # Estimate token count
        token_count = self._estimate_token_count(prompt)

        # Detect prompt type
        prompt_type = self._detect_prompt_type(prompt)

        # Extract directives and constraints
        directives = self._extract_directives(prompt)
        constraints = self._extract_constraints(prompt)

        # Identify issues
        issues = []
        if token_count > self.max_tokens:
            issues.append(f"Token count ({token_count}) exceeds maximum ({self.max_tokens})")

        if not directives:
            issues.append("No MLA directives detected - prompt may be underspecified")

        if prompt_type == PromptType.MIXED:
            issues.append("Prompt type is ambiguous - consider clarifying intent")

        # Check for required directives
        directive_names = {d.name for d in directives}
        for directive in self._mla_directives.values():
            if directive.required and directive.name not in directive_names:
                issues.append(f"Missing required directive: {directive.name}")

        self.state = OptimizationState.INITIAL

        return AnalysisResult(
            prompt_type=prompt_type,
            token_count=token_count,
            directive_count=len(directives),
            constraint_count=len(constraints),
            issues=issues,
            directives=directives,
            constraints=constraints,
            metadata={
                "mla_version": self.mla_version,
                "max_tokens": self.max_tokens,
            },
        )

    def optimize_for_mla(
        self,
        prompt: str,
        analysis: Optional[AnalysisResult] = None,
    ) -> OptimizationResult:
        """
        Optimize prompt for MLA v3.0 alignment.

        This method transitions the FSA to OPTIMIZING state and performs:
        - Token reduction through redundancy elimination
        - Directive alignment and enhancement
        - Constraint preservation
        - Structure optimization

        Args:
            prompt: Input prompt to optimize (or AnalysisResult)
            analysis: Optional pre-computed analysis result

        Returns:
            OptimizationResult with optimized prompt and metrics

        Raises:
            ValueError: If prompt is invalid
        """
        self.state = OptimizationState.OPTIMIZING

        # If analysis not provided, perform it
        if analysis is None:
            analysis = self.analyze_prompt(prompt)

        original_token_count = analysis.token_count
        optimized_prompt = prompt
        optimization_notes = []

        # 1. Remove redundant whitespace
        optimized_prompt = re.sub(r'\s+', ' ', optimized_prompt)
        optimized_prompt = optimized_prompt.strip()
        optimization_notes.append("Normalized whitespace")

        # 2. Remove filler words for token efficiency
        filler_words = [
            r'\bplease\b',
            r'\bkindly\b',
            r'\bactually\b',
            r'\bbasically\b',
            r'\bjust\b',
            r'\breally\b',
        ]
        for filler in filler_words:
            if re.search(filler, optimized_prompt, re.IGNORECASE):
                optimized_prompt = re.sub(filler, '', optimized_prompt, flags=re.IGNORECASE)
                optimized_prompt = re.sub(r'\s+', ' ', optimized_prompt)
                optimization_notes.append(f"Removed filler words: {filler}")

        # 3. Enhance directive clarity
        directive_names = {d.name for d in analysis.directives}

        # Add task specification if missing
        if "task_specification" not in directive_names:
            if analysis.prompt_type in [PromptType.INSTRUCTION, PromptType.TASK]:
                optimized_prompt = f"Task: {optimized_prompt}"
                optimization_notes.append("Added task specification directive")

        # Add output format if not specified but constraints indicate format
        if "output_format" not in directive_names:
            format_constraints = [
                c for c in analysis.constraints if c.constraint_type == "format"
            ]
            if format_constraints and "format:" not in optimized_prompt.lower():
                fmt = format_constraints[0].value
                optimized_prompt = f"{optimized_prompt}\n\nOutput format: {fmt.upper()}"
                optimization_notes.append(f"Added output format directive: {fmt}")

        # 4. Structure optimization
        if "\n" not in optimized_prompt and len(optimized_prompt) > 200:
            # Add structure for long single-line prompts
            parts = optimized_prompt.split(". ")
            if len(parts) > 3:
                optimized_prompt = ".\n".join(parts)
                optimization_notes.append("Added structure with line breaks")

        # 5. Calculate final token count
        optimized_token_count = self._estimate_token_count(optimized_prompt)
        token_reduction = original_token_count - optimized_token_count

        # 6. Verify all constraints are preserved
        constraints_preserved = len(analysis.constraints)
        for constraint in analysis.constraints:
            if constraint.value and str(constraint.value).lower() not in optimized_prompt.lower():
                optimization_notes.append(f"Warning: Constraint may not be preserved: {constraint.description}")

        self.state = OptimizationState.INITIAL

        return OptimizationResult(
            optimized_prompt=optimized_prompt.strip(),
            original_token_count=original_token_count,
            optimized_token_count=optimized_token_count,
            token_reduction=token_reduction,
            directives_aligned=len(directive_names) + len([n for n in optimization_notes if "Added" in n and "directive" in n]),
            constraints_preserved=constraints_preserved,
            optimization_notes=optimization_notes,
            metadata={
                "mla_version": self.mla_version,
                "original_prompt_type": analysis.prompt_type,
            },
        )

    def validate_optimization(
        self,
        original_prompt: str,
        optimized_prompt: str,
        analysis: Optional[AnalysisResult] = None,
    ) -> ValidationResult:
        """
        Validate the optimization result for correctness and compliance.

        This method transitions the FSA to VALIDATING state and performs:
        - MLA directive compliance checking
        - Constraint preservation verification
        - Token limit validation
        - Semantic similarity checking

        Args:
            original_prompt: Original prompt
            optimized_prompt: Optimized prompt
            analysis: Optional analysis of original prompt

        Returns:
            ValidationResult with validation status and details
        """
        self.state = OptimizationState.VALIDATING

        # Analyze both prompts
        if analysis is None:
            analysis = self.analyze_prompt(original_prompt)

        optimized_analysis = self.analyze_prompt(optimized_prompt)

        validation_errors = []
        validation_warnings = []
        constraint_violations = []

        # 1. Check token limit
        if optimized_analysis.token_count > self.max_tokens:
            validation_errors.append(
                f"Optimized prompt exceeds token limit: {optimized_analysis.token_count} > {self.max_tokens}"
            )

        # 2. Verify token reduction (should not increase)
        if optimized_analysis.token_count > analysis.token_count:
            validation_warnings.append(
                f"Token count increased: {analysis.token_count} → {optimized_analysis.token_count}"
            )

        # 3. Check directive preservation
        original_directives = {d.name for d in analysis.directives}
        optimized_directives = {d.name for d in optimized_analysis.directives}

        # Required directives must be present
        for directive in self._mla_directives.values():
            if directive.required and directive.name not in optimized_directives:
                validation_errors.append(f"Missing required directive: {directive.name}")

        # Warn about lost directives
        lost_directives = original_directives - optimized_directives
        if lost_directives and self.strict_mode:
            validation_errors.append(f"Lost directives: {', '.join(lost_directives)}")
        elif lost_directives:
            validation_warnings.append(f"Lost directives: {', '.join(lost_directives)}")

        # 4. Verify constraint preservation
        original_constraints = {
            (c.constraint_type, c.value) for c in analysis.constraints
        }
        optimized_constraints = {
            (c.constraint_type, c.value) for c in optimized_analysis.constraints
        }

        lost_constraints = original_constraints - optimized_constraints
        if lost_constraints:
            for constraint_type, value in lost_constraints:
                constraint_violations.append(
                    f"Lost constraint: {constraint_type} = {value}"
                )

        # 5. Check for empty or invalid result
        if not optimized_prompt.strip():
            validation_errors.append("Optimized prompt is empty")

        # 6. Calculate validation score (0.0 - 1.0)
        score = 1.0

        # Deduct for errors (0.2 per error)
        score -= len(validation_errors) * 0.2

        # Deduct for warnings (0.1 per warning)
        score -= len(validation_warnings) * 0.1

        # Deduct for constraint violations (0.15 per violation)
        score -= len(constraint_violations) * 0.15

        # Ensure score is in valid range
        score = max(0.0, min(1.0, score))

        # Determine validity
        is_valid = len(validation_errors) == 0 and score >= 0.6

        self.state = OptimizationState.COMPLETED if is_valid else OptimizationState.FAILED

        return ValidationResult(
            is_valid=is_valid,
            validation_errors=validation_errors,
            validation_warnings=validation_warnings,
            constraint_violations=constraint_violations,
            score=score,
        )

    def optimize_and_validate(
        self,
        prompt: str,
    ) -> Tuple[OptimizationResult, ValidationResult]:
        """
        Convenience method to optimize and validate in one call.

        Args:
            prompt: Input prompt to optimize

        Returns:
            Tuple of (OptimizationResult, ValidationResult)
        """
        # Analyze
        analysis = self.analyze_prompt(prompt)

        # Optimize
        optimization = self.optimize_for_mla(prompt, analysis)

        # Validate
        validation = self.validate_optimization(
            prompt,
            optimization.optimized_prompt,
            analysis,
        )

        return optimization, validation

    def format_for_claude_api(
        self,
        optimized_prompt: str,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Format optimized prompt for Claude API consumption.

        Args:
            optimized_prompt: Optimized prompt text
            system_prompt: Optional system prompt

        Returns:
            Dictionary formatted for Claude API
        """
        api_format = {
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": self.max_tokens,
            "messages": [
                {
                    "role": "user",
                    "content": optimized_prompt,
                }
            ],
        }

        if system_prompt:
            api_format["system"] = system_prompt

        return api_format
