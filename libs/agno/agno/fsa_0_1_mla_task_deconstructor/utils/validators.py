"""
Validation utilities for MLA Framework

Validates goal alignment, fractal MLA alignment, and risk assessment.
"""

from dataclasses import dataclass
from typing import List

from agno.fsa_0_1_mla_task_deconstructor.models.action_model import Action
from agno.fsa_0_1_mla_task_deconstructor.models.goal_model import Goal
from agno.fsa_0_1_mla_task_deconstructor.models.mla_framework import MLAFramework


@dataclass
class ValidationResult:
    """
    Result of validation check.

    Attributes:
        valid: Whether validation passed
        message: Validation message
        warnings: List of warnings
        risks: List of identified risks
    """

    valid: bool
    message: str
    warnings: List[str] = None
    risks: List[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
        if self.risks is None:
            self.risks = []

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "valid": self.valid,
            "message": self.message,
            "warnings": self.warnings,
            "risks": self.risks,
        }


class Validator:
    """
    Validates MLA framework components and outputs.
    """

    @staticmethod
    def validate_goal_alignment(goal: Goal, actions: List[Action]) -> ValidationResult:
        """
        Validate that actions align with goal.

        Args:
            goal: Target goal
            actions: List of actions to validate

        Returns:
            ValidationResult
        """
        if not actions:
            return ValidationResult(valid=False, message="No actions provided", warnings=[], risks=[])

        # Extract goal keywords
        goal_keywords = set(word.lower() for word in goal.G.split() if len(word) > 3)

        # Check alignment
        aligned_count = 0
        warnings = []

        for action in actions:
            action_keywords = set(word.lower() for word in action.description.split() if len(word) > 3)
            overlap = goal_keywords.intersection(action_keywords)

            if overlap or action.calculate_lq_mla() >= 1.0:
                aligned_count += 1
            else:
                warnings.append(f"Action '{action.action_id}' may not align with goal: {action.description}")

        alignment_ratio = aligned_count / len(actions)

        if alignment_ratio >= 0.8:
            return ValidationResult(
                valid=True,
                message=f"Strong goal alignment ({alignment_ratio:.0%})",
                warnings=warnings,
            )
        elif alignment_ratio >= 0.5:
            return ValidationResult(
                valid=True,
                message=f"Moderate goal alignment ({alignment_ratio:.0%})",
                warnings=warnings,
            )
        else:
            return ValidationResult(
                valid=False,
                message=f"Weak goal alignment ({alignment_ratio:.0%})",
                warnings=warnings,
                risks=["Many actions may not contribute to goal achievement"],
            )

    @staticmethod
    def validate_fractal_mla_alignment(actions: List[Action], goal: Goal) -> ValidationResult:
        """
        Validate fractal MLA alignment.

        Ensures all actions and sub-actions are MLA-optimized.

        Args:
            actions: List of actions
            goal: Target goal

        Returns:
            ValidationResult
        """
        misaligned = []

        for action in actions:
            if not MLAFramework.validate_fractal_alignment(action, goal):
                misaligned.append(action.action_id)

        if not misaligned:
            return ValidationResult(
                valid=True, message="All actions are fractally MLA-aligned", warnings=[]
            )
        else:
            return ValidationResult(
                valid=False,
                message=f"{len(misaligned)} actions are not fractally aligned",
                warnings=[f"Action {aid} has sub-optimal LQ_MLA" for aid in misaligned],
            )

    @staticmethod
    def assess_risks(goal: Goal, actions: List[Action], context: dict = None) -> List[str]:
        """
        Assess risks in the plan.

        Args:
            goal: Target goal
            actions: List of actions
            context: Additional context

        Returns:
            List of identified risks
        """
        risks = []
        context = context or {}

        # Risk 1: Low goal confidence
        if goal.confidence < 0.6:
            risks.append(
                f"Goal confidence is low ({goal.confidence:.0%}). "
                "Consider clarifying the objective before proceeding."
            )

        # Risk 2: Circular dependencies
        action_map = {a.action_id: a for a in actions}
        visited = set()
        rec_stack = set()

        def has_cycle(action_id):
            visited.add(action_id)
            rec_stack.add(action_id)

            action = action_map.get(action_id)
            if action:
                for dep_id in action.dependencies:
                    if dep_id not in visited:
                        if has_cycle(dep_id):
                            return True
                    elif dep_id in rec_stack:
                        return True

            rec_stack.remove(action_id)
            return False

        for action in actions:
            if action.action_id not in visited:
                if has_cycle(action.action_id):
                    risks.append("Circular dependencies detected in action sequence")
                    break

        # Risk 3: Resource constraints
        if context.get("budget"):
            total_cost = sum(
                a.cost.resource_cost for a in actions
            )  # This is normalized, not actual cost
            if context["budget"] < 1000 and total_cost > 50:
                risks.append("Resource requirements may exceed budget constraints")

        # Risk 4: Timeline constraints
        if context.get("timeline"):
            total_time = sum(a.cost.time_minutes for a in actions)
            # Parse timeline (e.g., "3 days", "2 weeks")
            import re

            timeline_match = re.search(r"(\d+)\s+(day|week|hour)s?", str(context["timeline"]))
            if timeline_match:
                amount = int(timeline_match.group(1))
                unit = timeline_match.group(2)

                # Convert to minutes
                timeline_minutes = {
                    "hour": amount * 60,
                    "day": amount * 480,  # 8 hour work days
                    "week": amount * 2400,  # 5 day work weeks
                }.get(unit, 0)

                if total_time > timeline_minutes:
                    risks.append(
                        f"Estimated time ({total_time} min) exceeds timeline ({timeline_minutes} min)"
                    )

        # Risk 5: Low LQ actions
        low_lq_actions = [a for a in actions if a.calculate_lq_mla() < 0.5]
        if low_lq_actions:
            risks.append(
                f"{len(low_lq_actions)} actions have very low leverage (LQ < 0.5). "
                "Consider eliminating or optimizing."
            )

        return risks

    @staticmethod
    def validate_output_completeness(output: dict) -> ValidationResult:
        """
        Validate that output has all required fields.

        Args:
            output: Output dictionary to validate

        Returns:
            ValidationResult
        """
        required_fields = [
            "task_id",
            "original_task",
            "inferred_goal",
            "action_set",
            "recommended_sequence",
        ]

        missing = []
        for field in required_fields:
            if field not in output or output[field] is None:
                missing.append(field)

        if missing:
            return ValidationResult(
                valid=False, message=f"Missing required fields: {', '.join(missing)}", warnings=[]
            )

        return ValidationResult(valid=True, message="Output is complete", warnings=[])
