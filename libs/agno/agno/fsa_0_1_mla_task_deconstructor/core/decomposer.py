"""
Task Decomposer for MLA Framework

Recursively decomposes complex tasks into atomic actions with dependency tracking.
"""

from typing import Dict, List, Optional

from agno.fsa_0_1_mla_task_deconstructor.config import config
from agno.fsa_0_1_mla_task_deconstructor.core.lq_calculator import LQCalculator
from agno.fsa_0_1_mla_task_deconstructor.models.action_model import Action
from agno.fsa_0_1_mla_task_deconstructor.models.goal_model import Goal


class TaskDecomposer:
    """
    Decomposes tasks into atomic actions using recursive breakdown.

    Generates dependency graphs and maintains goal alignment.
    """

    def __init__(self, lq_calculator: Optional[LQCalculator] = None):
        """
        Initialize task decomposer.

        Args:
            lq_calculator: LQ calculator for action estimation
        """
        self.lq_calculator = lq_calculator or LQCalculator()

    def decompose(
        self, task_description: str, goal: Goal, context: Dict[str, any] = None, depth: int = 0
    ) -> List[Action]:
        """
        Decompose a task into atomic actions.

        Args:
            task_description: Description of the task to decompose
            goal: Target goal
            context: Additional context
            depth: Current decomposition depth

        Returns:
            List of atomic actions
        """
        context = context or {}

        # Check max depth
        if depth >= config.MAX_DECOMPOSITION_DEPTH:
            # Create single atomic action at max depth
            return [
                self.lq_calculator.create_action(
                    action_id=f"a{depth}_1",
                    description=task_description,
                    goal=goal,
                    context=context,
                )
            ]

        # Check if task is already atomic
        if self._is_atomic(task_description, context):
            return [
                self.lq_calculator.create_action(
                    action_id=f"a{depth}_1",
                    description=task_description,
                    goal=goal,
                    context=context,
                )
            ]

        # Decompose into subtasks
        subtasks = self._identify_subtasks(task_description)

        if len(subtasks) <= 1:
            # Cannot decompose further
            return [
                self.lq_calculator.create_action(
                    action_id=f"a{depth}_1",
                    description=task_description,
                    goal=goal,
                    context=context,
                )
            ]

        # Recursively decompose subtasks
        actions = []
        for idx, subtask in enumerate(subtasks, start=1):
            action_id = f"a{depth}_{idx}"

            # Recursively decompose if needed
            sub_actions = self.decompose(subtask, goal, context, depth + 1)

            if len(sub_actions) == 1:
                # Single atomic subtask
                sub_actions[0].action_id = action_id
                actions.append(sub_actions[0])
            else:
                # Multiple sub-actions: create composite action
                composite_action = self._create_composite_action(
                    action_id, subtask, sub_actions, goal, context
                )
                actions.append(composite_action)

        # Identify dependencies between actions
        actions = self._identify_dependencies(actions, task_description)

        return actions

    def _is_atomic(self, task_description: str, context: Dict[str, any]) -> bool:
        """
        Determine if a task is atomic (indivisible).

        Args:
            task_description: Task description
            context: Additional context

        Returns:
            True if task is atomic
        """
        # Heuristics for atomic tasks:
        # 1. Very short description (< 10 words)
        word_count = len(task_description.split())
        if word_count <= 10:
            return True

        # 2. Estimated time below threshold
        time_estimate = self.lq_calculator._estimate_time(task_description, context)
        if time_estimate <= config.MIN_TASK_GRANULARITY:
            return True

        # 3. Single action verb
        import re

        action_verbs = [
            "write",
            "read",
            "run",
            "test",
            "install",
            "configure",
            "review",
            "validate",
        ]

        verb_count = sum(
            1 for verb in action_verbs if re.search(r"\b" + verb + r"\b", task_description.lower())
        )

        if verb_count == 1 and word_count <= 15:
            return True

        return False

    def _identify_subtasks(self, task_description: str) -> List[str]:
        """
        Identify subtasks within a task description.

        Args:
            task_description: Task description

        Returns:
            List of subtask descriptions
        """
        import re

        subtasks = []

        # Pattern 1: Numbered lists
        numbered_pattern = r"(?:\d+\.|\d+\))\s*([^.]+)"
        numbered_matches = re.findall(numbered_pattern, task_description)
        if numbered_matches and len(numbered_matches) >= 2:
            return [match.strip() for match in numbered_matches]

        # Pattern 2: Sequence words (first, then, next, finally)
        sequence_pattern = r"(?:first|then|next|after that|finally),?\s+([^,.;]+)"
        sequence_matches = re.findall(sequence_pattern, task_description, re.IGNORECASE)
        if sequence_matches and len(sequence_matches) >= 2:
            return [match.strip() for match in sequence_matches]

        # Pattern 3: Split by "and"
        if " and " in task_description.lower():
            parts = re.split(r"\s+and\s+", task_description, flags=re.IGNORECASE)
            if len(parts) >= 2 and len(parts) <= 5:
                return [part.strip() for part in parts]

        # Pattern 4: Split by sentences
        sentences = [s.strip() for s in task_description.split(".") if s.strip()]
        if len(sentences) >= 2 and len(sentences) <= 6:
            return sentences

        # Pattern 5: Detect major components (using keywords)
        component_patterns = [
            r"(build|create|write|implement)\s+([^,.;]+)",
            r"(setup|configure|install)\s+([^,.;]+)",
            r"(test|validate|verify)\s+([^,.;]+)",
        ]

        for pattern in component_patterns:
            matches = re.findall(pattern, task_description, re.IGNORECASE)
            if matches and len(matches) >= 2:
                return [f"{verb} {obj}" for verb, obj in matches]

        # Cannot identify clear subtasks
        return [task_description]

    def _create_composite_action(
        self,
        action_id: str,
        description: str,
        subtasks: List[Action],
        goal: Goal,
        context: Dict[str, any],
    ) -> Action:
        """
        Create a composite action from subtasks.

        Args:
            action_id: Action identifier
            description: Action description
            subtasks: List of sub-actions
            goal: Target goal
            context: Additional context

        Returns:
            Composite action containing subtasks
        """
        # Aggregate costs and impacts
        total_time = sum(subtask.cost.time_minutes for subtask in subtasks)

        # Average cognitive load (weighted by time)
        cognitive_loads = {
            "trivial": 10,
            "low": 25,
            "medium": 50,
            "high": 75,
            "very_high": 90,
        }

        avg_cognitive = sum(
            cognitive_loads[subtask.cost.cognitive_load] * subtask.cost.time_minutes
            for subtask in subtasks
        ) / total_time

        # Map back to cognitive load level
        if avg_cognitive <= 17.5:
            composite_cognitive = "trivial"
        elif avg_cognitive <= 37.5:
            composite_cognitive = "low"
        elif avg_cognitive <= 62.5:
            composite_cognitive = "medium"
        elif avg_cognitive <= 82.5:
            composite_cognitive = "high"
        else:
            composite_cognitive = "very_high"

        # Average resource cost
        avg_resource = sum(subtask.cost.resource_cost for subtask in subtasks) / len(subtasks)

        # Sum immediate progress (capped at 100)
        total_progress = min(100.0, sum(subtask.impact.immediate_progress for subtask in subtasks))

        # Max future efficiency (highest leverage subtask)
        max_efficiency = max(subtask.impact.future_efficiency for subtask in subtasks)

        # Create composite action
        from agno.fsa_0_1_mla_task_deconstructor.models.action_model import ActionCost, ActionImpact

        cost = ActionCost(
            time_minutes=total_time, cognitive_load=composite_cognitive, resource_cost=avg_resource
        )

        impact = ActionImpact(immediate_progress=total_progress, future_efficiency=max_efficiency)

        composite = Action(
            action_id=action_id,
            description=description,
            cost=cost,
            impact=impact,
            atomic=False,
            subtasks=subtasks,
        )

        return composite

    def _identify_dependencies(self, actions: List[Action], task_description: str) -> List[Action]:
        """
        Identify dependencies between actions.

        Args:
            actions: List of actions
            task_description: Original task description

        Returns:
            Actions with dependencies populated
        """
        import re

        # Heuristic dependency detection
        # 1. Sequential keywords (first, then, after, before)
        if re.search(r"\b(first|then|next|after|before|finally)\b", task_description, re.IGNORECASE):
            # Assume sequential dependencies
            for i in range(1, len(actions)):
                actions[i].dependencies.append(actions[i - 1].action_id)
            return actions

        # 2. Detect explicit dependencies in descriptions
        for i, action in enumerate(actions):
            for j, other_action in enumerate(actions):
                if i == j:
                    continue

                # Check if action description references other action
                if self._implies_dependency(action.description, other_action.description):
                    if other_action.action_id not in action.dependencies:
                        action.dependencies.append(other_action.action_id)

        # 3. Foundational tasks come first
        foundational_keywords = ["setup", "initialize", "install", "configure", "create framework"]

        foundational_actions = []
        dependent_actions = []

        for action in actions:
            is_foundational = any(
                kw in action.description.lower() for kw in foundational_keywords
            )
            if is_foundational:
                foundational_actions.append(action)
            else:
                dependent_actions.append(action)

        # Dependent actions depend on all foundational actions
        for dep_action in dependent_actions:
            for found_action in foundational_actions:
                if found_action.action_id not in dep_action.dependencies:
                    dep_action.dependencies.append(found_action.action_id)

        return actions

    def _implies_dependency(self, action_desc: str, other_desc: str) -> bool:
        """
        Check if action description implies dependency on another action.

        Args:
            action_desc: Action description
            other_desc: Other action description

        Returns:
            True if dependency is implied
        """
        # Extract key nouns from other action
        import re

        # Simple heuristic: extract words from other_desc
        other_words = set(
            word.lower()
            for word in re.findall(r"\b\w+\b", other_desc)
            if len(word) > 3  # Skip short words
        )

        # Check if action references these words with dependency keywords
        dependency_patterns = [
            r"(?:using|with|based on|after)\s+(\w+)",
            r"(?:test|validate|deploy)\s+(\w+)",
        ]

        for pattern in dependency_patterns:
            matches = re.findall(pattern, action_desc, re.IGNORECASE)
            for match in matches:
                if match.lower() in other_words:
                    return True

        return False
