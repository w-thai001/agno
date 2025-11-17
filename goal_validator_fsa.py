"""
Goal Validator FSA - Finite State Automaton for validating goals using SMART criteria.

This module provides a production-ready implementation for validating goals based on
SMART criteria (Specific, Measurable, Achievable, Relevant, Time-bound) with
LQ-based scoring and constraint feasibility checking.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
import re
from datetime import datetime, timedelta


class ValidationState(Enum):
    """FSA states for goal validation process."""
    INITIAL = "initial"
    CHECKING_SPECIFIC = "checking_specific"
    CHECKING_MEASURABLE = "checking_measurable"
    CHECKING_ACHIEVABLE = "checking_achievable"
    CHECKING_RELEVANT = "checking_relevant"
    CHECKING_TIMEBOUND = "checking_timebound"
    ANALYZING_CONSTRAINTS = "analyzing_constraints"
    COMPUTING_SCORES = "computing_scores"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class ValidationResult:
    """Result of goal validation."""
    is_valid: bool
    clarity_score: float  # 0.0 to 1.0
    achievability_score: float  # 0.0 to 1.0
    overall_score: float  # 0.0 to 1.0
    recommendations: List[str] = field(default_factory=list)
    smart_scores: Dict[str, float] = field(default_factory=dict)
    constraint_issues: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class GoalValidatorFSA:
    """
    Finite State Automaton for validating goals using SMART criteria.

    This class implements a state machine that validates goals through multiple
    stages, checking for Specific, Measurable, Achievable, Relevant, and Time-bound
    criteria, along with constraint feasibility analysis.
    """

    def __init__(self, strict_mode: bool = False):
        """
        Initialize the Goal Validator FSA.

        Args:
            strict_mode: If True, all SMART criteria must score above threshold.
        """
        self.strict_mode = strict_mode
        self.state = ValidationState.INITIAL
        self._reset_state()

    def _reset_state(self) -> None:
        """Reset internal state for new validation."""
        self.state = ValidationState.INITIAL
        self._smart_scores: Dict[str, float] = {}
        self._recommendations: List[str] = []
        self._constraint_issues: List[str] = []
        self._errors: List[str] = []

    def validate_goal(
        self,
        goal: str,
        constraints: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """
        Validate a goal using SMART criteria and constraint analysis.

        Args:
            goal: The goal description to validate.
            constraints: Optional constraints dict with keys like:
                - max_duration: Maximum time allowed (e.g., "30 days")
                - min_resources: Minimum resources required
                - dependencies: List of prerequisite goals
                - budget: Maximum budget allowed
            context: Optional context dict with keys like:
                - user_level: User expertise level ("beginner", "intermediate", "advanced")
                - available_resources: Resources available to user
                - timeline: Expected timeline for completion
                - domain: Domain or category of the goal

        Returns:
            ValidationResult containing scores, recommendations, and issues.

        Raises:
            ValueError: If goal is empty or invalid.
            TypeError: If arguments are of wrong type.
        """
        self._reset_state()

        try:
            # Input validation
            if not isinstance(goal, str):
                raise TypeError(f"Goal must be a string, got {type(goal).__name__}")

            if not goal or not goal.strip():
                raise ValueError("Goal description cannot be empty")

            goal = goal.strip()
            constraints = constraints or {}
            context = context or {}

            # Validate input types
            if not isinstance(constraints, dict):
                raise TypeError(f"Constraints must be a dict, got {type(constraints).__name__}")
            if not isinstance(context, dict):
                raise TypeError(f"Context must be a dict, got {type(context).__name__}")

            # FSA State transitions
            self._transition_to(ValidationState.CHECKING_SPECIFIC)
            specific_score = self._check_specific(goal, context)

            self._transition_to(ValidationState.CHECKING_MEASURABLE)
            measurable_score = self._check_measurable(goal, context)

            self._transition_to(ValidationState.CHECKING_ACHIEVABLE)
            achievable_score = self._check_achievable(goal, constraints, context)

            self._transition_to(ValidationState.CHECKING_RELEVANT)
            relevant_score = self._check_relevant(goal, context)

            self._transition_to(ValidationState.CHECKING_TIMEBOUND)
            timebound_score = self._check_timebound(goal, constraints, context)

            # Store SMART scores
            self._smart_scores = {
                "specific": specific_score,
                "measurable": measurable_score,
                "achievable": achievable_score,
                "relevant": relevant_score,
                "timebound": timebound_score
            }

            self._transition_to(ValidationState.ANALYZING_CONSTRAINTS)
            self._analyze_constraints(goal, constraints, context)

            self._transition_to(ValidationState.COMPUTING_SCORES)
            clarity_score = self._compute_clarity_score()
            achievability_score = self._compute_achievability_score()
            overall_score = self._compute_overall_score(clarity_score, achievability_score)

            # Determine if goal is valid
            is_valid = self._determine_validity(overall_score)

            self._transition_to(ValidationState.COMPLETE)

            return ValidationResult(
                is_valid=is_valid,
                clarity_score=clarity_score,
                achievability_score=achievability_score,
                overall_score=overall_score,
                recommendations=self._recommendations.copy(),
                smart_scores=self._smart_scores.copy(),
                constraint_issues=self._constraint_issues.copy(),
                errors=self._errors.copy(),
                metadata={
                    "goal_length": len(goal),
                    "word_count": len(goal.split()),
                    "has_constraints": bool(constraints),
                    "has_context": bool(context),
                    "strict_mode": self.strict_mode
                }
            )

        except (ValueError, TypeError) as e:
            self._transition_to(ValidationState.ERROR)
            self._errors.append(str(e))
            raise
        except Exception as e:
            self._transition_to(ValidationState.ERROR)
            self._errors.append(f"Unexpected error: {str(e)}")
            raise

    def _transition_to(self, new_state: ValidationState) -> None:
        """Transition to a new validation state."""
        self.state = new_state

    def _check_specific(self, goal: str, context: Dict[str, Any]) -> float:
        """
        Check if goal is Specific (clear and well-defined).

        Uses LQ-based scoring to evaluate specificity based on:
        - Presence of action verbs
        - Concrete nouns and details
        - Question words (what, why, who, where, which)
        - Length and detail level
        """
        score = 0.0

        # Check for action verbs (stronger specificity)
        action_verbs = [
            r'\b(create|build|develop|implement|design|write|complete|achieve|'
            r'increase|decrease|improve|reduce|learn|master|finish|deliver|'
            r'launch|release|deploy|optimize|refactor|test)\b'
        ]
        if any(re.search(pattern, goal.lower()) for pattern in action_verbs):
            score += 0.3

        # Check for specific details (numbers, percentages, quantities)
        if re.search(r'\b\d+\b|[0-9]+%|\d+\.\d+', goal):
            score += 0.25

        # Check for concrete nouns and proper nouns
        words = goal.split()
        if len(words) >= 5:  # Sufficient detail
            score += 0.2

        # Check for specificity keywords
        specificity_keywords = r'\b(specific|exactly|precisely|particular|certain|explicit)\b'
        if re.search(specificity_keywords, goal.lower()):
            score += 0.15

        # Penalize vague language
        vague_terms = r'\b(something|somehow|maybe|perhaps|might|could|some|thing|stuff)\b'
        if re.search(vague_terms, goal.lower()):
            score -= 0.2
            self._recommendations.append(
                "Make the goal more specific by replacing vague terms with concrete details"
            )

        # Context bonus
        if context.get("domain"):
            score += 0.1

        score = max(0.0, min(1.0, score))

        if score < 0.6:
            self._recommendations.append(
                "Increase specificity by adding what, why, who, where, and which details"
            )

        return score

    def _check_measurable(self, goal: str, context: Dict[str, Any]) -> float:
        """
        Check if goal is Measurable (has quantifiable criteria).

        Looks for metrics, numbers, percentages, and measurable outcomes.
        """
        score = 0.0

        # Check for numbers and percentages
        if re.search(r'\b\d+\b', goal):
            score += 0.3

        if re.search(r'\d+%', goal):
            score += 0.2

        # Check for measurement keywords
        measurement_terms = [
            r'\b(metric|measure|track|count|number|amount|quantity|rate|'
            r'percentage|ratio|score|value|level|degree)\b',
            r'\b(increase|decrease|improve|reduce|grow|decline) by\b'
        ]
        if any(re.search(pattern, goal.lower()) for pattern in measurement_terms):
            score += 0.25

        # Check for comparison words
        comparison_terms = r'\b(more|less|better|worse|higher|lower|faster|slower|from|to)\b'
        if re.search(comparison_terms, goal.lower()):
            score += 0.15

        # Check for units of measurement
        unit_terms = r'\b(days|weeks|months|years|hours|minutes|dollars|points|items|units|KB|MB|GB)\b'
        if re.search(unit_terms, goal.lower(), re.IGNORECASE):
            score += 0.1

        score = max(0.0, min(1.0, score))

        if score < 0.6:
            self._recommendations.append(
                "Add measurable criteria: include specific numbers, percentages, or quantifiable metrics"
            )

        return score

    def _check_achievable(
        self,
        goal: str,
        constraints: Dict[str, Any],
        context: Dict[str, Any]
    ) -> float:
        """
        Check if goal is Achievable (realistic and attainable).

        Considers user level, available resources, and constraints.
        """
        score = 0.7  # Start with optimistic baseline

        # Check user level vs. goal complexity
        user_level = context.get("user_level", "intermediate")
        goal_lower = goal.lower()

        # Complex terms that might be challenging
        complex_terms = [
            "advanced", "complex", "sophisticated", "comprehensive",
            "enterprise", "large-scale", "distributed"
        ]
        complexity_count = sum(1 for term in complex_terms if term in goal_lower)

        if user_level == "beginner" and complexity_count > 2:
            score -= 0.3
            self._recommendations.append(
                "Goal may be too complex for beginner level - consider breaking into smaller goals"
            )
        elif user_level == "intermediate" and complexity_count > 3:
            score -= 0.15

        # Check resource availability
        available_resources = context.get("available_resources", {})
        if isinstance(available_resources, dict):
            if available_resources.get("time") == "limited":
                score -= 0.1
            if available_resources.get("budget") == "limited":
                score -= 0.1

        # Check for realistic language
        realistic_terms = r'\b(realistic|achievable|feasible|attainable|practical|reasonable)\b'
        if re.search(realistic_terms, goal_lower):
            score += 0.1

        # Check for overly ambitious language
        ambitious_terms = r'\b(revolutionary|groundbreaking|world-class|perfect|flawless|unlimited)\b'
        if re.search(ambitious_terms, goal_lower):
            score -= 0.2
            self._recommendations.append(
                "Goal may be overly ambitious - consider more realistic objectives"
            )

        # Budget constraint check
        if "budget" in constraints:
            budget = constraints["budget"]
            if isinstance(budget, (int, float)) and budget < 100:
                score -= 0.15
                self._constraint_issues.append(
                    f"Limited budget ({budget}) may affect achievability"
                )

        score = max(0.0, min(1.0, score))

        if score < 0.5:
            self._recommendations.append(
                "Improve achievability by ensuring resources and skills are available"
            )

        return score

    def _check_relevant(self, goal: str, context: Dict[str, Any]) -> float:
        """
        Check if goal is Relevant (worthwhile and aligned with objectives).

        Evaluates purpose, value, and alignment with context.
        """
        score = 0.6  # Baseline assumption of relevance

        goal_lower = goal.lower()

        # Check for purpose/value keywords
        purpose_terms = [
            r'\b(because|in order to|so that|to enable|to support|to achieve)\b',
            r'\b(important|critical|essential|key|vital|crucial|necessary)\b',
            r'\b(benefit|value|impact|outcome|result|advantage)\b'
        ]
        if any(re.search(pattern, goal_lower) for pattern in purpose_terms):
            score += 0.2

        # Check domain alignment
        if context.get("domain"):
            domain = context["domain"].lower()
            if domain in goal_lower:
                score += 0.15

        # Check for alignment keywords
        alignment_terms = r'\b(align|support|contribute|advance|further|enhance|complement)\b'
        if re.search(alignment_terms, goal_lower):
            score += 0.05

        # Check for irrelevant or off-topic indicators
        if re.search(r'\b(random|arbitrary|unrelated|pointless)\b', goal_lower):
            score -= 0.3
            self._recommendations.append(
                "Ensure goal is relevant to your broader objectives"
            )

        score = max(0.0, min(1.0, score))

        if score < 0.6:
            self._recommendations.append(
                "Clarify why this goal is relevant and how it aligns with larger objectives"
            )

        return score

    def _check_timebound(
        self,
        goal: str,
        constraints: Dict[str, Any],
        context: Dict[str, Any]
    ) -> float:
        """
        Check if goal is Time-bound (has a deadline or time frame).

        Looks for dates, durations, and time-related constraints.
        """
        score = 0.0

        goal_lower = goal.lower()

        # Check for specific dates or time frames
        date_patterns = [
            r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',  # 12/31/2024
            r'\b\d{4}-\d{2}-\d{2}\b',  # 2024-12-31
            r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}\b',
            r'\b\d{1,2}\s+(january|february|march|april|may|june|july|august|september|october|november|december)\b'
        ]
        if any(re.search(pattern, goal_lower) for pattern in date_patterns):
            score += 0.4

        # Check for duration terms
        duration_patterns = [
            r'\b(in|within|by|before|after|until)\s+\d+\s+(day|week|month|year|hour)s?\b',
            r'\b\d+\s+(day|week|month|year|hour)s?\b',
            r'\bby\s+(tomorrow|next week|next month|end of|Q[1-4])\b'
        ]
        if any(re.search(pattern, goal_lower) for pattern in duration_patterns):
            score += 0.35

        # Check for deadline keywords
        deadline_terms = r'\b(deadline|due date|target date|completion date|by the end of)\b'
        if re.search(deadline_terms, goal_lower):
            score += 0.15

        # Check timeline in context
        if context.get("timeline"):
            score += 0.1

        # Check max_duration constraint
        if "max_duration" in constraints:
            score += 0.1

        score = max(0.0, min(1.0, score))

        if score < 0.5:
            self._recommendations.append(
                "Add a specific deadline or time frame (e.g., 'by December 31' or 'within 3 months')"
            )

        return score

    def _analyze_constraints(
        self,
        goal: str,
        constraints: Dict[str, Any],
        context: Dict[str, Any]
    ) -> None:
        """Analyze constraint feasibility and identify potential issues."""

        # Check dependencies
        if "dependencies" in constraints:
            deps = constraints["dependencies"]
            if isinstance(deps, list) and len(deps) > 5:
                self._constraint_issues.append(
                    f"High number of dependencies ({len(deps)}) may complicate achievement"
                )

        # Check max_duration constraint
        if "max_duration" in constraints:
            duration_str = str(constraints["max_duration"])
            # Parse duration
            match = re.search(r'(\d+)\s*(day|week|month|year)s?', duration_str.lower())
            if match:
                amount = int(match.group(1))
                unit = match.group(2)

                # Check if goal mentions longer duration
                goal_lower = goal.lower()
                if unit == "day" and amount < 7 and re.search(r'\d+\s*weeks?', goal_lower):
                    self._constraint_issues.append(
                        "Goal timeline may exceed max_duration constraint"
                    )
                elif unit == "week" and amount < 4 and re.search(r'\d+\s*months?', goal_lower):
                    self._constraint_issues.append(
                        "Goal timeline may exceed max_duration constraint"
                    )

        # Check min_resources constraint
        if "min_resources" in constraints:
            min_res = constraints["min_resources"]
            available = context.get("available_resources", {})
            if isinstance(available, dict) and isinstance(min_res, dict):
                for resource, min_amount in min_res.items():
                    available_amount = available.get(resource, 0)
                    if available_amount < min_amount:
                        self._constraint_issues.append(
                            f"Insufficient {resource}: need {min_amount}, have {available_amount}"
                        )

        # Check budget constraint
        if "budget" in constraints:
            budget = constraints["budget"]
            if isinstance(budget, (int, float)) and budget == 0:
                self._constraint_issues.append(
                    "Zero budget constraint may limit achievability"
                )

    def _compute_clarity_score(self) -> float:
        """
        Compute clarity score using LQ-based assessment.

        Clarity is derived from Specific and Measurable scores.
        """
        specific = self._smart_scores.get("specific", 0.0)
        measurable = self._smart_scores.get("measurable", 0.0)

        # Weighted average with emphasis on specificity
        clarity = 0.6 * specific + 0.4 * measurable

        return round(clarity, 3)

    def _compute_achievability_score(self) -> float:
        """
        Compute achievability score.

        Derived from Achievable, Relevant, and Time-bound scores.
        """
        achievable = self._smart_scores.get("achievable", 0.0)
        relevant = self._smart_scores.get("relevant", 0.0)
        timebound = self._smart_scores.get("timebound", 0.0)

        # Weighted average
        achievability = 0.5 * achievable + 0.25 * relevant + 0.25 * timebound

        # Apply penalty for constraint issues
        if self._constraint_issues:
            penalty = min(0.2, len(self._constraint_issues) * 0.05)
            achievability -= penalty

        return round(max(0.0, achievability), 3)

    def _compute_overall_score(self, clarity: float, achievability: float) -> float:
        """Compute overall goal quality score."""
        # Balanced combination of clarity and achievability
        overall = 0.5 * clarity + 0.5 * achievability

        return round(overall, 3)

    def _determine_validity(self, overall_score: float) -> bool:
        """
        Determine if goal is valid based on overall score and mode.

        Args:
            overall_score: The computed overall quality score.

        Returns:
            True if goal meets validity criteria.
        """
        if self.strict_mode:
            # In strict mode, all SMART components must be >= 0.6
            return all(score >= 0.6 for score in self._smart_scores.values())
        else:
            # In normal mode, overall score >= 0.5 is acceptable
            return overall_score >= 0.5


def main():
    """Example usage of GoalValidatorFSA."""
    validator = GoalValidatorFSA()

    # Example 1: Well-formed SMART goal
    goal1 = "Implement a user authentication system with JWT tokens and OAuth2 support by December 31, 2024"
    result1 = validator.validate_goal(
        goal=goal1,
        constraints={"max_duration": "60 days", "budget": 5000},
        context={"user_level": "intermediate", "domain": "web development"}
    )

    print("Example 1: Well-formed goal")
    print(f"Valid: {result1.is_valid}")
    print(f"Clarity: {result1.clarity_score}")
    print(f"Achievability: {result1.achievability_score}")
    print(f"Overall: {result1.overall_score}")
    print(f"SMART Scores: {result1.smart_scores}")
    print(f"Recommendations: {result1.recommendations}\n")

    # Example 2: Vague goal
    goal2 = "Do something with the website"
    result2 = validator.validate_goal(goal=goal2)

    print("Example 2: Vague goal")
    print(f"Valid: {result2.is_valid}")
    print(f"Overall: {result2.overall_score}")
    print(f"Recommendations: {result2.recommendations}\n")


if __name__ == "__main__":
    main()
