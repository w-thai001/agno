"""
LQ Calculator for MLA Framework

Calculates LQ_MLA scores for actions and estimates cost/impact components.
"""

from typing import Dict, List

from agno.fsa_0_1_mla_task_deconstructor.config import config
from agno.fsa_0_1_mla_task_deconstructor.models.action_model import Action, ActionCost, ActionImpact
from agno.fsa_0_1_mla_task_deconstructor.models.goal_model import Goal


class LQCalculator:
    """
    Calculates LQ_MLA scores and estimates action costs and impacts.

    Applies heuristics to estimate:
    - Time cost
    - Cognitive load
    - Resource cost
    - Immediate progress
    - Future efficiency gains
    """

    def __init__(self):
        """Initialize LQ calculator"""
        pass

    def estimate_action_components(
        self, action_description: str, goal: Goal, context: Dict[str, any] = None
    ) -> Dict[str, any]:
        """
        Estimate cost and impact components for an action.

        Args:
            action_description: Description of the action
            goal: Target goal
            context: Additional context (resources, constraints, etc.)

        Returns:
            Dictionary with estimated components
        """
        context = context or {}

        # Estimate cost components
        time_estimate = self._estimate_time(action_description, context)
        cognitive_load = self._estimate_cognitive_load(action_description, context)
        resource_cost = self._estimate_resource_cost(action_description, context)

        # Estimate impact components
        immediate_progress = self._estimate_immediate_progress(action_description, goal, context)
        future_efficiency = self._estimate_future_efficiency(action_description, goal, context)

        return {
            "cost": {
                "time_minutes": time_estimate,
                "cognitive_load": cognitive_load,
                "resource_cost": resource_cost,
            },
            "impact": {
                "immediate_progress": immediate_progress,
                "future_efficiency": future_efficiency,
            },
        }

    def _estimate_time(self, action_description: str, context: Dict[str, any]) -> float:
        """
        Estimate time cost in minutes.

        Args:
            action_description: Action description
            context: Additional context

        Returns:
            Estimated time in minutes
        """
        # Base time estimate
        base_time = config.DEFAULT_TIME_ESTIMATE

        # Adjust based on action complexity indicators
        complexity_keywords = {
            "simple": 0.5,
            "quick": 0.5,
            "basic": 0.7,
            "complex": 2.0,
            "comprehensive": 2.5,
            "detailed": 1.5,
            "thorough": 1.8,
            "implement": 1.5,
            "build": 2.0,
            "create": 1.5,
            "write": 1.2,
            "research": 1.8,
            "analyze": 1.6,
        }

        multiplier = 1.0
        action_lower = action_description.lower()

        for keyword, factor in complexity_keywords.items():
            if keyword in action_lower:
                multiplier *= factor

        # Check for scope indicators
        if "system" in action_lower or "framework" in action_lower:
            multiplier *= 1.5

        if "test" in action_lower:
            multiplier *= 1.3

        return base_time * multiplier

    def _estimate_cognitive_load(self, action_description: str, context: Dict[str, any]) -> str:
        """
        Estimate cognitive load level.

        Args:
            action_description: Action description
            context: Additional context

        Returns:
            Cognitive load level: trivial, low, medium, high, very_high
        """
        action_lower = action_description.lower()

        # High cognitive load indicators
        high_load_keywords = [
            "algorithm",
            "optimize",
            "design",
            "architecture",
            "complex",
            "integrate",
            "analyze",
            "research",
        ]

        # Low cognitive load indicators
        low_load_keywords = [
            "copy",
            "paste",
            "simple",
            "basic",
            "trivial",
            "quick",
            "straightforward",
        ]

        # Medium cognitive load indicators
        medium_load_keywords = [
            "implement",
            "write",
            "create",
            "build",
            "configure",
        ]

        # Count matches
        high_count = sum(1 for kw in high_load_keywords if kw in action_lower)
        low_count = sum(1 for kw in low_load_keywords if kw in action_lower)
        medium_count = sum(1 for kw in medium_load_keywords if kw in action_lower)

        # Determine load level
        if high_count >= 2:
            return "very_high"
        elif high_count >= 1:
            return "high"
        elif medium_count >= 1:
            return "medium"
        elif low_count >= 1:
            return "low"
        else:
            return "medium"  # Default

    def _estimate_resource_cost(self, action_description: str, context: Dict[str, any]) -> float:
        """
        Estimate resource cost (0-100 scale).

        Args:
            action_description: Action description
            context: Additional context

        Returns:
            Resource cost estimate
        """
        # Base resource cost
        base_cost = 10.0

        action_lower = action_description.lower()

        # Check for resource-intensive keywords
        resource_keywords = {
            "deploy": 30.0,
            "infrastructure": 40.0,
            "cloud": 25.0,
            "server": 20.0,
            "database": 15.0,
            "api": 10.0,
            "external": 15.0,
        }

        for keyword, cost in resource_keywords.items():
            if keyword in action_lower:
                base_cost += cost

        # Check budget constraints
        if context.get("budget"):
            budget = context["budget"]
            if budget < 100:
                base_cost *= 0.5  # Low budget means low resource cost expected

        return min(100.0, base_cost)

    def _estimate_immediate_progress(
        self, action_description: str, goal: Goal, context: Dict[str, any]
    ) -> float:
        """
        Estimate immediate progress toward goal (0-100 scale).

        Args:
            action_description: Action description
            goal: Target goal
            context: Additional context

        Returns:
            Immediate progress estimate
        """
        # Base progress
        base_progress = 50.0

        # Check alignment with goal
        goal_terms = set(goal.G.lower().split())
        action_terms = set(action_description.lower().split())

        alignment = len(goal_terms.intersection(action_terms))

        if alignment >= 3:
            base_progress += 30.0
        elif alignment >= 2:
            base_progress += 20.0
        elif alignment >= 1:
            base_progress += 10.0

        # Check for direct outcome keywords
        outcome_keywords = ["complete", "finish", "deliver", "achieve", "produce"]
        if any(kw in action_description.lower() for kw in outcome_keywords):
            base_progress += 15.0

        return min(100.0, base_progress)

    def _estimate_future_efficiency(
        self, action_description: str, goal: Goal, context: Dict[str, any]
    ) -> float:
        """
        Estimate future efficiency gains (0-100 scale).

        Args:
            action_description: Action description
            goal: Target goal
            context: Additional context

        Returns:
            Future efficiency estimate
        """
        # Base efficiency
        base_efficiency = 20.0

        action_lower = action_description.lower()

        # High-leverage actions (force multipliers)
        leverage_keywords = {
            "framework": 40.0,
            "system": 35.0,
            "automation": 50.0,
            "automate": 50.0,
            "template": 30.0,
            "tool": 35.0,
            "library": 30.0,
            "infrastructure": 45.0,
            "foundation": 40.0,
            "platform": 40.0,
        }

        for keyword, efficiency in leverage_keywords.items():
            if keyword in action_lower:
                base_efficiency += efficiency

        # Check if this is a foundational task
        if "first" in action_lower or "setup" in action_lower or "initialize" in action_lower:
            base_efficiency += 20.0

        return min(100.0, base_efficiency)

    def create_action(
        self,
        action_id: str,
        description: str,
        goal: Goal,
        context: Dict[str, any] = None,
        dependencies: List[str] = None,
    ) -> Action:
        """
        Create an Action object with estimated cost and impact.

        Args:
            action_id: Unique action identifier
            description: Action description
            goal: Target goal
            context: Additional context
            dependencies: List of dependency action IDs

        Returns:
            Action object with calculated LQ_MLA
        """
        components = self.estimate_action_components(description, goal, context)

        cost = ActionCost(
            time_minutes=components["cost"]["time_minutes"],
            cognitive_load=components["cost"]["cognitive_load"],
            resource_cost=components["cost"]["resource_cost"],
        )

        impact = ActionImpact(
            immediate_progress=components["impact"]["immediate_progress"],
            future_efficiency=components["impact"]["future_efficiency"],
        )

        return Action(
            action_id=action_id,
            description=description,
            cost=cost,
            impact=impact,
            dependencies=dependencies or [],
        )
