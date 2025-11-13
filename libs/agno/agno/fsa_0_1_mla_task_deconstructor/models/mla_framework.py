"""
MLA Framework v3.0 Implementation

Implements the core MLA (Maximized Leverage Action) framework equations:
- C(a) = Σ[w_r * c_r(a)] - Total cost function
- I(a, G) = w_p * P(a, G) + w_e * ΔE_f(a, G) - Total impact function
- LQ_MLA(a, G) = I(a, G) / C(a) - Leverage Quotient
"""

from typing import List, Tuple

from agno.fsa_0_1_mla_task_deconstructor.config import config
from agno.fsa_0_1_mla_task_deconstructor.models.action_model import Action
from agno.fsa_0_1_mla_task_deconstructor.models.goal_model import Goal


class MLAFramework:
    """
    Core MLA Framework implementation for calculating leverage quotients
    and optimizing action selection.
    """

    @staticmethod
    def calculate_cost(action: Action) -> float:
        """
        Calculate total cost C(a) for an action.

        Following MLA v3.0: C(a) = Σ[w_r * c_r(a)]

        Args:
            action: Action to calculate cost for

        Returns:
            Total weighted cost (normalized 0-100)
        """
        return action.cost.total()

    @staticmethod
    def calculate_impact(action: Action, goal: Goal) -> float:
        """
        Calculate total impact I(a, G) for an action toward a goal.

        Following MLA v3.0: I(a, G) = w_p * P(a, G) + w_e * ΔE_f(a, G)

        Args:
            action: Action to calculate impact for
            goal: Target goal

        Returns:
            Total weighted impact
        """
        return action.impact.total()

    @staticmethod
    def calculate_lq_mla(action: Action, goal: Goal) -> float:
        """
        Calculate LQ_MLA (Leverage Quotient) for an action.

        Following MLA v3.0: LQ_MLA(a, G) = I(a, G) / C(a)

        Args:
            action: Action to calculate LQ for
            goal: Target goal

        Returns:
            LQ_MLA score (higher is better)
        """
        return action.calculate_lq_mla()

    @staticmethod
    def normalize_lq_score(lq_score: float, max_observed: float = 10.0) -> float:
        """
        Normalize LQ_MLA score to 0-100 scale.

        Args:
            lq_score: Raw LQ_MLA score
            max_observed: Maximum observed LQ score for normalization

        Returns:
            Normalized score (0-100)
        """
        # Normalize to 0-100 scale
        normalized = (lq_score / max_observed) * 100.0

        # Cap at 100
        return min(config.LQ_NORMALIZATION_MAX, max(config.LQ_NORMALIZATION_MIN, normalized))

    @classmethod
    def rank_actions(cls, actions: List[Action], goal: Goal) -> List[Action]:
        """
        Rank actions by their LQ_MLA scores (highest first).

        Args:
            actions: List of actions to rank
            goal: Target goal

        Returns:
            List of actions sorted by LQ_MLA (descending)
        """
        # Calculate LQ for each action
        actions_with_lq = [
            (action, cls.calculate_lq_mla(action, goal)) for action in actions
        ]

        # Sort by LQ (descending)
        sorted_actions = sorted(actions_with_lq, key=lambda x: x[1], reverse=True)

        # Assign ranks
        ranked_actions = []
        for rank, (action, lq) in enumerate(sorted_actions, start=1):
            action.rank = rank
            ranked_actions.append(action)

        return ranked_actions

    @classmethod
    def filter_mla_aligned(
        cls, actions: List[Action], goal: Goal, threshold: float = 1.0
    ) -> Tuple[List[Action], List[Action]]:
        """
        Filter actions into MLA-aligned (LQ >= threshold) and misaligned.

        Args:
            actions: List of actions to filter
            goal: Target goal
            threshold: LQ_MLA threshold for alignment (default: 1.0)

        Returns:
            Tuple of (aligned_actions, misaligned_actions)
        """
        aligned = []
        misaligned = []

        for action in actions:
            lq = cls.calculate_lq_mla(action, goal)
            if lq >= threshold:
                action.mla_aligned = True
                aligned.append(action)
            else:
                action.mla_aligned = False
                misaligned.append(action)

        return aligned, misaligned

    @staticmethod
    def compute_compound_effect(actions: List[Action]) -> float:
        """
        Compute total compound efficiency effect from a sequence of actions.

        This calculates how much future effort is reduced by completing
        this sequence of actions.

        Args:
            actions: Sequence of actions

        Returns:
            Total future efficiency gain (0-100)
        """
        total_efficiency = 0.0
        compound_multiplier = 1.0

        for action in actions:
            # Add efficiency gain
            efficiency = action.impact.future_efficiency
            total_efficiency += efficiency * compound_multiplier

            # Compound effect: each efficiency-boosting action makes future actions more effective
            if efficiency > 50:  # High efficiency gains compound
                compound_multiplier *= 1.1  # 10% boost to future actions

        return min(100.0, total_efficiency)

    @classmethod
    def optimize_sequence(cls, actions: List[Action], goal: Goal) -> List[str]:
        """
        Optimize the sequence of actions to maximize LQ_MLA and respect dependencies.

        Uses topological sort with LQ_MLA prioritization.

        Args:
            actions: List of actions to sequence
            goal: Target goal

        Returns:
            Ordered list of action_ids
        """
        # Build dependency graph
        action_map = {action.action_id: action for action in actions}
        in_degree = {action.action_id: len(action.dependencies) for action in actions}
        dependency_graph = {action.action_id: action.dependencies for action in actions}

        # Find actions with no dependencies and rank by LQ_MLA
        ready_queue = []
        for action in actions:
            if in_degree[action.action_id] == 0:
                lq = cls.calculate_lq_mla(action, goal)
                ready_queue.append((action.action_id, lq))

        # Sort ready queue by LQ (highest first)
        ready_queue.sort(key=lambda x: x[1], reverse=True)

        # Topological sort with LQ prioritization
        sequence = []
        while ready_queue:
            # Pick highest LQ action from ready queue
            current_id, _ = ready_queue.pop(0)
            sequence.append(current_id)

            # Update dependencies
            for action in actions:
                if current_id in action.dependencies:
                    in_degree[action.action_id] -= 1

                    # If all dependencies satisfied, add to ready queue
                    if in_degree[action.action_id] == 0:
                        lq = cls.calculate_lq_mla(action, goal)
                        ready_queue.append((action.action_id, lq))

                        # Re-sort ready queue
                        ready_queue.sort(key=lambda x: x[1], reverse=True)

        # Check for circular dependencies
        if len(sequence) != len(actions):
            raise ValueError("Circular dependencies detected in action set")

        return sequence

    @staticmethod
    def validate_fractal_alignment(action: Action, goal: Goal) -> bool:
        """
        Validate that an action maintains fractal MLA alignment.

        Fractal alignment means:
        1. The action itself is MLA-optimized
        2. All subtasks (if any) are also MLA-optimized
        3. The decomposition maintains goal alignment

        Args:
            action: Action to validate
            goal: Target goal

        Returns:
            True if fractally aligned
        """
        # Check action itself
        lq = action.calculate_lq_mla()
        if lq < 1.0:  # Below neutral leverage
            return False

        # Check all subtasks recursively
        if action.subtasks:
            for subtask in action.subtasks:
                if not MLAFramework.validate_fractal_alignment(subtask, goal):
                    return False

        return True
