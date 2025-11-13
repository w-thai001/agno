"""
Goal Analyzer for MLA Framework

Infers optimal goal G' when not explicitly provided and applies
MLA meta-level optimization.
"""

from typing import Dict, List, Optional

from agno.fsa_0_1_mla_task_deconstructor.config import config
from agno.fsa_0_1_mla_task_deconstructor.models.goal_model import Goal


class GoalAnalyzer:
    """
    Analyzes task descriptions to infer optimal goals using MLA Goal Derivation Logic.

    Applies MLA meta-level optimization to ensure goal alignment.
    """

    def __init__(self):
        """Initialize goal analyzer"""
        pass

    def analyze(self, parsed_task: Dict[str, any]) -> Goal:
        """
        Analyze parsed task and infer/validate the optimal goal.

        Args:
            parsed_task: Parsed task data from TaskParser

        Returns:
            Goal object with G, O_G, and confidence score
        """
        # Check if goal is explicitly stated
        if parsed_task.get("explicit_goal"):
            return self._create_explicit_goal(parsed_task)
        else:
            return self._infer_goal(parsed_task)

    def _create_explicit_goal(self, parsed_task: Dict[str, any]) -> Goal:
        """
        Create goal from explicit statement.

        Args:
            parsed_task: Parsed task data

        Returns:
            Goal object
        """
        goal_text = parsed_task["explicit_goal"]

        # Derive outcome criteria from success criteria or description
        outcome_criteria = self._derive_outcome_criteria(parsed_task)

        # Extract constraints
        constraints = parsed_task.get("constraints", [])

        # Extract success metrics
        success_metrics = parsed_task.get("success_criteria", [])

        return Goal(
            G=goal_text,
            O_G=outcome_criteria,
            confidence=0.95,  # High confidence when explicitly stated
            explicit=True,
            context=parsed_task.get("context"),
            constraints=constraints,
            success_metrics=success_metrics,
        )

    def _infer_goal(self, parsed_task: Dict[str, any]) -> Goal:
        """
        Infer optimal goal from task description using MLA Goal Derivation Logic.

        Applies the question: "What is the actual outcome I want to achieve?"

        Args:
            parsed_task: Parsed task data

        Returns:
            Inferred goal with confidence score
        """
        description = parsed_task["description"]

        # Apply MLA Goal Derivation Logic
        # 1. Extract the core outcome
        inferred_goal = self._extract_core_outcome(description)

        # 2. Derive outcome criteria
        outcome_criteria = self._derive_outcome_criteria(parsed_task)

        # 3. Calculate confidence based on clarity and specificity
        confidence = self._calculate_goal_confidence(parsed_task, inferred_goal)

        # Extract constraints
        constraints = parsed_task.get("constraints", [])

        # Extract success metrics
        success_metrics = parsed_task.get("success_criteria", [])

        return Goal(
            G=inferred_goal,
            O_G=outcome_criteria,
            confidence=confidence,
            explicit=False,
            context=parsed_task.get("context"),
            constraints=constraints,
            success_metrics=success_metrics,
        )

    def _extract_core_outcome(self, description: str) -> str:
        """
        Extract the core outcome from task description.

        Args:
            description: Task description

        Returns:
            Core outcome/goal
        """
        # Heuristic: Look for outcome-oriented keywords
        import re

        # Pattern 1: "to achieve/accomplish/deliver X"
        pattern1 = r"(?:to|for)\s+(?:achieve|accomplish|deliver|create|build|develop)\s+(.+?)(?:\.|$)"
        match1 = re.search(pattern1, description, re.IGNORECASE)
        if match1:
            return match1.group(1).strip()

        # Pattern 2: Extract main action + object
        # "Build X", "Create Y", "Write Z"
        pattern2 = r"^(build|create|write|develop|implement|design)\s+(.+?)(?:\.|$)"
        match2 = re.search(pattern2, description, re.IGNORECASE)
        if match2:
            action = match2.group(1)
            object_desc = match2.group(2).strip()
            return f"{action.capitalize()} {object_desc}"

        # Default: Use first sentence as goal
        first_sentence = description.split(".")[0].strip()
        return first_sentence

    def _derive_outcome_criteria(self, parsed_task: Dict[str, any]) -> str:
        """
        Derive O_G (outcome criteria) from task information.

        Args:
            parsed_task: Parsed task data

        Returns:
            Outcome criteria description
        """
        # Check for explicit success criteria
        success_criteria = parsed_task.get("success_criteria", [])
        if success_criteria:
            return "; ".join(success_criteria)

        # Infer from description
        description = parsed_task["description"]

        # Look for measurable outcomes
        import re

        measurable_patterns = [
            r"(?:result in|produce|achieve)\s+(.+?)(?:\.|$)",
            r"(?:successful|complete)(?:\s+when|\s+if)\s+(.+?)(?:\.|$)",
        ]

        for pattern in measurable_patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        # Default outcome criteria
        return f"Successfully complete: {description.split('.')[0]}"

    def _calculate_goal_confidence(
        self, parsed_task: Dict[str, any], inferred_goal: str
    ) -> float:
        """
        Calculate confidence in inferred goal.

        Args:
            parsed_task: Parsed task data
            inferred_goal: Inferred goal text

        Returns:
            Confidence score (0.0-1.0)
        """
        confidence = 0.5  # Base confidence for inferred goals

        # Increase confidence if:
        # 1. Task has clear action verbs
        if any(
            verb in parsed_task["description"].lower()
            for verb in ["build", "create", "write", "develop", "implement"]
        ):
            confidence += 0.15

        # 2. Task has success criteria
        if parsed_task.get("success_criteria"):
            confidence += 0.15

        # 3. Task has constraints (specificity)
        if parsed_task.get("constraints"):
            confidence += 0.10

        # 4. Inferred goal is specific (longer, more detailed)
        if len(inferred_goal.split()) > 5:
            confidence += 0.10

        return min(1.0, confidence)

    def generate_clarifying_questions(
        self, goal: Goal, parsed_task: Dict[str, any]
    ) -> List[str]:
        """
        Generate clarifying questions for context elicitation.

        Following Proactive Context Elicitation Protocol.

        Args:
            goal: Analyzed goal
            parsed_task: Parsed task data

        Returns:
            List of clarifying questions
        """
        questions = []

        # If confidence is low, ask about goal
        if goal.confidence < config.GOAL_CONFIDENCE_MEDIUM:
            questions.append(f"Is your goal to: {goal.G}? Please clarify if different.")

        # Ask about success criteria if missing
        if not goal.success_metrics:
            questions.append("What does success look like for this task?")

        # Ask about constraints if missing
        if not goal.constraints:
            questions.append("Are there any constraints (time, budget, resources)?")

        # Ask about priorities if multiple components
        if len(parsed_task.get("description", "").split(".")) > 2:
            questions.append("Which aspect of this task is most important?")

        # Ask about resources if not specified
        if not parsed_task.get("resources"):
            questions.append("What tools or resources do you have available?")

        # Limit to max questions
        return questions[: config.MAX_CLARIFYING_QUESTIONS]

    def validate_goal_alignment(self, goal: Goal, actions: List[str]) -> bool:
        """
        Validate that proposed actions align with goal.

        Args:
            goal: Target goal
            actions: List of action descriptions

        Returns:
            True if actions appear aligned with goal
        """
        # Extract key terms from goal
        goal_terms = set(goal.G.lower().split())

        # Check if actions reference goal terms
        alignment_count = 0
        for action in actions:
            action_terms = set(action.lower().split())
            if goal_terms.intersection(action_terms):
                alignment_count += 1

        # At least 50% of actions should reference goal terms
        alignment_ratio = alignment_count / len(actions) if actions else 0
        return alignment_ratio >= 0.5
