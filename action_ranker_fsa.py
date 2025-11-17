"""
Action Ranker FSA (Finite State Automaton) with LQ_MLA Scoring

This module implements an advanced action ranking system using Leverage Quotient
with Marginal Leverage Analysis (LQ_MLA) algorithm for optimal action selection.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import logging
from copy import deepcopy


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ActionState(Enum):
    """Enumeration of possible action states in FSA."""
    UNPROCESSED = "unprocessed"
    FILTERED = "filtered"
    SCORED = "scored"
    RANKED = "ranked"
    REJECTED = "rejected"


@dataclass
class Action:
    """
    Represents an action with metadata for ranking.

    Attributes:
        id: Unique identifier for the action
        name: Human-readable action name
        description: Detailed action description
        impact: Expected impact score (0.0-10.0)
        cost: Resource cost (0.0-10.0, lower is better)
        risk: Risk level (0.0-10.0, lower is better)
        time_to_value: Time to realize value in days
        dependencies: List of action IDs this action depends on
        metadata: Additional action-specific metadata
    """
    id: str
    name: str
    description: str = ""
    impact: float = 5.0
    cost: float = 5.0
    risk: float = 5.0
    time_to_value: float = 1.0
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate action attributes."""
        self._validate_range("impact", self.impact)
        self._validate_range("cost", self.cost)
        self._validate_range("risk", self.risk)
        if self.time_to_value <= 0:
            raise ValueError(f"time_to_value must be positive, got {self.time_to_value}")

    def _validate_range(self, name: str, value: float) -> None:
        """Validate that a value is within acceptable range."""
        if not 0.0 <= value <= 10.0:
            raise ValueError(f"{name} must be between 0.0 and 10.0, got {value}")


@dataclass
class RankedAction:
    """
    Represents a ranked action with scoring details.

    Attributes:
        action: The original action
        lq_mla_score: Final LQ_MLA score
        rank: Position in ranked list (1-based)
        rationale: Explanation of the ranking
        score_breakdown: Detailed scoring components
        state: Current FSA state
    """
    action: Action
    lq_mla_score: float
    rank: int = 0
    rationale: str = ""
    score_breakdown: Dict[str, float] = field(default_factory=dict)
    state: ActionState = ActionState.SCORED

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.action.id,
            "name": self.action.name,
            "rank": self.rank,
            "lq_mla_score": round(self.lq_mla_score, 4),
            "rationale": self.rationale,
            "score_breakdown": {k: round(v, 4) for k, v in self.score_breakdown.items()},
            "state": self.state.value
        }


@dataclass
class ScoringWeights:
    """
    Configurable weights for multi-factor scoring.

    All weights should sum to 1.0 for normalized scoring.
    """
    impact: float = 0.35
    cost: float = 0.20
    risk: float = 0.20
    dependencies: float = 0.10
    time_to_value: float = 0.15

    def __post_init__(self):
        """Validate weights sum to approximately 1.0."""
        total = self.impact + self.cost + self.risk + self.dependencies + self.time_to_value
        if not (0.99 <= total <= 1.01):
            raise ValueError(f"Weights must sum to 1.0, got {total}")


@dataclass
class RankingConstraints:
    """
    Constraints for filtering actions before ranking.

    Attributes:
        max_cost: Maximum acceptable cost
        max_risk: Maximum acceptable risk
        min_impact: Minimum required impact
        max_time_to_value: Maximum acceptable time to value
        required_tags: Tags that must be present in action metadata
        excluded_tags: Tags that must not be present in action metadata
    """
    max_cost: Optional[float] = None
    max_risk: Optional[float] = None
    min_impact: Optional[float] = None
    max_time_to_value: Optional[float] = None
    required_tags: List[str] = field(default_factory=list)
    excluded_tags: List[str] = field(default_factory=list)


class ActionRankerFSA:
    """
    Finite State Automaton for ranking actions using LQ_MLA algorithm.

    The LQ_MLA (Leverage Quotient - Marginal Leverage Analysis) algorithm
    evaluates actions based on their marginal benefit relative to costs and risks,
    optimizing for maximum leverage in achieving stated goals.

    FSA States:
        UNPROCESSED -> FILTERED -> SCORED -> RANKED
                    -> REJECTED (if constraints not met)
    """

    def __init__(
        self,
        weights: Optional[ScoringWeights] = None,
        constraints: Optional[RankingConstraints] = None,
        enable_dependency_boost: bool = True
    ):
        """
        Initialize the Action Ranker FSA.

        Args:
            weights: Custom scoring weights (uses defaults if None)
            constraints: Filtering constraints (no filtering if None)
            enable_dependency_boost: Whether to boost scores for actions with satisfied dependencies
        """
        self.weights = weights or ScoringWeights()
        self.constraints = constraints or RankingConstraints()
        self.enable_dependency_boost = enable_dependency_boost
        self._state_transitions: Dict[str, ActionState] = {}

    def rank_actions(
        self,
        actions: List[Dict[str, Any]],
        context: Dict[str, Any],
        goal: str
    ) -> List[Dict[str, Any]]:
        """
        Rank actions using LQ_MLA algorithm.

        Args:
            actions: List of action dictionaries with metadata
            context: Context dictionary containing current state and available resources
            goal: Goal description for context-aware ranking

        Returns:
            List of ranked actions with scores and rationale

        Raises:
            ValueError: If inputs are invalid
            TypeError: If input types are incorrect
        """
        # Input validation
        self._validate_inputs(actions, context, goal)

        # Convert to Action objects
        action_objects = self._parse_actions(actions)

        if not action_objects:
            logger.warning("No valid actions to rank")
            return []

        # FSA State 1: Filter actions based on constraints
        filtered_actions = self._filter_actions(action_objects, context)

        if not filtered_actions:
            logger.warning("No actions passed constraint filtering")
            return []

        # FSA State 2: Calculate LQ_MLA scores
        scored_actions = self._score_actions(filtered_actions, context, goal)

        # FSA State 3: Rank and generate rationale
        ranked_actions = self._rank_and_explain(scored_actions, goal, context)

        # Convert to dictionary format
        return [ra.to_dict() for ra in ranked_actions]

    def _validate_inputs(
        self,
        actions: List[Dict[str, Any]],
        context: Dict[str, Any],
        goal: str
    ) -> None:
        """Validate input parameters."""
        if not isinstance(actions, list):
            raise TypeError(f"actions must be a list, got {type(actions)}")

        if not isinstance(context, dict):
            raise TypeError(f"context must be a dict, got {type(context)}")

        if not isinstance(goal, str):
            raise TypeError(f"goal must be a string, got {type(goal)}")

        if not actions:
            raise ValueError("actions list cannot be empty")

        if not goal.strip():
            raise ValueError("goal cannot be empty")

    def _parse_actions(self, actions: List[Dict[str, Any]]) -> List[Action]:
        """
        Parse action dictionaries into Action objects.

        Args:
            actions: List of action dictionaries

        Returns:
            List of valid Action objects
        """
        action_objects = []

        for i, action_dict in enumerate(actions):
            try:
                # Extract required fields
                action_id = action_dict.get("id", f"action_{i}")
                name = action_dict.get("name", f"Action {i}")

                # Create Action object with defaults for optional fields
                action = Action(
                    id=action_id,
                    name=name,
                    description=action_dict.get("description", ""),
                    impact=float(action_dict.get("impact", 5.0)),
                    cost=float(action_dict.get("cost", 5.0)),
                    risk=float(action_dict.get("risk", 5.0)),
                    time_to_value=float(action_dict.get("time_to_value", 1.0)),
                    dependencies=action_dict.get("dependencies", []),
                    metadata=action_dict.get("metadata", {})
                )

                action_objects.append(action)
                self._state_transitions[action_id] = ActionState.UNPROCESSED

            except (ValueError, TypeError) as e:
                logger.error(f"Error parsing action {i}: {e}")
                continue

        return action_objects

    def _filter_actions(
        self,
        actions: List[Action],
        context: Dict[str, Any]
    ) -> List[Action]:
        """
        Filter actions based on constraints.

        Args:
            actions: List of actions to filter
            context: Current context

        Returns:
            List of actions that pass all constraints
        """
        filtered = []

        for action in actions:
            # Check cost constraint
            if self.constraints.max_cost is not None:
                if action.cost > self.constraints.max_cost:
                    self._state_transitions[action.id] = ActionState.REJECTED
                    logger.debug(f"Action {action.id} rejected: cost too high")
                    continue

            # Check risk constraint
            if self.constraints.max_risk is not None:
                if action.risk > self.constraints.max_risk:
                    self._state_transitions[action.id] = ActionState.REJECTED
                    logger.debug(f"Action {action.id} rejected: risk too high")
                    continue

            # Check impact constraint
            if self.constraints.min_impact is not None:
                if action.impact < self.constraints.min_impact:
                    self._state_transitions[action.id] = ActionState.REJECTED
                    logger.debug(f"Action {action.id} rejected: impact too low")
                    continue

            # Check time to value constraint
            if self.constraints.max_time_to_value is not None:
                if action.time_to_value > self.constraints.max_time_to_value:
                    self._state_transitions[action.id] = ActionState.REJECTED
                    logger.debug(f"Action {action.id} rejected: time to value too high")
                    continue

            # Check required tags
            if self.constraints.required_tags:
                action_tags = set(action.metadata.get("tags", []))
                if not all(tag in action_tags for tag in self.constraints.required_tags):
                    self._state_transitions[action.id] = ActionState.REJECTED
                    logger.debug(f"Action {action.id} rejected: missing required tags")
                    continue

            # Check excluded tags
            if self.constraints.excluded_tags:
                action_tags = set(action.metadata.get("tags", []))
                if any(tag in action_tags for tag in self.constraints.excluded_tags):
                    self._state_transitions[action.id] = ActionState.REJECTED
                    logger.debug(f"Action {action.id} rejected: contains excluded tags")
                    continue

            self._state_transitions[action.id] = ActionState.FILTERED
            filtered.append(action)

        return filtered

    def _score_actions(
        self,
        actions: List[Action],
        context: Dict[str, Any],
        goal: str
    ) -> List[RankedAction]:
        """
        Calculate LQ_MLA scores for actions.

        The LQ_MLA algorithm calculates:
        1. Base scores for each factor (normalized)
        2. Marginal leverage for each action
        3. Combined weighted score
        4. Dependency adjustments

        Args:
            actions: Filtered actions to score
            context: Current context
            goal: Goal description

        Returns:
            List of RankedAction objects with scores
        """
        scored_actions = []
        action_lookup = {a.id: a for a in actions}

        for action in actions:
            # Calculate individual factor scores (0-1 scale)
            impact_score = self._normalize_score(action.impact, 0, 10)
            cost_score = self._normalize_score(10 - action.cost, 0, 10)  # Inverted: lower cost is better
            risk_score = self._normalize_score(10 - action.risk, 0, 10)  # Inverted: lower risk is better

            # Time-to-value score (faster is better)
            max_ttv = max(a.time_to_value for a in actions)
            time_score = self._normalize_score(max_ttv - action.time_to_value, 0, max_ttv)

            # Dependency score
            dependency_score = self._calculate_dependency_score(action, action_lookup, context)

            # Calculate marginal leverage quotient
            # LQ = (Impact * Velocity) / (Cost * Risk)
            # where Velocity = 1 / time_to_value
            velocity = 1.0 / action.time_to_value
            leverage_numerator = action.impact * velocity
            leverage_denominator = max(action.cost * action.risk, 0.1)  # Avoid division by zero
            leverage_quotient = leverage_numerator / leverage_denominator

            # Normalize leverage quotient
            lq_normalized = min(leverage_quotient / 10.0, 1.0)  # Cap at 1.0

            # Apply weighted scoring with marginal analysis
            base_score = (
                self.weights.impact * impact_score +
                self.weights.cost * cost_score +
                self.weights.risk * risk_score +
                self.weights.time_to_value * time_score +
                self.weights.dependencies * dependency_score
            )

            # Combine base score with leverage quotient for final LQ_MLA score
            # LQ_MLA = base_score * (1 + leverage_quotient_bonus)
            lq_mla_score = base_score * (1.0 + lq_normalized * 0.5)  # Up to 50% bonus from leverage

            # Create score breakdown
            score_breakdown = {
                "impact_score": impact_score,
                "cost_score": cost_score,
                "risk_score": risk_score,
                "time_to_value_score": time_score,
                "dependency_score": dependency_score,
                "leverage_quotient": leverage_quotient,
                "base_score": base_score,
                "lq_mla_final": lq_mla_score
            }

            # Create RankedAction
            ranked_action = RankedAction(
                action=action,
                lq_mla_score=lq_mla_score,
                score_breakdown=score_breakdown,
                state=ActionState.SCORED
            )

            scored_actions.append(ranked_action)
            self._state_transitions[action.id] = ActionState.SCORED

        return scored_actions

    def _normalize_score(self, value: float, min_val: float, max_val: float) -> float:
        """
        Normalize a value to 0-1 range.

        Args:
            value: Value to normalize
            min_val: Minimum possible value
            max_val: Maximum possible value

        Returns:
            Normalized value between 0 and 1
        """
        if max_val == min_val:
            return 0.5
        return max(0.0, min(1.0, (value - min_val) / (max_val - min_val)))

    def _calculate_dependency_score(
        self,
        action: Action,
        action_lookup: Dict[str, Action],
        context: Dict[str, Any]
    ) -> float:
        """
        Calculate dependency score for an action.

        Higher score if dependencies are satisfied or action has no dependencies.
        Lower score if action has many unmet dependencies.

        Args:
            action: Action to score
            action_lookup: Lookup dictionary for all actions
            context: Current context with completed actions

        Returns:
            Dependency score between 0 and 1
        """
        if not action.dependencies:
            return 1.0  # No dependencies = perfect score

        completed_actions = set(context.get("completed_actions", []))
        available_actions = set(action_lookup.keys())

        satisfied_deps = 0
        total_deps = len(action.dependencies)

        for dep_id in action.dependencies:
            # Check if dependency is already completed
            if dep_id in completed_actions:
                satisfied_deps += 1
            # Check if dependency is available in current action set
            elif dep_id in available_actions:
                satisfied_deps += 0.5  # Partial credit for available but not completed

        dependency_ratio = satisfied_deps / total_deps if total_deps > 0 else 1.0

        # Apply boost if enabled and dependencies are well-satisfied
        if self.enable_dependency_boost and dependency_ratio > 0.7:
            dependency_ratio = min(1.0, dependency_ratio * 1.2)

        return dependency_ratio

    def _rank_and_explain(
        self,
        scored_actions: List[RankedAction],
        goal: str,
        context: Dict[str, Any]
    ) -> List[RankedAction]:
        """
        Rank actions and generate rationale.

        Args:
            scored_actions: Actions with LQ_MLA scores
            goal: Goal description
            context: Current context

        Returns:
            Sorted list of ranked actions with rationale
        """
        # Sort by LQ_MLA score (descending)
        ranked = sorted(scored_actions, key=lambda x: x.lq_mla_score, reverse=True)

        # Assign ranks and generate rationale
        for rank, ranked_action in enumerate(ranked, start=1):
            ranked_action.rank = rank
            ranked_action.state = ActionState.RANKED
            ranked_action.rationale = self._generate_rationale(
                ranked_action, rank, len(ranked), goal, context
            )
            self._state_transitions[ranked_action.action.id] = ActionState.RANKED

        return ranked

    def _generate_rationale(
        self,
        ranked_action: RankedAction,
        rank: int,
        total: int,
        goal: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Generate human-readable rationale for ranking.

        Args:
            ranked_action: The ranked action
            rank: Current rank
            total: Total number of actions
            goal: Goal description
            context: Current context

        Returns:
            Rationale string
        """
        action = ranked_action.action
        breakdown = ranked_action.score_breakdown

        # Determine tier
        if rank <= total * 0.2:
            tier = "high-priority"
        elif rank <= total * 0.6:
            tier = "medium-priority"
        else:
            tier = "low-priority"

        # Identify strengths
        strengths = []
        if breakdown["impact_score"] > 0.7:
            strengths.append("high impact")
        if breakdown["cost_score"] > 0.7:
            strengths.append("low cost")
        if breakdown["risk_score"] > 0.7:
            strengths.append("low risk")
        if breakdown["time_to_value_score"] > 0.7:
            strengths.append("quick wins")
        if breakdown["leverage_quotient"] > 1.0:
            strengths.append("strong leverage")

        # Identify weaknesses
        weaknesses = []
        if breakdown["impact_score"] < 0.3:
            weaknesses.append("limited impact")
        if breakdown["cost_score"] < 0.3:
            weaknesses.append("high cost")
        if breakdown["risk_score"] < 0.3:
            weaknesses.append("high risk")
        if breakdown["dependency_score"] < 0.5:
            weaknesses.append("unmet dependencies")

        # Build rationale
        parts = [f"Ranked #{rank} ({tier})"]

        if strengths:
            parts.append(f"Strengths: {', '.join(strengths)}")

        if weaknesses:
            parts.append(f"Considerations: {', '.join(weaknesses)}")

        parts.append(f"LQ_MLA score: {ranked_action.lq_mla_score:.3f}")

        return ". ".join(parts) + "."

    def get_state_transitions(self) -> Dict[str, str]:
        """
        Get FSA state transitions for all processed actions.

        Returns:
            Dictionary mapping action IDs to their current states
        """
        return {aid: state.value for aid, state in self._state_transitions.items()}


# Convenience function
def rank_actions(
    actions: List[Dict[str, Any]],
    context: Dict[str, Any],
    goal: str,
    weights: Optional[ScoringWeights] = None,
    constraints: Optional[RankingConstraints] = None
) -> List[Dict[str, Any]]:
    """
    Convenience function to rank actions using default ActionRankerFSA.

    Args:
        actions: List of action dictionaries
        context: Context dictionary
        goal: Goal description
        weights: Optional custom weights
        constraints: Optional constraints

    Returns:
        Ranked action list
    """
    ranker = ActionRankerFSA(weights=weights, constraints=constraints)
    return ranker.rank_actions(actions, context, goal)
