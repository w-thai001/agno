"""
Context Elicitor for MLA Framework

Implements Proactive Context Elicitation Protocol.
"""

from typing import Dict, List

from agno.fsa_0_1_mla_task_deconstructor.models.goal_model import Goal


class ContextElicitor:
    """
    Generates clarifying questions to elicit missing context.

    Follows Proactive Context Elicitation Protocol from MLA v3.0.
    """

    @staticmethod
    def elicit_questions(goal: Goal, parsed_task: Dict[str, any]) -> List[str]:
        """
        Generate context elicitation questions.

        Args:
            goal: Analyzed goal
            parsed_task: Parsed task data

        Returns:
            List of clarifying questions
        """
        questions = []

        # 1. Goal clarification (if confidence is low)
        if goal.confidence < 0.7:
            questions.append(
                f"I interpreted your goal as: '{goal.G}'. Is this correct? "
                "Please clarify if your objective is different."
            )

        # 2. Success criteria
        if not goal.success_metrics and not parsed_task.get("success_criteria"):
            questions.append("What does success look like for this task? What specific outcomes should be achieved?")

        # 3. Constraints
        if not goal.constraints and not parsed_task.get("constraints"):
            questions.append("Are there any constraints I should know about (time, budget, resources, dependencies)?")

        # 4. Timeline
        if not parsed_task.get("timeline"):
            questions.append("What is your timeline for completing this task?")

        # 5. Resources
        if not parsed_task.get("resources"):
            questions.append("What tools, resources, or capabilities do you have available?")

        # 6. Context/Background
        if not parsed_task.get("context"):
            questions.append("Is there any additional context or background I should consider?")

        # 7. Priorities (if multiple components detected)
        task_desc = parsed_task.get("description", "")
        if "and" in task_desc.lower() or len(task_desc.split(".")) > 2:
            questions.append("If you had to prioritize, which aspect of this task is most important?")

        # Limit to reasonable number
        return questions[:5]

    @staticmethod
    def generate_confirmation_prompt(goal: Goal) -> str:
        """
        Generate a confirmation prompt for goal validation.

        Args:
            goal: Analyzed goal

        Returns:
            Confirmation prompt
        """
        if goal.explicit:
            return f"I understand your goal is: {goal.G}\nIs this correct?"
        else:
            confidence_pct = int(goal.confidence * 100)
            return (
                f"Based on your input, I inferred your goal is: {goal.G}\n"
                f"(Confidence: {confidence_pct}%)\n"
                f"Is this interpretation correct?"
            )

    @staticmethod
    def suggest_refinements(parsed_task: Dict[str, any], actions: List[any]) -> List[str]:
        """
        Suggest refinements to improve task specification.

        Args:
            parsed_task: Parsed task data
            actions: List of identified actions

        Returns:
            List of refinement suggestions
        """
        suggestions = []

        # 1. Vague task description
        if len(parsed_task.get("description", "").split()) < 5:
            suggestions.append("Your task description is quite brief. More details would help me provide a better breakdown.")

        # 2. Too many actions (overly complex)
        if len(actions) > 10:
            suggestions.append(
                "This task has many components. Consider breaking it into smaller, focused tasks for better clarity."
            )

        # 3. No quantifiable metrics
        has_metrics = any(
            metric_word in parsed_task.get("description", "").lower()
            for metric_word in ["number", "percent", "amount", "quantity", "measure"]
        )
        if not has_metrics and not parsed_task.get("success_criteria"):
            suggestions.append("Consider adding measurable success criteria to track progress objectively.")

        return suggestions
