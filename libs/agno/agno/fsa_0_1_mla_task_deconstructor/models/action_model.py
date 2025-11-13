"""
Action Model for MLA Framework

Represents an action 'a' with its costs, impacts, and LQ_MLA score.
"""

from dataclasses import dataclass, field
from typing import List, Optional

from agno.fsa_0_1_mla_task_deconstructor.config import config


@dataclass
class ActionCost:
    """
    Represents the cost C(a) of an action.

    Following MLA v3.0: C(a) = Σ[w_r * c_r(a)]
    where r ∈ {time, energy, resources}
    """

    time_minutes: float  # Time cost in minutes
    cognitive_load: str  # Cognitive load level: trivial, low, medium, high, very_high
    resource_cost: float = 0.0  # Additional resource cost (normalized 0-100)

    def total(self) -> float:
        """
        Calculate total weighted cost.

        Returns:
            Total cost C(a) as weighted sum of components (normalized 0-100)
        """
        # Get cognitive load value
        cognitive_value = config.COGNITIVE_LOAD_LEVELS.get(
            self.cognitive_load, config.COGNITIVE_LOAD_LEVELS["medium"]
        )

        # Normalize time to 0-100 scale (assume 240 min = 4 hours = 100)
        time_normalized = min(100.0, (self.time_minutes / 240.0) * 100.0)

        # Calculate weighted sum
        total_cost = (
            config.COST_WEIGHTS["time"] * time_normalized
            + config.COST_WEIGHTS["cognitive"] * cognitive_value
            + config.COST_WEIGHTS["resources"] * self.resource_cost
        )

        # Ensure minimum cost to avoid division by zero
        return max(1.0, total_cost)

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "time_minutes": self.time_minutes,
            "cognitive_load": self.cognitive_load,
            "resource_cost": self.resource_cost,
            "C_total": self.total(),
        }


@dataclass
class ActionImpact:
    """
    Represents the impact I(a, G) of an action on a goal.

    Following MLA v3.0: I(a, G) = w_p * P(a, G) + w_e * ΔE_f(a, G)
    where:
    - P(a, G): Immediate progress toward goal
    - ΔE_f(a, G): Change in future efficiency (compound effect)
    """

    immediate_progress: float  # P(a, G): Direct progress toward goal (0-100)
    future_efficiency: float  # ΔE_f(a, G): Future effort reduction (0-100)

    def total(self) -> float:
        """
        Calculate total weighted impact.

        Returns:
            Total impact I(a, G) as weighted sum
        """
        return (
            config.IMPACT_WEIGHTS["progress"] * self.immediate_progress
            + config.IMPACT_WEIGHTS["efficiency"] * self.future_efficiency
        )

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "immediate_progress": self.immediate_progress,
            "future_effort_reduction": self.future_efficiency,
            "I_total": self.total(),
        }


@dataclass
class Action:
    """
    Represents an action in the MLA framework.

    Attributes:
        action_id: Unique identifier for the action
        description: Clear description of what the action does
        cost: Cost components of the action
        impact: Impact components of the action
        dependencies: List of action_ids that must complete before this action
        mla_aligned: Whether this action is MLA-aligned
        atomic: Whether this is an atomic (indivisible) action
        subtasks: List of sub-actions if this is a composite task
    """

    action_id: str
    description: str
    cost: ActionCost
    impact: ActionImpact
    dependencies: List[str] = field(default_factory=list)
    mla_aligned: bool = True
    atomic: bool = True
    subtasks: List["Action"] = field(default_factory=list)
    rank: Optional[int] = None

    def calculate_lq_mla(self) -> float:
        """
        Calculate LQ_MLA (Leverage Quotient) for this action.

        Following MLA v3.0: LQ_MLA(a, G) = I(a, G) / C(a)

        Returns:
            LQ_MLA score (higher is better)
        """
        return self.impact.total() / self.cost.total()

    def to_dict(self) -> dict:
        """Convert action to dictionary format"""
        return {
            "action_id": self.action_id,
            "description": self.description,
            "immediate_cost": self.cost.to_dict(),
            "total_impact": self.impact.to_dict(),
            "LQ_MLA": round(self.calculate_lq_mla(), 2),
            "rank": self.rank,
            "mla_aligned": self.mla_aligned,
            "dependencies": self.dependencies,
            "atomic": self.atomic,
            "subtasks": [subtask.to_dict() for subtask in self.subtasks] if self.subtasks else [],
        }

    def __str__(self) -> str:
        """Human-readable representation"""
        lq = self.calculate_lq_mla()
        return f"Action {self.action_id} (LQ={lq:.2f}): {self.description}"

    @classmethod
    def from_dict(cls, data: dict) -> "Action":
        """Create Action from dictionary"""
        cost_data = data.get("immediate_cost", {})
        impact_data = data.get("total_impact", {})

        cost = ActionCost(
            time_minutes=cost_data.get("time_minutes", config.DEFAULT_TIME_ESTIMATE),
            cognitive_load=cost_data.get("cognitive_load", config.DEFAULT_COGNITIVE_LOAD),
            resource_cost=cost_data.get("resource_cost", 0.0),
        )

        impact = ActionImpact(
            immediate_progress=impact_data.get("immediate_progress", 50.0),
            future_efficiency=impact_data.get("future_effort_reduction", 0.0),
        )

        subtasks = [cls.from_dict(st) for st in data.get("subtasks", [])]

        return cls(
            action_id=data["action_id"],
            description=data["description"],
            cost=cost,
            impact=impact,
            dependencies=data.get("dependencies", []),
            mla_aligned=data.get("mla_aligned", True),
            atomic=data.get("atomic", True),
            subtasks=subtasks,
            rank=data.get("rank"),
        )
